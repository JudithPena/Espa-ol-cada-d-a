/* Пошаговый урок грамматики. Данные и проверка ответов общие с остальным сайтом. */
let G = null;
let gAutoTimer = null;
function gCancelAuto() { clearTimeout(gAutoTimer); gAutoTimer = null; }
function gQueueAuto() {
  gCancelAuto();
  if (!G || G.ended || G.review) return;
  const step = G.steps[G.at], response = gResponse(step);
  if (!response?.checked) return;
  const session = G, at = G.at;
  gAutoTimer = setTimeout(() => {
    gAutoTimer = null;
    if (G === session && G.at === at && !G.review) gMove(1);
  }, response.good ? 1500 : 3000);
}
const G_SESSION_KEY = "espanol-cada-dia.grammar-session.v1";
const gUnit = () => (COURSE.grammar || []).find(u => u.id === G?.unit);
const gGroups = u => [...u.sections.map(s => s.check).filter(Boolean), ...u.exercises];
const gRoutes = u => [...u.sections.map((_, i) => `section:${i}`), "summary", ...u.exercises.map(g => `exercise:${g.id}`)];
function gRouteDone(unit, route) {
  const group = route.startsWith("section:") ? unit.sections[+route.split(":")[1]]?.check : unit.exercises.find(g => route === `exercise:${g.id}`);
  return group ? !!P.grammar?.[grammarKey(unit, group)] : !!P.grammarRead?.[`${unit.id}/${route}`];
}
function gRouteOpen(unit, route) {
  if (route === "all") return true;
  const routes = gRoutes(unit), index = routes.indexOf(route);
  return index >= 0 && routes.slice(0,index).every(r => gRouteDone(unit,r));
}
function gStepRoute(unit, step) {
  if (step.type === "theory") return `section:${step.section}`;
  if (step.type === "summary") return "summary";
  const index = unit.sections.findIndex(s => s.check?.id === step.group);
  return index >= 0 ? `section:${index}` : `exercise:${step.group}`;
}
function gSaved() { try { return JSON.parse(store.get(G_SESSION_KEY) || "null"); } catch (_) { return null; } }
function gSave() { if (G) store.set(G_SESSION_KEY, JSON.stringify(G)); }
function gSteps(unit, route = "all") {
  const steps = [];
  unit.sections.forEach((s, i) => {
    if (route !== "all" && route !== `section:${i}`) return;
    steps.push({type:"theory", section:i});
    s.check?.questions.forEach((_, qi) => steps.push({type:"question", group:s.check.id, qi}));
  });
  if (["all", "summary"].includes(route)) steps.push({type:"summary"});
  unit.exercises.forEach(g => {
    if (route !== "all" && route !== `exercise:${g.id}`) return;
    steps.push({type:"intro", group:g.id});
    g.questions.forEach((_, qi) => steps.push({type:"question", group:g.id, qi}));
  });
  return steps;
}
function gStart(unitId, route = "all", resume = false) {
  const unit = COURSE.grammar.find(u => u.id === unitId), saved = resume && gSaved();
  if (!unit || !gRouteOpen(unit, route)) return;
  gCancelAuto();
  const steps = gSteps(unit, route);
  if (saved?.unit === unit.id && Array.isArray(saved.steps) && saved.steps.length && saved.at >= 0 && saved.at < saved.steps.length && gRouteOpen(unit,gStepRoute(unit,saved.steps[saved.at]))) G = saved;
  else if (steps.length) G = {unit:unit.id, route, steps, at:0, responses:{}, ended:false};
  else return;
  view.grammar = unit.id; view.tab = "grammar"; S = null;
  G.review = false; gSave(); render(); gQueueAuto();
}
function gResponse(step) {
  if (step.type !== "question") return null;
  G.responses[step.group] ||= {};
  return G.responses[step.group][step.qi] ||= {value:"", checked:false};
}
function gCheck() {
  const step = G.steps[G.at], response = gResponse(step);
  if (!response || response.checked || !response.value.trim()) return;
  const unit = gUnit(), group = gGroups(unit).find(g => g.id === step.group);
  response.checked = true;
  response.good = grammarCorrect(group.questions[step.qi], response.value);
  if (group.questions.every((_, i) => G.responses[group.id]?.[i]?.checked)) {
    gradeGrammar(unit, group, group.questions.map((_, i) => G.responses[group.id][i].value));
  }
  G.review = false; gSave(); render(); sfx(response.good); gQueueAuto();
}
function gPick(index) {
  if (!G || G.ended) return;
  const step = G.steps[G.at], response = gResponse(step);
  if (!response || response.checked) return;
  const options = gGroups(gUnit()).find(g => g.id === step.group).questions[step.qi].options;
  if (!Number.isInteger(index) || !options || index < 0 || index >= options.length) return;
  response.value = options[index];
  gCheck();
}
function gMove(delta) {
  gCancelAuto();
  const step = G.steps[G.at];
  if (delta > 0 && step.type === "question" && !gResponse(step).checked) return;
  if (delta > 0 && (step.type === "summary" || (step.type === "theory" && !gUnit().sections[step.section].check))) {
    P.grammarRead ||= {}; P.grammarRead[`${G.unit}/${gStepRoute(gUnit(),step)}`] = true; save();
  }
  const target = G.steps[G.at + delta];
  if (target && !gRouteOpen(gUnit(), gStepRoute(gUnit(),target))) return;
  G.review = delta < 0;
  if (delta > 0 && G.at === G.steps.length - 1) G.ended = true;
  else G.at = Math.max(0, Math.min(G.steps.length - 1, G.at + delta));
  gSave(); render(); gQueueAuto();
}
function gExit() { gCancelAuto(); gSave(); G = null; view.tab = "grammar"; render(); }
function gRetry() {
  gCancelAuto();
  const wrong = G.steps.filter(s => s.type === "question" && !G.responses[s.group]?.[s.qi]?.good);
  if (!wrong.length) return;
  for (const s of wrong) G.responses[s.group][s.qi] = {value:"", checked:false};
  G.steps = wrong; G.at = 0; G.ended = false; G.retry = true; G.review = false; gSave(); render();
}
function gNextRoute(unit, route) {
  const routes = gRoutes(unit);
  return route === "all" ? null : routes[routes.indexOf(route) + 1];
}
function grammarView() {
  const units = COURSE.grammar || [], unit = units.find(u => u.id === view.grammar);
  if (!unit) return `<button class="btn ghost sm back" data-tab="home">← Главная</button><h2>📐 Грамматика</h2><div class="menu">${units.map(u => `<button class="mcard" data-grammar="${esc(u.id)}"><span class="mi">📐</span><span><b>${u.number}. ${esc(u.title)}</b><small>${esc(u.subtitle)}</small></span><span aria-hidden="true">›</span></button>`).join("")}</div>`;
  const saved = gSaved(), resume = saved?.unit === unit.id && !saved.ended && saved.steps?.[saved.at] && gRouteOpen(unit,gStepRoute(unit,saved.steps[saved.at]));
  const row = (route, title, subtitle, group) => {
    const best = group && P.grammar?.[grammarKey(unit, group)];
    const open = gRouteOpen(unit,route), done = gRouteDone(unit,route);
    return `<button class="mcard ${open ? '' : 'glocked'}" data-gstart="${esc(route)}" ${open ? '' : 'disabled aria-disabled="true"'}><span class="mi">${open ? done ? "✓" : group ? "✎" : "📖" : "🔒"}</span><span><b>${esc(title)}</b><small>${open ? `${best ? `${best.correct} из ${best.total} · ` : ""}${esc(subtitle)}` : 'Сначала пройди предыдущий раздел'}</small></span><span aria-hidden="true">${open ? '›' : '🔒'}</span></button>`;
  };
  return `<button class="btn ghost sm back" data-grammar-list>← Все уроки грамматики</button><span class="eyebrow">Unidad ${unit.number} · ${esc(unit.level)}</span><h2>${esc(unit.title)}</h2><p class="muted">${esc(unit.subtitle)}</p>
    <div class="gactions">${resume ? '<button class="btn" data-gresume>Продолжить урок</button>' : ""}<button class="btn ${resume ? "ghost" : ""}" data-gstart="all">${resume ? "Начать сначала" : "Пройти весь урок"}</button></div>
    <h3 class="sech">Теория и мини-проверки</h3><div class="menu">${unit.sections.map((s, i) => row(`section:${i}`, s.title, "Правило → мини-проверка", s.check)).join("")}${row("summary", "Что запомнить", "Краткая таблица правил")}</div>
    <h3 class="sech">Упражнения</h3><div class="menu">${unit.exercises.map(g => row(`exercise:${g.id}`, g.title, `${g.questions.length} заданий · по одному на экран`, g)).join("")}</div>`;
}
function gTheory(section) {
  return `<div class="theory">${section.paragraphs.map(p => `<p>${esc(p)}</p>`).join("")}${(section.examples || []).map(([es,ru]) => `<div class="box rule">${playBtn(es)} <b lang="es">${esc(es)}</b><br>${esc(ru)}</div>`).join("")}</div>
    ${section.schemes ? grammarSchemes(section.schemes) : ""}${section.table ? grammarTable(section.table) : ""}
    ${section.agreement ? `<div class="gagreement">${section.agreement.map(w => `<div><small>${esc(w.label)}</small><b>${esc(w.from)}</b><span>↓</span><b>${esc(w.to)}</b></div>`).join("")}</div>` : ""}
    ${section.notes?.length ? `<aside class="gnotes">${section.notes.map(n => `<p>${esc(n)}</p>`).join("")}</aside>` : ""}`;
}
function gPlayerView() {
  const unit = gUnit();
  if (G.ended) {
    const tested = G.steps.filter(s => s.type === "question"), good = tested.filter(s => G.responses[s.group]?.[s.qi]?.good).length;
    const next = gNextRoute(unit, G.route);
    return `<div class="player gplayer"><div class="ptop"><div class="wrap"><button class="x" data-gexit aria-label="К разделам урока">×</button><div class="bar"><i style="width:100%"></i></div></div></div><div class="pbody"><div class="wrap gresult"><span class="gresult-icon">${tested.length && good < tested.length ? "🌱" : "✓"}</span><h2 id="g-title" tabindex="-1">${tested.length ? "Практика завершена" : "Раздел прочитан"}</h2>${tested.length ? `<p>Верно: <b>${good} из ${tested.length}</b></p>` : ""}<p class="muted">Лучшие результаты сохранены.</p>${good < tested.length ? '<button class="btn" data-gretry-mistakes>Повторить ошибки</button>' : ""}${next ? `<button class="btn ${good < tested.length ? "ghost" : ""}" data-gstart="${esc(next)}">Следующий раздел →</button>` : ""}<button class="btn ghost" data-gexit>К разделам урока</button></div></div><div></div></div>`;
  }
  const step = G.steps[G.at], group = step.group && gGroups(unit).find(g => g.id === step.group), response = gResponse(step);
  let title, content, kicker = "Грамматика";
  if (step.type === "theory") { const section = unit.sections[step.section]; title = section.title; content = gTheory(section); kicker = "Правило"; }
  if (step.type === "summary") { title = "Что запомнить"; content = grammarTable(unit.summary); kicker = "Кратко"; }
  if (step.type === "intro") {
    title = group.title; kicker = "Упражнение";
    content = `<p>${esc(group.instruction)}</p>${group.family ? grammarFamily(group.family) : ""}${group.example ? `<div class="gworked-example"><small>${esc(group.example.label)}</small><b>${esc(group.example.es)}</b><small>${esc(group.example.ru)}</small></div>` : ""}<p class="muted">${group.questions.length} заданий. Отвечай по одному — пояснение появится после проверки.</p>`;
  }
  if (step.type === "question") {
    const q = group.questions[step.qi], block = (group.questionBlocks || []).filter(b => b.at <= step.qi).at(-1);
    kicker = `${group.title === "Мини-проверка" ? "Мини-проверка" : group.title} · ${step.qi + 1} из ${group.questions.length}`;
    title = q.context || (q.image ? "Выбери название профессии" : q.prompt);
    const who = block ? `<div class="gwho"><img src="${esc(group.family.portraits[block.person])}" alt="" width="44" height="44"><b>Родственники ${esc(block.person)}</b></div>` : "";
    const options = q.options ? `<div class="opts" role="group" aria-label="Варианты ответа">${q.options.map((o,i) => `<button class="opt ${response.checked && q.answers.includes(o) ? "right" : response.checked && response.value === o && !response.good ? "wrong" : ""}" data-gpick="${i}" aria-pressed="${response.value === o}" ${response.checked ? "disabled" : ""}><span class="k">${i + 1}</span><span lang="es">${esc(o)}</span></button>`).join("")}</div>`
      : `<div><label class="sr-only" for="g-answer">Ответ на испанском</label><input class="ginput" id="g-answer" aria-label="Ответ на испанском" lang="es" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="Слово на испанском" value="${esc(response.value)}" ${response.checked ? "disabled" : ""}>${response.checked ? "" : `<div class="gaccents" aria-label="Испанские буквы">${["á","é","í","ó","ú","ü","ñ"].map(c => `<button class="btn ghost sm" data-gchar="${c}" aria-label="Вставить ${c}">${c}</button>`).join("")}</div>`}</div>`;
    const question = `${who}${q.context ? `<p class="gquestion-sentence" lang="es">${esc(q.prompt)}</p>` : ""}${options}`;
    content = group.family ? `<div class="gfamily-work"><details class="gplay-family" ${G.treeOpen === false ? "" : "open"}><summary>Семейное дерево</summary>${grammarFamily({...group.family, activeName:block?.person})}</details><div class="ganswer-area">${question}${group.vocabulary ? `<details class="gvocab"><summary>Слова родства</summary>${grammarTable(group.vocabulary)}</details>` : ""}</div></div>`
      : `<div class="gquestion-work ${q.image ? "has-image" : ""}">${q.image ? `<img class="gquestion-picture" src="${esc(q.image)}" alt="${esc(q.imageAlt)}" width="384" height="384">` : ""}<div class="ganswer-area">${question}</div></div>`;
    if (group.title === "Мини-проверка") content = `<p class="muted ginstruction">${esc(group.instruction.replace(/ Затем нажми.*$/, ""))}</p>` + content;
  }
  const checked = response?.checked, feedback = checked ? `<div class="fb" role="status"><h3>${response.good ? "✓ Верно" : "Пока неверно"}</h3>${response.good ? "" : `<span class="ans">Верный ответ: ${esc(group.questions[step.qi].answers.join(" / "))}</span>`}<span class="ex">${esc(group.questions[step.qi].explain)}</span></div>` : "";
  return `<div class="player gplayer"><div class="ptop"><div class="wrap"><button class="x" data-gexit aria-label="Выйти из урока">×</button><div class="bar" role="progressbar" aria-label="Прогресс урока" aria-valuemin="0" aria-valuemax="${G.steps.length}" aria-valuenow="${G.at}"><i style="width:${Math.round(G.at / G.steps.length * 100)}%"></i></div><span class="pcount">${G.at + 1}/${G.steps.length}</span></div></div>
    <div class="pbody"><div class="wrap"><span class="kicker">${esc(kicker)}</span><h2 id="g-title" tabindex="-1">${esc(title)}</h2>${content}</div></div>
    <div class="pfoot ${checked ? response.good ? "good" : "bad" : ""}"><div class="wrap">${feedback}<div class="gplayer-actions"><button class="btn ghost" data-gback ${G.at ? "" : "disabled"}>← Назад</button>${checked && !G.review ? '<span class="muted gpick-hint" role="status">Переходим дальше…</span>' : step.type === "question" && !checked ? group.questions[step.qi].options ? '<span class="muted gpick-hint">Нажми на вариант ответа</span>' : `<button class="btn" data-gcheck ${response.value.trim() ? "" : "disabled"}>Проверить</button>` : `<button class="btn" data-gnext>${G.at === G.steps.length - 1 ? "Завершить" : step.type === "intro" ? "Начать" : "Далее →"}</button>`}</div></div></div></div>`;
}
