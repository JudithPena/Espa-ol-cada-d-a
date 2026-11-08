#!/usr/bin/env node
// Шаги урока так, как их строит движок страницы: для карт слайдов (docs/site_slide_maps) и аудита.
//   node tools/site_steps.cjs saludos/vocab1 [--done] [--json]   — один урок
//   node tools/site_steps.cjs --unit 1 [--done]                     — все уроки темы
// --done — все предыдущие уроки пройдены (как у ученика, который идёт по порядку).
const {SIG_CODE, siteData, context} = require('./site_vm.cjs');

const args = process.argv.slice(2);
const flag = f => args.includes(f);
const unitAt = args.indexOf('--unit');
const ids = args.filter((a, k) => !a.startsWith('--') && (unitAt < 0 || k !== unitAt + 1));
const data = siteData();
const run = context(data);

run(SIG_CODE);

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
