// Движок уроков основного курса на сайте (espanol/site_template.html): сценарии и прежний путь.
// Run with: node --test tests/site_course.test.cjs
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');

const template = fs.readFileSync('espanol/site_template.html', 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1].replace('/*__GRAMMAR_PLAYER__*/', fs.readFileSync('espanol/grammar_player.js', 'utf8'));

// Уроки сайта тем 0–1 и 6 так, как их получает страница (без картинок: они тесту не нужны).
const site = JSON.parse(execFileSync('python3', ['-c', `
import json
from espanol.course import load_course
from espanol.site import site_data
from espanol.wordcards import load_cards
d = site_data(load_course("content/site"), load_cards("content"), units={0, 1, 6})
for L in d["lessons"]:
    for w in L["words"]:
        w.pop("img", None)
print(json.dumps({"lessons": d["lessons"], "units": d["units"], "intervals": d["intervals"]}, ensure_ascii=False))
`], {maxBuffer: 64 * 1024 * 1024}).toString());

function context(data = site, storage = new Map()) {
  const noop = () => {};
  // Любой элемент страницы — заглушка: свойства и вызовы возвращают её же (отрисовка тесту не нужна).
  const node = new Proxy(function () {}, {get: (t, k) => k === 'isConnected' ? false : typeof k === 'string' ? node : undefined, apply: () => node});
  const ctx = vm.createContext({console, setTimeout: noop, clearTimeout: noop, addEventListener: noop,
    localStorage: {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k)},
    window: {addEventListener: noop}, document: {documentElement: {classList: {toggle: noop}}, addEventListener: noop,
      getElementById: () => null, querySelector: () => node, querySelectorAll: () => [], body: {appendChild: noop}},
    matchMedia: () => ({matches: false, addEventListener: noop}), navigator: {}, speechSynthesis: {getVoices: () => [], addEventListener: noop},
  });
  vm.runInContext(script.replace('/*__DATA__*/{}', JSON.stringify({grammar: [], ...data})).replace(/render\(\);\s*$/, ''), ctx);
  const run = code => vm.runInContext(code, ctx);
  run('render = () => {}; say = () => {}; sfx = () => {}');
  return run;
}
const word = (es, ru) => ({es, ru, pron: '', emoji: '', pos: 'noun', say: es, srs: true});

test('legacy lesson keeps the old order: all words, explanation with its exercise, then practice', () => {
  const legacy = {n: 1, id: 't/legacy', unit: 1, level: 'A0', kind: 'vocab', kindLabel: 'Лексика', emoji: '📚', title: 'Legacy',
    goal: '', scripted: false, words: [word('la casa', 'дом'), word('el perro', 'собака'), word('el gato', 'кот')],
    blocks: [{t: 'text', html: 'Короткий текст.'}, {t: 'exercise', title: 'Переведите', items: [
      {q: 'дом', a: 'la casa', qp: 'дом', ap: 'la casa'}, {q: 'собака', a: 'el perro', qp: 'собака', ap: 'el perro'},
      {q: 'кот', a: 'el gato', qp: 'кот', ap: 'el gato'}]}],
    quiz: [{q: '?', options: ['a', 'b', 'c'], correct: 0, shuffle: true, explain: ''}], sentences: []};
  const run = context({lessons: [legacy], units: [{number: 1, title: 'T', level: 'A0', goals: []}], intervals: [1, 3]});
  run('startLesson(0)');
  assert.deepEqual(JSON.parse(run('JSON.stringify(S.steps.map(s => s.type + (s.mode ? ":" + s.mode : "")))')),
    ['intro', 'word', 'word', 'word', 'mc:ex', 'mc:ex', 'mc:ex', 'mc:quiz']);
});

test('scripted lesson interleaves word portions with tasks', () => {
  const run = context();
  const i = run('LESSONS.findIndex(L => L.id === "saludos/vocab1")');
  run(`startLesson(${i})`);
  const types = JSON.parse(run('JSON.stringify(S.steps.map(s => s.type))'));
  const graded = ['mc', 'write', 'match', 'sort', 'build', 'mf'];
  const firstTask = types.findIndex(t => graded.includes(t)), lastWord = types.lastIndexOf('word');
  assert.ok(types.indexOf('word') < firstTask && firstTask < lastWord, types.join(' '));
  assert.ok(!types.includes('task'), 'в сценарии нет заданий-самопроверок');
  assert.ok(types.includes('write') && types.includes('match'));
  // Каждое слово появляется карточкой до задания, где оно — верный ответ.
  const order = JSON.parse(run(`JSON.stringify(S.steps.map(s => s.type === "word" ? "W:" + s.word.es : s.type === "mc" && s.plain ? "A:" + s.plain[s.correct] : s.type === "write" ? "A:" + s.a[0] : ""))`));
  for (const w of site.lessons[i].words) {
    const card = order.indexOf('W:' + w.es), core = w.es.toLowerCase();
    const used = order.findIndex(x => x.startsWith('A:') && x.toLowerCase().includes(core));
    if (used >= 0) assert.ok(card < used, `${w.es}: карточка ${card}, задание ${used}`);
  }
  // Ошибка ведёт к ближайшему объяснению: у заданий после правила есть ссылка на экран теории.
  const refs = JSON.parse(run('JSON.stringify(S.steps.filter(s => ["mc","write"].includes(s.type) && s.mode !== "quiz").map(s => s.ref))'));
  assert.ok(refs.some(r => r >= 0));
  assert.ok(JSON.parse(run('JSON.stringify(S.steps.filter(s => s.ref >= 0).every(s => S.steps[s.ref].type === "theory"))')));
});

test('typed answers: accents soft, meaning accents and ñ strict, article and punctuation hints', () => {
  const run = context();
  const r = (a, typed, accents = 'soft') => JSON.parse(run(`JSON.stringify(writeResult(${JSON.stringify({a, accents})}, ${JSON.stringify(typed)}))`));
  assert.equal(r(['Buenos días'], '¡buenos días!').ok, true);
  assert.deepEqual(r(['Buenos días'], 'buenos dias'), {ok: true, almost: true, match: 'Buenos días'});
  assert.equal(r(['Buenos días'], 'buenos dias', 'strict').ok, false);
  assert.equal(r(['¿Y tú?'], 'y tu').ok, false);
  assert.match(r(['¿Y tú?'], 'y tu').why, /ударения меняет смысл/);
  assert.equal(r(['el año'], 'el ano').ok, false);
  assert.match(r(['el año'], 'el ano').why, /ñ/);
  assert.match(r(['la mesa'], 'el mesa').why, /артикль другой/);
  assert.match(r(['la mesa'], 'mesa').why, /Нужен артикль/);
  assert.match(r(['mesa'], 'la mesa').why, /артикль не нужен/);
  assert.equal(r(['Muchas gracias', 'Gracias'], 'GRACIAS').ok, true);
  assert.equal(r(['Perdón'], 'perdon').almost, true);
});

test('write: second attempt after a hint, answer shown after two misses, first try counted once', () => {
  const run = context();
  run('S = {kind: "review", steps: [{type: "write", a: ["la mesa"], q: "Стол", show: "la mesa"}], at: 0, firstTry: 0, graded: 0, seen: new Set(), state: {value: "", tries: 0}, pool: []}');
  run('S.state.value = "el mesa"; writeCheck()');
  assert.equal(run('S.state.result'), undefined);
  assert.match(run('S.state.why'), /артикль/);
  run('S.state.value = "la mesa"; writeCheck()');
  assert.equal(run('S.state.result'), 'good');
  assert.equal(run('S.firstTry'), 0);
  assert.equal(run('S.graded'), 1);
  assert.equal(run('S.steps.length'), 1, 'решённое со второй попытки задание не возвращается');
  run('S = {kind: "review", steps: [{type: "write", a: ["la mesa"], q: "Стол", show: "la mesa"}], at: 0, firstTry: 0, graded: 0, seen: new Set(), state: {value: "", tries: 0}, pool: []}');
  run('S.state.value = "x"; writeCheck(); S.state.value = "y"; writeCheck()');
  assert.equal(run('S.state.result'), 'bad');
  assert.equal(run('S.steps.length'), 2, 'ошибка возвращается в конце урока один раз');
});

test('match pairs by taps in any order; wrong pairs are counted; rows never line up', () => {
  const run = context();
  for (let n = 2; n <= 6; n++) {
    const order = JSON.parse(run(`JSON.stringify(matchOrder(${n}))`));
    assert.deepEqual([...order].sort(), [...Array(n).keys()]);
    assert.ok(order.every((x, k) => x !== k), `строки совпали: ${order}`);
  }
  run('S = {kind: "review", steps: [{type: "match", pairs: [["sí","да","sí",""],["no","нет","no",""],["vale","ладно","vale",""]]}], at: 0, firstTry: 0, graded: 0, seen: new Set(), pool: [], state: {left: [0,1,2], right: [1,2,0], done: [], sel: null, bad: null, err: 0}}');
  run('matchPick("l", 0); matchPick("r", 1)');
  assert.equal(run('S.state.err'), 1);
  run('matchPick("r", 0); matchPick("l", 0); matchPick("l", 1); matchPick("r", 1); matchPick("l", 2); matchPick("r", 2)');
  assert.equal(run('S.state.result'), 'bad');
  assert.equal(run('S.firstTry'), 0);
  assert.equal(run('S.steps.length'), 1);
});

test('sort places cards one by one and highlights the right group after two misses', () => {
  const run = context();
  run('S = {kind: "review", steps: [{type: "sort", groups: [["el", [["libro","libro"]]], ["la", [["mesa","mesa"]]]]}], at: 0, firstTry: 0, graded: 0, seen: new Set(), pool: [], state: {order: [[["libro","libro"],0],[["mesa","mesa"],1]], k: 0, placed: [[],[]], err: 0, here: 0}}');
  run('sortPick(1); sortPick(1)');
  assert.equal(run('S.state.hint'), 0);
  run('sortPick(0); sortPick(1)');
  assert.equal(run('S.state.result'), 'bad');
  assert.equal(run('S.state.err'), 2);
  assert.deepEqual(JSON.parse(run('JSON.stringify(S.state.placed)')), [['libro'], ['mesa']]);
});

test('build accepts every listed word order', () => {
  const run = context();
  for (const order of [['En', 'la', 'mesa', 'hay', 'un', 'libro.'], ['Hay', 'un', 'libro', 'en', 'la', 'mesa.']]) {
    run(`S = {kind: "review", steps: [{type: "build", es: "En la mesa hay un libro.", alt: ["Hay un libro en la mesa."], extra: ["el"], ru: "x"}], at: 0, firstTry: 0, graded: 0, seen: new Set(), pool: [], state: null}`);
    run('S.state = {n: 0, err: 0, miss: 0, helps: 0, here: 0, tiles: ["el", ...S.steps[0].es.split(" "), "Hay", "libro", "en", "mesa."], used: [], cands: [S.steps[0].es, ...S.steps[0].alt].map(x => x.split(" "))}');
    for (const tok of order) run(`buildPick(S.state.tiles.findIndex((t, j) => t === ${JSON.stringify(tok)} && !S.state.used[j]))`);
    assert.equal(run('S.state.result'), 'good', order.join(' '));
  }
});

test('correct option never sits in the same position three questions in a row', () => {
  const run = context();
  const steps = JSON.parse(run('JSON.stringify(balance([0,1,2,3,4,5].map(() => ({type: "mc", options: ["a","b","c"], plain: ["a","b","c"], correct: 0}))))'));
  const pos = steps.map(s => s.correct);
  for (let k = 2; k < pos.length; k++) assert.ok(!(pos[k] === pos[k - 1] && pos[k] === pos[k - 2]), pos.join());
  assert.ok(steps.every(s => s.options[s.correct] === 'a'), 'верный вариант остался верным');
});

test('finishing a scripted lesson keeps the old progress format; recall uses only done lessons', () => {
  const storage = new Map(), run = context(site, storage);
  const i = run('LESSONS.findIndex(L => L.id === "saludos/vocab1")'), j = run('LESSONS.findIndex(L => L.id === "saludos/vocab2")');
  assert.equal(run(`recallSteps(${j}).length`), 0, 'из непройденных уроков повторять нечего');
  run(`startLesson(${i}); S.firstTry = 9; S.graded = 10; finish()`);
  const P = JSON.parse(run('JSON.stringify(P)'));
  assert.equal(P.done['saludos/vocab1'].stars, 3);
  assert.ok(P.words['buenos días'] && P.words['hasta mañana']);
  const recall = JSON.parse(run(`JSON.stringify(recallSteps(${j}))`));
  assert.ok(recall.length >= 1 && recall.length <= 2 && recall.every(s => s.recall));
  run(`startLesson(${j})`);
  assert.ok(JSON.parse(run('JSON.stringify(S.steps.slice(1, 4).some(s => s.recall))')), 'в начале следующего урока — «Вспомним»');
});

test('recall never takes tasks bound to a dialogue, reading or mission; context lines play in the character voice', () => {
  const run = context();
  const i = run('LESSONS.findIndex(L => L.id === "saludos/dialogue")');
  run(`P.done[LESSONS[${i}].id] = { stars: 1 }`);
  const pool = JSON.parse(run(`JSON.stringify(recallPool(${i + 1}).map(x => x.make()).map(s => s.q || s.plain?.[s.correct] || s.a?.[0]))`));
  const ctxQs = JSON.parse(run(`JSON.stringify(LESSONS[${i}].blocks.filter(b => b.ctx).flatMap(b => b.items.map(it => it.q)))`));
  assert.ok(ctxQs.length > 0, 'в уроке есть вопросы к диалогу');
  assert.ok(pool.length > 0, 'и задания без контекста');
  for (const q of ctxQs.filter(Boolean)) assert.ok(!pool.includes(q), `«${q}» попал в «Вспомним»`);
  // Реплика-контекст: кнопка с голосом персонажа, запись ищется по ключу «@голос|текст».
  run('AUDIO["@es-ES-AlvaroNeural|¡Hola!"] = "x"');
  const html = run('chatHTML({ lines: [["Pablo", "¡Hola!", "", "¡Hola!"]], cast: { Pablo: { v: "es-ES-AlvaroNeural", a: "" } } })');
  assert.match(html, /data-voice="es-ES-AlvaroNeural"/);
  assert.equal(run('canSay("¡Hola!", "es-ES-AlvaroNeural")'), true);
  assert.equal(run('audioId("¡Hola!", "es-ES-AlvaroNeural")'), 'x');
});
