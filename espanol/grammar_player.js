/* Пошаговый урок грамматики. Данные и проверка ответов общие с остальным сайтом. */
let G = null;
const G_SESSION_KEY = "espanol-cada-dia.grammar-session.v1";
const G_ATTEMPTS_KEY = "espanol-cada-dia.grammar-attempts.v1";
const G_CHOICE_ORDER_VERSION = 2;
// All grammar groups, including mini-checks, have exactly three lives.
const gHasLives = _group => true;
const gErrorLimit = _group => 3;
const gOutOfLives = (_group, errors) => errors >= 3;
function gAttempts() {
  try { const records=JSON.parse(store.get(G_ATTEMPTS_KEY) || '{}'); return records && typeof records==='object' && !Array.isArray(records) ? records : {}; }
  catch (_) { return {}; }
}
const gAttempt = (unit, group) => gAttempts()[grammarKey(unit,group)];
function gStoreAttempt(unit, group, attempt) {
  const records=gAttempts(); records[grammarKey(unit,group)]=attempt;
  store.set(G_ATTEMPTS_KEY,JSON.stringify(records));
}
function gChoiceSpecs(group) {
  const specs=[];
  group.questions.forEach((q,qi)=>{
    const fixed=group.shuffleOptions===false || q.shuffleOptions===false;
    // A guided task can retain an old full-answer list for saved legacy responses only.
    if(q.options) specs.push({key:String(qi),values:q.options,answer:q.answers.find(a=>!q.answerWarnings?.[a]) || q.answers[0],answers:q.options.filter(value=>grammarCorrect(q,value)),fixed:fixed || !!q.guidedGaps});
    if(q.guidedGaps) {
      const {parts,choices}=q.guidedGaps, matches=[];
      const visit=values=>{
        if(values.length===choices.length) {
          const answer=gComposeGaps(parts,values);
          const rank=q.answers.findIndex(a=>grammarNormalize(a)===grammarNormalize(answer));
          if(rank>=0)matches.push({rank,values});
        } else choices[values.length].forEach(value=>visit([...values,value]));
      };
      visit([]); matches.sort((a,b)=>a.rank-b.rank);
      choices.forEach((values,slot)=>specs.push({key:`${qi}:${slot}`,values,answer:matches[0]?.values[slot],answers:[...new Set(matches.map(m=>m.values[slot]))],fixed}));
    }
  });
  return specs;
}
function gChoicePermutation(order, values) {
  return Array.isArray(order) && order.length===values.length
    && values.every(value=>order.filter(v=>v===value).length===values.filter(v=>v===value).length);
}
function gShuffleChoices(values, random=Math.random) {
  const result=values.slice();
  for(let i=result.length-1;i>0;i--) {const j=Math.floor(random()*(i+1));[result[i],result[j]]=[result[j],result[i]];}
  return result;
}
function gChoiceBucketIssues(specs, orders) {
  const issues=[], size=specs[0]?.values.length;
  if(!size)return issues;
  const positions=specs.map(s=>orders[s.key]?.indexOf(s.answer)), counts=Array(size).fill(0);
  positions.forEach(p=>{if(p>=0)counts[p]++;});
  if(specs.some(s=>!gChoicePermutation(orders[s.key],s.values)) || positions.some(p=>!(p>=0)))return ['invalid'];
  // Small samples must not promise the learner a remaining position by an exact quota.
  if(specs.length>=Math.max(5,size)) {
    const expected=specs.length/size, tolerance=Math.max(1.5,Math.ceil(expected/4));
    if(counts.some(n=>Math.abs(n-expected)>tolerance))issues.push('imbalance');
    const accepted=Array(size).fill(0);
    specs.forEach(s=>orders[s.key].forEach((value,i)=>{if(s.answers.includes(value))accepted[i]++;}));
    const acceptedExpected=accepted.reduce((n,k)=>n+k,0)/size, acceptedTolerance=Math.max(1.5,Math.ceil(acceptedExpected/4));
    if(accepted.some(n=>Math.abs(n-acceptedExpected)>acceptedTolerance))issues.push('accepted-imbalance');
  }
  if(specs.length>=5 && Math.max(...counts)>=Math.ceil(specs.length*.8) && !issues.includes('imbalance'))issues.push('imbalance');
  for(let i=3;i<positions.length;i++)if(positions.slice(i-3,i+1).every(p=>p===positions[i])){issues.push('run');break;}
  for(let i=0;i+5<positions.length;i++) {
    const six=positions.slice(i,i+6);
    if([2,3].some(period=>six.every((p,k)=>p===six[k%period]))) {issues.push('cycle');break;}
    if(size>=3 && [1,size-1].some(delta=>six.slice(1).every((p,k)=>(p-six[k]+size)%size===delta))) {issues.push('cycle');break;}
  }
  return issues;
}
function gChoiceSequenceIssues(specs, orders) {
  const positions=specs.filter(s=>!s.fixed).map(s=>orders[s.key]?.indexOf(s.answer)), issues=[];
  for(let i=3;i<positions.length;i++)if(positions.slice(i-3,i+1).every(p=>p===positions[i])){issues.push('run');break;}
  for(let i=0;i+5<positions.length;i++) {
    const six=positions.slice(i,i+6), size=Math.max(...six)+1;
    if([2,3].some(period=>six.every((p,k)=>p===six[k%period]))
       || (size>=3 && [1,size-1].some(delta=>six.slice(1).every((p,k)=>(p-six[k]+size)%size===delta)))){issues.push('cycle');break;}
  }
  return issues;
}
function gChoiceOrderIssues(group, orders) {
  const buckets=new Map(), issues=[], specs=gChoiceSpecs(group);
  for(const spec of specs) {
    if(!gChoicePermutation(orders?.[spec.key],spec.values))issues.push({kind:'invalid',key:spec.key});
    if(spec.fixed)continue;
    const bucket=buckets.get(spec.values.length) || [];bucket.push(spec);buckets.set(spec.values.length,bucket);
  }
  for(const [size,items] of buckets)for(const kind of gChoiceBucketIssues(items,orders || {}))issues.push({kind,size});
  for(const kind of gChoiceSequenceIssues(specs,orders || {}))issues.push({kind,scope:'exercise'});
  return issues;
}
function gPlanChoiceOrders(group, random=Math.random, round=0) {
  if(round===0) {
    // Expand one random seed into a stream, so a low-entropy draw cannot repeat a layout per question.
    let state=Math.floor(random()*4294967296)>>>0;
    random=()=>{state=(state+0x6D2B79F5)>>>0;let x=state;x=Math.imul(x^(x>>>15),x|1);x^=x+Math.imul(x^(x>>>7),x|61);return ((x^(x>>>14))>>>0)/4294967296;};
  }
  const orders={}, buckets=new Map();
  for(const spec of gChoiceSpecs(group)) {
    orders[spec.key]=spec.values.slice();
    if(!spec.fixed) {const bucket=buckets.get(spec.values.length) || [];bucket.push(spec);buckets.set(spec.values.length,bucket);}
  }
  for(const [size,specs] of buckets) {
    let best=null, bestScore=Infinity;
    for(let trial=0;trial<256;trial++) {
      let slots;
      if(specs.length<Math.max(5,size))slots=specs.map(()=>Math.floor(random()*size));
      else {
        const expected=specs.length/size, tolerance=Math.max(1.5,Math.ceil(expected/4));
        const counts=Array(size).fill(Math.floor(expected));
        gShuffleChoices(Array.from({length:size},(_,i)=>i),random).slice(0,specs.length%size).forEach(i=>counts[i]++);
        // Vary the counts within the allowed range: balanced does not mean a fixed quota.
        for(let i=0;i<specs.length;i++) {
          const from=Math.floor(random()*size),to=Math.floor(random()*size);
          if(from!==to && counts[from]>0 && Math.abs(counts[from]-1-expected)<=tolerance && Math.abs(counts[to]+1-expected)<=tolerance){counts[from]--;counts[to]++;}
        }
        slots=gShuffleChoices(counts.flatMap((n,i)=>Array(n).fill(i)),random);
      }
      const candidate={};
      specs.forEach((s,i)=>{const rest=s.values.slice();rest.splice(rest.indexOf(s.answer),1);const shuffled=gShuffleChoices(rest,random);shuffled.splice(slots[i],0,s.answer);candidate[s.key]=shuffled;});
      const score=gChoiceBucketIssues(specs,candidate).length;
      if(score<bestScore){best=candidate;bestScore=score;}
      if(!score)break;
    }
    Object.assign(orders,best);
  }
  // Different option counts can be interleaved in one exercise; inspect their combined sequence too.
  if(round<64 && gChoiceOrderIssues(group,orders).length)return gPlanChoiceOrders(group,random,round+1);
  return orders;
}
function gEnsureChoiceOrders(group, attempt) {
  const specs=gChoiceSpecs(group), previous=attempt.optionOrders;
  const valid=previous && typeof previous==='object' && !Array.isArray(previous) ? previous : {};
  const migrating=attempt.choiceOrderVersion!==G_CHOICE_ORDER_VERSION;
  if(!migrating && specs.every(s=>gChoicePermutation(valid[s.key],s.values)))return false;
  const seen=new Set(Object.keys(attempt.responses || {}));
  const current=G?.steps[G.at];
  if(current?.type==='question' && current.group===group.id && gGroups(gUnit()).includes(group))seen.add(String(current.qi));
  const lockedQuestions=new Set(), locked={};
  for(const spec of specs) {
    const qi=spec.key.split(':')[0], saved=gChoicePermutation(valid[spec.key],spec.values);
    // Old attempts keep every visited question; current plans keep every valid order.
    // Missing plans for unseen questions must never fall back to the biased source array.
    if(spec.fixed || seen.has(qi) || (!migrating && saved)) {
      locked[spec.key]=saved?valid[spec.key]:spec.values.slice();
      // A fixed legacy full-answer list must not freeze unseen guided slots.
      if(!spec.fixed)lockedQuestions.add(+qi);
    }
  }
  const remaining={...group,questions:group.questions.map((q,i)=>lockedQuestions.has(i)?{...q,shuffleOptions:false}:q)};
  attempt.optionOrders={...valid,...gPlanChoiceOrders(remaining),...locked};
  attempt.choiceOrderVersion=G_CHOICE_ORDER_VERSION;
  return true;
}
function gOrderedChoices(group, qi, slot=null, attempt=null) {
  const q=group.questions[qi], source=slot===null?q.options:q.guidedGaps.choices[slot];
  const key=slot===null?String(qi):`${qi}:${slot}`, order=attempt?.optionOrders?.[key];
  return gChoicePermutation(order,source)?order:source;
}
function gNewAttempt(group, responses={}) {
  const errors=Object.values(responses).filter(r=>r.checked && !r.good).length;
  const attempt={id:Date.now().toString(36)+'-'+Math.random().toString(36).slice(2),revision:group.revision || 1,errors,limit:gErrorLimit(group),status:gOutOfLives(group,errors)?'failed':'active',responses};
  if(Object.keys(responses).length)gEnsureChoiceOrders(group,attempt);
  else {attempt.optionOrders=gPlanChoiceOrders(group);attempt.choiceOrderVersion=G_CHOICE_ORDER_VERSION;}
  return attempt;
}
function gRefreshAttemptVersions(unit) {
  const records=gAttempts(), current=G.steps[G.at]; let changed=false, restartGroup=null;
  G.groupRevisions ||= {};
  for(const group of gGroups(unit)) {
    const key=grammarKey(unit,group), old=records[key], revision=group.revision || 1;
    const savedRevision=old?.revision ?? G.groupRevisions[group.id] ?? 1;
    if(savedRevision!==revision && (old || Object.keys(G.responses[group.id] || {}).length)) {
      records[key]=gNewAttempt(group); changed=true;
      G.responses[group.id]={}; G.attemptIds[group.id]=records[key].id;
      // Old answers and old correction steps belong to different questions.
      G.steps=G.steps.filter(s=>s.group!==group.id || !s.correction);
      if(current?.group===group.id || G.recovery===group.id) {
        restartGroup=group;
        G.ended=false; if(G.recovery===group.id) delete G.recovery;
      }
    }
    G.groupRevisions[group.id]=revision;
  }
  if(restartGroup) {
    const start=G.steps.findIndex(s=>(s.group===restartGroup.id && s.type==='intro')
      || (s.type==='theory' && unit.sections[s.section].check?.id===restartGroup.id));
    G.at=start>=0 && gRouteOpen(unit,gStepRoute(unit,G.steps[start])) ? start
      : Math.max(0,G.steps.findIndex(s=>gRouteOpen(unit,gStepRoute(unit,s)) && !gRouteDone(unit,gStepRoute(unit,s))));
  }
  else if(current) G.at=Math.max(0,G.steps.indexOf(current));
  if(changed) store.set(G_ATTEMPTS_KEY,JSON.stringify(records));
}
function gEnsureAttempt(unit, group) {
  G.attemptIds ||= {};
  let attempt=gAttempt(unit,group);
  if(attempt && (attempt.revision || 1)!==(group.revision || 1)) {
    gRefreshAttemptVersions(unit); attempt=gAttempt(unit,group);
  }
  if(attempt && attempt.limit!==gErrorLimit(group)) {
    // Never resurrect spent lives, discard completed progress, or change question ids.
    attempt.limit=3;
    if(!['passed','review'].includes(attempt.status) && gOutOfLives(group,attempt.errors)) attempt.status='failed';
    gStoreAttempt(unit,group,attempt);
  }
  if(G.attemptIds[group.id] !== attempt?.id || !attempt) {
    const old=G.responses[group.id] || {};
    if(!attempt || (attempt.status==='passed' && !G.resumed && !G.attemptIds[group.id])) {
      attempt=gNewAttempt(group, G.resumed ? old : {});
      // Completed attempts from before the limit keep their earned progress.
      if(G.resumed && group.questions.every((_,i)=>old[i]?.checked) && P.grammar?.[grammarKey(unit,group)]) attempt.status='passed';
      gStoreAttempt(unit,group,attempt);
    }
    G.responses[group.id]=attempt.responses;
    G.attemptIds[group.id]=attempt.id;
  }
  if(gEnsureChoiceOrders(group,attempt))gStoreAttempt(unit,group,attempt);
  if(attempt.status==='review') G.recovery=group.id;
  return attempt;
}
function gFlushAttempt() {
  const groupId=G.recovery || G.steps[G.at]?.group;
  const group=gGroups(gUnit()).find(g=>g.id===groupId);
  if(!group || !G.responses[groupId]) return;
  const attempt=gEnsureAttempt(gUnit(),group);
  // A second tab or an older screen cannot overwrite a submitted answer.
  for(const [i,response] of Object.entries(G.responses[groupId])) {
    if(!attempt.responses[i]?.checked) attempt.responses[i]=response;
    else if(response.correction && !attempt.responses[i].correction?.checked) attempt.responses[i].correction=response.correction;
  }
  G.responses[groupId]=attempt.responses;
  gStoreAttempt(gUnit(),group,attempt);
}
function gTheorySections(unit, group) {
  const own=unit.sections.findIndex(s=>s.check?.id===group.id);
  return own>=0 ? [own] : group.theorySections || [0];
}
function gReviewTheory() {
  const unit=gUnit(), group=gGroups(unit).find(g=>g.id===(G.recovery || G.steps[G.at]?.group));
  if(!group) return;
  const attempt=gAttempt(unit,group);
  if(attempt?.status!=='failed') return;
  attempt.status='review'; attempt.reviewAt=0;
  G.recovery=group.id; // Only an explicit click opens the related rule.
  gStoreAttempt(unit,group,attempt); gSave(); render();
}
function gReviewMove(delta) {
  const unit=gUnit(), group=gGroups(unit).find(g=>g.id===G.recovery), attempt=group && gAttempt(unit,group);
  if(attempt?.status!=='review') return;
  if(delta<0 && !attempt.reviewAt) return gReturnToMistake();
  attempt.reviewAt=Math.max(0,Math.min(gTheorySections(unit,group).length-1,(attempt.reviewAt||0)+delta));
  gStoreAttempt(unit,group,attempt); gSave(); render();
}
function gReturnToMistake() {
  if(!G?.recovery) return;
  const unit=gUnit(), group=gGroups(unit).find(g=>g.id===G.recovery);
  const attempt=group && gAttempt(unit,group);
  if(attempt?.status!=='review') return;
  attempt.status='failed';
  gStoreAttempt(unit,group,attempt);
  G.recovery=null;
  gSave(); render();
}
// «Назад» браузера в плеере: есть ли предыдущий шаг (иначе выход к разделам урока).
function gCanBack() {
  if(!G) return false;
  if(G.recovery) {
    const unit=gUnit(), group=gGroups(unit).find(g=>g.id===G.recovery), attempt=group && gAttempt(unit,group);
    return attempt?.status==='review';
  }
  return !G.ended && G.at>0;
}
function gRepeatExercise() {
  const unit=gUnit(), group=gGroups(unit).find(g=>g.id===(G.recovery || G.steps[G.at]?.group)), attempt=group && gAttempt(unit,group);
  if(!attempt || (attempt.status!=='failed' && !(attempt.status==='review' && attempt.reviewAt===gTheorySections(unit,group).length-1))) return;
  const freshAttempt=gNewAttempt(group); gStoreAttempt(unit,group,freshAttempt);
  G.responses[group.id]={}; G.attemptIds[group.id]=freshAttempt.id;
  G.recovery=null; G.retry=false; G.ended=false;
  G.steps=gSteps(unit,G.route);
  G.at=G.steps.findIndex(s=>s.group===group.id);
  gSave(); render();
}
function gHearts(attempt, group) {
  if(!gHasLives(group)) return '';
  const limit=gErrorLimit(group), left=Math.max(0,limit-(attempt?.errors||0));
  return `<span class="ghearts" role="img" aria-label="Осталось попыток: ${left} из ${limit}">${Array.from({length:limit},(_,i)=>`<span aria-hidden="true"${i>=left?' class="is-empty"':''}>♥</span>`).join('')}</span>`;
}
function gBlockInfo(unit, step) {
  const group=step.group && gGroups(unit).find(g=>g.id===step.group);
  const sectionIndex=step.type==='theory'?step.section:step.group?unit.sections.findIndex(s=>s.check?.id===step.group):-1;
  if(sectionIndex>=0) {
    const section=unit.sections[sectionIndex], total=1+(section.check?.questions.length || 0);
    return {meta:`Юнит ${unit.number} · Теория ${unit.number}.${sectionIndex+1}`,title:section.title,progress:`${step.type==='question'?step.qi+2:1} из ${total}`};
  }
  if(group) {
    const title=group.title.startsWith(group.id+' · ')?group.title.slice(group.id.length+3):group.title;
    let progress=`${step.type==='intro'?0:step.qi+1} из ${group.questions.length}`;
    if(step.correction) {
      const queue=G.steps.filter(s=>s.correction&&s.group===group.id);
      progress=`Повторение · ${queue.findIndex(s=>s.qi===step.qi)+1} из ${queue.length}`;
    }
    return {meta:`Юнит ${unit.number} · Упражнение ${group.id}`,title,progress};
  }
  return {meta:`Юнит ${unit.number} · Памятка`,title:'Что запомнить',progress:'1 из 1'};
}
function gContext(unit, step, heading=false, reviewProgress='') {
  const info=gBlockInfo(unit,step);
  if(step.correction) { const queue=G.steps.filter(s=>s.correction&&s.group===step.group);info.progress=`Повторение · ${queue.findIndex(s=>s.qi===step.qi)+1} из ${queue.length}`; }
  return `<div class="wrap gcontext" aria-label="Текущий раздел"><div class="gcontext-copy"><span class="gcontext-meta">${esc(info.meta)}</span><${heading?'h2 id="g-title" tabindex="-1"':'span'} class="gcontext-title" title="${esc(info.title)}">${esc(info.title)}</${heading?'h2':'span'}></div><span class="gcontext-progress">${esc(reviewProgress || info.progress)}</span></div>`;
}
function gRecoveryView(unit) {
  const group=gGroups(unit).find(g=>g.id===G.recovery), attempt=gAttempt(unit,group);
  if(attempt.status==='review') {
    const sections=gTheorySections(unit,group), at=attempt.reviewAt||0, section=unit.sections[sections[at]], last=at===sections.length-1;
    return `<div class="player gplayer"><div class="ptop"><div class="wrap"><button class="x" data-gexit aria-label="Выйти из урока">×</button><span class="greview-label">Повторение правила</span><span class="pcount">${at+1}/${sections.length}</span></div>${gContext(unit,{type:"theory",section:sections[at]},true,`Повторение · ${at+1} из ${sections.length}`)}</div><div class="pbody"><div class="wrap">${gTheory(section)}</div></div><div class="pfoot"><div class="wrap gplayer-actions greview-actions"><button class="btn ghost" data-greview-mistake>← К разбору ошибки</button>${at?'<button class="btn ghost" data-greview-back>← Назад по теории</button>':''}<button class="btn" ${last?'data-grepeat-exercise':'data-greview-next'}>${last?'Попробовать ещё раз':'Далее →'}</button></div></div></div>`;
  }
  // Persisted error identity wins over the current screen (back/reopen/multiple tabs).
  const last=attempt.lastError;
  const qi=Number.isInteger(last?.qi) && group.questions[last.qi] ? last.qi
    : Object.keys(attempt.responses || {}).map(Number).filter(i=>group.questions[i] && attempt.responses[i]?.checked && !attempt.responses[i].good).at(-1);
  if(qi===undefined) return `<div class="player gplayer"><div class="pbody"><div class="wrap"><h2>Попытка завершена</h2><p>Сохранённый ответ недоступен. Повтори правило и начни заново.</p></div></div><div class="pfoot"><button class="btn" data-greview-theory>Вернуться к теории</button></div></div>`;
  const original=attempt.responses[qi], correction=original?.correction;
  const saved=correction?.checked && last?.qi===qi && correction.value===last.value ? correction : original;
  const response={...saved,value:last?.qi===qi ? last.value : saved.value,checked:true,good:false};
  return gPlayerView({group,attempt,qi,response});
}
const gUnit = () => (COURSE.grammar || []).find(u => u.id === G?.unit);
function gSyncViewport() {
  const player=document.querySelector('.gplayer');
  if(!player?.style) return;
  const viewport=window.visualViewport, active=document.activeElement;
  if(viewport) {
    player.style.height=`${viewport.height}px`;
    player.style.top=`${viewport.offsetTop || 0}px`;
  }
  const typing=!!active?.matches?.('.gplayer input:not(:disabled), .gplayer textarea:not(:disabled)');
  player.classList.toggle('is-typing',typing);
  player.classList.toggle('is-short',typing && (viewport?.height || window.innerHeight)<600);
  const body=player.querySelector?.('.pbody');
  if(typing && body && body.scrollHeight<=body.clientHeight+2) body.scrollTop=0;
  // A clock or a long prompt can push the focused field below the fixed footer.
  // Scroll only the exercise body, keeping the field and its character keys visible.
  const field=typing && active.getBoundingClientRect?.(), bounds=body?.getBoundingClientRect?.();
  if(field && bounds && bounds.bottom>bounds.top) {
    const keys=(active.parentElement?.querySelector?.('.gaccents') || active.closest?.('.gfill-sentence')?.querySelector?.('.gaccents'))?.getBoundingClientRect?.();
    let bottom=keys?.bottom || field.bottom;
    if(bottom-field.top>bounds.bottom-bounds.top-24) bottom=field.bottom;
    if(field.top<bounds.top+12) body.scrollTop-=bounds.top+12-field.top;
    else if(bottom>bounds.bottom-12) body.scrollTop+=bottom-bounds.bottom+12;
  }
}
function gHideKeyboard() {
  document.activeElement?.blur?.();
  gSyncViewport();
}
function gToggleFeedback() {
  if(!G || G.ended || G.recovery) return;
  const response=gResponse(G.steps[G.at]);
  if(!response?.checked) return;
  response.feedbackHidden=!response.feedbackHidden;
  const group=gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group), attempt=gAttempt(gUnit(),group);
  if(G.steps[G.at].correction) attempt.responses[G.steps[G.at].qi].correction=response;
  else attempt.responses[G.steps[G.at].qi]=response;
  gStoreAttempt(gUnit(),group,attempt); G.responses[group.id]=attempt.responses;
  gSave(); render();
  document.querySelector('[data-gfeedback-toggle]')?.focus({preventScroll:true});
}
window.visualViewport?.addEventListener('resize',gSyncViewport);
window.visualViewport?.addEventListener('scroll',gSyncViewport);
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
function gSave() { if (G) { gFlushAttempt(); store.set(G_SESSION_KEY, JSON.stringify(G)); } }
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
  if (!unit || !(route==='all' ? gCanStartUnit(unit) : gRouteOpen(unit, route))) return;
  const steps = gSteps(unit, route);
  if (saved?.unit === unit.id && Array.isArray(saved.steps) && saved.steps.length && saved.at >= 0 && saved.at < saved.steps.length) {
    const restoredRoute=gRouteOpen(unit,saved.route)?saved.route:'all';
    const reordered=saved.retry && restoredRoute===saved.route && (saved.unitRevision || 1)===(unit.revision || 1) ? saved.steps : gSteps(unit,restoredRoute);
    const old=saved.steps[saved.at];
    let at=reordered.findIndex(s=>s.type===old.type && s.section===old.section && s.group===old.group && s.qi===old.qi && !!s.correction===!!old.correction);
    if(at<0 || !gRouteOpen(unit,gStepRoute(unit,reordered[at]))) at=reordered.findIndex(s=>gRouteOpen(unit,gStepRoute(unit,s)) && !gRouteDone(unit,gStepRoute(unit,s)));
    G={...saved,route:restoredRoute,steps:reordered,at:Math.max(0,at),responses:saved.responses || {},attemptIds:{},resumed:true};
  }
  else if (steps.length) G = {unit:unit.id, route, steps, at:0, responses:{}, ended:false};
  else return;
  G.unitRevision=unit.revision || 1; G.attemptIds ||= {};
  gRefreshAttemptVersions(unit);
  // Migrate sessions which used to force failed attempts to a separate screen.
  if(G.recovery) {
    const failed=gGroups(unit).find(g=>g.id===G.recovery), attempt=failed && gAttempt(unit,failed);
    if(attempt?.status==='failed') {
      const wrong=G.steps.filter(s=>s.group===failed.id && s.type==='question' && attempt.responses[s.qi]?.checked && !attempt.responses[s.qi]?.good);
      if(wrong.length) G.at=G.steps.indexOf(wrong.at(-1));
      G.recovery=null;
    }
  }
  view.grammar = unit.id; view.tab = "grammar"; S = null;
  gSave(); render();
}
function gResponse(step) {
  if (step.type !== "question") return null;
  const group=gGroups(gUnit()).find(g=>g.id===step.group);
  gEnsureAttempt(gUnit(),group);
  if(G.steps[G.at]!==step) return null;
  G.responses[step.group] ||= {};
  const response=G.responses[step.group][step.qi] ||= {value:"", checked:false};
  const q=gGroups(gUnit()).find(g=>g.id===step.group)?.questions[step.qi];
  if(Array.isArray(response.chosen) && q?.tiles && response.chosen.map(i=>q.tiles[i]).join(' ')!==response.value) delete response.chosen;
  const current=step.correction ? (response.correction ||= {value:'',checked:false}) : response;
  // Reopen earlier accepted answers with today's recommendation, without changing scores or lives.
  if(current.checked && grammarCorrect(q,current.value)) {
    delete current.warning; Object.assign(current,grammarResult(q,current.value,group,false));
  }
  return current;
}
function gAttemptErrors(attempt) {
  if(Array.isArray(attempt.errorHistory)) return attempt.errorHistory;
  const errors=[];
  for(const [qi,response] of Object.entries(attempt.responses || {})) {
    if(response.checked && !response.good) errors.push({qi:Number(qi),value:response.value});
    if(response.correction?.checked && !response.correction.good) errors.push({qi:Number(qi),value:response.correction.value});
  }
  const last=attempt.lastError;
  if(last && !errors.some(e=>e.qi===last.qi && e.value===last.value)) errors.push(last);
  return errors;
}
function gRecordError(attempt,qi,value) {
  attempt.errors++;
  attempt.lastError={qi,value};
  attempt.errorHistory.push({qi,value});
}
function gCheck() {
  if(!G || G.ended || G.recovery) return;
  const step = G.steps[G.at], response = gResponse(step);
  if (!response || response.checked || !response.value.trim()) return;
  const unit = gUnit(), group = gGroups(unit).find(g => g.id === step.group);
  const attempt=gAttempt(unit,group);
  attempt.errorHistory ||= gAttemptErrors(attempt);
  const assessment=grammarResult(group.questions[step.qi],response.value,group,gQuestionMode(group.questions[step.qi],response)==='input');
  if(step.correction) {
    if(!['correcting','passed'].includes(attempt.status)) return;
    if(attempt.responses[step.qi]?.correction?.checked) { G.responses[group.id]=attempt.responses; return; }
    response.checked=true; Object.assign(response,assessment);
    attempt.responses[step.qi].correction=response;
    if(!response.good) {
      gRecordError(attempt,step.qi,response.value);
      if(gOutOfLives(group,attempt.errors)) attempt.status='failed';
    } else if(group.questions.every((_,i)=>attempt.responses[i]?.good || attempt.responses[i]?.correction?.good)) {
      attempt.status='passed'; gStoreAttempt(unit,group,attempt);
      gradeGrammar(unit,group,group.questions.map((_,i)=>attempt.responses[i].value));
    }
    G.responses[group.id]=attempt.responses; gStoreAttempt(unit,group,attempt);
    gSave(); render(); sfx(response.status==='almost'?'almost':response.good); return;
  }
  if(attempt.status!=='active') { gSave(); render(); return; }
  if(attempt.responses[step.qi]?.checked) {
    G.responses[group.id]=attempt.responses; gSave(); render(); return;
  }
  response.checked = true;
  Object.assign(response,assessment);
  attempt.responses[step.qi]=response;
  if(!response.good) gRecordError(attempt,step.qi,response.value);
  if(gOutOfLives(group,attempt.errors)) attempt.status='failed';
  else if(group.questions.every((_,i)=>attempt.responses[i]?.checked)) attempt.status=attempt.errors?'correcting':'passed';
  G.responses[group.id]=attempt.responses;
  gStoreAttempt(unit,group,attempt);
  if (attempt.status==='passed') {
    gradeGrammar(unit, group, group.questions.map((_, i) => G.responses[group.id][i].value));
  }
  gSave(); render(); sfx(response.status==='almost'?'almost':response.good);
}
function gPick(index) {
  const step=G?.steps[G.at], q=step?.group && gGroups(gUnit()).find(g=>g.id===step.group)?.questions[step.qi];
  if(Number.isInteger(index) && q?.options?.[index]!==undefined)gPickValue(q.options[index]);
}
function gPickValue(value) {
  if (!G || G.ended || G.recovery) return;
  const step = G.steps[G.at], response = gResponse(step);
  if (!response || response.checked) return;
  const options = gGroups(gUnit()).find(g => g.id === step.group).questions[step.qi].options;
  if (!options?.includes(value)) return;
  response.value = value;
  gCheck();
}
function gQuestionMode(q, response) {
  if (q.guidedGaps && (response.slotValues || !response.value)) return 'gaps';
  // An unfinished answer from the old typing interface remains editable after the update.
  if (q.tiles && !(response.value && !response.checked && !Array.isArray(response.chosen))) return 'build';
  return q.options ? 'choice' : 'input';
}
function gNoArticleControl(group,response) {
  return group.allowNoArticle ? `<button type="button" class="btn ghost gno-article" data-gno-article aria-pressed="${grammarNormalize(response.value)==='без артикля'}" ${response.checked?'disabled':''}>Без артикля</button>` : '';
}
function gNoArticle() {
  if(!G || G.ended || G.recovery) return;
  const step=G.steps[G.at], response=gResponse(step), group=gGroups(gUnit()).find(g=>g.id===step.group);
  if(!response || response.checked || !group?.allowNoArticle || gQuestionMode(group.questions[step.qi],response)!=='input') return;
  response.value='∅'; gSave();
  const input=document.getElementById('g-answer');
  if(input) {input.value=response.value;input.focus({preventScroll:true});input.select();}
  const check=document.querySelector('[data-gcheck]'); if(check)check.disabled=false;
  document.querySelector('[data-gno-article]')?.setAttribute('aria-pressed','true');
}
function gBuild(action, index) {
  if (!G || G.ended || G.recovery) return;
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
function gAnswerHint(q) { return q.answerHint && !q.answers?.some(a=>grammarNormalize(a)===grammarNormalize(q.answerHint)) ? `<p class="ganswer-hint">Нужно сказать: <strong>«${esc(q.answerHint)}»</strong></p>` : ''; }
function gBuilder(q,response) { return `<div class="gbuild">${gBuilderContents(q,response)}</div>`; }
function gComposeGaps(parts, values) {
  return parts.map((part,i)=>part+(values[i] || '')).join('').trim();
}
function gSelectGap(slot, option) {
  if (!G || G.ended || G.recovery) return;
  const response=gResponse(G.steps[G.at]);
  const group=gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group), q=group?.questions[G.steps[G.at].qi];
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
    area.innerHTML=gGuidedContents(q,response,group,G.steps[G.at].qi);
    area.querySelector(`[data-gslot="${response.activeGap}"]`)?.focus({preventScroll:true});
  }
  const check=document.querySelector('[data-gcheck]'); if(check)check.disabled=!response.value;
}
function gSelectGapValue(slot,value) {
  const step=G?.steps[G.at], q=step?.group && gGroups(gUnit()).find(g=>g.id===step.group)?.questions[step.qi];
  const choices=q?.guidedGaps?.choices[slot];
  if(choices?.includes(value))gSelectGap(slot,choices.indexOf(value));
}
function gGuidedContents(q,response,group=null,qi=null) {
  const {parts,choices}=q.guidedGaps, values=response.slotValues || [], active=response.activeGap || 0;
  const [before,after]=q.prompt.split('___');
  const wrong=response.checked&&!response.good?gGapMistakes(q,response,group)?.wrong:null;
  return `${gAnswerHint(q)}<p class="gguided-sentence" lang="es">${esc(before)}${parts.map((part,i)=>`${esc(part)}${i<choices.length ? `<button class="gguided-slot ${wrong?.[i]?'is-incorrect':''} ${i===active && !response.checked?'is-active':''}" data-gslot="${i}" aria-label="Пропуск ${i+1}${wrong?.[i]?', неверно':''}${values[i]?': '+esc(values[i]):''}" ${response.checked?'disabled':''}>${esc(values[i] || '…')}<small aria-hidden="true">${i+1}</small></button>`:''}`).join('')}${esc(after || '')}</p>${response.checked?'':`<div class="gguided-options" role="group" aria-label="Варианты для пропуска ${active+1}"><p class="muted">Выбери слово для пропуска ${active+1} из ${choices.length}</p><div class="gbuild-bank">${(group?gOrderedChoices(group,qi,active,gAttempt(gUnit(),group)):choices[active]).map(word=>`<button class="gtile" data-gslot-choice="${choices[active].indexOf(word)}" data-gslot-value="${esc(word)}" data-slot="${active}" lang="es" aria-pressed="${values[active]===word}">${esc(word)}</button>`).join('')}</div></div>`}`;
}
function gGuided(q,response,group,qi) { return `<div class="gguided">${gGuidedContents(q,response,group,qi)}</div>`; }
function gMove(delta) {
  if(!G) return;
  if(G.recovery) return gReviewMove(delta);
  const selected=G.steps[G.at];
  if(selected?.type==='question') {
    const group=gGroups(gUnit()).find(g=>g.id===selected.group);
    if(group && gAttempt(gUnit(),group)?.status==='failed') return;
  }
  if (delta < 0 && G.at === 0) return gExit();
  const step = G.steps[G.at];
  if (delta > 0 && step.type === "question" && !gResponse(step)?.checked) return;
  if (delta > 0 && (step.type === "summary" || (step.type === "theory" && !gUnit().sections[step.section].check))) {
    P.grammarRead ||= {}; P.grammarRead[`${G.unit}/${gStepRoute(gUnit(),step)}`] = true; save();
  }
  if(delta>0 && step.type==='question') {
    const group=gGroups(gUnit()).find(g=>g.id===step.group), attempt=gAttempt(gUnit(),group);
    if(step.correction && !gResponse(step).good) {
      delete attempt.responses[step.qi].correction;
      G.responses[group.id]=attempt.responses; gStoreAttempt(gUnit(),group,attempt);
      gSave(); render(); return;
    }
    if(!step.correction && attempt.status==='correcting' && !G.steps.some(s=>s.group===group.id && s.correction)) {
      const wrong=group.questions.flatMap((_,qi)=>attempt.responses[qi].good?[]:[{type:'question',group:group.id,qi,correction:true}]);
      G.steps.splice(G.at+1,0,...wrong); G.retry=true;
    }
  }
  // A separately opened final exercise must lead into the recap as well.
  if(delta>0 && G.at===G.steps.length-1 && step.type==='question'
      && gNextRoute(gUnit(),G.route)==='summary' && gRouteOpen(gUnit(),'summary')) {
    G.steps.push({type:'summary'}); G.retry=true;
  }
  const target = G.steps[G.at + delta];
  if (target && !gRouteOpen(gUnit(), gStepRoute(gUnit(),target))) return;
  if (delta > 0 && G.at === G.steps.length - 1) G.ended = true;
  else G.at = Math.max(0, Math.min(G.steps.length - 1, G.at + delta));
  gSave(); render();
}
function gExit() { gSave(); G = null; view.tab = "grammar"; render(); }
function gRetry() {
  if(!G || !G.ended || G.recovery) return;
  const wrong=G.steps.filter(s=>s.type==='question' && !s.correction && !G.responses[s.group]?.[s.qi]?.good);
  if(!wrong.length) return;
  for(const id of new Set(wrong.map(s=>s.group))) {
    const group=gGroups(gUnit()).find(g=>g.id===id), attempt=gEnsureAttempt(gUnit(),group);
    if(gOutOfLives(group,attempt.errors)) return;
    for(const s of wrong.filter(s=>s.group===id)) delete attempt.responses[s.qi].correction;
    attempt.status='correcting'; G.responses[id]=attempt.responses; gStoreAttempt(gUnit(),group,attempt);
  }
  G.steps=wrong.map(s=>({...s,correction:true})); G.at=0; G.ended=false; G.retry=true;
  gSave(); render();
}
function gNextRoute(unit, route) {
  const routes = gRoutes(unit);
  return route === "all" ? null : routes[routes.indexOf(route) + 1];
}
function gSubmitGrammarForm(unit, group, values) {
  const section=unit.sections.findIndex(s=>s.check?.id===group.id);
  const route=section>=0 ? `section:${section}` : `exercise:${group.id}`;
  gStart(unit.id,route);
  if(!G || G.unit!==unit.id || G.route!==route || G.recovery) return;
  for(let qi=0;qi<group.questions.length;qi++) {
    G.at=G.steps.findIndex(s=>s.group===group.id && s.qi===qi);
    const response=gResponse(G.steps[G.at]);
    if(!response.checked) { response.value=values[qi] || ''; gCheck(); }
    if(G.recovery || gAttempt(unit,group)?.status==='failed' || !response.checked) break;
  }
  if(!G.recovery && ['passed','correcting'].includes(gAttempt(unit,group)?.status)) gMove(1);
  gSave(); render();
}
const G_UNIT_ICONS = {
  '001_el_hijo_la_hija': '👥',
  '002_el_libro_la_mesa': '🐾',
  '003_libro_libros': '📚',
  '004_articulo_indefinido': '🎲',
  '005_sin_articulo': '🚗',
  '006_articulo_definido': '🔎',
  '007_un_perro_el_perro': '🐕',
  '008_nombres_propios': '📍',
  '009_tiempo_fecha': '📅',
  '010_usos_articulo': '🎸',
  '011_el_rojo_uno_rojo': '🎨',
  '012_demostrativos': '👈',
  '013_adjetivos': '✨',
  '014_gentilicios': '🌎',
  '015_mas_caro': '⚖️',
  '016_tan_alto': '🟰',
  '017_la_mas_alta': '🏆',
  '018_mi_tu_su': '🏠',
  '019_mio_tuyo_suyo': '🔑',
  '020_todos_algunos_ninguno': '🧺',
  '021_uno_otro_cualquiera': '🧩',
  '022_mucho_poco': '🥣',
  '023_alguien_algo': '🚪',
  '024_mas_menos_tanto': '📊',
  '025_uno_dos_tres': '🔢',
  '026_cien_mil_millon': '💶',
  '027_primero_segundo': '🏢',
  '028_relativos_que': '🔗',
  '029_cuyo_donde_cuando': '🧭',
  '030_quien_que': '❔',
  '031_cual_que': '🎯',
  '032_cuando_donde': '⏱️',
  '033_exclamativos': '❗',
  '034_yo_tu_el': '🗣️',
  '035_te_amo': '💞',
  '036_me_han_regalado': '🎁',
  '037_se_lo_he_dado': '📨',
  '038_lo_la_le': '🪞',
  '039_amame_damelo': '✍️',
  '040_me_ducho_nos_queremos': '🚿',
  '041_para_mi_contigo': '🤝',
  '047_hay_estar': '🏙️',
  '048_trabajo_como_vivo': '💼',
  '049_quiero_mido_sueno': '🔄',
  '050_voy_hago_conozco': '🚶',
  '051_manana_voy_al_medico': '🗓️',
  '046_hay': '🥛',
  '045_tengo_tienes_tiene': '👜',
  '044_ser_estar': '🎭',
  '043_estoy_estas_esta': '🌡️',
  '042_soy_eres_es': '🪪',
};
function gUnitComplete(unit) {
  const routes=gRoutes(unit);
  return routes.length>0 && routes.every(route=>gRouteDone(unit,route));
}
function grammarView() {
  const units = COURSE.grammar || [], unit = units.find(u => u.id === view.grammar);
  if (!unit) return `<button class="btn ghost sm back" data-tab="home">← Главная</button><h2>📐 Грамматика</h2><p class="muted">Пройдено тем: ${units.filter(gUnitComplete).length} из ${units.length}</p><div class="menu">${units.map(u => {
    const done=gUnitComplete(u);
    return `<button class="mcard ${done?'gcomplete':''}" data-grammar="${esc(u.id)}"><span class="mi" aria-hidden="true">${G_UNIT_ICONS[u.id] || '📖'}</span><span><b>${u.number}. ${esc(u.title)}</b><small>${esc(u.subtitle)}</small>${done?'<span class="gcompleted-badge"><span aria-hidden="true">✓</span> Пройдено</span>':''}</span><span aria-hidden="true">›</span></button>`;
  }).join("")}</div>`;
  const saved = gSaved(), resume = saved?.unit === unit.id && !saved.ended && saved.steps?.[saved.at];
  const row = (route, title, subtitle, group) => {
    const best = group && P.grammar?.[grammarKey(unit, group)];
    const open = gRouteOpen(unit,route), done = gRouteDone(unit,route);
    const kind=route.startsWith('section:')?'theory':route.startsWith('exercise:')?'practice':'recap';
    const icon={theory:'📖',practice:'✍️',recap:'📌'}[kind];
    const label=kind==='theory' ? (group?'Теория + мини-проверка':'Теория') : kind==='practice'?'Упражнение':'Памятка';
    return `<button class="mcard gstage-card ${done?'gcomplete':''} ${open ? '' : 'glocked'}" data-gkind="${kind}" data-gstart="${esc(route)}" ${open ? '' : 'disabled aria-disabled="true"'}><span class="mi" aria-hidden="true">${icon}</span><span><span class="gstage-label">${label}</span><b>${esc(title)}</b><small>${done?'✓ Пройдено · ':''}${best ? `${best.correct} из ${best.total} · ` : ""}${esc(subtitle)}</small>${open?'':'<span class="gstage-lock">Сначала пройди предыдущий раздел</span>'}</span><span aria-hidden="true">${open ? '›' : '🔒'}</span></button>`;
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
  if(art.captionDialogue) return gTheoryDialogues([{lines:art.examples}]);
  return `<div class="gscene-examples">${art.examples.map(([es,ru])=>`<div class="gscene-line"><b lang="es">${gTheoryText(es)}</b><span>${esc(ru)}</span></div>`).join('')}</div>`;
}
function gTheoryDialogues(dialogues) {
  return `<div class="gtheory-dialogues">${dialogues.map(d=>`<section class="gtheory-dialogue" aria-label="${esc(d.title || 'Разговор')}">${d.title?`<h3>${esc(d.title)}</h3>`:''}${d.lines.map(([es,ru],i)=>`<div class="gdialogue-turn"><span class="gdialogue-speaker" aria-label="Говорящий ${i%2+1}">${i%2?'Б':'А'}</span><div class="gdialogue-text"><p class="gdialogue-es" lang="es">${playBtn(es.replace(/\*\*/g,''))}${gTheoryText(es)}</p><p class="gdialogue-ru">${esc(ru)}</p></div></div>`).join('')}</section>`).join('')}</div>`;
}
function gArtFigure(art) {
  if (!art) return '';
  return `<figure class="gscene${art.captionExamples===false?' gscene-image-only':''}"><button class="gscene-image" data-gart aria-label="Увеличить иллюстрацию"><img src="${esc(art.image)}" alt="${esc(art.alt)}" width="1200" height="800" decoding="async"><span aria-hidden="true">⤢</span></button>${art.captionExamples===false?'':`<figcaption>${gArtExamples(art)}</figcaption>`}</figure>`;
}
function gOpenArt() {
  const step=G?.steps[G.at], unit=gUnit(), group=G?.recovery && gGroups(unit).find(g=>g.id===G.recovery);
  const recovery=group && gAttempt(unit,group);
  const art=recovery?.status==='review' ? unit.sections[gTheorySections(unit,group)[recovery.reviewAt||0]].illustration : step?.type==='theory' && unit?.sections[step.section].illustration;
  if (!art || document.querySelector('#g-art-modal')) return;
  const opener=document.activeElement, dialog=document.createElement('dialog');
  dialog.id='g-art-modal'; dialog.className='gart-modal'; dialog.setAttribute('aria-label','Иллюстрация к правилу');
  dialog.innerHTML=`<div class="gart-toolbar"><button class="btn ghost sm" data-gart-close>Закрыть ×</button></div><img src="${esc(art.image)}" alt="${esc(art.alt)}" width="1200" height="800" decoding="async">${gArtExamples(art)}`;
  dialog.addEventListener('close',()=>{dialog.remove(); if(opener?.isConnected)opener.focus();});
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  document.body.appendChild(dialog); dialog.showModal();
}
function gTheory(section) {
  const art=gArtFigure(section.illustration), formsFirst=section.presentation==='paradigm' && section.table;
  const copy=section.paragraphs.map((p,i)=>`<p class="gtheory-paragraph${i?'':' is-lead'}">${gTheoryText(p)}</p>`);
  return `<article class="gtheory gtheory-${esc(section.presentation || 'examples')}"><div class="gtheory-copy">${copy[0] || ''}${section.formulas ? `<div class="gformulas" aria-label="Модель правила">${section.formulas.map(f=>`<div>${gTheoryText(f)}</div>`).join('')}</div>`:''}</div>${formsFirst?'':art}
    ${section.dialogues ? gTheoryDialogues(section.dialogues) : ''}
    ${section.wordGroups ? grammarWordGroups(section.wordGroups) : ""}${section.schemes ? `<div${section.schemeGrid ? ' class="gsummary-cards"' : ""}>${grammarSchemes(section.schemes)}</div>` : ""}${section.table ? gTheoryTable(section.table) : ""}${formsFirst?art:''}
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
  return !!lastExercise && ["all", "summary", lastExercise].includes(G.route) && gUnitComplete(unit);
}
function gNextUnit(unit) {
  const units=COURSE.grammar || [], index=units.findIndex(u=>u.id===unit?.id);
  return index>=0 ? units[index+1] : undefined;
}
function gCanStartUnit(unit) {
  return !!unit && (gUnitComplete(unit) || gRouteOpen(unit,'all')) && gSteps(unit,'all').length>0;
}
function gStartNextUnit(id) {
  const next=gNextUnit(gUnit());
  if(next?.id===id && gCanStartUnit(next)) gStart(next.id,'all');
}
function gFireworks() {
  const colors = ["#7357dd","#f0aa36","#46a890","#ed7183"];
  return `<div class="gfireworks" aria-hidden="true">${[20,50,80].map((x,k) => `<div class="gburst" style="left:${x}%;top:${20+k%2*15}%">${Array.from({length:16},(_,i) => {
    const angle = i * Math.PI / 8;
    return `<i style="--dx:${Math.round(Math.cos(angle)*110)}px;--dy:${Math.round(Math.sin(angle)*110)}px;--delay:${k*.3}s;--spark:${colors[i%colors.length]}"></i>`;
  }).join("")}</div>`).join("")}</div>`;
}
function gFinalView(unit, tested, good) {
  const nextUnit=gNextUnit(unit), nextOpen=gCanStartUnit(nextUnit);
  const total = unit.exercises.reduce((n,g) => n+g.questions.length,0);
  const correct = unit.exercises.reduce((n,g) => n+(P.grammar[grammarKey(unit,g)]?.correct||0),0);
  return `<div class="player gplayer gfinal"><div class="ptop"><div class="wrap"><button class="x" data-gmain aria-label="На главную">×</button><div class="bar"><i style="width:100%"></i></div><span class="pcount">✓</span></div></div>
    <div class="pbody">${gFireworks()}<div class="wrap gresult"><span class="gresult-icon" aria-hidden="true">🏆</span><span class="kicker" lang="es">¡Enhorabuena!</span><h2 id="g-title" tabindex="-1">Поздравляю! Урок пройден!</h2><p>${esc(unit.title)} · ${esc(unit.subtitle)}</p>
    <div class="gfinal-score"><b>${unit.exercises.length} ${plural(unit.exercises.length,'упражнение завершено','упражнения завершены','упражнений завершено')}</b><span>Лучший результат: ${correct} из ${total}</span></div>
    ${nextUnit ? `<section class="gnext-lesson" aria-label="Следующий урок"><span class="kicker">Далее · Урок ${esc(nextUnit.number)}</span><h3>${esc(nextUnit.title)}</h3>${nextUnit.subtitle?`<p>${esc(nextUnit.subtitle)}</p>`:''}${!nextOpen?'<p class="gnext-status">🔒 Следующий урок пока недоступен</p>':gUnitComplete(nextUnit)?'<p class="gnext-status">✓ Уже пройден · можно повторить</p>':''}</section>` : '<p class="gcourse-complete" role="status">Все уроки раздела пройдены!</p>'}
    ${nextUnit && nextOpen ? `<button class="btn wide" data-gnext-unit="${esc(nextUnit.id)}">Начать следующий урок</button>` : '<button class="btn wide" data-grammar-list>К списку уроков</button>'}
    <button class="btn ghost wide" data-gmain>На главную</button><button class="btn ghost wide" data-gexit>К разделам урока</button>${nextUnit && nextOpen?'<button class="btn ghost wide" data-grammar-list>К списку уроков</button>':''}</div></div><div></div></div>`;
}
function gBlank(text) {
  return esc(text).replace(/_{3,}/g, '<span class="gblank" role="img" aria-label="Место для ответа">…</span>');
}
function gWorkedPreview(preview) {
  if (preview.gapParts) return preview.gapParts.map((part,i)=>`${esc(part)}${i < preview.gapAnswers.length ? `<mark class="gpreview-insert">${esc(preview.gapAnswers[i])}</mark>` : ""}`).join("");
  if (!preview.sentenceParts) return gBlank(preview.source);
  return `${esc(preview.sentenceParts[0])}<mark class="gpreview-insert">${esc(preview.displayAnswer ?? preview.answer)}</mark>${esc(preview.sentenceParts[1])}`;
}
function gGapMistakes(q,response,group={}) {
  if(!q.answers?.length)return null;
  const count=q.guidedGaps?.choices?.length||(q.gapParts?.length-1);
  if(!count)return null;
  let values=response.slotValues||response.gapValues;
  if(!values&&response.value&&q.gapParts) {
    const words=response.value.trim().split(/\s+/);let start=0;
    values=(q.gapWordCounts||Array(count).fill(1)).map(n=>{const part=words.slice(start,start+n).join(' ');start+=n;return part;});
  }
  if(!values||values.length!==count)return null;
  const candidates=[];
  if(q.guidedGaps) {
    const selected=[],{parts,choices}=q.guidedGaps;
    function visit(i) {
      if(i===choices.length) {
        if(grammarResult(q,gComposeGaps(parts,selected),group,false).good)candidates.push([...selected]);
        return;
      }
      for(const v of choices[i]){selected[i]=v;visit(i+1);}
    }
    visit(0);
  } else {
    for(const answer of q.answers) {
      const words=answer.trim().split(/\s+/),candidate=[];let start=0;
      for(const n of q.gapWordCounts||Array(count).fill(1)){candidate.push(words.slice(start,start+n).join(' '));start+=n;}
      if(start===words.length)candidates.push(candidate);
    }
  }
  if(!candidates.length)return null;
  // Compare every gap with the same accent policy as the whole answer. An omitted
  // acute accent in one gap must not make a different, grammatical error look red.
  const assess=c=>c.map((expected,i)=>grammarResult({...q,answers:[expected]},values[i],group,true));
  const penalty=results=>results.reduce((n,r)=>n+(r.good?(r.status==='almost'?0.1:0):1),0);
  const expected=candidates.reduce((best,c)=>penalty(assess(c))<penalty(assess(best))?c:best);
  const statuses=assess(expected);
  return {values,expected,wrong:statuses.map(r=>!r.good),almost:statuses.map(r=>r.status==='almost')};
}
function gMistakeAnalysis(q,response,group={}) {
  // Reveal accepted solutions on the FIRST wrong submission without grading it as correct.
  // The original response and gCheck's life counter remain unchanged.
  const gaps=gGapMistakes(q,response,group), wrong=gaps?.wrong.flatMap((bad,i)=>bad?[i]:[])||[];
  const details=wrong.map(i=>'<li>Пропуск '+(i+1)+': «'+esc(gaps.values[i])+'» → «'+esc(gaps.expected[i])+'»</li>').join('');
  const accentNotes=(gaps?.almost||[]).flatMap((ok,i)=>ok?['<li>Пропуск '+(i+1)+': ответ засчитан по форме, но напиши «'+esc(gaps.expected[i])+'» с ударением.</li>']:[]).join('');
  const accepted=[...new Set(q.answers.map(a=>gOptionLabel(q,a)))];
  return '<span class="ans">Верный ответ: '+accepted.map(esc).join(' / ')+'</span>'
    +'<p>Твой ответ: <b lang="es">'+esc(gOptionLabel(q,response.value))+'</b>.</p>'
    +(details?'<ul class="gwrong-fields">'+details+'</ul>':'')
    +(accentNotes?'<ul class="gaccent-notes">'+accentNotes+'</ul>':'')
    +'<p>Почему: '+esc(grammarFeedbackExplanation(q,response)||'Сравни свою форму с правилом.')+'</p>';
}
function gGapSentence(q,response,group={}) {
  const words=response.value ? response.value.split(" ") : [];
  let offset=0;
  const values=response.gapValues || (q.gapWordCounts ? q.gapWordCounts.map(n=>{const value=words.slice(offset,offset+n).join(' ');offset+=n;return value;}) : words);
  const wrong=response.checked&&!response.good?gGapMistakes(q,response,group)?.wrong:null;
  return `<div class="gfill-sentence"><p class="ggap-line" lang="es">${q.gapParts.map((part,i)=>`${esc(part)}${i<q.gapParts.length-1?`<span class="ggap-control"><input class="ginput ggap-input ${wrong?.[i]?'ggap-incorrect':''}" id="${i?'g-answer-'+i:'g-answer'}" data-ggap="${i}" data-gwords="${q.gapWordCounts?.[i] || 1}" aria-describedby="g-answer-format" aria-label="Пропуск ${i+1}${wrong?.[i]?', неверно':''}" ${wrong?.[i]?'aria-invalid="true"':''} lang="es" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="…" value="${esc(values[i] || '')}" ${response.checked?'disabled':''}></span>`:''}`).join('')}</p>${response.checked?'':gCharsPanel(q,'g-answer')}</div>`;
}
function gIntro(group) {
  const pictures = group.questions.filter(q => q.image).slice(0,3);
  const preview = group.preview;
  const visual = pictures.length ? `<div class="gintro-art" aria-hidden="true">${pictures.map(q => `<img src="${esc(q.image)}" alt="" width="384" height="384">`).join("")}</div>` : preview ? `<div class="gintro-demo"><span class="kicker">Образец</span><div class="gintro-source" lang="es">${gWorkedPreview(preview)}${preview.targetPrefix === "" ? "" : ` <span aria-hidden="true">→</span> ${esc(preview.targetPrefix ?? "la")}`}</div><div class="gintro-answer" lang="es">${esc(preview.answer)}<span aria-hidden="true">✓</span></div><span class="muted">${esc(preview.translation)}</span></div>` : group.introGroups ? grammarWordGroups(group.introGroups) : "";
  const choice = group.questions.every(q => q.options), modes=new Set(group.questions.map(q=>q.guidedGaps?'Выбор слов в пропусках':q.tiles?'Сборка фразы':q.options?'Выбор ответа':'Короткий ввод')), mixed=modes.size>1;
  const tip = preview?.tip || '';
  return `<div class="gintro ${visual ? "has-visual" : ""}">${visual}<div class="gintro-copy"><div class="gintro-tags"><span>${group.questions.length} ${plural(group.questions.length,"задание","задания","заданий")}</span><span>${esc([...modes].join(' · '))}</span></div><p>${esc(group.instruction)}</p><p class="muted gintro-tip">У тебя три жизни. После каждой ошибки сразу увидишь правильный ответ и объяснение. После третьей ошибки останешься на вопросе и сам выберешь: повторить правило или упражнение.</p>${modes.has('Сборка фразы') ? '<p class="muted gintro-tip">Нажимай на слова по порядку. Выбранное слово можно убрать нажатием.</p>' : mixed ? '<p class="muted gintro-tip">Часть ответов выбирай из вариантов, остальные вписывай самостоятельно.</p>' : tip ? `<p class="muted gintro-tip">${esc(tip)}</p>` : ""}</div>${group.family ? `<div class="gintro-family">${grammarFamily(group.family)}</div>` : ""}${group.example ? `<div class="gworked-example gintro-family"><small>${esc(group.example.label)}</small><b>${esc(group.example.es)}</b><small>${esc(group.example.ru)}</small></div>` : ""}</div>`;
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
function gFailureAnalysis(attempt,unit,group) {
  const errors=gAttemptErrors(attempt).filter(e=>group.questions[e.qi]);
  return `<section class="gerror-analysis" aria-labelledby="g-error-title"><h3 id="g-error-title" role="status">Разбор ошибок</h3>${errors.map((error,i)=>{
    const q=group.questions[error.qi], answers=[...new Set(q.answers.map(a=>gOptionLabel(q,a)))];
    const assessment=grammarResult(q,error.value,group,gQuestionMode(q,{value:error.value})==='input');
    return `<article class="gerror-item"><h4>Ошибка ${i+1} · Вопрос ${error.qi+1}</h4>${q.context?`<p>${esc(q.context)}</p>`:''}<p lang="es">${esc(q.prompt)}</p><h4>Твой ответ</h4><p class="gerror-entered" lang="es">${esc(gOptionLabel(q,error.value))}</p><h4>${answers.length>1?'Правильные варианты':'Правильный ответ'}</h4><ul class="gerror-answers">${answers.map(a=>`<li lang="es">${esc(a)}</li>`).join('')}</ul><h4>Почему ответ не подходит</h4><p>${esc(grammarFeedbackExplanation(q,assessment))}</p></article>`;
  }).join('')}</section>`;
}
function gPlayerView(failure=null) {
  const unit = gUnit();
  const current=G.steps[G.at], currentGroup=current?.group && gGroups(unit).find(g=>g.id===current.group);
  const attempt=failure?.attempt || (currentGroup && !G.ended ? gEnsureAttempt(unit,currentGroup) : null);
  if(G.recovery && !failure) return gRecoveryView(unit);
  if (G.ended && !failure) {
    const tested = G.steps.filter(s => s.type === "question" && !s.correction), good = tested.filter(s => G.responses[s.group]?.[s.qi]?.good).length;
    if (gUnitFinished(unit)) return gFinalView(unit, tested, good);
    const next = gNextRoute(unit, G.route);
    return `<div class="player gplayer"><div class="ptop"><div class="wrap"><button class="x" data-gexit aria-label="К разделам урока">×</button><div class="bar"><i style="width:100%"></i></div></div></div><div class="pbody"><div class="wrap gresult"><span class="gresult-icon">${tested.length && good < tested.length ? "🌱" : "✓"}</span><h2 id="g-title" tabindex="-1">${tested.length ? "Практика завершена" : "Раздел прочитан"}</h2>${tested.length ? `<p>С первого раза: <b>${good} из ${tested.length}</b></p>` : ""}<p class="muted">Лучшие результаты сохранены.</p>${next ? `<button class="btn ${good < tested.length ? "ghost" : ""}" data-gstart="${esc(next)}">Следующий раздел →</button>` : ""}<button class="btn ghost" data-gexit>К разделам урока</button></div></div><div></div></div>`;
  }
  const step = failure ? {type:'question',group:failure.group.id,qi:failure.qi} : G.steps[G.at], group = failure?.group || (step.group && gGroups(unit).find(g => g.id === step.group)), response = failure?.response || gResponse(step);
  // Answers remain hidden until submission; after each checked mistake they are shown immediately.
  let title, content, kicker = "Грамматика";
  if (step.type === "theory") { const section = unit.sections[step.section]; title = section.title; content = gTheory(section); kicker = "Правило"; }
  if (step.type === "summary") { title = "Что запомнить"; content = unit.summary.wordGroups ? grammarWordGroups(unit.summary.wordGroups) : unit.summary.schemes ? `<div class="gsummary-cards">${grammarSchemes(unit.summary.schemes)}</div>` : grammarTable(unit.summary); kicker = "Кратко"; }
  if (step.type === "intro") {
    title = group.title; kicker = "Упражнение";
    content = gIntro(group);
  }
  if (step.type === "question") {
    const q = group.questions[step.qi], block = (group.questionBlocks || []).filter(b => b.at <= step.qi).at(-1);
    kicker = `${group.title === "Мини-проверка" ? "Мини-проверка" : "Вопрос"} · ${step.qi + 1} из ${group.questions.length}`;
    if(step.correction) kicker="Работа над ошибками";
    title = q.context || (group.inlineAnswer ? "Дополни фразу" : q.image ? (group.pictureTitle || "Выбери название профессии") : q.prompt);
    const who = block ? `<div class="gwho"><img src="${esc(group.family.portraits[block.person])}" alt="" width="44" height="44"><b>Родственники ${esc(block.person)}</b></div>` : "";
    const mode=gQuestionMode(q,response);
    const showChoices=response.checked;
    const options = mode==='gaps' ? gGuided(q,response,group,step.qi) : mode==='build' ? gBuilder(q,response) : q.options ? `<div class="${q.interaction==='gap-choice'?'gchoices':'opts'}${q.answerWarnings?' has-warnings':''}" role="group" aria-label="Варианты ответа">${gOrderedChoices(group,step.qi,null,attempt).map((o,position) => `<button class="opt ${grammarChoiceClass(q,o,response.value,showChoices,group)}" data-gpick="${q.options.indexOf(o)}" data-gvalue="${esc(o)}" data-gposition="${position}" aria-label="${esc(o === 'Без артикля' ? 'Ничего не вставлять' : gOptionLabel(q,o))}" aria-pressed="${response.value === o}" ${response.checked ? "disabled" : ""}><span class="k">${position + 1}</span><span class="goption-label"><span lang="es">${esc(gOptionLabel(q,o))}</span>${grammarChoiceNote(q,o,showChoices)}</span></button>`).join("")}</div>`
      : `<div>${grammarInputHelp(q,group,"g-answer-format")}<label class="sr-only" for="g-answer">Ответ на испанском</label>${group.phraseInput && q.answers[0].split(' ').length>2 ? `<textarea class="ginput gphrase-input" id="g-answer" aria-label="Ответ на испанском" aria-describedby="g-answer-format" lang="es" autocomplete="off" autocapitalize="none" spellcheck="false" rows="2" placeholder="${esc(grammarInputPlaceholder(q,group))}" ${response.checked ? "disabled" : ""}>${esc(response.value)}</textarea>` : `<input class="ginput" id="g-answer" enterkeyhint="done" autocorrect="off" aria-label="Ответ на испанском" aria-describedby="g-answer-format" lang="es" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="${esc(grammarInputPlaceholder(q,group))}" value="${esc(response.value)}" ${response.checked ? "disabled" : ""}>`}${response.checked ? "" : gCharsPanel(q)}${gNoArticleControl(group,response)}</div>`;
    const source = q.sourceParts ? `<div class="gsource" lang="es"><span class="kicker">${esc(q.sourceLabel || 'Исходная фраза')}</span><p>${esc(q.sourceParts[0])}<strong>${esc(q.sourceParts[1])}</strong>${esc(q.sourceParts[2])}</p></div>` : "";
    const clues = q.clues ? `<div class="gclues" aria-label="Слова для ответа">${q.clues.map(([es,ru])=>`<span><b lang="es">${esc(es)}</b><small>${esc(ru)}</small></span>`).join("")}</div>` : "";
    const inline = group.inlineAnswer && mode==='input' && !q.options && q.prompt.includes("___");
    const sentence = mode==='gaps' ? options : q.gapParts ? grammarInputHelp(q,group,"g-answer-format")+gGapSentence(q,response,group) : inline ? `<div class="gfill-sentence"><p lang="es">${esc(q.prompt.split("___")[0])}</p>${options}<p lang="es">${esc(q.prompt.split("___").slice(1).join("___"))}</p></div>` : `${q.context ? `<p class="gquestion-sentence" lang="es">${gBlank(q.prompt)}</p>` : ""}${options}`;
    const question = `${who}${source}${clues}${gRatings(q.ratings)}${gFacts(q.facts)}${gClock(q.clock)}${gDistance(q.distance)}${q.translation ? `<p class="muted gquestion-translation">${esc(q.translation)}</p>` : ""}${['build','gaps'].includes(mode)?'':gAnswerHint(q)}${sentence}`;
    content = group.family ? `<div class="gfamily-work"><details class="gplay-family" ${G.treeOpen === false ? "" : "open"}><summary>Семейное дерево</summary>${grammarFamily({...group.family, activeName:block?.person})}</details><div class="ganswer-area">${question}${group.vocabulary ? `<details class="gvocab"><summary>Слова родства</summary>${grammarTable(group.vocabulary)}</details>` : ""}</div></div>`
      : `<div class="gquestion-work ${q.image ? "has-image" : ""}">${gPicture(q)}<div class="ganswer-area">${question}${group.vocabulary ? `<details class="gvocab"><summary>Слова для упражнения</summary>${grammarTable(group.vocabulary)}</details>` : ""}</div></div>`;
    if (group.title === "Мини-проверка" && group.instruction) content = `<p class="muted ginstruction">${esc(group.instruction.replace(/ Затем нажми.*$/, ""))}</p>` + content;
  }
  const progressAt = failure ? Math.max(0,G.steps.findIndex(s=>s.type==='question' && s.group===group.id && s.qi===step.qi)) : G.at;
  const checked = response?.checked;
  const failed=step.type==='question'&&attempt?.status==='failed';
  const question=step.type==='question'?group.questions[step.qi]:null;
  const feedback=checked ? `<div class="fb"><div class="gfeedback-head"><h3 role="status">${esc(grammarFeedbackTitle(response))}${failed?' · Жизни закончились':''}</h3><button class="btn ghost sm" data-gfeedback-toggle aria-expanded="${!response.feedbackHidden}" aria-controls="g-feedback-details" aria-label="${response.feedbackHidden?'Показать разбор ответа':'Свернуть разбор ответа'}">${response.feedbackHidden?'Показать':'Свернуть ×'}</button></div><div id="g-feedback-details" ${response.feedbackHidden?'hidden':''}>${failed?`<p>Три ошибки. Упражнение не засчитано, ты остаёшься на этом вопросе.</p>`:(!response.good&&attempt?.errors===2?'<p class="glast-chance">Осталась последняя жизнь.</p>':'')}${response.good?`${grammarAccentHint(response)}<span class="ex">${esc(grammarFeedbackExplanation(question,response))}</span>`:gMistakeAnalysis(question,response,group)}</div></div>` : "";
  return `<div class="player gplayer"><div class="ptop"><div class="wrap"><button class="x" data-gexit aria-label="Выйти из урока">×</button><div class="bar" role="progressbar" aria-label="Прогресс урока" aria-valuemin="0" aria-valuemax="${G.steps.length}" aria-valuenow="${G.at}"><i style="width:${Math.round(G.at / G.steps.length * 100)}%"></i></div>${attempt ? gHearts(attempt, group) : ''}</div>${gContext(unit,step,step.type!=="question")}</div>
    <div class="pbody"><div class="wrap">${step.type==="question"?`<span class="kicker">${esc(kicker)}</span><h2 id="g-title" tabindex="-1">${esc(title)}</h2>`:""}${content}${failed ? gFailureAnalysis(attempt,unit,group) : ""}</div></div>
    <div class="pfoot ${checked ? response.status==='almost'?'almost':response.good ? "good" : "bad" : ""}"><div class="wrap">${feedback}<div class="gplayer-actions">${failed ? '<button class="btn ghost" data-gexit>К разделам</button><button class="btn ghost" data-greview-theory>Повторить правило</button><button class="btn" data-grepeat-exercise>Попробовать заново</button>' : `${step.type==='question' && !checked ? '<button class="btn ghost ghide-keyboard" data-ghide-keyboard>Скрыть клавиатуру ↓</button>' : ''}<button class="btn ghost" data-gback${G.at ? "" : ' aria-label="Назад к разделам урока"'}>← Назад</button>${step.type === "question" && !checked ? gQuestionMode(group.questions[step.qi],response)==='choice' ? '<span class="muted gpick-hint">Нажми на вариант ответа</span>' : `<button class="btn" data-gcheck ${response.value.trim() ? "" : "disabled"}>Проверить</button>` : `<button class="btn" data-gnext>${step.correction && checked && !response.good ? "Попробовать ещё раз" : !step.correction && attempt?.status==='correcting' ? "К ошибкам →" : G.at===G.steps.length-1 && step.type==='question' && gNextRoute(unit,G.route)==='summary' ? "Что запомнить →" : G.at === G.steps.length - 1 ? "Завершить" : step.type === "intro" ? "Начать" : "Далее →"}</button>`}`}</div></div></div></div>`;
}
