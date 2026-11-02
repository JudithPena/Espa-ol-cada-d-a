// Run with: node --test tests/site_grammar.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const template = fs.readFileSync('espanol/site_template.html', 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1];
const unit = JSON.parse(fs.readFileSync('content/grammar/001_genero.json','utf8'));
function context() {
  const noop = () => {};
  const ctx = vm.createContext({console, setTimeout:noop, clearTimeout:noop, addEventListener:noop,
    localStorage:{getItem:()=>null,setItem:noop},
    window:{addEventListener:noop}, document:{addEventListener:noop,querySelector:()=>({})},
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
 assert.equal((tree.match(/class="gperson"/g)||[]).length,10);
 for(const name of ['Luis','Ana','Julio','Lucía','Gabriel','Laura','Blanca','Pedro','Raúl','Silvia']) {
   assert.ok(tree.includes(`<figcaption>${name}</figcaption>`));
 }
 const form = run('grammarForm(COURSE.grammar[0], COURSE.grammar[0].exercises[2])');
 assert.ok(form.indexOf('Часть 1 · Родственники Julio') < form.indexOf('1. Кем Luis приходится Julio?'));
 assert.ok(form.indexOf('Часть 2 · Родственники Silvia') < form.indexOf('6. Кем Luis приходится Silvia?'));
 assert.equal((form.match(/class="ginput"/g)||[]).length,10);
});
