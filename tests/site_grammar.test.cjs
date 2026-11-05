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
function context(grammar = [unit], storage = new Map()) {
  const noop = () => {};
  const ctx = vm.createContext({console, setTimeout:noop, clearTimeout:noop, addEventListener:noop,
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    window:{addEventListener:noop}, document:{documentElement:{classList:{toggle:noop}},addEventListener:noop,getElementById:()=>null,querySelector:()=>({focus:noop})},
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
 run('gStart(COURSE.grammar[0].id,"exercise:1.3");gMove(1);while(!G.ended){const step=G.steps[G.at],group=gGroups(gUnit()).find(g=>g.id===step.group);gResponse(step).value=group.questions[step.qi].answers[0];gCheck();gMove(1);}');
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

test('unit 10 also celebrates when its last practice route differs from the exercise array order', () => {
 const u=newUnits.find(u=>u.number===10),run=context([u]);
 run('render=()=>{};sfx=()=>{};gStart(COURSE.grammar[0].id);');
 run('for(const g of gGroups(gUnit()))gradeGrammar(gUnit(),g,g.questions.map(q=>q.answers[0]));G.route="exercise:10.3";G.ended=true;');
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
 assert.equal(units.length,17);
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

test('time options display whole sentence openings while old stored article values still grade',()=>{
 const all=JSON.parse(fs.readFileSync('content/grammar/009_tiempo_fecha.json','utf8'));
 const run=context([all]);unlockUntil(run,'exercise:9.1');
 run(`gStart(COURSE.grammar[0].id,'exercise:9.1');gMove(1);`);
 let html=run('gPlayerView()');
 assert.ok(html.includes('Es la') && html.includes('Son las'));
 assert.ok(!html.includes('Son ___'));
 run(`gPick(gUnit().exercises[0].questions[0].options.indexOf('las'));`);
 assert.equal(run('gResponse(G.steps[G.at]).value'),'las');
 assert.equal(run('gResponse(G.steps[G.at]).good'),true);
 assert.equal(run('G.at'),1);
 assert.equal(run(`gOptionLabel({optionLabels:{la:'<img>'}},'la')`),'<img>');
 run(`gUnit().exercises[0].questions[0].optionLabels.las='<img src=x>';`);
 assert.ok(run('gPlayerView()').includes('&lt;img src=x&gt;'));
});

test('article omission is compact, accessible and works in converted input with a mobile symbol key',()=>{
 const all=JSON.parse(fs.readFileSync('content/grammar/008_nombres_propios.json','utf8'));
 const run=context([all]);unlockUntil(run,'exercise:8.3');
 run(`gStart(COURSE.grammar[0].id,'exercise:8.3');G.at=3;`);
 assert.ok(run('gPlayerView()').includes('placeholder="Артикль или ∅"'));
 assert.ok(run('gPlayerView()').includes('data-gchar="∅"'));
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
    if(!html.includes(esc(format.instruction))||!html.includes(esc(format.example))||!html.includes('aria-describedby="g-answer-format"')) throw Error(group.id+': missing guidance');
    if(!q.gapParts&&!html.includes('placeholder="'+esc(format.placeholder)+'"')) throw Error(group.id+': missing placeholder');
    r.value=q.answers[0];
    if(!grammarCorrect(q,r.value))throw Error(group.id+': changed answer');
    r.checked=true;r.good=true;
    html=gPlayerView();
    if((gQuestionMode(q,r)==='input'&&!html.includes(esc(format.example)))||!html.includes('data-gnext'))throw Error(group.id+': guidance or manual Next disappeared');
   }
   return {typed,legacy};
  })())`));
  typed+=result.typed;legacy+=result.legacy;
 }
 assert.equal(typed,183);assert.equal(legacy,49);
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
 assert.equal(count,60);
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
