#!/usr/bin/env node
// Шаги урока так, как их строит движок страницы: для карт слайдов (docs/site_slide_maps) и аудита.
//   node tools/site_steps.cjs saludos/vocab1 [--done] [--json]   — один урок
//   node tools/site_steps.cjs --unit 1 [--done]                     — все уроки темы
// --done — все предыдущие уроки пройдены (как у ученика, который идёт по порядку); навыки ещё не повторялись.
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
  if (flag('--refs')) {   // ручная проверка ссылок: задание → источник, правило (id или тип блока), навык
    console.log(`${id}:`);
    console.log(run(`S.steps.filter(s => ["mc", "write", "match", "sort", "build", "mf"].includes(s.type)).map(s => {
      const L = LESSONS[s.li] || LESSONS[S.li], q = String(s.q || s.es || s.title || (s.pairs ? s.pairs.map(p => p[0]).join(", ") : "") || s.word?.es || "").replace(/<[^>]*>/g, "").slice(0, 60);
      const src = s.src != null ? (L.blocks[s.src].id || L.blocks[s.src].t) : s.free ? "free" : s.ctx ? "ctx" : "—";
      const rule = (s.rule || []).map(k => L.blocks[k].id || L.blocks[k].t).join("+") || "—";
      return "  " + stepSig(s).padEnd(6) + " " + q.padEnd(60) + " src=" + src + " rule=" + rule + " skill=" + ((s.skill || []).join(",") || "—");
    }).join("\\n")`));
    continue;
  }
  if (flag('--json')) {
    console.log(run(`JSON.stringify({id: LESSONS[${i}].id, steps: S.steps.map(s => ({sig: stepSig(s), title: s.title || "", q: String(s.q || s.ru || s.word?.es || "").replace(/<[^>]*>/g, "").slice(0, 80), text: s.type === "theory" ? s.blocks.map(b => JSON.stringify(b).replace(/<[^>]*>/g, "").length).reduce((a, b) => a + b, 0) : 0}))})`));
  } else {
    console.log(`${id}: ${run('signature(S.steps)')}`);
  }
}
