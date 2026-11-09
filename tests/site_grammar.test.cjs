// Run with: node --test tests/site_grammar.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const template = fs.readFileSync('espanol/site_template.html', 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1].replace('/*__GRAMMAR_PLAYER__*/', fs.readFileSync('espanol/grammar_player.js','utf8'));
const unit = JSON.parse(fs.readFileSync('content/grammar/001_genero.json','utf8'));
const unit2 = JSON.parse(fs.readFileSync('content/grammar/002_objetos_animales.json','utf8'));
const unit3 = JSON.parse(fs.readFileSync('content/grammar/003_singular_plural.json','utf8'));
const unit17 = JSON.parse(fs.readFileSync('content/grammar/017_superlativo.json','utf8'));
const unit15 = JSON.parse(fs.readFileSync('content/grammar/015_comparativos.json','utf8'));
const unit16 = JSON.parse(fs.readFileSync('content/grammar/016_igualdad.json','utf8'));
function context(grammar = [unit], storage = new Map(), handlers = {}) {
  const noop = () => {};
  const ctx = vm.createContext({console, setTimeout:noop, clearTimeout:noop, addEventListener:noop,
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    window:{addEventListener:noop}, document:{documentElement:{classList:{toggle:noop}},addEventListener:(type,callback)=>{handlers[type]=callback;},getElementById:()=>null,querySelector:()=>({focus:noop})},
    matchMedia:()=>({matches:false,addEventListener:noop}),
    navigator:{}, speechSynthesis:{getVoices:()=>[],addEventListener:noop},
  });
  const data = {lessons:[],units:[],intervals:[1],grammar};
  // Execute the production script, excluding only the initial DOM render.
  vm.runInContext(script.replace('/*__DATA__*/{}',JSON.stringify(data)).replace(/render\(\);\s*$/, ''),ctx);
  return (code) => vm.runInContext(code,ctx);
}
function unlockUntil(run, route) {
 run(`(() => { const u=COURSE.grammar[0]; for(const r of gRoutes(u).slice(0,gRoutes(u).indexOf(${JSON.stringify(route)}))) { const g=r.startsWith('section:')?u.sections[+r.split(':')[1]].check:u.exercises.find(g=>r==='exercise:'+g.id); if(g)P.grammar[grammarKey(u,g)]={correct:0,total:g.questions.length}; else P.grammarRead[u.id+'/'+r]=true; } })()`);
}

test('unit 36 completes every answer, resumes drafts and reviews its own theory after three errors',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/036_me_han_regalado.json','utf8'));
 const run=context([u]);run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
 while(!run('G.ended')&&turns++<150)run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);
 assert.ok(turns<150);assert.equal(run('gUnitComplete(gUnit())'),true);
 for(const g of [...u.sections.map(s=>s.check),...u.exercises])for(const q of g.questions)for(const a of q.answers){
  assert.equal(run(`grammarResult(${JSON.stringify(q)},${JSON.stringify('  '+a.toUpperCase()+'  ')}).good`),true);
  assert.equal(run(`grammarResult(${JSON.stringify(q)},'incorrecto').status`),'wrong');
 }
 for(const g of u.exercises){
  const storage=new Map();let r=context([u],storage);unlockUntil(r,'exercise:'+g.id);
  r(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);gResponse(G.steps[G.at]).value='borrador';gSave();`);
  r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.equal(r('gResponse(G.steps[G.at]).value'),'borrador');
  r(`P.grammar[grammarKey(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}'))]={correct:2,total:${g.questions.length}};save();var best=JSON.stringify(P.grammar);`);
  for(let i=1;i<=3;i++){
   r(`gResponse(G.steps[G.at]).value='incorrecto';gCheck();`);
   assert.equal(r(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),i);
   if(i<3)r('gMove(1);');
  }
  assert.equal(r('JSON.stringify(P.grammar)'),r('best'));
  r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.ok(r('G.recovery'));r('gReviewTheory();');
  assert.ok(r('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
  for(let i=1;i<g.theorySections.length;i++)r('gMove(1);');r('gRepeatExercise();');
  assert.equal(r(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
 }
});

test('unit 36 rejects recipient and order errors and preserves meaningful accents',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/036_me_han_regalado.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['36.1.3','la','wrong'],['36.1.3','le','correct'],['36.1.4','les','wrong'],['36.2.2','no le ha dicho nada','wrong'],['36.2.5','no me ha dicho nada','wrong'],['36.2.6','no nos han preguntado nada','wrong'],['36.2.8','no les han dado nada','wrong'],['36.2.10','no las han regalado nada','wrong'],['36.3.2','les nos','correct'],['36.3.6','le me','correct'],['36.3.8','nos os','correct'],['36.3.8','os nos','wrong']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 unlockUntil(run,'exercise:36.2');run(`gStart(COURSE.grammar[0].id,'exercise:36.2');gMove(1);`);
 assert.equal(run(`grammarResult(gUnit().exercises[1].questions[0],'no han me dicho nada').status`),'wrong');
 const q=u.exercises[1].questions[10];assert.equal(run(`grammarResult(${JSON.stringify(q)},'no me han dicho nada').status`),'correct');
 const emphasis=u.exercises[2].questions[0];
 assert.equal(run(`grammarResult(${JSON.stringify(emphasis)},'mí me').status`),'correct');
 assert.equal(run(`grammarResult(${JSON.stringify(emphasis)},'mi me').status`),'wrong');
 assert.equal(run(`grammarResult(${JSON.stringify(emphasis)},'mí').status`),'wrong');
 assert.equal(run(`grammarResult(${JSON.stringify(emphasis)},'mi\u0301 me').status`),'correct');
});

test('personal-pronoun units finish every question and preserve failed attempts at the related theory',()=>{
 const files=fs.readdirSync('content/grammar').filter(f=>/^03[45]_.*\.json$/.test(f));
 for(const file of files){
  const u=JSON.parse(fs.readFileSync('content/grammar/'+file,'utf8'));const run=context([u]);
  run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
  while(!run('G.ended')&&turns++<200)run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);
  assert.ok(turns<200);assert.equal(run('gUnitComplete(gUnit())'),true);
  for(const g of [...u.sections.map(s=>s.check),...u.exercises])for(const q of g.questions)for(const a of q.answers)
   assert.equal(run(`grammarResult(${JSON.stringify(q)},${JSON.stringify(a)}).good`),true,u.number+'/'+a);
  for(const g of u.exercises){
   const storage=new Map();let r=context([u],storage);unlockUntil(r,'exercise:'+g.id);
   r(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);gResponse(G.steps[G.at]).value='borrador';gSave();`);
   r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.equal(r('gResponse(G.steps[G.at]).value'),'borrador');
   r(`var best=JSON.stringify(P.grammar);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}`);
   assert.equal(r('JSON.stringify(P.grammar)'),r('best'));
   r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.ok(r('G.recovery'));r('gReviewTheory();');
   assert.ok(r('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
   for(let i=1;i<g.theorySections.length;i++)r('gMove(1);');r('gRepeatExercise();');
   assert.equal(r(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
  }
 }
});

test('unit 34 checks speaker inclusion, address, accents and contrast',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/034_yo_tu_el.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['34.1.2','nosotras','wrong'],['34.1.2','nosotros','correct'],['34.1.3','él','wrong'],['34.1.6','nosotros','wrong'],['34.1.8','tu','wrong'],['34.1.8','tú','correct'],['34.3.2','Ella el','wrong'],['34.3.2','Ella él','correct'],['34.3.3','Es argentino','wrong'],['34.4.1','ti','wrong'],['34.4.1','tú','correct'],['34.4.5','Yo ellas','wrong']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
});

test('unit 35 checks roles, placement, doubling, semantic accents and normative leismo',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/035_te_amo.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['35.1.1','lo','correct'],['35.1.1','le','almost'],['35.1.3','les','almost'],['35.1.4','le','wrong'],['35.1.5','le','wrong'],['35.1.6','les','almost'],['35.2.3','los','wrong'],['35.2.3','os','correct'],['35.2.4','le','almost'],['35.2.5','les','almost'],['35.2.6','las','wrong'],['35.3.3','no he lo comprado','wrong'],['35.3.3','no le he comprado','wrong'],['35.3.4','nos quiero','wrong'],['35.3.6','te recuerdo','correct'],['35.3.8','no te quiero','wrong'],['35.3.8','no me quiere','correct'],['35.3.10','te conocen','wrong'],['35.3.10','me conocen','correct'],['35.4.1','me a mi','wrong'],['35.4.1','a mí','wrong'],['35.4.1','me a mí','correct'],['35.4.2','nos a nosotras','wrong'],['35.4.2','nos a nosotros','correct'],['35.4.4','les a ellas','wrong'],['35.4.5','les a ustedes','almost'],['35.4.6','les a ellos','almost']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 // A normative warning uses yellow feedback and does not consume one of the three lives.
 const storage=new Map();const r=context([u],storage);unlockUntil(r,'exercise:35.1');
 r(`gStart(COURSE.grammar[0].id,'exercise:35.1');gMove(1);gResponse(G.steps[G.at]).value='le';gCheck();`);
 assert.equal(r(`gAttempt(gUnit(),gUnit().exercises[0]).errors`),0);
 assert.equal(r(`gResponse(G.steps[G.at]).checked`),true);
 assert.ok(r('gPlayerView()').includes('Ответ засчитан.'));
});
test('unit 28 accepts normative relatives and rejects pronoun duplication and semantic accents',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/028_relativos_que.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['28.1.1','quien','correct'],['28.1.1','que','correct'],['28.1.3','quien','wrong'],['28.1.5','que','correct'],['28.1.8','que','wrong'],['28.1.10','que','correct'],['28.2.7','con quien','wrong'],['28.2.7','con quienes','correct'],['28.3.1','que conoci en el parque','almost'],['28.3.1','que lo conocí en el parque','wrong'],['28.3.8','con quien','wrong'],['28.4.2','el que','wrong'],['28.4.2','lo que','correct'],['28.4.5','lo qué','wrong']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
});

test('relative units complete all questions and restore failed attempts at the exact theory',()=>{
 for(const filename of ['028_relativos_que.json','029_cuyo_donde_cuando.json']){
 const u=JSON.parse(fs.readFileSync('content/grammar/'+filename,'utf8'));const run=context([u]);
 run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
 while(!run('G.ended')&&turns++<180)run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);
 assert.ok(turns<180);assert.equal(run('gUnitComplete(gUnit())'),true);
 for(const g of u.exercises){
  const storage=new Map();let r=context([u],storage);unlockUntil(r,'exercise:'+g.id);
  r(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);gResponse(G.steps[G.at]).value='parcial';gSave();`);
  r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.equal(r('gResponse(G.steps[G.at]).value'),'parcial');
  r(`var previous=JSON.stringify(P.grammar);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}`);
  assert.equal(r('JSON.stringify(P.grammar)'),r('previous'));
  r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.ok(r('G.recovery'));r('gReviewTheory();');
  assert.ok(r('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
  for(let i=1;i<g.theorySections.length;i++)r('gMove(1);');r('gRepeatExercise();');
  assert.equal(r(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
 }
 }
});

test('unit 29 distinguishes possession agreement, retained prepositions, place and time',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/029_cuyo_donde_cuando.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['29.1.1','cuya','wrong'],['29.1.3','cuya','correct'],['29.1.4','cuyas','wrong'],['29.1.6','cuya','wrong'],['29.1.6','en cuyo','correct'],['29.1.9','con cuya','correct'],['29.1.10','para cuyo','wrong'],['29.2.2','cuyas','wrong'],['29.2.4','cuya','wrong'],['29.2.4','en cuya','correct'],['29.2.6','cuyos','wrong'],['29.3.1','adonde','wrong'],['29.3.2','dónde','wrong'],['29.3.6','a donde','correct'],['29.3.6','donde','correct'],['29.3.6','a la que','correct'],['29.3.7','cuándo','wrong'],['29.3.10','al que','correct'],['29.3.11','adonde','wrong'],['29.3.12','cuando','correct'],['29.3.12','en la que','correct'],['29.3.12','donde','wrong']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 const corrected=u.exercises[0].questions.at(-1);
 assert.equal(run(`grammarResult(${JSON.stringify(corrected)},'cuya su').status`),'wrong');
});

test('relative unit 29 accepts every listed alternative and next cards connect 27 through 29',()=>{
 const units=['027_ordinales.json','028_relativos_que.json','029_cuyo_donde_cuando.json'].map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));const run=context(units);
 for(const u of units.slice(1))for(const g of [...u.sections.map(s=>s.check),...u.exercises])for(const q of g.questions)for(const a of q.answers)
  assert.equal(run(`grammarResult(${JSON.stringify(q)},${JSON.stringify(a)}).good`),true,a);
 for(const i of [0,1]){
  assert.equal(run(`gNextUnit(COURSE.grammar[${i}]).number`),units[i+1].number);
  assert.ok(run(`gFinalView(COURSE.grammar[${i}],[],0)`).includes(units[i+1].title));
 }
 assert.equal(run('gNextUnit(COURSE.grammar[2])'),undefined);
});

test('new interrogative lessons complete all formats and preserve attempts, alternatives and exact review routes',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>/^03[0-3]_.*\.json$/.test(f)).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 assert.ok(units.length);
 for(const u of units){
  const run=context([u]);run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
  while(!run('G.ended')&&turns++<220){run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);}
  assert.ok(turns<220);assert.equal(run('gUnitComplete(gUnit())'),true);
  for(const g of [...u.sections.map(s=>s.check),...u.exercises])for(const q of g.questions)for(const a of q.answers)
   assert.equal(run(`grammarResult(${JSON.stringify(q)},${JSON.stringify(a)}).good`),true,u.number+'/'+a);
  for(const g of u.exercises){
   const storage=new Map();let r=context([u],storage);unlockUntil(r,'exercise:'+g.id);
   r(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);gResponse(G.steps[G.at]).value='borrador';gSave();`);
   r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.equal(r('gResponse(G.steps[G.at]).value'),'borrador');
   r(`var best=JSON.stringify(P.grammar);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}`);
   assert.equal(r('JSON.stringify(P.grammar)'),r('best'));
   r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.ok(r('G.recovery'));r('gReviewTheory();');
   assert.ok(r('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
   for(let i=1;i<g.theorySections.length;i++)r('gMove(1);');r('gRepeatExercise();');
   assert.equal(r(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
  }
 }
});

test('unit 30 preserves question meaning, number, prepositions and meaningful accents',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/030_quien_que.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['30.2.1','quien','wrong'],['30.2.1','quién','correct'],['30.2.6','quién','wrong'],['30.2.7','qué','correct'],['30.2.9','quiénes','correct'],['30.3.5','de qué','wrong'],['30.3.7','Quiénes','correct'],['30.3.9','quién','wrong'],['30.3.9','a quién','correct'],['30.1.1','Qué tiene Julian en la mano','almost'],['30.1.9','Quién quiere a María','wrong'],['30.1.10','Quién quiere a María','correct']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
});

test('unit 31 distinguishes definitions, identification, regional determiners and de',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/031_cual_que.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['31.1.3','Cuáles de','wrong'],['31.1.4','Cuáles de','correct'],['31.1.6','cuál','wrong'],['31.2.1','Quién de','correct'],['31.2.2','Qué','wrong'],['31.2.4','Cuáles','correct'],['31.2.4','Cuál','wrong'],['31.2.5','Cuál','wrong'],['31.2.8','cuál','correct'],['31.2.12','Cuál','correct'],['31.3.2','Cuál','wrong'],['31.3.3','cual','wrong'],['31.3.3','cuál','correct'],['31.3.7','cuáles','correct'],['31.3.8','cuál','wrong'],['31.3.12','Qué es un poncho','correct']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
});

test('unit 32 distinguishes movement, time, quantity, motive and purpose',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/032_cuando_donde.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['32.2.2','adónde','correct'],['32.2.2','a dónde','correct'],['32.2.2','dónde','correct'],['32.2.2','adonde','wrong'],['32.2.6','adónde','wrong'],['32.2.9','cuándo','wrong'],['32.2.9','desde cuándo','correct'],['32.2.10','dónde','wrong'],['32.2.7','para qué','correct'],['32.2.8','porque','wrong'],['32.3.3','por qué','correct'],['32.3.3','para qué','correct'],['32.3.6','adónde','wrong'],['32.4.3','cuántos','wrong'],['32.4.4','cuánto tiempo','correct'],['32.4.5','cuántas','wrong']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
});

test('unit 33 accepts emotional alternatives and preserves agreement and split gaps',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/033_exclamativos.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['33.1.2','Qué tan','correct'],['33.1.2','Qué más','correct'],['33.1.2','Cómo tan','wrong'],['33.2.1','Cómo','correct'],['33.2.3','Cuántos','wrong'],['33.2.5','Qué Cuánto','correct'],['33.2.5','Qué Cuánta','wrong'],['33.2.6','Cuánto','correct'],['33.2.6','Cómo','correct'],['33.3.3','Cómo bien','wrong'],['33.3.4','Qué cansados','wrong'],['33.3.9','Cuánto','correct'],['33.3.9','Cómo','correct'],['33.3.11','Cuántas','wrong'],['33.3.12','Qué','correct']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 const q=u.exercises[0].questions[1];
 assert.ok(run(`gGapSentence(${JSON.stringify(q)},{value:'',gapValues:['Qué','más']})`).includes('value="más"'));
 assert.equal((run(`gGapSentence(${JSON.stringify(q)},{value:'',gapValues:[]})`).match(/data-ggap=/g)||[]).length,2);
 assert.equal((run(`gGapSentence(${JSON.stringify(q)},{value:'',gapValues:[]})`).match(/class="gaccents"/g)||[]).length,1);
});

test('shared Spanish keys follow the focused gap and disappear after checking',()=>{
 const handlers={};const run=context([unit17],new Map(),handlers);
 run(`G={};`);
 const buttons=Array.from({length:7},()=>({dataset:{gfield:'g-answer'}}));
 handlers.focusin({target:{id:'g-answer-1',dataset:{ggap:'1'},closest:()=>({querySelectorAll:()=>buttons})}});
 assert.ok(buttons.every(b=>b.dataset.gfield==='g-answer-1'));
 assert.equal(run('G.gapIndex'),1);
 const q={gapParts:['¡',' noche ',' fría!'],gapWordCounts:[1,1],inputChars:['á','é','í','ó','ú','ü','ñ']};
 assert.ok(!run(`gGapSentence(${JSON.stringify(q)},{value:'Qué tan',checked:true})`).includes('gaccents'));
});

test('Spanish answers accept alternatives and NFC but preserve ñ and stress', () => {
 const run = context();
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[1], " JEFA ")'),true);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[14], "me\\u0301dica")'),true);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[14], "medica")'),false);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[11], "nina")'),false);
});
test('current RAE variants are accepted without preserving obsolete textbook answers', () => {
 const run=context();
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[0].questions[6], "la pilota")'),true);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[0].questions[6], "la piloto")'),true);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[12], "dependiente")'),true);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[14], "médico")'),false);
});
test('retries cannot farm XP and progress keeps the best score', () => {
 const run=context();
 run('var u=COURSE.grammar[0], g=u.exercises[0]; gradeGrammar(u,g,g.questions.map(q=>q.answers[0]));');
 assert.equal(run('P.xp'),20);
 run('gradeGrammar(u,g,g.questions.map(q=>q.answers[0])); gradeGrammar(u,g,g.questions.map(()=>"wrong"));');
 assert.equal(run('P.xp'),20);
 assert.equal(run('P.grammar["001_el_hijo_la_hija/1.1"].correct'),10);
 assert.equal(run('grammarAttempts.get("001_el_hijo_la_hija/1.1").correct'),0);
});
test('sync preserves grammar results from both devices without lowering scores', () => {
 const run=context();
 assert.equal(run('mergeProgress({...fresh(),grammar:{a:{correct:8}}},{...fresh(),grammar:{a:{correct:3},b:{correct:5}}}).grammar.a.correct'),8);
 assert.equal(run('mergeProgress({...fresh(),grammar:{a:{correct:3}}},{...fresh(),grammar:{a:{correct:8},b:{correct:5}}}).grammar.b.correct'),5);
});
test('family tree labels ten portraits and questions clearly separate Julio and Silvia', () => {
 const run=context();
 const tree = run('grammarFamily(COURSE.grammar[0].exercises[2].family)');
 assert.equal((tree.match(/class="gperson /g)||[]).length,10);
 for(const name of ['Luis','Ana','Julio','Lucía','Gabriel','Laura','Blanca','Pedro','Raúl','Silvia']) {
   assert.ok(tree.includes(`<figcaption>${name}</figcaption>`));
 }
 const form = run('grammarForm(COURSE.grammar[0], COURSE.grammar[0].exercises[2])');
 assert.ok(form.indexOf('Часть 1 · Родственники Julio') < form.indexOf('1. Кем Luis приходится Julio?'));
 assert.ok(form.indexOf('Часть 2 · Родственники Silvia') < form.indexOf('6. Кем Luis приходится Silvia?'));
 assert.equal((form.match(/class="ginput"/g)||[]).length,unit.exercises[2].questions.filter(q=>!q.options).length);
});
test('player shows one picture question, requires a check, and resumes the same step', () => {
 const run=context();
 unlockUntil(run,'exercise:1.1');
 run('gStart(COURSE.grammar[0].id,"exercise:1.1"); gMove(1);');
 assert.equal(run('G.at'),1);
 assert.equal((run('gPlayerView()').match(/class="gquestion-picture"/g)||[]).length,1);
 run('gMove(1)');
 assert.equal(run('G.at'),1);
 run('gResponse(G.steps[G.at]).value="la periodista"; gCheck(); gMove(1); G=null; gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(run('G.at'),2);
 assert.equal(run('G.responses["1.1"][0].checked'),true);
 run('gMove(-1)');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
});
test('corrections preserve the first-answer score without duplicate XP', () => {
 const run=context();
 unlockUntil(run,'exercise:1.1');
 run(`gStart(COURSE.grammar[0].id,"exercise:1.1"); gMove(1);
   while(!G.ended) { const step=G.steps[G.at], group=gGroups(gUnit()).find(g=>g.id===step.group); gResponse(step).value=!step.correction && step.qi===0?"wrong":group.questions[step.qi].answers[0]; gCheck(); gMove(1); }`);
 assert.equal(run('P.grammar["001_el_hijo_la_hija/1.1"].correct'),9);
 assert.equal(run('P.xp'),18);
 run('gRetry();');
 assert.equal(run('G.steps.length'),1);
 run('gResponse(G.steps[0]).value="la periodista"; gCheck(); gMove(1);');
 assert.equal(run('P.grammar["001_el_hijo_la_hija/1.1"].correct'),9);
 assert.equal(run('P.xp'),18);
});
test('family question keeps the tree and one input beside a named speaker', () => {
 const run=context();
 unlockUntil(run,'exercise:1.3');
 run('gStart(COURSE.grammar[0].id,"exercise:1.3"); gMove(1);');
 const html=run('gPlayerView()');
 assert.equal((html.match(/id="g-answer"/g)||[]).length,1);
 assert.ok(html.includes('Кем Luis приходится Julio?'));
 assert.ok(html.includes('gtree-person is-active'));
 assert.ok(html.includes('Семейное дерево'));
});
test('kinship edges terminate at children and exclude their spouses', () => {
 const run=context(), tree=run('grammarFamily(COURSE.grammar[0].exercises[2].family)');
 assert.equal((tree.match(/data-kinship-child=/g)||[]).length,6);
 for(const name of ['Julio','Laura','Blanca','Pedro','Raúl','Silvia']) assert.ok(tree.includes(`data-kinship-child="${name}"`));
 for(const name of ['Lucía','Gabriel']) assert.ok(!tree.includes(`data-kinship-child="${name}"`));
 assert.ok(!tree.includes('сын') && !tree.includes('дочь'));
 assert.ok(tree.includes('data-kinship-child="Julio" data-kinship-parents="Luis, Ana" d="M300 45V130H90V170"'));
});
test('stages unlock in order after completing the previous practice', () => {
 const run=context();
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"section:0")'),true);
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"section:1")'),false);
 run('gStart(COURSE.grammar[0].id,"exercise:1.3")');
 assert.equal(run('G'),null);
 run(`gStart(COURSE.grammar[0].id,"section:0"); gMove(1); while(!G.ended) { const step=G.steps[G.at]; gResponse(step).value=!step.correction && step.qi<2?"wrong":COURSE.grammar[0].sections[0].check.questions[step.qi].answers[0];gCheck();gMove(1); }`);
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"section:1")'),true);
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"section:2")'),false);
});
test('summary reading persists and opening an old saved locked stage cannot bypass gates', () => {
 const run=context();
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"summary")'),false);
 unlockUntil(run,'summary');
 run('gStart(COURSE.grammar[0].id,"summary");gMove(1);');
 assert.equal(run('P.grammarRead[COURSE.grammar[0].id+"/summary"]'),true);
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"exercise:1.1")'),true);
 run('gStart(COURSE.grammar[0].id,"exercise:1.1"); G=null; P=fresh(); gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(run('G.at'),0);
 assert.equal(run('G.steps[0].type'), 'theory');
 assert.equal(run('mergeProgress({...fresh(),grammarRead:{a:true}},{...fresh(),grammarRead:{b:true}}).grammarRead.b'),true);
});
test('choice click grades immediately, plays the matching sound once and keeps explanation visible', () => {
 const run=context();
 run('var played=[];sfx=ok=>played.push(ok);gStart(COURSE.grammar[0].id,"section:0");gMove(1);');
 assert.ok(!run('gPlayerView()').includes('data-gcheck'));
 run('gPick(1);gPick(0);');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('played.join(",")'),'true');
 assert.ok(run('gPlayerView()').includes('data-gnext'));
 run('gMove(1);gPick(0);');
 assert.equal(run('gResponse(G.steps[G.at]).good'),false);
 assert.equal(run('played.join(",")'),'true,false');
 assert.ok(run('gPlayerView()').includes('Верный ответ: la estudiante'));
});
test('answer sounds differ, resume suspended audio and respect mute', () => {
 const run=context();
 run(`var tones=[],resumed=0;window.AudioContext=class {
  constructor(){this.currentTime=0;this.state="suspended";this.destination={};}
  resume(){resumed++;this.state="running";return Promise.resolve();}
  createOscillator(){const o={frequency:{value:0},connect:g=>g,stop:()=>{}};o.start=()=>tones.push(o.frequency.value);return o;}
  createGain(){return {connect:()=>{},gain:{setValueAtTime:()=>{},exponentialRampToValueAtTime:()=>{}}};}
 };sfx(true);sfx(false);P.sound=false;sfx(true);`);
 assert.equal(run('tones.join(",")'),'659,988,196,147');
 assert.equal(run('resumed'),1);
});
test('quiz answers keep explanation and manual next for correct and incorrect responses, including resume', () => {
 const run=context();
 run(`var scheduled=0;setTimeout=()=>++scheduled;
 gStart(COURSE.grammar[0].id,"section:0");gMove(1);gPick(1);`);
 assert.equal(run('scheduled'),0);
 assert.equal(run('G.at'),1);
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.ok(run('gPlayerView()').includes('data-gnext'));
 assert.ok(!run('gPlayerView()').includes('Переходим дальше'));
 run('gExit();gStart(COURSE.grammar[0].id,"section:0",true);');
 assert.equal(run('G.at'),1);
 assert.equal(run('scheduled'),0);
 assert.ok(run('gPlayerView()').includes('data-gnext'));
 run('gMove(1);gPick(0);');
 assert.equal(run('G.at'),2);
 assert.equal(run('gResponse(G.steps[G.at]).good'),false);
 assert.equal(run('scheduled'),0);
 assert.ok(run('gPlayerView()').includes('data-gnext'));
});

test('typed answers always keep manual next, whether correct or incorrect', () => {
 const run=context();
 unlockUntil(run,'exercise:1.2');
 run('var scheduled=0;setTimeout=()=>++scheduled;gStart(COURSE.grammar[0].id,"exercise:1.2");gMove(1);gResponse(G.steps[G.at]).value="señora";gCheck();');
 assert.equal(run('scheduled'),0);
 assert.equal(run('G.at'),1);
 assert.ok(run('gPlayerView()').includes('data-gnext'));
 run('gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();');
 assert.equal(run('scheduled'),0);
 assert.ok(run('gPlayerView()').includes('data-gnext'));
});
test('completion celebrates the whole unit and offers a next lesson only when available', () => {
 const run=context();
 unlockUntil(run,'exercise:1.3');
 run('gStart(COURSE.grammar[0].id,"exercise:1.3");gMove(1);while(!G.ended){const step=G.steps[G.at],group=gGroups(gUnit()).find(g=>g.id===step.group);if(step.type==="question"){gResponse(step).value=group.questions[step.qi].answers[0];gCheck();}gMove(1);}');
 let html=run('gPlayerView()');
 assert.ok(html.includes('Поздравляю! Урок пройден!'));
 assert.ok(html.includes('gfireworks') && html.includes('data-gmain'));
 assert.ok(!html.includes('data-gnext-unit'));
 run('COURSE.grammar.push({...COURSE.grammar[0],id:"next-unit"})');
 assert.ok(run('gPlayerView()').includes('data-gnext-unit="next-unit"'));
 run('G.route="section:0";');
 assert.ok(!run('gPlayerView()').includes('Поздравляю! Урок пройден!'));
});

test('second unit runs through locks, choice and typed questions and preserves first-unit progress', () => {
 const run=context([unit,unit2]);
 run(`var original=COURSE.grammar[0];gradeGrammar(original,original.exercises[0],original.exercises[0].questions.map(q=>q.answers[0]));
 gStart(COURSE.grammar[1].id); var count=0;
 while(!G.ended && count++<200) {
  const step=G.steps[G.at];
  if(step.type==='question') {const group=gGroups(gUnit()).find(g=>g.id===step.group);gResponse(step).value=group.questions[step.qi].answers[0];gCheck();}
  gMove(1);
 }`);
 assert.equal(run('G.ended'),true);
 assert.equal(run('P.grammar["002_el_libro_la_mesa/2.1"].correct'),32);
 assert.equal(run('P.grammar["002_el_libro_la_mesa/2.2"].correct'),6);
 assert.equal(run('P.grammar["002_el_libro_la_mesa/2.3"].correct'),10);
 assert.equal(run('P.grammar["001_el_hijo_la_hija/1.1"].correct'),10);
 assert.ok(run('gPlayerView()').includes('Поздравляю! Урок пройден!'));
});

test('new unit renders noun groups and typed pictures with matching instructions', () => {
 const run=context([unit2]);
 const theory=run('gTheory(COURSE.grammar[0].sections[0])');
 assert.ok(theory.includes('el libro') && theory.includes('(книга)'));
 assert.ok(!theory.includes('gscheme-arrow'));
 unlockUntil(run,'exercise:2.3');
 run('gStart(COURSE.grammar[0].id,"exercise:2.3");gMove(1);');
 const picture=run('gPlayerView()');
 assert.ok(picture.includes('Напиши название с артиклем'));
 assert.ok(picture.includes('id="g-answer"') && picture.includes('Слова для упражнения'));
 assert.ok(!picture.includes('профессии'));
 const intro=run('gIntro(COURSE.grammar[0].exercises[2])');
 assert.ok(intro.includes('Выбор ответа') && intro.includes('Короткий ввод'));
});

test('third unit completes all stages and keeps previous units intact', () => {
 const run=context([unit,unit2,unit3]);
 run(`gradeGrammar(COURSE.grammar[1],COURSE.grammar[1].exercises[0],COURSE.grammar[1].exercises[0].questions.map(q=>q.answers[0]));
 gStart(COURSE.grammar[2].id); var turns=0;
 while(!G.ended && turns++<200) {
  const step=G.steps[G.at];
  if(step.type==='question') {const group=gGroups(gUnit()).find(g=>g.id===step.group);gResponse(step).value=group.questions[step.qi].answers[0];gCheck();}
  gMove(1);
 }`);
 assert.equal(run('G.ended'),true);
 assert.deepEqual(JSON.parse(run('JSON.stringify(gUnit().exercises.map(g=>P.grammar[grammarKey(gUnit(),g)].correct))')),[18,10,10]);
 assert.equal(run('P.grammar["002_el_libro_la_mesa/2.1"].correct'),32);
 assert.ok(run('gPlayerView()').includes('Лучший результат: 38 из 38'));
});

test('counting renders the exact visible objects and rewriting highlights the source', () => {
 const run=context([unit3]);
 for (const question of unit3.exercises[1].questions) {
  const markup=run(`gPicture(${JSON.stringify(question)})`);
  assert.equal((markup.match(/<img /g)||[]).length,question.pictureCount);
  assert.ok(markup.includes(`aria-label="${question.imageAlt}"`));
 }
 unlockUntil(run,'exercise:3.3');
 run('gStart(COURSE.grammar[0].id,"exercise:3.3");gMove(1);');
 const markup=run('gPlayerView()');
 assert.ok(markup.includes('<strong>un hijo y dos hijas</strong>'));
 assert.ok(markup.includes('Amalia tiene tres <span class="gblank"'));
 const alternative=unit3.sections[2].check.questions[0];
 assert.equal(run(`grammarCorrect(${JSON.stringify(alternative)},"rubís")`),true);
 assert.equal(run(`grammarCorrect(${JSON.stringify(alternative)},"rubíes")`),true);
 const accent=unit3.exercises[0].questions[13];
 assert.equal(run(`grammarCorrect(${JSON.stringify(accent)},"dias")`),false);
});

test('back exits the first screen to the unit menu and preserves a resumable attempt', () => {
 const run=context([unit3]);
 unlockUntil(run,'section:2');
 run('gStart(COURSE.grammar[0].id,"section:2");');
 assert.ok(run('gPlayerView()').includes('data-gback aria-label="Назад к разделам урока"'));
 run('gMove(-1);');
 assert.equal(run('G'),null);
 assert.equal(run('view.grammar'),unit3.id);
 assert.equal(run('gSaved().route'),'section:2');
 run('gStart(view.grammar,"all",true);gMove(1);gResponse(G.steps[G.at]).value="rubíes";gCheck();gMove(-1);');
 assert.equal(run('G.at'),0);
 run('gMove(1);');
 assert.equal(run('gResponse(G.steps[G.at]).checked'),true);
});

test('theory emphasis escapes HTML and renders only supported inline formatting', () => {
 const run=context([unit3]);
 const markup=run('gTheory(COURSE.grammar[0].sections[0])');
 assert.ok(markup.includes('class="gtheory-paragraph is-lead"'));
 assert.ok(markup.includes('единственное число'));
 assert.ok(markup.includes('<code lang="es">singular</code>'));
 assert.equal(run('gTheoryText("<img src=x> **важно** `-s`")'),'&lt;img src=x&gt; <strong>важно</strong> <code lang="es">-s</code>');
});

test('unit 17 opens independently of skipped units and completes all four exercises', () => {
 const run=context([unit,unit2,unit3,unit17]);
 run(`gStart(COURSE.grammar[3].id); var turns17=0;
 while(!G.ended && turns17++<150) {
  const step=G.steps[G.at];
  if(step.type==='question') {const group=gGroups(gUnit()).find(g=>g.id===step.group);gResponse(step).value=group.questions[step.qi].answers[0];gCheck();}
  gMove(1);
 }`);
 assert.equal(run('G.ended'),true);
 assert.deepEqual(JSON.parse(run('JSON.stringify(gUnit().exercises.map(g=>P.grammar[grammarKey(gUnit(),g)].correct))')),[8,8,8,6]);
 assert.ok(run('gPlayerView()').includes('Лучший результат: 30 из 30'));
 assert.equal(run('Object.keys(P.grammar).some(k=>k.startsWith("003_"))'),false);
});

test('friend scales show ties, accessible values, escaped names and phrase input instructions', () => {
 const run=context([unit17]);
 unlockUntil(run,'exercise:17.2');
 run('gStart(COURSE.grammar[0].id,"exercise:17.2");gMove(1);gResponse(G.steps[G.at]).value="el más simpático";gCheck();gMove(1);gResponse(G.steps[G.at]).value="la menos simpática";gCheck();gMove(1);');
 const html=run('gPlayerView()');
 assert.equal((html.match(/class="gratings-person"/g)||[]).length,3);
 assert.equal((html.match(/aria-label="Уровень: 3 из 3"/g)||[]).length,2);
 assert.ok(html.includes('Marina y Leo son ') && html.includes('de sus amigos.'));
 assert.ok(html.includes('class="gbuild"'));
 assert.equal((html.match(/id="g-answer"/g)||[]).length,0);
 assert.ok(html.includes('data-gadd=') && html.includes('Слова для сборки'));
 const intro=run('gIntro(COURSE.grammar[0].exercises[1])');
 assert.ok(intro.includes('Сборка') && intro.includes('Сравни друзей по шкале'));
 assert.ok(!intro.includes('недостающее слово') && !intro.includes('aria-hidden="true">→'));
 const unsafe=run('gRatings({label:"<img>",people:[{name:"<script>",level:1}]})');
 assert.ok(!unsafe.includes('<script>') && unsafe.includes('&lt;img&gt;'));
});

test('unit 15 completes independently, shows paired data, and leads to unit 16', () => {
 const run=context([unit,unit2,unit3,unit15,unit16,unit17]);
 run(`gStart(COURSE.grammar[3].id);var turns15=0;
 while(!G.ended && turns15++<150) {
  const step=G.steps[G.at];
  if(step.type==='question'){const group=gGroups(gUnit()).find(g=>g.id===step.group);gResponse(step).value=group.questions[step.qi].answers[0];gCheck();}
  gMove(1);
 }`);
 assert.equal(run('G.ended'),true);
 assert.deepEqual(JSON.parse(run('JSON.stringify(gUnit().exercises.map(g=>P.grammar[grammarKey(gUnit(),g)].correct))')),[8,9,4,8]);
 assert.ok(run('gPlayerView()').includes('Лучший результат: 29 из 29'));
 assert.ok(run('gPlayerView()').includes('data-gnext-unit="016_tan_alto"'));
 const html=run(`gFacts(${JSON.stringify(unit15.exercises[1].questions[0].facts)})`);
 assert.equal((html.match(/class="gfacts-item"/g)||[]).length,2);
 assert.ok(html.includes('1,90 m') && html.includes('1,82 m'));
 const unsafe=run('gFacts({label:"<script>",items:[["<img>","<b>"]]})');
 assert.ok(!unsafe.includes('<script>') && unsafe.includes('&lt;img&gt;'));
 assert.equal(run('Object.keys(P.grammar).some(k=>k.startsWith("017_"))'),false);
});

test('unit 16 accepts both equality patterns and finishes before unit 17', () => {
 const run=context([unit16,unit17]);
 run(`gStart(COURSE.grammar[0].id);var turns16=0;
 while(!G.ended && turns16++<150) {
  const step=G.steps[G.at];
  if(step.type==='question'){const group=gGroups(gUnit()).find(g=>g.id===step.group);gResponse(step).value=group.questions[step.qi].answers.at(-1);gCheck();}
  gMove(1);
 }`);
 assert.equal(run('G.ended'),true);
 assert.deepEqual(JSON.parse(run('JSON.stringify(gUnit().exercises.map(g=>P.grammar[grammarKey(gUnit(),g)].correct))')),[7,8,6,8]);
 assert.ok(run('gPlayerView()').includes('Лучший результат: 29 из 29'));
 assert.ok(run('gPlayerView()').includes('data-gnext-unit="017_la_mas_alta"'));
 const q=unit16.exercises[1].questions[0];
 assert.equal(run(`grammarCorrect(${JSON.stringify(q)},'tan fácil como')`),true);
 assert.equal(run(`grammarCorrect(${JSON.stringify(q)},'igual de fácil que')`),true);
 assert.equal(run(`grammarCorrect(${JSON.stringify(q)},'igual de fácil como')`),false);
 assert.equal(run(`grammarCorrect(${JSON.stringify(unit16.exercises[2].questions[4])},'no soy tan fuerte como ti')`),false);
 assert.equal(run('Object.keys(P.grammar).some(k=>k.startsWith("017_"))'),false);
});

test('unit 17 only asks for the article and degree in two sentence gaps', () => {
 const run=context([unit17]);
 unlockUntil(run,'exercise:17.1');
 run('gStart(COURSE.grammar[0].id,"exercise:17.1");');
 const intro=run('gPlayerView()');
 assert.ok(intro.includes('<mark class="gpreview-insert">la</mark>'));
 assert.ok(intro.includes('<mark class="gpreview-insert">más</mark>'));
 run('gMove(1)');
 const html=run('gPlayerView()');
 assert.ok(html.includes('«самый красивый город»'));
 assert.ok(html.includes(' ciudad ') && html.includes(' bonita de Cuba?'));
 assert.ok(html.indexOf('¿Cuál es ') < html.indexOf('id="g-answer"'));
 assert.ok(html.indexOf('id="g-answer"') < html.indexOf('de Cuba?'));
 assert.equal((html.match(/id="g-answer"/g)||[]).length,1);
 assert.equal((html.match(/data-ggap=/g)||[]).length,2);
 assert.ok(!html.includes('class="gblank"'));
 run('gResponse(G.steps[G.at]).value="la más";gCheck();');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
});

test('unit 17 interleaves practice with relevant theory and locks the next block until practice is done', () => {
 const run=context([unit17]);
 unlockUntil(run,'exercise:17.1');
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"exercise:17.1")'),true);
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"section:5")'),false);
 run('gStart(COURSE.grammar[0].id);');
 const order=JSON.parse(run('JSON.stringify(G.steps.filter(s=>["theory","intro","summary"].includes(s.type)).map(s=>s.type==="theory"?"section:"+s.section:s.type==="intro"?"exercise:"+s.group:"summary"))'));
 assert.deepEqual(order,unit17.learningOrder);
 run('G=null;view.grammar=COURSE.grammar[0].id;');
 const menu=run('grammarView()');
 assert.ok(menu.indexOf('data-gstart="exercise:17.1"') < menu.indexOf('data-gstart="section:5"'));
});

test('resuming an older all-unit route rebases its current question onto the new order', () => {
 const run=context([unit17]);
 unlockUntil(run,'exercise:17.2');
 run(`gStart(COURSE.grammar[0].id);var u=COURSE.grammar[0];
 var oldOrder=u.learningOrder;delete u.learningOrder;var oldSteps=gSteps(u);u.learningOrder=oldOrder;
 G.steps=oldSteps;G.at=oldSteps.findIndex(s=>s.group==='17.1'&&s.qi===2);gSave();G=null;
 gStart(u.id,'all',true);`);
 assert.equal(run('G.steps[G.at].group'),'17.1');
 assert.equal(run('G.steps[G.at].qi'),2);
 assert.deepEqual(JSON.parse(run('JSON.stringify(G.steps)')),JSON.parse(run('JSON.stringify(gSteps(gUnit()))')));
});

const newUnits=fs.readdirSync('content/grammar').filter(f=>/^0(0[4-9]|1[0-4])_.*\.json$/.test(f)).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
test('theory scenes keep examples as text, escape untrusted markup and expose an enlargement button',()=>{
 const run=context();
 const art={image:'data:image/webp;base64,sample',alt:'<img onerror=bad>',examples:[['Es **un reloj**.','Это часы.'],['<script>bad</script>','Проверка экранирования']]};
 const html=run(`gArtFigure(${JSON.stringify(art)})`);
 assert.ok(html.includes('aria-label="Увеличить иллюстрацию"'));
 assert.ok(html.includes('Es <strong>un reloj</strong>.'));
 assert.ok(html.includes('Это часы.'));
 assert.ok(!html.includes('<script>'));
 assert.ok(!html.includes('alt="<img'));
 assert.equal(run('gArtFigure(null)'),'');
});
test('units 4–14 complete their interleaved routes, keep manual feedback and lead to the next actual unit', () => {
 assert.equal(newUnits.length,11);
 for(const u of newUnits){
  const next=newUnits.find(n=>n.number===u.number+1)||unit15;
  const run=context([u,next]);
  run('render=()=>{};sfx=()=>{};gStart(COURSE.grammar[0].id)');
  assert.equal(run('gRouteOpen(gUnit(),gRoutes(gUnit())[1])'),false);
  const order=JSON.parse(run('JSON.stringify(G.steps.filter(s=>s.type!=="question").map(s=>gStepRoute(gUnit(),s)))'));
  assert.deepEqual(order,u.learningOrder);
  run(`for(let guard=0;G&&!G.ended&&guard<800;guard++){
    const step=G.steps[G.at];
    if(step.type==='question'){
      const group=gGroups(gUnit()).find(g=>g.id===step.group),q=group.questions[step.qi],at=G.at;
      gResponse(step).value=q.answers.at(-1);gCheck();
      if(G.at!==at)throw Error('Automatic advance');
      if(!gPlayerView().includes('data-gnext'))throw Error('Missing manual next');
    }
    gMove(1);
  }`);
  assert.equal(run('G.ended'),true, u.number);
  assert.equal(run('gUnitFinished(gUnit())'),true,u.number);
  assert.ok(run('gPlayerView()').includes(`data-gnext-unit="${next.id}"`));
  assert.equal(run('gGroups(gUnit()).every(g=>P.grammar[grammarKey(gUnit(),g)].correct===g.questions.length)'),true);
 }
});

test('new article questions leave nouns written and the clock/distance aids render accessibly', () => {
 const run=context(newUnits);
 const unit9=newUnits.find(u=>u.number===9),unit12=newUnits.find(u=>u.number===12),unit13=newUnits.find(u=>u.number===13);
 const clock=run(`gClock(${JSON.stringify(unit9.exercises[0].questions[2].clock)})`);
 assert.ok(clock.includes('Часы: 03:50'));
 assert.ok(clock.includes('rotate(115 80 80)'));
 assert.ok(clock.includes('rotate(300 80 80)'));
 const distance=run('gDistance("far")');
 assert.equal((distance.match(/gdistance-zone is-active/g)||[]).length,1);
 assert.ok(distance.includes('Далеко от обоих')&&distance.includes('Здесь находится предмет'));
 assert.equal(unit12.exercises[2].questions.some(q=>q.distance),false);
 run(`gStart(${JSON.stringify(unit13.id)});G.at=G.steps.findIndex(s=>s.group==='13.1'&&s.type==='question');`);
 const html=run('gPlayerView()');
 assert.ok(html.includes('Vivo en un piso '));
 assert.equal((html.match(/id="g-answer"/g)||[]).length,1);
 assert.ok(html.includes('clues')&&html.includes('pequeño'));
});

test('unit 10 cannot celebrate until its recap is read, regardless of exercise array order', () => {
 const u=newUnits.find(u=>u.number===10),run=context([u]);
 run('render=()=>{};sfx=()=>{};for(const g of gGroups(COURSE.grammar[0]))P.grammar[grammarKey(COURSE.grammar[0],g)]={correct:g.questions.length,total:g.questions.length};gStart(COURSE.grammar[0].id,gRoutes(COURSE.grammar[0]).filter(r=>r.startsWith("exercise:")).at(-1));G.ended=true;');
 assert.equal(run('gUnitFinished(gUnit())'),false);
 assert.ok(!run('gPlayerView()').includes('Поздравляю!'));
 run('gStart(COURSE.grammar[0].id,"summary");gMove(1);');
 assert.equal(run('gUnitFinished(gUnit())'),true);
 assert.ok(run('gPlayerView()').includes('Поздравляю!'));
});

test('word banks support repeated words, undo, explicit checking, retries and stored attempts',()=>{
 const run=context([unit17]);
 unlockUntil(run,'exercise:17.2');
 run('gStart(COURSE.grammar[0].id,"exercise:17.2");gMove(1);document.querySelector=()=>null;');
 run(`var q=gUnit().exercises[1].questions[0];var r=gResponse(G.steps[G.at]);
 for(const word of q.answers[0].split(' ')){const i=q.tiles.findIndex((t,i)=>t===word&&!r.chosen?.includes(i));gBuild('add',i);}
 var current=G.at;var count=r.chosen.length;gBuild('add',r.chosen[0]);`);
 assert.equal(run('r.chosen.length'),run('count'));
 assert.equal(run('r.checked'),false);
 assert.equal(run('G.at'),run('current'));
 run('gBuild("remove",1);');
 assert.notEqual(run('r.value'),run('q.answers[0]'));
 run('gBuild("remove",0);gBuild("remove",0);');
 assert.equal(run('r.value'),'');
 run(`for(const word of q.answers[0].split(' ')){const i=q.tiles.findIndex((t,i)=>t===word&&!r.chosen.includes(i));gBuild('add',i);}gCheck();`);
 assert.equal(run('r.good'),true);
 assert.equal(run('G.at'),run('current'));
 run('G=null;gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(run('gResponse(G.steps[G.at]).value'),'el más simpático');
 assert.equal(run('gResponse(G.steps[G.at]).checked'),true);
 const duplicate=run(`gBuilder({tiles:['la','más','sana','y','la','más','fresca']},{value:'',chosen:[0,1]})`);
 assert.ok(duplicate.includes('data-gadd="4" lang="es" >la'));
});

test('old typed answers remain editable and reordered locked attempts retain responses',()=>{
 const run=context([unit17]);
 assert.equal(run(`gQuestionMode({tiles:['el','más','alto']},{value:'el más',checked:false})`),'input');
 assert.equal(run(`gQuestionMode({tiles:['el','más','alto']},{value:'el más',chosen:[0,1],checked:false})`),'build');
 unlockUntil(run,'section:5');
 run(`gStart(COURSE.grammar[0].id,'section:5');G.responses={'17.1':{0:{value:'la más',checked:true,good:true}}};gSave();G=null;P=fresh();gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('G.steps[G.at].type'),'theory');
 assert.equal(run('G.steps[G.at].section'),0);
 assert.equal(run('G.responses["17.1"][0].value'),'la más');
 assert.equal(run('G.responses["17.1"][0].good'),true);
});

test('all 17 units complete through their actual interaction and keep canonical answer indices',()=>{
 const all=fs.readdirSync('content/grammar').filter(f=>/^\d{3}_.*\.json$/.test(f)).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 for(const u of all){
  assert.ok(u.learningOrder.includes('summary'));
  const run=context([u]);run('gStart(COURSE.grammar[0].id);document.querySelector=()=>null;');
  run(`var turns=0;
  while(!G.ended&&turns++<400){const s=G.steps[G.at];
   if(s.type==='question'){const q=gGroups(gUnit()).find(g=>g.id===s.group).questions[s.qi];
    if(q.guidedGaps){
      const f=q.guidedGaps;let found;
      const search=(values=[])=>{if(values.length===f.choices.length){if(gComposeGaps(f.parts,values)===q.answers[0])found=values;return;}
        for(const word of f.choices[values.length])search([...values,word]);};search();
      found.forEach((word,i)=>gSelectGap(i,f.choices[i].indexOf(word)));gCheck();
    }
    else if(q.tiles){const r=gResponse(s);for(const word of q.answers[0].split(' ')){gBuild('add',q.tiles.findIndex((w,i)=>w===word&&!r.chosen?.includes(i)));}gCheck();}
    else if(q.options)gPick(q.options.indexOf(q.answers[0]));
    else{gResponse(s).value=q.answers[0];gCheck();}
   }gMove(1);
  }`);
  assert.equal(run('G.ended'),true,u.id);
  assert.ok(run('gUnit().exercises.every(g=>P.grammar[grammarKey(gUnit(),g)].correct===g.questions.length)'),u.id);
  assert.equal(run('P.xp'),u.sections.reduce((n,s)=>n+(s.check?.questions.length||0),0)*2+u.exercises.reduce((n,g)=>n+g.questions.length,0)*2,u.id);
 }
});

test('an old hotel choice resumes as editable input without losing checked answers or best progress',()=>{
 const run=context([unit3]);
 unlockUntil(run,'exercise:3.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:3.1');
   G.at=8; G.responses['3.1']={7:{value:'hotel',checked:false},1:{value:'peces',checked:true,good:true}};
   P.grammar[grammarKey(gUnit(),gUnit().exercises[0])]={correct:16,total:18};
   gSave(); G=null; gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('G.at'),8);
 assert.equal(run('gResponse(G.steps[G.at]).value'),'hotel');
 assert.ok(run('gPlayerView()').includes('id="g-answer"'));
 assert.ok(!run('gPlayerView()').includes('data-gpick'));
 run(`gResponse(G.steps[G.at]).value='hotels';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).good'),false);
 assert.equal(run('G.at'),8);
 assert.ok(run('gPlayerView()').includes('После -l добавляем -es'));
 run('gSave();G=null;gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(run('gResponse(G.steps[G.at]).checked'),true);
 assert.equal(run('G.responses["3.1"][1].good'),true);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().exercises[0])].correct'),16);
 run('gRetry();');
 assert.equal(run('gResponse(G.steps[G.at]).good'),false);
 assert.equal(run('G.responses["3.1"][7].value'),"hotels");
});

test('all group-name answers use a single noun input and keep manual checking and progress',()=>{
 const run=context([unit3]);unlockUntil(run,'exercise:3.3');
 run(`gStart(COURSE.grammar[0].id,'exercise:3.3');gMove(1);`);
 for(const q of unit3.exercises[2].questions){
  const html=run('gPlayerView()');
  assert.ok(html.includes('id="g-answer"') && html.includes('Одно слово без артикля'));
  assert.ok(html.includes('Впиши одно существительное во множественном числе'));
  assert.ok(html.includes('<strong>') && !html.includes('data-gpick') && !html.includes('data-gadd'));
  const at=run('G.at');
  run(`gResponse(G.steps[G.at]).value=${JSON.stringify(q.answers[0])};gMove(1);`);
  assert.equal(run('G.at'),at,'typing alone cannot submit or advance');
  run('gCheck();');
  assert.equal(run('gResponse(G.steps[G.at]).good'),true,q.prompt);
  assert.equal(run('G.at'),at,'feedback stays visible until Next');
  run('gMove(1);');
 }
 assert.equal(run('G.steps[G.at].type'),'summary');
 run('gMove(1);');
 assert.equal(run('G.ended'),true);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().exercises[2])].correct'),10);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[2]).errors'),0);
 assert.equal(run(`grammarCorrect(gUnit().exercises[2].questions[1],'los abuelos')`),false);
 assert.equal(run(`grammarCorrect(gUnit().exercises[2].questions[1],' ABUELOS ')`),true);
});

test('the group-name mini-check keeps errors and repeats them without losing lives',()=>{
 const storage=new Map();let run=context([unit3],storage);unlockUntil(run,'section:8');
 run(`gStart(COURSE.grammar[0].id,'section:8');gMove(1);
  gPick(0);gMove(1);gExit();`);
 run=context([unit3],storage);
 // Unlocking is a fixture setup; the attempt itself is restored from the real journal.
 unlockUntil(run,'section:8');
 run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[8].check).errors'),1);
 for(const wrong of ['madres','alumnos']){
  const html=run('gPlayerView()');
  assert.ok(!html.includes('id="g-answer"') && html.includes('data-gpick'));
  assert.ok(html.includes('Выбери правильный ответ.'));
  run(`gPick(gUnit().sections[8].check.questions[G.steps[G.at].qi].options.indexOf(${JSON.stringify(wrong)}));gMove(1);`);
 }
 assert.ok(!run('G.recovery'));
 assert.equal(run('G.steps[G.at].correction'),true);
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[8].check).errors'),3);
 assert.equal(run('!!P.grammar[grammarKey(gUnit(),gUnit().sections[8].check)]'),false);
 run(`while(!G.ended){const s=G.steps[G.at];gResponse(s).value=gUnit().sections[8].check.questions[s.qi].answers[0];gCheck();gMove(1);}`);
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[8].check).errors'),3);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().sections[8].check)].correct'),0);
});

test('every mini-check in all 17 units renders choices and completes by clicking',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>f.endsWith('.json')).sort()
  .map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 assert.equal(units.length,41);
 for(const unit of units){
  const run=context([unit]);
  for(const [index,section] of unit.sections.entries()){
   if(!section.check)continue;
   const route=`section:${index}`;
   unlockUntil(run,route);
   run(`gStart(COURSE.grammar[0].id,${JSON.stringify(route)});gMove(1);`);
   for(const q of section.check.questions){
    const html=run('gPlayerView()');
    assert.equal((html.match(/data-gpick="/g)||[]).length,q.options.length,unit.id+': '+q.prompt);
    assert.ok(!/<input|<textarea|data-gcheck/.test(html));
    const correct=q.options.findIndex(o=>q.answers.includes(o));
    run(`gPick(${correct});`);
    assert.equal(run('gResponse(G.steps[G.at]).good'),true);
    assert.ok(run('gPlayerView()').includes('data-gnext'));
    run('gMove(1);');
   }
   assert.equal(run('G.ended'),true);
   assert.equal(run(`P.grammar[grammarKey(gUnit(),gUnit().sections[${index}].check)].correct`),section.check.questions.length);
  }
 }
});

test('gorilla mini-check resumes a typed answer with choices and accepts stored alternatives',()=>{
 const storage=new Map();let run=context([unit2],storage);unlockUntil(run,'section:5');
 run(`gStart(COURSE.grammar[0].id,'section:5');gMove(1);gPick(2);gMove(1);
  gResponse(G.steps[G.at]).value='la gorila';gSave();gExit();`);
 run=context([unit2],storage);unlockUntil(run,'section:5');
 run(`gStart(COURSE.grammar[0].id,'all',true);`);
 const html=run('gPlayerView()');
 assert.ok(html.includes('Самка гориллы') && html.includes('data-gpick'));
 assert.ok(!/<input|<textarea/.test(html));
 assert.equal(run(`grammarCorrect(gUnit().sections[5].check.questions[1],gResponse(G.steps[G.at]).value)`),true);
 run('gPick(1);');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.ok(run('gPlayerView()').includes('la gorila'));
});

test('time practice offers complete openings for both current time and scheduled events',()=>{
 const all=JSON.parse(fs.readFileSync('content/grammar/009_tiempo_fecha.json','utf8'));
 const run=context([all]);unlockUntil(run,'exercise:9.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:9.1');gMove(1);`);
 let html=run('gPlayerView()');
 assert.ok(html.includes('Es la') && html.includes('Son las'));
 assert.ok(!html.includes('Son ___'));
 run(`gPick(gUnit().exercises[0].questions[0].options.indexOf('Son las'));`);
 assert.equal(run('gResponse(G.steps[G.at]).value'),'Son las');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('G.at'),1);
 assert.equal(run(`gOptionLabel({optionLabels:{la:'<img>'}},'la')`),'<img>');
 run(`gUnit().exercises[0].questions[0].optionLabels={'Son las':'<img src=x>'};`);
 assert.ok(run('gPlayerView()').includes('&lt;img src=x&gt;'));
});

test('article omission is compact, accessible and works in converted input with an explicit control',()=>{
 const all=JSON.parse(fs.readFileSync('content/grammar/008_nombres_propios.json','utf8'));
 const run=context([all]);unlockUntil(run,'exercise:8.3');
 run(`gStart(COURSE.grammar[0].id,'exercise:8.3');G.at=3;`);
 assert.ok(run('gPlayerView()').includes('placeholder="Артикль или ∅"'));
 assert.ok(run('gPlayerView()').includes('data-gno-article'));
 for(const spelling of ['∅','—','-','Без артикля']) assert.equal(run(`grammarCorrect(gUnit().exercises[2].questions[2],${JSON.stringify(spelling)})`),true);
 assert.equal(run(`grammarCorrect({answers:['las']},'∅')`),false);
 run(`gResponse(G.steps[G.at]).value='∅';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('G.at'),3);
});

test('form paradigms have a desktop table and readable mobile definitions with escaped text',()=>{
 const run=context([unit17]);
 const html=run('gTheoryTable(COURSE.grammar[0].sections[3].table)');
 assert.ok(html.includes('class="gforms-wide"') && html.includes('class="gforms-mobile"'));
 assert.ok(html.includes('<dt>Женский род</dt><dd lang="es">la mejor</dd>'));
 const unsafe=run(`gTheoryTable({compactForms:true,heads:['<script>','<img>'],rows:[['<b>','<svg>']]})`);
 assert.ok(!unsafe.includes('<script>')&&!unsafe.includes('<svg>')&&unsafe.includes('&lt;svg&gt;'));
});

test('17.2 keeps the Russian answer cue visible before, during and after assembly',()=>{
 const run=context([unit17]);
 const q=unit17.exercises[1].questions[3];
 assert.equal(q.answerHint,'наименее трудолюбивый');
 for(const response of [{value:'',chosen:[]},{value:'el',chosen:[q.tiles.indexOf('el')]},{value:q.answers[0],checked:true}]){
  const html=run(`gBuilder(${JSON.stringify(q)},${JSON.stringify(response)})`);
  assert.ok(html.includes('Нужно сказать:')&&html.includes('наименее трудолюбивый'));
  assert.ok(html.indexOf('наименее трудолюбивый')<html.indexOf('class="gbuild-answer"'));
 }
 assert.ok(unit17.exercises[1].questions.every(q=>q.answerHint));
 assert.ok(!run('gAnswerHint({answerHint:"<img>"})').includes('<img>'));
});

test('17.3 fills words in a fixed sentence, keeps partial choices on resume and checks manually',()=>{
 const run=context([unit17]);
 unlockUntil(run,'exercise:17.3');
 run('gStart(COURSE.grammar[0].id,"exercise:17.3");gMove(1);document.querySelector=()=>null;');
 let html=run('gPlayerView()');
 assert.equal((html.match(/data-gslot=/g)||[]).length,4);
 assert.ok(html.includes(' bebida ') && html.includes(' sana y ') && html.includes(' refrescante'));
 assert.ok(html.includes('самый полезный и освежающий напиток'));
 assert.ok(!html.includes('data-gadd=') && !html.includes('data-gpick='));
 assert.ok(html.includes('data-gcheck disabled'));
 run('gSelectGap(0,1);gCheck();');
 assert.equal(run('gResponse(G.steps[G.at]).checked'),false);
 assert.equal(run('gResponse(G.steps[G.at]).activeGap'),1);
 run('G=null;gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(run('gResponse(G.steps[G.at]).slotValues[0]'),'la');
 run('gSelectGap(1,1);gSelectGap(2,1);gSelectGap(3,0);gCheck();');
 assert.equal(run('gResponse(G.steps[G.at]).good'),false);
 html=run('gPlayerView()');
 assert.ok(html.includes('data-gnext'));
 assert.ok(!html.includes(' / la bebida'));
 run(`gMove(1);while(!G.steps[G.at].correction){const s=G.steps[G.at];gResponse(s).value=gUnit().exercises[2].questions[s.qi].answers[0];gCheck();gMove(1);}gSelectGap(0,1);gSelectGap(1,0);gSelectGap(2,1);gSelectGap(3,0);gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('G.ended'),false);
 run('var checkedAt=G.at;gMove(1);');
 assert.equal(run('G.ended'),true);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[2]).errors'),1);
 assert.equal(run('gQuestionMode(gUnit().exercises[2].questions[0],{value:"la más",chosen:[5,2]})'),'build');
 assert.equal(run('gQuestionMode(gUnit().exercises[2].questions[0],{value:"la bebida",checked:false})'),'input');
 assert.ok(!run('gGuided({...gUnit().exercises[2].questions[0],answerHint:"<img>"},{})').includes('<img>'));
});

test('all typing screens show a persistent format and example without changing grading', () => {
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 let typed=0,legacy=0;
 for(const unit of units) {
  const run=context([unit]);
  run('gStart(COURSE.grammar[0].id,"all");');
  const result=JSON.parse(run(`JSON.stringify((() => {
   let typed=0,legacy=0;
   for(let i=0;i<G.steps.length;i++) {
    const step=G.steps[i]; if(step.type!=='question') continue;
    const group=gGroups(gUnit()).find(g=>g.id===step.group),q=group.questions[step.qi];
    if(q.options) continue;
    G.at=i;
    const r=gResponse(step);
    // A saved typed answer in a bank/guided task must retain an editable typing screen.
    if(q.tiles||q.guidedGaps) {r.value='saved answer';legacy++;} else typed++;
    let html=gPlayerView(),format=grammarInputFormat(q,group);
    if(!html.includes(esc(format.instruction))||(format.example && !html.includes(esc(format.example)))||!html.includes('aria-describedby="g-answer-format"')) throw Error(group.id+': missing guidance');
    if(!q.gapParts&&!html.includes('placeholder="'+esc(format.placeholder)+'"')) throw Error(group.id+': missing placeholder');
    r.value=q.answers[0];
    if(!grammarCorrect(q,r.value))throw Error(group.id+': changed answer');
    r.checked=true;r.good=true;
    html=gPlayerView();
    if((gQuestionMode(q,r)==='input'&&(format.example && !html.includes(esc(format.example))))||!html.includes('data-gnext'))throw Error(group.id+': guidance or manual Next disappeared');
   }
   return {typed,legacy};
  })())`));
  typed+=result.typed;legacy+=result.legacy;
 }
 assert.equal(typed,1033);assert.equal(legacy,134);
});

test('quantity answers accept digits or words while the field explains the quantity format', () => {
 const run=context([unit3]);
 unlockUntil(run,'exercise:3.2');
 run('gStart(COURSE.grammar[0].id,"exercise:3.2");gMove(1);');
 const html=run('gPlayerView()');
 assert.ok(html.includes('Напиши количество и название предметов'));
 assert.ok(html.includes('Вместо un/una можно написать 1'));
 assert.ok(html.includes('placeholder="Количество и название"'));
 for(const answer of ['una mesa','1 mesa'])assert.equal(run(`grammarCorrect(COURSE.grammar[0].exercises[1].questions[0],${JSON.stringify(answer)})`),true);
 for(const answer of ['mesa','la mesa','dos mesas'])assert.equal(run(`grammarCorrect(COURSE.grammar[0].exercises[1].questions[0],${JSON.stringify(answer)})`),false);
 run('gResponse(G.steps[G.at]).value="1 mesa";gCheck();');
 assert.equal(run('G.at'),1);
 assert.ok(run('gPlayerView()').includes('Пример формата:'));
 run('gMove(1);');
 assert.equal(run('G.at'),2);
 assert.ok(run('gPlayerView()').includes('dos coches / 2 coches'));
});

test('format overrides work in textareas, and article-free answers stay article-free', () => {
 const run=context([unit17]);unlockUntil(run,'exercise:17.2');
 run('gStart(COURSE.grammar[0].id,"exercise:17.2");gMove(1);gResponse(G.steps[G.at]).value="saved answer";');
 assert.ok(run('gPlayerView()').includes('<textarea'));
 assert.ok(run('gPlayerView()').includes('placeholder="Артикль и сравнение"'));
 const gender=context([unit]);
 assert.equal(gender('grammarCorrect(COURSE.grammar[0].exercises[1].questions[0],"señora")'),true);
 assert.equal(gender('grammarCorrect(COURSE.grammar[0].exercises[1].questions[0],"la señora")'),false);
 assert.ok(gender('grammarForm(COURSE.grammar[0],COURSE.grammar[0].exercises[1])').includes('без артикля: la уже написано'));
});

test('the size-based life limit stops every exercise in all 17 units, without credit or a Next button', () => {
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 let count=0;
 for(const u of units) for(const group of u.exercises) {
  const limit=Math.max(3,Math.ceil(group.questions.length/5));
  const run=context([u]);unlockUntil(run,'exercise:'+group.id);
  run(`gStart(COURSE.grammar[0].id,${JSON.stringify('exercise:'+group.id)});gMove(1);`);
  assert.ok(run('gPlayerView()').includes(`Осталось попыток: ${limit} из ${limit}`));
  for(let error=1;error<=limit;error++) {
   run(`var s=G.steps[G.at],q=gGroups(gUnit()).find(g=>g.id===s.group).questions[s.qi];
     if(q.options)gPick(q.options.findIndex(o=>!grammarCorrect(q,o)));
     else{gResponse(s).value='wrong';gCheck();}`);
   assert.equal(run(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id===${JSON.stringify(group.id)})).errors`),error,u.number+'/'+group.id);
   if(error<limit) {
    assert.ok(run('gPlayerView()').includes(`Осталось попыток: ${limit-error} из ${limit}`));
    if(error===limit-1)assert.ok(run('gPlayerView()').includes('Осталась последняя попытка'));
    run('gMove(1)');
   }
  }
  assert.equal(run(`G.recovery`),group.id);
  assert.equal(run(`!!P.grammar[${JSON.stringify(u.id+'/'+group.id)}]`),false);
  assert.ok(run('gPlayerView()').includes('Пока не получилось. Давай повторим правило!'));
  assert.ok(!run('gPlayerView()').includes('data-gnext'));
  const before=run('G.at');run('gMove(1);gMove(-1);gCheck();gRepeatExercise();');
  assert.equal(run('G.at'),before);
  assert.equal(run(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id===${JSON.stringify(group.id)})).errors`),limit);
  count++;
 }
 assert.equal(count,156);
});

test('exit, route restart, whole-unit restart and reload preserve the failed or active attempt', () => {
 const run=context([unit3]);unlockUntil(run,'exercise:3.2');
 run('gStart(COURSE.grammar[0].id,"exercise:3.2");gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();');
 const id=run('gAttempt(gUnit(),gUnit().exercises[1]).id');
 run('gExit();gStart(COURSE.grammar[0].id,"exercise:3.1");gExit();gStart(COURSE.grammar[0].id,"exercise:3.2");gMove(1);');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),2);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).id'),id);
 assert.equal(run('gResponse(G.steps[G.at]).checked'),true);
 run('gMove(1);gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();gExit();G=null;gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(run('G.recovery'),'3.2');
 assert.ok(run('gPlayerView()').includes('Повторить теорию'));
 run('gExit();gStart(COURSE.grammar[0].id,"all");G.at=G.steps.findIndex(s=>s.group==="3.2");gPlayerView();');
 assert.equal(run('G.recovery'),'3.2');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),3);
});

test('failed 3.2 reviews its own rule, preserves review position and resets only after reading it', () => {
 const run=context([unit3]);unlockUntil(run,'exercise:3.2');
 run('gStart(COURSE.grammar[0].id,"exercise:3.2");gMove(1);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value="wrong";gCheck();if(i<2)gMove(1);}');
 const oldId=run('gAttempt(gUnit(),gUnit().exercises[1]).id');
 run('gReviewTheory();');
 assert.ok(run('gPlayerView()').includes('Один предмет, но слово во множественном числе'));
 assert.ok(run('gPlayerView()').includes('Попробовать ещё раз'));
 run('gExit();gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).status'),'review');
 run('gRepeatExercise();');
 assert.equal(run('G.steps[G.at].type'),'intro');
 assert.equal(run('G.recovery'),null);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),0);
 assert.notEqual(run('gAttempt(gUnit(),gUnit().exercises[1]).id'),oldId);
 assert.equal(run('Object.keys(G.responses["3.2"]).length'),0);
 run('gMove(1);while(!G.ended){const s=G.steps[G.at];gResponse(s).value=gUnit().exercises[1].questions[s.qi].answers[0];gCheck();gMove(1);}');
 assert.equal(run('P.grammar[gUnit().id+"/3.2"].correct'),10);
});

test('multi-part theory starts at the right block and cannot reset hearts before its last screen', () => {
 const run=context([unit17]);unlockUntil(run,'exercise:17.3');
 run('gStart(COURSE.grammar[0].id,"exercise:17.3");gMove(1);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value="wrong";gCheck();if(i<2)gMove(1);}gReviewTheory();');
 assert.ok(run('gPlayerView()').includes(unit17.sections[3].title));
 assert.ok(!run('gPlayerView()').includes('data-grepeat-exercise'));
 run('gRepeatExercise();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[2]).errors'),3);
 run('gReviewMove(1);gExit();gStart(COURSE.grammar[0].id,"all",true);');
 assert.ok(run('gPlayerView()').includes(unit17.sections[4].title));
 run('gRepeatExercise();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[2]).errors'),0);
});

test('third mistake on the last question fails, and previous successful results remain intact', () => {
 const run=context([unit]);unlockUntil(run,'exercise:1.1');
 run('gStart(COURSE.grammar[0].id,"exercise:1.1");gMove(1);while(!G.ended){const s=G.steps[G.at];gResponse(s).value=gUnit().exercises[0].questions[s.qi].answers[0];gCheck();gMove(1);}');
 const xp=run('P.xp'),best=run('P.grammar[gUnit().id+"/1.1"].correct');
 run('gStart(COURSE.grammar[0].id,"exercise:1.1");gMove(1);for(let i=0;i<10;i++){const s=G.steps[G.at];gResponse(s).value=i>=7?"wrong":gUnit().exercises[0].questions[i].answers[0];gCheck();if(i<9)gMove(1);}');
 assert.equal(run('G.recovery'),'1.1');
 assert.equal(run('P.xp'),xp);assert.equal(run('P.grammar[gUnit().id+"/1.1"].correct'),best);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).status'),'failed');
});

test('duplicate submission and back navigation never refund or double-charge hearts', () => {
 const run=context([unit]);unlockUntil(run,'exercise:1.2');
 run('gStart(COURSE.grammar[0].id,"exercise:1.2");gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();gCheck();gMove(-1);gMove(1);gCheck();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
 run('gMove(1);gResponse(G.steps[G.at]).value="jefa";gCheck();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
 assert.ok(run('gPlayerView()').includes('Осталось попыток: 2 из 3'));
});

test('errors during correction do not consume lives or change the first-answer score', () => {
 const run=context([unit]);unlockUntil(run,'exercise:1.1');
 run('gStart(COURSE.grammar[0].id,"exercise:1.1");gMove(1);while(!G.ended){const s=G.steps[G.at];gResponse(s).value=!s.correction && s.qi<2?"wrong":gUnit().exercises[0].questions[s.qi].answers[0];gCheck();gMove(1);}gRetry();gResponse(G.steps[G.at]).value="wrong";gCheck();');
 assert.ok(!run('G.recovery'));
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),2);
 assert.equal(run('P.grammar[gUnit().id+"/1.1"].correct'),8);
});

test('mini checks use their own theory, and partial legacy attempts retain existing errors', () => {
 const run=context([unit]);run('gStart(COURSE.grammar[0].id,"section:0");gMove(1);');
 run('for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value="wrong";gCheck();if(i<2)gMove(1);}gReviewTheory();');
 assert.deepEqual(JSON.parse(run('JSON.stringify(gTheorySections(gUnit(),gUnit().sections[0].check))')),[0]);
 assert.equal(run('!!P.grammar[gUnit().id+"/check-a"]'),false);
 const legacy=context([unit3]);unlockUntil(legacy,'exercise:3.1');
 legacy('gStart(COURSE.grammar[0].id,"exercise:3.1");G.at=3;G.responses["3.1"]={0:{value:"wrong",checked:true,good:false},1:{value:"wrong",checked:true,good:false}};store.set(G_SESSION_KEY,JSON.stringify(G));store.set(G_ATTEMPTS_KEY,"");G=null;gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(legacy('gAttempt(gUnit(),gUnit().exercises[0]).errors'),2);
});

test('a fresh JavaScript context and another tab cannot reset errors or overwrite checked answers', () => {
 const storage=new Map(),run=context([unit3],storage);unlockUntil(run,'exercise:3.2');run('save();gStart(COURSE.grammar[0].id,"exercise:3.2");gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();gMove(1);');
 const reload=context([unit3],storage);reload('gStart(COURSE.grammar[0].id,"all",true);');
 assert.equal(reload('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
 reload('gResponse(G.steps[G.at]).value="wrong";gCheck();');
 assert.equal(reload('gAttempt(gUnit(),gUnit().exercises[1]).errors'),2);
 run('gResponse(G.steps[G.at]).value="dos botellas";gCheck();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),2);
 assert.equal(run('gResponse(G.steps[G.at]).value'),'wrong');
 run('gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();');
 assert.equal(run('G.recovery'),'3.2');
 reload('gMove(1);gPlayerView();');
 assert.equal(reload('G.recovery'),'3.2');
});

test('actual bank and guided-gap submissions use the same error counter; incomplete answers cost nothing', () => {
 const bank=context([unit17]);unlockUntil(bank,'exercise:17.2');
 bank('gStart(COURSE.grammar[0].id,"exercise:17.2");gMove(1);document.querySelector=()=>null;gCheck();gBuild("add",0);gCheck();');
 assert.equal(bank('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
 const gaps=context([unit17]);unlockUntil(gaps,'exercise:17.3');
 gaps('gStart(COURSE.grammar[0].id,"exercise:17.3");gMove(1);document.querySelector=()=>null;gSelectGap(0,0);gCheck();');
 assert.equal(gaps('gAttempt(gUnit(),gUnit().exercises[2]).errors'),0);
 gaps(`var q=gUnit().exercises[2].questions[0];for(let i=1;i<q.guidedGaps.choices.length;i++)gSelectGap(i,0);
 if(grammarCorrect(q,gResponse(G.steps[G.at]).value))gSelectGap(0,1);gCheck();`);
 assert.equal(gaps('gAttempt(gUnit(),gUnit().exercises[2]).errors'),1);
});

test('the older form path also stops at the size-based limit without granting progress', () => {
 const run=context([unit3]);unlockUntil(run,'exercise:3.1');
 run('gSubmitGrammarForm(COURSE.grammar[0],COURSE.grammar[0].exercises[0],COURSE.grammar[0].exercises[0].questions.map(()=>"wrong"));');
 assert.equal(run('G.recovery'),'3.1');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),4);
 assert.equal(run('!!P.grammar[gUnit().id+"/3.1"]'),false);
});

test('review and retry in a full-unit run return to the exercise and then its next theory block', () => {
 const run=context([unit3]);unlockUntil(run,'exercise:3.2');
 run('gStart(COURSE.grammar[0].id,"all");G.at=G.steps.findIndex(s=>s.type==="intro"&&s.group==="3.2");gMove(1);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value="wrong";gCheck();if(i<2)gMove(1);}gReviewTheory();gRepeatExercise();');
 assert.equal(run('G.route'),'all');
 assert.equal(run('G.steps[G.at].group'),'3.2');
 assert.equal(run('G.steps[G.at].type'),'intro');
 run('gMove(1);for(let i=0;i<10;i++){const s=G.steps[G.at];gResponse(s).value=gUnit().exercises[1].questions[s.qi].answers[0];gCheck();gMove(1);}');
 assert.equal(run('G.steps[G.at].type'),'theory');
 assert.equal(run('G.steps[G.at].section'),8);
 assert.equal(run('G.ended'),false);
});


test('life counts round up per five questions with a minimum of three',()=>{
 for(const [size,limit] of [[3,3],[15,3],[16,4],[20,4],[21,5],[25,5],[26,6]]){
  const u=structuredClone(unit3),g=u.exercises[0];
  g.questions=Array.from({length:size},()=>structuredClone(g.questions[0]));
  const run=context([u]);unlockUntil(run,'exercise:'+g.id);
  run(`gStart(COURSE.grammar[0].id,'exercise:3.1');gMove(1);`);
  assert.equal(run('gErrorLimit(gUnit().exercises[0])'),limit);
  assert.ok(run('gPlayerView()').includes(`Осталось попыток: ${limit} из ${limit}`));
  // One life left still permits completing the exercise and earning progress.
  for(let i=0;i<size;i++){
   run(`gResponse(G.steps[G.at]).value=${i<limit-1?"'wrong'":"gUnit().exercises[0].questions[0].answers[0]"};gCheck();`);
   if(i===limit-2)assert.ok(run('gPlayerView()').includes('Осталась последняя попытка'));
   run('gMove(1);');
  }
  assert.equal(run('G.ended'),false);
  run(`while(!G.ended){const s=G.steps[G.at];gResponse(s).value=gUnit().exercises[0].questions[s.qi].answers[0];gCheck();gMove(1);}`);
  assert.equal(run('P.grammar[gUnit().id+"/3.1"].correct'),size-limit+1);
 }
});

test('an old failed long exercise gains lives on reload without losing its mistakes',()=>{
 const storage=new Map();let run=context([unit3],storage);unlockUntil(run,'exercise:3.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:3.1');gMove(1);
  for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='wrong';gCheck();if(i<2)gMove(1);}
  var old=gAttempt(gUnit(),gUnit().exercises[0]);delete old.limit;old.status='failed';
  gStoreAttempt(gUnit(),gUnit().exercises[0],old);G.recovery='3.1';
  store.set(G_SESSION_KEY,JSON.stringify(G));G=null;`);
 run=context([unit3],storage);unlockUntil(run,'exercise:3.1');
 run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.ok(!run('G.recovery'));
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),3);
 assert.ok(run('gPlayerView()').includes('Осталось попыток: 1 из 4'));
 run(`gMove(1);gResponse(G.steps[G.at]).value='wrong';gCheck();`);
 assert.equal(run('G.recovery'),'3.1');
 assert.ok(run('gPlayerView()').includes('Лимит ошибок исчерпан (4)'));
});

test('every exercise automatically repeats mistakes, without lives, credit or score inflation',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 for(const u of units)for(const group of u.exercises){
  const run=context([u]);unlockUntil(run,'exercise:'+group.id);
  run(`gStart(COURSE.grammar[0].id,${JSON.stringify('exercise:'+group.id)});gMove(1);`);
  for(let i=0;i<group.questions.length;i++){
   run(`gResponse(G.steps[G.at]).value=${JSON.stringify(i===0?'wrong':group.questions[i].answers[0])};gCheck();gMove(1);`);
  }
  assert.equal(run('G.steps[G.at].correction'),true);
  assert.equal(run('G.steps[G.at].qi'),0);
  assert.equal(run('G.ended'),false);
  assert.equal(run(`!!P.grammar[${JSON.stringify(u.id+'/'+group.id)}]`),false);
  assert.ok(run('gPlayerView()').includes('Жизни не тратятся'));
  for(let i=0;i<5;i++){
   run(`gResponse(G.steps[G.at]).value='wrong';gCheck();`);
   assert.ok(!run('G.recovery'));
   assert.ok(!run('gPlayerView()').includes('Осталась последняя попытка'));
   run('gMove(1);');
   assert.equal(run('G.steps[G.at].qi'),0);
   assert.equal(run('gResponse(G.steps[G.at]).checked'),false);
  }
  run(`gResponse(G.steps[G.at]).value=${JSON.stringify(group.questions[0].answers[0])};gCheck();gMove(1);`);
  if(run('G.steps[G.at].type')==='summary')run('gMove(1);');
  assert.equal(run('G.ended'),true);
  assert.equal(run(`P.grammar[${JSON.stringify(u.id+'/'+group.id)}].correct`),group.questions.length-1);
  assert.equal(run(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id===${JSON.stringify(group.id)})).errors`),1);
  assert.equal(run('P.xp'),2*(group.questions.length-1));
 }
});

test('correction queue and drafts survive reload and keep the next section locked',()=>{
 const storage=new Map();let run=context([unit],storage);unlockUntil(run,'exercise:1.1');
 run(`save();gStart(COURSE.grammar[0].id,'exercise:1.1');gMove(1);
 for(let i=0;i<10;i++){gResponse(G.steps[G.at]).value=i<2?'wrong':gUnit().exercises[0].questions[i].answers[0];gCheck();gMove(1);}
 gPick(0);gMove(1);gResponse(G.steps[G.at]).value='draft';gExit();`);
 run=context([unit],storage);unlockUntil(run,'exercise:1.1');
 run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('G.steps[G.at].correction'),true);
 assert.equal(run('gResponse(G.steps[G.at]).value'),'draft');
 assert.equal(run(`gRouteOpen(gUnit(),'exercise:1.2')`),false);
 run(`gResponse(G.steps[G.at]).value=gUnit().exercises[0].questions[G.steps[G.at].qi].answers[0];gCheck();gMove(1);`);
 // Complete whichever of the two mistakes remains after the earlier click.
 while(!run('G.ended'))run(`gResponse(G.steps[G.at]).value=gUnit().exercises[0].questions[G.steps[G.at].qi].answers[0];gCheck();gMove(1);`);
 assert.equal(run(`gRouteOpen(gUnit(),'exercise:1.2')`),true);
 assert.equal(run('P.grammar[gUnit().id+"/1.1"].correct'),8);
 assert.equal(run('P.xp'),16);
});

test('a whole-unit run corrects mistakes before moving to the next exercise',()=>{
 const run=context([unit]);unlockUntil(run,'exercise:1.1');
 run(`gStart(COURSE.grammar[0].id,'all');G.at=G.steps.findIndex(s=>s.type==='intro'&&s.group==='1.1');gMove(1);
 for(let i=0;i<10;i++){gResponse(G.steps[G.at]).value=i===9?'wrong':gUnit().exercises[0].questions[i].answers[0];gCheck();gMove(1);}`);
 assert.equal(run('G.steps[G.at].correction'),true);
 assert.equal(run('G.steps[G.at].group'),'1.1');
 assert.equal(run('G.steps[G.at].qi'),9);
 run(`gPick(gUnit().exercises[0].questions[9].options.findIndex(o=>grammarCorrect(gUnit().exercises[0].questions[9],o)));gMove(1);`);
 assert.equal(run('G.steps[G.at].type'),'intro');
 assert.equal(run('G.steps[G.at].group'),'1.2');
 assert.equal(run('P.grammar[gUnit().id+"/1.1"].correct'),9);
 assert.equal(run('G.ended'),false);
});

test('answer feedback can collapse and reopen without changing answers, hearts or progress',()=>{
 const storage=new Map();let run=context([unit],storage);
 run(`gStart(COURSE.grammar[0].id,'section:0');gMove(1);gPick(0);`);
 const errors=run('gAttempt(gUnit(),gUnit().sections[0].check).errors');
 const good=run('gResponse(G.steps[G.at]).good');
 run('gToggleFeedback();');
 assert.ok(run('gPlayerView()').includes('id="g-feedback-details" hidden'));
 assert.ok(run('gPlayerView()').includes('aria-expanded="false"'));
 assert.ok(run('gPlayerView()').includes('data-gnext'));
 run('gExit();');run=context([unit],storage);
 run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.ok(run('gPlayerView()').includes('id="g-feedback-details" hidden'));
 run('gToggleFeedback();');
 assert.ok(run('gPlayerView()').includes('aria-expanded="true"'));
 assert.equal(run('gResponse(G.steps[G.at]).good'),good);
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[0].check).errors'),errors);
 run('gMove(1);');
 assert.ok(!run('gPlayerView()').includes('g-feedback-details'));
});

test('grammar viewport follows the visible keyboard area and the keyboard can be dismissed',()=>{
 const run=context();
 run(`var classes={},viewportPlayer={style:{},classList:{toggle:(k,v)=>classes[k]=v}};
 document.querySelector=()=>viewportPlayer;
 window.visualViewport={height:340,offsetTop:25};
 document.activeElement={matches:()=>true,blur(){this.matches=()=>false;}};
 gSyncViewport();`);
 assert.equal(run('viewportPlayer.style.height'),'340px');
 assert.equal(run('viewportPlayer.style.top'),'25px');
 assert.equal(run('classes["is-short"]'),true);
 run('gHideKeyboard();');
 assert.equal(run('classes["is-typing"]'),false);
 run('window.visualViewport={height:800,offsetTop:0};gSyncViewport();');
 assert.equal(run('viewportPlayer.style.height'),'800px');
 assert.equal(run('viewportPlayer.style.top'),'0px');
});

test('all mini-checks allow every first answer to be wrong, then require corrections without hearts',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 for(const u of units)for(const [i,section] of u.sections.entries()){
  if(!section.check)continue;
  const run=context([u]);unlockUntil(run,'section:'+i);
  run(`gStart(COURSE.grammar[0].id,'section:${i}');gMove(1);`);
  for(let j=0;j<section.check.questions.length;j++){
   assert.ok(!run('gPlayerView()').includes('class="ghearts"'));
   run(`gResponse(G.steps[G.at]).value='wrong';gCheck();`);
   assert.ok(!run('G.recovery'));
   assert.ok(!run('gPlayerView()').includes('Осталась последняя попытка'));
   run('gMove(1);');
  }
  assert.equal(run('G.ended'),false);
  assert.equal(run('G.steps[G.at].correction'),true);
  run(`gResponse(G.steps[G.at]).value='wrong';gCheck();gMove(1);`);
  assert.equal(run('G.steps[G.at].qi'),0);
  run(`while(!G.ended){const s=G.steps[G.at];gResponse(s).value=gUnit().sections[${i}].check.questions[s.qi].answers[0];gCheck();gMove(1);}`);
  assert.equal(run(`gAttempt(gUnit(),gUnit().sections[${i}].check).errors`),section.check.questions.length);
  assert.equal(run(`P.grammar[grammarKey(gUnit(),gUnit().sections[${i}].check)].correct`),0);
 }
});

test('an old failed mini-check resumes straight into correction with all mistakes preserved',()=>{
 const storage=new Map();let run=context([unit3],storage);unlockUntil(run,'section:8');
 run(`gStart(COURSE.grammar[0].id,'section:8');gMove(1);
 for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='wrong';gCheck();if(i<2)gMove(1);}
 var old=gAttempt(gUnit(),gUnit().sections[8].check);old.limit=3;old.status='failed';
 gStoreAttempt(gUnit(),gUnit().sections[8].check,old);G.recovery='check-i';store.set(G_SESSION_KEY,JSON.stringify(G));`);
 run=context([unit3],storage);unlockUntil(run,'section:8');
 run(`gStart(COURSE.grammar[0].id,'all',true);gMove(1);`);
 assert.ok(!run('G.recovery'));
 assert.equal(run('G.steps[G.at].correction'),true);
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[8].check).errors'),3);
 assert.ok(!run('gPlayerView()').includes('class="ghearts"'));
});

test('every accepted alternative in mini-checks is offered and any one correct choice suffices',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 let checked=0;
 for(const u of units)for(const [si,section] of u.sections.entries()){
  if(!section.check)continue;
  for(const [qi,q] of section.check.questions.entries()){
   if(q.answers.length<2)continue;
   for(const answer of q.answers){
    const run=context([u]);unlockUntil(run,'section:'+si);
    run(`gStart(COURSE.grammar[0].id,'section:${si}');gMove(1);G.at=G.steps.findIndex(s=>s.group===${JSON.stringify(section.check.id)}&&s.qi===${qi});`);
    const index=q.options.indexOf(answer);assert.ok(index>=0,answer);
    assert.ok(run('gPlayerView()').includes(answer));
    run(`gPick(${index});`);
    assert.equal(run('gResponse(G.steps[G.at]).good'),true,answer);
    assert.equal(run(`gAttempt(gUnit(),gUnit().sections[${si}].check).errors`),0);
    assert.ok(run('gPlayerView()').includes('✓ Верно'));
    checked++;
   }
  }
 }
 assert.equal(checked,18);
});

test('grammar list gives each theme a distinct icon and marks only fully completed themes',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 const run=context(units);
 run('view.grammar=null;');
 const icons=run('COURSE.grammar.map(u=>G_UNIT_ICONS[u.id])');
 assert.ok(icons.every(Boolean));assert.equal(new Set(icons).size,41);
 assert.ok(!run('grammarView()').includes('gcompleted-badge'));
 // Completing the exercises alone leaves mini-checks and theory unfinished.
 run(`const doneUnit=COURSE.grammar[0];for(const g of doneUnit.exercises)P.grammar[grammarKey(doneUnit,g)]={correct:0,total:g.questions.length};`);
 assert.equal(run('gUnitComplete(COURSE.grammar[0])'),false);
 run(`for(const s of COURSE.grammar[0].sections)if(s.check)P.grammar[grammarKey(COURSE.grammar[0],s.check)]={correct:0,total:s.check.questions.length};`);
 assert.equal(run('gUnitComplete(COURSE.grammar[0])'),false,'summary still unread');
 run(`P.grammarRead[COURSE.grammar[0].id+'/summary']=true;`);
 assert.equal(run('gUnitComplete(COURSE.grammar[0])'),true);
 const html=run('grammarView()');
 assert.equal((html.match(/gcompleted-badge/g)||[]).length,1);
 assert.ok(html.includes('Пройдено тем: 1 из 41'));
 assert.match(html,/class="mcard gcomplete" data-grammar="001_el_hijo_la_hija"/);
 assert.match(html,/class="mcard " data-grammar="002_el_libro_la_mesa"/);
 run('delete P.grammarRead[COURSE.grammar[0].id+"/summary"];');
 assert.ok(!run('grammarView()').includes('gcompleted-badge'));
});

test('completed theme markers survive reload through the existing progress store',()=>{
 const storage=new Map();let run=context([unit],storage);
 run(`for(const g of gGroups(COURSE.grammar[0]))P.grammar[grammarKey(COURSE.grammar[0],g)]={correct:1,total:g.questions.length};P.grammarRead[COURSE.grammar[0].id+'/summary']=true;save();`);
 run=context([unit],storage);run('view.grammar=null;');
 assert.equal(run('gUnitComplete(COURSE.grammar[0])'),true);
 assert.ok(run('grammarView()').includes('gcompleted-badge'));
});

test('all 17 final exercises open the recap automatically, including after corrections and reload',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 for(const u of units)for(const makeError of [false,true]){
  const storage=new Map();let run=context([u],storage);
  const route=u.learningOrder.filter(r=>r.startsWith('exercise:')).at(-1);
  const group=u.exercises.find(g=>route==='exercise:'+g.id);
  unlockUntil(run,route);
  run(`save();gStart(COURSE.grammar[0].id,${JSON.stringify(route)});gMove(1);`);
  for(let qi=0;qi<group.questions.length;qi++){
   run(`gResponse(G.steps[G.at]).value=${JSON.stringify(makeError&&qi===0?'wrong':group.questions[qi].answers[0])};gCheck();gMove(1);`);
  }
  if(makeError){
   assert.equal(run('G.steps[G.at].correction'),true);
   run(`gResponse(G.steps[G.at]).value=${JSON.stringify(group.questions[0].answers[0])};gCheck();gMove(1);`);
  }
  assert.equal(run('G.steps[G.at].type'),'summary',u.id);
  assert.equal(run('G.ended'),false);
  assert.equal(run('gUnitComplete(gUnit())'),false);
  assert.ok(run('gPlayerView()').includes('Что запомнить'));
  assert.ok(!run('gPlayerView()').includes('Поздравляю!'));
  assert.equal(run('G.steps.filter(s=>s.type==="summary").length'),1);
  run('gExit();');run=context([u],storage);
  run(`gStart(COURSE.grammar[0].id,'all',true);`);
  assert.equal(run('G.steps[G.at].type'),'summary');
  run('gMove(1);');
  assert.equal(run('G.ended'),true);
  assert.equal(run('gUnitComplete(gUnit())'),true);
  assert.ok(run('gPlayerView()').includes('Поздравляю! Урок пройден!'));
 }
});

test('opening grammar from home always shows the list while preserving the saved lesson',()=>{
 const handlers={},storage=new Map(),run=context([unit],storage,handlers);
 run(`gStart(COURSE.grammar[0].id,'section:0');gMove(1);gPick(0);gExit();view.tab='home';render=()=>{};window.scrollTo=()=>{};`);
 const saved=storage.get('espanol-cada-dia.grammar-session.v1');
 assert.equal(run('view.grammar'),unit.id);
 const click=dataset=>handlers.click({target:{closest:s=>s==='button, .spoiler, [data-say], [data-line]'?{dataset,classList:{contains:()=>false}}:null,classList:{contains:()=>false}}});
 for(let i=0;i<3;i++){
  click({tab:'grammar'});
  assert.equal(run('view.grammar'),null);
  assert.equal(run('view.tab'),'grammar');
  assert.ok(run('grammarView()').includes(`data-grammar="${unit.id}"`));
  assert.ok(!run('grammarView()').includes('Все уроки грамматики'));
  assert.equal(storage.get('espanol-cada-dia.grammar-session.v1'),saved);
  click({grammar:unit.id});
  assert.equal(run('view.grammar'),unit.id);
  assert.ok(run('grammarView()').includes('Продолжить урок'));
  click({tab:'home'});
 }
});

test('theory, exercises and recap remain identifiable even before unlocking',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 for(const u of units){
  const run=context([u]);run(`view.grammar=${JSON.stringify(u.id)};`);
  const html=run('grammarView()');
  const cards=html.match(/<button class="mcard gstage-card[\s\S]*?<\/button>/g);
  assert.equal(cards.length,u.learningOrder.length);
  for(const [i,route] of u.learningOrder.entries()){
   const card=cards[i],theory=route.startsWith('section:'),practice=route.startsWith('exercise:');
   assert.ok(card.includes(`data-gstart="${route}"`));
   assert.ok(card.includes(`data-gkind="${theory?'theory':practice?'practice':'recap'}"`));
   assert.ok(card.includes(theory?'Теория':practice?'Упражнение':'Памятка'));
   assert.ok(card.includes(theory?'📖':practice?'✍️':'📌'));
   if(i>0){assert.ok(card.includes('disabled aria-disabled="true"'));assert.ok(card.includes('Сначала пройди предыдущий раздел'));}
  }
  run(`P.grammar[grammarKey(COURSE.grammar[0],COURSE.grammar[0].sections[0].check)]={correct:1,total:3};`);
  const first=run('grammarView()').match(/<button class="mcard gstage-card[\s\S]*?<\/button>/)[0];
  assert.ok(first.includes('gcomplete')&&first.includes('📖')&&first.includes('✓ Пройдено'));
 }
});

test('accent assessment forgives only missing acute accents and keeps meaning, ñ and ü strict',()=>{
 const run=context();
 for(const [answer,entered,status] of [
  ['tíos','tios','almost'],['tíos','ti\u0301os','correct'],['Tíos','TIOS','almost'],
  ['médica simpática','medica simpatica','almost'],['tíos','tíos','correct'],['tíos','tias','wrong'],
  ['tío','tió','wrong'],['tío','tíó','wrong'],['niña','nina','wrong'],['año','ano','wrong'],
  ['pingüino','pinguino','wrong'],['pingüino','pingu\u0308ino','correct'],['niña','nin\u0303a','correct'],['pingüino simpático','pingüino simpatico','almost'],
  ['sí','si','wrong'],['tú','tu','wrong'],['él','el','wrong'],['té','te','wrong'],['mí','mi','wrong'],
  ['sé','se','wrong'],['dé','de','wrong'],['más','mas','wrong'],['aún','aun','wrong'],
  ['¿Qué?','¿Que?','wrong'],['está','esta','wrong'],['tú tienes tíos','tú tienes tios','almost'],
  ['tú tienes tíos','tu tienes tios','wrong'],['el tío','él tio','wrong'],['tu tío','tu tio','almost'],
 ])assert.equal(run(`grammarResult({answers:[${JSON.stringify(answer)}]},${JSON.stringify(entered)}).status`),status,answer+'/'+entered);
 assert.equal(run(`grammarResult({answers:['tíos'],accentSensitive:true},'tios').status`),'wrong');
 assert.equal(run(`grammarResult({answers:['tíos']},'tios',{accentSensitive:true}).status`),'wrong');
 assert.equal(run(`grammarResult({prompt:'Поставь ударение',answers:['tíos']},'tios').status`),'wrong');
 assert.equal(run(`grammarResult({answers:['tíos'],options:['tíos','tios']},'tios').status`),'wrong');
 assert.equal(run(`grammarResult({answers:['sí','si']},'si').status`),'correct');
 const hint=run(`grammarAccentHint(grammarResult({answers:['Médica simpática']},'medica simpatica'))`);
 assert.equal((hint.match(/class="gmissing-accent"/g)||[]).length,2);
 assert.ok(hint.includes('M') && hint.includes('é, á'));
 assert.equal(unit3.sections[6].check.accentSensitive,true);
});

test('yellow answers survive reload, cost no lives and do not enter the correction queue',()=>{
 const u=structuredClone(unit3),storage=new Map();
 u.exercises[0].questions=[{prompt:'1',answers:['casas'],explain:'casas'}, {prompt:'2',answers:['libros'],explain:'libros'}, {prompt:'Дядя и тётя',answers:['tíos'],explain:'Дядя и тётя — tíos.'}];
 let run=context([u],storage);unlockUntil(run,'exercise:3.1');
 run(`save();var sounds=[];sfx=s=>sounds.push(s);gStart(COURSE.grammar[0].id,'exercise:3.1');gMove(1);
 for(let i=0;i<2;i++){gResponse(G.steps[G.at]).value='wrong';gCheck();gMove(1);}
 gResponse(G.steps[G.at]).value='tios';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('sounds.at(-1)'),'almost');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),2);
 assert.ok(!run('G.recovery'));
 let html=run('gPlayerView()');assert.ok(html.includes('pfoot almost')&&html.includes('Почти правильно!')&&html.includes('gmissing-accent'));
 assert.ok(!html.includes('Осталась последняя попытка'));
 run('gExit();');run=context([u],storage);unlockUntil(run,'exercise:3.1');run(`gStart(COURSE.grammar[0].id,'all',true);gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gResponse(G.steps[G.at]).value'),'tios');
 assert.equal(run('gUnit().exercises[0].questions[2].answers[0]'),'tíos');
 run(`gMove(1);`);
 assert.deepEqual(JSON.parse(run('JSON.stringify(G.steps.filter(s=>s.correction).map(s=>s.qi))')),[0,1]);
 run(`while(!G.ended){const s=G.steps[G.at];gResponse(s).value=gUnit().exercises[0].questions[s.qi].answers[0];gCheck();gMove(1);}`);
 assert.equal(run('P.grammar[gUnit().id+"/3.1"].correct'),1);
 assert.equal(run('P.xp'),2);
});

test('yellow feedback also completes a correction without changing first-answer score',()=>{
 const u=structuredClone(unit3);u.exercises[0].questions=[{prompt:'Родственники',answers:['tíos'],explain:'tíos'}];
 const run=context([u]);unlockUntil(run,'exercise:3.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:3.1');gMove(1);gResponse(G.steps[G.at]).value='wrong';gCheck();gMove(1);gResponse(G.steps[G.at]).value='tios';gCheck();gMove(1);`);
 assert.equal(run('G.ended'),true);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),1);
 assert.equal(run('P.grammar[gUnit().id+"/3.1"].correct'),0);
});

test('all manual screens include the six Spanish keys, with ü when needed',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 let fields=0;
 for(const u of units){
  const run=context([u]);
  for(const group of u.exercises){
   unlockUntil(run,'exercise:'+group.id);run(`gStart(COURSE.grammar[0].id,${JSON.stringify('exercise:'+group.id)});`);
   for(const [qi,q] of group.questions.entries()){
    if(q.options)continue;
    run(`G.at=G.steps.findIndex(s=>s.type==='question'&&s.qi===${qi});gResponse(G.steps[G.at]).value='draft';`);
    const html=run('gPlayerView()'),count=q.gapParts?q.gapParts.length-1:1;
    // A shared panel below a split sentence targets whichever gap has focus.
    for(const c of ['á','é','í','ó','ú','ñ'])assert.equal((html.match(new RegExp('data-gchar="'+c+'"','g'))||[]).length,1,u.id+'/'+group.id+'/'+qi);
    assert.ok(html.includes('type="button"'));fields+=count;
   }
  }
 }
 assert.ok(fields>200);
 assert.ok(runChars({answers:['pingüino']}).includes('ü'));
 function runChars(q){return context()(`gInputChars(${JSON.stringify(q)})`);}
 assert.equal(runChars({answers:['tíos']}).join(''),'áéíóúñ');
});

test('almost-correct sound is unique, soft, and respects mute',()=>{
 const run=context();
 run(`var tones=[],volumes=[];window.AudioContext=class {constructor(){this.currentTime=0;this.state='running';this.destination={};}createOscillator(){return {type:'',frequency:{set value(v){tones.push(v)}},connect:g=>g,start(){},stop(){}};}createGain(){return {gain:{setValueAtTime(){},exponentialRampToValueAtTime(v){volumes.push(v)}},connect:()=>{}};}};P.sound=true;sfx(true);var correct=tones.splice(0);sfx(false);var wrong=tones.splice(0);volumes=[];sfx('almost');`);
 const almost=run('tones.join()');assert.notEqual(almost,run('correct.join()'));assert.notEqual(almost,run('wrong.join()'));
 assert.ok(run('Math.max(...volumes)')<=.10);
 run(`P.sound=false;sfx('almost');`);assert.equal(run('tones.join()'),almost);
});

test('all 17 units derive persistent theory and practice context from their actual structure',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 for(const u of units){
  const run=context([u]);
  for(const [i,s] of u.sections.entries()){
   const step={type:'theory',section:i},info=run(`gBlockInfo(COURSE.grammar[0],${JSON.stringify(step)})`);
   assert.equal(info.title,s.title);
   assert.equal(info.meta,`Юнит ${u.number} · Теория ${u.number}.${i+1}`);
   assert.equal(info.progress,`1 из ${1+(s.check?.questions.length||0)}`);
   unlockUntil(run,'section:'+i);run(`gStart(COURSE.grammar[0].id,'section:${i}');`);
   const html=run('gPlayerView()');assert.ok(html.includes('gcontext-title'));assert.ok(html.indexOf('gcontext')<html.indexOf('class="pbody"'));
   if(s.check){
    const checkInfo=run(`gBlockInfo(COURSE.grammar[0],{type:'question',group:${JSON.stringify(s.check.id)},qi:0})`);
    assert.equal(checkInfo.title,s.title);assert.equal(checkInfo.progress,`2 из ${s.check.questions.length+1}`);
   }
  }
  for(const g of u.exercises){
   const info=run(`gBlockInfo(COURSE.grammar[0],{type:'question',group:${JSON.stringify(g.id)},qi:1})`);
   assert.equal(info.meta,`Юнит ${u.number} · Упражнение ${g.id}`);
   assert.ok(g.title.includes(info.title));assert.equal(info.progress,`2 из ${g.questions.length}`);
  }
 }
});

test('article theory presents one four-form table without repeated caption or word cards',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 const run=context([u]),s=u.sections[0];
 const html=run(`gTheory(${JSON.stringify(s)})`);
 assert.equal((html.match(/<table>/g)||[]).length,1);
 assert.ok(html.indexOf('<table>')<html.indexOf('<figure'));
 for(const text of ['un libro','una mesa','unos libros','unas mesas'])assert.equal(html.split(text).length-1,1,text);
 assert.ok(!html.includes('gword-group') && !html.includes('gformulas'));
 assert.ok(html.includes('gscene-image-only') && html.includes('Увеличить иллюстрацию'));
 assert.ok(!html.includes('<figcaption>'));
 const expanded=run(`gArtExamples(${JSON.stringify(s.illustration)})`);
 assert.ok(expanded.includes('un</strong> libro'));
});

test('theory dialogues keep consecutive speakers and translations together with safe markup',()=>{
 const run=context();
 const html=run(`gTheoryDialogues([{title:'Вопрос <img>',lines:[['¿Colombia es una ciudad?','Колумбия — город?'],['No, es un país.','Нет, это страна.']]}])`);
 assert.equal((html.match(/class="gdialogue-turn"/g)||[]).length,2);
 assert.ok(html.indexOf('¿Colombia')<html.indexOf('No, es un país.'));
 assert.ok(html.includes('Говорящий 1')&&html.includes('Говорящий 2'));
 assert.ok(html.includes('Колумбия — город?')&&html.includes('Нет, это страна.'));
 assert.ok(!html.includes('<img>'));
 const art={captionDialogue:true,examples:[['¿Qué gafas quieres?','Какие очки хочешь?'],['Las de la derecha.','Те, что справа.']]};
 const caption=run(`gArtExamples(${JSON.stringify(art)})`);
 assert.equal((caption.match(/class="gdialogue-turn"/g)||[]).length,2);
 assert.ok(!caption.includes('gscene-line'));
});

test('documented rare answers are yellow for both typed input and choice, with green recommendations',()=>{
 const u4=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 const run=context([u4]);
 for(const [gid,qi,word] of [['4.1',11,'aula'],['4.3',2,'hacha'],['4.4',3,'águila']]) {
  run(`var q=COURSE.grammar[0].exercises.find(g=>g.id===${JSON.stringify(gid)}).questions[${qi}];`);
  for(const manual of [true,false]) {
   assert.equal(run(`grammarResult(q,' UN ',{},${manual}).status`),'correct');
   assert.equal(run(`grammarResult(q,' UNA ',{},${manual}).status`),'almost');
   assert.equal(run(`grammarResult(q,'una',{},${manual}).good`),true);
   for(const wrong of ['unos','unas'])assert.equal(run(`grammarResult(q,${JSON.stringify(wrong)},{},${manual}).status`),'wrong');
  }
  assert.equal(run(`grammarFeedbackTitle(grammarResult(q,'una'))`),`Допустимо, но лучше сказать un ${word}.`);
  assert.ok(run(`grammarFeedbackExplanation(q,grammarResult(q,'una'))`).includes('женского рода'));
  assert.equal(run(`grammarAccentHint(grammarResult(q,'una'))`),'');
 }
 assert.equal(run(`grammarResult(COURSE.grammar[0].sections[2].check.questions[1],'una').status`),'correct');
 const r1=context();
 assert.equal(r1(`grammarResult(COURSE.grammar[0].exercises[0].questions[6],'la pilota').status`),'almost');
 assert.equal(r1(`grammarResult(COURSE.grammar[0].exercises[0].questions[6],'la piloto').status`),'correct');
 assert.equal(r1(`grammarResult(COURSE.grammar[0].exercises[1].questions[1],'jefe').status`),'almost');
 assert.equal(r1(`grammarResult(COURSE.grammar[0].exercises[1].questions[1],'jefa').status`),'correct');
 assert.equal(r1(`grammarResult(COURSE.grammar[0].exercises[1].questions[12],'dependiente').status`),'correct');
});

test('warning feedback stays distinct from omitted accents and safely combines the two reasons',()=>{
 const run=context();
 run(`var q={answers:['un águila','una águila'],answerWarnings:{'una águila':{preferred:'un águila',message:'Допустимо: <un águila>',explanation:'Пояснение'}}};`);
 assert.equal(run(`grammarResult(q,'una aguila').good`),true);
 assert.equal(run(`grammarResult(q,'una aguila').warning.preferred`),'un águila');
 assert.ok(run(`grammarAccentHint(grammarResult(q,'una aguila'))`).includes('gmissing-accent'));
 assert.equal(run(`grammarResult(q,'un aguila').warning`),undefined);
 assert.equal(run(`grammarFeedbackTitle(grammarResult(q,'un aguila'))`),'Почти правильно!');
 assert.equal(run(`grammarResult(q,'una aguila',{accentSensitive:true}).status`),'wrong');
 assert.equal(run(`grammarResult(q,'una águila',{accentSensitive:true}).status`),'almost');
 assert.equal(run(`grammarResult(q,'una águila').reason`),'variant');
 assert.equal(run(`grammarAccentHint(grammarResult(q,'una águila'))`),'');
});

test('choice feedback distinguishes green and yellow buttons and gives a reason-specific explanation',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 const q=u.exercises.find(g=>g.id==='4.3').questions[2];
 u.exercises.find(g=>g.id==='4.3').questions=[q];
 const run=context([u]);unlockUntil(run,'exercise:4.3');
 run(`var sounds=[];sfx=s=>sounds.push(s);gStart(COURSE.grammar[0].id,'exercise:4.3');gMove(1);`);
 assert.ok(!run('gPlayerView()').includes('goption-status'));
 run('gPick(1);gPick(0);');
 assert.equal(run('sounds.join()'),'almost');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==="4.3")).errors'),0);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().exercises.find(g=>g.id==="4.3"))].correct'),1);
 assert.equal(run('P.xp'),2);
 const html=run('gPlayerView()');
 assert.equal((html.match(/class="opt right"/g)||[]).length,1);
 assert.equal((html.match(/class="opt almost"/g)||[]).length,1);
 assert.ok(html.includes('pfoot almost')&&html.includes('Допустимо, но лучше сказать un hacha.'));
 assert.ok(html.includes('Рекомендуется')&&html.includes('Допустимо'));
 assert.ok(!html.includes('Почти правильно!')&&!html.includes('gmissing-accent'));
 assert.ok(html.includes('data-gnext'));
 const form=run(`grammarForm(gUnit(),gUnit().exercises.find(g=>g.id==='4.3'))`);
 assert.ok(form.includes('gchoice almost')&&form.includes('gchoice right')&&form.includes('gfeedback almost'));
 run('gMove(1);');assert.equal(run('G.steps.some(s=>s.correction)'),false);
});

test('rare variants retain the last life, survive reload, and never enter the error queue',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 const g=u.exercises.find(g=>g.id==='4.3');
 g.questions=[{prompt:'1',answers:['libros'],explain:'libros'},{prompt:'2',answers:['casas'],explain:'casas'},g.questions[2]];
 const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:4.3');
 run(`save();gStart(COURSE.grammar[0].id,'exercise:4.3');gMove(1);
 for(let i=0;i<2;i++){gResponse(G.steps[G.at]).value='wrong';gCheck();gMove(1);}gPick(1);gExit();`);
 run=context([u],storage);unlockUntil(run,'exercise:4.3');run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==="4.3")).errors'),2);
 assert.ok(!run('G.recovery'));
 run('gMove(1);');
 assert.equal(run('G.steps.filter(s=>s.correction).length'),2);
 assert.ok(run('G.steps.filter(s=>s.correction).every(s=>s.qi!==2)'));
});

test('yellow correction is accepted without another retry or error and keeps the original score',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 const g=u.exercises.find(g=>g.id==='4.3');g.questions=[g.questions[2]];
 const run=context([u]);unlockUntil(run,'exercise:4.3');
 run(`gStart(COURSE.grammar[0].id,'exercise:4.3');gMove(1);gPick(2);`);
 const wrong=run('gPlayerView()');assert.ok(wrong.includes('pfoot bad'));
 assert.equal((wrong.match(/class="opt wrong"/g)||[]).length,1);
 assert.equal((wrong.match(/class="opt right"/g)||[]).length,1);
 assert.equal((wrong.match(/class="opt almost"/g)||[]).length,1);
 run('gMove(1);gPick(1);');
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==="4.3")).status'),'passed');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==="4.3")).errors'),1);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().exercises.find(g=>g.id==="4.3"))].correct'),0);
 assert.equal(run('P.xp'),0);
 run('gMove(1);');assert.equal(run('G.ended'),true);
});

test('previously green accepted responses adopt current guidance without changing progress',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 const g=u.exercises.find(g=>g.id==='4.3');g.questions=[g.questions[2]];
 const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:4.3');
 run(`save();gStart(COURSE.grammar[0].id,'exercise:4.3');gMove(1);gPick(1);
 var records=gAttempts();records[grammarKey(gUnit(),gUnit().exercises.find(g=>g.id==='4.3'))].responses[0]={value:'una',checked:true,good:true,status:'correct'};store.set(G_ATTEMPTS_KEY,JSON.stringify(records));gExit();`);
 run=context([u],storage);unlockUntil(run,'exercise:4.3');run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==="4.3")).errors'),0);
 assert.equal(run('P.xp'),2);
 assert.ok(run('gPlayerView()').includes('Допустимо, но лучше сказать un hacha.'));
});

test('multi-answer audit keeps regional, contextual and equally valid choices green unless explicitly annotated',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>f.endsWith('.json')).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 const run=context(units);let questions=0,alternatives=0,warnings=0;
 for(const [ui,u] of units.entries()) {
  const groups=[...u.sections.filter(s=>s.check).map(s=>s.check),...u.exercises];
  for(const [gi,g] of groups.entries())for(const [qi,q] of g.questions.entries()){
   questions++;if(q.answers.length>1)alternatives++;
   run(`var q=gGroups(COURSE.grammar[${ui}])[${gi}].questions[${qi}];`);
   for(const a of q.answers){
    const status=q.answerWarnings?.[a]?'almost':'correct';if(status==='almost')warnings++;
    assert.equal(run(`grammarResult(q,${JSON.stringify(a)}).status`),status,`${u.number}/${g.id}/${qi}/${a}`);
   }
  }
 }
 assert.equal(questions,1861);assert.equal(alternatives,270);assert.equal(warnings,25);
});

test('yellow mini-check choices still have no lives and complete normally',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 u.sections[0].check.questions=[u.exercises.find(g=>g.id==='4.3').questions[2]];
 const run=context([u]);run(`gStart(COURSE.grammar[0].id,'section:0');gMove(1);gPick(1);`);
 const html=run('gPlayerView()');assert.ok(html.includes('pfoot almost'));
 assert.ok(!html.includes('class="ghearts"'));
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[0].check).errors'),0);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().sections[0].check)].correct'),1);
 run('gMove(1);');assert.equal(run('G.ended'),true);
 assert.equal(run('G.steps.some(s=>s.correction)'),false);
});

test('all 17 completion screens derive the next lesson from course order and preserve results',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>f.endsWith('.json')).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 for(const [i,u] of units.entries()) {
  const handlers={},run=context(units,new Map(),handlers);
  run(`render=()=>{};window.scrollTo=()=>{};var u=COURSE.grammar[${i}];
    for(const r of gRoutes(u)){const g=r.startsWith('section:')?u.sections[+r.split(':')[1]].check:u.exercises.find(g=>r==='exercise:'+g.id);if(g)P.grammar[grammarKey(u,g)]={correct:Math.max(0,g.questions.length-1),total:g.questions.length};else P.grammarRead[u.id+'/'+r]=true;}
    P.xp=78;gStart(u.id,'summary');G.ended=true;`);
  const before=run('JSON.stringify(P)'),html=run('gPlayerView()'),next=units[i+1];
  const correct=u.exercises.reduce((n,g)=>n+Math.max(0,g.questions.length-1),0),total=u.exercises.reduce((n,g)=>n+g.questions.length,0);
  assert.ok(html.includes(`Лучший результат: ${correct} из ${total}`));
  assert.ok(html.includes('data-gmain')&&html.includes('data-gexit')&&html.includes('data-grammar-list'));
  if(next){
   assert.ok(html.includes(`Далее · Урок ${next.number}`));
   assert.ok(html.includes(`<h3>${next.title.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}</h3>`));
   assert.ok(html.includes(run(`esc(COURSE.grammar[${i+1}].subtitle)`)));
   assert.ok(html.indexOf('class="gnext-lesson"')<html.indexOf('data-gnext-unit'));
   assert.ok(html.includes('>Начать следующий урок</button>'));
   handlers.click({target:{closest:s=>s==='button, .spoiler, [data-say], [data-line]'?{dataset:{gnextUnit:next.id}}:null,classList:{contains:()=>false}}});
   assert.equal(run('G.unit'),next.id);assert.equal(run('G.at'),0);assert.equal(run('G.ended'),false);
  }else{
   assert.ok(html.includes('Все уроки раздела пройдены!'));assert.ok(!html.includes('data-gnext-unit'));
   handlers.click({target:{closest:s=>s==='button, .spoiler, [data-say], [data-line]'?{dataset:{grammarList:''}}:null,classList:{contains:()=>false}}});
   assert.equal(run('G'),null);assert.equal(run('view.grammar'),null);assert.equal(run('view.tab'),'grammar');
   assert.equal((run('grammarView()').match(/data-grammar="/g)||[]).length,41);
  }
  assert.equal(run('JSON.stringify(P)'),before);
 }
});

test('completed next lessons remain repeatable and inaccessible lessons have a title without a dead button',()=>{
 const run=context([unit,unit2]);
 run(`render=()=>{};gStart(COURSE.grammar[0].id,'all');
   var complete=u=>{for(const r of gRoutes(u)){const g=r.startsWith('section:')?u.sections[+r.split(':')[1]].check:u.exercises.find(g=>r==='exercise:'+g.id);if(g)P.grammar[grammarKey(u,g)]={correct:g.questions.length,total:g.questions.length};else P.grammarRead[u.id+'/'+r]=true;}};
   complete(COURSE.grammar[0]);G.ended=true;var openRoute=gRouteOpen;gRouteOpen=(u,r)=>u.id!==COURSE.grammar[1].id&&openRoute(u,r);`);
 let html=run('gPlayerView()');
 assert.ok(html.includes('Далее · Урок 2')&&html.includes('El libro, la mesa')&&html.includes('Следующий урок пока недоступен'));
 assert.ok(!html.includes('data-gnext-unit'));
 const before=run('JSON.stringify(G)');run(`gStartNextUnit(COURSE.grammar[1].id);gStart(COURSE.grammar[1].id,'all');`);
 assert.equal(run('JSON.stringify(G)'),before);
 run('complete(COURSE.grammar[1]);');const progress=run('JSON.stringify(P)');
 html=run('gPlayerView()');
 assert.ok(html.includes('Уже пройден · можно повторить')&&html.includes('data-gnext-unit'));
 run(`gStartNextUnit(COURSE.grammar[1].id)`);
 assert.equal(run('G.unit'),unit2.id);assert.equal(run('G.at'),0);
 assert.equal(run('JSON.stringify(P)'),progress);
});

test('next lesson uses actual metadata and order, escapes titles, and ignores stale destinations',()=>{
 const next={...structuredClone(unit2),id:'next-custom',number:42,title:'Полная тема <A> & B',subtitle:'Описание «длинной темы»'};
 const run=context([unit,next,unit3]);run(`render=()=>{};gStart(COURSE.grammar[0].id,'all');`);
 const html=run('gFinalView(gUnit(),[],0)');
 assert.ok(html.includes('Далее · Урок 42')&&html.includes('Полная тема &lt;A&gt; &amp; B'));
 assert.ok(html.includes('Описание «длинной темы»'));
 assert.equal(run('gNextUnit({id:"missing"})'),undefined);
 run(`gStartNextUnit(COURSE.grammar[2].id);`);assert.equal(run('G.unit'),unit.id);
});

test('revised profession practice never reuses answers from the old all-omission exercise',()=>{
 const updated=JSON.parse(fs.readFileSync('content/grammar/005_sin_articulo.json','utf8'));
 const legacy=structuredClone(updated);delete legacy.revision;
 legacy.learningOrder=['section:0','exercise:5.1','section:1','exercise:5.2','section:2','exercise:5.3','summary'];
 delete legacy.exercises[0].revision;
 for(const q of legacy.exercises[0].questions)q.answers=['Без артикля'];
 const storage=new Map();let run=context([legacy],storage);unlockUntil(run,'exercise:5.1');
 run(`render=()=>{};save();P.xp=52;P.grammar['other-unit/practice']={correct:4,total:4};
   var u=COURSE.grammar[0],g=u.exercises[0];P.grammar[grammarKey(u,g)]={correct:8,total:8};save();
   gStoreAttempt(u,u.exercises[1],gNewAttempt(u.exercises[1],{0:{value:'wrong',checked:true,good:false}}));
   gStart(u.id,'exercise:5.1');gMove(1);
   for(let i=0;i<2;i++){gResponse(G.steps[G.at]).value='Без артикля';gCheck();gMove(1);}
   gResponse(G.steps[G.at]).value='un';gCheck();gExit();
   var records=gAttempts();delete records[grammarKey(u,g)].revision;store.set(G_ATTEMPTS_KEY,JSON.stringify(records));
   var session=gSaved();delete session.unitRevision;delete session.groupRevisions;store.set(G_SESSION_KEY,JSON.stringify(session));`);
 const previous=run('JSON.stringify(P)'),otherAttempt=run('JSON.stringify(gAttempt(COURSE.grammar[0],COURSE.grammar[0].exercises[1]))');
 run=context([updated],storage);run(`render=()=>{};gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('JSON.stringify(P)'),previous);
 assert.equal(run('G.steps[G.at].type'),'theory');assert.equal(run('G.steps[G.at].section'),1);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).revision'),2);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),0);
 assert.equal(run('Object.keys(gAttempt(gUnit(),gUnit().exercises[0]).responses).length'),0);
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().exercises[1]))'),otherAttempt);
 run(`P.grammar[grammarKey(gUnit(),gUnit().sections[1].check)]={correct:2,total:2};gStart(gUnit().id,'exercise:5.1');gMove(1);`);
 assert.equal(run('gResponse(G.steps[G.at]).checked'),false);
 assert.equal(run('P.xp'),52);
});

test('an updated exercise discards obsolete correction steps while the same revision retains errors',()=>{
 const updated=JSON.parse(fs.readFileSync('content/grammar/009_tiempo_fecha.json','utf8'));
 const legacy=structuredClone(updated);delete legacy.exercises[0].revision;
 const storage=new Map();let run=context([legacy],storage);unlockUntil(run,'exercise:9.1');
 run(`render=()=>{};save();gStart(COURSE.grammar[0].id,'exercise:9.1');gMove(1);
   while(!G.steps[G.at].correction){const s=G.steps[G.at],q=gUnit().exercises[0].questions[s.qi];gResponse(s).value=s.qi===0?'wrong':q.answers[0];gCheck();gMove(1);}gExit();`);
 run=context([updated],storage);run(`render=()=>{};gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('G.steps[G.at].type'),'intro');
 assert.equal(run('G.steps.some(s=>s.correction)'),false);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),0);
 run(`gMove(1);for(let i=0;i<2;i++){gResponse(G.steps[G.at]).value='wrong';gCheck();gMove(1);}gExit();`);
 run=context([updated],storage);run(`render=()=>{};gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),2);
 run(`gResponse(G.steps[G.at]).value='wrong';gCheck();`);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).status'),'failed');
 assert.equal(run('G.recovery'),'9.1');
});

test('all eight new profession questions pass with their contextual answers and cannot be passed by omission',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/005_sin_articulo.json','utf8'));
 let run=context([u]);unlockUntil(run,'exercise:5.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:5.1');gMove(1);while(!G.ended){const s=G.steps[G.at];gResponse(s).value=gUnit().exercises[0].questions[s.qi].answers[0];gCheck();gMove(1);}`);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().exercises[0])].correct'),8);
 assert.equal(run('P.xp'),16);
 run=context([u]);unlockUntil(run,'exercise:5.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:5.1');gMove(1);while(!G.ended&&!G.recovery){gResponse(G.steps[G.at]).value='Без артикля';gCheck();if(!G.recovery)gMove(1);}`);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).status'),'failed');
 assert.equal(run('P.xp'),0);
});

test('migrating several revised exercises returns the current exercise to its beginning only once',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/008_nombres_propios.json','utf8'));
 const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:8.1');
 run(`render=()=>{};save();gStart(COURSE.grammar[0].id,'exercise:8.1');G.at=4;
   var records=gAttempts();for(const g of gUnit().exercises.slice(0,2)){records[grammarKey(gUnit(),g)]={...gNewAttempt(g),revision:1,responses:{0:{value:'Без артикля',checked:true,good:true}}};}
   store.set(G_ATTEMPTS_KEY,JSON.stringify(records));store.set(G_SESSION_KEY,JSON.stringify(G));G=null;`);
 run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true)`);
 assert.equal(run('G.steps[G.at].type'),'intro');assert.equal(run('G.steps[G.at].group'),'8.1');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).revision'),2);
 assert.equal(run('Object.keys(gAttempt(gUnit(),gUnit().exercises[1]).responses).length'),0);
});

test('an old failed profession attempt reopens the newly required theory instead of a locked exercise',()=>{
 const updated=JSON.parse(fs.readFileSync('content/grammar/005_sin_articulo.json','utf8'));
 const legacy=structuredClone(updated);delete legacy.revision;delete legacy.exercises[0].revision;
 legacy.learningOrder=['section:0','exercise:5.1','section:1','exercise:5.2','section:2','exercise:5.3','summary'];
 const storage=new Map();let run=context([legacy],storage);unlockUntil(run,'exercise:5.1');
 run(`render=()=>{};save();gStart(COURSE.grammar[0].id,'exercise:5.1');gMove(1);
   for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='wrong';gCheck();if(!G.recovery)gMove(1);}gExit();`);
 run=context([updated],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.ok(!run('G.recovery'));
 assert.equal(run('G.steps[G.at].type'),'theory');assert.equal(run('G.steps[G.at].section'),1);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),0);
 run(`gMove(1)`);assert.equal(run('G.steps[G.at].type'),'question');
});

test('all grammar choice sets receive valid, balanced attempt orders without changing course data',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>f.endsWith('.json')).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 const run=context(units);
 run(`function seeded(seed){let n=seed>>>0;return ()=>((n=(1664525*n+1013904223)>>>0)/4294967296);}`);
 const before=run('JSON.stringify(COURSE.grammar)');let standard=0,guided=0;
 for(const [ui,u] of units.entries()){
  const groups=[...u.sections.filter(s=>s.check).map(s=>s.check),...u.exercises];
  for(const [gi,g] of groups.entries()){
   standard+=g.questions.filter(q=>q.options).length;guided+=g.questions.filter(q=>q.guidedGaps).length;
   const result=JSON.parse(run(`JSON.stringify((()=>{const g=gGroups(COURSE.grammar[${ui}])[${gi}];for(let seed=1;seed<=12;seed++){const orders=gPlanChoiceOrders(g,seeded(seed*7919));const issues=gChoiceOrderIssues(g,orders);if(issues.length)return {seed,issues};for(const s of gChoiceSpecs(g))if(!gChoicePermutation(orders[s.key],s.values))return {bad:s.key};}return {};})())`));
   assert.deepEqual(result,{},`${u.number}/${g.id}: ${JSON.stringify(result)}`);
  }
 }
 assert.equal(standard,694);assert.equal(guided,9);
 assert.equal(run('JSON.stringify(COURSE.grammar)'),before);
});

test('distribution control detects skew, runs and cycles, while short checks have no exact position quota',()=>{
 const run=context();
 run(`var group={questions:Array.from({length:24},()=>({answers:['d'],options:['a','b','c','d']}))};
 var source=Object.fromEntries(group.questions.map((q,i)=>[i,q.options]));`);
 assert.ok(run('gChoiceOrderIssues(group,source).some(x=>x.kind==="imbalance")'));
 assert.ok(run('gChoiceOrderIssues(group,source).some(x=>x.kind==="run")'));
 run(`var cycle=Object.fromEntries(group.questions.map((q,i)=>{const a=q.options.filter(v=>v!=='d');a.splice(i%4,0,'d');return [i,a]}));`);
 assert.ok(run('gChoiceOrderIssues(group,cycle).some(x=>x.kind==="cycle")'));
 assert.deepEqual(JSON.parse(run('JSON.stringify(gChoiceOrderIssues(group,gPlanChoiceOrders(group)))')),[]);
 run(`var short={questions:[{answers:['yes'],options:['yes','no']},{answers:['yes'],options:['yes','no']}]};var patterns=new Set();for(let i=0;i<100;i++){const o=gPlanChoiceOrders(short);patterns.add([o[0].indexOf('yes'),o[1].indexOf('yes')].join());}`);
 assert.equal(run('patterns.size'),4);
});

test('attempt order is unchanged by checking, back, reload and correction; completed repeats use a fresh attempt',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/004_articulo_indefinido.json','utf8'));
 u.exercises[0].questions=Array.from({length:8},()=>({prompt:'___',answers:['a'],options:['a','b','c','d'],explain:'a'}));
 const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:4.1');
 run(`save();gStart(COURSE.grammar[0].id,'exercise:4.1');gMove(1);`);
 const orders=run('JSON.stringify(gAttempt(gUnit(),gUnit().exercises[0]).optionOrders)'),attemptId=run('gAttempt(gUnit(),gUnit().exercises[0]).id');
 run(`gPickValue('b');gMove(1);gMove(-1);gExit();`);
 run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).id'),attemptId);
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().exercises[0]).optionOrders)'),orders);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),1);
 run(`gMove(1);while(!G.ended){gPickValue('a');gMove(1);}`);
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().exercises[0]).optionOrders)'),orders);
 assert.equal(run('P.grammar[grammarKey(gUnit(),gUnit().exercises[0])].correct'),7);
 run(`gStart(gUnit().id,'exercise:4.1');gMove(1);`);
 assert.notEqual(run('gAttempt(gUnit(),gUnit().exercises[0]).id'),attemptId);
 assert.equal(run('gResponse(G.steps[G.at]).checked'),false);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),0);
 assert.equal(run('gChoiceOrderIssues(gUnit().exercises[0],gAttempt(gUnit(),gUnit().exercises[0]).optionOrders).length'),0);
});

test('choice events and numeric keys follow displayed values rather than source positions',()=>{
 const handlers={},run=context([unit],new Map(),handlers);
 run(`gStart(COURSE.grammar[0].id,'section:0');gMove(1);
 var group=gUnit().sections[0].check,q=group.questions[0],record=gAttempt(gUnit(),group);
 record.optionOrders[0]=q.options.slice().reverse();gStoreAttempt(gUnit(),group,record);`);
 const displayed=JSON.parse(run('JSON.stringify(gOrderedChoices(group,0,null,gAttempt(gUnit(),group)))'));
 let html=run('gPlayerView()');
 const values=[...html.matchAll(/data-gvalue="([^"]*)"/g)].map(m=>m[1]);assert.deepEqual(values,displayed);
 run(`document.querySelector=selector=>selector==='[data-gposition="0"]'?{disabled:false,click:()=>gPickValue(${JSON.stringify(displayed[0])})}:null;`);
 handlers.keydown({key:'1',target:{tagName:'DIV',dataset:{},closest:()=>null}});
 assert.equal(run('gResponse(G.steps[G.at]).value'),displayed[0]);
 assert.equal(run('gResponse(G.steps[G.at]).good'),run(`grammarCorrect(q,${JSON.stringify(displayed[0])})`));
 const handlers2={},r2=context([unit],new Map(),handlers2);
 r2(`gStart(COURSE.grammar[0].id,'section:0');gMove(1)`);
 handlers2.click({target:{closest:s=>s==='button, .spoiler, [data-say], [data-line]'?{dataset:{gvalue:'la',gpick:'0'}}:null,classList:{contains:()=>false}}});
 assert.equal(r2('gResponse(G.steps[G.at]).value'),'la');assert.equal(r2('gResponse(G.steps[G.at]).good'),true);
});

test('legacy and damaged order records preserve answered values, lives and valid existing orders',()=>{
 const storage=new Map();let run=context([unit],storage);run(`save();gStart(COURSE.grammar[0].id,'section:0');gMove(1);gPickValue('el');gExit();
 var records=gAttempts(),key=grammarKey(COURSE.grammar[0],COURSE.grammar[0].sections[0].check);delete records[key].optionOrders;store.set(G_ATTEMPTS_KEY,JSON.stringify(records));`);
 run=context([unit],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('gResponse(G.steps[G.at]).value'),'el');
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[0].check).errors'),1);
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().sections[0].check).optionOrders[0])'),run('JSON.stringify(gUnit().sections[0].check.questions[0].options)'));
 run(`var record=gAttempt(gUnit(),gUnit().sections[0].check);var oldFirst=JSON.stringify(record.optionOrders[0]);record.optionOrders[1]=['bad'];gStoreAttempt(gUnit(),gUnit().sections[0].check,record);gEnsureAttempt(gUnit(),gUnit().sections[0].check);`);
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().sections[0].check).optionOrders[0])'),run('oldFirst'));
 assert.equal(run('gAttempt(gUnit(),gUnit().sections[0].check).errors'),1);
 assert.equal(run('gChoicePermutation(gAttempt(gUnit(),gUnit().sections[0].check).optionOrders[1],gUnit().sections[0].check.questions[1].options)'),true);
});

test('guided choice values and their stored order survive editing and reload without touching word banks',()=>{
 const storage=new Map();let run=context([unit17],storage);unlockUntil(run,'exercise:17.3');
 run(`save();document.querySelector=()=>null;gStart(COURSE.grammar[0].id,'exercise:17.3');gMove(1);
 var group=gUnit().exercises[2],specs=gChoiceSpecs(group),originalTiles=JSON.stringify(group.questions.map(q=>q.tiles));`);
 const orders=run('JSON.stringify(gAttempt(gUnit(),group).optionOrders)');
 run(`for(let slot=0;slot<group.questions[0].guidedGaps.choices.length;slot++)gSelectGapValue(slot,specs.find(s=>s.key==='0:'+slot).answer);gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('JSON.stringify(group.questions.map(q=>q.tiles))'),run('originalTiles'));
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),group).optionOrders)'),orders);
 run('gExit()');run=context([unit17],storage);run(`gStart(COURSE.grammar[0].id,'all',true)`);
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().exercises[2]).optionOrders)'),orders);
});

test('ordered pedagogical choices can explicitly opt out with no content reordering',()=>{
 const run=context();
 run(`var fixed={shuffleOptions:false,optionOrderReason:'Частотная шкала по возрастанию',questions:Array.from({length:12},()=>({answers:['c'],options:['a','b','c']}))};`);
 assert.equal(run('Object.values(gPlanChoiceOrders(fixed)).every(o=>o.join()===\'a,b,c\')'),true);
 assert.equal(run('gChoiceOrderIssues(fixed,gPlanChoiceOrders(fixed)).length'),0);
 run(`delete fixed.shuffleOptions;fixed.questions.forEach(q=>q.shuffleOptions=false);`);
 assert.equal(run('Object.values(gPlanChoiceOrders(fixed)).every(o=>o.join()===\'a,b,c\')'),true);
});

test('failed exercise recovery creates new orders while preserving the same order throughout the failed attempt',()=>{
 const storage=new Map(),run=context([unit],storage);unlockUntil(run,'exercise:1.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:1.1');gMove(1);var firstId=gAttempt(gUnit(),gUnit().exercises[0]).id,firstOrders=JSON.stringify(gAttempt(gUnit(),gUnit().exercises[0]).optionOrders);
 for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='wrong';gCheck();if(!G.recovery)gMove(1);}`);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).status'),'failed');
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().exercises[0]).optionOrders)'),run('firstOrders'));
 run(`gReviewTheory();while(gAttempt(gUnit(),gUnit().exercises[0]).reviewAt<gTheorySections(gUnit(),gUnit().exercises[0]).length-1)gReviewMove(1);gRepeatExercise();`);
 assert.notEqual(run('gAttempt(gUnit(),gUnit().exercises[0]).id'),run('firstId'));
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),0);
 assert.equal(run('gChoiceOrderIssues(gUnit().exercises[0],gAttempt(gUnit(),gUnit().exercises[0]).optionOrders).length'),0);
});

test('a degenerate random seed still expands to a non-repeating valid plan',()=>{
 const run=context();
 run(`var group={questions:Array.from({length:32},()=>({answers:['d'],options:['a','b','c','d']}))};var order=gPlanChoiceOrders(group,()=>0);`);
 assert.equal(run('gChoiceOrderIssues(group,order).length'),0);
 assert.ok(run('Object.values(order).some(o=>o.indexOf("d")===0)'));
 assert.ok(run('Object.values(order).some(o=>o.indexOf("d")===3)'));
});

test('multiple accepted answers cannot hide an always-correct last position behind balanced primary answers',()=>{
 const run=context();
 run(`var group={questions:Array.from({length:8},()=>({answers:['a','b'],options:['a','b','c','d']}))};
 var biased=Object.fromEntries(group.questions.map((q,i)=>{const o=['c','d','c','b'];o[i%4]='a';o[(i%4)===3?2:3]='b';const unused=['c','d'];for(let j=0;j<4;j++)if(o[j]!=='a'&&o[j]!=='b')o[j]=unused.shift();return [i,o]}));`);
 assert.ok(run('gChoiceOrderIssues(group,biased).some(x=>x.kind==="accepted-imbalance")'));
 assert.equal(run('gChoiceOrderIssues(group,gPlanChoiceOrders(group)).length'),0);
});

test('article recall accepts every preserved answer, case and whitespace, while rejecting extra accents and wrong forms',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>f.endsWith('.json')).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 const run=context(units);
 const result=JSON.parse(run(`JSON.stringify((()=>{let count=0;for(const u of COURSE.grammar)for(const g of u.exercises)for(const q of g.questions){if(q.interaction!=='article-input')continue;count++;for(const a of q.answers){const value='  '+a.toUpperCase().replace(/ /g,'   ')+'  ';if(!grammarResult(q,value,g,true).good)throw Error(g.id+': '+a);}if(grammarResult(q,'ellos',g,true).good)throw Error(g.id+': wrong article');if(q.inputFormat.example||q.options)throw Error(g.id+': answer cue');}return {count};})())`));
 assert.equal(result.count,177);
 for(const value of ['él','ellos','es la','un padre',''])assert.equal(run(`grammarResult(COURSE.grammar[5].exercises[1].questions[0],${JSON.stringify(value)},COURSE.grammar[5].exercises[1],true).good`),false);
});

test('omission control is available for both required and absent articles and does not submit or consume a life',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/005_sin_articulo.json','utf8'));
 const run=context([u]);unlockUntil(run,'exercise:5.2');
 run(`gStart(COURSE.grammar[0].id,'exercise:5.2');gMove(1);`);
 assert.ok(run('gPlayerView()').includes('data-gno-article'));
 assert.ok(!run('gPlayerView()').includes('data-gchar="∅"'));
 run(`render=()=>{};document.querySelector=()=>null;gNoArticle();`);
 assert.equal(run('gResponse(G.steps[G.at]).value'),'∅');
 assert.equal(run('gResponse(G.steps[G.at]).checked'),false);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),0);
 run('gCheck();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
 run('gMove(1);');
 assert.ok(run('gPlayerView()').includes('data-gno-article'));
 run('gNoArticle();gCheck();');
 assert.equal(run('gResponse(G.steps[G.at]).status'),'correct');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
});

test('changing article choices to typing preserves saved answers, drafts, lives and original question position',()=>{
 const current=JSON.parse(fs.readFileSync('content/grammar/006_articulo_definido.json','utf8'));
 const old=JSON.parse(JSON.stringify(current));for(const q of old.exercises[1].questions){q.options=['el','la','los','las'];q.interaction='gap-choice';}
 const storage=new Map();let run=context([old],storage);unlockUntil(run,'exercise:6.2');
 run(`save();gStart(COURSE.grammar[0].id,'exercise:6.2');gMove(1);gPickValue('la');gMove(1);gResponse(G.steps[G.at]).value=' La ';gSave();`);
 run=context([current],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('G.steps[G.at].qi'),1);
 assert.equal(run('gResponse(G.steps[G.at]).value'),' La ');
 assert.equal(run('gQuestionMode(gUnit().exercises[1].questions[1],gResponse(G.steps[G.at]))'),'input');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).responses[0].checked'),true);
 run('gCheck();');assert.equal(run('gResponse(G.steps[G.at]).status'),'correct');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),1);
});

test('family article recall stops on the third mistake and requires theory before a new attempt',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/006_articulo_definido.json','utf8'));
 const run=context([u]);unlockUntil(run,'exercise:6.2');
 run(`gStart(COURSE.grammar[0].id,'exercise:6.2');gMove(1);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='unos';gCheck();if(i<2)gMove(1);}`);
 assert.equal(run('G.recovery'),'6.2');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),3);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).status'),'failed');
 assert.equal(run('P.xp'),0);
 assert.ok(run('gPlayerView()').includes('data-greview-theory'));
});

test('six-choice short exercises balance positions instead of leaving seven questions unbalanced',()=>{
 const run=context();
 run(`var six={questions:Array.from({length:7},()=>({answers:['f'],options:['a','b','c','d','e','f']}))};
 function seeded18(seed){let n=seed>>>0;return ()=>((n=(1664525*n+1013904223)>>>0)/4294967296);}`);
 for(let seed=1;seed<=300;seed++){
  const counts=JSON.parse(run(`JSON.stringify((()=>{const o=gPlanChoiceOrders(six,seeded18(${seed}));const counts=Array(6).fill(0);for(const s of gChoiceSpecs(six))counts[o[s.key].indexOf(s.answer)]++;if(gChoiceOrderIssues(six,o).length)throw Error('invalid plan');return counts;})())`));
  assert.ok(Math.max(...counts)<=2,`seed ${seed}: ${counts}`);
 }
});

test('2 through 10 choices distribute across attempts and within thirty-question exercises without source-index bias',()=>{
 const run=context();
 const results=JSON.parse(run(`JSON.stringify((()=>{
  function seeded18(seed){let n=seed>>>0;return ()=>((n=(1664525*n+1013904223)>>>0)/4294967296);}
  const results=[];for(const size of [2,3,4,5,6,7,8,10]){
   const values=Array.from({length:size},(_,i)=>'value-'+i),answer=values.at(-1),group={questions:Array.from({length:30},()=>({options:values,answers:[answer]}))};
   const counts=Array(size).fill(0),perQuestion=Array.from({length:30},()=>Array(size).fill(0));
   for(let seed=1;seed<=300;seed++){
    const orders=gPlanChoiceOrders(group,seeded18(seed*7919));if(gChoiceOrderIssues(group,orders).length)throw Error(size+': invalid distribution');
    for(const s of gChoiceSpecs(group)){const position=orders[s.key].indexOf(answer);counts[position]++;perQuestion[+s.key][position]++;}
   }
   results.push({size,counts,perQuestion});
  }return results;
 })())`));
 for(const {size,counts,perQuestion} of results){
  const expected=9000/size;
  assert.ok(counts.every(n=>Math.abs(n-expected)<expected*.12),`${size} choices: ${counts}`);
  assert.ok(perQuestion.every(c=>c.every(n=>n>0)),`${size}: a question never reached some position`);
 }
});

test('all actual six-option questions reach all six positions across seeded attempts',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>f.endsWith('.json')).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 const run=context(units);
 const result=JSON.parse(run(`JSON.stringify((()=>{
  function seeded18(seed){let n=seed>>>0;return ()=>((n=(1664525*n+1013904223)>>>0)/4294967296);}
  const counts=Array(6).fill(0),questions={};
  for(const u of COURSE.grammar)for(const group of gGroups(u)){
   const six=gChoiceSpecs(group).filter(s=>s.values.length===6&&!s.fixed);if(!six.length)continue;
   for(const s of six)questions[u.number+'/'+group.id+'/'+s.key]=Array(6).fill(0);
   for(let seed=1;seed<=600;seed++){
    const orders=gPlanChoiceOrders(group,seeded18(seed*3571));if(gChoiceOrderIssues(group,orders).length)throw Error(group.id+': invalid plan');
    for(const s of six){const p=orders[s.key].indexOf(s.answer);counts[p]++;questions[u.number+'/'+group.id+'/'+s.key][p]++;}
   }
  }return {counts,questions};
 })())`));
 assert.equal(Object.keys(result.questions).length,9);
 assert.ok(result.counts.every(n=>Math.abs(n-900)<108),JSON.stringify(result.counts));
 for(const [key,counts] of Object.entries(result.questions))assert.ok(counts.every(n=>n>0),`${key}: ${counts}`);
});

test('legacy source-order attempts shuffle unseen six-option questions once while retaining visited layouts and errors',()=>{
 const run=context();
 run(`var group={questions:Array.from({length:30},()=>({answers:['f'],options:['a','b','c','d','e','f']}))};
 var old={id:'old',errors:1,status:'active',responses:{0:{value:'a',checked:true,good:false},2:{value:'draft',checked:false}},optionOrders:Object.fromEntries(group.questions.map((q,i)=>[i,q.options.slice()]))};
 var originalResponses=JSON.stringify(old.responses);gEnsureChoiceOrders(group,old);`);
 assert.equal(run('old.choiceOrderVersion'),2);
 assert.equal(run('old.optionOrders[0].join()'),'a,b,c,d,e,f');
 assert.equal(run('old.optionOrders[2].join()'),'a,b,c,d,e,f');
 assert.equal(run('JSON.stringify(old.responses)'),run('originalResponses'));
 assert.equal(run('old.errors'),1);
 assert.equal(run('gChoiceOrderIssues({...group,questions:group.questions.map((q,i)=>i===0||i===2?{...q,shuffleOptions:false}:q)},old.optionOrders).length'),0);
 assert.ok(run("Object.entries(old.optionOrders).some(([qi,o])=>qi!=='0'&&qi!=='2'&&o.indexOf('f')!==5)"));
 run('var plan=JSON.stringify(old.optionOrders);');
 assert.equal(run('gEnsureChoiceOrders(group,old)'),false);
 assert.equal(run('JSON.stringify(old.optionOrders)'),run('plan'));
});

test('a currently visible unanswered six-option question keeps its layout during migration and reload',()=>{
 const u=JSON.parse(JSON.stringify(unit));u.sections[0].check.questions=Array.from({length:12},()=>({prompt:'___',answers:['f'],options:['a','b','c','d','e','f'],explain:'f'}));
 const storage=new Map();let run=context([u],storage);
 run(`save();gStart(COURSE.grammar[0].id,'section:0');gMove(1);var group=gUnit().sections[0].check,record=gAttempt(gUnit(),group);delete record.choiceOrderVersion;record.responses={};record.optionOrders=Object.fromEntries(group.questions.map((q,i)=>[i,q.options.slice()]));gStoreAttempt(gUnit(),group,record);gEnsureAttempt(gUnit(),group);`);
 assert.equal(run("gAttempt(gUnit(),group).optionOrders[0].join()"),'a,b,c,d,e,f');
 assert.ok(run("Object.values(gAttempt(gUnit(),group).optionOrders).some(o=>o.indexOf('f')!==5)"));
 const orders=run('JSON.stringify(gAttempt(gUnit(),group).optionOrders)');
 run('gSave();gExit();');run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('JSON.stringify(gAttempt(gUnit(),gUnit().sections[0].check).optionOrders)'),orders);
 run("gPickValue('f');");assert.equal(run('gResponse(G.steps[G.at]).status'),'correct');
});

test('the form renderer creates a persistent randomized plan instead of rendering unsaved source order',()=>{
 const u=JSON.parse(JSON.stringify(unit));u.exercises[0].questions=Array.from({length:30},()=>({prompt:'___',answers:['f'],options:['a','b','c','d','e','f'],explain:'f'}));
 const run=context([u]);
 run('var group=COURSE.grammar[0].exercises[0];var firstForm=grammarForm(COURSE.grammar[0],group);var firstPlan=JSON.stringify(gAttempt(COURSE.grammar[0],group).optionOrders);');
 assert.equal(run('gChoiceOrderIssues(group,gAttempt(COURSE.grammar[0],group).optionOrders).length'),0);
 assert.equal(run('grammarForm(COURSE.grammar[0],group)'),run('firstForm'));
 assert.equal(run('JSON.stringify(gAttempt(COURSE.grammar[0],group).optionOrders)'),run('firstPlan'));
});

test('fixed legacy full-answer lists do not freeze unseen guided choices during migration',()=>{
 const run=context([unit17]);
 run(`var group=COURSE.grammar[0].exercises[2],old={id:'old-guided',errors:0,status:'active',responses:{}};gEnsureChoiceOrders(group,old);var sourceLists=gChoiceSpecs(group).filter(s=>s.fixed),slots=gChoiceSpecs(group).filter(s=>!s.fixed);`);
 assert.ok(run('sourceLists.length>0'));
 assert.equal(run('sourceLists.every(s=>old.optionOrders[s.key].join()===s.values.join())'),true);
 assert.ok(run('slots.some(s=>old.optionOrders[s.key].join()!==s.values.join())'));
 assert.equal(run('gChoiceOrderIssues(group,old.optionOrders).length'),0);
});

test('possessives distinguish semantic tu/tú and forgive omitted mío accents without spending lives',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/019_posesivos_largos.json','utf8'));
 const run=context([u]);unlockUntil(run,'exercise:19.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:19.1');gMove(1);gResponse(G.steps[G.at]).value='mias';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),0);
 assert.equal(run(`grammarResult({answers:['tu']},'tú').good`),false);
 assert.equal(run(`grammarResult({answers:['tú']},'tu').good`),false);
 assert.equal(run(`grammarResult({answers:['suyo']},'suyos').good`),false);
 assert.equal(run(`gInputChars(gUnit().exercises[0].questions[0]).join('')`),'áéíóúüñ');
});

test('multiword dialogue gaps restore one complete possessive phrase per field',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/019_posesivos_largos.json','utf8'));
 const run=context([u]);
 const html=run(`gGapSentence(COURSE.grammar[0].exercises[1].questions[5],{value:'el tuyo el mío',checked:true})`);
 assert.ok(html.includes('value="el tuyo"'));assert.ok(html.includes('value="el mío"'));
 assert.ok(!html.includes('value="tuyo"'));
});

test('new possessive units fail at three errors, preserve failure on reload, and review their own theory',()=>{
 for(const name of ['018_posesivos_cortos.json','019_posesivos_largos.json']){
  const u=JSON.parse(fs.readFileSync('content/grammar/'+name,'utf8'));
  for(const g of u.exercises){
   const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:'+g.id);
   run(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}gSave();`);
   assert.equal(run('gAttempt(gUnit(),gGroups(gUnit()).find(g=>g.id===G.recovery)).errors'),3);
   run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true);gReviewTheory();`);
   assert.ok(run('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
   assert.equal(run('P.xp'),0);
  }
 }
});

test('unit 20 accepts omitted acute accent with a warning but rejects wrong indefinite forms',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/020_indefinidos.json','utf8'));
 const run=context([u]);unlockUntil(run,'exercise:20.2');
 run(`gStart(COURSE.grammar[0].id,'exercise:20.2');gMove(1);G.at=G.steps.findIndex(s=>s.type==='question'&&s.group==='20.2'&&s.qi===6);gResponse(G.steps[G.at]).value='ningun';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),0);
 assert.equal(run(`grammarResult(gUnit().exercises[1].questions[6],'ninguno').good`),false);
 assert.equal(run(`grammarResult(gUnit().exercises[2].questions[2],'ningún de').good`),false);
 assert.equal(run(`grammarResult(gUnit().exercises[3].questions[1],'todo').good`),false);
 assert.equal(run(`grammarResult(gUnit().exercises[3].questions[3],'ninguno').good`),false);
 assert.equal(run(`grammarResult(gUnit().exercises[0].questions[0],'  TODAS   LAS CAJAS  ').good`),true);
});

test('unit 20 stops every exercise at three errors and returns to its own theory after reload',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/020_indefinidos.json','utf8'));
 for(const g of u.exercises){
  const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:'+g.id);
  run(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}`);
  assert.equal(run(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).status`),'failed');
  assert.equal(run(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),3);
  run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true);gReviewTheory();`);
  assert.ok(run('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
  assert.equal(run('P.xp'),0);
 }
});

test('unit 20 requires both dialogue gaps and preserves a partial answer on reload',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/020_indefinidos.json','utf8'));
 const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:20.4');
 run(`save();gStart(COURSE.grammar[0].id,'exercise:20.4');gMove(1);var response=gResponse(G.steps[G.at]);response.gapValues=['algunos',''];response.value='';gSave();gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).checked'),false);
 run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(run('gResponse(G.steps[G.at]).gapValues[0]'),'algunos');
 assert.equal(run('gResponse(G.steps[G.at]).checked'),false);
 run(`var r=gResponse(G.steps[G.at]);r.gapValues=['algunos','todos'];r.value='algunos todos';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'correct');
});

test('unit 21 accepts regional and context-equivalent answers but rejects target grammar errors',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/021_uno_otro_cualquiera.json','utf8'));
 const run=context([u]);
 for(const [g,qi,value,status] of [
  [0,1,'otra','correct'],[0,1,'una otra','wrong'],[0,1,'otro','wrong'],
  [1,0,'cualquiera','almost'],[1,0,'cualquier','correct'],[1,1,'cualquier de','wrong'],
  [1,2,'cualquiera','wrong'],[1,3,'cualquiera','wrong'],
  [2,2,'otros de','wrong'],[2,4,'uno','wrong'],[2,5,'otros','wrong'],
  [2,6,'una cualquiera de','correct'],[3,2,'uno cualquiera','correct'],[3,2,'una cualquiera','wrong']
 ]) assert.equal(run(`grammarResult(COURSE.grammar[0].exercises[${g}].questions[${qi}],${JSON.stringify(value)}).status`),status);
 unlockUntil(run,'exercise:21.2');
 run(`gStart(COURSE.grammar[0].id,'exercise:21.2');gMove(1);gResponse(G.steps[G.at]).value='cualquiera';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),0);
 assert.equal(run('G.at'),1,'feedback waits for manual Next');
 assert.ok(run('gPlayerView()').includes('обычно перед существительным говорят cualquier'));
});

test('unit 21 preserves partial input and a failed attempt; retry resets only the current exercise',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/021_uno_otro_cualquiera.json','utf8'));
 for(const g of u.exercises){
  const storage=new Map();let run=context([u],storage);unlockUntil(run,'exercise:'+g.id);
  run(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);gResponse(G.steps[G.at]).value='parcial';gSave();`);
  run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
  assert.equal(run('gResponse(G.steps[G.at]).value'),'parcial');
  run(`var best=JSON.stringify(P.grammar);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}`);
  assert.equal(run(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),3);
  assert.equal(run('JSON.stringify(P.grammar)'),run('best'));
  run=context([u],storage);run(`gStart(COURSE.grammar[0].id,'all',true);`);
  assert.ok(run('G.recovery'));
  run('gReviewTheory();');
  assert.ok(run('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
  run('gRepeatExercise();');
  assert.equal(run(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
  assert.equal(run('G.steps[G.at].type'),'intro');
 }
});

test('unit 21 completes every new format and reaches the final summary without changing previous units',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/021_uno_otro_cualquiera.json','utf8'));
 const run=context([u]);run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
 while(!run('G.ended')&&turns++<100){
  run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);
 }
 assert.ok(turns<100);assert.equal(run('gUnitComplete(gUnit())'),true);
 assert.equal(run('P.xp'),76);
 assert.ok(run('gPlayerView()').includes('Все уроки раздела пройдены!'));
});

test('unit 22 distinguishes agreement, sufficiency and context-equivalent short answers',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/022_cantidad.json','utf8'));const run=context([u]);
 for(const [gi,qi,a,status] of [[0,3,'mucha','correct'],[0,3,'mucho','wrong'],[0,6,'poca','correct'],[1,0,'demasiadas','correct'],[1,0,'demasiados','wrong'],[1,4,'suficienta','wrong'],[2,3,'bastantes gente','wrong'],[2,5,'muchos arboles','almost'],[3,1,'bastantes','correct'],[3,2,'bastante','correct'],[3,3,'muchas','wrong']]){
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises[${gi}].questions[${qi}],${JSON.stringify(a)}).status`),status);
 }
});

test('quantity lessons complete every format and retain three-error recovery across reload',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>/^02[2-4]_.*\.json$/.test(f)).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 for(const u of units){
  const run=context([u]);run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
  while(!run('G.ended')&&turns++<180){run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);}
  assert.ok(turns<180);assert.equal(run('gUnitComplete(gUnit())'),true);
  for(const g of u.exercises){
   const storage=new Map();let retry=context([u],storage);unlockUntil(retry,'exercise:'+g.id);
   retry(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);gResponse(G.steps[G.at]).value='parcial';gSave();`);
   retry=context([u],storage);retry(`gStart(COURSE.grammar[0].id,'all',true);`);
   assert.equal(retry('gResponse(G.steps[G.at]).value'),'parcial');
   retry(`var savedBest=JSON.stringify(P.grammar);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}`);
   assert.equal(retry(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),3);
   assert.equal(retry('JSON.stringify(P.grammar)'),retry('savedBest'));
   retry=context([u],storage);retry(`gStart(COURSE.grammar[0].id,'all',true);`);
   assert.ok(retry('G.recovery'));retry('gReviewTheory();');
   assert.ok(retry('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
   for(let i=1;i<g.theorySections.length;i++)retry('gMove(1);');retry('gRepeatExercise();');
   assert.equal(retry(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
  }
 }
});

test('unit 23 distinguishes people and things, negation order and quantity de',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/023_alguien_algo.json','utf8'));const run=context([u]);
 for(const [gi,qi,a,status] of [[0,0,'No hay nadie','wrong'],[0,1,'Hay alguien','correct'],[0,3,'No hay nada','wrong'],[1,3,'algo','wrong'],[1,5,'Nadie','correct'],[1,10,'Nadie no ha venido','wrong'],[1,10,'Nadie ha venido','correct'],[2,0,'nada algo','wrong'],[2,0,'nada de algo de','correct'],[2,1,'algo de','wrong'],[2,2,'nada algo de','correct']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises[${gi}].questions[${qi}],${JSON.stringify(a)}).status`),status);
 const storage=new Map();let r=context([u],storage);unlockUntil(r,'exercise:23.3');
 r(`save();gStart(COURSE.grammar[0].id,'exercise:23.3');gMove(1);var x=gResponse(G.steps[G.at]);x.gapValues=['nada de',''];x.value='';gSave();gCheck();`);
 assert.equal(r('gResponse(G.steps[G.at]).checked'),false);
 r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(r('gResponse(G.steps[G.at]).gapValues[0]'),'nada de');
 r(`var x=gResponse(G.steps[G.at]);x.gapValues=['nada de','algo de'];x.value='nada de algo de';gCheck();`);
 assert.equal(r('gResponse(G.steps[G.at]).status'),'correct');
});

test('unit 24 checks comparison links, noun agreement and meaning-changing accents',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/024_mas_menos_tanto.json','utf8'));const run=context([u]);
 for(const [gi,qi,a,status] of [[0,0,'mas','wrong'],[0,0,'más','correct'],[1,4,'tanto','wrong'],[1,4,'tanta','correct'],[2,0,'menos como','wrong'],[2,0,'menos que','correct'],[2,1,'tanta como','correct'],[2,1,'tanto como','wrong'],[3,1,'tantos como tu','wrong'],[3,3,'tantos como tú','correct'],[3,7,'tantas como tú','wrong'],[3,7,'tanto como tú','correct'],[3,8,'tantas','correct']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises[${gi}].questions[${qi}],${JSON.stringify(a)}).status`),status);
 const storage=new Map();let r=context([u],storage);unlockUntil(r,'exercise:24.2');
 r(`save();gStart(COURSE.grammar[0].id,'exercise:24.2');gMove(1);var x=gResponse(G.steps[G.at]);x.gapValues=['menos',''];x.value='';gSave();gCheck();`);
 assert.equal(r('gResponse(G.steps[G.at]).checked'),false);
 r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);
 assert.equal(r('gResponse(G.steps[G.at]).gapValues[0]'),'menos');
 r(`var x=gResponse(G.steps[G.at]);x.gapValues=['menos','que'];x.value='menos que';gCheck();`);
 assert.equal(r('gResponse(G.steps[G.at]).status'),'correct');
});

test('course next-lesson cards now connect 21 through 27 without skipping 22 to 24',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>/^02[1-7]_.*\.json$/.test(f)).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 for(let i=0;i<units.length-1;i++){
  const run=context(units);
  assert.equal(run(`gNextUnit(COURSE.grammar[${i}]).number`),units[i+1].number);
  const html=run(`gFinalView(COURSE.grammar[${i}],[],0)`);assert.ok(html.includes('Далее · Урок '+units[i+1].number));assert.ok(html.includes(units[i+1].title));
 }
});

test('numeral unit 25 distinguishes agreement, accents, date alternatives and leading telephone zeroes',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/025_numeros_0_99.json','utf8'));const run=context([u]);
 for(const [gi,qi,a,status] of [[0,0,'veintiun','almost'],[0,0,'veintiuno','wrong'],[0,6,'treinta y una','correct'],[0,6,'treintaiuna','correct'],[1,0,'primero','correct'],[1,5,'veintiún','wrong'],[3,0,'dos','wrong'],[3,5,'cero uno','correct'],[2,1,'las una y cuarto','wrong']]){
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises[${gi}].questions[${qi}],${JSON.stringify(a)}).status`),status);
 }
});

test('typing after a tall clock scrolls only the body to expose the field and Spanish keys',()=>{
 const run=context();
 run(`var scroller={scrollTop:0,scrollHeight:900,clientHeight:400,getBoundingClientRect:()=>({top:120,bottom:520})};
 var fieldRect={top:480,bottom:550};var keyRect={bottom:610};
 var input={matches:()=>true,getBoundingClientRect:()=>fieldRect,parentElement:{querySelector:()=>({getBoundingClientRect:()=>keyRect})}};
 document.activeElement=input;document.querySelector=()=>({style:{},classList:{toggle:()=>{}},querySelector:()=>scroller});gSyncViewport();`);
 assert.equal(run('scroller.scrollTop'),102);
 run('scroller.scrollTop=0;fieldRect={top:180,bottom:240};keyRect={bottom:290};gSyncViewport();');
 assert.equal(run('scroller.scrollTop'),0,'already visible input does not jump');
 run('scroller.scrollTop=200;fieldRect={top:70,bottom:130};keyRect={bottom:180};gSyncViewport();');
 assert.equal(run('scroller.scrollTop'),138,'a field above the body is brought back');
});

test('numeral unit 26 rejects cien/ciento, agreement and million/de errors but accepts decimal variants',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/026_cien_mil_millon.json','utf8'));const run=context([u]);
 for(const [gi,qi,a,status] of [[0,0,'ciento','wrong'],[0,1,'cien un','wrong'],[0,2,'quinientos','wrong'],[1,1,'un mil setenta','wrong'],[1,3,'un millon doscientos treinta y un mil setecientos cincuenta y ocho','almost'],[2,0,'ciento quince coma uno cero','correct'],[2,0,'ciento quince con diez','correct'],[2,7,'mil cuatrocientos veintiún','wrong'],[3,0,'dos millones de','wrong'],[3,2,'trescientos','wrong'],[4,1,'dos mil uno','correct']]){
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises[${gi}].questions[${qi}],${JSON.stringify(a)}).status`),status);
 }
});

test('growing phrase input preserves the draft and resynchronizes its visible area without grading',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/026_cien_mil_millon.json','utf8'));const handlers={};const run=context([u],new Map(),handlers);
 unlockUntil(run,'exercise:26.1');run(`gStart(COURSE.grammar[0].id,'exercise:26.1');gMove(1);var syncCalls=0;gSyncViewport=()=>syncCalls++;document.querySelector=()=>null;`);
 handlers.input({target:{id:'g-answer',tagName:'TEXTAREA',dataset:{},value:'mil setenta',closest:()=>null}});
 assert.equal(run('syncCalls'),1);assert.equal(run('gResponse(G.steps[G.at]).value'),'mil setenta');
 assert.equal(run('gResponse(G.steps[G.at]).checked'),false);assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).errors'),0);
});

test('ordinal unit 27 separates apocope, gender, quantity and alternative high-number readings',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/027_ordinales.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['27.1.4','tercero','wrong'],['27.1.6','primer','correct'],['27.1.9','septimo','almost'],['27.1.9','sétimo','correct'],['27.2.2','primero','wrong'],['27.2.3','veintitres','almost'],['27.2.4','duodécimo','correct'],['27.3.3a','decimoquinto','wrong'],['27.3.3b','undécimo','correct'],['27.3.5','tercer','wrong'],['27.3.6','primeros','wrong'],['27.3.12','cuartas','correct']]){
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)}).status`),status,ref+'/'+a);
 }
});

test('numeral lessons fully complete all formats and retain failures across reload and retry',()=>{
 const units=fs.readdirSync('content/grammar').filter(f=>/^02[5-7]_.*\.json$/.test(f)).sort().map(f=>JSON.parse(fs.readFileSync('content/grammar/'+f,'utf8')));
 for(const u of units){
  const run=context([u]);run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
  while(!run('G.ended')&&turns++<180){run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);}
  assert.ok(turns<180);assert.equal(run('gUnitComplete(gUnit())'),true);
  if(u.number===26)assert.ok(run('gPlayerView()').includes('5 упражнений завершено'));
  for(const g of u.exercises){
   const storage=new Map();let retry=context([u],storage);unlockUntil(retry,'exercise:'+g.id);
   retry(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);for(let i=0;i<3;i++){gResponse(G.steps[G.at]).value='incorrecto';gCheck();if(!G.recovery)gMove(1);}`);
   assert.equal(retry(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).status`),'failed');
   retry=context([u],storage);retry(`gStart(COURSE.grammar[0].id,'all',true);gReviewTheory();`);
   assert.ok(retry('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
   for(let i=1;i<g.theorySections.length;i++)retry('gMove(1);');retry('gRepeatExercise();');
   assert.equal(retry(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
  }
 }
});
test('new pronoun lessons complete every answer and preserve failed attempts across reload',()=>{
 const files=fs.readdirSync('content/grammar').filter(f=>/^(03[789]|04[01])_.*\.json$/.test(f)).sort();
 for(const file of files){
  const u=JSON.parse(fs.readFileSync('content/grammar/'+file,'utf8'));const run=context([u]);
  run(`gStart(COURSE.grammar[0].id,'all');`);let turns=0;
  while(!run('G.ended')&&turns++<220)run(`var s=G.steps[G.at];if(s.type==='question'){var g=gGroups(gUnit()).find(g=>g.id===s.group);gResponse(s).value=g.questions[s.qi].answers[0];gCheck();}gMove(1);`);
  assert.ok(turns<220);assert.equal(run('gUnitComplete(gUnit())'),true,u.number);
  for(const g of [...u.sections.map(s=>s.check),...u.exercises])for(const q of g.questions)for(const a of q.answers){
   const result=JSON.parse(run(`JSON.stringify(grammarResult(${JSON.stringify(q)},${JSON.stringify('  '+a.toUpperCase()+'  ')},{},true))`));
   assert.equal(result.good,true,u.number+'/'+q.sourceRef+'/'+a);
   assert.equal(result.status,q.answerWarnings?.[a]?'almost':'correct');
   assert.equal(run(`grammarResult(${JSON.stringify(q)},'incorrecto').status`),'wrong');
  }
  for(const g of u.exercises){
   const storage=new Map();let r=context([u],storage);unlockUntil(r,'exercise:'+g.id);
   r(`save();gStart(COURSE.grammar[0].id,'exercise:${g.id}');gMove(1);gResponse(G.steps[G.at]).value='borrador';gSave();`);
   r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.equal(r('gResponse(G.steps[G.at]).value'),'borrador');
   r(`P.grammar[grammarKey(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}'))]={correct:2,total:${g.questions.length}};save();var best=JSON.stringify(P.grammar);`);
   for(let i=1;i<=3;i++){r(`gResponse(G.steps[G.at]).value='incorrecto';gCheck();`);assert.equal(r(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),i);if(i<3)r('gMove(1);');}
   assert.equal(r('JSON.stringify(P.grammar)'),r('best'));
   r=context([u],storage);r(`gStart(COURSE.grammar[0].id,'all',true);`);assert.ok(r('G.recovery'));r('gReviewTheory();');
   assert.ok(r('gPlayerView()').includes(u.sections[g.theorySections[0]].title));
   for(let i=1;i<g.theorySections.length;i++)r('gMove(1);');r('gRepeatExercise();');
   assert.equal(r(`gAttempt(gUnit(),gUnit().exercises.find(g=>g.id==='${g.id}')).errors`),0);
  }
 }
});
test('unit 37 diagnoses role changes, se replacement, order and semantic accents',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/037_se_lo_he_dado.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['37.1.2','se los','wrong'],['37.1.2','les lo','wrong'],['37.1.3','os lo','wrong'],['37.1.4','me las','wrong'],['37.2.1','no lo me ha dado','wrong'],['37.2.4','se la ha enseñado','wrong'],['37.3.7','se los','correct'],['37.4.1','a mi no me las ha dado','wrong'],['37.4.4','a usted no me lo he enviado','wrong'],['37.4.7','a él no le han aprobado','almost']]){
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 }
 const q=u.exercises[0].questions[0];assert.equal(run(`grammarResult(${JSON.stringify(q)},'me').status`),'wrong');
});
test('unit 38 distinguishes object, recipient, neutral lo and permissible personal le',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/038_lo_la_le.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['38.1.1','le','wrong'],['38.1.3','le','wrong'],['38.1.6','les','almost'],['38.1.10','le','almost'],['38.1.11','verle','almost'],['38.1.14','le','almost'],['38.1.7','la','wrong'],['38.1.8','les les lo','wrong'],['38.1.15','le le','correct'],['38.2.3','le','almost'],['38.2.7','les','wrong'],['38.3.2','la','wrong'],['38.3.3','la la','wrong'],['38.3.5','lo le lo','wrong'],['38.3.5','lo le la','correct'],['38.3.7','lo la','correct'],['38.3.8','lo le','wrong']]){
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 }
 unlockUntil(run,'exercise:38.1a');run(`gStart(COURSE.grammar[0].id,'exercise:38.1a');gMove(1);`);
 run(`var s=G.steps[G.at],r=gResponse(s);r.value='lo';gCheck();gMove(1);`);
 assert.equal(run(`gAttempt(gUnit(),gUnit().exercises[0]).errors`),0);
});
test('unit 39 distinguishes joining, two legal positions, accent omissions and targeted spelling',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/039_amame_damelo.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['39.1.1','amalos','almost'],['39.1.1','ámales','almost'],['39.1.2','comprádlo','wrong'],['39.1.3','dálelo','wrong'],['39.1.4','házsela','correct'],['39.1.7','pásaselo','wrong'],['39.2.2','devolvermelo','almost'],['39.2.2','devolverselo','wrong'],['39.2.3','vernos','wrong'],['39.2.6','vendérselo','correct'],['39.3.5','Están haciéndosela','correct'],['39.3.5','Se la están haciendo','correct'],['39.3.5','Se están haciéndola','wrong'],['39.3.5','Están haciendosela','almost'],['39.4.1','Pasame la sal','wrong'],['39.4.1','Pásame la sal','correct'],['39.4.4','Me puedes ayudar','correct'],['39.4.5','Preguntaselo a Julio','wrong'],['39.4.6','Quién está haciéndolo','correct'],['39.4.6','Quien está haciéndolo','wrong'],['39.4.7','Me gustaría decirselo a Sandra','wrong']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 // Yellow accent feedback does not consume a heart in an ordinary replacement.
 unlockUntil(run,'exercise:39.1');run(`gStart(COURSE.grammar[0].id,'exercise:39.1');gMove(1);gResponse(G.steps[G.at]).value='amalos';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),0);
});
test('unit 39 shows meaningful answer alternatives once and retains old feedback when unspecified',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/039_amame_damelo.json','utf8'));const run=context([u]);
 unlockUntil(run,'exercise:39.4');run(`gStart(COURSE.grammar[0].id,'exercise:39.4');gMove(1);gResponse(G.steps[G.at]).value='wrong';gCheck();`);
 const html=run('gPlayerView()');assert.ok(html.includes('Верный ответ: Pásame la sal</span>'));assert.ok(!html.includes('Pásame la sal / Pásame la sal.'));
});

test('unit 40 checks reflexive roles, reciprocal person, omission and semantic accents',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/040_me_ducho_nos_queremos.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['40.1.2','se','correct'],['40.1.2','la','wrong'],['40.1.10','te','wrong'],['40.1.14','os','correct'],['40.2.3','Roque y tú os queréis','correct'],['40.2.3','Roque y tú nos queremos','wrong'],['40.2.3','Roque y tu os queréis','wrong'],['40.2.5','Andres y yo nos conocemos muy bien','almost'],['40.3.5','∅','correct'],['40.3.5','-','correct'],['40.3.5','te','wrong'],['40.3.12','me','wrong'],['40.3.12','—','correct'],['40.1.13','¿Cuándo te lavas el pelo, Sonia?','correct']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
});

test('unit 41 checks fused con, semantic accents and subject versus prepositional exceptions',()=>{
 const u=JSON.parse(fs.readFileSync('content/grammar/041_para_mi_contigo.json','utf8'));const run=context([u]);
 for(const [ref,a,status] of [['41.1.2','usted','correct'],['41.1.2','él','wrong'],['41.1.3','contigo','correct'],['41.1.3','con ti','wrong'],['41.1.4','vosotros','wrong'],['41.1.7','nosotras','correct'],['41.2.1','el','wrong'],['41.2.1','él','correct'],['41.2.3','usted','wrong'],['41.2.4','Antonio quiere hablar contigo','correct'],['41.2.4','Antonio quiere hablar con contigo','wrong'],['41.2.7','mi','wrong'],['41.4.1','tu','wrong'],['41.4.2','tí','wrong'],['41.4.3','yo','wrong'],['41.4.4','Luisa se sienta entre Jorge y yo','correct'],['41.4.6','Sebastian se sienta delante de mí','almost'],['41.4.7','yo','wrong'],['41.4.7','mí','correct'],['41.4.8','mí','wrong'],['41.3.7','con contigo','wrong']])
  assert.equal(run(`grammarResult(COURSE.grammar[0].exercises.flatMap(g=>g.questions).find(q=>q.sourceRef===${JSON.stringify(ref)}),${JSON.stringify(a)},{},true).status`),status,ref+'/'+a);
 unlockUntil(run,'exercise:41.3');run(`gStart(COURSE.grammar[0].id,'exercise:41.3');gMove(1);`);
 run(`G.at=G.steps.findIndex(s=>s.type==='question'&&s.qi===5);gResponse(G.steps[G.at]).value='Sebastian se sienta delante de mí';gCheck();`);
 assert.equal(run('gResponse(G.steps[G.at]).status'),'almost');assert.equal(run('gAttempt(gUnit(),gUnit().exercises[2]).errors'),0);
});
