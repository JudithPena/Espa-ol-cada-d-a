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
 assert.equal(units.length,19);
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
 assert.equal(typed,413);assert.equal(legacy,52);
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
 assert.equal(count,66);
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
 assert.equal(checked,12);
});

test('grammar list gives each theme a distinct icon and marks only fully completed themes',()=>{
 const units=fs.readdirSync('content/grammar').filter(n=>n.endsWith('.json')).sort().map(n=>JSON.parse(fs.readFileSync('content/grammar/'+n,'utf8')));
 const run=context(units);
 run('view.grammar=null;');
 const icons=run('COURSE.grammar.map(u=>G_UNIT_ICONS[u.id])');
 assert.ok(icons.every(Boolean));assert.equal(new Set(icons).size,19);
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
 assert.ok(html.includes('Пройдено тем: 1 из 19'));
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
    for(const c of ['á','é','í','ó','ú','ñ'])assert.equal((html.match(new RegExp('data-gchar="'+c+'"','g'))||[]).length,count,u.id+'/'+group.id+'/'+qi);
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
 assert.equal(questions,970);assert.equal(alternatives,72);assert.equal(warnings,5);
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
   assert.equal((run('grammarView()').match(/data-grammar="/g)||[]).length,19);
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
 assert.equal(standard,505);assert.equal(guided,9);
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
