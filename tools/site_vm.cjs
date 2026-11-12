// Движок страницы курса (espanol/site_template.html) в node:vm без браузера — для тестов и инструментов.
// siteData(units) — данные уроков так, как их получает страница (без картинок); context(data) — функция run(code).
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const template = fs.readFileSync(path.join(ROOT, 'espanol/site_template.html'), 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1]
  .replace('/*__GRAMMAR_PLAYER__*/', fs.readFileSync(path.join(ROOT, 'espanol/grammar_player.js'), 'utf8'));

function siteData(units = null) {
  const spec = units ? `{${[...units].join(', ')}}` : 'None';
  return JSON.parse(execFileSync('python3', ['-c', `
import json
from espanol.course import load_course
from espanol.site import site_data
from espanol.wordcards import load_cards
d = site_data(load_course("content/site"), load_cards("content"), units=${spec})
for L in d["lessons"]:
    for w in L["words"]:
        w.pop("img", None)
print(json.dumps({k: d[k] for k in ("lessons", "units", "intervals", "skills", "forms") if k in d}, ensure_ascii=False))
`], {cwd: ROOT, maxBuffer: 256 * 1024 * 1024}).toString());
}

// Маленький курс сайта из описания (темы как в YAML) — через тот же конвейер, что и настоящий: load_course → site_data.
function siteDataFrom(units, skills = {}) {
  const os = require('node:os');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'site-course-'));
  fs.mkdirSync(path.join(dir, 'units'));
  fs.writeFileSync(path.join(dir, 'course.yaml'), JSON.stringify({title: 't', names: {female: ['Ana', 'Lucía'], male: ['Pablo']}}));
  fs.writeFileSync(path.join(dir, 'skills.yaml'), JSON.stringify(skills));
  units.forEach((u, k) => fs.writeFileSync(path.join(dir, 'units', `${String(k).padStart(2, '0')}_${u.id}.yaml`), JSON.stringify({number: k, level: 'A0', title: u.id, ...u})));
  const out = execFileSync('python3', ['-c', `
import json, sys
from espanol.course import load_course
from espanol.site import site_data
d = site_data(load_course(sys.argv[1]), {})
print(json.dumps({k: d[k] for k in ("lessons", "units", "intervals", "skills")}, ensure_ascii=False))
`, dir], {cwd: ROOT, maxBuffer: 64 * 1024 * 1024}).toString();
  fs.rmSync(dir, {recursive: true, force: true});
  return JSON.parse(out);
}

// opts.speech — есть ли испанский голос телефона; opts.audio — карта записей COURSE.audio.
function context(data, storage = new Map(), opts = {}) {
  const noop = () => {};
  // Любой элемент страницы — заглушка: свойства и вызовы возвращают её же (отрисовка тесту не нужна).
  const node = new Proxy(function () {}, {get: (t, k) => k === 'isConnected' ? false : typeof k === 'string' ? node : undefined, apply: () => node});
  const voices = opts.speech ? [{lang: 'es-ES', name: 'test'}] : [];
  const appNode = {innerHTML: ''};
  const sandbox = {console, AbortController, ...(opts.fetch ? {fetch: opts.fetch} : {}), ...(opts.caches ? {caches: opts.caches} : {}), setTimeout: noop, clearTimeout: noop, addEventListener: noop,
    localStorage: {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k)},
    window: {addEventListener: noop, scrollTo: noop}, document: {documentElement: {classList: {toggle: noop}}, addEventListener: noop,
      getElementById: () => null, querySelector: sel => sel === '#app' ? appNode : node, querySelectorAll: () => [], body: {appendChild: noop}},
    matchMedia: () => ({matches: false, addEventListener: noop}), navigator: {},
    location: {hostname: 'localhost'},
  };
  // Испанский голос телефона есть, только если opts.speech: тогда window.speechSynthesis отдаёт голос es-ES.
  sandbox.speechSynthesis = {getVoices: () => voices, addEventListener: noop, speak: noop, cancel: noop};
  if (opts.speech) sandbox.window.speechSynthesis = sandbox.speechSynthesis;
  sandbox.SpeechSynthesisUtterance = function (t) { this.text = t; };
  // Плеер записей: opts.audioFail — "error" (запись не загрузилась) или "block" (браузер не дал включить звук).
  sandbox.Audio = function () {
    this.paused = true;
    this.play = () => {
      if (opts.audioFail === 'error') { this.onerror?.(); return Promise.resolve(); }
      if (opts.audioFail === 'block') return Promise.reject(Object.assign(new Error('blocked'), {name: 'NotAllowedError'}));
      this.paused = false; return Promise.resolve();
    };
    this.pause = () => { this.paused = true; };
  };
  const ctx = vm.createContext(sandbox);
  const course = {grammar: [], ...data, ...(opts.audio ? {audio: opts.audio} : {})};
  vm.runInContext(script.replace('/*__DATA__*/{}', JSON.stringify(course)).replace(/render\(\);\s*$/, ''), ctx);
  const run = code => vm.runInContext(code, ctx);
  // Отрисовка без DOM: только playerView (он заводит состояние шага), как render() в браузере.
  // opts.audio — проверяем и сам звук, иначе say отключён.
  if (!opts.render) run(`render = () => { if (S && S.kind !== "result" && S.steps?.[S.at]) playerView(); }; sfx = () => {}; ${opts.audio ? '' : 'say = () => {};'}`);
  return run;
}

// Сигнатура шагов урока для карт слайдов (docs/site_slide_maps/README.md): T(блоки) — экран объяснения, W — карточка
// слова, C — выбор, I — ввод, M — пары, S — группы, B — сборка фразы, F — «Мастер фраз», Q — тест, V — вопрос на слово;
// O — письмо по признакам (compose); HB / HI / HC / HO — ход разговора (chat) сборкой, вводом, выбором, письмом, HL — лента разговора;
// @id — источник задания, ~ — на слух, R: — повторение, ×N — N шагов подряд.
// Шаг повторения (блок review) — просто «R»: его задание выбирается из навыков, которым пора, и меняется от раза к разу.
const SIG_CODE = `function stepSig(st) {
  if (st.recall || st.review) return "R";
  const pre = "";
  const src = st.src != null ? "@" + (LESSONS[st.li]?.blocks[st.src]?.id || st.src) : "";
  const ear = st.say ? "~" : "";
  if (st.type === "chatlog") return "HL";
  if (st.chat) return "H" + ({ build: "B", write: "I", mc: "C", compose: "O" })[st.type];
  switch (st.type) {
    case "compose": return "O" + src;
    case "intro": return "intro";
    case "theory": return "T(" + st.blocks.map(b => b.t).join("+") + ")";
    case "word": return "W";
    case "write": return pre + "I" + ear + src;
    case "match": return pre + "M";
    case "sort": return pre + "S";
    case "build": return pre + "B";
    case "mf": return pre + "F";
    case "mc": return pre + (st.mode === "quiz" ? "Q" : st.mode === "choose" ? "C" : "V") + ear + src;
  }
  return st.type;
}
function signature(steps) {
  const out = [];
  for (const t of steps.map(stepSig)) { const l = out[out.length - 1]; if (l && l[0] === t) l[1]++; else out.push([t, 1]); }
  return out.map(([t, n]) => n > 1 ? t + "×" + n : t).join(" ");
}`;

module.exports = {ROOT, SIG_CODE, script, siteData, siteDataFrom, context};
