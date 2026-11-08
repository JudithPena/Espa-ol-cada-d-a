// Движок уроков основного курса на сайте (espanol/site_template.html): сценарии и прежний путь.
// Run with: node --test tests/site_course.test.cjs
// Чек-лист приёмки доводки A0–A1 (docs/a0_a1_fixes_plan.md) — тесты с пометкой «приёмка N».
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {ROOT, SIG_CODE, siteData, siteDataFrom, context} = require('../tools/site_vm.cjs');

// Уроки сайта так, как их получает страница (без картинок: они тесту не нужны).
const site = siteData();
const J = (run, code) => JSON.parse(run(`JSON.stringify(${code})`));
const word = (es, ru) => ({es, ru, pron: '', emoji: '', pos: 'noun', say: es, srs: true});
const idx = (run, id) => run(`LESSONS.findIndex(L => L.id === ${JSON.stringify(id)})`);
const sigs = run => J(run, 'S.steps.map(s => s.type + (s.mode ? ":" + s.mode : ""))');
// Сессия задания из теста: newSession движка с одним шагом и его начальным состоянием.
const session = (run, step, state) => run(`S = newSession({kind: "review", pool: [], steps: [${JSON.stringify(step)}]}); S.state = ${JSON.stringify(state)}`);
const sounds = run => { run('SFX = []; sfx = ok => SFX.push(ok)'); return () => J(run, 'SFX'); };

// Маленький курс: тема 0 со словами и тема 1 с уроками теста — через тот же конвейер YAML → site_data.
const BASE = {id: 'base', lessons: [{id: 'w', kind: 'vocab', vocab: ['el café — кофе', 'sí — да', 'no — нет', 'gracias — спасибо',
  'bien — хорошо', 'mal — плохо', 'regular — так себе', 'hola — привет', 'adiós — пока', 'por favor — пожалуйста', 'un — один (артикль)']}]};
const mini = (lessons, skills = {}) => siteDataFrom([BASE, {id: 'u', lessons}], skills);
const MORNING = {dialogue: {id: 'morning', title: 'Утром', lines: ['Lucía: Bien, gracias. | Хорошо, спасибо.']}};
const EVENING = {dialogue: {id: 'evening', title: 'Вечером', lines: ['Lucía: Regular. | Так себе.']}};

test('legacy lesson keeps the old order: all words, explanation with its exercise, then practice', () => {
  const legacy = {n: 1, id: 't/legacy', unit: 1, level: 'A0', kind: 'vocab', kindLabel: 'Лексика', emoji: '📚', title: 'Legacy',
    goal: '', scripted: false, words: [word('la casa', 'дом'), word('el perro', 'собака'), word('el gato', 'кот')],
    blocks: [{t: 'text', html: 'Короткий текст.'}, {t: 'exercise', title: 'Переведите', items: [
      {q: 'дом', a: 'la casa', qp: 'дом', ap: 'la casa'}, {q: 'собака', a: 'el perro', qp: 'собака', ap: 'el perro'},
      {q: 'кот', a: 'el gato', qp: 'кот', ap: 'el gato'}]}],
    quiz: [{q: '?', options: ['a', 'b', 'c'], correct: 0, shuffle: true, explain: ''}], sentences: []};
  const run = context({lessons: [legacy], units: [{number: 1, title: 'T', level: 'A0', goals: []}], intervals: [1, 3]});
  run('startLesson(0)');
  assert.deepEqual(sigs(run), ['intro', 'word', 'word', 'word', 'mc:ex', 'mc:ex', 'mc:ex', 'mc:quiz']);
});

test('scripted lesson interleaves word portions with tasks', () => {
  const run = context(site);
  const i = idx(run, 'saludos/vocab1');
  run(`startLesson(${i})`);
  const types = J(run, 'S.steps.map(s => s.type)');
  const graded = ['mc', 'write', 'match', 'sort', 'build', 'mf'];
  const firstTask = types.findIndex(t => graded.includes(t)), lastWord = types.lastIndexOf('word');
  assert.ok(types.indexOf('word') < firstTask && firstTask < lastWord, types.join(' '));
  assert.ok(!types.includes('task'), 'в сценарии нет заданий-самопроверок');
  assert.ok(types.includes('write') && types.includes('match'));
  // Каждое слово появляется карточкой до задания, где оно — верный ответ.
  const order = J(run, 'S.steps.map(s => s.type === "word" ? "W:" + s.word.es : s.type === "mc" && s.plain ? "A:" + s.plain[s.correct] : s.type === "write" ? "A:" + s.a[0] : "")');
  for (const w of site.lessons[i].words) {
    const card = order.indexOf('W:' + w.es), core = w.es.toLowerCase();
    const used = order.findIndex(x => x.startsWith('A:') && x.toLowerCase().includes(core));
    if (used >= 0) assert.ok(card < used, `${w.es}: карточка ${card}, задание ${used}`);
  }
});

test('приёмка 1, 2, 12: a scripted lesson opens with useful content — no title slide, no random recall', () => {
  const run = context(site);
  for (const L of site.lessons.filter(L => L.scripted)) {
    const i = idx(run, L.id);
    run(`P = fresh(); LESSONS.slice(0, ${i}).forEach(L => { P.done[L.id] = {stars: 3}; }); startLesson(${i})`);
    const steps = J(run, 'S.steps.map(s => ({type: s.type, recall: !!s.recall, review: !!s.review}))');
    assert.notEqual(steps[0].type, 'intro', `${L.id}: титульный слайд`);
    assert.ok(!steps.some(s => s.recall), `${L.id}: случайное «Вспомним»`);
    const firstBlock = L.blocks[0]?.t;
    if (['choose', 'write', 'match', 'sort', 'build'].includes(firstBlock)) assert.ok(['mc', 'write', 'match', 'sort', 'build'].includes(steps[0].type), `${L.id}: практика начинается с задания`);
  }
  // Шапка плеера: уровень, тема, номер, название и цель урока.
  const i = idx(run, 'presentarse/vocab');
  run(`startLesson(${i})`);
  const html = run('playerView()');
  assert.match(html, /A0 · Тема 2 · Урок \d+ · Как тебя зовут\?/);
  assert.match(html, /class="pgoal"/);
});

test('typed answers: accents soft, meaning accents and ñ strict, article and punctuation hints', () => {
  const run = context(site);
  const r = (a, typed, accents = 'soft', extra = {}) => J(run, `writeResult(${JSON.stringify({a, accents, ...extra})}, ${JSON.stringify(typed)})`);
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

test('приёмка 5: typed mistakes get a precise reason — author map first, then the nearest accepted answer', () => {
  const run = context(site);
  const why = (a, typed, extra = {}) => J(run, `writeResult(${JSON.stringify({a, accents: 'soft', ...extra})}, ${JSON.stringify(typed)}).why`);
  const coffee = ['Un café, por favor', 'Hola, un café, por favor', 'Buenos días, un café, por favor'];
  // Без авторской карты: неопределённый артикль и ударение вместе.
  assert.match(why(coffee, 'el cafe por favor'), /неопределённый артикль \(un, una\), а не el.*ударения/);
  // Авторская карта ожидаемых ошибок важнее (пояснение без ещё не пройденного правила).
  assert.deepEqual(why(coffee, 'El café, por favor', {mistakes: {'el cafe por favor': 'В готовой фразе — <b>un café</b>.'}}), {html: 'В готовой фразе — <b>un café</b>.'});
  // «Не хватает слова» не говорим, если другой допустимый ответ той же длины.
  assert.doesNotMatch(why(['Hola, buenos días', 'Buenos días'], 'buenos tardes'), /Не хватает/);
  assert.match(why(['Me llamo Lucía'], 'me llamo'), /Не хватает слова/);
  assert.match(why(['Me llamo Lucía'], 'llamo me lucía'), /порядок другой/);
  assert.match(why(['Muchas gracias'], 'muchas grasias'), /как пишется слово «grasias»/);
  run('FORMS["soy"] = "ser"; FORMS["eres"] = "ser"; WORDS.set("ser", {es: "ser", pos: "verb"})');
  assert.match(why(['Yo soy Ana'], 'yo eres ana'), /другая форма глагола/);
});

test('write: second attempt after a reason, answer shown after two misses, progressive hints', () => {
  const run = context(site);
  const step = {type: 'write', a: ['la mesa'], q: 'Стол', show: 'la mesa', key: 'k'};
  session(run, step, {value: '', tries: 0, n: 0, err: 0, miss: 0, helps: 0, here: 0});
  run('S.state.value = "el mesa"; writeCheck()');
  assert.equal(run('S.state.result'), undefined);
  assert.match(run('S.state.why'), /артикль/);
  run('S.state.value = "la mesa"; writeCheck()');
  assert.equal(run('S.state.result'), 'good');
  assert.equal(run('S.firstTry'), 0);
  assert.equal(run('S.fixed'), 1);
  assert.equal(run('S.steps.length'), 1, 'решённое со второй попытки задание не возвращается');
  session(run, step, {value: '', tries: 0, n: 0, err: 0, miss: 0, helps: 0, here: 0});
  run('S.state.value = "x"; writeCheck(); S.state.value = "y"; writeCheck()');
  assert.equal(run('S.state.result'), 'bad');
  assert.equal(run('S.steps.length'), 2, 'ошибка возвращается в конце урока один раз');
  // Подсказка: сначала число слов, потом первые буквы, потом «Показать ответ» — это не «решил сам».
  session(run, {...step, a: ['Un café, por favor']}, {value: '', tries: 0, n: 0, err: 0, miss: 0, helps: 0, here: 0});
  run('writeHint()');
  assert.match(run('writeHintHTML(S.steps[0], S.state)'), /4 слова: <span class="mask">__ ____, ___ _____/);
  run('writeHint()');
  assert.match(run('writeHintHTML(S.steps[0], S.state)'), /U_ c___, p__ f____/);
  run('S.state.value = "un café por favor"; writeCheck()');
  assert.equal(run('S.state.result'), 'helped');
  assert.equal(run('S.outcomes[0].outcome'), 'helped');
  session(run, step, {value: '', tries: 0, n: 0, err: 0, miss: 0, helps: 0, here: 0});
  run('writeGive()');
  assert.equal(run('S.state.result'), 'revealed');
});

test('приёмка 7: match pairs by taps; a self-corrected match is green, rows never line up', () => {
  const run = context(site), sfx = sounds(run);
  for (let n = 2; n <= 6; n++) {
    const order = J(run, `matchOrder(${n})`);
    assert.deepEqual([...order].sort(), [...Array(n).keys()]);
    assert.ok(order.every((x, k) => x !== k), `строки совпали: ${order}`);
  }
  session(run, {type: 'match', pairs: [['sí', 'да', 'sí', ''], ['no', 'нет', 'no', ''], ['vale', 'ладно', 'vale', '']]},
    {left: [0, 1, 2], right: [1, 2, 0], done: [], sel: null, bad: null, err: 0, miss: 0, helps: 0});
  run('matchPick("l", 0); matchPick("r", 1)');
  assert.equal(run('S.state.err'), 1);
  run('matchPick("r", 0); matchPick("l", 0); matchPick("l", 1); matchPick("r", 1); matchPick("l", 2); matchPick("r", 2)');
  assert.equal(run('S.state.result'), 'good', 'ученик сам исправил пару — итог зелёный');
  assert.equal(run('S.firstTry'), 0, 'ошибка учтена: не с первой попытки');
  assert.deepEqual(sfx().slice(-1), [true], 'звук успеха');
  assert.equal(run('S.steps.length'), 1);
  assert.match(run('stepFoot(S.steps[0])'), /class="pfoot good".*Исправлено ошибок: 1/s);
});

test('приёмка 7: sort — a highlighted group after two misses is a hint, not a solo solve', () => {
  const run = context(site);
  const step = {type: 'sort', groups: [['el', [['libro', 'libro']]], ['la', [['mesa', 'mesa']]]]};
  const state = {order: [[['libro', 'libro'], 0], [['mesa', 'mesa'], 1]], k: 0, placed: [[], []], err: 0, miss: 0, helps: 0, here: 0};
  session(run, step, state);
  run('sortPick(1); sortPick(1)');
  assert.equal(run('S.state.hint'), 0);
  run('sortPick(0); sortPick(1)');
  assert.equal(run('S.state.result'), 'helped');
  assert.deepEqual(J(run, 'S.state.placed'), [['libro'], ['mesa']]);
  session(run, step, state);
  run('sortPick(1); sortPick(0); sortPick(1)');
  assert.equal(run('S.state.result'), 'good', 'одна ошибка, исправлена сама — зелёный');
});

test('build accepts every listed word order', () => {
  const run = context(site);
  for (const order of [['En', 'la', 'mesa', 'hay', 'un', 'libro.'], ['Hay', 'un', 'libro', 'en', 'la', 'mesa.']]) {
    const step = {type: 'build', es: 'En la mesa hay un libro.', alt: ['Hay un libro en la mesa.'], extra: ['el'], ru: 'x'};
    session(run, step, null);
    run('S.state = {n: 0, err: 0, miss: 0, helps: 0, here: 0, tiles: ["el", ...S.steps[0].es.split(" "), "Hay", "libro", "en", "mesa."], used: [], cands: [S.steps[0].es, ...S.steps[0].alt].map(x => x.split(" "))}');
    for (const tok of order) run(`buildPick(S.state.tiles.findIndex((t, j) => t === ${JSON.stringify(tok)} && !S.state.used[j]))`);
    assert.equal(run('S.state.result'), 'good', order.join(' '));
  }
});

test('приёмка 6: «¡Hasta mañana, Pablo!» — one wrong tile, then a correct solo build → green with success sound', () => {
  const run = context(site), sfx = sounds(run);
  const step = {type: 'build', es: '¡Hasta mañana, Pablo!', alt: [], extra: ['luego'], ru: 'Попрощайтесь до завтра.'};
  session(run, step, null);
  run('S.state = {n: 0, err: 0, miss: 0, helps: 0, here: 0, tiles: ["hasta", "luego", "mañana,", "Pablo!"], used: [], cands: [S.steps[0].es.split(" ")]}');
  const pick = t => run(`buildPick(S.state.tiles.indexOf(${JSON.stringify(t)}))`);
  pick('hasta'); pick('luego'); pick('mañana,'); pick('Pablo!');
  assert.equal(run('S.state.result'), 'good');
  assert.deepEqual(sfx(), [true], 'один положительный звук, без звука ошибки в итоге');
  assert.equal(run('S.firstTry'), 0);
  assert.equal(run('S.outcomes[0].outcome'), 'fixed', 'исправление учтено в аналитике');
  const foot = run('stepFoot(S.steps[0])');
  assert.match(foot, /pfoot good/);
  assert.doesNotMatch(foot, /Почти|Ошибка/);
  // Подсказка — жёлтый «с подсказкой», а «Мастер фраз», открытый целиком, — «ответ показан».
  session(run, step, null);
  run('S.state = {n: 0, err: 0, miss: 0, helps: 0, here: 0, tiles: ["hasta", "luego", "mañana,", "Pablo!"], used: [], cands: [S.steps[0].es.split(" ")]}');
  run('hint()'); pick('hasta'); pick('mañana,'); pick('Pablo!');
  assert.equal(run('S.state.result'), 'helped');
  session(run, {type: 'mf', es: 'Hola Ana', ru: 'Привет, Ана'}, {n: 0, err: 0, miss: 0, helps: 0, here: 0});
  run('hint(); hint()');
  assert.equal(run('S.state.result'), 'revealed');
});

test('correct option never sits in the same position three questions in a row', () => {
  const run = context(site);
  const steps = J(run, 'balance([0,1,2,3,4,5].map(() => ({type: "mc", options: ["a","b","c"], plain: ["a","b","c"], correct: 0})))');
  const pos = steps.map(s => s.correct);
  for (let k = 2; k < pos.length; k++) assert.ok(!(pos[k] === pos[k - 1] && pos[k] === pos[k - 2]), pos.join());
  assert.ok(steps.every(s => s.options[s.correct] === 'a'), 'верный вариант остался верным');
});

test('приёмка 3, 4: a question about a dialogue shows its own source and is repeated next to it, not at the end', () => {
  const data = mini([{id: 'd', kind: 'dialogue', version: 2, goal: 'g', blocks: [
    MORNING,
    {choose: {title: 'Поняли?', source: 'morning', items: [{q: 'Как дела у Лусии утром?', options: 'Bien. | Mal. | Regular.'},
                                                         {q: 'Что она говорит?', options: 'gracias | adiós'}]}},
    EVENING,
    {choose: {title: 'Поняли?', source: 'evening', items: [{q: 'Как дела у Лусии вечером?', options: 'Regular. | Bien.'}]}},
    {choose: {title: 'Как сказать?', free: true, items: [{q: '«Хорошо»', options: 'bien | mal'}]}},
  ]}]);
  const run = context(data, new Map(), {audio: {'@es-ES-ElviraNeural|Bien, gracias.': 'a1'}});
  run('startLesson(1)');
  const steps = J(run, 'S.steps.map(s => ({type: s.type, q: s.q, src: s.src}))');
  const first = steps.findIndex(s => s.q === 'Как дела у Лусии утром?');
  run(`S.at = ${first}; S.state = null; playerView()`);
  const html = run('stepBody(S.steps[S.at])');
  assert.match(html, /Показать диалог «Утром»/);
  assert.doesNotMatch(html, /Вечером/, 'открывается свой диалог, а не соседний');
  assert.match(html, /Слушать ещё раз/);
  assert.doesNotMatch(html, /data-src-tr/, 'перевод — только после ответа');
  // Ошибка: вопрос повторяется сразу после вопросов к тому же диалогу, а не в конце урока.
  run('S.state.pick = (S.steps[S.at].correct + 1) % S.steps[S.at].options.length; answer(false, S.steps[S.at])');
  const after = J(run, 'S.steps.map(s => s.q + (s.retry ? " (повтор)" : ""))');
  assert.equal(after[first + 2], 'Как дела у Лусии утром? (повтор)', after.join(' | '));
  assert.notEqual(after[after.length - 1], 'Как дела у Лусии утром? (повтор)');
  assert.ok(J(run, `S.steps[${first + 2}].srcOpen`), 'повтор — с открытым источником');
  // Открытие источника не сбрасывает ответ.
  run('S.state.srcOpen = true');
  assert.match(run('stepBody(S.steps[S.at])'), /details class="src" data-src open/);
  assert.equal(run('S.state.result'), 'bad');
  // Самостоятельная ошибка — в конец урока.
  const free = J(run, 'S.steps.findIndex(s => s.q === "«Хорошо»")');
  run(`S.at = ${free}; S.state = null; playerView(); answer(false, S.steps[S.at])`);
  assert.equal(J(run, 'S.steps[S.steps.length - 1].q'), '«Хорошо»');
});

test('приёмка 3: hidden listening dialogue — replay is free, the transcript before answering is an explicit hint', () => {
  const data = mini([{id: 'l', kind: 'listening', version: 2, goal: 'g', blocks: [
    {dialogue: {id: 'call', hidden: true, lines: ['Lucía: Regular. | Так себе.']}},
    {choose: {source: 'call', items: [{q: 'Как дела у Лусии?', options: 'Regular. | Bien.'}]}},
  ]}]);
  const run = context(data, new Map(), {audio: {'@es-ES-ElviraNeural|Regular.': 'a1'}});
  run('startLesson(1); S.at = 1; S.state = null; playerView()');
  let html = run('stepBody(S.steps[1])');
  assert.match(html, /Показать текст \(подсказка\)/);
  assert.match(html, /hidden data-hidden-text/);
  run('S.state.peek = true; S.state.pick = S.steps[1].correct; answer(true, S.steps[1])');
  assert.equal(run('S.state.result'), 'helped');
});

test('приёмка 8: listening without any audio is never 100 % — status, alternative, deferred, retry', () => {
  const data = mini([{id: 'dict', kind: 'listening', version: 2, goal: 'g', blocks: [
    {write: {title: 'Диктант', items: [
      {say: 'sí', a: 'sí', noaudio: {q: 'Как пишется «да»?', a: 'sí'}},
      {say: 'no', a: 'no'}]}},
    {choose: {items: [{say: 'Hola.', options: 'Hola. | Adiós.'}]}},
  ]}]);
  const storage = new Map();
  let run = context(data, storage);   // нет записей и нет испанского голоса
  run('startLesson(1)');
  assert.equal(run('S.steps.length'), 3, 'задания на слух не выкидываются');
  assert.equal(run('audioOK(S.steps[0])'), false);
  run('playerView()');
  const body = run('stepBody(S.steps[0])');
  assert.match(body, /Попробовать снова/);
  assert.match(body, /Нет возможности слушать/);
  assert.doesNotMatch(run('stepBody(S.steps[2])'), /data-opt/, 'варианты без звука не показываются — угадывать нечего');
  // Всё отложено: урок не засчитан, это не 100 %.
  run('useNoAudio(); S.steps = S.steps.map(s => isListen(s) && !s.noaudioUsed ? {type: "deferred", orig: s} : s); S.steps[0] = {type: "deferred", orig: S.steps[0]}; finish()');
  assert.equal(run('S.graded'), 0);
  assert.equal(run('S.passed'), false);
  assert.equal(run('!!P.done["u/dict"]'), false);
  assert.match(run('resultView()'), /Урок не засчитан/);
  // Альтернатива автора: письменно, урок засчитан «без звука».
  run('startLesson(1); useNoAudio()');
  assert.equal(run('S.steps[0].noaudioUsed'), true);
  assert.equal(run('S.steps[0].q'), 'Как пишется «да»?');
  run('playerView(); S.state.value = "sí"; writeCheck(); next()');
  assert.equal(run('S.steps[1].type'), 'deferred', 'без альтернативы — отложено до звука');
  run('next(); finish()');
  assert.equal(run('!!P.done["u/dict"]'), true);
  assert.equal(run('P.ver["u/dict"].noaudio'), 3, 'одно задание — письменная альтернатива, два — отложены до звука');
  // «Попробовать снова»: появилась запись — задание снова на слух.
  run = context(data, new Map());
  run('startLesson(1); playerView(); AUDIO["sí"] = "x"; playClip = () => {}; retryAudio()');
  assert.equal(run('audioOK(S.steps[0])'), true);
  // Запись не загрузилась — статус «Запись не загрузилась».
  run('S.state.audio = "fail"');
  assert.match(run('stepBody(S.steps[0])'), /Запись не загрузилась/);
});

test('приёмка 8: a recording that fails to load or is blocked shows its status instead of silence', async () => {
  const data = mini([{id: 'dict', kind: 'listening', version: 2, goal: 'g', blocks: [{write: {items: [{say: 'sí', a: 'sí'}]}}]}]);
  let run = context(data, new Map(), {audio: {'sí': 'a1'}, audioFail: 'error'});
  run('startLesson(1)');
  assert.equal(run('S.state.audio'), 'fail', 'запись не загрузилась, испанского голоса нет');
  assert.match(run('stepBody(S.steps[0])'), /Запись не загрузилась[\s\S]*Попробовать снова/);
  // Нажатие ▶ (say) тоже показывает статус, а не молчит.
  run('S.state.audio = null; say("sí")');
  assert.equal(run('S.state.audio'), 'fail');
  run = context(data, new Map(), {audio: {'sí': 'a1'}, audioFail: 'block'});
  run('startLesson(1)');
  await new Promise(r => setImmediate(r));
  assert.equal(run('S.state.audio'), 'blocked');
  assert.match(run('stepBody(S.steps[0])'), /Браузер не дал включить звук/);
});

test('приёмка 9: old completions stay, but goals of an updated lesson are not confirmed until the new version', () => {
  const data = mini([
    {id: 'a', kind: 'vocab', version: 2, goal: 'здороваться', vocab: ['buenos días — доброе утро'], blocks: [{learn: ['buenos días']}, {recap: {}}]},
    {id: 'b', kind: 'vocab', goal: 'прощаться', vocab: ['hasta luego — до встречи'], blocks: [{learn: ['hasta luego']}, {recap: {}}]}]);
  const storage = new Map([['espanol-cada-dia.v1', JSON.stringify({done: {'u/a': {stars: 3, acc: 100, at: '2026-11-01'}, 'u/b': {stars: 2, acc: 80, at: '2026-11-01'}}, xp: 50})]]);
  const run = context(data, storage);
  assert.equal(run('isDone(1) && isDone(2)'), true, 'старые прохождения не стёрты');
  assert.equal(run('isOutdated(1)'), true, 'урок версии 2 пройден в версии 1');
  assert.equal(run('isCurrent(2)'), true, 'урок без изменений подтверждён');
  const panel = run('skillsPanel()');
  assert.doesNotMatch(panel, /здороваться/);
  assert.match(panel, /прощаться/);
  assert.match(panel, /1 урок обновлён/);
  assert.match(run('view.level = "A0"; courseView()'), /Урок обновлён — пройти новую версию/);
  assert.equal(run('P.xp'), 50);
  // Прохождение новой версии: P.ver, старые звёзды не теряются.
  run('startLesson(1); S.outcomes = [{outcome: "first", skill: []}]; S.firstTry = 1; finish()');
  assert.equal(run('P.ver["u/a"].v'), 2);
  assert.equal(run('P.done["u/a"].stars'), 3);
  assert.equal(run('isCurrent(1)'), true);
  // Синхронизация: объединение берёт бо́льшую версию и идемпотентно.
  const a = J(run, 'P'), b = {done: {'u/a': {stars: 3}}, ver: {'u/a': {v: 1, stars: 3}}, skills: {}, ctl: {}};
  const once = J(run, `mergeProgress(${JSON.stringify(a)}, ${JSON.stringify(b)})`);
  assert.equal(once.ver['u/a'].v, 2);
  assert.deepEqual(J(run, `mergeProgress(${JSON.stringify(once)}, ${JSON.stringify(once)})`), once);
  assert.deepEqual(J(run, `mergeProgress(${JSON.stringify(b)}, ${JSON.stringify(a)})`).ver['u/a'].v, 2);
});

test('приёмка 10: control checks — under 80 % is not a pass and shows weak topics; soft tests let you continue', () => {
  const data = mini([
    {id: 'c', kind: 'review', version: 2, check: 'control', goal: 'итог', blocks: [
      {choose: {skill: 'greet', items: [{q: '1', options: 'Hola. | Adiós.'}, {q: '2', options: 'Hola. | Adiós.'}]}},
      {choose: {skill: 'thanks', items: [{q: '3', options: 'gracias | adiós'}, {q: '4', options: 'gracias | adiós'}, {q: '5', options: 'gracias | adiós'}]}}]},
    {id: 'n', kind: 'vocab', version: 2, goal: 'g', blocks: [{choose: {free: true, items: [{q: '?', options: 'sí | no'}]}}]},
    {id: 't', kind: 'quiz', check: 'soft', quiz: [{q: '?', options: 'sí | no'}, {q: '??', options: 'sí | no'}]}],
    {greet: {title: 'приветствие', lesson: 'u/c'}, thanks: {title: 'спасибо', lesson: 'u/c'}});
  const run = context(data);
  const play = outs => { run('startLesson(1)'); run(`S.outcomes = ${JSON.stringify(outs)}; S.firstTry = S.outcomes.filter(o => o.outcome === "first").length; finish()`); };
  // 1 + 0.5 + 0 + 1 + 1 = 3.5 из 5 = 70 % — не сдан.
  play([{outcome: 'first', skill: ['greet']}, {outcome: 'fixed', skill: ['greet']}, {outcome: 'bad', skill: ['thanks']},
        {outcome: 'first', skill: ['thanks']}, {outcome: 'first', skill: ['thanks']}]);
  assert.equal(run('Math.round(S.score * 100)'), 70);
  assert.equal(run('!!P.done["u/c"]'), false);
  assert.equal(run('isOpen(2)'), false, 'следующий урок закрыт до сдачи итога');
  assert.equal(run('P.ctl["u/c"].best'), 70);
  const res = run('resultView()');
  assert.match(res, /Нужно повторить/);
  assert.match(res, /Результат 70 % — нужно 80 %/);
  assert.match(res, /спасибо — 67 %/);
  assert.match(res, /Пройти ещё раз/);
  assert.match(run('view.level = "A0"; courseView()'), /Откроется после итога/);
  // Подсказки и показанные ответы не дают сдать: 0,25 и 0.
  play([{outcome: 'helped', skill: ['greet']}, {outcome: 'revealed', skill: ['greet']}, {outcome: 'first', skill: ['thanks']},
        {outcome: 'first', skill: ['thanks']}, {outcome: 'first', skill: ['thanks']}]);
  assert.equal(run('!!P.done["u/c"]'), false);
  // 80 % и выше — сдан, следующий урок открыт.
  play([{outcome: 'first', skill: ['greet']}, {outcome: 'fixed', skill: ['greet']}, {outcome: 'first', skill: ['thanks']},
        {outcome: 'first', skill: ['thanks']}, {outcome: 'first', skill: ['thanks']}]);
  assert.equal(run('!!P.done["u/c"]'), true);
  assert.equal(run('isOpen(2)'), true);
  // Тест темы (soft) ниже порога: честно «нужно повторить», но урок засчитан.
  run('startLesson(3); S.outcomes = [{outcome: "first", skill: []}, {outcome: "bad", skill: []}]; S.firstTry = 1; finish()');
  assert.equal(run('!!P.done["u/t"]'), true);
  assert.match(run('resultView()'), /Нужно повторить/);
});

test('приёмка 11: «Повторить правило» shows the rule the task is bound to, not the nearest screen', () => {
  const data = mini([{id: 'g', kind: 'grammar', version: 2, goal: 'g', blocks: [
    {rule: {id: 'gracias', text: 'Правило про **gracias**.'}},
    {choose: {free: true, items: [{q: 'Спасибо?', options: 'gracias | adiós'}]}},
    {rule: {id: 'adios', text: 'Правило про **adiós**.'}},
    {choose: {free: true, items: [{q: 'Пока?', options: 'adiós | gracias'}, {q: 'Ещё раз спасибо?', options: 'gracias | adiós', rule: 'gracias'}]}},
    {choose: {free: true, rule: 'none', items: [{q: 'Без правила', options: 'sí | no'}]}},
  ]}]);
  const run = context(data);
  run('startLesson(1)');
  const rule = q => run(`ruleHTML(S.steps.find(s => s.q === ${JSON.stringify(q)}))`);
  assert.match(rule('Спасибо?'), /про <b>gracias<\/b>/);
  assert.match(rule('Пока?'), /про <b>adiós<\/b>/);
  assert.match(rule('Ещё раз спасибо?'), /про <b>gracias<\/b>/, 'явная ссылка на правило, а не ближайший экран');
  assert.equal(rule('Без правила'), '');
});

test('приёмка 12: constructions are repeated by schedule — intervals grow on success, errors come back sooner', () => {
  const data = mini([
    {id: 'a', kind: 'vocab', version: 2, goal: 'g', blocks: [
      MORNING,
      {choose: {source: 'morning', skill: 'greet', items: [{q: 'Как дела у Лусии?', options: 'Bien. | Mal.'}]}},
      {choose: {free: true, skill: 'greet', items: [{q: '«Привет»', options: 'hola | adiós'}, {q: '«Пока»', options: 'adiós | hola'}]}}]},
    {id: 'b', kind: 'practice', version: 2, goal: 'g', blocks: [
      {review: {skills: ['greet'], n: 2}}, {choose: {free: true, items: [{q: 'Да?', options: 'sí | no'}]}}]}],
    {greet: {title: 'приветствие', lesson: 'u/a'}});
  const run = context(data);
  run('P.done["u/a"] = {stars: 3}');
  const pool = J(run, 'skillPool().map(x => x.step.q)');
  assert.deepEqual(pool.sort(), ['«Пока»', '«Привет»'], 'вопрос к диалогу в повторение не попадает');
  // Расписание: успех — интервал растёт, ошибка — завтра, ступень вниз.
  run('updateSkills([{outcome: "first", skill: ["greet"], key: "k1"}])');
  assert.equal(run('P.skills.greet.due - dayNum()'), 1);
  run('updateSkills([{outcome: "first", skill: ["greet"], key: "k1"}])');
  assert.equal(run('P.skills.greet.due - dayNum()'), 3);
  run('updateSkills([{outcome: "first", skill: ["greet"]}])');
  assert.equal(run('P.skills.greet.due - dayNum()'), 7);
  run('updateSkills([{outcome: "bad", skill: ["greet"]}, {outcome: "revealed", skill: ["greet"]}])');
  assert.equal(run('P.skills.greet.due - dayNum()'), 1);
  assert.equal(run('P.skills.greet.s'), 2);
  // Не пора — блок review урока ничего не вставляет; пора — вставляет 1–2 самостоятельных задания.
  run('P.skills.greet.due = dayNum() + 5; startLesson(2)');
  assert.equal(run('S.steps.filter(s => s.review).length'), 0);
  run('P.skills.greet.due = dayNum(); startLesson(2)');
  const rev = J(run, 'S.steps.filter(s => s.review).map(s => s.q)');
  assert.ok(rev.length >= 1 && rev.length <= 2 && !rev.includes('Как дела у Лусии?'), rev.join());
  // «Фразы и конструкции»: навыки, которым пора.
  run('startPhraseReview()');
  assert.ok(run('S.kind') === 'review' && run('S.steps.every(s => s.review && s.src == null)'));
});

test('finishing a scripted lesson keeps the old progress format and adds the version record', () => {
  const storage = new Map(), run = context(site, storage);
  const i = idx(run, 'saludos/vocab1');
  run(`startLesson(${i}); S.firstTry = 9; S.outcomes = Array.from({length: 10}, (_, k) => ({outcome: k < 9 ? "first" : "bad", skill: []})); finish()`);
  const P = J(run, 'P');
  assert.equal(P.done['saludos/vocab1'].stars, 3);
  assert.ok(P.words['buenos días'] && P.words['hasta mañana']);
  assert.ok(P.ver['saludos/vocab1'].v >= 1);
  assert.ok(JSON.parse(storage.get('espanol-cada-dia.v1')).done['saludos/vocab1']);
});

test('context lines play in the character voice', () => {
  const run = context(site);
  run('AUDIO["@es-ES-AlvaroNeural|¡Hola!"] = "x"');
  const html = run('chatHTML({ lines: [["Pablo", "¡Hola!", "", "¡Hola!"]], cast: { Pablo: { v: "es-ES-AlvaroNeural", a: "" } } })');
  assert.match(html, /data-voice="es-ES-AlvaroNeural"/);
  assert.equal(run('canSay("¡Hola!", "es-ES-AlvaroNeural")'), true);
  assert.equal(run('audioId("¡Hola!", "es-ES-AlvaroNeural")'), 'x');
});

// Приёмка 13: у каждого перестроенного урока есть карта слайдов (docs/site_slide_maps), и её сигнатура совпадает
// с шагами, которые строит движок (node tools/site_steps.cjs <урок> --done).
test('приёмка 13: slide maps match what the engine builds', () => {
  const dir = path.join(ROOT, 'docs/site_slide_maps');
  const maps = new Map();
  for (const f of fs.readdirSync(dir).filter(f => /^\d\d_.*\.md$/.test(f))) {
    let id = null;
    for (const line of fs.readFileSync(path.join(dir, f), 'utf8').split('\n')) {
      const h = line.match(/^###? .*`([a-z_]+\/[a-z0-9_]+)`/);
      if (h) id = h[1];
      const m = line.match(/^Сигнатура: `(.+)`/);
      if (m && id) maps.set(id, m[1]);
    }
  }
  const run = context(site);
  run(SIG_CODE);
  // Тема, где перестроен хоть один урок, должна иметь карты всех своих уроков (и тесты темы тоже).
  const reworked = new Set(site.lessons.filter(L => (L.version || 1) >= 2).map(L => L.unit));
  for (const L of site.lessons.filter(L => reworked.has(L.unit))) {
    assert.ok(maps.has(L.id), `${L.id}: урок перестроенной темы без карты слайдов`);
    const i = idx(run, L.id);
    run(`P = fresh(); LESSONS.slice(0, ${i}).forEach(L => { P.done[L.id] = {stars: 3}; }); startLesson(${i})`);
    // V-вопросы на слова (recap) перемешиваются: сравниваем без порядка внутри них.
    const norm = sig => sig.replace(/V~?(×\d+)?( V~?(×\d+)?)*/g, 'V*');
    assert.equal(norm(run('signature(S.steps)')), norm(maps.get(L.id)), `${L.id}: карта и урок разошлись`);
  }
});
