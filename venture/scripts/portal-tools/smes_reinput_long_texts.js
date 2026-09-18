#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const {
  parseArgs, requireArg, normalizeWinPath, cleanMarkdownFile, connect, getSmesPage,
  gotoSmes, saveTemporary, visibleTextareaSummary, setValues, applicationUrls, ensureDir,
} = require('./smes_common');

const TEXT_FILES = {
  summary: 'texts/business_plan_summary.md',
  pds: [
    'texts/problem_background.md',
    'texts/solution.md',
    'texts/tech_progress.md',
    'texts/tech_plan.md',
    'texts/entrepreneurship.md',
  ],
  growth: [
    'texts/target_market.md',
    'texts/competition.md',
    'texts/market_progress.md',
    'texts/market_plan.md',
    'texts/funding_plan.md',
  ],
};

function companyDir(root, company) {
  return path.join(root, 'companies', company);
}

function readTexts(base) {
  return {
    summary: cleanMarkdownFile(path.join(base, TEXT_FILES.summary), 3900),
    pds: TEXT_FILES.pds.map(f => cleanMarkdownFile(path.join(base, f), 990)),
    growth: TEXT_FILES.growth.map(f => cleanMarkdownFile(path.join(base, f), 990)),
  };
}

async function fillPage(page, url, mappings) {
  await gotoSmes(page, url);
  const filled = await setValues(page, mappings);
  const save = await saveTemporary(page);
  await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => {});
  await page.waitForTimeout(1200);
  const verify = await visibleTextareaSummary(page);
  return { filled, save, verify };
}

async function main() {
  const args = parseArgs();
  const root = normalizeWinPath(args.root || 'C:/Users/chaconne/Desktop/venture');
  const company = requireArg(args, 'company');
  const vniaSn = requireArg(args, 'vnia');
  const cdp = args.cdp || 'http://127.0.0.1:9331';
  const pagesArg = args.pages || 'summary,pds,growth';
  const out = args.out || path.join(root, '.venture-sessions', 'portal-runs', company, 'long_texts_reinput_verify.json');

  const base = companyDir(root, company);
  const texts = readTexts(base);
  const browser = await connect(cdp);
  const page = await getSmesPage(browser);
  const urls = applicationUrls(vniaSn);
  const result = { at: new Date().toISOString(), company, vniaSn, textLengths: { summary: texts.summary.length, pds: texts.pds.map(x => x.length), growth: texts.growth.map(x => x.length) }, steps: [] };

  const wanted = new Set(pagesArg.split(',').map(x => x.trim()).filter(Boolean));

  if (wanted.has('summary')) {
    result.steps.push({
      page: '사업계획서 요약',
      ...(await fillPage(page, urls.summary, [
        { selector: 'textarea[name="bizplanSumryCn"], textarea[id="bizplanSumryCn"]', value: texts.summary },
      ])),
    });
  }

  if (wanted.has('pds')) {
    result.steps.push({
      page: '문제정의 및 해결방안',
      ...(await fillPage(page, urls.pds, [
        { selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[6].bizplanDtlclsCn"]', value: texts.pds[0] },
        { selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[13].bizplanDtlclsCn"]', value: texts.pds[1] },
        { selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[14].bizplanDtlclsCn"]', value: texts.pds[2] },
        { selector: 'textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[15].bizplanDtlclsCn"]', value: texts.pds[3] },
        { selector: 'textarea[name="rprsvList[0].etprnsExpcCn"]', value: texts.pds[4] },
      ])),
    });
  }

  if (wanted.has('growth')) {
    result.steps.push({
      page: '성장전략',
      ...(await fillPage(page, urls.growth, [
        { selector: 'textarea[id="4001"], textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[0].bizplanDtlclsCn"]', value: texts.growth[0] },
        { selector: 'textarea[id="5001"], textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[1].bizplanDtlclsCn"]', value: texts.growth[1] },
        { selector: 'textarea[id="6001"], textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[2].bizplanDtlclsCn"]', value: texts.growth[2] },
        { selector: 'textarea[id="6002"], textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[3].bizplanDtlclsCn"]', value: texts.growth[3] },
        { selector: 'textarea[id="7006"], textarea[name="bizplanDvsnDtlsInfo.bizplanDtlsDataVO[10].bizplanDtlclsCn"]', value: texts.growth[4] },
      ])),
    });
  }

  ensureDir(out);
  fs.writeFileSync(out, JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ out, summary: result.steps.map(s => ({ page: s.page, save: s.save, verify: s.verify.map(v => ({ title: v.title, len: v.len, empty: v.empty, preview: v.preview })) })) }, null, 2));
  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
