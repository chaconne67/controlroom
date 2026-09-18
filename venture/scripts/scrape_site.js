// 홈페이지 렌더링 스크래퍼.
// 정적 fetch로는 JS로 주입되는 네비게이션 링크를 발견하지 못하므로,
// Playwright로 렌더링한 뒤 메인 페이지와 주요 하위 페이지의 본문을 추출한다.
//
// 사용법:
//   node scripts/scrape_site.js --url https://example.com/ [--out path.md] [--max 12] [--timeout 20000]
// 출력: Markdown(메인 본문 + 하위 페이지 섹션). --out 지정 시 파일로 저장.

const fs = require("fs");
const path = require("path");
const Module = require("module");

const DEFAULT_NODE_MODULE_PATH =
  "C:/Users/chaconne/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/.pnpm/node_modules";
const DEFAULT_MAX_SUBPAGES = 12;
const DEFAULT_TIMEOUT_MS = 20000;

// 하위 페이지 우선순위 키워드. 앵커 텍스트 또는 URL 경로에 포함되면 가산점.
const SUBPAGE_KEYWORDS = [
  "사업", "제품", "서비스", "기술", "솔루션", "회사", "소개", "연혁", "사업영역", "특허",
  "heritage", "about", "company", "business", "product", "service", "tech", "history", "press",
];
// 제외 패턴(동작용 링크, 파일 다운로드, 외부 채널).
const SKIP_PATTERNS = [
  "mailto:", "tel:", "javascript:", "#none",
  ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".zip", ".hwp", ".doc", ".xls",
  "facebook.com", "instagram.com", "youtube.com", "youtu.be", "blog.naver",
];

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

function selectSubpages(baseUrl, links, maxSubpages) {
  const base = new URL(baseUrl);
  const seen = new Set([base.href.replace(/\/$/, "")]);
  const scored = [];
  for (const { href, text } of links) {
    if (!href) continue;
    const lowered = href.toLowerCase();
    if (SKIP_PATTERNS.some((pattern) => lowered.includes(pattern))) continue;
    let absolute;
    try {
      absolute = new URL(href, base);
    } catch (error) {
      continue;
    }
    if (!/^https?:$/.test(absolute.protocol)) continue;
    if (absolute.host !== base.host) continue;
    absolute.hash = "";
    const normalized = absolute.href.replace(/\/$/, "");
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    const haystack = `${text || ""} ${absolute.pathname}`.toLowerCase();
    const score = SUBPAGE_KEYWORDS.reduce(
      (acc, keyword) => (haystack.includes(keyword.toLowerCase()) ? acc + 1 : acc),
      0,
    );
    scored.push({ score, url: normalized, anchor: (text || "").trim() });
  }
  scored.sort((a, b) => b.score - a.score);
  const positive = scored.filter((item) => item.score > 0);
  const chosen = positive.length > 0 ? positive : scored;
  return chosen.slice(0, maxSubpages);
}

async function extractPage(page, url, timeout) {
  await page.goto(url, { waitUntil: "load", timeout });
  // JS로 주입되는 네비게이션·본문이 채워질 시간을 준다.
  await page.waitForTimeout(1500).catch(() => {});
  return page.evaluate(() => {
    const links = Array.from(document.querySelectorAll("a[href]")).map((a) => ({
      href: a.getAttribute("href"),
      text: (a.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60),
    }));
    const text = (document.body ? document.body.innerText : "").replace(/\n{3,}/g, "\n\n").trim();
    return { links, text };
  });
}

function renderMarkdown(url, main, subpages) {
  let body = `# 홈페이지(렌더링)\n\n## 메타\n\n- homepage_url: ${url}\n- status: ready\n- extraction_method: playwright_rendered\n- subpage_count: ${subpages.length}\n- char_count: ${main.text.length}\n\n## 추출 텍스트\n\n${main.text}\n`;
  for (const sub of subpages) {
    body += `\n## 하위 페이지: ${sub.title}\n\n- url: ${sub.url}\n- char_count: ${sub.text.length}\n\n${sub.text}\n`;
  }
  return body;
}

async function main() {
  const args = parseArgs();
  const url = args.url;
  if (!url || url === true) {
    process.stderr.write("--url 인자가 필요합니다.\n");
    process.exit(2);
  }
  const maxSubpages = Number(args.max || DEFAULT_MAX_SUBPAGES);
  const timeout = Number(args.timeout || DEFAULT_TIMEOUT_MS);

  const { chromium } = requirePlaywrightCore();
  const browser = await chromium.launch({ headless: true, executablePath: chromePath() });
  try {
    const context = await browser.newContext({ userAgent: "Mozilla/5.0" });
    const page = await context.newPage();

    const main = await extractPage(page, url, timeout);
    const candidates = selectSubpages(url, main.links, maxSubpages);

    const subpages = [];
    for (const candidate of candidates) {
      try {
        const result = await extractPage(page, candidate.url, timeout);
        if (!result.text) continue;
        subpages.push({
          url: candidate.url,
          title: candidate.anchor || new URL(candidate.url).pathname || candidate.url,
          text: result.text,
        });
      } catch (error) {
        // 개별 하위 페이지 실패는 건너뛴다(메인 추출은 보존).
      }
    }

    const markdown = renderMarkdown(url, main, subpages);
    if (args.out && args.out !== true) {
      fs.mkdirSync(path.dirname(args.out), { recursive: true });
      fs.writeFileSync(args.out, markdown, "utf8");
      process.stdout.write(`saved: ${args.out} (subpages: ${subpages.length})\n`);
    } else {
      process.stdout.write(markdown);
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  process.stderr.write(`scrape_site failed: ${error.message}\n`);
  process.exit(1);
});
