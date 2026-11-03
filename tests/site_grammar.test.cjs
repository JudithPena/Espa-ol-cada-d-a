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
function context(grammar = [unit]) {
  const noop = () => {};
  const storage = new Map();
  const ctx = vm.createContext({console, setTimeout:noop, clearTimeout:noop, addEventListener:noop,
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    window:{addEventListener:noop}, document:{documentElement:{classList:{toggle:noop}},addEventListener:noop,getElementById:()=>null,querySelector:()=>({focus:noop})},
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
 assert.equal((form.match(/class="ginput"/g)||[]).length,10);
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
test('retry only failed questions improves existing group score without duplicate XP', () => {
 const run=context();
 unlockUntil(run,'exercise:1.1');
 run(`gStart(COURSE.grammar[0].id,"exercise:1.1"); gMove(1);
   while(!G.ended) { const step=G.steps[G.at], group=gGroups(gUnit()).find(g=>g.id===step.group); gResponse(step).value=step.qi===0?"wrong":group.questions[step.qi].answers[0]; gCheck(); gMove(1); }`);
 assert.equal(run('P.grammar["001_el_hijo_la_hija/1.1"].correct'),9);
 assert.equal(run('P.xp'),18);
 run('gRetry();');
 assert.equal(run('G.steps.length'),1);
 run('gResponse(G.steps[0]).value="la periodista"; gCheck(); gMove(1);');
 assert.equal(run('P.grammar["001_el_hijo_la_hija/1.1"].correct'),10);
 assert.equal(run('P.xp'),20);
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
 run(`gStart(COURSE.grammar[0].id,"section:0"); gMove(1); while(!G.ended) { gResponse(G.steps[G.at]).value="wrong";gCheck();gMove(1); }`);
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"section:1")'),true);
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"section:2")'),false);
});
test('summary reading persists and opening an old saved locked stage cannot bypass gates', () => {
 const run=context();
 unlockUntil(run,'summary');
 assert.equal(run('gRouteOpen(COURSE.grammar[0],"exercise:1.1")'),false);
 run('gStart(COURSE.grammar[0].id,"summary");gMove(1);');
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
 assert.ok(intro.includes('Ввод слова') && !intro.includes('Выбор ответа'));
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
 assert.ok(markup.includes('Amalia tiene tres ___.'));
 const alternative=unit3.sections[2].check.questions[0];
 assert.equal(run(`grammarCorrect(${JSON.stringify(alternative)},"rubís")`),true);
 assert.equal(run(`grammarCorrect(${JSON.stringify(alternative)},"rubíes")`),true);
 const accent=unit3.exercises[0].questions[13];
 assert.equal(run(`grammarCorrect(${JSON.stringify(accent)},"dias")`),false);
});
