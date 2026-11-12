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
  // Вторая ошибка в той же группе — повтор встаёт после первого повтора, порядок вопросов сохраняется.
  const second = J(run, 'S.steps.findIndex(s => s.q === "Что она говорит?")');
  run(`S.at = ${second}; S.state = null; playerView(); S.state.pick = (S.steps[S.at].correct + 1) % 2; answer(false, S.steps[S.at])`);
  const order = J(run, `S.steps.slice(${first}, ${first} + 4).map(s => s.q + (s.retry ? " (повтор)" : ""))`);
  assert.deepEqual(order, ['Как дела у Лусии утром?', 'Что она говорит?', 'Как дела у Лусии утром? (повтор)', 'Что она говорит? (повтор)']);
  run(`S.at = ${first}; S.state = null; playerView(); S.state.result = "bad"`);
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
  assert.match(res, /Результат 70&nbsp;% — нужно 80&nbsp;%/);   // неразрывный пробел: «%» не отрывается от числа
  assert.match(res, /спасибо — 67&nbsp;%/);
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

test('приёмка 1–7 на реальных уроках темы 01 и 02', () => {
  const run = context(site, new Map(), {audio: {}});
  run('say = () => {}');
  // 2: «Поздоровайтесь!» открывается заданием, без титульного экрана и кнопки «Начать».
  run(`startLesson(${idx(run, 'saludos/practice')})`);
  assert.equal(run('S.steps[0].type'), 'mc');
  assert.doesNotMatch(run('stepFoot(S.steps[0])'), /Начать/);
  // 1: «Как тебя зовут?» открывается разговором на вечеринке.
  run(`startLesson(${idx(run, 'presentarse/vocab')})`);
  assert.equal(run('S.steps[0].type'), 'theory');
  assert.ok(run('S.steps[0].blocks.some(b => b.t === "dialogue")'));
  // 3, 4: вопросы к двум диалогам «Утро в офисе» — каждый к своему.
  run(`startLesson(${idx(run, 'saludos/dialogue')})`);
  const at = q => run(`S.steps.findIndex(s => s.q === ${JSON.stringify(q)})`);
  const srcTitle = q => run(`LESSONS[S.li].blocks[S.steps[${at(q)}].src].title`);
  assert.equal(srcTitle('Как дела у Лусии утром?'), 'Утром');
  assert.equal(srcTitle('Как дела у Лусии вечером?'), 'Вечером');
  const i = at('Как дела у Лусии утром?');
  run(`S.at = ${i}; S.state = null; playerView()`);
  assert.match(run('stepBody(S.steps[S.at])'), /Показать диалог «Утром»/);
  run('S.state.pick = (S.steps[S.at].correct + 1) % 3; answer(false, S.steps[S.at])');
  const qs = J(run, 'S.steps.map(s => s.q)');
  assert.equal(qs.indexOf('Как дела у Лусии утром?', i + 1), i + 2, 'повтор — сразу после двух вопросов к этому диалогу');
  // 5: кофе — ясная формулировка и формат, пояснение к el cafe por favor.
  const coffee = J(run, 'S.steps.find(s => s.type === "write" && /кофе/.test(s.q))');
  assert.match(coffee.q, /Напишите по-испански: «Один кофе, пожалуйста»/);
  assert.equal(coffee.format, 'короткая фраза');
  for (const ok of ['Un café, por favor', 'Hola, un café, por favor', 'Buenos días, un café, por favor'])
    assert.equal(J(run, `writeResult(${JSON.stringify(coffee)}, ${JSON.stringify(ok)}).ok`), true, ok);
  const why = J(run, `writeResult(${JSON.stringify(coffee)}, "el cafe por favor").why`);
  assert.match(why.html, /<b>un<\/b> café: un значит «один»/);
  assert.match(why.html, /ударения/);
  // 6: «¡Hasta mañana, Pablo!» в практикуме — одна неверная плитка, потом верно → зелёный.
  run(`startLesson(${idx(run, 'saludos/practice')})`);
  const b = run('S.steps.findIndex(s => s.type === "build")');
  run(`S.at = ${b}; S.state = null; playerView(); SFX = []; sfx = ok => SFX.push(ok)`);
  const pick = t => run(`buildPick(S.state.tiles.findIndex((x, j) => !S.state.used[j] && tileKey(x) === tileKey(${JSON.stringify(t)})))`);
  pick('hasta'); pick('luego'); pick('mañana'); pick('Pablo');
  assert.equal(run('S.state.result'), 'good');
  assert.deepEqual(J(run, 'SFX'), [true]);
});

// ТЗ №1 темы 01 (U01-01, U01-05, U01-06, U01-07, U01-08): ввод и выбор на шагах, собранных из content/site/units/01_saludos.yaml.
test('тема 01: ответы на предложение, благодарность и извинение, два порядка в просьбе о кофе, подсказки Hola и tú', () => {
  const run = context(site, new Map(), {audio: {}});
  run('say = () => {}');
  const steps = id => { run(`startLesson(${idx(run, id)})`); return J(run, 'S.steps'); };
  const res = (st, typed) => J(run, `writeResult(${JSON.stringify(st)}, ${JSON.stringify(typed)})`);
  const plainQ = st => String(st.q || '').replace(/<[^>]+>/g, '');

  // U01-01: условие называет цель, ¡Hola! получает подсказку по ситуации; оба образца утра засчитываются.
  const greet = steps('saludos/vocab1').filter(s => s.type === 'write' && /Поздоровайтесь/.test(plainQ(s)));
  assert.equal(greet.length, 2);
  const [morning9, evening17] = greet;
  for (const st of greet) assert.match(plainQ(st), /по времени суток/);
  for (const ok of ['Buenos días', 'Hola, buenos días']) assert.equal(res(morning9, ok).ok, true, ok);
  for (const ok of ['Buenas tardes', 'Hola, buenas tardes']) assert.equal(res(evening17, ok).ok, true, ok);
  assert.match(res(morning9, 'Hola').why.html, /уместно.*утреннее приветствие/);
  assert.match(res(evening17, '¡Hola!').why.html, /уместно.*после обеда/);

  // U01-05: tú в заметке до ввода; без знака — подсказка про слово tú, забытый вопрос — прежняя подсказка.
  const v2 = steps('saludos/vocab2');
  const tip = J(run, 'LESSONS[S.li].blocks.find(b => b.id === "y_tu")');
  assert.match(JSON.stringify(tip), /tú.*означает «ты» и пишется со знаком ударения/);
  const tu = v2.find(s => s.type === 'write' && /¿Qué tal\?/.test(plainQ(s)));
  assert.ok(v2.findIndex(s => s.type === 'theory' && JSON.stringify(s).includes('пишется со знаком ударения')) < v2.indexOf(tu), 'заметка до ввода');
  assert.equal(res(tu, 'Bien, gracias. ¿Y tú?').ok, true);
  for (const bad of ['Bien, gracias. ¿Y tu?', 'Bien, ¿y tu?', 'Muy bien, ¿y tu?', 'Muy bien, gracias. ¿Y tu?', 'Bien, gracias, ¿y tu?']) {
    const r = res(tu, bad);
    assert.equal(r.ok, false, bad);
    assert.match(r.why.html, /<b>tú<\/b>.*знаком ударения/, bad);
  }
  assert.match(res(tu, 'Bien, gracias').why.html, /вопрос в ответ забыли/);

  // U01-08: оба порядка и приветствие засчитываются сразу и без «почти»; другое слово — вторая попытка.
  const d = steps('saludos/dialogue');
  const coffee = d.find(s => s.type === 'write' && /кофе/.test(plainQ(s)));
  assert.equal(coffee.a[0], 'Un café, por favor', 'первый образец');
  assert.ok(coffee.a.includes('Por favor, un café'), 'альтернатива «Por favor, un café» на месте');
  for (const ok of ['Por favor, un café', 'Un café, por favor', 'Hola, un café, por favor']) {
    const r = res(coffee, ok);
    assert.equal(r.ok, true, ok);
    assert.ok(!r.almost, `${ok}: без «почти»`);
  }
  run(`S.at = S.steps.findIndex(s => s.type === "write" && /кофе/.test(s.q)); S.state = null; playerView(); S.state.value = "Un vino, por favor"; writeCheck()`);
  assert.equal(run('S.state.result'), undefined, 'после первой ошибки — вторая попытка');
  assert.equal(run('S.state.tries'), 1);

  // U01-06, U01-07: morning — понятный обмен, два вопроса с ответом в репликах; lift — извинение и ответ.
  const L = J(run, 'LESSONS[S.li]');
  const src = id => L.blocks.find(b => b.t === 'dialogue' && b.id === id);
  const spoken = id => src(id).lines.map(l => l[1]).join(' ');
  assert.doesNotMatch(spoken('morning'), /Perdón|No, no/);
  assert.match(spoken('morning'), /¿Café\?.*¡Vale! ¡Muchas gracias, Pablo!.*De nada\./);
  const flat = t => t.toLowerCase().replace(/[¡!¿?.,]/g, '').trim();
  for (const id of ['morning', 'lift']) {
    const qs = d.filter(s => s.type === 'mc' && s.src != null && L.blocks[s.src].id === id);
    assert.equal(qs.length, id === 'morning' ? 2 : 1, id);
    for (const q of qs) assert.ok(flat(spoken(id)).includes(flat(q.plain[q.correct])), `${id}: «${q.plain[q.correct]}» звучит в сцене`);
  }
  assert.ok(!d.some(s => /Почему Пабло говорит/.test(plainQ(s))));
  const lift = src('lift');
  assert.equal(lift.title, 'У лифта');
  assert.deepEqual(lift.lines.map(l => [l[0], l[1]]), [['Pablo', '¡Perdón, señora López!'], ['Señora López', 'No pasa nada.']]);
  assert.notEqual(lift.cast['Señora López'].v, lift.cast.Pablo.v);
  const wNo = d.findIndex(s => s.type === 'word' && s.word.es === 'no pasa nada');
  const qLift = d.findIndex(s => s.type === 'mc' && /сеньора Лопес отвечает на извинение/.test(plainQ(s)));
  assert.ok(wNo >= 0 && wNo < qLift, 'карточка no pasa nada до первой проверки');
  assert.equal(d[qLift - 1].type, 'theory', 'вопрос сразу после сцены у лифта');
  assert.deepEqual([...d[qLift].plain].sort(), ['De nada.', 'No pasa nada.', 'Por favor.']);
  // Ошибка в вопросе к lift — повтор рядом, с открытой сценой «У лифта».
  run(`S.at = ${qLift}; S.state = null; playerView()`);
  assert.match(run('stepBody(S.steps[S.at])'), /Показать диалог «У лифта»/);
  run('S.state.pick = S.steps[S.at].plain.indexOf("De nada."); answer(false, S.steps[S.at])');
  assert.equal(run(`S.steps[${qLift + 1}].srcOpen && LESSONS[S.li].blocks[S.steps[${qLift + 1}].src].id`), 'lift');

  // Финальный ответ на ¡Perdón, Pablo!: De nada — пояснение ошибки, No pasa nada — верно.
  run(`startLesson(${idx(run, 'saludos/dialogue')})`);
  const fin = run('S.steps.findIndex(s => s.type === "mc" && JSON.stringify(s).includes("¡Perdón, Pablo!"))');
  run(`S.at = ${fin}; S.state = null; playerView(); S.state.pick = S.steps[S.at].plain.indexOf("De nada."); answer(false, S.steps[S.at])`);
  const foot = run('stepFoot(S.steps[S.at])');
  assert.match(foot, /Верно: No pasa nada\./);
  assert.match(foot, /<i>De nada<\/i> говорят в ответ на благодарность/);
  const again = run('S.steps.length - 1');
  assert.match(run(`JSON.stringify(S.steps[${again}])`), /¡Perdón, Pablo!/, 'самостоятельное задание вернулось в конце');
  run(`S.at = ${again}; S.state = null; playerView(); S.state.pick = S.steps[S.at].correct; answer(true, S.steps[S.at])`);
  assert.equal(run('S.state.result'), 'good');
  assert.equal(run('S.steps[S.at].plain[S.steps[S.at].correct]'), 'No pasa nada.');
  // Проверка Sí, por favor в ответ на предложение сохранена.
  assert.equal(run('S.steps.find(s => s.type === "mc" && JSON.stringify(s.lines || []).includes("¿Café?") && s.plain[s.correct] === "¡Sí, por favor!") != null'), true);
});

test('тема 01: старое прохождение «Утро в офисе» (версия 2) сохраняется, но просит пройти версию 3', () => {
  const storage = new Map([['espanol-cada-dia.v1', JSON.stringify({done: {'saludos/dialogue': {stars: 3, acc: 100, at: '2026-11-09'}},
    ver: {'saludos/dialogue': {v: 2}}, xp: 40,
    // Ключи заданий старой версии (удалённый вопрос, прежние условия 9:00) — в истории навыков.
    skills: {polite: {s: 1, due: 0, n: 1, ok: 1, err: 0, seen: ['saludos/dialogue|почему пабло говорит perdón']},
      greeting_time: {s: 1, due: 0, n: 1, ok: 1, err: 0, seen: ['saludos/vocab1|☀️ 9:00. вы входите в офис.']}}})]]);
  const run = context(site, storage);
  run(`startLesson(${idx(run, 'saludos/dialogue')})`);
  assert.ok(run('S.steps.length') > 10, 'урок новой версии открывается при старых ключах в истории');
  run('startPhraseReview()');
  assert.ok(run('S.steps.length') >= 1, 'повторение навыков работает со старыми ключами');
  const i = idx(run, 'saludos/dialogue');
  assert.equal(run(`LESSONS[${i}].version`), 3);
  assert.equal(run(`isDone(${i})`), true, 'старое прохождение не стёрто');
  assert.equal(run(`isOutdated(${i})`), true);
  assert.equal(run('P.done["saludos/dialogue"].stars'), 3);
  assert.equal(run('P.xp'), 40);
  assert.match(run('view.level = "A0"; courseView()'), /Урок обновлён — пройти новую версию/);
});

// ТЗ №2 темы 02 (U02-01 … U02-06): вопросы без опоры на невидимые подписи, допустимые ответы — на шагах из 02_presentarse.yaml.
test('тема 02: вопросы к разговорам по репликам, ответы миссии meet, ввод se llama, тест без двух верных вариантов', () => {
  const run = context(site, new Map(), {audio: {}});
  run('say = () => {}');
  const steps = id => { run(`startLesson(${idx(run, id)})`); return J(run, 'S.steps'); };
  const res = (st, typed) => J(run, `writeResult(${JSON.stringify(st)}, ${JSON.stringify(typed)})`);
  const plainQ = st => String(st.q || '').replace(/<[^>]+>/g, '');
  const lesson = () => J(run, 'LESSONS[S.li]');
  const opts = st => st.plain || st.options;   // у вопросов quiz варианты — в options

  // U02-05: миссия meet — «очень приятно» до и после имени; encantada и пропущенное «очень приятно» — подсказки.
  const meet = steps('presentarse/vocab').find(s => s.type === 'write' && /Ответьте: вас зовут Пабло/.test(plainQ(s)));
  for (const ok of ['Encantado, Ana. Me llamo Pablo', 'Mucho gusto. Me llamo Pablo', 'Mucho gusto, Ana. Me llamo Pablo',
    'Hola, me llamo Pablo. Encantado, Ana', 'Hola, me llamo Pablo. Mucho gusto, Ana', 'Hola, Ana. Encantado. Me llamo Pablo',
    'Hola, Ana. Mucho gusto. Me llamo Pablo', 'Me llamo Pablo. Encantado'])
    assert.equal(res(meet, ok).ok, true, ok);
  assert.equal(meet.a.length, 16);
  for (const bad of ['Encantada. Me llamo Pablo', 'Me llamo Pablo. Encantada, Ana', 'Encantada, Ana. Me llamo Pablo'])
    assert.match(res(meet, bad).why.html, /поэтому <b>encantado<\/b>/, bad);
  assert.match(res(meet, 'Me llamo Pablo').why.html, /добавьте «очень приятно»/);

  // U02-06: se llama — ввод в конце урока grammar, со своими подсказками.
  const g = steps('presentarse/grammar');
  const sl = g.find(s => s.type === 'write' && plainQ(s) === 'Её зовут Лусия.');
  assert.ok(sl && g.indexOf(sl) === g.length - 1, 'ввод se llama — последнее задание урока');
  for (const ok of ['Se llama Lucía', 'Ella se llama Lucía']) assert.equal(res(sl, ok).ok, true, ok);
  assert.match(res(sl, 'Es Lucía').why.html, /«это Лусия».*<b>se llama<\/b>/);
  assert.match(res(sl, 'Me llamo Lucía').why.html, /«меня зовут»/);
  assert.match(res(sl, 'Te llamas Lucía').why.html, /«тебя зовут»/);

  // U02-01, U02-02: в listening роли не спрашиваются, Елена на «ты», «Кто это сказал?» по звучащим репликам.
  const l = steps('presentarse/listening'), L = lesson();
  const cls = L.blocks.find(b => b.t === 'dialogue' && b.id === 'class');
  assert.match(cls.lines[0][1], /¿Cómo te llamas\?/);
  assert.doesNotMatch(cls.lines[0][1], /usted/);
  assert.ok(!l.some(s => s.type === 'match'), 'пар «Кто есть кто?» больше нет');
  const answers = JSON.stringify(l.map(s => opts(s) || s.pairs || []));
  assert.doesNotMatch(answers, /преподавательница — |ученик|ученица/);
  assert.ok(!l.some(s => /Как зовут преподавательницу/.test(plainQ(s))));
  const spoken = cls.lines.map(l => l[1]).join(' ');
  const who = (q, name, line) => {
    const st = l.find(s => s.type === 'mc' && plainQ(s) === q);
    assert.ok(st, q);
    assert.equal(opts(st)[st.correct], name, q);
    assert.equal(L.blocks[st.src].id, 'class', `${q}: source class`);
    assert.ok(spoken.includes(line), `${q}: «${line}» звучит в разговоре`);
  };
  who('Кто говорит «Encantada»?', 'Elena', 'Encantada, Iván.');
  who('Кто говорит «Mucho gusto»?', 'Olga', 'Mucho gusto.');
  who('Кто представляет Ольгу?', 'Iván', 'Es Olga.');

  // U02-03: вопрос к party — по реплике Аны, а не по русскому вступлению.
  const d = steps('presentarse/dialogue'), D = lesson();
  assert.ok(!d.some(s => /Кто такая Лусия/.test(plainQ(s))));
  const ana = d.find(s => s.type === 'mc' && plainQ(s) === 'Что Ана спрашивает о Лусии?');
  assert.equal(ana.plain[ana.correct], '¿Quién es ella?');
  assert.equal(D.blocks[ana.src].id, 'party');
  assert.match(D.blocks[ana.src].lines.map(l => l[1]).join(' '), /¿quién es ella\?/);

  // U02-04: в тесте один верный вариант «очень приятно» для Аны.
  const q = steps('presentarse/quiz').find(s => s.type === 'mc' && /очень приятно/.test(plainQ(s)));
  assert.deepEqual([...opts(q)].sort(), ['Encantada.', 'Encantado.']);
  assert.equal(opts(q)[q.correct], 'Encantada.');
});

test('тема 02: старое прохождение listening, dialogue и grammar (версия 2) сохраняется, но просит пройти версию 3', () => {
  const ids = ['presentarse/grammar', 'presentarse/dialogue', 'presentarse/listening'];
  const done = Object.fromEntries(ids.map(id => [id, {stars: 3, acc: 100, at: '2026-11-09'}]));
  const ver = Object.fromEntries(ids.map(id => [id, {v: 2}]));
  const run = context(site, new Map([['espanol-cada-dia.v1', JSON.stringify({done, ver, xp: 60})]]));
  for (const id of ids) {
    const i = idx(run, id);
    assert.equal(run(`LESSONS[${i}].version`), 3, id);
    assert.equal(run(`isDone(${i}) && isOutdated(${i})`), true, id);
    assert.equal(run(`P.done[${JSON.stringify(id)}].stars`), 3, id);
  }
  assert.equal(run(`isCurrent(${idx(run, 'presentarse/vocab')})`), false, 'vocab не пройден — и не отмечен');
  assert.equal(run('P.xp'), 60);
  assert.match(run('view.level = "A0"; courseView()'), /Урок обновлён — пройти новую версию/);
});

// ТЗ №3 (U03-01, U03-02, U03-04, U03-05, U01-02, U01-03): шаги из 03_en_clase.yaml и saludos/vocab1.
test('тема 03 и saludos/vocab1: вопрос о слове mochila, ответы про сыр, ввод в тесте темы, приветствия без подсказки', () => {
  const run = context(site, new Map(), {audio: {}});
  run('say = () => {}');
  const steps = id => { run(`startLesson(${idx(run, id)})`); return J(run, 'S.steps'); };
  const res = (st, typed) => J(run, `writeResult(${JSON.stringify(st)}, ${JSON.stringify(typed)})`);
  const plainQ = st => String(st.q || '').replace(/<[^>]+>/g, '');
  const opts = st => st.plain || st.options || [];
  const line = st => (st.lines || []).map(l => l[1]).join(' ');
  const offTopic = ['Muy bien, gracias.', 'No, gracias.', 'De nada.', '¿Cómo te llamas?'];

  // U03-01: вопрос о значении незнакомого mochila; неверные варианты — из той же функции.
  const d = steps('en_clase/dialogue');
  assert.ok(!d.some(s => /tarea/.test(plainQ(s))), 'нет условия про tarea');
  const moch = d.find(s => s.type === 'mc' && /mochila/.test(plainQ(s)));
  assert.equal(opts(moch)[moch.correct], 'Perdón, ¿qué significa «mochila»?');
  const malaga = d.find(s => s.type === 'mc' && /Málaga/.test(line(s)));
  assert.equal(opts(malaga)[malaga.correct], '¿Cómo se escribe?');
  assert.match(malaga.explain, /спрашивают о значении/);

  // U03-02, U03-04: миссия school.
  const pr = steps('en_clase/practice');
  const again = pr.find(s => s.type === 'mc' && /Попросите повторить/.test(plainQ(s)));
  assert.equal(opts(again)[again.correct], 'Otra vez, por favor.');
  for (const st of [moch, malaga, again]) for (const bad of offTopic) assert.ok(!opts(st).includes(bad), `${plainQ(st)}: ${bad}`);
  const cheese = pr.find(s => s.type === 'write' && /сыр/.test(plainQ(s)));
  assert.ok(!cheese.format, 'без требования «с артиклем»');
  for (const ok of ['el queso', 'queso', 'Se dice queso', 'Se dice «queso»']) assert.equal(res(cheese, ok).ok, true, ok);
  assert.equal(res(cheese, 'la queso').ok, false);

  // U03-05: ввод в тесте темы — с подсказками и в подсчёте результата.
  const qz = steps('en_clase/quiz');
  const w = qz.find(s => s.type === 'write');
  assert.ok(w && /Скажите об этом и попросите повторить/.test(plainQ(w)));
  for (const ok of ['No entiendo. Otra vez, por favor', 'Otra vez, por favor. No entiendo']) assert.equal(res(w, ok).ok, true, ok);
  assert.match(res(w, 'No entiendo').why.html, /Добавьте просьбу повторить/);
  assert.match(res(w, 'No entiendo. Más despacio, por favor').why.html, /«Ещё раз» — <b>otra vez<\/b>/);
  assert.equal(run('S.check'), 'soft');
  assert.equal(run('S.steps.filter(isGraded).some(s => s.type === "write")'), true, 'ввод — оцениваемое задание теста');
  const wi = qz.indexOf(w);
  run(`S.at = ${wi}; S.state = null; playerView(); S.state.value = "No entiendo. Otra vez, por favor"; writeCheck()`);
  assert.equal(run('S.graded'), 1);
  assert.equal(run('S.outcomes[0].key'), w.key);
  assert.equal(run('S.outcomes[0].outcome'), 'first');

  // U01-02, U01-03: оцениваемое время — 11:00; реплика Пабло не подсказывает ответ.
  const v1 = steps('saludos/vocab1');
  assert.ok(!v1.some(s => /13:30/.test(plainQ(s))));
  const eleven = v1.find(s => s.type === 'mc' && /^11:00/.test(plainQ(s)));
  assert.equal(opts(eleven)[eleven.correct], '¡Buenos días!');
  const night = v1.find(s => s.type === 'mc' && /^23:00\. Пабло/.test(plainQ(s)));
  assert.equal(line(night), '¡Hola, Lucía!');
  assert.doesNotMatch(line(night), /noches/i);
  assert.equal(opts(night)[night.correct], '¡Buenas noches, Pablo!');
});

test('тема 03: старое прохождение dialogue, practice и quiz (версия 2) сохраняется, но просит пройти версию 3', () => {
  const ids = ['en_clase/dialogue', 'en_clase/practice', 'en_clase/quiz'];
  const done = Object.fromEntries(ids.map(id => [id, {stars: 3, acc: 100, at: '2026-11-10'}]));
  const ver = Object.fromEntries(ids.map(id => [id, {v: 2}]));
  const run = context(site, new Map([['espanol-cada-dia.v1', JSON.stringify({done, ver, xp: 70})]]));
  for (const id of ids) {
    const i = idx(run, id);
    assert.equal(run(`LESSONS[${i}].version`), 3, id);
    assert.equal(run(`isDone(${i}) && isOutdated(${i})`), true, id);
    assert.equal(run(`P.done[${JSON.stringify(id)}].stars`), 3, id);
  }
  assert.equal(run('P.xp'), 70);
  assert.match(run('view.level = "A0"; courseView()'), /Урок обновлён — пройти новую версию/);
});

test('приёмка 8 на реальных уроках: numeros/dictado и hora/escucha без звука не засчитываются пустыми, с альтернативой — «без звука»', () => {
  for (const id of ['numeros/dictado', 'hora/escucha']) {
    const run = context(site);   // нет записей и испанского голоса
    const i = idx(run, id);
    run(`startLesson(${i})`);
    const listen = run('S.steps.filter(isListen).length');
    assert.ok(listen >= 5, `${id}: задания на слух на месте (${listen})`);
    assert.equal(run('audioOK(S.steps.find(isListen))'), false);
    // Ученик ничего не слышит и уходит из каждого задания «на потом»: не 100 %, урок не засчитан.
    run('S.steps = S.steps.map(s => isListen(s) ? {type: "deferred", orig: s} : s); finish()');
    assert.equal(run('S.graded'), 0, id);
    assert.equal(run(`!!P.done[${JSON.stringify(id)}]`), false, `${id}: пустой урок не засчитан`);
    // «Нет возможности слушать»: у каждого задания — письменная альтернатива, урок засчитан «без звука».
    run(`startLesson(${i}); S.noAudio = true`);
    for (let k = 0; k < 40 && run('S.kind') !== 'result'; k++) {
      run('enterStep(); playerView()');
      const t = run('S.steps[S.at].type');
      assert.notEqual(t, 'deferred', `${id}: задание без альтернативы`);
      if (t === 'write') run('S.state.value = S.steps[S.at].a[0]; writeCheck(); next()');
      else if (t === 'mc') run('S.state.pick = S.steps[S.at].correct; answer(true, S.steps[S.at]); next()');
      else run('next()');
    }
    assert.equal(run(`!!P.done[${JSON.stringify(id)}]`), true, id);
    assert.equal(run(`P.ver[${JSON.stringify(id)}].noaudio`), listen, `${id}: пометка «без звука»`);
  }
});

test('приёмка 10 на реальных итогах: familia/repaso и final/examen — контроль с порогом и слабыми темами', () => {
  for (const id of ['familia/repaso', 'final/examen']) {
    const run = context(site);
    const i = idx(run, id);
    assert.equal(run(`LESSONS[${i}].check`), 'control', `${id}: нет check: control`);
    assert.equal(run(`LESSONS[${i}].scripted`), true, `${id}: итог открывается сразу заданием, без титульного слайда`);
    run(`P.openAll = false; LESSONS.slice(0, ${i}).forEach(L => { P.done[L.id] = {stars: 3}; }); startLesson(${i})`);
    const graded = J(run, 'S.steps.filter(isGraded)');
    assert.ok(graded.length >= 8, `${id}: оцениваемых заданий ${graded.length}`);
    assert.ok(graded.every(s => s.skill.length), `${id}: у каждого задания итога есть навык`);
    // Половина ответов — с ошибкой: не сдан, следующий урок закрыт, слабые темы со ссылками на уроки.
    run('S.outcomes = S.steps.filter(isGraded).map((s, k) => ({outcome: k % 2 ? "bad" : "first", skill: s.skill})); S.firstTry = Math.ceil(S.outcomes.length / 2); finish()');
    assert.equal(run(`!!P.done[${JSON.stringify(id)}]`), false);
    assert.equal(run(`isOpen(${i + 1})`), false, 'следующий урок закрыт до сдачи итога');
    const res = run('resultView()');
    assert.match(res, /Нужно повторить/);
    assert.match(res, /data-lesson="\d+" data-free>Урок \d+/);
    // Почти всё с первой попытки, одна ошибка исправлена самим — сдан.
    run(`startLesson(${i}); S.outcomes = S.steps.filter(isGraded).map((s, k) => ({outcome: k === 0 ? "fixed" : "first", skill: s.skill})); finish()`);
    assert.equal(run(`!!P.done[${JSON.stringify(id)}]`), true);
    assert.equal(run(`isOpen(${i + 1})`), true);
  }
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
