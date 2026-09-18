#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const {
  parseArgs, requireArg, connect, getSmesPage, gotoSmes, applicationUrls,
  visibleTextareaSummary, ensureDir,
} = require('./smes_common');

async function main() {
  const args = parseArgs();
  const cdp = args.cdp || 'http://127.0.0.1:9331';
  const vniaSn = args.vnia;
  const pageKey = args.page;
  const out = args.out;

  const browser = await connect(cdp);
  const page = await getSmesPage(browser);

  if (vniaSn && pageKey) {
    const urls = applicationUrls(vniaSn);
    if (!urls[pageKey]) throw new Error(`Unknown --page ${pageKey}. Use one of: ${Object.keys(urls).join(', ')}`);
    await gotoSmes(page, urls[pageKey]);
  } else if (args.url) {
    await gotoSmes(page, args.url);
  }

  const data = await page.evaluate(() => {
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
    const controls = [...document.querySelectorAll('input,select,textarea,a,button')].map((el, i) => ({
      i,
      tag: el.tagName,
      type: el.type || '',
      id: el.id || '',
      name: el.name || '',
      title: el.title || '',
      text: (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 160),
      value: el.type === 'password' ? '' : (el.value || ''),
      checked: !!el.checked,
      selectedIndex: el.selectedIndex,
      visible: visible(el),
      onclick: el.getAttribute('onclick'),
      className: String(el.className || ''),
      data: Object.fromEntries(Object.entries(el.dataset || {})),
    }));
    const files = Object.fromEntries(['APLY03','APLY06','APLY08','APLY12','APLY13','APLY15','APLY16','APLY66','APLY71','APLY72'].map(id => {
      const e = document.getElementById(id);
      return [id, e ? { value: e.value || '', fileGrpSn: e.dataset.filegrpsn || '', fileSno: e.dataset.filesno || '', required: e.dataset.requiredYn || '' } : null];
    }));
    return {
      url: location.href,
      title: document.title,
      bodyPreview: (document.body.innerText || '').replace(/\s+/g, ' ').slice(0, 2000),
      visibleTextareas: controls.filter(c => c.tag === 'TEXTAREA' && c.visible).map(c => ({ title: c.title || c.name, name: c.name, id: c.id, len: c.value.length, empty: !c.value.trim(), preview: c.value.replace(/\s+/g, ' ').slice(0, 180) })),
      files,
      controls,
    };
  });

  if (out) { ensureDir(out); fs.writeFileSync(out, JSON.stringify(data, null, 2)); }
  console.log(JSON.stringify({ out: out || null, url: data.url, title: data.title, visibleTextareas: data.visibleTextareas, files: Object.fromEntries(Object.entries(data.files).filter(([,v]) => v && v.value)) }, null, 2));
  await browser.close();
}

main().catch(e => { console.error(e); process.exit(1); });
