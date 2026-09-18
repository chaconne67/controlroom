#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const {
  parseArgs, requireArg, normalizeWinPath, connect, getSmesPage, gotoSmes,
  applicationUrls, closeCustomAlert, ensureDir,
} = require('./smes_common');

const DEFAULT_CODES = ['APLY03','APLY06','APLY08','APLY12','APLY13'];

function readMapping(file) {
  const json = JSON.parse(fs.readFileSync(file, 'utf8'));
  if (Array.isArray(json)) return json;
  if (Array.isArray(json.files)) return json.files;
  throw new Error('Mapping JSON must be an array or { files: [...] }');
}

async function uploadBase64(page, items) {
  return page.evaluate(async ({ items }) => {
    const uploadID = window.G_APLY_ATCH_UPLOADER_ID || 'APLY_ATCH_FILE';
    if (!window.RAONKUPLOAD || !window.RAONKUPLOAD.CustomHandler || !window.RAONKUPLOAD.CustomHandler[uploadID]) {
      throw new Error('RAONK uploader not found on this page');
    }
    const addResults = [];
    for (const it of items) {
      window.RAONKUPLOAD.CustomHandler[uploadID].selectedId = it.code + '|' + it.code;
      const before = window.RAONKUPLOAD.GetTotalFileCount(uploadID);
      window.RAONKUPLOAD.AddBase64Data(it.dataUri, it.filename, uploadID);
      await new Promise(r => setTimeout(r, 700));
      const after = window.RAONKUPLOAD.GetTotalFileCount(uploadID);
      addResults.push({ code: it.code, filename: it.filename, before, after });
    }
    return { uploadID, addResults, beforeSave: window.RAONKUPLOAD.GetListInfo('json', uploadID) };
  }, { items });
}

async function saveAttachment(page) {
  const dialogs = [];
  const handler = async d => { dialogs.push(d.message()); await d.accept().catch(() => {}); };
  page.on('dialog', handler);
  const saved = await page.evaluate(() => {
    if (typeof window.doAtchFileSave !== 'function') throw new Error('doAtchFileSave not found');
    window.doAtchFileSave('SAVE');
    return 'doAtchFileSave(SAVE)';
  }).catch(e => `eval-error: ${String(e).slice(0,160)}`);
  await page.waitForTimeout(70000);
  await closeCustomAlert(page);
  await page.reload({ waitUntil: 'domcontentloaded' }).catch(() => {});
  await page.waitForTimeout(1500);
  page.off('dialog', handler);
  return { saved, dialogs };
}

async function verifyAttachment(page, codes) {
  return page.evaluate(({ codes }) => {
    const uploadID = window.G_APLY_ATCH_UPLOADER_ID || 'APLY_ATCH_FILE';
    let list = null;
    try { list = window.RAONKUPLOAD && window.RAONKUPLOAD.GetListInfo('json', uploadID); } catch (e) { list = String(e); }
    return {
      uploadID,
      list,
      inputs: Object.fromEntries(codes.map(id => {
        const e = document.getElementById(id);
        return [id, e ? { value: e.value || '', fileGrpSn: e.dataset.filegrpsn || '', fileSno: e.dataset.filesno || '', required: e.dataset.requiredYn || '' } : null];
      })),
    };
  }, { codes });
}

async function main() {
  const args = parseArgs();
  const vniaSn = requireArg(args, 'vnia');
  const cdp = args.cdp || 'http://127.0.0.1:9331';
  const mappingFile = args.mapping;
  const out = args.out || `attachment_upload_verify_${vniaSn}.json`;
  let items;

  if (mappingFile) {
    items = readMapping(normalizeWinPath(mappingFile));
  } else {
    const file = requireArg(args, 'file');
    items = DEFAULT_CODES.map(code => ({ code, file, filename: `${code}_${path.basename(file)}` }));
  }

  items = items.map(it => {
    const file = normalizeWinPath(it.file);
    const dataUri = 'data:application/pdf;base64,' + fs.readFileSync(file).toString('base64');
    return { code: it.code, filename: it.filename || path.basename(file), dataUri };
  });

  const browser = await connect(cdp);
  const page = await getSmesPage(browser);
  await gotoSmes(page, applicationUrls(vniaSn).attachments);
  const add = await uploadBase64(page, items);
  const save = await saveAttachment(page);
  const verify = await verifyAttachment(page, [...new Set([...items.map(i => i.code), 'APLY03','APLY06','APLY08','APLY12','APLY13','APLY15','APLY16','APLY66','APLY71','APLY72'])]);
  const result = { at: new Date().toISOString(), vniaSn, add, save, verify };
  ensureDir(out);
  fs.writeFileSync(out, JSON.stringify(result, null, 2));
  console.log(JSON.stringify({ out, saved: save, inputs: Object.fromEntries(Object.entries(verify.inputs).filter(([,v]) => v && v.value)) }, null, 2));
  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
