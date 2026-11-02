// Run with: node --test tests/site_grammar.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const template = fs.readFileSync('espanol/site_template.html', 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1].replace('/*__GRAMMAR_PLAYER__*/', fs.readFileSync('espanol/grammar_player.js','utf8'));
const unit = JSON.parse(fs.readFileSync('content/grammar/001_genero.json','utf8'));
function context() {
  const noop = () => {};
  const storage = new Map();
  const ctx = vm.createContext({console, setTimeout:noop, clearTimeout:noop, addEventListener:noop,
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    window:{addEventListener:noop}, document:{addEventListener:noop,querySelector:()=>({focus:noop})},
    navigator:{}, speechSynthesis:{getVoices:()=>[],addEventListener:noop},
  });
  const data = {lessons:[],units:[],intervals:[1],grammar:[unit]};
  // Execute the production script, excluding only the initial DOM render.
  vm.runInContext(script.replace('/*__DATA__*/{}',JSON.stringify(data)).replace(/render\(\);\s*$/, ''),ctx);
  return (code) => vm.runInContext(code,ctx);
}
test('Spanish answers accept alternatives and NFC but preserve ñ and stress', () => {
 const run = context();
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[1], " JEFA ")'),true);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[14], "me\\u0301dica")'),true);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[14], "medica")'),false);
 assert.equal(run('grammarCorrect(COURSE.grammar[0].exercises[1].questions[11], "nina")'),false);
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
 run('gStart(COURSE.grammar[0].id,"exercise:1.3"); gMove(1);');
 const html=run('gPlayerView()');
 assert.equal((html.match(/id="g-answer"/g)||[]).length,1);
 assert.ok(html.includes('Кем Luis приходится Julio?'));
 assert.ok(html.includes('gperson is-active'));
 assert.ok(html.includes('Семейное дерево'));
});
