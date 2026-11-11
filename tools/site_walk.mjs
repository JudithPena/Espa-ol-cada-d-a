#!/usr/bin/env node
// Проход уроков сайта в настоящем браузере (Playwright, Chromium): каждый шаг урока на ширинах 320, 390 и 430 px.
//   python -m espanol site --preview && node tools/site_walk.mjs --unit 1 [--mistakes] [--noaudio] [--shots DIR]
//   node tools/site_walk.mjs saludos/dialogue saludos/practice
// Ученик отвечает верно; с --mistakes на каждом задании сначала ошибается (повтор, источник, подсказка);
// с --noaudio нажимает «Нет возможности слушать». Проверяется: нет ошибок JS, нет горизонтальной прокрутки,
// урок доходит до экрана результата. Записей звука при локальной сборке нет — это и есть проверка «без звука».
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');   // Playwright стоит глобально (NODE_PATH), ESM его так не видит
import http from 'node:http';
import path from 'node:path';
import fs from 'node:fs';

const args = process.argv.slice(2);
const flag = f => args.includes(f);
const val = f => { const k = args.indexOf(f); return k >= 0 ? args[k + 1] : null; };
const widths = (val('--widths') || '320,390,430').split(',').map(Number);
const shots = val('--shots');
// Split JSON cannot be fetched from file://. Serve the same directory as Pages.
const root = path.resolve('site');
const server = http.createServer((req, res) => {
  const filename = path.resolve(root, '.' + decodeURIComponent(req.url.split('?')[0] === '/' ? '/index.html' : req.url.split('?')[0]));
  if (!filename.startsWith(root + path.sep)) { res.writeHead(403); res.end(); return; }
  fs.readFile(filename, (error, data) => {
    if (error) { res.writeHead(404); res.end(); return; }
    res.setHeader('Content-Type', filename.endsWith('.json') ? 'application/json' : filename.endsWith('.html') ? 'text/html; charset=utf-8' : filename.endsWith('.webp') ? 'image/webp' : 'application/octet-stream');
    res.end(data);
  });
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const page0 = `http://127.0.0.1:${server.address().port}/`;
const browser = await chromium.launch();
let failures = 0;

async function lessonIds(page) {
  const unit = val('--unit');
  const ids = args.filter((a, k) => !a.startsWith('--') && !['--unit', '--widths', '--shots'].includes(args[k - 1]));
  if (unit == null) return ids;
  return page.evaluate(u => LESSONS.filter(L => L.unit === +u).map(L => L.id), unit);
}

// Один шаг: ответить так, как ответил бы ученик (верно; с mistakes — сначала ошибиться).
async function act(page, mistakes) {
  return page.evaluate(async (mistakes) => {
    if (S.kind === 'result') return 'result';
    const st = S.steps[S.at], s = S.state, click = sel => { const el = document.querySelector(sel); if (!el) throw new Error('нет ' + sel); el.click(); };
    if (s?.result) { click('[data-next]'); return 'next'; }
    const listenOff = document.querySelector('.listen.off [data-noaudio]');
    if (listenOff) { listenOff.click(); return 'noaudio'; }
    switch (st.type) {
      case 'intro': case 'word': case 'theory': case 'task': case 'deferred': click('[data-primary]'); return st.type;
      case 'mc': {
        if (mistakes && !st.retry && !s.tried) { s.tried = true; click(`[data-opt="${(st.correct + 1) % st.options.length}"]`); return 'mc-wrong'; }
        click(`[data-opt="${st.correct}"]`); return 'mc';
      }
      case 'write': {
        const f = document.querySelector('#wans');
        const put = v => { f.value = v; f.dispatchEvent(new Event('input', { bubbles: true })); };
        if (mistakes && !s.tries && !st.retry) { put('xxx'); click('[data-primary]'); return 'write-wrong'; }
        put(st.a[0]); click('[data-primary]'); return 'write';
      }
      case 'match': {
        const k = [...Array(st.pairs.length).keys()].find(k => !s.done.includes(k));
        if (mistakes && !s.err && st.pairs.length > 1) { const o = [...Array(st.pairs.length).keys()].find(j => j !== k && !s.done.includes(j));
          if (o != null) { click(`[data-m="l:${k}"]`); click(`[data-m="r:${o}"]`); return 'match-wrong'; } }
        click(`[data-m="l:${k}"]`); click(`[data-m="r:${k}"]`); return 'match';
      }
      case 'sort': {
        const want = s.order[s.k][1];
        if (mistakes && !s.err && st.groups.length > 1) { click(`[data-sg="${(want + 1) % st.groups.length}"]`); return 'sort-wrong'; }
        click(`[data-sg="${want}"]`); return 'sort';
      }
      case 'build': {
        const want = (s.cands || [st.es.split(' ')])[0][s.n], key = t => String(t).toLowerCase().replace(/^[¿¡"«]+|[.,;:!?"»…]+$/g, '');
        if (mistakes && !s.err) { const bad = s.tiles.findIndex((t, j) => !s.used[j] && key(t) !== key(want)); if (bad >= 0) { click(`[data-pick="${bad}"]`); return 'build-wrong'; } }
        click(`[data-pick="${s.tiles.findIndex((t, j) => !s.used[j] && key(t) === key(want))}"]`); return 'build';
      }
      case 'mf': {
        const f = document.querySelector('#letter');
        const tok = st.es.split(' ')[s.n];
        const ch = tok.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/^[^a-z0-9]+/, '').charAt(0);
        f.value = ch; f.dispatchEvent(new Event('input', { bubbles: true })); return 'mf';
      }
    }
    throw new Error('неизвестный шаг ' + st.type);
  }, mistakes);
}

for (const width of widths) {
  const page = await browser.newPage({ viewport: { width, height: 760 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error' && !/a\/[0-9a-f]+\.mp3|ERR_FILE_NOT_FOUND|net::/.test(m.text())) errors.push(m.text()); });
  await page.goto(page0);
  await page.waitForFunction(() => !COURSE.resources || dataLoaded.has(COURSE.resources.common.url));
  await page.evaluate(() => { P.openAll = true; P.sound = false; P.autoDlg = false; });
  for (const id of await lessonIds(page)) {
    const i = await page.evaluate(id => LESSONS.findIndex(L => L.id === id), id);
    if (i < 0) { console.log(`✗ нет урока ${id}`); failures++; continue; }
    await page.evaluate(i => startLesson(i), i);
    await page.waitForFunction(() => !!S);
    if (flag('--noaudio')) await page.evaluate(() => { S.noAudio = true; enterStep(); });
    let n = 0, wide = 0, last = '';
    for (; n < 400; n++) {
      const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (over > 1) wide++;
      if (shots && n < 60) { fs.mkdirSync(shots, { recursive: true }); await page.screenshot({ path: path.join(shots, `${id.replace('/', '_')}-${width}-${String(n).padStart(2, '0')}.png`) }); }
      try { last = await act(page, flag('--mistakes')); } catch (e) { errors.push(`${id} шаг ${n}: ${e.message}`); break; }
      if (last === 'result') break;
    }
    const res = await page.evaluate(() => S?.kind === 'result' ? { passed: S.passed, graded: S.graded, acc: S.acc, noaudio: S.noaudio } : null);
    const ok = res && !errors.length && !wide;
    if (!ok) failures++;
    console.log(`${ok ? '✓' : '✗'} ${width}px ${id}: ${n} действий, ${res ? `итог: ${res.passed ? 'засчитан' : 'не засчитан'}, оценено ${res.graded}, с первой попытки ${Math.round(res.acc * 100)} %${res.noaudio ? `, без звука ${res.noaudio}` : ''}` : 'не дошёл до итога'}${wide ? `, горизонтальная прокрутка на ${wide} шагах` : ''}`);
    errors.splice(0).forEach(e => console.log('   ошибка:', e));
    await page.evaluate(() => { S = null; render(); });
  }
  await page.close();
}
await browser.close();
await new Promise(resolve => server.close(resolve));
process.exit(failures ? 1 : 0);
