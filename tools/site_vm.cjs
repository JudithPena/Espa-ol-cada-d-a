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
print(json.dumps({k: d[k] for k in ("lessons", "units", "intervals", "skills") if k in d}, ensure_ascii=False))
`], {cwd: ROOT, maxBuffer: 256 * 1024 * 1024}).toString());
}

// opts.speech — есть ли испанский голос телефона; opts.audio — карта записей COURSE.audio.
function context(data, storage = new Map(), opts = {}) {
  const noop = () => {};
  // Любой элемент страницы — заглушка: свойства и вызовы возвращают её же (отрисовка тесту не нужна).
  const node = new Proxy(function () {}, {get: (t, k) => k === 'isConnected' ? false : typeof k === 'string' ? node : undefined, apply: () => node});
  const voices = opts.speech ? [{lang: 'es-ES', name: 'test'}] : [];
  const sandbox = {console, setTimeout: noop, clearTimeout: noop, addEventListener: noop,
    localStorage: {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v), removeItem: k => storage.delete(k)},
    window: {addEventListener: noop}, document: {documentElement: {classList: {toggle: noop}}, addEventListener: noop,
      getElementById: () => null, querySelector: () => node, querySelectorAll: () => [], body: {appendChild: noop}},
    matchMedia: () => ({matches: false, addEventListener: noop}), navigator: {},
    location: {hostname: 'localhost'},
  };
  // Испанский голос телефона есть, только если opts.speech: тогда window.speechSynthesis отдаёт голос es-ES.
  sandbox.speechSynthesis = {getVoices: () => voices, addEventListener: noop, speak: noop, cancel: noop};
  if (opts.speech) sandbox.window.speechSynthesis = sandbox.speechSynthesis;
  sandbox.SpeechSynthesisUtterance = function (t) { this.text = t; };
  const ctx = vm.createContext(sandbox);
  const course = {grammar: [], ...data, ...(opts.audio ? {audio: opts.audio} : {})};
  vm.runInContext(script.replace('/*__DATA__*/{}', JSON.stringify(course)).replace(/render\(\);\s*$/, ''), ctx);
  const run = code => vm.runInContext(code, ctx);
  run('render = () => {}; say = () => {}; sfx = () => {}');
  return run;
}

module.exports = {ROOT, script, siteData, context};
