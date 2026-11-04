/* Пошаговый урок грамматики. Данные и проверка ответов общие с остальным сайтом. */
let G = null;
const G_SESSION_KEY = "espanol-cada-dia.grammar-session.v1";
const gUnit = () => (COURSE.grammar || []).find(u => u.id === G?.unit);
function gSyncViewport() {
  const player=document.querySelector('.gplayer');
  if(player?.style && window.visualViewport)player.style.height=`${window.visualViewport.height}px`;
}
window.visualViewport?.addEventListener('resize',gSyncViewport);
const gGroups = u => [...u.sections.map(s => s.check).filter(Boolean), ...u.exercises];
const gRoutes = u => u.learningOrder || [...u.sections.map((_, i) => `section:${i}`), "summary", ...u.exercises.map(g => `exercise:${g.id}`)];
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
  gRoutes(unit).forEach(r => {
    if (route !== "all" && route !== r) return;
    if(r === "summary") { steps.push({type:"summary"}); return; }
    if(r.startsWith("section:")) {
      const i=+r.split(":")[1], s=unit.sections[i];
      steps.push({type:"theory",section:i});
      s.check?.questions.forEach((_,qi)=>steps.push({type:"question",group:s.check.id,qi}));
    } else {
      const g=unit.exercises.find(g=>r===`exercise:${g.id}`);
      steps.push({type:"intro",group:g.id});
      g.questions.forEach((_,qi)=>steps.push({type:"question",group:g.id,qi}));
    }
  });
  return steps;
}
function gStart(unitId, route = "all", resume = false) {
  const unit = COURSE.grammar.find(u => u.id === unitId), saved = resume && gSaved();
  if (!unit || !gRouteOpen(unit, route)) return;
  const steps = gSteps(unit, route);
  if (saved?.unit === unit.id && Array.isArray(saved.steps) && saved.steps.length && saved.at >= 0 && saved.at < saved.steps.length) {
    const restoredRoute=gRouteOpen(unit,saved.route)?saved.route:'all';
    const reordered=saved.retry && restoredRoute===saved.route ? saved.steps : gSteps(unit,restoredRoute);
    const old=saved.steps[saved.at];
    let at=reordered.findIndex(s=>s.type===old.type && s.section===old.section && s.group===old.group && s.qi===old.qi);
    if(at<0 || !gRouteOpen(unit,gStepRoute(unit,reordered[at]))) at=reordered.findIndex(s=>gRouteOpen(unit,gStepRoute(unit,s)) && !gRouteDone(unit,gStepRoute(unit,s)));
    G={...saved,route:restoredRoute,steps:reordered,at:Math.max(0,at),responses:saved.responses || {}};
  }
  else if (steps.length) G = {unit:unit.id, route, steps, at:0, responses:{}, ended:false};
  else return;
  view.grammar = unit.id; view.tab = "grammar"; S = null;
  gSave(); render();
}
function gResponse(step) {
  if (step.type !== "question") return null;
  G.responses[step.group] ||= {};
  const response=G.responses[step.group][step.qi] ||= {value:"", checked:false};
  const q=gGroups(gUnit()).find(g=>g.id===step.group)?.questions[step.qi];
  if(Array.isArray(response.chosen) && q?.tiles && response.chosen.map(i=>q.tiles[i]).join(' ')!==response.value) delete response.chosen;
  return response;
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
  gSave(); render(); sfx(response.good);
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
function gQuestionMode(q, response) {
  if (q.guidedGaps && (response.slotValues || !response.value)) return 'gaps';
  // An unfinished answer from the old typing interface remains editable after the update.
  if (q.tiles && !(response.value && !response.checked && !Array.isArray(response.chosen))) return 'build';
  return q.options ? 'choice' : 'input';
}
function gBuild(action, index) {
  if (!G || G.ended) return;
  const step=G.steps[G.at], response=gResponse(step), q=gGroups(gUnit()).find(g=>g.id===step.group)?.questions[step.qi];
  if (!q?.tiles || !response || response.checked || !Number.isInteger(index)) return;
  response.chosen ||= [];
  if (action==='add' && index>=0 && index<q.tiles.length && !response.chosen.includes(index)) response.chosen.push(index);
  else if (action==='remove' && index>=0 && index<response.chosen.length) response.chosen.splice(index,1);
  else return;
  response.value=response.chosen.map(i=>q.tiles[i]).join(' '); gSave();
  const area=document.querySelector('.gbuild');
  if(area) {
    area.innerHTML=gBuilderContents(q,response);
    area.querySelector(action==='add' ? `[data-gremove="${response.chosen.length-1}"]` : `[data-gremove="${Math.min(index,response.chosen.length-1)}"],[data-gadd]:not(:disabled)`)?.focus({preventScroll:true});
  }
  const check=document.querySelector('[data-gcheck]'); if(check)check.disabled=!response.value.trim();
}
function gBuilderContents(q,response) {
  const chosen=response.chosen || [];
  return `${gAnswerHint(q)}<div class="gbuild-answer" role="group" aria-label="Собранный ответ">${response.checked ? `<b lang="es">${esc(response.value)}</b>` : chosen.length ? chosen.map((index,i)=>`<button class="gtile is-chosen" data-gremove="${i}" aria-label="Убрать ${esc(q.tiles[index])}">${esc(q.tiles[index])}<span aria-hidden="true"> ×</span></button>`).join('') : `<span class="muted">${q.answerHint ? 'Собери ответ из слов ниже' : 'Нажимай на слова в нужном порядке'}</span>`}</div>${response.checked?'':`<div class="gbuild-bank" role="group" aria-label="Слова для сборки">${q.tiles.map((word,i)=>`<button class="gtile" data-gadd="${i}" lang="es" ${chosen.includes(i)?'disabled':''}>${esc(word)}</button>`).join('')}</div>`}`;
}
function gAnswerHint(q) { return q.answerHint ? `<p class="ganswer-hint">Нужно сказать: <strong>«${esc(q.answerHint)}»</strong></p>` : ''; }
function gBuilder(q,response) { return `<div class="gbuild">${gBuilderContents(q,response)}</div>`; }
function gComposeGaps(parts, values) {
  return parts.map((part,i)=>part+(values[i] || '')).join('').trim();
}
function gSelectGap(slot, option) {
  if (!G || G.ended) return;
  const response=gResponse(G.steps[G.at]);
  const q=gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group)?.questions[G.steps[G.at].qi];
  if (!response || response.checked || !q?.guidedGaps || !Number.isInteger(slot) || !q.guidedGaps.choices[slot]) return;
  if (option !== undefined && (!Number.isInteger(option) || !q.guidedGaps.choices[slot][option])) return;
  response.slotValues ||= Array(q.guidedGaps.choices.length).fill('');
  response.activeGap=slot;
  if (option !== undefined) {
    response.slotValues[slot]=q.guidedGaps.choices[slot][option];
    const next=response.slotValues.findIndex((v,i)=>!v && i>slot);
    const remaining=response.slotValues.findIndex(v=>!v);
    response.activeGap=next>=0 ? next : remaining>=0 ? remaining : slot;
  }
  response.value=response.slotValues.every(Boolean) ? gComposeGaps(q.guidedGaps.parts,response.slotValues) : '';
  gSave();
  const area=document.querySelector('.gguided');
  if(area) {
    area.innerHTML=gGuidedContents(q,response);
    area.querySelector(`[data-gslot="${response.activeGap}"]`)?.focus({preventScroll:true});
  }
  const check=document.querySelector('[data-gcheck]'); if(check)check.disabled=!response.value;
}
function gGuidedContents(q,response) {
  const {parts,choices}=q.guidedGaps, values=response.slotValues || [], active=response.activeGap || 0;
  const [before,after]=q.prompt.split('___');
  return `${gAnswerHint(q)}<p class="gguided-sentence" lang="es">${esc(before)}${parts.map((part,i)=>`${esc(part)}${i<choices.length ? `<button class="gguided-slot ${i===active && !response.checked?'is-active':''}" data-gslot="${i}" aria-label="Пропуск ${i+1}${values[i]?': '+esc(values[i]):''}" ${response.checked?'disabled':''}>${esc(values[i] || '…')}<small aria-hidden="true">${i+1}</small></button>`:''}`).join('')}${esc(after || '')}</p>${response.checked?'':`<div class="gguided-options" role="group" aria-label="Варианты для пропуска ${active+1}"><p class="muted">Выбери слово для пропуска ${active+1} из ${choices.length}</p><div class="gbuild-bank">${choices[active].map((word,i)=>`<button class="gtile" data-gslot-choice="${i}" data-slot="${active}" lang="es" aria-pressed="${values[active]===word}">${esc(word)}</button>`).join('')}</div></div>`}`;
}
function gGuided(q,response) { return `<div class="gguided">${gGuidedContents(q,response)}</div>`; }
function gMove(delta) {
  if (delta < 0 && G.at === 0) return gExit();
  const step = G.steps[G.at];
  if (delta > 0 && step.type === "question" && !gResponse(step).checked) return;
  if (delta > 0 && (step.type === "summary" || (step.type === "theory" && !gUnit().sections[step.section].check))) {
    P.grammarRead ||= {}; P.grammarRead[`${G.unit}/${gStepRoute(gUnit(),step)}`] = true; save();
  }
  const target = G.steps[G.at + delta];
  if (target && !gRouteOpen(gUnit(), gStepRoute(gUnit(),target))) return;
  if (delta > 0 && G.at === G.steps.length - 1) G.ended = true;
  else G.at = Math.max(0, Math.min(G.steps.length - 1, G.at + delta));
  gSave(); render();
}
function gExit() { gSave(); G = null; view.tab = "grammar"; render(); }
function gRetry() {
  const wrong = G.steps.filter(s => s.type === "question" && !G.responses[s.group]?.[s.qi]?.good);
  if (!wrong.length) return;
  for (const s of wrong) G.responses[s.group][s.qi] = {value:"", checked:false};
  G.steps = wrong; G.at = 0; G.ended = false; G.retry = true; gSave(); render();
}
function gNextRoute(unit, route) {
  const routes = gRoutes(unit);
  return route === "all" ? null : routes[routes.indexOf(route) + 1];
}
function grammarView() {
  const units = COURSE.grammar || [], unit = units.find(u => u.id === view.grammar);
  if (!unit) return `<button class="btn ghost sm back" data-tab="home">← Главная</button><h2>📐 Грамматика</h2><div class="menu">${units.map(u => `<button class="mcard" data-grammar="${esc(u.id)}"><span class="mi">📐</span><span><b>${u.number}. ${esc(u.title)}</b><small>${esc(u.subtitle)}</small></span><span aria-hidden="true">›</span></button>`).join("")}</div>`;
  const saved = gSaved(), resume = saved?.unit === unit.id && !saved.ended && saved.steps?.[saved.at];
  const row = (route, title, subtitle, group) => {
    const best = group && P.grammar?.[grammarKey(unit, group)];
    const open = gRouteOpen(unit,route), done = gRouteDone(unit,route);
    return `<button class="mcard ${open ? '' : 'glocked'}" data-gstart="${esc(route)}" ${open ? '' : 'disabled aria-disabled="true"'}><span class="mi">${open ? done ? "✓" : group ? "✎" : "📖" : "🔒"}</span><span><b>${esc(title)}</b><small>${open ? `${best ? `${best.correct} из ${best.total} · ` : ""}${esc(subtitle)}` : 'Сначала пройди предыдущий раздел'}</small></span><span aria-hidden="true">${open ? '›' : '🔒'}</span></button>`;
  };
  return `<button class="btn ghost sm back" data-grammar-list>← Все уроки грамматики</button><span class="eyebrow">Unidad ${unit.number} · ${esc(unit.level)}</span><h2>${esc(unit.title)}</h2><p class="muted">${esc(unit.subtitle)}</p>
    <div class="gactions">${resume ? '<button class="btn" data-gresume>Продолжить урок</button>' : ""}<button class="btn ${resume ? "ghost" : ""}" data-gstart="all">${resume ? "Начать сначала" : "Пройти весь урок"}</button></div>
    ${unit.learningOrder ? `<h3 class="sech">Теория и практика по порядку</h3><div class="menu">${gRoutes(unit).map(r=>{
      if(r==="summary") return row(r,"Что запомнить","Правила с примерами");
      if(r.startsWith("section:")){const s=unit.sections[+r.split(":")[1]];return row(r,s.title,"Правило → мини-проверка",s.check);}
      const g=unit.exercises.find(g=>r===`exercise:${g.id}`);return row(r,g.title,`${g.questions.length} заданий · практика`,g);
    }).join("")}</div>` : `<h3 class="sech">Теория и мини-проверки</h3><div class="menu">${unit.sections.map((s, i) => row(`section:${i}`, s.title, "Правило → мини-проверка", s.check)).join("")}${row("summary", "Что запомнить", "Правила с примерами")}</div>
    <h3 class="sech">Упражнения</h3><div class="menu">${unit.exercises.map(g => row(`exercise:${g.id}`, g.title, `${g.questions.length} ${plural(g.questions.length,"задание","задания","заданий")} · по одному на экран`, g)).join("")}</div>`}`;
}
function gTheoryText(text) {
  return esc(text).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/`([^`]+)`/g, (_, token) => `<code lang="es"${token.includes(" ") ? ' class="is-phrase"' : ""}>${token}</code>`);
}
function gArtExamples(art) {
  return `<div class="gscene-examples">${art.examples.map(([es,ru])=>`<div class="gscene-line"><b lang="es">${gTheoryText(es)}</b><span>${esc(ru)}</span></div>`).join('')}</div>`;
}
function gArtFigure(art) {
  if (!art) return '';
  return `<figure class="gscene"><button class="gscene-image" data-gart aria-label="Увеличить иллюстрацию"><img src="${esc(art.image)}" alt="${esc(art.alt)}" width="1200" height="800" decoding="async"><span aria-hidden="true">⤢</span></button><figcaption>${gArtExamples(art)}</figcaption></figure>`;
}
function gOpenArt() {
  const step=G?.steps[G.at], art=step?.type==='theory' && gUnit()?.sections[step.section].illustration;
  if (!art || document.querySelector('#g-art-modal')) return;
  const opener=document.activeElement, dialog=document.createElement('dialog');
  dialog.id='g-art-modal'; dialog.className='gart-modal'; dialog.setAttribute('aria-label','Иллюстрация к правилу');
  dialog.innerHTML=`<div class="gart-toolbar"><button class="btn ghost sm" data-gart-close>Закрыть ×</button></div><img src="${esc(art.image)}" alt="${esc(art.alt)}" width="1200" height="800" decoding="async">${gArtExamples(art)}`;
  dialog.addEventListener('close',()=>{dialog.remove(); if(opener?.isConnected)opener.focus();});
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  document.body.appendChild(dialog); dialog.showModal();
}
function gTheory(section) {
  const copy=section.paragraphs.map((p,i)=>`<p class="gtheory-paragraph${i?'':' is-lead'}">${gTheoryText(p)}</p>`);
  return `<article class="gtheory gtheory-${esc(section.presentation || 'examples')}"><div class="gtheory-copy">${copy[0] || ''}${section.formulas ? `<div class="gformulas" aria-label="Модель правила">${section.formulas.map(f=>`<div>${gTheoryText(f)}</div>`).join('')}</div>`:''}</div>${gArtFigure(section.illustration)}
    ${section.wordGroups ? grammarWordGroups(section.wordGroups) : ""}${section.schemes ? `<div${section.schemeGrid ? ' class="gsummary-cards"' : ""}>${grammarSchemes(section.schemes)}</div>` : ""}${section.table ? gTheoryTable(section.table) : ""}
    ${section.agreement ? `<div class="gagreement">${section.agreement.map(w => `<div><small>${esc(w.label)}</small><b>${esc(w.from)}</b><span>↓</span><b>${esc(w.to)}</b></div>`).join("")}</div>` : ""}
    <div class="gtheory-copy">${copy.slice(1).join('')}</div><div class="gtheory-examples">${(section.examples || []).map(([es,ru]) => `<div class="gexample">${playBtn(es)} <b lang="es">${esc(es)}</b><small>${esc(ru)}</small></div>`).join("")}</div>
    ${section.notes?.length ? `<aside class="gnotes"><b>Обрати внимание</b>${section.notes.map(n => `<p>${esc(n)}</p>`).join("")}</aside>` : ""}</article>`;
}
function gTheoryTable(table) {
  if(!table.compactForms)return grammarTable(table);
  return `<div class="gforms-wide">${grammarTable(table)}</div><div class="gforms-mobile">${table.rows.map(row=>`<section><h3>${esc(row[0])}</h3><dl>${row.slice(1).map((value,i)=>`<div><dt>${esc(table.heads[i+1])}</dt><dd lang="es">${esc(value)}</dd></div>`).join('')}</dl></section>`).join('')}</div>`;
}
function gUnitFinished(unit) {
  const lastExercise = gRoutes(unit).filter(r=>r.startsWith('exercise:')).at(-1);
  return !!lastExercise && ["all", "summary", lastExercise].includes(G.route) && unit.exercises.every(g => !!P.grammar?.[grammarKey(unit,g)]);
}
function gFireworks() {
  const colors = ["#7357dd","#f0aa36","#46a890","#ed7183"];
  return `<div class="gfireworks" aria-hidden="true">${[20,50,80].map((x,k) => `<div class="gburst" style="left:${x}%;top:${20+k%2*15}%">${Array.from({length:16},(_,i) => {
    const angle = i * Math.PI / 8;
    return `<i style="--dx:${Math.round(Math.cos(angle)*110)}px;--dy:${Math.round(Math.sin(angle)*110)}px;--delay:${k*.3}s;--spark:${colors[i%colors.length]}"></i>`;
  }).join("")}</div>`).join("")}</div>`;
}
function gFinalView(unit, tested, good) {
  const nextUnit = COURSE.grammar[COURSE.grammar.findIndex(u => u.id === unit.id)+1];
  const total = unit.exercises.reduce((n,g) => n+g.questions.length,0);
  const correct = unit.exercises.reduce((n,g) => n+(P.grammar[grammarKey(unit,g)]?.correct||0),0);
  return `<div class="player gplayer gfinal"><div class="ptop"><div class="wrap"><button class="x" data-gmain aria-label="На главную">×</button><div class="bar"><i style="width:100%"></i></div><span class="pcount">✓</span></div></div>
    <div class="pbody">${gFireworks()}<div class="wrap gresult"><span class="gresult-icon" aria-hidden="true">🏆</span><span class="kicker" lang="es">¡Enhorabuena!</span><h2 id="g-title" tabindex="-1">Поздравляю! Урок пройден!</h2><p>${esc(unit.title)} · ${esc(unit.subtitle)}</p>
    <div class="gfinal-score"><b>${unit.exercises.length} упражнения завершены</b><span>Лучший результат: ${correct} из ${total}</span></div>
    ${tested.length && good<tested.length ? '<button class="btn ghost wide" data-gretry-mistakes>Повторить ошибки</button>' : ""}
    ${nextUnit ? `<button class="btn wide" data-gnext-unit="${esc(nextUnit.id)}">Следующий урок →</button><button class="btn ghost wide" data-gmain>На главную</button>` : '<button class="btn wide" data-gmain>На главную</button>'}
    <button class="btn ghost wide" data-gexit>К разделам урока</button></div></div><div></div></div>`;
}
function gBlank(text) {
  return esc(text).replace(/_{3,}/g, '<span class="gblank" role="img" aria-label="Место для ответа">…</span>');
}
function gWorkedPreview(preview) {
  if (preview.gapParts) return preview.gapParts.map((part,i)=>`${esc(part)}${i < preview.gapAnswers.length ? `<mark class="gpreview-insert">${esc(preview.gapAnswers[i])}</mark>` : ""}`).join("");
  if (!preview.sentenceParts) return gBlank(preview.source);
  return `${esc(preview.sentenceParts[0])}<mark class="gpreview-insert">${esc(preview.displayAnswer ?? preview.answer)}</mark>${esc(preview.sentenceParts[1])}`;
}
function gGapSentence(q, response) {
  const values = response.gapValues || (response.value ? response.value.split(" ") : []);
  return `<div class="gfill-sentence"><p class="ggap-line" lang="es">${q.gapParts.map((part,i)=>`${esc(part)}${i < q.gapParts.length-1 ? `<input class="ginput ggap-input" id="${i ? 'g-answer-'+i : 'g-answer'}" data-ggap="${i}" aria-label="${i ? 'Пропуск 2: más или menos' : 'Пропуск 1: артикль'}" lang="es" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="…" value="${esc(values[i] || '')}" ${response.checked ? 'disabled' : ''}>` : ""}`).join("")}</p>${response.checked ? "" : `<div class="gaccents"><button class="btn ghost sm" data-gchar="á" aria-label="Вставить á">á</button></div>`}</div>`;
}
function gIntro(group) {
  const pictures = group.questions.filter(q => q.image).slice(0,3);
  const preview = group.preview;
  const visual = pictures.length ? `<div class="gintro-art" aria-hidden="true">${pictures.map(q => `<img src="${esc(q.image)}" alt="" width="384" height="384">`).join("")}</div>` : preview ? `<div class="gintro-demo"><span class="kicker">Образец</span><div class="gintro-source" lang="es">${gWorkedPreview(preview)}${preview.targetPrefix === "" ? "" : ` <span aria-hidden="true">→</span> ${esc(preview.targetPrefix ?? "la")}`}</div><div class="gintro-answer" lang="es">${esc(preview.answer)}<span aria-hidden="true">✓</span></div><span class="muted">${esc(preview.translation)}</span></div>` : group.introGroups ? grammarWordGroups(group.introGroups) : "";
  const choice = group.questions.every(q => q.options), modes=new Set(group.questions.map(q=>q.guidedGaps?'Выбор слов в пропусках':q.tiles?'Сборка фразы':q.options?'Выбор ответа':'Короткий ввод')), mixed=modes.size>1;
  const tip = preview?.tip || '';
  return `<div class="gintro ${visual ? "has-visual" : ""}">${visual}<div class="gintro-copy"><div class="gintro-tags"><span>${group.questions.length} ${plural(group.questions.length,"задание","задания","заданий")}</span><span>${esc([...modes].join(' · '))}</span></div><p>${esc(group.instruction)}</p>${modes.has('Сборка фразы') ? '<p class="muted gintro-tip">Нажимай на слова по порядку. Выбранное слово можно убрать нажатием.</p>' : mixed ? '<p class="muted gintro-tip">Часть ответов выбирай из вариантов, остальные вписывай самостоятельно.</p>' : tip ? `<p class="muted gintro-tip">${esc(tip)}</p>` : ""}</div>${group.family ? `<div class="gintro-family">${grammarFamily(group.family)}</div>` : ""}${group.example ? `<div class="gworked-example gintro-family"><small>${esc(group.example.label)}</small><b>${esc(group.example.es)}</b><small>${esc(group.example.ru)}</small></div>` : ""}</div>`;
}
function gRatings(ratings) {
  if (!ratings) return "";
  return `<section class="gratings" aria-label="Сравнение друзей"><h3>${esc(ratings.label)}</h3><div class="gratings-grid">${ratings.people.map(p => `<div class="gratings-person"><span class="gratings-avatar" aria-hidden="true">${esc(p.name.slice(0,1))}</span><b lang="es">${esc(p.name)}</b><span class="gratings-scale" role="img" aria-label="Уровень: ${p.level} из 3">${[1,2,3].map(n => `<i${n <= p.level ? ' class="is-filled"' : ""}></i>`).join("")}</span></div>`).join("")}</div><small>Больше полосок — сильнее выражено качество.</small></section>`;
}
function gFacts(facts) {
  if (!facts) return "";
  return `<section class="gratings gfacts" aria-label="Подсказка к заданию"><h3>${esc(facts.label)}</h3><div class="gfacts-grid">${facts.items.map(([name,value]) => `<div class="gfacts-item"><span lang="es">${esc(name)}</span><b>${esc(value)}</b></div>`).join("")}</div></section>`;
}
function gClock(clock) {
  if (!clock) return "";
  const time = `${String(clock.hour).padStart(2,'0')}:${String(clock.minute).padStart(2,'0')}`;
  return `<div class="gclock" role="img" aria-label="Часы: ${time}"><svg viewBox="0 0 160 160" aria-hidden="true"><circle class="gclock-face" cx="80" cy="80" r="74"/>${Array.from({length:12},(_,i)=>{const angle=(i+1)*Math.PI/6; return `<text x="${80+59*Math.sin(angle)}" y="${80-59*Math.cos(angle)}">${i+1}</text>`;}).join('')}<path class="gclock-hour" d="M80 80V43" transform="rotate(${clock.hour%12*30+clock.minute/2} 80 80)"/><path class="gclock-minute" d="M80 80V28" transform="rotate(${clock.minute*6} 80 80)"/><circle cx="80" cy="80" r="4" fill="currentColor"/></svg><span>${time}</span></div>`;
}
function gDistance(distance) {
  if (!distance) return "";
  return `<div class="gdistance" aria-label="Расположение предмета">${[['near','Я','У меня'],['listener','Ты','У собеседника'],['far','Там','Далеко от обоих']].map(([key,person,label])=>`<div class="gdistance-zone ${key===distance?'is-active':''}"><span class="gdistance-person">${person}</span><span class="gdistance-dot" aria-hidden="true">${key===distance?'●':'·'}</span><small>${label}</small>${key===distance?'<span class="sr-only">Здесь находится предмет</span>':''}</div>`).join('')}</div>`;
}
function gPicture(q) {
  if (!q.image) return "";
  if (q.pictureCount) return `<div class="gcount-picture" role="img" aria-label="${esc(q.imageAlt)}" data-picture-count="${q.pictureCount}">${Array.from({length:q.pictureCount},() => `<img src="${esc(q.image)}" alt="" width="384" height="384">`).join("")}</div>`;
  return `<img class="gquestion-picture" src="${esc(q.image)}" alt="${esc(q.imageAlt)}" width="384" height="384">`;
}
function gPlayerView() {
  const unit = gUnit();
  if (G.ended) {
    const tested = G.steps.filter(s => s.type === "question"), good = tested.filter(s => G.responses[s.group]?.[s.qi]?.good).length;
    if (gUnitFinished(unit)) return gFinalView(unit, tested, good);
    const next = gNextRoute(unit, G.route);
    return `<div class="player gplayer"><div class="ptop"><div class="wrap"><button class="x" data-gexit aria-label="К разделам урока">×</button><div class="bar"><i style="width:100%"></i></div></div></div><div class="pbody"><div class="wrap gresult"><span class="gresult-icon">${tested.length && good < tested.length ? "🌱" : "✓"}</span><h2 id="g-title" tabindex="-1">${tested.length ? "Практика завершена" : "Раздел прочитан"}</h2>${tested.length ? `<p>Верно: <b>${good} из ${tested.length}</b></p>` : ""}<p class="muted">Лучшие результаты сохранены.</p>${good < tested.length ? '<button class="btn" data-gretry-mistakes>Повторить ошибки</button>' : ""}${next ? `<button class="btn ${good < tested.length ? "ghost" : ""}" data-gstart="${esc(next)}">Следующий раздел →</button>` : ""}<button class="btn ghost" data-gexit>К разделам урока</button></div></div><div></div></div>`;
  }
  const step = G.steps[G.at], group = step.group && gGroups(unit).find(g => g.id === step.group), response = gResponse(step);
  let title, content, kicker = "Грамматика";
  if (step.type === "theory") { const section = unit.sections[step.section]; title = section.title; content = gTheory(section); kicker = "Правило"; }
  if (step.type === "summary") { title = "Что запомнить"; content = unit.summary.wordGroups ? grammarWordGroups(unit.summary.wordGroups) : unit.summary.schemes ? `<div class="gsummary-cards">${grammarSchemes(unit.summary.schemes)}</div>` : grammarTable(unit.summary); kicker = "Кратко"; }
  if (step.type === "intro") {
    title = group.title; kicker = "Упражнение";
    content = gIntro(group);
  }
  if (step.type === "question") {
    const q = group.questions[step.qi], block = (group.questionBlocks || []).filter(b => b.at <= step.qi).at(-1);
    kicker = `${group.title === "Мини-проверка" ? "Мини-проверка" : group.title} · ${step.qi + 1} из ${group.questions.length}`;
    title = q.context || (group.inlineAnswer ? "Дополни фразу" : q.image ? (group.pictureTitle || "Выбери название профессии") : q.prompt);
    const who = block ? `<div class="gwho"><img src="${esc(group.family.portraits[block.person])}" alt="" width="44" height="44"><b>Родственники ${esc(block.person)}</b></div>` : "";
    const mode=gQuestionMode(q,response);
    const options = mode==='gaps' ? gGuided(q,response) : mode==='build' ? gBuilder(q,response) : q.options ? `<div class="${q.interaction==='gap-choice'?'gchoices':'opts'}" role="group" aria-label="Варианты ответа">${q.options.map((o,i) => `<button class="opt ${response.checked && grammarCorrect(q,o) ? "right" : response.checked && response.value === o && !response.good ? "wrong" : ""}" data-gpick="${i}" aria-label="${esc(o === 'Без артикля' ? 'Ничего не вставлять' : gOptionLabel(q,o))}" aria-pressed="${response.value === o}" ${response.checked ? "disabled" : ""}><span class="k">${i + 1}</span><span lang="es">${esc(gOptionLabel(q,o))}</span></button>`).join("")}</div>`
      : `<div><label class="sr-only" for="g-answer">Ответ на испанском</label>${group.phraseInput && q.answers[0].split(' ').length>2 ? `<textarea class="ginput gphrase-input" id="g-answer" aria-label="Ответ на испанском" lang="es" autocomplete="off" autocapitalize="none" spellcheck="false" rows="2" placeholder="${esc(group.answerPlaceholder || "Фраза на испанском")}" ${response.checked ? "disabled" : ""}>${esc(response.value)}</textarea>` : `<input class="ginput" id="g-answer" aria-label="Ответ на испанском" lang="es" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="${esc(q.answerPlaceholder || "Ответ")}" value="${esc(response.value)}" ${response.checked ? "disabled" : ""}>`}${response.checked ? "" : `<div class="gaccents" aria-label="Испанские буквы">${gInputChars(q).map(c => `<button class="btn ghost sm" data-gchar="${c}" aria-label="Вставить ${c}">${c}</button>`).join("")}</div>`}</div>`;
    const source = q.sourceParts ? `<div class="gsource" lang="es"><span class="kicker">${esc(q.sourceLabel || 'Исходная фраза')}</span><p>${esc(q.sourceParts[0])}<strong>${esc(q.sourceParts[1])}</strong>${esc(q.sourceParts[2])}</p></div>` : "";
    const clues = q.clues ? `<div class="gclues" aria-label="Слова для ответа">${q.clues.map(([es,ru])=>`<span><b lang="es">${esc(es)}</b><small>${esc(ru)}</small></span>`).join("")}</div>` : "";
    const inline = group.inlineAnswer && mode==='input' && !q.options && q.prompt.includes("___");
    const sentence = mode==='gaps' ? options : q.gapParts ? gGapSentence(q,response) : inline ? `<div class="gfill-sentence"><p lang="es">${esc(q.prompt.split("___")[0])}</p><label class="gfill-label" for="g-answer">Впиши пропущенную часть</label>${options}<p lang="es">${esc(q.prompt.split("___").slice(1).join("___"))}</p></div>` : `${q.context ? `<p class="gquestion-sentence" lang="es">${gBlank(q.prompt)}</p>` : ""}${options}`;
    const question = `${who}${source}${clues}${gRatings(q.ratings)}${gFacts(q.facts)}${gClock(q.clock)}${gDistance(q.distance)}${q.translation ? `<p class="muted gquestion-translation">${esc(q.translation)}</p>` : ""}${['build','gaps'].includes(mode)?'':gAnswerHint(q)}${sentence}`;
    content = group.family ? `<div class="gfamily-work"><details class="gplay-family" ${G.treeOpen === false ? "" : "open"}><summary>Семейное дерево</summary>${grammarFamily({...group.family, activeName:block?.person})}</details><div class="ganswer-area">${question}${group.vocabulary ? `<details class="gvocab"><summary>Слова родства</summary>${grammarTable(group.vocabulary)}</details>` : ""}</div></div>`
      : `<div class="gquestion-work ${q.image ? "has-image" : ""}">${gPicture(q)}<div class="ganswer-area">${question}${group.vocabulary ? `<details class="gvocab"><summary>Слова для упражнения</summary>${grammarTable(group.vocabulary)}</details>` : ""}</div></div>`;
    if (group.title === "Мини-проверка" && group.instruction) content = `<p class="muted ginstruction">${esc(group.instruction.replace(/ Затем нажми.*$/, ""))}</p>` + content;
  }
  const checked = response?.checked;
  const feedback = checked ? `<div class="fb" role="status"><h3>${response.good ? "✓ Верно" : "Пока неверно"}</h3>${response.good ? "" : `<span class="ans">Верный ответ: ${esc(response.slotValues ? group.questions[step.qi].answers[0] : group.questions[step.qi].answers.map(a=>gOptionLabel(group.questions[step.qi],a)).join(" / "))}</span>`}<span class="ex">${esc(group.questions[step.qi].explain)}</span></div>` : "";
  return `<div class="player gplayer"><div class="ptop"><div class="wrap"><button class="x" data-gexit aria-label="Выйти из урока">×</button><div class="bar" role="progressbar" aria-label="Прогресс урока" aria-valuemin="0" aria-valuemax="${G.steps.length}" aria-valuenow="${G.at}"><i style="width:${Math.round(G.at / G.steps.length * 100)}%"></i></div><span class="pcount">${G.at + 1}/${G.steps.length}</span></div></div>
    <div class="pbody"><div class="wrap"><span class="kicker">${esc(kicker)}</span><h2 id="g-title" tabindex="-1">${esc(title)}</h2>${content}</div></div>
    <div class="pfoot ${checked ? response.good ? "good" : "bad" : ""}"><div class="wrap">${feedback}<div class="gplayer-actions"><button class="btn ghost" data-gback${G.at ? "" : ' aria-label="Назад к разделам урока"'}>← Назад</button>${step.type === "question" && !checked ? gQuestionMode(group.questions[step.qi],response)==='choice' ? '<span class="muted gpick-hint">Нажми на вариант ответа</span>' : `<button class="btn" data-gcheck ${response.value.trim() ? "" : "disabled"}>Проверить</button>` : `<button class="btn" data-gnext>${G.at === G.steps.length - 1 ? "Завершить" : step.type === "intro" ? "Начать" : "Далее →"}</button>`}</div></div></div></div>`;
}
