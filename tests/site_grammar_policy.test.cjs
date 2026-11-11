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


test('each grammar exercise and mini-check gets exactly three lives regardless of length',()=>{
  for(const size of [1,2,3,15,16,40]){
    const g={id:'t',title:size===2?'Мини-проверка':'Упражнение',questions:Array.from({length:size},()=>({prompt:'',answers:['correct']}))};
    const run=context([unit]);
    assert.equal(run('gErrorLimit('+JSON.stringify(g)+')'),3);
    assert.equal(run('gOutOfLives('+JSON.stringify(g)+',2)'),false);
    assert.equal(run('gOutOfLives('+JSON.stringify(g)+',3)'),true);
    assert.equal(run('gHearts(null,'+JSON.stringify(g)+')').match(/♥/g).length,3);
  }
});
test('incorrect answers do not leak, failed card stays visible, theory and retry are voluntary',()=>{
  const run=context([unit3]);unlockUntil(run,'exercise:3.2');
  run('gStart(COURSE.grammar[0].id,"exercise:3.2");gMove(1);');
  for(let i=1;i<=3;i++){
    run('gResponse(G.steps[G.at]).value="wrong";gCheck();');
    const html=run('gPlayerView()');
    assert.equal(html.includes('Верный ответ:'),i===3);
    if(i<3) {
      assert.ok(html.includes('Осталось попыток: '+(3-i)+' из 3'));
      run('gMove(1)');
    }
  }
  assert.ok(!run('G.recovery'));
  assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).status'),'failed');
  assert.equal(run('G.steps[G.at].type'),'question');
  assert.ok(run('gPlayerView()').includes('data-greview-theory'));
  assert.ok(run('gPlayerView()').includes('data-grepeat-exercise'));
  assert.ok(!run('gPlayerView()').includes('data-gnext'));
  const position=run('G.at');run('gMove(1)');
  assert.equal(run('G.at'),position);
  run('gReviewTheory()');
  assert.equal(run('gAttempt(gUnit(),gUnit().exercises[1]).status'),'review');
  assert.equal(run('G.recovery'),'3.2');
});
test('every incorrect field is identified using the nearest of all accepted solutions',()=>{
  const run=context([unit]);
  const guided={
    prompt:'Le ___ ___',answers:['Le la doy','Le lo doy'],
    guidedGaps:{parts:['Le ',' ',''],choices:[['la','lo','me'],['doy','das']]}
  };
  const bad=run('gGapMistakes('+JSON.stringify(guided)+',{value:"Le la das",slotValues:["la","das"],checked:true,good:false})');
  assert.deepEqual(JSON.parse(JSON.stringify(bad.wrong)),[false,true]);
  const html=run('gGuidedContents('+JSON.stringify(guided)+',{value:"Le la das",slotValues:["la","das"],checked:true,good:false})');
  assert.ok(html.includes('is-incorrect'));
  assert.ok(html.includes('Пропуск 2, неверно'));
  assert.ok(!html.includes('Верный ответ:'));
  const typed={prompt:'___ ___',answers:['la niña','una niña'],gapParts:['','',''],gapWordCounts:[1,1]};
  const t=run('gGapMistakes('+JSON.stringify(typed)+',{value:"una niño",gapValues:["una","niño"],checked:true,good:false})');
  assert.deepEqual(JSON.parse(JSON.stringify(t.wrong)),[false,true]);
  const typedHtml=run('gGapSentence('+JSON.stringify(typed)+',{value:"una niño",gapValues:["una","niño"],checked:true,good:false})');
  assert.equal((typedHtml.match(/aria-invalid="true"/g)||[]).length,1);
});
test('wrong correction costs a life instead of permitting unlimited copying',()=>{
 const run=context([unit]);unlockUntil(run,'exercise:1.1');
 run('gStart(COURSE.grammar[0].id,"exercise:1.1");gMove(1);');
 for(let i=0;i<10;i++){
   run('gResponse(G.steps[G.at]).value='+ (i===0?'"wrong"':'gUnit().exercises[0].questions[G.steps[G.at].qi].answers[0]') +';gCheck();gMove(1);');
 }
 assert.equal(run('G.steps[G.at].correction'),true);
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),1);
 run('gResponse(G.steps[G.at]).value="wrong";gCheck();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).errors'),2);
 assert.ok(!run('gPlayerView()').includes('Верный ответ:'));
 run('gMove(1);gResponse(G.steps[G.at]).value="wrong";gCheck();');
 assert.equal(run('gAttempt(gUnit(),gUnit().exercises[0]).status'),'failed');
 assert.ok(run('gPlayerView()').includes('Верный ответ:'));
});

test('PR #34: units 1, 7, 15, 38 and 45 retain question-specific explanations after the third error',()=>{
  const cases=[
    ['001_genero.json','exercise:1.2'],
    ['007_un_perro_el_perro.json','exercise:7.3'],
    ['015_comparativos.json','exercise:15.2'],
    ['038_lo_la_le.json','exercise:38.1b'],
    ['045_tengo_tienes_tiene.json','exercise:45.2']
  ];
  for(const [file,route] of cases){
    const u=JSON.parse(fs.readFileSync('content/grammar/'+file,'utf8'));
    const run=context([u]);
    unlockUntil(run,route);
    run('gStart(COURSE.grammar[0].id,'+JSON.stringify(route)+');gMove(1);');
    for(let i=1;i<=3;i++){
      run('gResponse(G.steps[G.at]).value="incorrecto";gCheck();');
      const html=run('gPlayerView()');
      assert.equal(html.includes('Верный ответ:'),i===3,file+' life '+i);
      if(i===3){
        const question=run('gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group).questions[G.steps[G.at].qi]');
        assert.ok(html.includes(question.explain.replaceAll('&','&amp;').replaceAll('<','&lt;')),file+' explanation');
        assert.equal(run('gAttempt(gUnit(),gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group)).status'),'failed');
      } else run('gMove(1)');
    }
    const before=run('G.responses[G.steps[G.at].group][G.steps[G.at].qi].value');
    const progress=run('JSON.stringify(P.grammar)');
    run('gReviewTheory()');
    assert.ok(run('gPlayerView()').includes('data-greview-mistake'),file);
    assert.equal(run('gCanBack()'),true,file);
    run('gReturnToMistake()');
    assert.equal(run('G.recovery'),null,file);
    assert.equal(run('G.responses[G.steps[G.at].group][G.steps[G.at].qi].value'),before,file);
    assert.ok(run('gPlayerView()').includes('Верный ответ:'),file);
    run('gRepeatExercise()');
    assert.equal(run('gAttempt(gUnit(),gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group)).errors'),0,file);
    assert.equal(run('JSON.stringify(P.grammar)'),progress,file);
  }
});

test('PR #34: accepted alternatives in actual multi-blank tasks do not produce false error highlights',()=>{
  const u38=JSON.parse(fs.readFileSync('content/grammar/038_lo_la_le.json','utf8'));
  const u45=JSON.parse(fs.readFileSync('content/grammar/045_tengo_tienes_tiene.json','utf8'));
  const run=context([u38,u45]);
  const q38=u38.exercises.flatMap(g=>g.questions).find(q=>q.sourceRef==='38.1.5');
  const a38=q38.answers[0].split(' ');
  const r38=run('gGapMistakes('+JSON.stringify(q38)+','+JSON.stringify({value:'le se lo se la',gapValues:['le','se','lo','se','la'],checked:true,good:false})+')');
  assert.deepEqual(JSON.parse(JSON.stringify(r38.wrong)),[false,false,true,false,false]);
  const q45=u45.exercises.flatMap(g=>g.questions).find(q=>q.sourceRef==='45.1.1');
  const r45=run('gGapMistakes('+JSON.stringify(q45)+','+JSON.stringify({value:'tiene tiene tengo',gapValues:['tiene','tiene','tengo'],checked:true,good:false})+')');
  assert.deepEqual(JSON.parse(JSON.stringify(r45.wrong)),[false,true,false]);
  assert.ok(a38.length===5);
});

test('PR #34: outdated hardcoded unit counts are absent from both agent instructions',()=>{
  for(const name of ['AGENTS.md','content/grammar/AGENTS.md']){
    const text=fs.readFileSync(name,'utf8');
    assert.doesNotMatch(text,/\\b(?:17|45)\\s+юнит/i,name);
  }
});
