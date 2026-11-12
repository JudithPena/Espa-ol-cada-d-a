#!/usr/bin/env node
// Карта экранов темы (docs/site_slide_maps/NN_тема.md), собранная из сценария уроков так, как их строит движок.
//   node tools/site_map_gen.cjs --unit 24            — напечатать карту
//   node tools/site_map_gen.cjs --unit 24 --write    — записать docs/site_slide_maps/24_<id>.md
// Для уровня A2 порядок шагов проектируется в docs/a2_c2_curriculum_map.md и docs/a2_pilot_blueprint.md, а карта
// фиксирует то, что получилось: шаги, длину, новую лексику и «Сигнатуру» (её сверяет tests/site_course.test.cjs).
// Карты A0–A1 написаны вручную до правки уроков — этим инструментом их не перезаписываем.
const fs = require('node:fs');
const path = require('node:path');
const {ROOT, SIG_CODE, siteData, context} = require('./site_vm.cjs');

const args = process.argv.slice(2);
const unit = +args[args.indexOf('--unit') + 1];
if (!args.includes('--unit') || Number.isNaN(unit)) { console.error('нужен --unit N'); process.exit(1); }
const data = siteData();
const U = data.units.find(u => u.number === unit);
if (!U) { console.error(`нет темы ${unit}`); process.exit(1); }
if (U.level === 'A0' || U.level === 'A1') { console.error('карты A0–A1 написаны вручную: инструмент только для A2 и выше'); process.exit(1); }
const run = context(data);
run(SIG_CODE);

const strip = s => String(s ?? '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').replace(/\|/g, '/').trim();
const cut = (s, n = 90) => { s = strip(s); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
const SECONDS = {theory: 30, word: 15, mc: 20, write: 35, build: 30, match: 40, sort: 40, mf: 40, compose: 90, chatlog: 30};
const KIND = {mc: 'выбор', write: 'ввод', build: 'сборка', compose: 'письмо'};

function describe(st, L) {
  const src = st.src != null ? `\`${L.blocks[st.src]?.id || st.src}\`` : '—';
  if (st.type === 'theory') {
    const types = st.blocks.map(b => b.t).join(' + ');
    const first = st.blocks.map(b => b.title || b.html || (b.lines ? b.lines[0][3] : '') || (b.cards ? b.cards.map(c => strip(c.head)).join(' · ') : '') || (b.items ? b.items.map(x => Array.isArray(x) ? x[2] : '').join(' ') : '')).find(x => strip(x));
    return [`T: ${types}`, cut(first), '—'];
  }
  if (st.type === 'word') return ['W', `новое слово: ${strip(st.word.es)} — ${cut(st.word.ru, 40)}`, '—'];
  if (st.type === 'chatlog') return ['HL: лента разговора', `весь разговор «${strip(st.chat.title)}»${st.end.length ? `; ${st.chat.who}: ${cut(st.end[0][3], 50)}` : ''}`, '—'];
  if (st.chat) {
    const what = st.type === 'mc' ? `выбрать: ${cut(st.plain[st.correct], 40)}` : st.type === 'write' ? `написать: ${cut(st.a[0], 40)}`
      : st.type === 'build' ? `собрать: ${cut(st.es, 40)}` : `ответить от себя; образец: ${cut(st.sample, 40)}`;
    return [`H: ход разговора (${KIND[st.type]})`, `${st.chat.who}: ${cut(st.line[3], 50)} → ${what}`, '—'];
  }
  if (st.type === 'mc') {
    const ear = st.say ? `на слух «${cut(st.say, 40)}»` : cut(st.q || (st.lines || []).map(l => l[3]).join(' '), 60);
    return [st.mode === 'quiz' ? 'Q: тест' : st.say ? 'C~: выбор на слух' : 'C: выбор', `${ear} → ${cut(st.plain ? st.plain[st.correct] : st.options[st.correct], 40)}`, src];
  }
  if (st.type === 'write') return [st.say ? 'I~: диктант' : 'I: ввод', `${st.say ? `на слух «${cut(st.say, 40)}»` : cut(st.q, 60)} → ${cut(st.a[0], 40)}`, src];
  if (st.type === 'build') return ['B: сборка', cut(st.es, 70), src];
  if (st.type === 'match') return ['M: пары', `${cut(st.title, 30)}: ${st.pairs.length} пар (${cut(st.pairs[0][0], 25)} — ${cut(st.pairs[0][1], 25)}…)`, src];
  if (st.type === 'sort') return ['S: группы', `${cut(st.title, 30)}: ${st.groups.map(g => strip(g[0])).join(' / ')}`, src];
  if (st.type === 'compose') return ['O: письмо по признакам', `${cut(st.q, 60)}; образец: ${cut(st.sample, 40)}`, src];
  if (st.type === 'mf') return ['F: мастер фраз', cut(st.es, 60), '—'];
  return [st.type, '', '—'];
}

let out = `# Тема ${U.number} «${U.title}» · ${U.level} — карта экранов\n\n`;
out += `Цели темы: ${U.goals.join('; ')}.\n\n`;
out += 'Карта собрана из сценария уроков (`node tools/site_map_gen.cjs --unit ' + U.number + ' --write`): для A2 порядок шагов\n' +
  'проектируется в `docs/a2_c2_curriculum_map.md` (первая тема — в `docs/a2_pilot_blueprint.md`), карта фиксирует результат.\n' +
  'Обозначения — `docs/site_slide_maps/README.md`.\n';
for (const meta of data.lessons.filter(L => L.unit === unit)) {
  const i = run(`LESSONS.findIndex(L => L.id === ${JSON.stringify(meta.id)})`);
  run(`P = fresh(); LESSONS.slice(0, ${i}).forEach(L => { P.done[L.id] = {stars: 3, acc: 100, at: "2026-11-01"}; }); startLesson(${i})`);
  const sig = run('signature(S.steps)');
  const steps = JSON.parse(run(`JSON.stringify(S.steps.map(st => ({...st, word: st.word && {es: st.word.es, ru: st.word.ru}, blocks: st.blocks && st.blocks.map(b => ({t: b.t, title: b.title, html: b.html, lines: b.lines, cards: b.cards && b.cards.map(c => ({head: c.head})), items: b.t === "examples" ? b.items : undefined}))})))`));
  const L = data.lessons[i];
  const secs = steps.reduce((a, st) => a + (st.type === 'theory' ? (st.blocks.some(b => b.t === 'reading') ? 100 : st.blocks.some(b => b.t === 'dialogue') ? 70 : 30)
    : st.type === 'compose' ? ((st.words && st.words[0] >= 20) ? 240 : st.chat || (st.words && st.words[1] <= 16) ? 40 : 75) : st.type === 'write' ? (String(st.a[0]).includes(' ') ? 40 : 20) : SECONDS[st.type] || 20) + (st.chat ? 10 : 0), 0);
  const count = t => steps.filter(st => st.type === t).length;
  const listen = steps.filter(st => st.say || (st.chat && st.line)).length;
  const parts = [['выбор', count('mc')], ['ввод', count('write')], ['сборка', count('build')], ['пары', count('match')], ['группы', count('sort')], ['письмо', count('compose')]]
    .filter(p => p[1]).map(p => `${p[0]} ${p[1]}`).join(', ');
  out += `\n## Урок \`${L.id}\` — «${L.title}»\n\n`;
  out += `- **Цель:** ${L.goal || '—'}.\n`;
  out += `- **Длина:** ${steps.length} ${steps.length % 10 === 1 && steps.length % 100 !== 11 ? 'шаг' : [2, 3, 4].includes(steps.length % 10) && ![12, 13, 14].includes(steps.length % 100) ? 'шага' : 'шагов'}, около ${Math.max(1, Math.round(secs / 60))} минут. **Новая лексика:** ${L.words.length ? L.words.map(w => strip(w.es)).join(', ') : 'нет'}.\n`;
  out += `- **Интерактив:** ${parts || '—'}; на слух и с голосом собеседника — ${listen}. **Самостоятельное воспроизведение:** ввод, сборка и письмо — ${count('write') + count('build') + count('compose')} заданий.\n\n`;
  out += '| Шаг | Экран / тип блока | Что видит или делает ученик | Источник |\n|---|---|---|---|\n';
  steps.forEach((st, k) => { const [type, text, src] = describe(st, L); out += `| ${k + 1} | ${type} | ${text} | ${src} |\n`; });
  out += `\nСигнатура: \`${sig}\`\n`;
}

if (args.includes('--write')) {
  const id = data.lessons.find(L => L.unit === unit).id.split('/')[0];
  const file = path.join(ROOT, 'docs/site_slide_maps', `${String(unit).padStart(2, '0')}_${id}.md`);
  fs.writeFileSync(file, out);
  console.log(`записано: ${path.relative(ROOT, file)}`);
} else process.stdout.write(out);
