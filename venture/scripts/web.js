const childProcess = require("child_process");
const fs = require("fs");
const Module = require("module");
const path = require("path");

const DEFAULT_DEBUG_PORT = 9331;
const DEFAULT_WAIT_SECONDS = 60;
const DEFAULT_SMES_URL = "https://www.smes.go.kr/venturein/home/viewHome";
const DEFAULT_NODE_MODULE_PATH =
  "C:/Users/chaconne/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/node_modules";

function assertCliArgsNotMojibake() {
  const joined = process.argv.slice(2).join(" ");
  if (/[�]|\?\?/.test(joined)) {
    throw new Error("CLI 인자에 깨진 문자가 있습니다. UTF-8로 다시 실행하세요.");
  }
}

function stringifyPowerShellSafeJson(value, spaces = 2) {
  return JSON.stringify(value, null, spaces);
}

function requirePlaywrightCore() {
  try {
    return require("playwright-core");
  } catch (error) {
    if (!process.env.NODE_PATH && fs.existsSync(DEFAULT_NODE_MODULE_PATH)) {
      process.env.NODE_PATH = DEFAULT_NODE_MODULE_PATH;
      Module._initPaths();
      return require("playwright-core");
    }
    throw error;
  }
}

const { chromium } = requirePlaywrightCore();

function parseArgs(argv = process.argv.slice(2)) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function chromePath() {
  const candidates = [
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    path.join(process.env.LOCALAPPDATA || "", "Google/Chrome/Application/chrome.exe"),
  ];
  const found = candidates.find((candidate) => fs.existsSync(candidate));
  if (!found) throw new Error("Chrome executable not found");
  return found;
}

function parseFrontmatter(text) {
  const trimmed = text.replace(/^\uFEFF/, "");
  if (!trimmed.startsWith("---")) return {};
  const parts = trimmed.split("---");
  if (parts.length < 3) return {};

  const meta = {};
  for (const rawLine of parts[1].split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes(":")) continue;
    const [rawKey, ...rest] = line.split(":");
    const key = rawKey.trim();
    const value = rest.join(":").trim().replace(/^['"]|['"]$/g, "");
    meta[key] = value;
  }
  return meta;
}

function parseReadmeKeyValues(text) {
  const values = {};
  for (const rawLine of String(text || "").replace(/\r/g, "").split("\n")) {
    const line = rawLine.trim();
    const match = line.match(/^-\s*([A-Za-z0-9_.-]+):\s*(.*)$/);
    if (!match) continue;
    values[match[1]] = match[2].trim().replace(/^['"]|['"]$/g, "");
  }
  return values;
}

function parseDotEnv(text) {
  const values = {};
  for (const rawLine of String(text || "").replace(/\r/g, "").split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$/);
    if (!match) continue;
    values[match[1]] = match[2].trim().replace(/^['"]|['"]$/g, "");
  }
  return values;
}

// 포털 자격증명은 git에 올리지 않는 companies/<회사>/.env에 둔다.
// 구 작업공간을 위해 회사정보.md와 README.md도 fallback으로 읽는다.
function loadCompanyConfig(company) {
  const root = companyRoot(company);
  const envPath = path.join(root, ".env");
  const infoPath = path.join(root, "회사정보.md");
  const readmePath = path.join(root, "README.md");

  let meta = {};
  let filePath = null;
  if (fs.existsSync(envPath)) {
    const env = parseDotEnv(fs.readFileSync(envPath, "utf8"));
    meta = { smes_id: env.SMES_ID, smes_pw: env.SMES_PW, smes_url: env.SMES_URL };
    filePath = envPath;
  } else {
    for (const candidate of [infoPath, readmePath]) {
      if (!fs.existsSync(candidate)) continue;
      const text = fs.readFileSync(candidate, "utf8");
      const parsed = { ...parseFrontmatter(text), ...parseReadmeKeyValues(text) };
      if (!parsed.smes_id && !parsed.smes_pw) continue;
      meta = parsed;
      filePath = candidate;
      break;
    }
  }

  if (!filePath) {
    throw new Error(
      `companies/${company}/.env 파일이 없습니다. SMES_ID, SMES_PW를 담은 .env를 만드세요.`
    );
  }

  const smesId = meta.smes_id;
  const smesPw = meta.smes_pw;
  const smesUrl = meta.smes_url || DEFAULT_SMES_URL;

  if (!smesId) throw new Error(`companies/${company}/.env에 SMES_ID가 없습니다.`);
  if (!smesPw) throw new Error(`companies/${company}/.env에 SMES_PW가 없습니다.`);

  return { company, smesId, smesPw, smesUrl, filePath };
}

function readJsonIfExists(filePath) {
  if (!fs.existsSync(filePath)) return {};
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, ""));
  } catch (error) {
    return {};
  }
}

function writeChromePasswordManagerPrefs(userDataDir) {
  const defaultDir = path.join(userDataDir, "Default");
  fs.mkdirSync(defaultDir, { recursive: true });
  const preferencesFile = path.join(defaultDir, "Preferences");
  const preferences = readJsonIfExists(preferencesFile);
  preferences.credentials_enable_service = false;
  preferences.profile = {
    ...(preferences.profile || {}),
    password_manager_enabled: false,
  };
  preferences.autofill = {
    ...(preferences.autofill || {}),
    profile_enabled: false,
    credit_card_enabled: false,
  };
  fs.writeFileSync(preferencesFile, JSON.stringify(preferences, null, 2), "utf8");
}

function companyRoot(company) {
  return path.join(process.cwd(), "companies", company);
}

function applicationPath(company, fileName) {
  return path.join(process.cwd(), ".venture-sessions", "portal-runs", safeFilePart(company), fileName);
}

function experimentScreenshotDir(company) {
  return applicationPath(company, "screenshots");
}

function sessionPath(company) {
  const sessionDir = path.join(process.cwd(), ".venture-sessions");
  fs.mkdirSync(sessionDir, { recursive: true });
  return path.join(sessionDir, `${company}.json`);
}

function safeFilePart(value) {
  return String(value || "session")
    .replace(/[^\p{L}\p{N}_.-]+/gu, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80) || "session";
}

function automationChromeProfileDir(company, debugPort) {
  return path.join(
    process.cwd(),
    ".venture-sessions",
    "chrome-profiles",
    `${safeFilePart(company)}-${debugPort}`,
  );
}

async function fetchTargets(cdpUrl) {
  const response = await fetch(`${cdpUrl}/json/list`);
  if (!response.ok) throw new Error(`CDP target list failed: ${response.status}`);
  return response.json();
}

async function waitForCdp(cdpUrl, waitSeconds = 20) {
  const deadline = Date.now() + waitSeconds * 1000;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      await fetchTargets(cdpUrl);
      return;
    } catch (error) {
      lastError = error.message;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error(`CDP endpoint was not ready within ${waitSeconds}s: ${lastError || "unknown error"}`);
}

async function findTargetById(cdpUrl, targetId) {
  const targets = await fetchTargets(cdpUrl);
  return targets.find((item) => item.type === "page" && item.id === targetId) || null;
}

async function getPageTargetId(page) {
  const cdp = await page.context().newCDPSession(page);
  try {
    const { targetInfo } = await cdp.send("Target.getTargetInfo");
    return targetInfo?.targetId || null;
  } finally {
    await cdp.detach().catch(() => {});
  }
}

async function resolveSessionPage(context, session) {
  if (!session.targetId) throw new Error("Session has no targetId; cannot resolve the working tab.");
  for (const candidate of context.pages()) {
    if ((await getPageTargetId(candidate)) === session.targetId) return candidate;
  }
  throw new Error(`Working tab not found in Chrome CDP session: targetId=${session.targetId}`);
}

function loginState({ body, url, company }) {
  const companyName = String(company || "").trim();
  return {
    hasLogout: body.includes("로그아웃"),
    leftAuth: !url.includes("/auth/"),
    ventureUrl: url.includes("/venturein/"),
    hasPortalMarker: body.includes("My 벤처") || body.includes("확인신청"),
    hasCompanyMarker: !companyName || body.includes(companyName),
  };
}

function loginStateReady(state) {
  return state.hasLogout;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, ""));
}

function writeJsonAscii(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, stringifyPowerShellSafeJson(value, 2), "utf8");
}

function isPhase21ExperimentArtifact(filePath) {
  const name = path.basename(filePath);
  return /^portal_run_.*\.(json|md)$/i.test(name);
}

function companyFromCompanyArtifactPath(filePath) {
  const normalized = path.resolve(filePath);
  const parts = normalized.split(path.sep);
  const companiesIndex = parts.lastIndexOf("companies");
  if (companiesIndex < 0 || !parts[companiesIndex + 1]) {
    throw new Error(`Cannot infer company from artifact path: ${filePath}`);
  }
  return parts[companiesIndex + 1];
}

function unifiedInputPathForCompany(company) {
  return applicationPath(company, "portal_run_state.json");
}

function writeUnifiedInput(company, unified) {
  unified.updated_at = new Date().toISOString();
  writeJsonAscii(unifiedInputPathForCompany(company), unified);
}

function readOperationalState(company) {
  const filePath = unifiedInputPathForCompany(company);
  if (fs.existsSync(filePath)) return readJson(filePath);
  return {
    company,
    execution_state: {
      portal_run: {
        artifacts: {},
        runs: [],
      },
    },
    workflow: {
      pages: {},
    },
  };
}

function mergePlainObject(base, patch) {
  const result = { ...(base || {}) };
  for (const [key, value] of Object.entries(patch || {})) {
    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      result[key] &&
      typeof result[key] === "object" &&
      !Array.isArray(result[key])
    ) {
      result[key] = mergePlainObject(result[key], value);
    } else {
      result[key] = value;
    }
  }
  return result;
}

function updateWorkflowPage(company, pageKey, patch, currentVerifiedStep = null) {
  const unified = readOperationalState(company);
  unified.workflow = unified.workflow || {};
  unified.workflow.pages = unified.workflow.pages || {};
  unified.workflow.pages[pageKey] = mergePlainObject(unified.workflow.pages[pageKey] || {}, sanitizeLog(patch));
  if (currentVerifiedStep) unified.workflow.current_verified_step = currentVerifiedStep;
  writeUnifiedInput(company, unified);
}

function ensurePhase21ExperimentStore(unified) {
  unified.execution_state = unified.execution_state || {};
  unified.execution_state.portal_run = unified.execution_state.portal_run || {};
  unified.execution_state.portal_run.artifacts =
    unified.execution_state.portal_run.artifacts || {};
  unified.execution_state.portal_run.runs =
    unified.execution_state.portal_run.runs || [];
  return unified.execution_state.portal_run;
}

function installUnifiedScreenshotCapture(page, company) {
  if (page.__ventureUnifiedScreenshotCaptureInstalled) return;
  const originalScreenshot = page.screenshot.bind(page);
  page.screenshot = async (options = {}) => {
    const requestedPath = options.path ? String(options.path) : "";
    if (!requestedPath) return await originalScreenshot(options);

    const nextOptions = { ...options };
    delete nextOptions.path;
    const buffer = await originalScreenshot(nextOptions);
    const unified = readOperationalState(company);
    const store = ensurePhase21ExperimentStore(unified);
    store.screenshots = store.screenshots || [];
    store.screenshots.push({
      logical_path: requestedPath.replace(/\\/g, "/"),
      label: path.basename(requestedPath, path.extname(requestedPath)),
      captured_at: new Date().toISOString(),
      mime: "image/png",
      byte_length: buffer.length,
      data_omitted: true,
      omit_reason: "base64 screenshot data is not stored in portal_run_state.json",
    });
    writeUnifiedInput(company, unified);
    return buffer;
  };
  page.__ventureUnifiedScreenshotCaptureInstalled = true;
}

function storeScreenshotBuffer(company, logicalPath, buffer) {
  const unified = readOperationalState(company);
  const store = ensurePhase21ExperimentStore(unified);
  store.screenshots = store.screenshots || [];
  store.screenshots.push({
    logical_path: String(logicalPath).replace(/\\/g, "/"),
    label: path.basename(String(logicalPath), path.extname(String(logicalPath))),
    captured_at: new Date().toISOString(),
    mime: "image/png",
    byte_length: buffer.length,
    data_omitted: true,
    omit_reason: "base64 screenshot data is not stored in portal_run_state.json",
  });
  writeUnifiedInput(company, unified);
}

async function captureScreenshot(page, company, logicalPath, fullPage = false) {
  const buffer = await page.screenshot({ fullPage });
  storeScreenshotBuffer(company, logicalPath, buffer);
  return {
    ref: "portal_run_state.json#execution_state.portal_run.screenshots",
    logicalPath: String(logicalPath).replace(/\\/g, "/"),
  };
}

function writeUnifiedExperimentArtifact(filePath, value) {
  const company = companyFromCompanyArtifactPath(filePath);
  const unified = readOperationalState(company);
  const store = ensurePhase21ExperimentStore(unified);
  const artifactKey = path.basename(filePath).replace(/\.(json|md)$/i, "");
  store.artifacts[artifactKey] = {
    content_type: "json",
    recorded_at: new Date().toISOString(),
    content: sanitizeLog(value),
  };
  writeUnifiedInput(company, unified);
}

function nowFileStamp() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function isNavigationContextError(error) {
  return /Execution context was destroyed|Cannot find context/i.test(error.message || "");
}

function valuesMarkdownPath(company) {
  return path.join(companyRoot(company), "values.md");
}

const TEXT_MARKDOWN_FILES = {
  problem_background: "problem_background.md",
  solution: "solution.md",
  tech_progress: "tech_progress.md",
  tech_plan: "tech_plan.md",
  target_market: "target_market.md",
  competition: "competition.md",
  market_progress: "market_progress.md",
  market_plan: "market_plan.md",
  funding_plan: "funding_plan.md",
  entrepreneurship: "entrepreneurship.md",
  business_plan_summary: "business_plan_summary.md",
};

const VALUES_MD_FIELD_PATHS = {
  company_name: ["values.basic.company_name"],
  business_registration_number: ["values.basic.business_registration_number"],
  established_date: ["values.basic.established_date"],
  industry_name: ["values.basic.industry_name"],
  main_products_or_services: ["values.basic.main_products_or_services"],
  headquarters_address: ["values.basic.headquarters_address"],
  homepage: ["values.basic.homepage"],
  representative_name: ["values.basic.representative_name"],
  representative_table: ["values.basic.representative_table"],
  desired_evaluation_industry: ["values.basic.desired_evaluation_industry"],
  new_industry_field: ["values.basic.new_industry_field"],
  existing_application: ["values.application_type.existing_application"],
  venture_confirmation_history: ["values.application_type.venture_confirmation_history"],
  company_application_status: ["values.application_type.company_application_status"],
  application_type: ["values.application_type.application_type"],
  phone_country: ["values.basic.phone_country"],
  phone_number: ["values.basic.phone_number"],
  fax_number: ["values.basic.fax_number"],
  headquarters_zip: ["values.basic.headquarters_zip"],
  headquarters_base_address: ["values.basic.headquarters_base_address"],
  headquarters_detail_address: ["values.basic.headquarters_detail_address"],
  representative_birth_date: ["values.basic.representative_birth_date"],
  representative_gender: ["values.basic.representative_gender"],
  representative_mobile_phone: ["values.basic.representative_mobile_phone"],
  representative_email: ["values.basic.representative_email"],
  manager_name: ["values.basic.manager_name"],
  manager_position: ["values.basic.manager_position"],
  manager_mobile_phone: ["values.basic.manager_mobile_phone"],
  manager_email: ["values.basic.manager_email"],
  paid_in_capital: ["values.basic.paid_in_capital"],
  fiscal_year_end_month: ["values.basic.fiscal_year_end_month"],
  financial_statement_confirmed: ["values.basic.financial_statement_confirmed"],
  innobiz_confirmation: ["values.certifications.innobiz_confirmation"],
  pre_venture_confirmation: ["values.certifications.pre_venture_confirmation"],
  three_year_employee_count: ["values.basic.three_year_employee_count"],
  corporate_registry_extract: ["values.attachments.corporate_registry_extract"],
  required_submission_documents: ["values.attachments.required_submission_documents"],
  attachment_source_paths: ["attachments.source_paths"],
  ip_ownership_table: ["values.intellectual_property.ip_ownership_table"],
  iso_certifications: ["values.certifications.iso_certifications"],
  technology_keywords: ["values.basic.technology_keywords"],
  product_service_differentiation_choices: ["values.basic.product_service_differentiation_choices"],
  research_development_organization: ["values.basic.research_development_organization"],
  technology_development_personnel_table: ["values.basic.technology_development_personnel_table"],
  current_research_development_cost: ["values.basic.current_research_development_cost"],
  technology_development_achievements: ["values.basic.technology_development_achievements"],
  finance_values: ["values.finance.finance_values"],
  external_collaboration_table: ["values.collaboration.external_collaboration_table"],
  funding_method_choices: ["values.funding.funding_method_choices"],
  growth_stage_radio: ["values.basic.growth_stage_radio"],
  esg_self_check_choices: ["values.esg.esg_self_check_choices"],
  problem_background: ["texts.problem_background"],
  solution: ["texts.solution"],
  tech_progress: ["texts.tech_progress"],
  tech_plan: ["texts.tech_plan"],
  target_market: ["texts.target_market"],
  competition: ["texts.competition"],
  market_progress: ["texts.market_progress"],
  market_plan: ["texts.market_plan"],
  funding_plan: ["texts.funding_plan"],
  entrepreneurship: ["texts.entrepreneurship"],
  tech_name: ["values.basic.tech_name"],
  business_plan_summary: ["texts.business_plan_summary"],
};

function parseYamlScalar(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  return text.replace(/^['"]|['"]$/g, "");
}

function parseIndentedYamlValue(lines) {
  const meaningful = lines.filter((line) => line.trim() !== "");
  if (meaningful.length === 0) return "";
  if (meaningful.every((line) => /^\s*-\s*/.test(line))) {
    return meaningful.map((line) => parseYamlScalar(line.replace(/^\s*-\s*/, "")));
  }
  if (meaningful[0] && /^\s*-\s*/.test(meaningful[0])) {
    const items = [];
    let current = null;
    for (const line of meaningful) {
      const listMatch = line.match(/^\s*-\s*(.*)$/);
      if (listMatch) {
        if (current) items.push(current);
        const first = listMatch[1];
        const pair = first.match(/^([A-Za-z0-9_.-]+):\s*(.*)$/);
        current = pair ? { [pair[1]]: parseYamlScalar(pair[2]) } : parseYamlScalar(first);
        continue;
      }
      const pair = line.match(/^\s+([A-Za-z0-9_.-]+):\s*(.*)$/);
      if (pair && current && typeof current === "object") current[pair[1]] = parseYamlScalar(pair[2]);
    }
    if (current) items.push(current);
    return items;
  }
  const objectValue = {};
  for (const line of meaningful) {
    const pair = line.match(/^\s+([A-Za-z0-9_.-]+):\s*(.*)$/);
    if (pair) objectValue[pair[1]] = parseYamlScalar(pair[2]);
  }
  return Object.keys(objectValue).length > 0 ? objectValue : meaningful.map((line) => line.trim()).join("\n");
}

function parseValuesYamlBlock(block) {
  const result = {};
  const lines = String(block || "").replace(/\r/g, "").split("\n");
  let currentKey = null;
  let currentInline = "";
  let currentLines = [];

  const flush = () => {
    if (!currentKey) return;
    result[currentKey] = currentInline ? parseYamlScalar(currentInline) : parseIndentedYamlValue(currentLines);
  };

  for (const line of lines) {
    const match = line.match(/^([A-Za-z0-9_.-]+):\s*(.*)$/);
    if (match) {
      flush();
      currentKey = match[1];
      currentInline = match[2] || "";
      currentLines = [];
    } else if (currentKey) {
      currentLines.push(line);
    }
  }
  flush();
  return result;
}

function setValueAtPath(root, dottedPath, value) {
  const parts = String(dottedPath || "").split(".").filter(Boolean);
  let current = root;
  for (let i = 0; i < parts.length - 1; i += 1) {
    const part = parts[i];
    current[part] = current[part] || {};
    current = current[part];
  }
  current[parts[parts.length - 1]] = value;
}

function parseValuesMarkdown(text) {
  const fields = {};
  const pattern = /^###\s+([A-Za-z0-9_.-]+)\s*\r?\n+```yaml\s*\r?\n([\s\S]*?)\r?\n```/gm;
  let match = null;
  while ((match = pattern.exec(text))) {
    const fieldId = match[1].trim();
    fields[fieldId] = {
      label: fieldId,
      value: "",
      status: "needs_confirmation",
      source: [],
      notes: [],
      ...parseValuesYamlBlock(match[2]),
    };
  }
  return fields;
}

function valuesMarkdownToPortalInput(text) {
  const parsedFields = parseValuesMarkdown(text);
  const portalInput = {
    __sourceFormat: "values_md",
    values: {
      basic: {},
      application_type: {},
      finance: {},
      intellectual_property: {},
      certifications: {},
      collaboration: {},
      funding: {},
      esg: {},
    },
    texts: {},
    attachments: {},
  };

  for (const [fieldId, item] of Object.entries(parsedFields)) {
    const paths = VALUES_MD_FIELD_PATHS[fieldId];
    if (!paths) throw new Error(`values.md 매핑이 없는 필드입니다: ${fieldId}`);
    for (const targetPath of paths) setValueAtPath(portalInput, targetPath, item);
  }
  return portalInput;
}

function readValuesMarkdownAsPortalInput(filePath) {
  return valuesMarkdownToPortalInput(fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, ""));
}

function splitMarkdownArtifact(text) {
  const clean = String(text || "").replace(/^\uFEFF/, "");
  let meta = {};
  let body = clean;
  if (clean.startsWith("---")) {
    const end = clean.indexOf("\n---", 3);
    if (end >= 0) {
      meta = parseValuesYamlBlock(clean.slice(3, end));
      body = clean.slice(end + 4);
    }
  }
  body = body
    .replace(/^\s+/, "")
    .replace(/^#\s+.*(?:\r?\n)+/, "")
    .trim();
  return { meta, body };
}

function attachTextMarkdownArtifacts(company, portalInput) {
  const textsDir = path.join(companyRoot(company), "texts");
  portalInput.texts = portalInput.texts || {};
  for (const [fieldId, fileName] of Object.entries(TEXT_MARKDOWN_FILES)) {
    const filePath = path.join(textsDir, fileName);
    if (!fs.existsSync(filePath)) continue;
    const { meta, body } = splitMarkdownArtifact(fs.readFileSync(filePath, "utf8"));
    portalInput.texts[fieldId] = {
      label: fieldId,
      value: body.replace(/\r\n/g, "\n"),
      status: meta.status || (body ? "ready" : "missing"),
      char_count: meta.char_count || String(body.length),
      source: meta.source || [`texts/${fileName}`],
      notes: meta.notes || [],
    };
  }
  return portalInput;
}

function loadPortalInputForCompany(company, args) {
  const mdPath = valuesMarkdownPath(company);
  if (!fs.existsSync(mdPath)) {
    throw new Error(`companies/${company}/values.md 파일이 없습니다.`);
  }
  const portalInput = attachTextMarkdownArtifacts(company, readValuesMarkdownAsPortalInput(mdPath));
  return { portalInputFile: `${mdPath} + texts/*.md`, portalInput };
}

function unifiedRefForLegacyPath(value) {
  const text = String(value || "");
  const logicalPath = text.replace(/\\/g, "/");
  const fileName = logicalPath.split("/").pop() || "";
  if (/\/screenshots\/portal-run\/.+\.png$/i.test(logicalPath)) {
    return {
      ref: "portal_run_state.json#execution_state.portal_run.screenshots",
      logicalPath,
    };
  }
  if (/^portal_run_.*\.(json|md)$/i.test(fileName)) {
    const artifactKey = fileName.replace(/\.(json|md)$/i, "");
    return {
      ref: `portal_run_state.json#execution_state.portal_run.artifacts.${artifactKey}`,
      logicalPath,
    };
  }
  return null;
}

function sanitizeLog(value) {
  if (Array.isArray(value)) return value.map(sanitizeLog);
  if (typeof value === "string") return unifiedRefForLegacyPath(value) || value;
  if (!value || typeof value !== "object") return value;
  const result = {};
  for (const [key, child] of Object.entries(value)) {
    if (/pw|password|smesPw|secret|token/i.test(key)) {
      result[key] = child ? "[redacted]" : child;
    } else {
      result[key] = sanitizeLog(child);
    }
  }
  return result;
}

function createRun(company, args) {
  const run = {
    company,
    script: "scripts/web.js",
    mode: args.step || "login",
    debugPort: Number(args["debug-port"] || DEFAULT_DEBUG_PORT),
    startedAt: new Date().toISOString(),
    status: "running",
    principles: [
      "기존 운영 스크립트는 수정하지 않고 실험용 스크립트에만 절차를 기록한다.",
      "로그인은 web.js 내부 메서드로 처리하며 별도 로그인 스크립트를 호출하지 않는다.",
      "자격증명 값은 로그와 stdout에 출력하지 않는다.",
      "브라우저는 자동화 전용 Chrome 세션으로 열고, 열린 탭은 전체화면 상태로 맞춘다.",
      "성공한 과정과 실패한 검증을 모두 회사별 application 로그에 누적 기록한다.",
      "임시저장 버튼이 있는 화면에서는 임시저장만 클릭하고 저장 후 다음단계로 이동 버튼은 클릭하지 않는다.",
    ],
    steps: [],
  };
  return run;
}

function addStep(run, name, status, details = {}) {
  run.steps.push({
    index: run.steps.length + 1,
    name,
    status,
    at: new Date().toISOString(),
    details: sanitizeLog(details),
  });
}

const APPLICATION_FORM_INPUT_FIELDS = [
  {
    key: "company_name",
    label: "기업명",
    sourcePath: "values.basic.company_name",
    selector: 'input[name="cmpNm"]',
    inputMethod: "screen_keyboard_replace",
    required: true,
  },
  {
    key: "opening_date",
    label: "설립일",
    sourcePath: "values.basic.established_date",
    selector: 'input[name="_fndnYmd"]',
    inputMethod: "screen_keyboard_replace",
    required: true,
  },
  {
    key: "legal_conversion_history",
    label: "개인 -> 법인 전환 이력 기업",
    sourcePath: "values.basic.legal_conversion_history",
    selector: "#indvCrprSwtcHstYn",
    inputMethod: "checkbox_toggle",
    transform: "yes_no_code",
    required: false,
  },
  {
    key: "phone_country_code",
    label: "전화번호 국가번호",
    sourcePath: "values.basic.phone_country",
    selector: "#cmpIntlTelCrNo",
    inputMethod: "screen_keyboard_replace",
    transform: "phone_country_code",
    required: true,
  },
  {
    key: "phone_number",
    label: "전화번호",
    sourcePath: "values.basic.phone_number",
    selector: 'input[name="hdofcTelno"]',
    inputMethod: "screen_keyboard_replace",
    transform: "phone_local_without_area_code",
    required: true,
  },
  {
    key: "fax_number",
    label: "팩스번호",
    sourcePath: "values.basic.fax_number",
    selector: 'input[name="hdofcFaxNo"]',
    inputMethod: "screen_keyboard_replace",
    transform: "digits_only",
    required: false,
  },
  {
    key: "headquarters_address_lookup",
    label: "본사주소 우편번호/기본주소",
    sourcePath: "values.basic.headquarters_address",
    selector: "#hdofcJusoBtn",
    targetSelectors: ['input[name="hdofcZip"]', 'input[name="hdofcBaseAddr"]'],
    inputMethod: "address_search_popup_required",
    required: true,
  },
  {
    key: "headquarters_detail_address",
    label: "본사주소 상세주소",
    sourcePath: "values.basic.headquarters_address",
    selector: 'input[name="hdofcDtlAddr"]',
    inputMethod: "screen_keyboard_replace",
    transform: "headquarters_detail_address",
    required: true,
  },
  {
    key: "site_inspection_address_choice",
    label: "현장실제조사 주소 지정",
    sourcePath: "values.basic.site_inspection_address",
    selector: "#aplyRprsAddrDvsnCd_H",
    inputMethod: "radio_click",
    transform: "site_address_code",
    options: [{ value: "H", label: "본사주소", selector: "#aplyRprsAddrDvsnCd_H" }],
    required: false,
  },
  {
    key: "homepage",
    label: "홈페이지",
    sourcePath: "values.basic.homepage",
    selector: 'input[name="cmpHmpgUrl"]',
    inputMethod: "screen_keyboard_replace",
    required: true,
  },
  {
    key: "representative_name",
    label: "대표자명",
    sourcePath: "values.basic.representative_name",
    selector: 'input[name="rprsvNm"]',
    inputMethod: "screen_keyboard_replace",
    required: true,
  },
  {
    key: "representative_birth_date",
    label: "대표자 생년월일",
    sourcePath: "values.basic.representative_birth_date",
    selector: 'input[name="_brdt"]',
    inputMethod: "screen_keyboard_replace",
    required: true,
  },
  {
    key: "representative_gender",
    label: "대표자 성별",
    sourcePath: "values.basic.representative_gender",
    selector: "",
    inputMethod: "radio_click",
    transform: "gender_code",
    options: [
      { value: "M", label: "남", selector: "#rprsvGndrCd_M" },
      { value: "F", label: "여", selector: "#rprsvGndrCd_F" },
    ],
    required: true,
  },
  {
    key: "representative_mobile",
    label: "대표자 휴대전화",
    sourcePath: "values.basic.representative_mobile_phone",
    selector: 'input[name="encptRprsvMblTelno"]',
    inputMethod: "screen_keyboard_replace",
    transform: "digits_only",
    required: true,
  },
  {
    key: "representative_email",
    label: "대표자 이메일",
    sourcePath: "values.basic.representative_email",
    selector: 'input[name="rprsvEmlAddr"]',
    inputMethod: "screen_keyboard_replace",
    required: true,
  },
  {
    key: "manager_name",
    label: "담당자명",
    sourcePath: "values.basic.manager_name",
    selector: 'input[name="cmpChrgrNm"]',
    inputMethod: "identity_verification_required_manual_only",
    required: true,
  },
  {
    key: "manager_position",
    label: "담당자 직위",
    sourcePath: "values.basic.manager_position",
    selector: 'input[name="cmpChrgrPstnNm"]',
    inputMethod: "identity_verification_required_manual_only",
    required: true,
  },
  {
    key: "manager_mobile",
    label: "담당자 휴대전화",
    sourcePath: "values.basic.manager_mobile_phone",
    selector: 'input[name="encptCmpChrgrMblTelno"]',
    inputMethod: "identity_verification_required_manual_only",
    transform: "digits_only",
    required: true,
  },
  {
    key: "manager_email",
    label: "담당자 이메일",
    sourcePath: "values.basic.manager_email",
    selector: 'input[name="cmpChrgrEmlAddr"]',
    inputMethod: "identity_verification_required_manual_only",
    required: true,
  },
  {
    key: "paid_in_capital",
    label: "납입자본금",
    sourcePath: "values.basic.paid_in_capital",
    selector: 'input[name="cmpPmntCptlAmt"]',
    inputMethod: "screen_keyboard_replace",
    transform: "digits_only",
    required: true,
  },
  {
    key: "innobiz_confirmation",
    label: "6개월 이내 이노비즈기업 확인여부",
    sourcePath: "values.certifications.innobiz_confirmation",
    selector: "",
    inputMethod: "radio_click",
    transform: "yes_no_code",
    options: [
      { value: "Y", label: "예", selector: "#inbizCertYn_Y" },
      { value: "N", label: "아니오", selector: "#inbizCertYn_N" },
    ],
    required: true,
  },
  {
    key: "innobiz_validity_start_date",
    label: "이노비즈 확인서 유효기간 시작일자",
    sourcePath: "values.certifications.innobiz_validity_start_date",
    selector: 'input[name="inbizCnfmtIssuYmd"]',
    inputMethod: "screen_keyboard_replace",
    transform: "date_digits",
    required: false,
    enabledWhen: {
      sourcePath: "values.certifications.innobiz_confirmation",
      transform: "yes_no_code",
      equals: "Y",
    },
  },
  {
    key: "innobiz_issue_number",
    label: "이노비즈 확인서 발급번호",
    sourcePath: "values.certifications.innobiz_issue_number",
    selector: 'input[name="inbizCnfmtIssuNo"]',
    inputMethod: "screen_keyboard_replace",
    required: false,
    enabledWhen: {
      sourcePath: "values.certifications.innobiz_confirmation",
      transform: "yes_no_code",
      equals: "Y",
    },
  },
  {
    key: "pre_venture_confirmation",
    label: "예비벤처기업 확인여부",
    sourcePath: "values.certifications.pre_venture_confirmation",
    selector: "",
    inputMethod: "radio_click",
    transform: "yes_no_code",
    options: [
      { value: "Y", label: "예", selector: "#rsrvVntrCnfmtYn_Y" },
      { value: "N", label: "아니오", selector: "#rsrvVntrCnfmtYn_N" },
    ],
    required: true,
  },
  {
    key: "pre_venture_issue_date",
    label: "예비벤처기업 확인서 발급일자",
    sourcePath: "values.certifications.pre_venture_issue_date",
    selector: 'input[name="rsrvVntrCnfmtIssuYmd"]',
    inputMethod: "screen_keyboard_replace",
    transform: "date_digits",
    required: false,
    enabledWhen: {
      sourcePath: "values.certifications.pre_venture_confirmation",
      transform: "yes_no_code",
      equals: "Y",
    },
  },
  {
    key: "pre_venture_issue_number",
    label: "예비벤처기업 확인서 발급번호",
    sourcePath: "values.certifications.pre_venture_issue_number",
    selector: 'input[name="rsrvVntrCnfmtIssuNo"]',
    inputMethod: "screen_keyboard_replace",
    required: false,
    enabledWhen: {
      sourcePath: "values.certifications.pre_venture_confirmation",
      transform: "yes_no_code",
      equals: "Y",
    },
  },
];

const APPLICATION_FORM_CONFIRM_ACTIONS = [
  {
    key: "confirm_company_name",
    fieldKey: "company_name",
    label: "기업명 확인",
    selector: 'a[onclick="clickChkBtn(\'cmpNm\');"]',
  },
  {
    key: "confirm_opening_date",
    fieldKey: "opening_date",
    label: "설립일 확인",
    selector: 'a[onclick="clickChkBtn(\'_fndnYmd\');"]',
  },
  {
    key: "confirm_headquarters_detail_address",
    fieldKey: "headquarters_detail_address",
    label: "사업자등록증 주소지와 일치 여부 확인",
    selector: 'a[onclick="clickChkBtn(\'hdofcDtlAddr\');"]',
  },
];

const COMPANY_INFO_FIELD_GROUPS = [
  {
    sectionKey: "evaluation_industry",
    sectionLabel: "평가희망업종 / 신산업분야",
    fields: [
      {
        key: "desired_evaluation_industry",
        label: "평가희망업종",
        sourcePath: "values.basic.desired_evaluation_industry",
        selector: "#hopeIndstyLclsCd",
        inputMethod: "select_by_label_or_value",
        required: true,
      },
      {
        key: "new_industry_field",
        label: "신산업분야",
        sourcePath: "values.basic.new_industry_field",
        inputMethod: "radio_click",
        options: [
          { value: "Y", selector: "#nwtcSphrChkY" },
          { value: "N", selector: "#nwtcSphrChkN" },
        ],
        required: true,
      },
    ],
  },
  {
    sectionKey: "technology_roadmap",
    sectionLabel: "중소기업 기술로드맵 해당 여부 / 전략분야",
    fields: [
      {
        key: "sme_technology_roadmap_related",
        label: "중소기업 기술로드맵 해당 여부",
        sourcePath: "values.basic.sme_technology_roadmap_related",
        inputMethod: "radio_click",
        options: [
          { value: "Y", selector: "#cfY01" },
          { value: "N", selector: "#cfN01" },
        ],
        required: true,
      },
      {
        key: "strategy_field_three_choices",
        label: "전략분야 3단계 선택",
        sourcePath: "values.basic.strategy_field_three_choices",
        selectors: ["#mapLclsCd", "#mapMclsCd", "#mapSclsCd"],
        inputMethod: "cascading_selects",
        required: false,
        enabledWhen: {
          sourcePath: "values.basic.sme_technology_roadmap_related",
          transform: "yes_no_code",
          equals: "Y",
        },
      },
    ],
  },
  {
    sectionKey: "employee_count",
    sectionLabel: "3개년 피보험자 수",
    fields: [
      {
        key: "three_year_employee_count",
        label: "3개년 피보험자 수",
        sourcePath: "values.basic.three_year_employee_count",
        selectors: ['input[name="bbbfrYrEmplCnt"]', 'input[name="bbfrYrEmplCnt"]', 'input[name="bfrYrEmplCnt"]'],
        inputMethod: "three_text_inputs",
        required: true,
      },
    ],
  },
  {
    sectionKey: "company_history",
    sectionLabel: "주요 연혁",
    fields: [
      {
        key: "company_history",
        label: "기업연혁 년월, 내용",
        sourcePath: "values.basic.company_history",
        addButtonSelector: "button.addNextTbRow",
        rowSelectors: {
          month: 'input[name="cmpHstyList[{index}].hstyYm"]',
          content: 'input[name="cmpHstyList[{index}].hstyPrmyCn"]',
        },
        inputMethod: "dynamic_rows_keyboard_replace",
        required: false,
      },
    ],
  },
];

function valueAtPath(root, dottedPath) {
  return String(dottedPath || "")
    .split(".")
    .filter(Boolean)
    .reduce((current, part) => (current && Object.prototype.hasOwnProperty.call(current, part) ? current[part] : undefined), root);
}

function sourceItemForField(root, field) {
  return { item: valueAtPath(root, field.sourcePath), sourcePath: field.sourcePath };
}

function canUseSourceItemForInput(item) {
  const status = item && item.status ? String(item.status).trim() : "";
  if (!status) return true;
  return !["needs_confirmation", "candidate", "not_applicable", "blocked", "missing"].includes(status);
}

function rawPortalValue(item) {
  if (!item || item.value === null || item.value === undefined) return "";
  if (typeof item.value === "string") return item.value.trim();
  return JSON.stringify(item.value);
}

function digitsOnly(value) {
  return String(value || "").replace(/\D/g, "");
}

function normalizeYesNo(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return "";
  if (["y", "yes", "true", "1", "예", "있음", "해당", "해당함"].includes(text)) return "Y";
  if (["n", "no", "false", "0", "아니오", "없음", "미해당", "해당없음"].includes(text)) return "N";
  return text.toUpperCase();
}

function normalizeGender(value) {
  const text = String(value || "").trim().toLowerCase();
  if (!text) return "";
  if (["m", "male", "남", "남자", "남성"].includes(text)) return "M";
  if (["f", "female", "여", "여자", "여성"].includes(text)) return "F";
  return text.toUpperCase();
}

function splitHeadquartersAddress(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return { searchText: "", detailAddress: "" };
  const parts = text.split(",").map((part) => part.trim()).filter(Boolean);
  if (parts.length >= 2) {
    return { searchText: parts[0], detailAddress: parts.slice(1).join(" ") };
  }
  const match = text.match(/^(.*?(?:로|길)\s*\d+(?:-\d+)?)(.*)$/);
  if (match) {
    return { searchText: match[1].trim(), detailAddress: match[2].trim().replace(/^,?\s*/, "") };
  }
  return { searchText: text, detailAddress: "" };
}

function prepareApplicationInputValue(rawValue, transform) {
  if (!rawValue) return "";
  if (transform === "yes_no_code") return normalizeYesNo(rawValue);
  if (transform === "gender_code") return normalizeGender(rawValue);
  if (transform === "site_address_code") {
    const text = String(rawValue || "").trim().toLowerCase();
    if (["h", "본사", "본사주소", "headquarters", "head_office"].includes(text)) return "H";
    return text.toUpperCase();
  }
  if (transform === "phone_country_code") return "+82";
  if (transform === "digits_only") return digitsOnly(rawValue);
  if (transform === "date_digits") return digitsOnly(rawValue);
  if (transform === "phone_local_without_area_code") {
    const digits = digitsOnly(rawValue);
    if (digits.startsWith("02") && digits.length > 2) return digits.slice(2);
    return digits;
  }
  if (transform === "headquarters_detail_address") {
    return splitHeadquartersAddress(rawValue).detailAddress;
  }
  return String(rawValue).trim();
}

function buildApplicationFormInputPlan(portalInput, portalInputFile) {
  const fields = APPLICATION_FORM_INPUT_FIELDS.map((field) => {
    const { item, sourcePath } = sourceItemForField(portalInput, field);
    const rawValue = rawPortalValue(item);
    const preparedValue =
      field.inputMethod === "address_search_popup_required"
        ? splitHeadquartersAddress(rawValue).searchText
        : prepareApplicationInputValue(rawValue, field.transform);
    const selectedOption = (field.options || []).find((option) => option.value === preparedValue) || null;
    const enabledWhen = field.enabledWhen
      ? {
          ...field.enabledWhen,
          actualValue: prepareApplicationInputValue(
            rawPortalValue(valueAtPath(portalInput, field.enabledWhen.sourcePath)),
            field.enabledWhen.transform,
          ),
        }
      : null;
    const enabledBySource = !enabledWhen || enabledWhen.actualValue === enabledWhen.equals;
    const source = item && Array.isArray(item.source) ? item.source : [];
    return {
      key: field.key,
      label: field.label,
      required: field.required,
      sourceFile: portalInputFile,
      sourcePath,
      sourceStatus: item ? item.status || "" : "missing",
      sourceLabel: item ? item.label || "" : "",
      source,
      selector: selectedOption ? selectedOption.selector : field.selector,
      options: field.options || [],
      selectedOption,
      enabledWhen,
      enabledBySource,
      targetSelectors: field.targetSelectors || [],
      inputMethod: field.inputMethod,
      transform: field.transform || "",
      rawValueLength: rawValue.length,
      preparedValue,
      preparedValueLength: preparedValue.length,
      canInputFromPreparedValue:
        Boolean(preparedValue) &&
        Boolean(selectedOption || field.selector) &&
        enabledBySource &&
        canUseSourceItemForInput(item),
    };
  });
  return {
    page: "application_form",
    assumption: "아무 값도 없는 신규 신청서 화면에서 values.md와 texts/*.md 값을 기준으로 직접 입력한다.",
    inputSequence: fields,
    confirmActions: APPLICATION_FORM_CONFIRM_ACTIONS,
    missingRequired: fields.filter((field) => field.required && !field.canInputFromPreparedValue),
    unsupportedMethods: fields.filter((field) => field.inputMethod === "address_search_popup_required"),
  };
}

function prepareCompanyInfoValue(rawValue, transform) {
  if (transform === "yes_no_code") return normalizeYesNo(rawValue);
  return rawValue;
}

function buildCompanyInfoInputPlan(portalInput, portalInputFile) {
  const sections = COMPANY_INFO_FIELD_GROUPS.map((section) => {
    const fields = section.fields.map((field) => {
      const { item, sourcePath } = sourceItemForField(portalInput, field);
      const rawValue = item && Object.prototype.hasOwnProperty.call(item, "value") ? item.value : null;
      const enabledWhen = field.enabledWhen
        ? {
            ...field.enabledWhen,
            actualValue: prepareCompanyInfoValue(
              rawPortalValue(valueAtPath(portalInput, field.enabledWhen.sourcePath)),
              field.enabledWhen.transform,
            ),
          }
        : null;
      const enabledBySource = !enabledWhen || enabledWhen.actualValue === enabledWhen.equals;
      const preparedValue =
        field.inputMethod === "radio_click"
          ? normalizeYesNo(rawValue)
          : field.inputMethod === "dynamic_rows_keyboard_replace"
            ? Array.isArray(rawValue)
              ? rawValue
              : []
            : rawValue;
      const selectedOption = (field.options || []).find((option) => option.value === preparedValue) || null;
      const hasPreparedValue = Array.isArray(preparedValue)
        ? preparedValue.length > 0
        : preparedValue !== null && preparedValue !== undefined && String(preparedValue).trim() !== "";
      return {
        ...field,
        sourceFile: portalInputFile,
        sourcePath,
        sourceStatus: item ? item.status || "" : "missing",
        sourceLabel: item ? item.label || "" : "",
        source: item && Array.isArray(item.source) ? item.source : [],
        preparedValue,
        selectedOption,
        selector: selectedOption ? selectedOption.selector : field.selector,
        enabledWhen,
        enabledBySource,
        canInputFromPreparedValue: Boolean(hasPreparedValue && enabledBySource && canUseSourceItemForInput(item)),
      };
    });
    return {
      ...section,
      fields,
    };
  });
  const fields = sections.flatMap((section) => section.fields.map((field) => ({ ...field, sectionKey: section.sectionKey })));
  return {
    page: "company_info",
    assumption: "기업정보 화면은 values.md에서 값이 준비된 항목만 입력한다.",
    sections,
    fields,
    missingRequired: fields.filter((field) => field.required && !field.canInputFromPreparedValue),
    readyForPreparedInput: fields.filter((field) => field.canInputFromPreparedValue),
  };
}

function persistRun(company, run) {
  const unified = readOperationalState(company);
  const store = ensurePhase21ExperimentStore(unified);
  store.runs.push(sanitizeLog(run));
  if (run.status === "completed") {
    store.latest_completed_step = run.mode;
    store.latest_completed_script = run.script;
    store.latest_completed_at = run.finishedAt || new Date().toISOString();
  }
  store.markdown_log = renderMarkdown({ company, runs: store.runs });
  store.updated_at = new Date().toISOString();
  writeUnifiedInput(company, unified);
  return {
    jsonFile: unifiedInputPathForCompany(company),
    mdFile: `${unifiedInputPathForCompany(company)}#execution_state.portal_run.markdown_log`,
  };
}

function renderMarkdown(log) {
  const lines = [`# 포털 입력 실행 로그`, "", `회사명: ${log.company}`, ""];
  for (const run of log.runs || []) {
    lines.push(`## ${run.startedAt} - ${run.mode}`);
    lines.push(`- 상태: ${run.status}`);
    lines.push(`- 디버그 포트: ${run.debugPort}`);
    if (run.finishedAt) lines.push(`- 종료: ${run.finishedAt}`);
    lines.push("");
    lines.push("### 원칙");
    for (const item of run.principles || []) lines.push(`- ${item}`);
    lines.push("");
    lines.push("### 단계");
    for (const step of run.steps || []) {
      lines.push(`${step.index}. ${step.name}: ${step.status}`);
      const detailText = JSON.stringify(step.details || {}, null, 2);
      lines.push("```json");
      lines.push(detailText);
      lines.push("```");
    }
    lines.push("");
  }
  return `${lines.join("\n")}\n`;
}

async function makeFullscreen(session, run) {
  const browser = await chromium.connectOverCDP(session.cdpUrl);
  try {
    const context = browser.contexts()[0] || await browser.newContext({ viewport: null });
    const page = await resolveSessionPage(context, session);
    await page.bringToFront();
    const cdp = await page.context().newCDPSession(page);
    try {
      const { windowId } = await cdp.send("Browser.getWindowForTarget");
      await cdp.send("Browser.setWindowBounds", {
        windowId,
        bounds: { windowState: "fullscreen" },
      });
      await page.waitForTimeout(500);
      const viewport = await page.evaluate(() => ({
        url: location.href,
        title: document.title,
        innerWidth,
        innerHeight,
        screenWidth: screen.width,
        screenHeight: screen.height,
      }));
      addStep(run, "브라우저 탭 전체화면 전환", "completed", {
        cdpUrl: session.cdpUrl,
        targetId: session.targetId,
        windowState: "fullscreen",
        viewport,
      });
    } finally {
      await cdp.detach().catch(() => {});
    }
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function connectSessionPage(session, company) {
  const browser = await chromium.connectOverCDP(session.cdpUrl);
  const context = browser.contexts()[0] || await browser.newContext({ viewport: null });
  const page = await resolveSessionPage(context, session);
  await page.bringToFront();
  installUnifiedScreenshotCapture(page, company);
  return { browser, page };
}

async function createSmesLoginSession(company, config, args, run) {
  const debugPort = Number(args["debug-port"] || DEFAULT_DEBUG_PORT);
  const waitSeconds = Number(args["wait-seconds"] || DEFAULT_WAIT_SECONDS);
  const cdpUrl = `http://127.0.0.1:${debugPort}`;
  const sessionFile = sessionPath(company);
  if (fs.existsSync(sessionFile)) fs.unlinkSync(sessionFile);

  const userDataDir = automationChromeProfileDir(company, debugPort);
  fs.mkdirSync(userDataDir, { recursive: true });
  writeChromePasswordManagerPrefs(userDataDir);

  const chromeArgs = [
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${userDataDir}`,
    "--start-maximized",
    "--disable-blink-features=AutomationControlled",
    "--disable-features=AutofillServerCommunication,PasswordManagerOnboarding,PasswordLeakDetection",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank",
  ];
  const chromeProcess = childProcess.spawn(chromePath(), chromeArgs, {
    detached: true,
    stdio: "ignore",
    windowsHide: false,
  });
  chromeProcess.unref();
  addStep(run, "Chrome 로그인 세션 실행", "completed", {
    cdpUrl,
    debugPort,
    chromeUserDataDir: userDataDir,
    browserPid: chromeProcess.pid || null,
  });

  await waitForCdp(cdpUrl, 20);
  const browser = await chromium.connectOverCDP(cdpUrl);
  const context = browser.contexts()[0] || await browser.newContext({ viewport: null });
  const page =
    context.pages().find((candidate) => /smes\.go\.kr\/venturein/i.test(candidate.url())) ||
    (await context.newPage());
  page.setDefaultTimeout(20000);
  page.on("dialog", async (dialog) => {
    addStep(run, "로그인 중 브라우저 dialog 처리", "completed", { message: dialog.message() });
    await dialog.accept().catch(() => {});
  });

  await page.goto(`${new URL(config.smesUrl).origin}/venturein/auth/viewLogin`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  const fieldState = await page.evaluate(() => ({
    idLength: document.querySelector("#id")?.value.length || 0,
    pwLength: document.querySelector("#password")?.value.length || 0,
    hasIdField: Boolean(document.querySelector("#id")),
    hasPwField: Boolean(document.querySelector("#password")),
    hasLogout: (document.body?.innerText || "").includes("로그아웃"),
    actionLogin: typeof window.actionLogin,
  }));
  if (fieldState.hasIdField && fieldState.hasPwField) {
    await page.evaluate(
      ({ smesId, smesPw }) => {
        const id = document.querySelector("#id");
        const pw = document.querySelector("#password");
        for (const [el, value] of [
          [id, smesId],
          [pw, smesPw],
        ]) {
          el.focus();
          el.value = value;
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
          el.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
          el.blur();
        }
      },
      { smesId: config.smesId, smesPw: config.smesPw },
    );
    const preparedFieldState = await page.evaluate(() => ({
      idLength: document.querySelector("#id")?.value.length || 0,
      pwLength: document.querySelector("#password")?.value.length || 0,
      actionLogin: typeof window.actionLogin,
    }));
    addStep(run, "로그인 입력 필드 준비", "completed", {
      idLength: preparedFieldState.idLength,
      pwLength: preparedFieldState.pwLength ? "[redacted-length]" : 0,
      actionLogin: preparedFieldState.actionLogin,
    });

    await page.evaluate(() => {
      if (typeof window.actionLogin === "function") window.actionLogin();
      else document.querySelector("button.common_btn.submit")?.click();
    });
  } else if (fieldState.hasLogout) {
    addStep(run, "이미 로그인된 세션 확인", "completed", {
      url: page.url(),
      title: await page.title(),
    });
  } else {
    throw new Error("login fields not found");
  }
  await page.waitForFunction(
    ({ company }) => {
      const body = (document.body?.innerText || "").replace(/\s+/g, " ");
      const url = location.href;
      return (
        body.includes("로그아웃") &&
        !url.includes("/auth/") &&
        url.includes("/venturein/") &&
        (body.includes("My 벤처") || body.includes("확인신청")) &&
        (!company || body.includes(company))
      );
    },
    { company: String(company || "").trim() },
    { timeout: waitSeconds * 1000 },
  ).catch(() => {});

  const body = (await page.locator("body").innerText()).replace(/\s+/g, " ");
  const state = loginState({ body, url: page.url(), company });
  const success = loginStateReady(state);
  addStep(run, "로그인 성공 판정", success ? "completed" : "failed", {
    loginState: state,
    url: page.url(),
    title: await page.title(),
    successMarker: "로그아웃",
    bodyHead: body.slice(0, 240),
  });
  if (!success) {
    throw new Error("SMES login failed: ready markers not found");
  }

  const targetId = await getPageTargetId(page);
  const target = targetId ? await findTargetById(cdpUrl, targetId) : null;
  if (!target?.id) {
    throw new Error("SMES login succeeded, but CDP targetId was not found");
  }

  const session = {
    schemaVersion: 2,
    status: "ready",
    company,
    sessionName: company,
    cdpUrl,
    debugPort,
    targetId: target.id,
    webSocketDebuggerUrl: target.webSocketDebuggerUrl || null,
    targetMatch: true,
    jsonListUrl: `${cdpUrl}/json/list`,
    browserPid: chromeProcess.pid || null,
    workerPid: process.pid,
    url: page.url(),
    title: await page.title(),
    successMarker: "로그아웃",
    chromeUserDataDir: userDataDir,
    sessionFileEncoding: "utf8-ascii-escaped",
    createdAt: new Date().toISOString(),
  };
  fs.writeFileSync(sessionFile, `${stringifyPowerShellSafeJson(session)}\n`, "utf8");
  return session;
}

async function inspectHomeScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  try {
    await page.waitForTimeout(1000);
    const dir = experimentScreenshotDir(company);
    ensureDir(dir);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-home-after-login.png`);
    await captureScreenshot(page, company, screenshotFile, false);

    const screen = await page.evaluate(() => {
      const textOf = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
      };
      const selectorOf = (el) => {
        if (el.id) return `#${el.id}`;
        const className = String(el.className || "").trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".");
        return `${el.tagName.toLowerCase()}${className ? `.${className}` : ""}`;
      };
      const controls = Array.from(document.querySelectorAll("button, a, input, textarea, select"))
        .filter(visible)
        .map((el, index) => ({
          index,
          selector: selectorOf(el),
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          text: textOf(el).slice(0, 120),
          placeholder: el.getAttribute("placeholder") || "",
          box: boxOf(el),
        }))
        .filter((item) => item.box.width > 5 && item.box.height > 5);
      const overlays = Array.from(document.querySelectorAll("body *"))
        .filter(visible)
        .map((el, index) => {
          const style = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          const zIndex = Number.parseInt(style.zIndex, 10);
          const text = textOf(el);
          return {
            index,
            selector: selectorOf(el),
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute("role") || "",
            ariaModal: el.getAttribute("aria-modal") || "",
            position: style.position,
            zIndex: Number.isFinite(zIndex) ? zIndex : null,
            text: text.slice(0, 240),
            box: {
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            },
          };
        })
        .filter((item) => {
          const largeEnough = item.box.width >= 160 && item.box.height >= 80;
          const overlayLike =
            item.role === "dialog" ||
            item.ariaModal === "true" ||
            ["fixed", "absolute", "sticky"].includes(item.position) ||
            (item.zIndex !== null && item.zIndex >= 100);
          return largeEnough && overlayLike && item.text.length > 0;
        })
        .sort((a, b) => {
          const za = a.zIndex ?? 0;
          const zb = b.zIndex ?? 0;
          return zb - za || b.box.width * b.box.height - a.box.width * a.box.height;
        })
        .slice(0, 20);
      return {
        url: location.href,
        title: document.title,
        viewport: { width: innerWidth, height: innerHeight },
        bodyHead: textOf(document.body).slice(0, 600),
        controls,
        overlays,
      };
    });

    const inspectFile = applicationPath(company, "portal_run_screen_inspection.json");
    writeJsonAscii(inspectFile, {
      company,
      capturedAt: new Date().toISOString(),
      screenshotFile,
      screen,
    });
    addStep(run, "로그인 후 홈 화면 캡처 및 팝업 후보 확인", "completed", {
      screenshotFile,
      inspectFile,
      url: screen.url,
      title: screen.title,
      viewport: screen.viewport,
      overlayCount: screen.overlays.length,
      controlCount: screen.controls.length,
      overlaySummaries: screen.overlays.slice(0, 8).map((item) => ({
        selector: item.selector,
        position: item.position,
        zIndex: item.zIndex,
        text: item.text,
        box: item.box,
      })),
    });
    return { screenshotFile, inspectFile, screen };
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function closeVisiblePopups(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const closed = [];
  try {
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-close-popups.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);

    for (let attempt = 0; attempt < 12; attempt += 1) {
      const candidate = await page.evaluate(() => {
        const textOf = (el) => (el.innerText || el.textContent || el.getAttribute("title") || el.getAttribute("alt") || "").replace(/\s+/g, " ").trim();
        const boxOf = (el) => {
          const rect = el.getBoundingClientRect();
          return {
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            centerX: Math.round(rect.x + rect.width / 2),
            centerY: Math.round(rect.y + rect.height / 2),
          };
        };
        const visible = (el) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
        };
        const selectorOf = (el) => {
          if (el.id) return `#${el.id}`;
          const className = String(el.className || "").trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".");
          return `${el.tagName.toLowerCase()}${className ? `.${className}` : ""}`;
        };
        const closeText = /레이어\s*창\s*닫기|창\s*닫기|닫기|close|확인/i;
        const popupText = /레이어\s*창\s*닫기|오늘\s*하루|팝업|공지|스톡옵션|닫기/i;
        const overlays = Array.from(document.querySelectorAll("body *"))
          .filter(visible)
          .map((el) => {
            const style = getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            const zIndex = Number.parseInt(style.zIndex, 10);
            const text = textOf(el);
            return {
              el,
              selector: selectorOf(el),
              position: style.position,
              zIndex: Number.isFinite(zIndex) ? zIndex : null,
              text,
              area: rect.width * rect.height,
              box: boxOf(el),
            };
          })
          .filter((item) => {
            const largeEnough = item.box.width >= 160 && item.box.height >= 80;
            const overlayLike =
              ["fixed", "absolute", "sticky"].includes(item.position) ||
              (item.zIndex !== null && item.zIndex >= 100);
            return largeEnough && overlayLike && popupText.test(item.text);
          })
          .sort((a, b) => {
            const za = a.zIndex ?? 0;
            const zb = b.zIndex ?? 0;
            return zb - za || b.area - a.area;
          });

        for (const overlay of overlays) {
          const controls = Array.from(overlay.el.querySelectorAll("button, a, input, [role='button']"))
            .filter(visible)
            .map((el) => ({
              el,
              selector: selectorOf(el),
              tag: el.tagName.toLowerCase(),
              text: (textOf(el) || el.getAttribute("value") || el.getAttribute("aria-label") || "").slice(0, 120),
              box: boxOf(el),
            }))
            .filter((control) => closeText.test(control.text));
          const preferred =
            controls.find((control) => /레이어\s*창\s*닫기|창\s*닫기/i.test(control.text)) ||
            controls.find((control) => /닫기|close/i.test(control.text)) ||
            controls.find((control) => /확인/i.test(control.text));
          if (preferred) {
            return {
              overlay: {
                selector: overlay.selector,
                position: overlay.position,
                zIndex: overlay.zIndex,
                text: overlay.text.slice(0, 240),
                box: overlay.box,
              },
              closeControl: {
                selector: preferred.selector,
                tag: preferred.tag,
                text: preferred.text,
                box: preferred.box,
              },
            };
          }
        }
        return null;
      });

      if (!candidate) break;
      await page.mouse.click(candidate.closeControl.box.centerX, candidate.closeControl.box.centerY);
      await page.waitForTimeout(500);
      closed.push(candidate);
    }

    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-close-popups.png`);
    await captureScreenshot(page, company, afterScreenshot, false);

    const verification = await page.evaluate(() => {
      const textOf = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
      };
      const selectorOf = (el) => {
        if (el.id) return `#${el.id}`;
        const className = String(el.className || "").trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".");
        return `${el.tagName.toLowerCase()}${className ? `.${className}` : ""}`;
      };
      const remainingPopupLike = Array.from(document.querySelectorAll("body *"))
        .filter(visible)
        .map((el) => {
          const style = getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          const zIndex = Number.parseInt(style.zIndex, 10);
          return {
            selector: selectorOf(el),
            text: textOf(el).slice(0, 160),
            position: style.position,
            zIndex: Number.isFinite(zIndex) ? zIndex : null,
            box: {
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
            },
          };
        })
        .filter((item) => {
          const overlayLike =
            ["fixed", "absolute", "sticky"].includes(item.position) ||
            (item.zIndex !== null && item.zIndex >= 100);
          return item.box.width >= 160 && item.box.height >= 80 && overlayLike && /레이어\s*창\s*닫기|오늘\s*하루|팝업|공지|스톡옵션|닫기/i.test(item.text);
        })
        .slice(0, 10);

      const targets = Array.from(document.querySelectorAll("button, a"))
        .filter(visible)
        .map((el) => ({ el, text: textOf(el), box: boxOf(el), selector: selectorOf(el) }))
        .filter((item) => item.text === "확인신청" || item.text.includes("확인신청"));
      const targetChecks = targets.map((item) => {
        const top = document.elementFromPoint(item.box.centerX, item.box.centerY);
        return {
          selector: item.selector,
          text: item.text,
          box: item.box,
          topSelector: top ? selectorOf(top) : "",
          topText: top ? textOf(top).slice(0, 120) : "",
          clickable: top === item.el || item.el.contains(top),
        };
      });
      return {
        url: location.href,
        title: document.title,
        remainingPopupLike,
        targetChecks,
      };
    });

    const resultFile = applicationPath(company, "portal_run_popup_close.json");
    writeJsonAscii(resultFile, {
      company,
      capturedAt: new Date().toISOString(),
      beforeScreenshot,
      afterScreenshot,
      closed,
      verification,
    });
    addStep(run, "팝업 후보 동적 닫기", "completed", {
      beforeScreenshot,
      afterScreenshot,
      resultFile,
      closedCount: closed.length,
      remainingPopupLikeCount: verification.remainingPopupLike.length,
      targetChecks: verification.targetChecks,
    });
    return {
      beforeScreenshot,
      afterScreenshot,
      resultFile,
      closed,
      verification,
    };
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function clickConfirmationMenu(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {});
    await page.waitForTimeout(400);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-hover-confirmation-dropdown.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);

    const topMenu = await page.evaluate(() => {
      const textOf = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
      };
      const selectorOf = (el) => {
        if (el.id) return `#${el.id}`;
        const className = String(el.className || "").trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".");
        return `${el.tagName.toLowerCase()}${className ? `.${className}` : ""}`;
      };
      const candidates = Array.from(document.querySelectorAll("button, a"))
        .filter(visible)
        .map((el) => ({ el, selector: selectorOf(el), text: textOf(el), box: boxOf(el) }))
        .filter((item) => item.text === "확인신청" || item.text.includes("확인신청"));
      const preferred =
        candidates.find((item) => item.selector === "#d-gnb-btn-02") ||
        candidates.find((item) => item.box.y < 220) ||
        candidates[0];
      if (!preferred) return null;
      const top = document.elementFromPoint(preferred.box.centerX, preferred.box.centerY);
      return {
        selector: preferred.selector,
        text: preferred.text,
        box: preferred.box,
        topSelector: top ? selectorOf(top) : "",
        topText: top ? textOf(top).slice(0, 120) : "",
        clickable: top === preferred.el || preferred.el.contains(top),
        urlBefore: location.href,
      };
    });
    if (!topMenu) throw new Error("확인신청 상단 메뉴 후보를 찾지 못했습니다.");
    if (!topMenu.clickable) {
      throw new Error(`확인신청 상단 메뉴가 다른 요소에 가려져 있습니다: ${topMenu.topText || topMenu.topSelector}`);
    }

    await page.mouse.move(topMenu.box.centerX, topMenu.box.centerY);
    await page.waitForTimeout(700);
    const afterHoverScreenshot = path.join(dir, `${nowFileStamp()}-after-hover-confirmation-dropdown.png`);
    await captureScreenshot(page, company, afterHoverScreenshot, false);

    const submenu = await page.evaluate(() => {
      const textOf = (el) => (el.innerText || el.textContent || "").replace(/\s+/g, " ").trim();
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
      };
      const selectorOf = (el) => {
        if (el.id) return `#${el.id}`;
        const className = String(el.className || "").trim().split(/\s+/).filter(Boolean).slice(0, 3).join(".");
        return `${el.tagName.toLowerCase()}${className ? `.${className}` : ""}`;
      };
      const links = Array.from(document.querySelectorAll("a"))
        .filter(visible)
        .map((el) => ({ el, selector: selectorOf(el), text: textOf(el), href: el.href || "", box: boxOf(el) }));
      const candidates = links.filter(
        (item) =>
          item.text === "확인신청" &&
          item.href.includes("/venturein/aply/v2") &&
          item.box.y > 150 &&
          item.box.y < 500,
      );
      const preferred = candidates.sort((a, b) => a.box.y - b.box.y)[0];
      const visibleConfirmLinks = links
        .filter((item) => item.text.includes("확인신청"))
        .map((item) => ({ text: item.text, href: item.href, box: item.box }));
      if (!preferred) return { visibleConfirmLinks };
      const top = document.elementFromPoint(preferred.box.centerX, preferred.box.centerY);
      return {
        selector: preferred.selector,
        text: preferred.text,
        href: preferred.href,
        box: preferred.box,
        topSelector: top ? selectorOf(top) : "",
        topText: top ? textOf(top).slice(0, 120) : "",
        clickable: top === preferred.el || preferred.el.contains(top),
        visibleConfirmLinks,
      };
    });
    if (!submenu.selector) {
      throw new Error(`확인신청 드롭다운 세부 메뉴를 찾지 못했습니다: ${JSON.stringify(submenu)}`);
    }
    if (!submenu.clickable) {
      throw new Error(`확인신청 드롭다운 세부 메뉴가 다른 요소에 가려져 있습니다: ${submenu.topText || submenu.topSelector}`);
    }

    await Promise.all([
      page.waitForLoadState("domcontentloaded", { timeout: 15000 }).catch(() => {}),
      page.mouse.click(submenu.box.centerX, submenu.box.centerY),
    ]);
    await page.waitForTimeout(2500);

    let after = null;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        after = await page.evaluate(() => ({
          url: location.href,
          title: document.title,
          bodyHead: (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 800),
        }));
        break;
      } catch (error) {
        if (!isNavigationContextError(error) || attempt === 2) throw error;
        await page.waitForLoadState("domcontentloaded", { timeout: 10000 }).catch(() => {});
        await page.waitForTimeout(700);
      }
    }
    const success =
      after.url.includes("/venturein/aply/v2") ||
      after.bodyHead.includes("신청서") ||
      after.bodyHead.includes("기업정보") ||
      after.bodyHead.includes("혁신성장");
    if (!success) {
      throw new Error(`확인신청 세부 메뉴 클릭 후 신청 화면 검증 실패: ${after.url}`);
    }

    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-click-dropdown-submenu-confirmation.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const resultFile = applicationPath(company, "portal_run_confirmation_menu.json");
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      beforeScreenshot,
      afterHoverScreenshot,
      afterScreenshot,
      topMenu,
      clickedTarget: submenu,
      after,
      resultFile,
    };
    writeJsonAscii(resultFile, result);
    addStep(run, "확인신청 메뉴 클릭", "completed", {
      resultFile,
      beforeScreenshot,
      afterHoverScreenshot,
      afterScreenshot,
      topMenu,
      clickedTarget: submenu,
      urlAfter: after.url,
      titleAfter: after.title,
      bodyHeadAfter: after.bodyHead,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}


async function selectVentureTypeAndFillForm(company, session, args, run) {
  const { page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const { portalInput } = loadPortalInputForCompany(company, args);

  const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-venture-type-select.png`);
  await captureScreenshot(page, company, beforeScreenshot, false);

  // 현재 화면 판별
  const bodyText = await page.evaluate(() => document.body.innerText);
  const isTypeSelectionScreen = bodyText.includes("벤처투자유형") && bodyText.includes("혁신성장유형") && bodyText.includes("바로가기");

  addStep(run, "확인신청 화면 판별", "completed", {
    screenType: isTypeSelectionScreen ? "venture_type_selection" : "step_form",
    beforeScreenshot,
  });

  if (!isTypeSelectionScreen) {
    return { screenType: "step_form", message: "단계별 신청서 화면 — 유형 선택 불필요" };
  }

  // values.md에서 유형 읽기
  const appTypeItem = valueAtPath(portalInput, "values.application_type.application_type");
  const appType = rawPortalValue(appTypeItem);
  if (!appType) throw new Error("values.md의 application_type 값이 없습니다.");

  // 유형 카드 클릭 (텍스트 매칭)
  await page.evaluate((typeName) => {
    const links = Array.from(document.querySelectorAll("a"));
    const target = links.find(a => a.innerText.includes(typeName));
    if (target) target.click();
  }, appType);
  await page.waitForURL(/viewVniaBfrv/, { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(1000);

  addStep(run, "벤처 유형 선택", "completed", {
    selectedType: appType,
    urlAfter: page.url(),
  });

  // 회사개요 폼 값 읽기
  const capitalItem = valueAtPath(portalInput, "values.basic.paid_in_capital");
  const capitalVal = rawPortalValue(capitalItem);
  const fiscalItem = valueAtPath(portalInput, "values.basic.fiscal_year_end_month");
  const fiscalVal = rawPortalValue(fiscalItem);
  const fnstItem = valueAtPath(portalInput, "values.basic.financial_statement_confirmed");
  const fnstVal = rawPortalValue(fnstItem);

  // 폼 입력 — Playwright locator API 사용 (page.evaluate는 change 이벤트가 안 먹히는 경우 있음)
  await page.locator("#confirmCancelAgree").check();
  await page.locator("#confirmNotAllowedAgree").check();
  if (capitalVal) {
    await page.locator("#AMT_SHOW").fill(capitalVal);
    await page.locator("#AMT_SHOW").dispatchEvent("change");
    await page.waitForTimeout(300);
  }
  if (fiscalVal) {
    await page.locator("[name=stacntMm]").selectOption(String(fiscalVal));
    await page.waitForTimeout(300);
  }
  if (fnstVal === "Y") {
    await page.locator("#thstrmFnstCfmtnYn_Y").check();
  } else if (fnstVal === "N") {
    await page.locator("#thstrmFnstCfmtnYn_N").check();
  }

  await page.waitForTimeout(600);
  const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-venture-type-form-fill.png`);
  await captureScreenshot(page, company, afterScreenshot, false);

  // 입력값 검증
  const filled = await page.evaluate(() => ({
    cancelAgree: document.getElementById("confirmCancelAgree")?.checked,
    notAllowedAgree: document.getElementById("confirmNotAllowedAgree")?.checked,
    capital: document.getElementById("AMT_SHOW")?.value,
    fiscal: document.querySelector("[name=stacntMm]")?.value,
    fnstY: document.getElementById("thstrmFnstCfmtnYn_Y")?.checked,
    indstyNm: document.querySelector("[name=indstyNm]")?.value,
    url: location.href,
  }));

  const resultFile = applicationPath(company, "portal_run_venture_type_select.json");
  const result = {
    company,
    screenType: "venture_type_selection",
    selectedType: appType,
    filled,
    beforeScreenshot,
    afterScreenshot,
    resultFile,
  };
  writeJsonAscii(resultFile, result);

  addStep(run, "회사개요 폼 입력 완료 (예 클릭 전 정지)", "completed", {
    resultFile,
    afterScreenshot,
    filled,
  });

  return result;
}

async function confirmVentureTypeSelection(company, session, run) {
  const { page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);

  const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-venture-type-confirm.png`);
  await captureScreenshot(page, company, beforeScreenshot, false);

  const btnState = await page.evaluate(() => {
    const btn = document.getElementById("btnNext");
    if (!btn) return null;
    const r = btn.getBoundingClientRect();
    return { visible: r.width > 0 && r.height > 0, text: btn.innerText.trim(), centerX: Math.round(r.x + r.width / 2), centerY: Math.round(r.y + r.height / 2) };
  });
  if (!btnState || !btnState.visible) throw new Error("예 버튼(#btnNext)을 찾지 못했습니다.");

  await Promise.all([
    page.waitForLoadState("domcontentloaded", { timeout: 15000 }).catch(() => {}),
    page.mouse.click(btnState.centerX, btnState.centerY),
  ]);
  await page.waitForTimeout(2000);

  const after = await page.evaluate(() => ({
    url: location.href,
    title: document.title,
    bodyHead: (document.body?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 800),
  }));

  const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-venture-type-confirm.png`);
  await captureScreenshot(page, company, afterScreenshot, false);

  const resultFile = applicationPath(company, "portal_run_venture_type_confirm.json");
  const result = { company, beforeScreenshot, afterScreenshot, btnState, after, resultFile };
  writeJsonAscii(resultFile, result);

  addStep(run, "혁신성장유형 예 클릭 및 다음 화면 확인", "completed", {
    resultFile, beforeScreenshot, afterScreenshot,
    urlAfter: after.url, titleAfter: after.title, bodyHead: after.bodyHead,
  });
  return result;
}

async function verifyApplicationFormInputPlan(company, session, args, run) {
  const { portalInputFile, portalInput } = loadPortalInputForCompany(company, args);
  const inputPlan = buildApplicationFormInputPlan(portalInput, portalInputFile);
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-application-form-input-plan.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);

    const selectors = [
      ...inputPlan.inputSequence
        .filter((field) => field.selector)
        .map((field) => ({ key: field.key, selector: field.selector })),
      ...inputPlan.inputSequence.flatMap((field) =>
        (field.targetSelectors || [])
          .filter(Boolean)
          .map((selector) => ({ key: `${field.key}:target:${selector}`, selector })),
      ),
      ...inputPlan.confirmActions.map((action) => ({ key: action.key, selector: action.selector })),
      { key: "save_next", selector: 'a[onclick*="doNext"]' },
    ];
    const selectorChecks = await page.evaluate((items) => {
      const textOf = (el) => (el.innerText || el.value || el.textContent || "").replace(/\s+/g, " ").trim();
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          style.visibility !== "hidden" &&
          style.display !== "none" &&
          Number(style.opacity || 1) !== 0
        );
      };
      return items.map((item) => {
        const el = document.querySelector(item.selector);
        if (!el) return { key: item.key, selector: item.selector, found: false };
        return {
          key: item.key,
          selector: item.selector,
          found: true,
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          text: textOf(el).slice(0, 120),
          currentValueLength: "value" in el ? String(el.value || "").length : null,
          readonly: Boolean(el.readOnly),
          disabled: Boolean(el.disabled),
          checked: Boolean(el.checked),
          visible: visible(el),
          box: boxOf(el),
        };
      });
    }, selectors);

    const fields = inputPlan.inputSequence.map((field) => {
      const selectorCheck = selectorChecks.find((item) => item.key === field.key) || null;
      const targetChecks = (field.targetSelectors || []).map((selector) =>
        selectorChecks.find((item) => item.key === `${field.key}:target:${selector}`) || { selector, found: false },
      );
      const methodCanUseReadonly = ["address_search_popup_required", "radio_click", "checkbox_toggle"].includes(
        field.inputMethod,
      );
      const methodCanScreenInput = ["screen_keyboard_replace", "radio_click", "checkbox_toggle"].includes(
        field.inputMethod,
      );
      const conditionMayEnableAfterPriorInput = Boolean(field.enabledWhen && field.enabledBySource);
      const selectorUsable =
        selectorCheck &&
        selectorCheck.found &&
        selectorCheck.visible &&
        !selectorCheck.disabled &&
        (methodCanUseReadonly || !selectorCheck.readonly);
      return {
        ...field,
        selectorCheck,
        targetChecks,
        selectorUsable: Boolean(selectorUsable),
        conditionMayEnableAfterPriorInput,
        readyForScreenInput:
          Boolean(field.canInputFromPreparedValue) &&
          methodCanScreenInput &&
          (Boolean(selectorUsable) || conditionMayEnableAfterPriorInput),
      };
    });
    const confirmActions = inputPlan.confirmActions.map((action) => ({
      ...action,
      selectorCheck: selectorChecks.find((item) => item.key === action.key) || null,
    }));
    const saveNext = selectorChecks.find((item) => item.key === "save_next") || null;
    let saveNextScreenshot = null;
    if (saveNext && saveNext.found) {
      await page.evaluate((selector) => {
        document.querySelector(selector)?.scrollIntoView({ block: "center", inline: "center" });
      }, saveNext.selector);
      await page.waitForTimeout(600);
      saveNextScreenshot = path.join(dir, `${nowFileStamp()}-application-form-save-next-button.png`);
      await captureScreenshot(page, company, saveNextScreenshot, false);
    }
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "application_form",
      url: page.url(),
      title: await page.title().catch(() => ""),
      beforeScreenshot,
      portalInputFile,
      fields,
      confirmActions,
      saveAction: {
        selector: 'a[onclick*="doNext"]',
        method:
          "신청서 단계는 별도 임시저장 버튼이 아니라 저장 후 다음단계로 이동 버튼을 클릭한 뒤 표시되는 확인/예 알림을 수락한다.",
        selectorCheck: saveNext,
        screenshot: saveNextScreenshot,
      },
      missingRequired: fields.filter((field) => field.required && !field.canInputFromPreparedValue),
      notUsableSelectors: fields.filter((field) => field.canInputFromPreparedValue && !field.selectorUsable),
      addressSearchRequired: fields.filter((field) => field.inputMethod === "address_search_popup_required"),
      readyForKeyboardInput: fields.filter((field) => field.readyForScreenInput),
      readyForPreparedInput: fields.filter((field) => field.readyForScreenInput),
    };
    const resultFile = applicationPath(company, "portal_run_application_form_input_plan.json");
    writeJsonAscii(resultFile, result);
    addStep(run, "신청서 1단계 신규 입력 계획 및 위치 검증", "completed", {
      resultFile,
      beforeScreenshot,
      portalInputFile,
      totalFields: fields.length,
      readyForKeyboardInputCount: result.readyForKeyboardInput.length,
      missingRequiredCount: result.missingRequired.length,
      notUsableSelectorCount: result.notUsableSelectors.length,
      addressSearchRequiredCount: result.addressSearchRequired.length,
      confirmActionCount: confirmActions.length,
      saveNextFound: Boolean(saveNext && saveNext.found),
      saveNextScreenshot,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function applicationElementSnapshot(page, selector) {
  return await page.evaluate((css) => {
    const element = document.querySelector(css);
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return {
      selector: css,
      tag: element.tagName.toLowerCase(),
      id: element.id || "",
      name: element.getAttribute("name") || "",
      type: element.getAttribute("type") || "",
      value: "value" in element ? String(element.value || "") : "",
      readonly: Boolean(element.readOnly),
      disabled: Boolean(element.disabled),
      checked: Boolean(element.checked),
      visible:
        rect.width > 0 &&
        rect.height > 0 &&
        style.visibility !== "hidden" &&
        style.display !== "none" &&
        Number(style.opacity || 1) !== 0,
      box: {
        x: Math.round(rect.x),
        y: Math.round(rect.y),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        centerX: Math.round(rect.x + rect.width / 2),
        centerY: Math.round(rect.y + rect.height / 2),
      },
      viewport: { width: innerWidth, height: innerHeight },
    };
  }, selector);
}

async function bringApplicationSelectorIntoView(page, selector) {
  for (let attempt = 0; attempt < 18; attempt += 1) {
    const snapshot = await applicationElementSnapshot(page, selector);
    if (!snapshot) return null;
    const topBand = 160;
    const bottomBand = snapshot.viewport.height - 160;
    if (snapshot.visible && snapshot.box.centerY >= topBand && snapshot.box.centerY <= bottomBand) {
      return snapshot;
    }
    await page.evaluate((css) => {
      document.querySelector(css)?.scrollIntoView({ block: "center", inline: "center" });
    }, selector);
    await page.waitForTimeout(300);
  }
  return await applicationElementSnapshot(page, selector);
}

async function dismissOverlayBlockingPoint(page, point, selector) {
  for (let attempt = 0; attempt < 6; attempt += 1) {
    const blocking = await page.evaluate(
      ({ pt, css }) => {
        const target = css ? document.querySelector(css) : null;
        const top = document.elementFromPoint(pt.centerX, pt.centerY);
        if (!top) return null;
        if (target && (top === target || target.contains(top) || top.contains(target))) return null;
        if (!target && top.tagName === "BODY") return null;
        const textOf = (el) =>
          (el.innerText || el.value || el.getAttribute("title") || el.getAttribute("alt") || "").replace(/\s+/g, " ").trim();
        let node = top;
        while (node && node !== document.body) {
          const style = getComputedStyle(node);
          const zIndex = Number.parseInt(style.zIndex, 10);
          if (["fixed", "absolute", "sticky"].includes(style.position) || (Number.isFinite(zIndex) && zIndex >= 100)) break;
          node = node.parentElement;
        }
        const container = node && node !== document.body ? node : top;
        const controls = Array.from(container.querySelectorAll("button, a, input[type=button], input[type=submit]"));
        const priority = [/레이어\s*창\s*닫기/i, /창\s*닫기/i, /닫기|close/i];
        let closeControl = null;
        for (const pattern of priority) {
          closeControl = controls.find((el) => pattern.test(textOf(el)));
          if (closeControl) break;
        }
        const overlayText = textOf(container).slice(0, 120);
        if (!closeControl) return { blocked: true, closed: false, overlayText };
        closeControl.click();
        return { blocked: true, closed: true, overlayText, closeText: textOf(closeControl) };
      },
      { pt: point, css: selector || null },
    );
    if (!blocking) return;
    if (!blocking.closed) {
      throw new Error(`클릭 지점을 가린 레이어의 닫기 버튼을 찾지 못했습니다: ${blocking.overlayText}`);
    }
    await page.waitForTimeout(400);
  }
  throw new Error("클릭 지점을 가린 레이어를 해제하지 못했습니다.");
}

async function clickApplicationPoint(page, point, selector) {
  await dismissOverlayBlockingPoint(page, point, selector);
  await page.mouse.move(point.centerX, point.centerY, { steps: 10 });
  await page.mouse.click(point.centerX, point.centerY, { delay: 70 });
}

function applicationKeyboardValueMatches(field, actualValue) {
  const actualText = String(actualValue ?? "");
  const expectedText = String(field.preparedValue ?? "");
  if (field.key === "phone_country_code") {
    return actualText.replace(/^\+/, "") === expectedText.replace(/^\+/, "");
  }
  return actualText === expectedText;
}

async function fillApplicationKeyboardField(page, field) {
  const before = await bringApplicationSelectorIntoView(page, field.selector);
  if (!before || !before.visible) throw new Error(`신청서 입력칸을 찾지 못했습니다: ${field.key}`);
  if (before.disabled) throw new Error(`신청서 입력칸이 비활성화되어 있습니다: ${field.key}`);
  if (before.readonly) throw new Error(`신청서 입력칸이 읽기 전용입니다: ${field.key}`);

  let after = null;
  let alreadyMatched = false;
  const preparedValueText = String(field.preparedValue ?? "");
  if (preparedValueText.length > 0 && applicationKeyboardValueMatches(field, before.value)) {
    after = before;
    alreadyMatched = true;
  } else
  if (field.key === "opening_date" || field.key === "representative_birth_date") {
    await dismissOverlayBlockingPoint(page, before.box, field.selector);
    await page.mouse.click(before.box.centerX, before.box.centerY, { clickCount: 3, delay: 40 });
    await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
    await page.keyboard.press("Delete");
    for (let i = 0; i < 30; i += 1) await page.keyboard.press("Backspace");
    await page.keyboard.insertText(String(field.preparedValue).replace(/\D/g, ""));
    await page.waitForTimeout(350);
    after = await applicationElementSnapshot(page, field.selector);
  } else {
    await clickApplicationPoint(page, before.box, field.selector);
    await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
    await page.keyboard.press("Delete");
    await page.keyboard.press("Backspace");
    await page.keyboard.insertText(String(field.preparedValue));
    await page.waitForTimeout(300);
    after = await applicationElementSnapshot(page, field.selector);
  }

  const result = {
    key: field.key,
    label: field.label,
    sourcePath: field.sourcePath,
    selector: field.selector,
    inputMethod:
      field.key === "opening_date" || field.key === "representative_birth_date"
        ? "masked_date_keyboard"
        : field.inputMethod,
    beforeValueLength: before.value.length,
    typedValueLength: String(field.preparedValue).length,
    afterValueLength: after ? after.value.length : null,
    beforeValue: before.value,
    typedValue: field.preparedValue,
    afterValue: after ? after.value : null,
    alreadyMatched,
    verified: Boolean(after && applicationKeyboardValueMatches(field, after.value)),
    point: before.box,
  };
  if (!result.verified) {
    throw new Error(`신청서 입력값 검증 실패: ${field.key}`);
  }
  return result;
}

async function clickApplicationRadioField(page, field) {
  const before = await bringApplicationSelectorIntoView(page, field.selector);
  if (!before || !before.visible) throw new Error(`신청서 라디오 항목을 찾지 못했습니다: ${field.key}`);
  if (before.disabled) throw new Error(`신청서 라디오 항목이 비활성화되어 있습니다: ${field.key}`);
  await clickApplicationPoint(page, before.box, field.selector);
  await page.waitForTimeout(300);
  const after = await applicationElementSnapshot(page, field.selector);
  const result = {
    key: field.key,
    label: field.label,
    sourcePath: field.sourcePath,
    selector: field.selector,
    inputMethod: field.inputMethod,
    selectedOption: field.selectedOption || null,
    typedValue: field.preparedValue,
    beforeChecked: before.checked,
    afterChecked: after ? after.checked : null,
    point: before.box,
    verified: Boolean(after && after.checked),
  };
  if (!result.verified) {
    throw new Error(`신청서 라디오 선택 검증 실패: ${field.key}`);
  }
  return result;
}

async function setApplicationCheckboxField(page, field) {
  const before = await bringApplicationSelectorIntoView(page, field.selector);
  if (!before || !before.visible) throw new Error(`신청서 체크박스를 찾지 못했습니다: ${field.key}`);
  if (before.disabled) throw new Error(`신청서 체크박스가 비활성화되어 있습니다: ${field.key}`);
  const desiredChecked = field.preparedValue === "Y";
  if (Boolean(before.checked) !== desiredChecked) {
    await clickApplicationPoint(page, before.box, field.selector);
    await page.waitForTimeout(300);
  }
  const after = await applicationElementSnapshot(page, field.selector);
  const result = {
    key: field.key,
    label: field.label,
    sourcePath: field.sourcePath,
    selector: field.selector,
    inputMethod: field.inputMethod,
    typedValue: field.preparedValue,
    desiredChecked,
    beforeChecked: before.checked,
    afterChecked: after ? after.checked : null,
    point: before.box,
    verified: Boolean(after) && Boolean(after.checked) === desiredChecked,
  };
  if (!result.verified) {
    throw new Error(`신청서 체크박스 선택 검증 실패: ${field.key}`);
  }
  return result;
}

async function fillApplicationPreparedField(page, field) {
  if (field.inputMethod === "radio_click") return await clickApplicationRadioField(page, field);
  if (field.inputMethod === "checkbox_toggle") return await setApplicationCheckboxField(page, field);
  return await fillApplicationKeyboardField(page, field);
}

async function fillApplicationFormReadyFields(company, session, inputPlan, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    const fields = inputPlan.readyForPreparedInput || inputPlan.readyForKeyboardInput || [];
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-fill-ready-application-fields.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const results = [];
    for (const field of fields) {
      const result = await fillApplicationPreparedField(page, field);
      results.push(result);
    }
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-fill-ready-application-fields.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const resultFile = applicationPath(company, "portal_run_application_form_fill_ready.json");
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "application_form",
      url: page.url(),
      title: await page.title().catch(() => ""),
      beforeScreenshot,
      afterScreenshot,
      filledCount: results.length,
      verifiedCount: results.filter((item) => item.verified).length,
      skippedAddressPopup: (inputPlan.addressSearchRequired || []).map((item) => ({
        key: item.key,
        selector: item.selector,
        inputMethod: item.inputMethod,
        preparedValue: item.preparedValue,
      })),
      results,
      resultFile,
    };
    writeJsonAscii(resultFile, result);
    addStep(run, "신청서 1단계 준비된 값 입력", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      filledCount: result.filledCount,
      verifiedCount: result.verifiedCount,
      filledKeys: results.map((item) => item.key),
      skippedAddressPopup: result.skippedAddressPopup,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function confirmApplicationRequiredChecks(company, session, inputPlan, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-application-required-checks.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const results = [];
    const readyKeys = new Set((inputPlan.readyForPreparedInput || []).map((field) => field.key));
    const actions = (inputPlan.confirmActions || []).filter((action) => !action.fieldKey || readyKeys.has(action.fieldKey));
    for (const action of actions) {
      const before = await bringApplicationSelectorIntoView(page, action.selector);
      if (!before || !before.visible) throw new Error(`신청서 확인 버튼을 찾지 못했습니다: ${action.key}`);
      await clickApplicationPoint(page, before.box, action.selector);
      await page.waitForTimeout(900);
      const after = await applicationElementSnapshot(page, action.selector);
      results.push({
        key: action.key,
        label: action.label,
        selector: action.selector,
        before,
        after,
        clicked: true,
        point: before.box,
      });
    }
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-application-required-checks.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const resultFile = applicationPath(company, "portal_run_application_form_required_checks.json");
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "application_form",
      url: page.url(),
      title: await page.title().catch(() => ""),
      beforeScreenshot,
      afterScreenshot,
      checkedCount: results.length,
      dialogs,
      results,
      skipped: (inputPlan.confirmActions || [])
        .filter((action) => action.fieldKey && !readyKeys.has(action.fieldKey))
        .map((action) => ({ key: action.key, fieldKey: action.fieldKey, reason: "source_value_missing_or_not_ready" })),
      resultFile,
    };
    writeJsonAscii(resultFile, result);
    addStep(run, "신청서 1단계 필수 확인 버튼 처리", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      checkedCount: result.checkedCount,
      checkedKeys: results.map((item) => item.key),
      skipped: result.skipped,
      dialogs,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function saveApplicationFormAndGoNext(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-application-form-next.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const selector = 'a[onclick*="doNext"]';
    const before = await bringApplicationSelectorIntoView(page, selector);
    if (!before || !before.visible) throw new Error("저장 후 다음단계로 이동 버튼을 찾지 못했습니다.");
    await clickApplicationPoint(page, before.box, selector);
    await page
      .waitForURL(/\/venturein\/aply\/v2\/cmp\/viewCmpForm/, { timeout: 15000, waitUntil: "domcontentloaded" })
      .catch(() => {});
    await page.waitForTimeout(1200);
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-application-form-next.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const afterUrl = page.url();
    const afterTitle = await page.title().catch(() => "");
    const bodyPreview = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const success = /\/venturein\/aply\/v2\/cmp\/viewCmpForm/.test(afterUrl);
    const resultFile = applicationPath(company, "portal_run_application_form_save_next.json");
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      fromPage: "application_form",
      toPage: "company_info",
      beforeScreenshot,
      afterScreenshot,
      selector,
      before,
      dialogs,
      afterUrl,
      afterTitle,
      bodyPreview: bodyPreview.slice(0, 700),
      success,
      resultFile,
    };
    writeJsonAscii(resultFile, result);
    if (!success) {
      throw new Error(`저장 후 다음단계 이동 실패: ${afterUrl}`);
    }
    addStep(run, "신청서 1단계 저장 후 다음단계 이동", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      afterUrl,
      afterTitle,
      dialogs,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function inspectCompanyInfoScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-company-info-screen-structure.png`);
    await captureScreenshot(page, company, screenshotFile, false);
    const structure = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const boxOf = (element) => {
        const rect = element.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
          docY: Math.round(rect.y + window.scrollY),
        };
      };
      const visible = (element) => {
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          style.display !== "none" &&
          style.visibility !== "hidden" &&
          Number(style.opacity || 1) !== 0
        );
      };
      const selectorOf = (element, index) => {
        if (element.id) return `#${element.id}`;
        const name = element.getAttribute("name");
        if (name) return `${element.tagName.toLowerCase()}[name="${name.replace(/"/g, '\\"')}"]`;
        const onclick = element.getAttribute("onclick");
        if (onclick) return `${element.tagName.toLowerCase()}[onclick="${onclick.replace(/"/g, '\\"')}"]`;
        return `${element.tagName.toLowerCase()}:visible-index(${index})`;
      };
      const bodyText = document.body.innerText || "";
      const sectionCandidates = Array.from(
        document.querySelectorAll("h1,h2,h3,h4,h5,h6,legend,strong,th,caption,div,p,span,label"),
      )
        .filter(visible)
        .map((element, index) => ({
          text: norm(element.innerText || element.textContent).slice(0, 160),
          tag: element.tagName.toLowerCase(),
          className: String(element.className || "").slice(0, 80),
          selector: selectorOf(element, index),
          box: boxOf(element),
        }))
        .filter((item) => item.text.length >= 2 && item.text.length <= 160)
        .filter(
          (item) =>
            !item.text.includes("바로가기") &&
            !item.text.includes("로그아웃") &&
            !item.text.includes("통합로그인"),
        )
        .sort((a, b) => a.box.docY - b.box.docY || a.box.x - b.box.x);
      const sections = [];
      for (const candidate of sectionCandidates) {
        if (sections.some((item) => item.text === candidate.text || Math.abs(item.box.docY - candidate.box.docY) < 10)) {
          continue;
        }
        sections.push(candidate);
        if (sections.length >= 80) break;
      }
      const controls = Array.from(document.querySelectorAll("input,textarea,select,button,a"))
        .filter(visible)
        .map((element, index) => ({
          tag: element.tagName.toLowerCase(),
          type: element.getAttribute("type") || "",
          id: element.id || "",
          name: element.getAttribute("name") || "",
          selector: selectorOf(element, index),
          text: norm(element.innerText || element.value || element.textContent).slice(0, 120),
          valueLength: "value" in element ? String(element.value || "").length : null,
          checked: "checked" in element ? Boolean(element.checked) : null,
          readonly: Boolean(element.readOnly),
          disabled: Boolean(element.disabled),
          onclick: (element.getAttribute("onclick") || "").slice(0, 160),
          href: (element.getAttribute("href") || "").slice(0, 160),
          box: boxOf(element),
        }));
      return {
        url: location.href,
        title: document.title,
        viewport: {
          innerWidth,
          innerHeight,
          scrollHeight: document.documentElement.scrollHeight,
        },
        bodyHead: bodyText.slice(0, 1500),
        sections,
        controls,
        inputs: controls.filter((control) => ["input", "textarea", "select"].includes(control.tag)),
        actions: controls.filter((control) => control.tag === "button" || control.tag === "a"),
      };
    });
    const success = /\/venturein\/aply\/v2\/cmp\/viewCmpForm/.test(structure.url);
    const resultFile = applicationPath(company, "portal_run_company_info_screen_structure.json");
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "company_info",
      screenshotFile,
      success,
      structure,
      resultFile,
    };
    writeJsonAscii(resultFile, result);
    if (!success) {
      throw new Error(`기업정보 화면 구조 파악 실패: ${structure.url}`);
    }
    addStep(run, "기업정보 화면 구성 파악", "completed", {
      resultFile,
      screenshotFile,
      url: structure.url,
      title: structure.title,
      sectionCount: structure.sections.length,
      controlCount: structure.controls.length,
      inputCount: structure.inputs.length,
      actionCount: structure.actions.length,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function verifyCompanyInfoInputPlan(company, session, args, run) {
  const { portalInputFile, portalInput } = loadPortalInputForCompany(company, args);
  const inputPlan = buildCompanyInfoInputPlan(portalInput, portalInputFile);
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-company-info-input-plan.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);

    const selectorItems = inputPlan.fields.flatMap((field) => {
      const items = [];
      if (field.selector) items.push({ key: field.key, selector: field.selector });
      for (const option of field.options || []) items.push({ key: `${field.key}:${option.value}`, selector: option.selector });
      for (const selector of field.selectors || []) items.push({ key: `${field.key}:${selector}`, selector });
      if (field.addButtonSelector) items.push({ key: `${field.key}:add`, selector: field.addButtonSelector });
      if (field.rowSelectors) {
        items.push({ key: `${field.key}:row0:month`, selector: field.rowSelectors.month.replace("{index}", "0") });
        items.push({ key: `${field.key}:row0:content`, selector: field.rowSelectors.content.replace("{index}", "0") });
      }
      return items;
    });
    const selectorChecks = await page.evaluate((items) => {
      const textOf = (el) => (el.innerText || el.value || el.textContent || "").replace(/\s+/g, " ").trim();
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
          docY: Math.round(rect.y + window.scrollY),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      return items.map((item) => {
        const el = document.querySelector(item.selector);
        if (!el) return { key: item.key, selector: item.selector, found: false };
        return {
          key: item.key,
          selector: item.selector,
          found: true,
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          text: textOf(el).slice(0, 120),
          valueLength: "value" in el ? String(el.value || "").length : null,
          checked: "checked" in el ? Boolean(el.checked) : null,
          readonly: Boolean(el.readOnly),
          disabled: Boolean(el.disabled),
          visible: visible(el),
          box: boxOf(el),
        };
      });
    }, selectorItems);

    const fields = inputPlan.fields.map((field) => {
      const selectorCheck = field.selector
        ? selectorChecks.find((item) => item.key === field.key) || null
        : null;
      const optionChecks = (field.options || []).map((option) => ({
        ...option,
        selectorCheck: selectorChecks.find((item) => item.key === `${field.key}:${option.value}`) || null,
      }));
      const selectChecks = (field.selectors || []).map((selector) => ({
        selector,
        selectorCheck: selectorChecks.find((item) => item.key === `${field.key}:${selector}`) || null,
      }));
      const addButtonCheck = field.addButtonSelector
        ? selectorChecks.find((item) => item.key === `${field.key}:add`) || null
        : null;
      const row0Checks = field.rowSelectors
        ? {
            month: selectorChecks.find((item) => item.key === `${field.key}:row0:month`) || null,
            content: selectorChecks.find((item) => item.key === `${field.key}:row0:content`) || null,
          }
        : null;
      const methodUsable =
        field.inputMethod === "dynamic_rows_keyboard_replace"
          ? Boolean(addButtonCheck?.found && addButtonCheck.visible && row0Checks?.month?.found && row0Checks?.content?.found)
          : field.inputMethod === "radio_click"
            ? optionChecks.some((item) => item.value === field.preparedValue && item.selectorCheck?.found)
            : field.inputMethod === "cascading_selects" || field.inputMethod === "three_text_inputs"
              ? selectChecks.every((item) => item.selectorCheck?.found)
              : Boolean(selectorCheck?.found);
      return {
        ...field,
        selectorCheck,
        optionChecks,
        selectChecks,
        addButtonCheck,
        row0Checks,
        methodUsable,
        readyForScreenInput: Boolean(field.canInputFromPreparedValue && methodUsable),
      };
    });
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "company_info",
      url: page.url(),
      title: await page.title().catch(() => ""),
      beforeScreenshot,
      portalInputFile,
      sections: inputPlan.sections,
      fields,
      missingRequired: fields.filter((field) => field.required && !field.canInputFromPreparedValue),
      notUsableSelectors: fields.filter((field) => field.canInputFromPreparedValue && !field.methodUsable),
      readyForPreparedInput: fields.filter((field) => field.readyForScreenInput),
    };
    const resultFile = applicationPath(company, "portal_run_company_info_input_plan.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    addStep(run, "기업정보 2단계 입력 계획 및 위치 검증", "completed", {
      resultFile,
      beforeScreenshot,
      totalFields: fields.length,
      readyForPreparedInputCount: result.readyForPreparedInput.length,
      missingRequiredCount: result.missingRequired.length,
      notUsableSelectorCount: result.notUsableSelectors.length,
      readyKeys: result.readyForPreparedInput.map((field) => field.key),
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function closeCompanyInfoLayerIfPresent(page) {
  return await page.evaluate(() => {
    const visible = (el) => {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    };
    const target = Array.from(
      document.querySelectorAll(".layer_pop_box a.common_btn.next, .layer_pop_box button.layer_pop_close"),
    ).find(visible);
    if (!target) return false;
    target.click();
    return true;
  });
}

async function fillCompanyHistory(page, field) {
  const histories = Array.isArray(field.preparedValue) ? field.preparedValue : [];
  const countRows = async () =>
    await page.evaluate(() => Array.from(document.querySelectorAll('input[name^="cmpHstyList"][name$=".hstyYm"]')).length);
  const addClicks = [];
  while ((await countRows()) < histories.length) {
    await page.locator(field.addButtonSelector).scrollIntoViewIfNeeded();
    await page.locator(field.addButtonSelector).click();
    await page.waitForTimeout(500);
    addClicks.push({ afterCount: await countRows() });
    if (addClicks.length > histories.length + 2) throw new Error("기업연혁 행 추가가 진행되지 않습니다.");
  }
  const results = [];
  for (let index = 0; index < histories.length; index += 1) {
    const item = histories[index] || {};
    const month = String(item.month || item.ym || "").trim();
    const content = String(item.content || item.description || "").trim();
    const monthSelector = field.rowSelectors.month.replace("{index}", String(index));
    const contentSelector = field.rowSelectors.content.replace("{index}", String(index));
    await page.locator(monthSelector).scrollIntoViewIfNeeded();
    await page.locator(monthSelector).fill(month);
    await page.locator(contentSelector).fill(content);
    const actual = await page.evaluate(
      ({ monthSelector, contentSelector }) => ({
        month: document.querySelector(monthSelector)?.value || "",
        content: document.querySelector(contentSelector)?.value || "",
      }),
      { monthSelector, contentSelector },
    );
    results.push({
      index,
      monthSelector,
      contentSelector,
      expected: { month, content },
      actual,
      verified: actual.month === month && actual.content === content,
    });
  }
  return {
    key: field.key,
    addClicks,
    rowCountAfter: await countRows(),
    results,
    verified: results.every((item) => item.verified),
  };
}

async function fillCompanyInfoReadyFields(company, session, inputPlan, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    await closeCompanyInfoLayerIfPresent(page);
    await page.waitForTimeout(400);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-fill-ready-company-info-fields.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const results = [];
    for (const field of inputPlan.readyForPreparedInput || []) {
      if (field.key === "company_history") {
        results.push(await fillCompanyHistory(page, field));
      }
    }
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-fill-ready-company-info-fields.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "company_info",
      url: page.url(),
      title: await page.title().catch(() => ""),
      beforeScreenshot,
      afterScreenshot,
      filledCount: results.length,
      verifiedCount: results.filter((item) => item.verified).length,
      results,
    };
    const resultFile = applicationPath(company, "portal_run_company_info_fill_ready.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    addStep(run, "기업정보 2단계 준비된 값 입력", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      filledCount: result.filledCount,
      verifiedCount: result.verifiedCount,
      filledKeys: results.map((item) => item.key),
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function clickVisibleLayerConfirm(page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await page.evaluate(() => {
        const visible = (el) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
        };
        const target = Array.from(
          document.querySelectorAll(".layer_pop_box a.common_btn.next, .layer_pop_box button.layer_pop_close"),
        ).find(visible);
        if (!target) return false;
        target.click();
        return true;
      });
    } catch (error) {
      if (!/Execution context was destroyed|Cannot find context/i.test(error.message || "") || attempt === 2) {
        throw error;
      }
      await page.waitForLoadState("domcontentloaded", { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(500);
    }
  }
  return false;
}

async function waitForSavedLayer(page, timeoutMs = 20000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const found = await page.evaluate(() => {
        const visible = (el) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
        };
        return Array.from(document.querySelectorAll(".layer_pop_box"))
          .filter(visible)
          .some((el) => String(el.innerText || el.textContent || "").includes("저장되었습니다"));
      });
      if (found) return true;
    } catch (error) {
      if (!/Execution context was destroyed|Cannot find context/i.test(error.message || "")) {
        throw error;
      }
      await page.waitForLoadState("domcontentloaded", { timeout: 5000 }).catch(() => {});
    }
    await page.waitForTimeout(500);
  }
  return false;
}

async function collectVisibleLayerItems(page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await page.evaluate(() => {
        const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
        const visible = (el) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
        };
        return Array.from(document.querySelectorAll(".layer_pop_box, .layer_pop_box a, .layer_pop_box button"))
          .filter(visible)
          .map((el) => ({
            tag: el.tagName.toLowerCase(),
            className: String(el.className || ""),
            text: norm(el.innerText || el.value || el.textContent).slice(0, 200),
          }));
      });
    } catch (error) {
      if (!/Execution context was destroyed|Cannot find context/i.test(error.message || "") || attempt === 2) {
        throw error;
      }
      await page.waitForLoadState("domcontentloaded", { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(500);
    }
  }
  return [];
}

function nextPortalUrlFromCurrent(currentUrl, pathname) {
  const url = new URL(currentUrl);
  const vniaSn = url.searchParams.get("vniaSn");
  const menuId = url.searchParams.get("menuId") || "5000170";
  if (!vniaSn) throw new Error(`현재 URL에서 vniaSn을 찾지 못했습니다: ${currentUrl}`);
  return `${url.origin}${pathname}?vniaSn=${encodeURIComponent(vniaSn)}&menuId=${encodeURIComponent(menuId)}`;
}

async function navigateDirectlyAfterTemporarySave(company, session, run, options) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-direct-navigation-${options.fromPage}-to-${options.toPage}.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const beforeUrl = page.url();
    const targetUrl = nextPortalUrlFromCurrent(beforeUrl, options.pathname);
    await page.goto(targetUrl, { timeout: 15000, waitUntil: "domcontentloaded" }).catch(() => {});
    await page.waitForTimeout(1200);
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-direct-navigation-${options.fromPage}-to-${options.toPage}.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const afterUrl = page.url();
    const afterTitle = await page.title().catch(() => "");
    const bodyPreview = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const success = options.urlRegex.test(afterUrl);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      fromPage: options.fromPage,
      toPage: options.toPage,
      method: "direct_url_navigation_after_temporary_save",
      prohibitedAction: "save_next_button_click_when_temporary_save_exists",
      beforeUrl,
      targetUrl,
      beforeScreenshot,
      afterScreenshot,
      afterUrl,
      afterTitle,
      bodyPreview: bodyPreview.slice(0, 1000),
      success,
    };
    const resultFile = applicationPath(company, options.resultFileName);
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`${options.stepName} 실패: ${afterUrl}`);
    updateWorkflowPage(company, options.fromPage, {
      actions: {
        save_next: {
          selector: options.prohibitedSelector || "",
          status: "prohibited_when_temporary_save_exists",
          prohibited_reason: "임시저장 버튼이 있는 화면에서는 저장 후 다음단계로 이동 버튼을 누르지 않는다.",
        },
        direct_navigation_after_temporary_save: {
          method: "direct_url_navigation_after_temporary_save",
          to_page: options.toPage,
          pathname: options.pathname,
          status: "verified",
        },
      },
      evidence: {
        latest_direct_navigation_test: `portal_run_state.json#execution_state.portal_run.artifacts.${path.basename(options.resultFileName, ".json")}`,
      },
    });
    addStep(run, options.stepName, "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      beforeUrl,
      targetUrl,
      afterUrl,
      afterTitle,
      prohibitedAction: result.prohibitedAction,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function saveCompanyInfoTemporary(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    await page.waitForTimeout(600);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-company-info-temporary.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    await page.locator("#btnAplyTemporarySave").scrollIntoViewIfNeeded();
    await page.locator("#btnAplyTemporarySave").click();
    await page.waitForTimeout(1200);
    await waitForSavedLayer(page);
    const layerBeforeConfirm = await collectVisibleLayerItems(page);
    const layerConfirmed = await clickVisibleLayerConfirm(page);
    await page.waitForTimeout(700);
    const remainingLayerCount = (await collectVisibleLayerItems(page)).filter((item) =>
      String(item.className || "").includes("layer_pop_box"),
    ).length;
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-company-info-temporary.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success =
      layerBeforeConfirm.some((item) => item.text.includes("저장되었습니다")) &&
      layerConfirmed &&
      remainingLayerCount === 0;
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "company_info",
      beforeScreenshot,
      afterScreenshot,
      url: page.url(),
      title: await page.title().catch(() => ""),
      dialogs,
      layerBeforeConfirm,
      layerConfirmed,
      remainingLayerCount,
      success,
    };
    const resultFile = applicationPath(company, "portal_run_company_info_temporary_save.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("기업정보 임시저장 확인 처리 검증 실패");
    updateWorkflowPage(company, "company_info", {
      actions: {
        temporary_save: {
          selector: "#btnAplyTemporarySave",
          method: "click_then_wait_for_saved_layer_then_click_confirm",
          status: "verified",
        },
      },
      evidence: {
        latest_temporary_save_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_company_info_temporary_save",
      },
    });
    addStep(run, "기업정보 2단계 임시저장 및 확인 처리", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      layerConfirmed,
      remainingLayerCount,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function saveCompanyInfoAndGoNext(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    await page.waitForTimeout(600);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-company-info-next.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const selector = 'a[onclick*="/venturein/aply/v2/rprsv/viewRprsvForm"]';
    await page.locator(selector).scrollIntoViewIfNeeded();
    await page.locator(selector).click();
    await page.waitForTimeout(1000);
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const clicked = await clickVisibleLayerConfirm(page);
      if (!clicked) break;
      await page.waitForTimeout(700);
    }
    await page
      .waitForURL(/\/venturein\/aply\/v2\/rprsv\/viewRprsvForm/, { timeout: 15000, waitUntil: "domcontentloaded" })
      .catch(() => {});
    await page.waitForTimeout(1200);
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-company-info-next.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const afterUrl = page.url();
    const afterTitle = await page.title().catch(() => "");
    const bodyPreview = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const success = /\/venturein\/aply\/v2\/rprsv\/viewRprsvForm/.test(afterUrl);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      fromPage: "company_info",
      toPage: "representative_info",
      selector,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      afterUrl,
      afterTitle,
      bodyPreview: bodyPreview.slice(0, 1000),
      success,
    };
    const resultFile = applicationPath(company, "portal_run_company_info_save_next.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`기업정보 저장 후 다음단계 이동 실패: ${afterUrl}`);
    addStep(run, "기업정보 2단계 저장 후 다음단계 이동", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      afterUrl,
      afterTitle,
      dialogs,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function inspectRepresentativeInfoScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-representative-info-screen-structure.png`);
    await captureScreenshot(page, company, screenshotFile, false);
    const structure = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
          docY: Math.round(rect.y + window.scrollY),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const controls = Array.from(document.querySelectorAll("input,select,textarea,button,a"))
        .filter(visible)
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          text: norm(el.innerText || el.value || el.textContent).slice(0, 120),
          onclick: (el.getAttribute("onclick") || "").slice(0, 160),
          href: (el.getAttribute("href") || "").slice(0, 160),
          box: boxOf(el),
        }));
      return {
        url: location.href,
        title: document.title,
        bodyHead: norm(document.body.innerText).slice(0, 1500),
        controls,
        inputs: controls.filter((control) => ["input", "textarea", "select"].includes(control.tag)),
        actions: controls.filter((control) => control.tag === "button" || control.tag === "a"),
      };
    });
    const success = /\/venturein\/aply\/v2\/rprsv\/viewRprsvForm/.test(structure.url);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "representative_info",
      screenshotFile,
      success,
      structure,
    };
    const resultFile = applicationPath(company, "portal_run_representative_info_screen_structure.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`대표자정보 화면 구성 파악 실패: ${structure.url}`);
    addStep(run, "대표자정보 3단계 화면 구성 파악", "completed", {
      resultFile,
      screenshotFile,
      url: structure.url,
      title: structure.title,
      controlCount: structure.controls.length,
      inputCount: structure.inputs.length,
      actionCount: structure.actions.length,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function inspectRepresentativeInfoButtons(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-representative-info-before-buttons.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);

    await page.locator('button[name="btnRprsvAdd"]').click();
    await page.waitForTimeout(1200);
    const addScreenshot = path.join(dir, `${nowFileStamp()}-representative-info-add-modal.png`);
    await captureScreenshot(page, company, addScreenshot, false);
    const addModal = await inspectRepresentativeVisibleModal(page);
    await closeRepresentativeModal(page);
    await page.waitForTimeout(600);

    await page.locator('button[name="btnRprsvUpd"]').click();
    await page.waitForTimeout(1200);
    const updateScreenshot = path.join(dir, `${nowFileStamp()}-representative-info-update-modal.png`);
    await captureScreenshot(page, company, updateScreenshot, false);
    const updateModal = await inspectRepresentativeVisibleModal(page);
    await closeRepresentativeModal(page);
    await page.waitForTimeout(600);

    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "representative_info",
      beforeScreenshot,
      addScreenshot,
      updateScreenshot,
      addModal,
      updateModal,
      conclusion:
        "대표자가 1명인 현재 케이스에서는 대표자추가 입력이 필요 없고, 대표자수정 모달에서 기존 대표자 값이 채워진 구조만 확인한다.",
      success: Boolean(addModal.present && updateModal.present),
    };
    const resultFile = applicationPath(company, "portal_run_representative_info_buttons.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!result.success) throw new Error("대표자정보 버튼 화면 변화 검증 실패");
    addStep(run, "대표자정보 3단계 대표자추가/대표자수정 화면 확인", "completed", {
      resultFile,
      beforeScreenshot,
      addScreenshot,
      updateScreenshot,
      addModalPresent: addModal.present,
      updateModalPresent: updateModal.present,
      updatePrefilledKeys: updateModal.prefilledKeys,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function inspectRepresentativeVisibleModal(page) {
  return await page.evaluate(() => {
    const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
    const visible = (el) => {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    };
    const modal = Array.from(document.querySelectorAll(".layer_pop_box")).find(visible);
    const inputs = Array.from(document.querySelectorAll(".layer_pop_box input, .layer_pop_box select, .layer_pop_box textarea"))
      .filter(visible)
      .map((el) => ({
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute("type") || "",
        id: el.id || "",
        name: el.getAttribute("name") || "",
        valueLength: "value" in el ? String(el.value || "").length : null,
        checked: "checked" in el ? Boolean(el.checked) : null,
      }));
    const prefilledKeys = inputs
      .filter((item) => item.valueLength > 0 || item.checked === true)
      .map((item) => item.name || item.id)
      .filter(Boolean);
    return {
      present: Boolean(modal),
      title: modal ? norm(modal.innerText).slice(0, 80) : "",
      textHead: modal ? norm(modal.innerText).slice(0, 800) : "",
      inputCount: inputs.length,
      inputs,
      prefilledKeys,
    };
  });
}

async function closeRepresentativeModal(page) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      await page.evaluate(() => {
        const visible = (el) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
        };
        const close = Array.from(document.querySelectorAll(".layer_pop_box button.layer_pop_close, button.layer_pop_close"))
          .find(visible);
        if (close) close.click();
      });
      await page.waitForTimeout(300);
      return;
    } catch (error) {
      if (!/Execution context was destroyed|Cannot find context/i.test(error.message || "") || attempt === 2) {
        throw error;
      }
      await page.waitForLoadState("domcontentloaded", { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(500);
    }
  }
}

async function saveRepresentativeInfoTemporary(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    await closeRepresentativeModal(page);
    await page.waitForTimeout(600);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-representative-info-temporary.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    await page.locator("#btnAplyTemporarySave").scrollIntoViewIfNeeded();
    await page.locator("#btnAplyTemporarySave").click();
    await page.waitForTimeout(1200);
    const savedLayerFound = await waitForSavedLayer(page);
    const layerBeforeConfirm = await collectVisibleLayerItems(page);
    const layerConfirmed = await clickVisibleLayerConfirm(page);
    await page.waitForTimeout(700);
    const remainingLayerCount = (await collectVisibleLayerItems(page)).filter((item) =>
      String(item.className || "").includes("layer_pop_box"),
    ).length;
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-representative-info-temporary.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success = savedLayerFound && layerConfirmed && remainingLayerCount === 0;
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "representative_info",
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerBeforeConfirm,
      layerConfirmed,
      remainingLayerCount,
      success,
    };
    const resultFile = applicationPath(company, "portal_run_representative_info_temporary_save.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("대표자정보 임시저장 확인 처리 검증 실패");
    addStep(run, "대표자정보 3단계 임시저장 및 확인 처리", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerConfirmed,
      remainingLayerCount,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function saveRepresentativeInfoAndGoNext(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-representative-info-next.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const selector = 'a[onclick*="/venturein/aply/v2/fnaf/viewFnafForm"]';
    await page.locator(selector).scrollIntoViewIfNeeded();
    await page.locator(selector).click();
    await page.waitForTimeout(1000);
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const clicked = await clickVisibleLayerConfirm(page);
      if (!clicked) break;
      await page.waitForTimeout(700);
    }
    await page
      .waitForURL(/\/venturein\/aply\/v2\/fnaf\/viewFnafForm/, { timeout: 15000, waitUntil: "domcontentloaded" })
      .catch(() => {});
    await page.waitForTimeout(1200);
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-representative-info-next.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const afterUrl = page.url();
    const afterTitle = await page.title().catch(() => "");
    const bodyPreview = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const success = /\/venturein\/aply\/v2\/fnaf\/viewFnafForm/.test(afterUrl);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      fromPage: "representative_info",
      toPage: "finance_status",
      selector,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      afterUrl,
      afterTitle,
      bodyPreview: bodyPreview.slice(0, 1000),
      success,
    };
    const resultFile = applicationPath(company, "portal_run_representative_info_save_next.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`대표자정보 저장 후 다음단계 이동 실패: ${afterUrl}`);
    addStep(run, "대표자정보 3단계 저장 후 다음단계 이동", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      afterUrl,
      afterTitle,
      dialogs,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function inspectFinanceStatusScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-finance-status-screen-structure.png`);
    await captureScreenshot(page, company, screenshotFile, false);
    const structure = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const controls = Array.from(document.querySelectorAll("input,select,textarea,button,a"))
        .filter(visible)
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          text: norm(el.innerText || el.value || el.textContent).slice(0, 120),
          onclick: (el.getAttribute("onclick") || "").slice(0, 160),
          href: (el.getAttribute("href") || "").slice(0, 160),
        }));
      return {
        url: location.href,
        title: document.title,
        bodyHead: norm(document.body.innerText).slice(0, 1600),
        controls,
        inputs: controls.filter((control) => ["input", "textarea", "select"].includes(control.tag)),
        actions: controls.filter((control) => control.tag === "button" || control.tag === "a"),
      };
    });
    const success = /\/venturein\/aply\/v2\/fnaf\/viewFnafForm/.test(structure.url);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "finance_status",
      screenshotFile,
      success,
      structure,
    };
    const resultFile = applicationPath(company, "portal_run_finance_status_screen_structure.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`재무현황 화면 구성 파악 실패: ${structure.url}`);
    updateWorkflowPage(
      company,
      "finance_status",
      {
        step_index: 4,
        page_key: "finance_status",
        page_label: "재무현황",
        status: "verified_structure",
        url_pattern: "/venturein/aply/v2/fnaf/viewFnafForm",
        sections: {
          three_year_financial_statement: {
            section_label: "최근 3개년 재무현황표",
            status: "verified_structure_pending_values",
            input_names: structure.inputs.map((control) => control.name).filter(Boolean),
          },
        },
        actions: {
          temporary_save: {
            selector: "#btnAplyTemporarySave",
            method: "click_then_confirm_saved_layer",
            status: "observed",
          },
          save_next: {
            selector: 'a[onclick*="/venturein/aply/v3/bps/viewBizPlanSmryForm"]',
            method: "click_then_confirm_layer",
            to_page: "business_plan_summary",
            status: "observed_not_executed",
          },
        },
        evidence: {
          latest_structure_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_finance_status_screen_structure",
        },
      },
      "finance_status",
    );
    addStep(run, "재무현황 4단계 화면 구성 파악", "completed", {
      resultFile,
      screenshotFile,
      url: structure.url,
      title: structure.title,
      controlCount: structure.controls.length,
      inputCount: structure.inputs.length,
      actionCount: structure.actions.length,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function saveFinanceStatusTemporary(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    await page.waitForTimeout(600);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-finance-status-temporary.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    await page.locator("#btnAplyTemporarySave").scrollIntoViewIfNeeded();
    await page.locator("#btnAplyTemporarySave").click();
    await page.waitForTimeout(1200);
    const savedLayerFound = await waitForSavedLayer(page);
    const layerBeforeConfirm = await collectVisibleLayerItems(page);
    const layerConfirmed = await clickVisibleLayerConfirm(page);
    await page.waitForTimeout(700);
    const remainingLayerCount = (await collectVisibleLayerItems(page)).filter((item) =>
      String(item.className || "").includes("layer_pop_box"),
    ).length;
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-finance-status-temporary.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success = savedLayerFound && layerConfirmed && remainingLayerCount === 0;
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "finance_status",
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerBeforeConfirm,
      layerConfirmed,
      remainingLayerCount,
      success,
    };
    const resultFile = applicationPath(company, "portal_run_finance_status_temporary_save.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("재무현황 임시저장 확인 처리 검증 실패");
    updateWorkflowPage(company, "finance_status", {
      actions: {
        temporary_save: {
          selector: "#btnAplyTemporarySave",
          method: "click_then_wait_for_saved_layer_then_click_confirm",
          status: "verified",
        },
      },
      evidence: {
        latest_temporary_save_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_finance_status_temporary_save",
      },
    });
    addStep(run, "재무현황 4단계 임시저장 및 확인 처리", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerConfirmed,
      remainingLayerCount,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function saveFinanceStatusAndGoNext(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-finance-status-next.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const selector = 'a[onclick*="/venturein/aply/v3/bps/viewBizPlanSmryForm"]';
    await page.locator(selector).scrollIntoViewIfNeeded();
    await page.locator(selector).click();
    await page.waitForTimeout(1000);
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const clicked = await clickVisibleLayerConfirm(page);
      if (!clicked) break;
      await page.waitForTimeout(700);
    }
    await page
      .waitForURL(/\/venturein\/aply\/v3\/bps\/viewBizPlanSmryForm/, { timeout: 15000, waitUntil: "domcontentloaded" })
      .catch(() => {});
    await page.waitForTimeout(1200);
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-finance-status-next.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const afterUrl = page.url();
    const afterTitle = await page.title().catch(() => "");
    const bodyPreview = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const success = /\/venturein\/aply\/v3\/bps\/viewBizPlanSmryForm/.test(afterUrl);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      fromPage: "finance_status",
      toPage: "business_plan_summary",
      selector,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      afterUrl,
      afterTitle,
      bodyPreview: bodyPreview.slice(0, 1000),
      success,
    };
    const resultFile = applicationPath(company, "portal_run_finance_status_save_next.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`재무현황 저장 후 다음단계 이동 실패: ${afterUrl}`);
    updateWorkflowPage(company, "finance_status", {
      status: "verified_structure_save_next",
      actions: {
        save_next: {
          selector,
          method: "click_then_confirm_layer",
          to_page: "business_plan_summary",
          status: "verified",
        },
      },
      evidence: {
        latest_save_next_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_finance_status_save_next",
      },
    });
    addStep(run, "재무현황 4단계 저장 후 다음단계 이동", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      afterUrl,
      afterTitle,
      dialogs,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function inspectBusinessPlanSummaryScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-business-plan-summary-screen-structure.png`);
    await captureScreenshot(page, company, screenshotFile, false);
    const structure = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const controls = Array.from(document.querySelectorAll("input,select,textarea,button,a"))
        .filter(visible)
        .map((el) => ({
          tag: el.tagName.toLowerCase(),
          type: el.getAttribute("type") || "",
          id: el.id || "",
          name: el.getAttribute("name") || "",
          text: norm(el.innerText || el.value || el.textContent).slice(0, 160),
          onclick: (el.getAttribute("onclick") || "").slice(0, 160),
          href: (el.getAttribute("href") || "").slice(0, 160),
        }));
      return {
        url: location.href,
        title: document.title,
        bodyHead: norm(document.body.innerText).slice(0, 1600),
        controls,
        inputs: controls.filter((control) => ["input", "textarea", "select"].includes(control.tag)),
        actions: controls.filter((control) => control.tag === "button" || control.tag === "a"),
      };
    });
    const success = /\/venturein\/aply\/v3\/bps\/viewBizPlanSmryForm/.test(structure.url);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "business_plan_summary",
      screenshotFile,
      success,
      structure,
    };
    const resultFile = applicationPath(company, "portal_run_business_plan_summary_screen_structure.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`사업계획서 요약 화면 구성 파악 실패: ${structure.url}`);
    updateWorkflowPage(
      company,
      "business_plan_summary",
      {
        step_index: 5,
        page_key: "business_plan_summary",
        page_label: "사업계획서 요약",
        status: "verified_structure",
        url_pattern: "/venturein/aply/v3/bps/viewBizPlanSmryForm",
        sections: {
          summary_text: {
            section_label: "사업계획서 요약",
            status: "verified_structure",
            input_names: structure.inputs.map((control) => control.name).filter(Boolean),
          },
        },
        actions: {
          temporary_save: {
            selector: "#btnAplyTemporarySave",
            method: "click_then_confirm_saved_layer",
            status: "observed",
          },
          save_next: {
            selector: 'a[onclick*="/venturein/aply/v3/pds/viewProblemDefinitionSolutionForm"]',
            method: "click_then_confirm_layer",
            to_page: "problem_solution",
            status: "observed_not_executed",
          },
        },
        evidence: {
          latest_structure_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_business_plan_summary_screen_structure",
        },
      },
      "business_plan_summary",
    );
    addStep(run, "사업계획서 요약 5단계 화면 구성 파악", "completed", {
      resultFile,
      screenshotFile,
      url: structure.url,
      title: structure.title,
      controlCount: structure.controls.length,
      inputCount: structure.inputs.length,
      actionCount: structure.actions.length,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

function buildBusinessPlanSummaryInputPlan(company, args) {
  const { portalInputFile, portalInput } = loadPortalInputForCompany(company, args);
  const item = valueAtPath(portalInput, "texts.business_plan_summary");
  const preparedValue = rawPortalValue(item);
  return {
    page: "business_plan_summary",
    field: {
      key: "business_plan_summary",
      label: "사업계획서 요약",
      selector: 'textarea[name="bizplanSumryCn"]',
      sourcePath: "texts.business_plan_summary",
      sourceFile: portalInputFile,
      sourceStatus: item ? item.status || "" : "missing",
      sourceLabel: item ? item.label || "" : "",
      preparedValue,
      preparedLength: preparedValue.length,
      canInputFromPreparedValue: preparedValue.trim().length > 0,
      inputMethod: "textarea_keyboard_replace",
    },
  };
}

async function fillBusinessPlanSummaryReadyField(company, session, args, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    const inputPlan = buildBusinessPlanSummaryInputPlan(company, args);
    const field = inputPlan.field;
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-fill-business-plan-summary.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    if (!field.canInputFromPreparedValue) {
      const result = {
        company,
        capturedAt: new Date().toISOString(),
        page: "business_plan_summary",
        inputPlan,
        beforeScreenshot,
        skipped: [{ key: field.key, reason: "source_value_missing_or_not_ready" }],
        results: [],
        success: true,
      };
      const resultFile = applicationPath(company, "portal_run_business_plan_summary_fill_ready.json");
      result.resultFile = resultFile;
      writeJsonAscii(resultFile, result);
      addStep(run, "사업계획서 요약 5단계 값 없음으로 입력 생략", "completed", {
        resultFile,
        skipped: result.skipped,
      });
      return result;
    }
    await page.locator(field.selector).scrollIntoViewIfNeeded();
    await page.locator(field.selector).fill(field.preparedValue);
    await page.waitForTimeout(400);
    const actualValue = await page.locator(field.selector).inputValue();
    const verified = actualValue === field.preparedValue;
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-fill-business-plan-summary.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "business_plan_summary",
      inputPlan,
      beforeScreenshot,
      afterScreenshot,
      filledKey: field.key,
      selector: field.selector,
      preparedLength: field.preparedLength,
      actualLength: actualValue.length,
      verified,
      success: verified,
    };
    const resultFile = applicationPath(company, "portal_run_business_plan_summary_fill_ready.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!verified) throw new Error("사업계획서 요약 입력값 검증 실패");
    updateWorkflowPage(company, "business_plan_summary", {
      sections: {
        summary_text: {
          fields: {
            business_plan_summary: {
              label: "사업계획서 요약",
              selector: field.selector,
              source_path: field.sourcePath,
              input_method: field.inputMethod,
              status: "verified_input",
            },
          },
        },
      },
      evidence: {
        latest_fill_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_business_plan_summary_fill_ready",
      },
    });
    addStep(run, "사업계획서 요약 5단계 값 입력 및 검증", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      filledKey: field.key,
      preparedLength: field.preparedLength,
      actualLength: actualValue.length,
      verified,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function saveBusinessPlanSummaryTemporary(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    await page.waitForTimeout(600);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-business-plan-summary-temporary.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    await page.locator("#btnAplyTemporarySave").scrollIntoViewIfNeeded();
    await page.locator("#btnAplyTemporarySave").click();
    await page.waitForTimeout(1200);
    const savedLayerFound = await waitForSavedLayer(page);
    const layerBeforeConfirm = await collectVisibleLayerItems(page);
    const layerConfirmed = await clickVisibleLayerConfirm(page);
    await page.waitForTimeout(700);
    const remainingLayerCount = (await collectVisibleLayerItems(page)).filter((item) =>
      String(item.className || "").includes("layer_pop_box"),
    ).length;
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-business-plan-summary-temporary.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success = savedLayerFound && layerConfirmed && remainingLayerCount === 0;
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "business_plan_summary",
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerBeforeConfirm,
      layerConfirmed,
      remainingLayerCount,
      success,
    };
    const resultFile = applicationPath(company, "portal_run_business_plan_summary_temporary_save.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("사업계획서 요약 임시저장 확인 처리 검증 실패");
    updateWorkflowPage(company, "business_plan_summary", {
      actions: {
        temporary_save: {
          selector: "#btnAplyTemporarySave",
          method: "click_then_wait_for_saved_layer_then_click_confirm",
          status: "verified",
        },
      },
      evidence: {
        latest_temporary_save_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_business_plan_summary_temporary_save",
      },
    });
    addStep(run, "사업계획서 요약 5단계 임시저장 및 확인 처리", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerConfirmed,
      remainingLayerCount,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function saveBusinessPlanSummaryAndGoNext(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-business-plan-summary-next.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const selector = 'a[onclick*="/venturein/aply/v3/pds/viewProblemDefinitionSolutionForm"]';
    await page.locator(selector).scrollIntoViewIfNeeded();
    await page.locator(selector).click();
    await page.waitForTimeout(1000);
    for (let attempt = 0; attempt < 5; attempt += 1) {
      const clicked = await clickVisibleLayerConfirm(page);
      if (!clicked) break;
      await page.waitForTimeout(700);
    }
    await page
      .waitForURL(/\/venturein\/aply\/v3\/pds\/viewProblemDefinitionSolutionForm/, { timeout: 15000, waitUntil: "domcontentloaded" })
      .catch(() => {});
    await page.waitForTimeout(1200);
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-business-plan-summary-next.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const afterUrl = page.url();
    const afterTitle = await page.title().catch(() => "");
    const bodyPreview = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const success = /\/venturein\/aply\/v3\/pds\/viewProblemDefinitionSolutionForm/.test(afterUrl);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      fromPage: "business_plan_summary",
      toPage: "problem_solution",
      selector,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      afterUrl,
      afterTitle,
      bodyPreview: bodyPreview.slice(0, 1000),
      success,
    };
    const resultFile = applicationPath(company, "portal_run_business_plan_summary_save_next.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`사업계획서 요약 저장 후 다음단계 이동 실패: ${afterUrl}`);
    updateWorkflowPage(company, "business_plan_summary", {
      status: "verified_input_save_next",
      actions: {
        save_next: {
          selector,
          method: "click_then_confirm_layer",
          to_page: "problem_solution",
          status: "verified",
        },
      },
      evidence: {
        latest_save_next_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_business_plan_summary_save_next",
      },
    });
    addStep(run, "사업계획서 요약 5단계 저장 후 다음단계 이동", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      afterUrl,
      afterTitle,
      dialogs,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function inspectProblemSolutionScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-problem-solution-screen-structure.png`);
    await captureScreenshot(page, company, screenshotFile, false);
    const structure = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const controls = Array.from(document.querySelectorAll("input,select,textarea,button,a"))
        .filter(visible)
        .map((el) => {
          const row = el.closest("tr");
          return {
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute("type") || "",
            id: el.id || "",
            name: el.getAttribute("name") || "",
            text: norm(el.innerText || el.value || el.textContent).slice(0, 160),
            valueLength: "value" in el ? String(el.value || "").length : null,
            rowText: row ? norm(row.innerText).slice(0, 300) : "",
            onclick: (el.getAttribute("onclick") || "").slice(0, 160),
            href: (el.getAttribute("href") || "").slice(0, 160),
          };
        });
      return {
        url: location.href,
        title: document.title,
        bodyHead: norm(document.body.innerText).slice(0, 2000),
        controls,
        inputs: controls.filter((control) => ["input", "textarea", "select"].includes(control.tag)),
        textareas: controls.filter((control) => control.tag === "textarea"),
        actions: controls.filter((control) => control.tag === "button" || control.tag === "a"),
      };
    });
    const success = /\/venturein\/aply\/v3\/pds\/viewProblemDefinitionSolutionForm/.test(structure.url);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "problem_solution",
      screenshotFile,
      success,
      structure,
    };
    const resultFile = applicationPath(company, "portal_run_problem_solution_screen_structure.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`문제정의 및 해결방안 화면 구성 파악 실패: ${structure.url}`);
    updateWorkflowPage(
      company,
      "problem_solution",
      {
        step_index: 6,
        page_key: "problem_solution",
        page_label: "문제정의 및 해결방안",
        status: "verified_structure",
        url_pattern: "/venturein/aply/v3/pds/viewProblemDefinitionSolutionForm",
        sections: {
          observed_textareas: {
            section_label: "화면 내 장문 입력 항목",
            status: "verified_structure",
            fields: structure.textareas.map((control) => ({
              name: control.name,
              value_length: control.valueLength,
              row_text: control.rowText,
            })),
          },
        },
        actions: {
          temporary_save: {
            selector: "#btnAplyTemporarySave",
            method: "click_then_confirm_saved_layer",
            status: "observed",
          },
          save_next: {
            selector: 'a[onclick*="/venturein/aply/v3/gstrtg/viewGrwtStrategyForm"]',
            method: "click_then_confirm_layer",
            to_page: "growth_strategy",
            status: "observed_not_executed",
          },
        },
        evidence: {
          latest_structure_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_problem_solution_screen_structure",
        },
      },
      "problem_solution",
    );
    addStep(run, "문제정의 및 해결방안 6단계 화면 구성 파악", "completed", {
      resultFile,
      screenshotFile,
      url: structure.url,
      title: structure.title,
      controlCount: structure.controls.length,
      inputCount: structure.inputs.length,
      textareaCount: structure.textareas.length,
      actionCount: structure.actions.length,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

function buildProblemSolutionInputPlan(company, args) {
  const { portalInputFile, portalInput } = loadPortalInputForCompany(company, args);
  const fields = [
    {
      key: "problem_background",
      label: "개발 배경(동기)와 배경의 원인",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[6].bizplanDtlclsCn"]',
      sourcePath: "texts.problem_background",
    },
    {
      key: "solution",
      label: "경쟁력 확보 방안",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[13].bizplanDtlclsCn"]',
      sourcePath: "texts.solution",
    },
    {
      key: "tech_progress",
      label: "추진 경과",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[14].bizplanDtlclsCn"]',
      sourcePath: "texts.tech_progress",
    },
    {
      key: "tech_plan",
      label: "향후 3년간 추진 계획",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[15].bizplanDtlclsCn"]',
      sourcePath: "texts.tech_plan",
    },
    {
      key: "entrepreneurship_experience",
      label: "기업가 정신을 발휘했던 경험",
      selector: 'textarea[name="rprsvList[0].etprnsExpcCn"]',
      sourcePath: "texts.entrepreneurship",
    },
  ].map((field) => {
    const item = valueAtPath(portalInput, field.sourcePath);
    const preparedValue = rawPortalValue(item);
    return {
      ...field,
      sourceFile: portalInputFile,
      sourceStatus: item ? item.status || "" : "missing",
      sourceLabel: item ? item.label || "" : "",
      preparedValue,
      preparedLength: preparedValue.length,
      canInputFromPreparedValue: preparedValue.trim().length > 0,
      inputMethod: "textarea_keyboard_replace",
    };
  });
  return {
    page: "problem_solution",
    fields,
    readyForPreparedInput: fields.filter((field) => field.canInputFromPreparedValue),
    missingRequired: fields.filter((field) => !field.canInputFromPreparedValue),
  };
}

async function fillProblemSolutionReadyFields(company, session, args, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    const inputPlan = buildProblemSolutionInputPlan(company, args);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-fill-problem-solution.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const results = [];
    for (const field of inputPlan.readyForPreparedInput) {
      await page.locator(field.selector).scrollIntoViewIfNeeded();
      await page.locator(field.selector).fill(field.preparedValue);
      await page.waitForTimeout(250);
      const actualValue = await page.locator(field.selector).inputValue();
      results.push({
        key: field.key,
        selector: field.selector,
        expectedLength: field.preparedValue.length,
        actualLength: actualValue.length,
        verified: actualValue === field.preparedValue,
      });
    }
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-fill-problem-solution.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success = results.every((item) => item.verified);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "problem_solution",
      inputPlan,
      beforeScreenshot,
      afterScreenshot,
      results,
      skipped: inputPlan.missingRequired.map((field) => ({
        key: field.key,
        reason: "source_value_missing_or_not_ready",
      })),
      success,
    };
    const resultFile = applicationPath(company, "portal_run_problem_solution_fill_ready.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("문제정의 및 해결방안 입력값 검증 실패");
    updateWorkflowPage(company, "problem_solution", {
      sections: {
        observed_textareas: {
          fields: inputPlan.fields.map((field) => ({
            key: field.key,
            label: field.label,
            selector: field.selector,
            source_path: field.sourcePath,
            input_method: field.inputMethod,
            status: "verified_input",
          })),
        },
      },
      evidence: {
        latest_fill_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_problem_solution_fill_ready",
      },
    });
    addStep(run, "문제정의 및 해결방안 6단계 값 입력 및 검증", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      filledCount: results.length,
      verifiedCount: results.filter((item) => item.verified).length,
      filledKeys: results.map((item) => item.key),
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function saveProblemSolutionTemporary(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    await page.waitForTimeout(600);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-problem-solution-temporary.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    await page.locator("#btnAplyTemporarySave").scrollIntoViewIfNeeded();
    await page.locator("#btnAplyTemporarySave").click();
    await page.waitForTimeout(1200);
    const savedLayerFound = await waitForSavedLayer(page);
    const layerBeforeConfirm = await collectVisibleLayerItems(page);
    const layerConfirmed = await clickVisibleLayerConfirm(page);
    await page.waitForTimeout(700);
    const remainingLayerCount = (await collectVisibleLayerItems(page)).filter((item) =>
      String(item.className || "").includes("layer_pop_box"),
    ).length;
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-problem-solution-temporary.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success = savedLayerFound && layerConfirmed && remainingLayerCount === 0;
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "problem_solution",
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerBeforeConfirm,
      layerConfirmed,
      remainingLayerCount,
      success,
    };
    const resultFile = applicationPath(company, "portal_run_problem_solution_temporary_save.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("문제정의 및 해결방안 임시저장 확인 처리 검증 실패");
    updateWorkflowPage(company, "problem_solution", {
      actions: {
        temporary_save: {
          selector: "#btnAplyTemporarySave",
          method: "click_then_wait_for_saved_layer_then_click_confirm",
          status: "verified",
        },
      },
      evidence: {
        latest_temporary_save_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_problem_solution_temporary_save",
      },
    });
    addStep(run, "문제정의 및 해결방안 6단계 임시저장 및 확인 처리", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerConfirmed,
      remainingLayerCount,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function inspectGrowthStrategyScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-growth-strategy-screen-structure.png`);
    await captureScreenshot(page, company, screenshotFile, false);
    const structure = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const controls = Array.from(document.querySelectorAll("input,select,textarea,button,a"))
        .filter(visible)
        .map((el) => {
          const row = el.closest("tr");
          return {
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute("type") || "",
            id: el.id || "",
            name: el.getAttribute("name") || "",
            text: norm(el.innerText || el.value || el.textContent).slice(0, 160),
            valueLength: "value" in el ? String(el.value || "").length : null,
            rowText: row ? norm(row.innerText).slice(0, 300) : "",
            onclick: (el.getAttribute("onclick") || "").slice(0, 160),
            href: (el.getAttribute("href") || "").slice(0, 160),
          };
        });
      return {
        url: location.href,
        title: document.title,
        bodyHead: norm(document.body.innerText).slice(0, 2000),
        controls,
        inputs: controls.filter((control) => ["input", "textarea", "select"].includes(control.tag)),
        textareas: controls.filter((control) => control.tag === "textarea"),
        actions: controls.filter((control) => control.tag === "button" || control.tag === "a"),
      };
    });
    const success = /\/venturein\/aply\/v3\/gstrtg\/viewGrwtStrategyForm/.test(structure.url);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "growth_strategy",
      screenshotFile,
      success,
      structure,
    };
    const resultFile = applicationPath(company, "portal_run_growth_strategy_screen_structure.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`성장전략 화면 구성 파악 실패: ${structure.url}`);
    updateWorkflowPage(
      company,
      "growth_strategy",
      {
        step_index: 7,
        page_key: "growth_strategy",
        page_label: "성장전략",
        status: "verified_structure",
        url_pattern: "/venturein/aply/v3/gstrtg/viewGrwtStrategyForm",
        sections: {
          observed_textareas: {
            section_label: "화면 내 장문 입력 항목",
            status: "verified_structure",
            fields: structure.textareas.map((control) => ({
              name: control.name,
              value_length: control.valueLength,
              row_text: control.rowText,
            })),
          },
        },
        actions: {
          temporary_save: {
            selector: "#btnAplyTemporarySave",
            method: "click_then_confirm_saved_layer",
            status: "observed",
          },
          save_next: {
            selector: 'a[onclick*="/venturein/aply/v2/atch/viewAtchForm"]',
            status: "prohibited_when_temporary_save_exists",
            prohibited_reason: "임시저장 버튼이 있는 화면에서는 저장 후 다음단계로 이동 버튼을 누르지 않는다.",
          },
        },
        evidence: {
          latest_structure_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_growth_strategy_screen_structure",
        },
      },
      "growth_strategy",
    );
    addStep(run, "성장전략 7단계 화면 구성 파악", "completed", {
      resultFile,
      screenshotFile,
      url: structure.url,
      title: structure.title,
      controlCount: structure.controls.length,
      inputCount: structure.inputs.length,
      textareaCount: structure.textareas.length,
      actionCount: structure.actions.length,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

function buildGrowthStrategyInputPlan(company, args) {
  const { portalInputFile, portalInput } = loadPortalInputForCompany(company, args);
  const fields = [
    {
      key: "target_market",
      label: "목표시장 및 고객 정의",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[0].bizplanDtlclsCn"]',
      sourcePath: "texts.target_market",
    },
    {
      key: "competition",
      label: "경쟁사 분석",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[1].bizplanDtlclsCn"]',
      sourcePath: "texts.competition",
    },
    {
      key: "market_progress",
      label: "추진경과",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[2].bizplanDtlclsCn"]',
      sourcePath: "texts.market_progress",
    },
    {
      key: "market_plan",
      label: "향후 3년간 추진 계획",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[3].bizplanDtlclsCn"]',
      sourcePath: "texts.market_plan",
    },
    {
      key: "funding_plan",
      label: "자금조달 계획의 구체적 방안",
      selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[10].bizplanDtlclsCn"]',
      sourcePath: "texts.funding_plan",
    },
  ].map((field) => {
    const item = valueAtPath(portalInput, field.sourcePath);
    const preparedValue = rawPortalValue(item);
    return {
      ...field,
      sourceFile: portalInputFile,
      sourceStatus: item ? item.status || "" : "missing",
      sourceLabel: item ? item.label || "" : "",
      preparedValue,
      preparedLength: preparedValue.length,
      canInputFromPreparedValue: preparedValue.trim().length > 0,
      inputMethod: "textarea_keyboard_replace",
    };
  });
  return {
    page: "growth_strategy",
    fields,
    readyForPreparedInput: fields.filter((field) => field.canInputFromPreparedValue),
    missingRequired: fields.filter((field) => !field.canInputFromPreparedValue),
  };
}

async function fillGrowthStrategyReadyFields(company, session, args, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    const inputPlan = buildGrowthStrategyInputPlan(company, args);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-fill-growth-strategy.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const results = [];
    for (const field of inputPlan.readyForPreparedInput) {
      await page.locator(field.selector).scrollIntoViewIfNeeded();
      await page.locator(field.selector).fill(field.preparedValue);
      await page.waitForTimeout(250);
      const actualValue = await page.locator(field.selector).inputValue();
      results.push({
        key: field.key,
        selector: field.selector,
        expectedLength: field.preparedValue.length,
        actualLength: actualValue.length,
        verified: actualValue === field.preparedValue,
      });
    }
    // ESG 자가진단: 경영 여부와 모든 세부 평가기준을 '예(Y)'로 선택(규격: 무조건 모두 예).
    // 폼은 라디오 쌍(예 value=숫자, 아니오 value="N")이며 기본 checked가 예이나, 잔류 N 방지를 위해 명시 선택한다.
    const esgResult = await page.evaluate(() => {
      const radios = Array.from(
        document.querySelectorAll('input[type="radio"][name*="bizplanDtlsDataVO"][name$="bizplanDtlclsCd"]'),
      );
      const yes = radios.filter((r) => r.value !== "N");
      for (const r of yes) {
        r.checked = true;
        r.dispatchEvent(new Event("input", { bubbles: true }));
        r.dispatchEvent(new Event("change", { bubbles: true }));
      }
      if (typeof window.setEsgTrgt === "function") window.setEsgTrgt();
      return {
        total: yes.length,
        verifiedYes: radios.filter((r) => r.value !== "N" && r.checked).length,
        remainingNo: radios.filter((r) => r.value === "N" && r.checked).length,
      };
    });
    results.push({
      key: "esg_self_check_all_yes",
      selector: 'input[type="radio"][name$="bizplanDtlclsCd"]:not([value="N"])',
      expectedLength: esgResult.total,
      actualLength: esgResult.verifiedYes,
      verified:
        esgResult.total > 0 && esgResult.verifiedYes === esgResult.total && esgResult.remainingNo === 0,
    });
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-fill-growth-strategy.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success = results.every((item) => item.verified);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "growth_strategy",
      inputPlan,
      beforeScreenshot,
      afterScreenshot,
      results,
      skipped: inputPlan.missingRequired.map((field) => ({
        key: field.key,
        reason: "source_value_missing_or_not_ready",
      })),
      success,
    };
    const resultFile = applicationPath(company, "portal_run_growth_strategy_fill_ready.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("성장전략 입력값 검증 실패");
    updateWorkflowPage(company, "growth_strategy", {
      sections: {
        observed_textareas: {
          fields: inputPlan.fields.map((field) => ({
            key: field.key,
            label: field.label,
            selector: field.selector,
            source_path: field.sourcePath,
            input_method: field.inputMethod,
            status: "verified_input",
          })),
        },
      },
      evidence: {
        latest_fill_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_growth_strategy_fill_ready",
      },
    });
    addStep(run, "성장전략 7단계 값 입력 및 검증", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      filledCount: results.length,
      verifiedCount: results.filter((item) => item.verified).length,
      filledKeys: results.map((item) => item.key),
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function saveGrowthStrategyTemporary(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    await page.waitForTimeout(600);
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-save-growth-strategy-temporary.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    await page.locator("#btnAplyTemporarySave").scrollIntoViewIfNeeded();
    await page.locator("#btnAplyTemporarySave").click();
    await page.waitForTimeout(1200);
    const savedLayerFound = await waitForSavedLayer(page);
    const layerBeforeConfirm = await collectVisibleLayerItems(page);
    const layerConfirmed = await clickVisibleLayerConfirm(page);
    await page.waitForTimeout(700);
    const remainingLayerCount = (await collectVisibleLayerItems(page)).filter((item) =>
      String(item.className || "").includes("layer_pop_box"),
    ).length;
    const afterScreenshot = path.join(dir, `${nowFileStamp()}-after-save-growth-strategy-temporary.png`);
    await captureScreenshot(page, company, afterScreenshot, false);
    const success = savedLayerFound && layerConfirmed && remainingLayerCount === 0;
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "growth_strategy",
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerBeforeConfirm,
      layerConfirmed,
      remainingLayerCount,
      success,
    };
    const resultFile = applicationPath(company, "portal_run_growth_strategy_temporary_save.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("성장전략 임시저장 확인 처리 검증 실패");
    updateWorkflowPage(company, "growth_strategy", {
      actions: {
        temporary_save: {
          selector: "#btnAplyTemporarySave",
          method: "click_then_wait_for_saved_layer_then_click_confirm",
          status: "verified",
        },
      },
      evidence: {
        latest_temporary_save_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_growth_strategy_temporary_save",
      },
    });
    addStep(run, "성장전략 7단계 임시저장 및 확인 처리", "completed", {
      resultFile,
      beforeScreenshot,
      afterScreenshot,
      dialogs,
      savedLayerFound,
      layerConfirmed,
      remainingLayerCount,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function inspectAttachmentsScreen(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    await page.waitForTimeout(800);
    const screenshotFile = path.join(dir, `${nowFileStamp()}-attachments-screen-structure.png`);
    await captureScreenshot(page, company, screenshotFile, false);
    const structure = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
      };
      const controls = Array.from(document.querySelectorAll("input,select,textarea,button,a"))
        .filter(visible)
        .map((el) => {
          const row = el.closest("tr");
          const rect = el.getBoundingClientRect();
          return {
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute("type") || "",
            id: el.id || "",
            name: el.getAttribute("name") || "",
            text: norm(el.innerText || el.value || el.textContent).slice(0, 160),
            rowText: row ? norm(row.innerText).slice(0, 500) : "",
            value: "value" in el ? String(el.value || "") : "",
            onclick: (el.getAttribute("onclick") || "").slice(0, 160),
            href: (el.getAttribute("href") || "").slice(0, 160),
            box: {
              x: Math.round(rect.x),
              y: Math.round(rect.y),
              width: Math.round(rect.width),
              height: Math.round(rect.height),
              centerX: Math.round(rect.x + rect.width / 2),
              centerY: Math.round(rect.y + rect.height / 2),
            },
          };
        });
      const slots = controls
        .filter((control) => /^APLY\d+$/.test(control.id))
        .map((control) => ({
          code: control.id,
          input_name: control.name,
          current_file: control.value,
          row_text: control.rowText,
          upload_button_selector: `#btn_${control.id}`,
          delete_button_present: controls.some((candidate) => candidate.rowText === control.rowText && candidate.text.includes("파일 삭제하기")),
        }));
      return {
        url: location.href,
        title: document.title,
        bodyHead: norm(document.body.innerText).slice(0, 2500),
        controls,
        slots,
        actions: controls.filter((control) => control.tag === "button" || control.tag === "a"),
      };
    });
    const success = /\/venturein\/aply\/v2\/atch\/viewAtchForm/.test(structure.url);
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "attachments",
      screenshotFile,
      success,
      structure,
    };
    const resultFile = applicationPath(company, "portal_run_attachments_screen_structure.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error(`첨부파일 화면 구성 파악 실패: ${structure.url}`);
    const unified = readJson(unifiedInputPathForCompany(company));
    unified.attachments = unified.attachments || {};
    unified.attachments.screen_labels = mergePlainObject(unified.attachments.screen_labels || {}, {
      label: "항목명 또는 화면 라벨",
      value: structure.slots.map((slot) => ({
        code: slot.code,
        row_text: slot.row_text,
        current_file: slot.current_file,
      })),
      status: "verified_from_portal_screen",
      source: ["portal screen: /venturein/aply/v2/atch/viewAtchForm"],
    });
    writeUnifiedInput(company, unified);
    updateWorkflowPage(
      company,
      "attachments",
      {
        step_index: 8,
        page_key: "attachments",
        page_label: "신청첨부파일",
        status: "verified_structure",
        url_pattern: "/venturein/aply/v2/atch/viewAtchForm",
        sections: {
          file_slots: {
            section_label: "첨부파일 슬롯",
            status: "verified_structure",
            fields: structure.slots,
          },
        },
        actions: {
          temporary_save: {
            selector: "#btnFileTemporarySave",
            method: "click_then_wait_for_saved_layer_then_click_confirm",
            status: "observed",
          },
          upload_button: {
            selector_pattern: "#btn_<APLY코드>",
            method: "click_upload_icon_then_browser_filechooser_set_files",
            status: "observed",
          },
        },
        evidence: {
          latest_structure_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_attachments_screen_structure",
        },
      },
      "attachments",
    );
    addStep(run, "신청첨부파일 8단계 화면 구성 파악", "completed", {
      resultFile,
      screenshotFile,
      url: structure.url,
      title: structure.title,
      slotCount: structure.slots.length,
      actionCount: structure.actions.length,
    });
    return result;
  } finally {
    // Browser remains open for the next verified step.
  }
}

function resolveAttachmentSourcePath(company, rawPath) {
  if (!rawPath) return "";
  const candidates = [
    path.resolve(rawPath),
    path.resolve(process.cwd(), rawPath),
    path.resolve(companyRoot(company), rawPath.replace(/^companies[\\/][^\\/]+[\\/]/, "")),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return candidates[1];
}

function buildAttachmentUploadPlan(company, args, structure = null) {
  const { portalInputFile, portalInput } = loadPortalInputForCompany(company, args);
  const sources = portalInput.attachments?.source_paths?.value || [];
  const slots = structure?.slots || [];
  const uploadTargets = sources
    .filter((item) => item && typeof item === "object")
    .map((item) => {
      const code = String(item.portal_code || item.code || "").trim();
      const sourcePath = resolveAttachmentSourcePath(company, item.path || item.raw || item.source_path || "");
      let sourceStatus = item.status || "needs_confirmation";
      if (item.status === "ready" && !code) sourceStatus = "missing_portal_code";
      if (item.status === "ready" && code && !fs.existsSync(sourcePath)) sourceStatus = "missing_file";
      return {
        code,
        key: item.key || "",
        label: item.label || item.document || item.key || code,
        selector: code ? `#btn_${code}` : "",
        inputSelector: code ? `#${code}` : "",
        sourcePath,
        fileName: sourcePath ? path.basename(sourcePath) : "",
        sourceStatus,
        screenSlot: slots.find((slot) => slot.code === code) || null,
        inputMethod: "click_upload_icon_then_browser_filechooser_set_files",
      };
    });
  return {
    page: "attachments",
    sourceFile: portalInputFile,
    uploadTargets,
    unmatchedSlots: slots
      .filter((slot) => !uploadTargets.some((target) => target.code === slot.code))
      .map((slot) => ({
        code: slot.code,
        row_text: slot.row_text,
        status: "no_matching_source_in_values_md",
      })),
  };
}

async function uploadVerifiedAttachments(company, session, args, attachmentsScreenStructure, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  const dialogs = [];
  const dialogHandler = async (dialog) => {
    dialogs.push({ type: dialog.type(), message: dialog.message() });
    await dialog.accept().catch(() => {});
  };
  page.on("dialog", dialogHandler);
  try {
    const inputPlan = buildAttachmentUploadPlan(company, args, attachmentsScreenStructure?.structure);
    const readyTargets = inputPlan.uploadTargets.filter((target) => target.sourceStatus === "ready");
    if (!readyTargets.length) {
      const resultFile = applicationPath(company, "portal_run_attachments_upload.json");
      const result = {
        status: "skipped",
        reason: "첨부파일 업로드 가능한 매칭 원본이 없습니다.",
        inputPlan,
        results: [],
      };
      writeJsonAscii(resultFile, result);
      addStep(run, "신청첨부파일 8단계 업로드", "skipped", { resultFile, reason: result.reason });
      return { resultFile, results: [], inputPlan, skipped: true };
    }
    const beforeScreenshot = path.join(dir, `${nowFileStamp()}-before-upload-attachments.png`);
    await captureScreenshot(page, company, beforeScreenshot, false);
    const results = [];
    for (const target of readyTargets) {
      await page.locator(target.selector).scrollIntoViewIfNeeded();
      const [fileChooser] = await Promise.all([page.waitForEvent("filechooser", { timeout: 10000 }), page.locator(target.selector).click()]);
      await fileChooser.setFiles(target.sourcePath);
      await page.waitForTimeout(2500);
      const actualValue = await page.locator(target.inputSelector).inputValue().catch(() => "");
      results.push({
        code: target.code,
        label: target.label,
        selector: target.selector,
        sourcePath: target.sourcePath,
        expectedFileName: target.fileName,
        actualValue,
        verified: actualValue.includes(target.fileName),
        inputMethod: target.inputMethod,
      });
    }
    const afterUploadScreenshot = path.join(dir, `${nowFileStamp()}-after-upload-attachments.png`);
    await captureScreenshot(page, company, afterUploadScreenshot, false);
    await page.locator("#btnFileTemporarySave").scrollIntoViewIfNeeded();
    await page.locator("#btnFileTemporarySave").click();
    await page.waitForTimeout(1200);
    const savedLayerFound = await waitForSavedLayer(page, 30000);
    const layerBeforeConfirm = await collectVisibleLayerItems(page);
    const layerConfirmed = await clickVisibleLayerConfirm(page);
    await page.waitForTimeout(1000);
    const remainingLayerCount = (await collectVisibleLayerItems(page)).filter((item) =>
      String(item.className || "").includes("layer_pop_box"),
    ).length;
    const currentFiles = await page.evaluate(() => {
      const ids = ["APLY03", "APLY06", "APLY13", "APLY15", "APLY16", "APLY66", "APLY71", "APLY72"];
      return Object.fromEntries(ids.map((id) => [id, document.getElementById(id)?.value || ""]));
    });
    const afterSaveScreenshot = path.join(dir, `${nowFileStamp()}-after-save-attachments.png`);
    await captureScreenshot(page, company, afterSaveScreenshot, false);
    const success = results.every((item) => item.verified) && savedLayerFound && layerConfirmed && remainingLayerCount === 0;
    const result = {
      company,
      capturedAt: new Date().toISOString(),
      page: "attachments",
      inputPlan,
      beforeScreenshot,
      afterUploadScreenshot,
      afterSaveScreenshot,
      dialogs,
      results,
      currentFiles,
      savedLayerFound,
      layerBeforeConfirm,
      layerConfirmed,
      remainingLayerCount,
      success,
    };
    const resultFile = applicationPath(company, "portal_run_attachments_upload.json");
    result.resultFile = resultFile;
    writeJsonAscii(resultFile, result);
    if (!success) throw new Error("첨부파일 업로드 및 임시저장 검증 실패");
    updateWorkflowPage(company, "attachments", {
      actions: {
        upload_button: {
          selector_pattern: "#btn_<APLY코드>",
          method: "click_upload_icon_then_browser_filechooser_set_files",
          status: "verified",
        },
        temporary_save: {
          selector: "#btnFileTemporarySave",
          method: "click_then_wait_for_saved_layer_then_click_confirm",
          status: "verified",
        },
      },
      sections: {
        file_slots: {
          uploaded: results.map((item) => ({
            code: item.code,
            label: item.label,
            file_name: item.expectedFileName,
            status: "verified_uploaded",
          })),
          unmatched_slots: inputPlan.unmatchedSlots,
        },
      },
      evidence: {
        latest_upload_test: "portal_run_state.json#execution_state.portal_run.artifacts.portal_run_attachments_upload",
      },
    });
    addStep(run, "신청첨부파일 8단계 파일 업로드 및 임시저장", "completed", {
      resultFile,
      beforeScreenshot,
      afterUploadScreenshot,
      afterSaveScreenshot,
      uploadedCount: results.length,
      uploadedCodes: results.map((item) => item.code),
      unmatchedSlotCount: inputPlan.unmatchedSlots.length,
      savedLayerFound,
      layerConfirmed,
      remainingLayerCount,
    });
    return result;
  } finally {
    page.off("dialog", dialogHandler);
    // Browser remains open for the next verified step.
  }
}

async function verifyApplicationFormAllControlCapabilities(company, session, run) {
  const { browser, page } = await connectSessionPage(session, company);
  const dir = experimentScreenshotDir(company);
  ensureDir(dir);
  try {
    const screenshot = path.join(dir, `${nowFileStamp()}-application-form-all-controls-capability.png`);
    await captureScreenshot(page, company, screenshot, true);
    const capability = await page.evaluate(() => {
      const norm = (value) => String(value || "").replace(/\s+/g, " ").trim();
      const textOf = (el) => norm(el.innerText || el.value || el.textContent || "");
      const boxOf = (el) => {
        const rect = el.getBoundingClientRect();
        return {
          x: Math.round(rect.x),
          y: Math.round(rect.y),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
          centerX: Math.round(rect.x + rect.width / 2),
          centerY: Math.round(rect.y + rect.height / 2),
          docY: Math.round(rect.y + window.scrollY),
        };
      };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return (
          rect.width > 0 &&
          rect.height > 0 &&
          style.visibility !== "hidden" &&
          style.display !== "none" &&
          Number(style.opacity || 1) !== 0
        );
      };
      const selectorOf = (el) => {
        if (el.id) return `#${CSS.escape(el.id)}`;
        const name = el.getAttribute("name");
        if (name) return `${el.tagName.toLowerCase()}[name="${name.replace(/"/g, '\\"')}"]`;
        const onclick = el.getAttribute("onclick");
        if (onclick) return `${el.tagName.toLowerCase()}[onclick="${onclick.replace(/"/g, '\\"')}"]`;
        return el.tagName.toLowerCase();
      };
      const titleCandidates = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6,div,p,strong,span,th"))
        .filter(visible)
        .map((el) => ({ text: textOf(el), box: boxOf(el), selector: selectorOf(el) }))
        .filter((item) => /^(\d+)\./.test(item.text))
        .sort((a, b) => a.box.docY - b.box.docY || a.box.x - b.box.x);
      const sections = [];
      for (const candidate of titleCandidates) {
        const title = candidate.text.match(/^(\d+\.[^\s]+)/)?.[0] || candidate.text;
        if (sections.some((section) => section.title === title)) continue;
        sections.push({ title, selector: candidate.selector, box: candidate.box });
      }
      const sectionFor = (docY) => {
        let current = null;
        for (const section of sections) {
          if (section.box.docY <= docY) current = section;
          else break;
        }
        return current;
      };
      const methodOf = (el) => {
        const tag = el.tagName.toLowerCase();
        const type = (el.getAttribute("type") || "").toLowerCase();
        if (tag === "select") return "select_option";
        if (tag === "button" || tag === "a") return "click_action";
        if (type === "radio") return "radio_click";
        if (type === "checkbox") return "checkbox_toggle";
        if (el.readOnly) return "readonly_control_requires_related_button_or_existing_value";
        if (tag === "textarea") return "keyboard_replace";
        return ["text", "tel", "number", "email", "url", ""].includes(type) ? "keyboard_replace" : `input_${type}`;
      };
      const controls = Array.from(document.querySelectorAll("input, textarea, select, button, a"))
        .filter(visible)
        .map((el) => {
          const row = el.closest("tr");
          const box = boxOf(el);
          const section = sectionFor(box.docY);
          const rowHeaders = row
            ? Array.from(row.querySelectorAll("th")).map((th) => norm(th.innerText)).filter(Boolean)
            : [];
          const option = el.tagName.toLowerCase() === "select" ? el.options[el.selectedIndex] : null;
          return {
            section: section ? section.title : "",
            rowLabel: rowHeaders.join(" / "),
            rowText: row ? norm(row.innerText).slice(0, 500) : "",
            tag: el.tagName.toLowerCase(),
            type: el.getAttribute("type") || "",
            id: el.id || "",
            name: el.getAttribute("name") || "",
            selector: selectorOf(el),
            text: textOf(el).slice(0, 160),
            valueLength: "value" in el ? String(el.value || "").length : null,
            selectedText: option ? option.text : "",
            checked: "checked" in el ? Boolean(el.checked) : null,
            readonly: Boolean(el.readOnly),
            disabled: Boolean(el.disabled),
            onclick: el.getAttribute("onclick") || "",
            href: el.getAttribute("href") || "",
            inputMethod: methodOf(el),
            box,
          };
        })
        .sort((a, b) => a.box.docY - b.box.docY || a.box.x - b.box.x);
      return {
        url: location.href,
        title: document.title,
        viewport: {
          width: innerWidth,
          height: innerHeight,
          scrollHeight: Math.round(document.documentElement.scrollHeight || document.body.scrollHeight),
        },
        sections,
        controls,
      };
    });
    const resultFile = applicationPath(company, "portal_run_application_form_all_controls_capability.json");
    writeJsonAscii(resultFile, {
      company,
      capturedAt: new Date().toISOString(),
      screenshot,
      ...capability,
      resultFile,
    });
    const inputControls = capability.controls.filter((control) => ["input", "textarea", "select"].includes(control.tag));
    addStep(run, "신청서 1단계 전체 입력 가능 위치 및 방식 검증", "completed", {
      resultFile,
      screenshot,
      sectionCount: capability.sections.length,
      controlCount: capability.controls.length,
      inputControlCount: inputControls.length,
      keyboardInputCount: inputControls.filter((control) => control.inputMethod === "keyboard_replace").length,
      radioCount: inputControls.filter((control) => control.inputMethod === "radio_click").length,
      checkboxCount: inputControls.filter((control) => control.inputMethod === "checkbox_toggle").length,
      readonlyCount: inputControls.filter((control) => control.inputMethod === "readonly_control_requires_related_button_or_existing_value").length,
    });
    return { ...capability, screenshot, resultFile };
  } finally {
    // Browser remains open for the next verified step.
  }
}

async function loginStep(company, args, run) {
  const debugPort = Number(args["debug-port"] || DEFAULT_DEBUG_PORT);
  const config = loadCompanyConfig(company);
  addStep(run, "회사정보 파일 확인", "completed", {
    filePath: config.filePath,
    hasSmesId: Boolean(config.smesId),
    hasSmesPw: Boolean(config.smesPw),
    smesUrl: config.smesUrl,
  });
  addStep(run, "로그인 방식 선택", "completed", {
    toolScript: "scripts/web.js",
    reason: "web.js 내부 로그인 메서드로 Chrome 실행, 로그인 판정, 세션 파일 기록을 처리",
  });

  const session = await createSmesLoginSession(company, config, args, run);

  if (session.status !== "ready" || session.targetMatch !== true) {
    throw new Error("Login session is not ready or targetMatch is not true.");
  }
  addStep(run, "로그인 결과 검증", "completed", {
    status: session.status,
    targetMatch: session.targetMatch,
    url: session.url,
    title: session.title,
    cdpUrl: session.cdpUrl,
    sessionFile: session.sessionFile,
  });

  if (!args["no-fullscreen"]) await makeFullscreen(session, run);
  return session;
}

async function main() {
  assertCliArgsNotMojibake();
  const args = parseArgs();
  const company = args.company || process.env.VENTURE_COMPANY;
  if (!company) throw new Error("Use --company <회사명>.");
  const run = createRun(company, args);
  try {
    const step = args.step || "login";
    const supportedSteps = [
      "login",
      "login-inspect",
      "close-popups",
      "click-confirmation",
      "venture-type-select",
      "venture-type-confirm",
      "application-form-input-plan",
      "application-form-fill-ready",
      "application-form-save-next",
      "application-form-capability-map",
      "company-info-input-plan",
      "company-info-fill-ready",
      "company-info-save-next",
      "representative-info-save-next",
      "finance-status-save-next",
      "business-plan-summary-save-next",
      "problem-solution-save-next",
      "attachments-upload",
    ];
    if (!supportedSteps.includes(step)) throw new Error(`Unsupported step for now: ${step}`);
    const session = await loginStep(company, args, run);
    let inspection = null;
    if (step === "login-inspect") {
      inspection = await inspectHomeScreen(company, session, run);
    }
    let popupClose = null;
    if (step === "close-popups" || step === "click-confirmation" || step === "application-form-input-plan" || step === "application-form-fill-ready" || step === "application-form-save-next" || step === "application-form-capability-map" || step === "company-info-input-plan" || step === "company-info-fill-ready" || step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      inspection = await inspectHomeScreen(company, session, run);
      if (!args["no-popup-close"]) popupClose = await closeVisiblePopups(company, session, run);
    }
    let confirmationMenu = null;
    if (step === "click-confirmation" || step === "venture-type-select" || step === "venture-type-confirm" || step === "application-form-input-plan" || step === "application-form-fill-ready" || step === "application-form-save-next" || step === "application-form-capability-map" || step === "company-info-input-plan" || step === "company-info-fill-ready" || step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      confirmationMenu = await clickConfirmationMenu(company, session, run);
    }
    let ventureTypeSelect = null;
    if (step === "venture-type-select" || step === "venture-type-confirm") {
      ventureTypeSelect = await selectVentureTypeAndFillForm(company, session, args, run);
    }
    let ventureTypeConfirm = null;
    if (step === "venture-type-confirm") {
      ventureTypeConfirm = await confirmVentureTypeSelection(company, session, run);
    }
    let applicationFormInputPlan = null;
    if (step === "application-form-input-plan" || step === "application-form-fill-ready" || step === "application-form-save-next" || step === "application-form-capability-map" || step === "company-info-input-plan" || step === "company-info-fill-ready" || step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      applicationFormInputPlan = await verifyApplicationFormInputPlan(company, session, args, run);
    }
    let applicationFormFillReady = null;
    if (step === "application-form-fill-ready" || step === "application-form-save-next" || step === "company-info-input-plan" || step === "company-info-fill-ready" || step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      applicationFormFillReady = await fillApplicationFormReadyFields(company, session, applicationFormInputPlan, run);
    }
    let applicationFormRequiredChecks = null;
    let applicationFormSaveNext = null;
    let companyInfoScreenStructure = null;
    if (step === "application-form-save-next" || step === "company-info-input-plan" || step === "company-info-fill-ready" || step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      applicationFormRequiredChecks = await confirmApplicationRequiredChecks(company, session, applicationFormInputPlan, run);
      applicationFormSaveNext = await saveApplicationFormAndGoNext(company, session, run);
      companyInfoScreenStructure = await inspectCompanyInfoScreen(company, session, run);
    }
    let companyInfoInputPlan = null;
    if (step === "company-info-input-plan" || step === "company-info-fill-ready" || step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      companyInfoInputPlan = await verifyCompanyInfoInputPlan(company, session, args, run);
    }
    let companyInfoFillReady = null;
    if (step === "company-info-fill-ready" || step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      companyInfoFillReady = await fillCompanyInfoReadyFields(company, session, companyInfoInputPlan, run);
    }
    let companyInfoTemporarySave = null;
    let companyInfoSaveNext = null;
    let representativeInfoScreenStructure = null;
    if (step === "company-info-save-next" || step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      companyInfoTemporarySave = await saveCompanyInfoTemporary(company, session, run);
      companyInfoSaveNext = await navigateDirectlyAfterTemporarySave(company, session, run, {
        fromPage: "company_info",
        toPage: "representative_info",
        pathname: "/venturein/aply/v2/rprsv/viewRprsvForm",
        urlRegex: /\/venturein\/aply\/v2\/rprsv\/viewRprsvForm/,
        resultFileName: "portal_run_company_info_direct_navigation.json",
        stepName: "기업정보 2단계 임시저장 후 대표자정보 URL 이동",
        prohibitedSelector: 'a[onclick*="/venturein/aply/v2/rprsv/viewRprsvForm"]',
      });
      representativeInfoScreenStructure = await inspectRepresentativeInfoScreen(company, session, run);
    }
    let representativeInfoButtons = null;
    let representativeInfoTemporarySave = null;
    let representativeInfoSaveNext = null;
    let financeStatusScreenStructure = null;
    if (step === "representative-info-save-next" || step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      representativeInfoButtons = await inspectRepresentativeInfoButtons(company, session, run);
      representativeInfoTemporarySave = await saveRepresentativeInfoTemporary(company, session, run);
      representativeInfoSaveNext = await navigateDirectlyAfterTemporarySave(company, session, run, {
        fromPage: "representative_info",
        toPage: "finance_status",
        pathname: "/venturein/aply/v2/fnaf/viewFnafForm",
        urlRegex: /\/venturein\/aply\/v2\/fnaf\/viewFnafForm/,
        resultFileName: "portal_run_representative_info_direct_navigation.json",
        stepName: "대표자정보 3단계 임시저장 후 재무현황 URL 이동",
        prohibitedSelector: 'a[onclick*="/venturein/aply/v2/fnaf/viewFnafForm"]',
      });
      financeStatusScreenStructure = await inspectFinanceStatusScreen(company, session, run);
    }
    let financeStatusTemporarySave = null;
    let financeStatusSaveNext = null;
    let businessPlanSummaryScreenStructure = null;
    if (step === "finance-status-save-next" || step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      financeStatusTemporarySave = await saveFinanceStatusTemporary(company, session, run);
      financeStatusSaveNext = await navigateDirectlyAfterTemporarySave(company, session, run, {
        fromPage: "finance_status",
        toPage: "business_plan_summary",
        pathname: "/venturein/aply/v3/bps/viewBizPlanSmryForm",
        urlRegex: /\/venturein\/aply\/v3\/bps\/viewBizPlanSmryForm/,
        resultFileName: "portal_run_finance_status_direct_navigation.json",
        stepName: "재무현황 4단계 임시저장 후 사업계획서 요약 URL 이동",
        prohibitedSelector: 'a[onclick*="/venturein/aply/v3/bps/viewBizPlanSmryForm"]',
      });
      businessPlanSummaryScreenStructure = await inspectBusinessPlanSummaryScreen(company, session, run);
    }
    let businessPlanSummaryFillReady = null;
    let businessPlanSummaryTemporarySave = null;
    let businessPlanSummarySaveNext = null;
    let problemSolutionScreenStructure = null;
    if (step === "business-plan-summary-save-next" || step === "problem-solution-save-next" || step === "attachments-upload") {
      businessPlanSummaryFillReady = await fillBusinessPlanSummaryReadyField(company, session, args, run);
      businessPlanSummaryTemporarySave = await saveBusinessPlanSummaryTemporary(company, session, run);
      businessPlanSummarySaveNext = await navigateDirectlyAfterTemporarySave(company, session, run, {
        fromPage: "business_plan_summary",
        toPage: "problem_solution",
        pathname: "/venturein/aply/v3/pds/viewProblemDefinitionSolutionForm",
        urlRegex: /\/venturein\/aply\/v3\/pds\/viewProblemDefinitionSolutionForm/,
        resultFileName: "portal_run_business_plan_summary_direct_navigation.json",
        stepName: "사업계획서 요약 5단계 임시저장 후 문제정의 및 해결방안 URL 이동",
        prohibitedSelector: 'a[onclick*="/venturein/aply/v3/pds/viewProblemDefinitionSolutionForm"]',
      });
      problemSolutionScreenStructure = await inspectProblemSolutionScreen(company, session, run);
    }
    let problemSolutionFillReady = null;
    let problemSolutionTemporarySave = null;
    let problemSolutionDirectNavigation = null;
    let growthStrategyScreenStructure = null;
    if (step === "problem-solution-save-next" || step === "attachments-upload") {
      problemSolutionFillReady = await fillProblemSolutionReadyFields(company, session, args, run);
      problemSolutionTemporarySave = await saveProblemSolutionTemporary(company, session, run);
      problemSolutionDirectNavigation = await navigateDirectlyAfterTemporarySave(company, session, run, {
        fromPage: "problem_solution",
        toPage: "growth_strategy",
        pathname: "/venturein/aply/v3/gstrtg/viewGrwtStrategyForm",
        urlRegex: /\/venturein\/aply\/v3\/gstrtg\/viewGrwtStrategyForm/,
        resultFileName: "portal_run_problem_solution_direct_navigation.json",
        stepName: "문제정의 및 해결방안 6단계 임시저장 후 성장전략 URL 이동",
        prohibitedSelector: 'a[onclick*="/venturein/aply/v3/gstrtg/viewGrwtStrategyForm"]',
      });
      growthStrategyScreenStructure = await inspectGrowthStrategyScreen(company, session, run);
    }
    let growthStrategyFillReady = null;
    let growthStrategyTemporarySave = null;
    let growthStrategyDirectNavigation = null;
    let attachmentsScreenStructure = null;
    let attachmentsUpload = null;
    if (step === "attachments-upload") {
      growthStrategyFillReady = await fillGrowthStrategyReadyFields(company, session, args, run);
      growthStrategyTemporarySave = await saveGrowthStrategyTemporary(company, session, run);
      growthStrategyDirectNavigation = await navigateDirectlyAfterTemporarySave(company, session, run, {
        fromPage: "growth_strategy",
        toPage: "attachments",
        pathname: "/venturein/aply/v2/atch/viewAtchForm",
        urlRegex: /\/venturein\/aply\/v2\/atch\/viewAtchForm/,
        resultFileName: "portal_run_growth_strategy_direct_navigation.json",
        stepName: "성장전략 7단계 임시저장 후 신청첨부파일 URL 이동",
        prohibitedSelector: 'a[onclick*="/venturein/aply/v2/atch/viewAtchForm"]',
      });
      attachmentsScreenStructure = await inspectAttachmentsScreen(company, session, run);
      attachmentsUpload = await uploadVerifiedAttachments(company, session, args, attachmentsScreenStructure, run);
    }
    let applicationFormCapabilityMap = null;
    if (step === "application-form-capability-map") {
      applicationFormCapabilityMap = await verifyApplicationFormAllControlCapabilities(company, session, run);
    }
    run.status = "completed";
    run.finishedAt = new Date().toISOString();
    run.result = sanitizeLog({
      sessionReady: true,
      cdpUrl: session.cdpUrl,
      targetId: session.targetId,
      url: session.url,
      title: session.title,
      sessionFile: session.sessionFile,
      browserLeftOpen: true,
      inspection: inspection
        ? {
            screenshotFile: inspection.screenshotFile,
            inspectFile: inspection.inspectFile,
            overlayCount: inspection.screen.overlays.length,
            controlCount: inspection.screen.controls.length,
          }
        : null,
      popupClose: popupClose
        ? {
            beforeScreenshot: popupClose.beforeScreenshot,
            afterScreenshot: popupClose.afterScreenshot,
            resultFile: popupClose.resultFile,
            closedCount: popupClose.closed.length,
            remainingPopupLikeCount: popupClose.verification.remainingPopupLike.length,
          }
        : null,
      confirmationMenu: confirmationMenu
        ? {
            resultFile: confirmationMenu.resultFile,
            beforeScreenshot: confirmationMenu.beforeScreenshot,
            afterScreenshot: confirmationMenu.afterScreenshot,
            clickedText: confirmationMenu.clickedTarget.text,
            urlAfter: confirmationMenu.after.url,
            titleAfter: confirmationMenu.after.title,
          }
        : null,
      applicationFormInputPlan: applicationFormInputPlan
        ? {
            resultFile: applicationPath(company, "portal_run_application_form_input_plan.json"),
            beforeScreenshot: applicationFormInputPlan.beforeScreenshot,
            totalFields: applicationFormInputPlan.fields.length,
            readyForKeyboardInputCount: applicationFormInputPlan.readyForKeyboardInput.length,
            missingRequiredCount: applicationFormInputPlan.missingRequired.length,
            notUsableSelectorCount: applicationFormInputPlan.notUsableSelectors.length,
            addressSearchRequiredCount: applicationFormInputPlan.addressSearchRequired.length,
          }
        : null,
      applicationFormFillReady: applicationFormFillReady
        ? {
            resultFile: applicationFormFillReady.resultFile,
            beforeScreenshot: applicationFormFillReady.beforeScreenshot,
            afterScreenshot: applicationFormFillReady.afterScreenshot,
            filledCount: applicationFormFillReady.filledCount,
            verifiedCount: applicationFormFillReady.verifiedCount,
            filledKeys: applicationFormFillReady.results.map((item) => item.key),
            skippedAddressPopup: applicationFormFillReady.skippedAddressPopup.map((item) => item.key),
          }
        : null,
      applicationFormRequiredChecks: applicationFormRequiredChecks
        ? {
            resultFile: applicationFormRequiredChecks.resultFile,
            beforeScreenshot: applicationFormRequiredChecks.beforeScreenshot,
            afterScreenshot: applicationFormRequiredChecks.afterScreenshot,
            checkedCount: applicationFormRequiredChecks.checkedCount,
            checkedKeys: applicationFormRequiredChecks.results.map((item) => item.key),
            dialogs: applicationFormRequiredChecks.dialogs,
          }
        : null,
      applicationFormSaveNext: applicationFormSaveNext
        ? {
            resultFile: applicationFormSaveNext.resultFile,
            beforeScreenshot: applicationFormSaveNext.beforeScreenshot,
            afterScreenshot: applicationFormSaveNext.afterScreenshot,
            afterUrl: applicationFormSaveNext.afterUrl,
            afterTitle: applicationFormSaveNext.afterTitle,
            dialogs: applicationFormSaveNext.dialogs,
          }
        : null,
      companyInfoScreenStructure: companyInfoScreenStructure
        ? {
            resultFile: companyInfoScreenStructure.resultFile,
            screenshotFile: companyInfoScreenStructure.screenshotFile,
            url: companyInfoScreenStructure.structure.url,
            title: companyInfoScreenStructure.structure.title,
            sectionCount: companyInfoScreenStructure.structure.sections.length,
            controlCount: companyInfoScreenStructure.structure.controls.length,
            inputCount: companyInfoScreenStructure.structure.inputs.length,
            actionCount: companyInfoScreenStructure.structure.actions.length,
          }
        : null,
      companyInfoInputPlan: companyInfoInputPlan
        ? {
            resultFile: companyInfoInputPlan.resultFile,
            beforeScreenshot: companyInfoInputPlan.beforeScreenshot,
            totalFields: companyInfoInputPlan.fields.length,
            readyForPreparedInputCount: companyInfoInputPlan.readyForPreparedInput.length,
            missingRequiredCount: companyInfoInputPlan.missingRequired.length,
            notUsableSelectorCount: companyInfoInputPlan.notUsableSelectors.length,
            readyKeys: companyInfoInputPlan.readyForPreparedInput.map((field) => field.key),
          }
        : null,
      companyInfoFillReady: companyInfoFillReady
        ? {
            resultFile: companyInfoFillReady.resultFile,
            beforeScreenshot: companyInfoFillReady.beforeScreenshot,
            afterScreenshot: companyInfoFillReady.afterScreenshot,
            filledCount: companyInfoFillReady.filledCount,
            verifiedCount: companyInfoFillReady.verifiedCount,
            filledKeys: companyInfoFillReady.results.map((item) => item.key),
          }
        : null,
      companyInfoTemporarySave: companyInfoTemporarySave
        ? {
            resultFile: companyInfoTemporarySave.resultFile,
            beforeScreenshot: companyInfoTemporarySave.beforeScreenshot,
            afterScreenshot: companyInfoTemporarySave.afterScreenshot,
            dialogs: companyInfoTemporarySave.dialogs,
            layerConfirmed: companyInfoTemporarySave.layerConfirmed,
            remainingLayerCount: companyInfoTemporarySave.remainingLayerCount,
          }
        : null,
      companyInfoSaveNext: companyInfoSaveNext
        ? {
            resultFile: companyInfoSaveNext.resultFile,
            beforeScreenshot: companyInfoSaveNext.beforeScreenshot,
            afterScreenshot: companyInfoSaveNext.afterScreenshot,
            method: companyInfoSaveNext.method,
            targetUrl: companyInfoSaveNext.targetUrl,
            afterUrl: companyInfoSaveNext.afterUrl,
            afterTitle: companyInfoSaveNext.afterTitle,
            prohibitedAction: companyInfoSaveNext.prohibitedAction,
            dialogs: companyInfoSaveNext.dialogs,
          }
        : null,
      representativeInfoScreenStructure: representativeInfoScreenStructure
        ? {
            resultFile: representativeInfoScreenStructure.resultFile,
            screenshotFile: representativeInfoScreenStructure.screenshotFile,
            url: representativeInfoScreenStructure.structure.url,
            title: representativeInfoScreenStructure.structure.title,
            controlCount: representativeInfoScreenStructure.structure.controls.length,
            inputCount: representativeInfoScreenStructure.structure.inputs.length,
            actionCount: representativeInfoScreenStructure.structure.actions.length,
          }
        : null,
      representativeInfoButtons: representativeInfoButtons
        ? {
            resultFile: representativeInfoButtons.resultFile,
            beforeScreenshot: representativeInfoButtons.beforeScreenshot,
            addScreenshot: representativeInfoButtons.addScreenshot,
            updateScreenshot: representativeInfoButtons.updateScreenshot,
            addInputCount: representativeInfoButtons.addModal.inputCount,
            updateInputCount: representativeInfoButtons.updateModal.inputCount,
            updatePrefilledKeys: representativeInfoButtons.updateModal.prefilledKeys,
          }
        : null,
      representativeInfoTemporarySave: representativeInfoTemporarySave
        ? {
            resultFile: representativeInfoTemporarySave.resultFile,
            beforeScreenshot: representativeInfoTemporarySave.beforeScreenshot,
            afterScreenshot: representativeInfoTemporarySave.afterScreenshot,
            dialogs: representativeInfoTemporarySave.dialogs,
            savedLayerFound: representativeInfoTemporarySave.savedLayerFound,
            layerConfirmed: representativeInfoTemporarySave.layerConfirmed,
            remainingLayerCount: representativeInfoTemporarySave.remainingLayerCount,
          }
        : null,
      representativeInfoSaveNext: representativeInfoSaveNext
        ? {
            resultFile: representativeInfoSaveNext.resultFile,
            beforeScreenshot: representativeInfoSaveNext.beforeScreenshot,
            afterScreenshot: representativeInfoSaveNext.afterScreenshot,
            method: representativeInfoSaveNext.method,
            targetUrl: representativeInfoSaveNext.targetUrl,
            afterUrl: representativeInfoSaveNext.afterUrl,
            afterTitle: representativeInfoSaveNext.afterTitle,
            prohibitedAction: representativeInfoSaveNext.prohibitedAction,
            dialogs: representativeInfoSaveNext.dialogs,
          }
        : null,
      financeStatusScreenStructure: financeStatusScreenStructure
        ? {
            resultFile: financeStatusScreenStructure.resultFile,
            screenshotFile: financeStatusScreenStructure.screenshotFile,
            url: financeStatusScreenStructure.structure.url,
            title: financeStatusScreenStructure.structure.title,
            controlCount: financeStatusScreenStructure.structure.controls.length,
            inputCount: financeStatusScreenStructure.structure.inputs.length,
            actionCount: financeStatusScreenStructure.structure.actions.length,
          }
        : null,
      financeStatusTemporarySave: financeStatusTemporarySave
        ? {
            resultFile: financeStatusTemporarySave.resultFile,
            beforeScreenshot: financeStatusTemporarySave.beforeScreenshot,
            afterScreenshot: financeStatusTemporarySave.afterScreenshot,
            dialogs: financeStatusTemporarySave.dialogs,
            savedLayerFound: financeStatusTemporarySave.savedLayerFound,
            layerConfirmed: financeStatusTemporarySave.layerConfirmed,
            remainingLayerCount: financeStatusTemporarySave.remainingLayerCount,
          }
        : null,
      financeStatusSaveNext: financeStatusSaveNext
        ? {
            resultFile: financeStatusSaveNext.resultFile,
            beforeScreenshot: financeStatusSaveNext.beforeScreenshot,
            afterScreenshot: financeStatusSaveNext.afterScreenshot,
            method: financeStatusSaveNext.method,
            targetUrl: financeStatusSaveNext.targetUrl,
            afterUrl: financeStatusSaveNext.afterUrl,
            afterTitle: financeStatusSaveNext.afterTitle,
            prohibitedAction: financeStatusSaveNext.prohibitedAction,
            dialogs: financeStatusSaveNext.dialogs,
          }
        : null,
      businessPlanSummaryScreenStructure: businessPlanSummaryScreenStructure
        ? {
            resultFile: businessPlanSummaryScreenStructure.resultFile,
            screenshotFile: businessPlanSummaryScreenStructure.screenshotFile,
            url: businessPlanSummaryScreenStructure.structure.url,
            title: businessPlanSummaryScreenStructure.structure.title,
            controlCount: businessPlanSummaryScreenStructure.structure.controls.length,
            inputCount: businessPlanSummaryScreenStructure.structure.inputs.length,
            actionCount: businessPlanSummaryScreenStructure.structure.actions.length,
          }
        : null,
      businessPlanSummaryFillReady: businessPlanSummaryFillReady
        ? {
            resultFile: businessPlanSummaryFillReady.resultFile,
            beforeScreenshot: businessPlanSummaryFillReady.beforeScreenshot,
            afterScreenshot: businessPlanSummaryFillReady.afterScreenshot,
            filledKey: businessPlanSummaryFillReady.filledKey,
            preparedLength: businessPlanSummaryFillReady.preparedLength,
            actualLength: businessPlanSummaryFillReady.actualLength,
            verified: businessPlanSummaryFillReady.verified,
          }
        : null,
      businessPlanSummaryTemporarySave: businessPlanSummaryTemporarySave
        ? {
            resultFile: businessPlanSummaryTemporarySave.resultFile,
            beforeScreenshot: businessPlanSummaryTemporarySave.beforeScreenshot,
            afterScreenshot: businessPlanSummaryTemporarySave.afterScreenshot,
            dialogs: businessPlanSummaryTemporarySave.dialogs,
            savedLayerFound: businessPlanSummaryTemporarySave.savedLayerFound,
            layerConfirmed: businessPlanSummaryTemporarySave.layerConfirmed,
            remainingLayerCount: businessPlanSummaryTemporarySave.remainingLayerCount,
          }
        : null,
      businessPlanSummarySaveNext: businessPlanSummarySaveNext
        ? {
            resultFile: businessPlanSummarySaveNext.resultFile,
            beforeScreenshot: businessPlanSummarySaveNext.beforeScreenshot,
            afterScreenshot: businessPlanSummarySaveNext.afterScreenshot,
            method: businessPlanSummarySaveNext.method,
            targetUrl: businessPlanSummarySaveNext.targetUrl,
            afterUrl: businessPlanSummarySaveNext.afterUrl,
            afterTitle: businessPlanSummarySaveNext.afterTitle,
            prohibitedAction: businessPlanSummarySaveNext.prohibitedAction,
            dialogs: businessPlanSummarySaveNext.dialogs,
          }
        : null,
      problemSolutionScreenStructure: problemSolutionScreenStructure
        ? {
            resultFile: problemSolutionScreenStructure.resultFile,
            screenshotFile: problemSolutionScreenStructure.screenshotFile,
            url: problemSolutionScreenStructure.structure.url,
            title: problemSolutionScreenStructure.structure.title,
            controlCount: problemSolutionScreenStructure.structure.controls.length,
            inputCount: problemSolutionScreenStructure.structure.inputs.length,
            textareaCount: problemSolutionScreenStructure.structure.textareas.length,
            actionCount: problemSolutionScreenStructure.structure.actions.length,
          }
        : null,
      problemSolutionFillReady: problemSolutionFillReady
        ? {
            resultFile: problemSolutionFillReady.resultFile,
            beforeScreenshot: problemSolutionFillReady.beforeScreenshot,
            afterScreenshot: problemSolutionFillReady.afterScreenshot,
            filledCount: problemSolutionFillReady.results.length,
            verifiedCount: problemSolutionFillReady.results.filter((item) => item.verified).length,
            filledKeys: problemSolutionFillReady.results.map((item) => item.key),
          }
        : null,
      problemSolutionTemporarySave: problemSolutionTemporarySave
        ? {
            resultFile: problemSolutionTemporarySave.resultFile,
            beforeScreenshot: problemSolutionTemporarySave.beforeScreenshot,
            afterScreenshot: problemSolutionTemporarySave.afterScreenshot,
            dialogs: problemSolutionTemporarySave.dialogs,
            savedLayerFound: problemSolutionTemporarySave.savedLayerFound,
            layerConfirmed: problemSolutionTemporarySave.layerConfirmed,
            remainingLayerCount: problemSolutionTemporarySave.remainingLayerCount,
          }
        : null,
      problemSolutionDirectNavigation: problemSolutionDirectNavigation
        ? {
            resultFile: problemSolutionDirectNavigation.resultFile,
            beforeScreenshot: problemSolutionDirectNavigation.beforeScreenshot,
            afterScreenshot: problemSolutionDirectNavigation.afterScreenshot,
            method: problemSolutionDirectNavigation.method,
            targetUrl: problemSolutionDirectNavigation.targetUrl,
            afterUrl: problemSolutionDirectNavigation.afterUrl,
            afterTitle: problemSolutionDirectNavigation.afterTitle,
            prohibitedAction: problemSolutionDirectNavigation.prohibitedAction,
          }
        : null,
      growthStrategyScreenStructure: growthStrategyScreenStructure
        ? {
            resultFile: growthStrategyScreenStructure.resultFile,
            screenshotFile: growthStrategyScreenStructure.screenshotFile,
            url: growthStrategyScreenStructure.structure.url,
            title: growthStrategyScreenStructure.structure.title,
            controlCount: growthStrategyScreenStructure.structure.controls.length,
            inputCount: growthStrategyScreenStructure.structure.inputs.length,
            textareaCount: growthStrategyScreenStructure.structure.textareas.length,
            actionCount: growthStrategyScreenStructure.structure.actions.length,
          }
        : null,
      growthStrategyFillReady: growthStrategyFillReady
        ? {
            resultFile: growthStrategyFillReady.resultFile,
            beforeScreenshot: growthStrategyFillReady.beforeScreenshot,
            afterScreenshot: growthStrategyFillReady.afterScreenshot,
            filledCount: growthStrategyFillReady.results.length,
            verifiedCount: growthStrategyFillReady.results.filter((item) => item.verified).length,
            filledKeys: growthStrategyFillReady.results.map((item) => item.key),
          }
        : null,
      growthStrategyTemporarySave: growthStrategyTemporarySave
        ? {
            resultFile: growthStrategyTemporarySave.resultFile,
            beforeScreenshot: growthStrategyTemporarySave.beforeScreenshot,
            afterScreenshot: growthStrategyTemporarySave.afterScreenshot,
            dialogs: growthStrategyTemporarySave.dialogs,
            savedLayerFound: growthStrategyTemporarySave.savedLayerFound,
            layerConfirmed: growthStrategyTemporarySave.layerConfirmed,
            remainingLayerCount: growthStrategyTemporarySave.remainingLayerCount,
          }
        : null,
      growthStrategyDirectNavigation: growthStrategyDirectNavigation
        ? {
            resultFile: growthStrategyDirectNavigation.resultFile,
            beforeScreenshot: growthStrategyDirectNavigation.beforeScreenshot,
            afterScreenshot: growthStrategyDirectNavigation.afterScreenshot,
            method: growthStrategyDirectNavigation.method,
            targetUrl: growthStrategyDirectNavigation.targetUrl,
            afterUrl: growthStrategyDirectNavigation.afterUrl,
            afterTitle: growthStrategyDirectNavigation.afterTitle,
            prohibitedAction: growthStrategyDirectNavigation.prohibitedAction,
          }
        : null,
      attachmentsScreenStructure: attachmentsScreenStructure
        ? {
            resultFile: attachmentsScreenStructure.resultFile,
            screenshotFile: attachmentsScreenStructure.screenshotFile,
            url: attachmentsScreenStructure.structure.url,
            title: attachmentsScreenStructure.structure.title,
            slotCount: attachmentsScreenStructure.structure.slots.length,
            actionCount: attachmentsScreenStructure.structure.actions.length,
          }
        : null,
      attachmentsUpload: attachmentsUpload
        ? {
            resultFile: attachmentsUpload.resultFile,
            beforeScreenshot: attachmentsUpload.beforeScreenshot,
            afterUploadScreenshot: attachmentsUpload.afterUploadScreenshot,
            afterSaveScreenshot: attachmentsUpload.afterSaveScreenshot,
            uploadedCount: attachmentsUpload.results.length,
            uploadedCodes: attachmentsUpload.results.map((item) => item.code),
            savedLayerFound: attachmentsUpload.savedLayerFound,
            layerConfirmed: attachmentsUpload.layerConfirmed,
            remainingLayerCount: attachmentsUpload.remainingLayerCount,
          }
        : null,
      applicationFormCapabilityMap: applicationFormCapabilityMap
        ? {
            resultFile: applicationFormCapabilityMap.resultFile,
            screenshot: applicationFormCapabilityMap.screenshot,
            sectionCount: applicationFormCapabilityMap.sections.length,
            controlCount: applicationFormCapabilityMap.controls.length,
          }
        : null,
    });
    const files = persistRun(company, run);
    process.stdout.write(
      `${stringifyPowerShellSafeJson({
        status: "completed",
        company,
        step,
        browserLeftOpen: true,
        logFiles: files,
        session: run.result,
      }, 2)}\n`,
    );
    process.exit(0);
  } catch (error) {
    run.status = "failed";
    run.finishedAt = new Date().toISOString();
    run.error = error.message;
    const files = persistRun(company, run);
    process.stderr.write(
      `${stringifyPowerShellSafeJson({
        status: "failed",
        company,
        message: error.message,
        logFiles: files,
      }, 2)}\n`,
    );
    process.exit(1);
  }
}

if (require.main === module) {
  main();
} else {
  module.exports = {
    buildApplicationFormInputPlan,
    buildBusinessPlanSummaryInputPlan,
    buildCompanyInfoInputPlan,
    buildGrowthStrategyInputPlan,
    buildProblemSolutionInputPlan,
    loadPortalInputForCompany,
    parseValuesMarkdown,
    readValuesMarkdownAsPortalInput,
    valueAtPath,
    valuesMarkdownToPortalInput,
  };
}



