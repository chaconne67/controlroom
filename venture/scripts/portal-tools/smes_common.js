const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const SMES_BASE = 'https://www.smes.go.kr';
const DEFAULT_CDP = 'http://127.0.0.1:9331';

function parseArgs(argv = process.argv.slice(2)) {
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) continue;
    const key = a.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) args[key] = true;
    else { args[key] = next; i++; }
  }
  return args;
}

function requireArg(args, name) {
  if (!args[name]) throw new Error(`Missing required --${name}`);
  return args[name];
}

function normalizeWinPath(p) {
  if (!p) return p;
  return p.replace(/^\/mnt\/([a-z])\//, (_, d) => `${d.toUpperCase()}:/`).replace(/\\/g, '/');
}

function cleanMarkdownFile(filePath, maxLen) {
  let s = fs.readFileSync(filePath, 'utf8').replace(/^\uFEFF/, '');
  s = s
    .replace(/^---[\s\S]*?---\s*/, '')
    .replace(/^#.*$/gm, '')
    .replace(/\r/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  if (maxLen && s.length > maxLen) s = s.slice(0, maxLen).trim();
  return s;
}

async function connect(cdpUrl = DEFAULT_CDP) {
  return chromium.connectOverCDP(cdpUrl);
}

async function getSmesPage(browser, preferredUrlPart = '') {
  const pages = browser.contexts().flatMap(c => c.pages());
  if (preferredUrlPart) {
    const hit = pages.filter(p => p.url().includes(preferredUrlPart)).pop();
    if (hit) return hit;
  }
  return pages.filter(p => p.url().includes('smes.go.kr')).pop() || pages[0];
}

async function gotoSmes(page, pathOrUrl) {
  const url = pathOrUrl.startsWith('http') ? pathOrUrl : SMES_BASE + pathOrUrl;
  await page.goto(url);
  await page.waitForLoadState('domcontentloaded').catch(() => {});
  await page.waitForTimeout(1200);
  if (page.url().includes('/auth/viewLogin') || page.url().includes('/auth/viewExpiredSession')) {
    throw new Error(`SMES session is not active. Current URL: ${page.url()}`);
  }
}

async function closeCustomAlert(page) {
  await page.evaluate(() => {
    const ok = [...document.querySelectorAll('a,button')]
      .find(e => (e.innerText || '').trim() === '확인');
    if (ok) ok.click();
  }).catch(() => {});
}

async function saveTemporary(page) {
  const dialogs = [];
  const handler = async d => { dialogs.push(d.message()); await d.accept().catch(() => {}); };
  page.on('dialog', handler);
  let saved = null;
  try {
    saved = await page.evaluate(async () => {
      if (typeof window.aplySavePromise === 'function') {
        await window.aplySavePromise('Y');
        return 'aplySavePromise';
      }
      if (typeof window.doSave === 'function') {
        window.doSave();
        return 'doSave';
      }
      return null;
    });
  } catch (e) {
    // Some portal saves navigate/reload and destroy the JS context after the save request.
    saved = `context-destroyed-or-eval-error: ${String(e).slice(0, 160)}`;
  }
  await page.waitForTimeout(2500);
  await closeCustomAlert(page);
  await page.waitForTimeout(800);
  page.off('dialog', handler);
  return { saved, dialogs };
}

async function clickSaveNext(page) {
  const dialogs = [];
  const handler = async d => { dialogs.push(d.message()); await d.accept().catch(() => {}); };
  page.on('dialog', handler);
  const next = page.locator('a[onclick*="doNext"]').last();
  if (await next.count()) await next.click({ force: true });
  else await page.locator('#btnAplyTemporarySave, a[onclick="doSave();"]').first().click({ force: true });
  await page.waitForLoadState('domcontentloaded').catch(() => {});
  await page.waitForTimeout(2500);
  page.off('dialog', handler);
  return dialogs;
}

async function visibleTextareaSummary(page) {
  return page.evaluate(() => {
    const visible = (el) => {
      let n = el;
      while (n) {
        const s = getComputedStyle(n);
        if (s.display === 'none' || s.visibility === 'hidden') return false;
        n = n.parentElement;
      }
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    };
    return [...document.querySelectorAll('textarea')].map((ta, i) => ({
      i,
      visible: visible(ta),
      title: ta.title || ta.name,
      name: ta.name,
      id: ta.id,
      maxLength: ta.maxLength,
      len: (ta.value || '').length,
      empty: !(ta.value || '').trim(),
      preview: (ta.value || '').replace(/\s+/g, ' ').slice(0, 180),
    })).filter(x => x.visible);
  });
}

async function setValues(page, mappings) {
  return page.evaluate(({ mappings }) => {
    const fire = el => ['input', 'change', 'keyup', 'blur'].forEach(t => el.dispatchEvent(new Event(t, { bubbles: true })));
    const out = [];
    for (const item of mappings) {
      const el = document.querySelector(item.selector);
      if (!el) { out.push({ selector: item.selector, ok: false, reason: 'missing' }); continue; }
      if (el.type === 'checkbox' || el.type === 'radio') el.checked = !!item.value;
      else el.value = item.value == null ? '' : String(item.value);
      fire(el);
      out.push({ selector: item.selector, ok: true, title: el.title || el.name || el.id, len: (el.value || '').length, preview: (el.value || '').replace(/\s+/g, ' ').slice(0, 120) });
    }
    return out;
  }, { mappings });
}

function applicationUrls(vniaSn) {
  return {
    doc: `/venturein/aply/v2/doc/viewDocForm?vniaSn=${vniaSn}&menuId=5000170`,
    company: `/venturein/aply/v2/cmp/viewCmpForm?vniaSn=${vniaSn}&menuId=5000170`,
    representative: `/venturein/aply/v2/rprsv/viewRprsvForm?vniaSn=${vniaSn}&menuId=5000170`,
    finance: `/venturein/aply/v2/fnaf/viewFnafForm?vniaSn=${vniaSn}&menuId=5000170`,
    summary: `/venturein/aply/v3/bps/viewBizPlanSmryForm?vniaSn=${vniaSn}&menuId=5000170`,
    pds: `/venturein/aply/v3/pds/viewProblemDefinitionSolutionForm?vniaSn=${vniaSn}&menuId=5000170`,
    growth: `/venturein/aply/v3/gstrtg/viewGrwtStrategyForm?vniaSn=${vniaSn}&menuId=5000170`,
    attachments: `/venturein/aply/v2/atch/viewAtchForm?vniaSn=${vniaSn}&menuId=5000170`,
  };
}

function ensureDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

module.exports = {
  SMES_BASE,
  DEFAULT_CDP,
  parseArgs,
  requireArg,
  normalizeWinPath,
  cleanMarkdownFile,
  connect,
  getSmesPage,
  gotoSmes,
  closeCustomAlert,
  saveTemporary,
  clickSaveNext,
  visibleTextareaSummary,
  setValues,
  applicationUrls,
  ensureDir,
};
