#!/usr/bin/env node
// Шаги урока так, как их строит движок страницы: для карт слайдов (docs/site_slide_maps) и аудита.
//   node tools/site_steps.cjs saludos/vocab1 [--done] [--json]   — один урок
//   node tools/site_steps.cjs --unit 1 [--done]                     — все уроки темы
// --done — все предыдущие уроки пройдены (как у ученика, который идёт по порядку).
const {siteData, context} = require('./site_vm.cjs');

const args = process.argv.slice(2);
const flag = f => args.includes(f);
const unitAt = args.indexOf('--unit');
const ids = args.filter((a, k) => !a.startsWith('--') && (unitAt < 0 || k !== unitAt + 1));
const data = siteData();
const run = context(data);

// Сигнатура шага: T(блоки) — экран объяснения, W — карточка слова, C — выбор, I — ввод, M — пары, S — группы,
// B — сборка фразы, F — «Мастер фраз», Q — тест, V — вопрос на слово; @id — источник, ~ — на слух, R: — повторение.
run(`function stepSig(st) {
  const pre = st.recall || st.review ? "R:" : "";
  const src = st.srcId ? "@" + st.srcId : st.src != null ? "@" + st.src : "";
  const ear = st.say ? "~" : "";
  switch (st.type) {
    case "intro": return "intro" + (st.lead && st.lead.length ? "(" + st.lead.map(b => b.t).join("+") + ")" : "");
    case "theory": return "T(" + st.blocks.map(b => b.t).join("+") + ")";
    case "word": return "W";
    case "write": return pre + "I" + ear + src;
    case "match": return pre + "M";
    case "sort": return pre + "S";
    case "build": return pre + "B";
    case "mf": return pre + "F";
    case "mc": return pre + (st.mode === "quiz" ? "Q" : st.mode === "choose" ? "C" : "V") + ear + src;
  }
  return st.type;
}
function signature(steps) {
  const out = [];
  for (const t of steps.map(stepSig)) {
    const last = out[out.length - 1];
    if (last && last[0] === t) last[1]++; else out.push([t, 1]);
  }
  return out.map(([t, n]) => n > 1 ? t + "×" + n : t).join(" ");
}`);

const lessons = unitAt >= 0 ? data.lessons.filter(L => L.unit === +args[unitAt + 1]).map(L => L.id) : ids;
for (const id of lessons) {
  const i = run(`LESSONS.findIndex(L => L.id === ${JSON.stringify(id)})`);
  if (i < 0) { console.error(`нет урока ${id}`); process.exitCode = 1; continue; }
  run(`P = fresh(); ${flag('--done') ? `LESSONS.slice(0, ${i}).forEach(L => { P.done[L.id] = {stars: 3, acc: 100, at: "2026-11-01"}; });` : ''} startLesson(${i})`);
  if (flag('--json')) {
    console.log(run(`JSON.stringify({id: LESSONS[${i}].id, steps: S.steps.map(s => ({sig: stepSig(s), title: s.title || "", q: String(s.q || s.ru || s.word?.es || "").replace(/<[^>]*>/g, "").slice(0, 80), text: s.type === "theory" ? s.blocks.map(b => JSON.stringify(b).replace(/<[^>]*>/g, "").length).reduce((a, b) => a + b, 0) : 0}))})`));
  } else {
    console.log(`${id}: ${run('signature(S.steps)')}`);
  }
}
