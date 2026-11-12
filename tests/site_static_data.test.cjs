// Exercise the production loader with real built JSON, failed fetches and old progress.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {context, ROOT} = require('../tools/site_vm.cjs');
const out = fs.mkdtempSync(path.join(os.tmpdir(), 'ecd-data-'));
execFileSync('python3', ['-m', 'espanol', 'site', '-o', path.join(out,'index.html')], {cwd:ROOT});
const html = fs.readFileSync(path.join(out,'index.html'),'utf8');
const shell = JSON.parse(html.split('const COURSE = ')[1].split(/;\r?\n/)[0].replaceAll('<\\/', '</'));
const json = ref => JSON.parse(fs.readFileSync(path.join(out,ref.url),'utf8'));
const catalog = json(shell.resources.books);
const tick = () => new Promise(resolve=>setImmediate(resolve));
function harness(storage=new Map(), extra={}) {
  const counts = new Map();
  const fetch = async url => {
    counts.set(url,(counts.get(url)||0)+1);
    return new Response(fs.readFileSync(path.join(out,url)),{status:200,headers:{'Content-Type':'application/json'}});
  };
  return {run:context(structuredClone(shell),storage,{render:true,fetch,...extra}), counts, storage};
}
async function drain(run) {
  do { await run('Promise.all([...dataRequests.values()])'); await tick(); } while(run('dataRequests.size'));
}
async function ready(run) { run('render()'); await drain(run); }

test('bootstrap, all level files, preserved word index, audio map and chapter hydration', async () => {
  const {run,counts}=harness();
  await ready(run);
  assert.match(run('app.innerHTML'),/Курс по уровням/);
  assert.equal(run('WORDS.size'),new Set(json(shell.resources.common).words.flat().map(w=>w.es)).size);
  assert.equal(counts.size,1,'home fetches only common metadata, never lessons or chapters');
  for (const [level,ref] of Object.entries(shell.resources.levels)) {
    await run(`dataLoad(COURSE.resources.levels[${JSON.stringify(level)}])`);
    assert.equal(run(`LESSONS.filter(L=>L._data?.url===${JSON.stringify(ref.url)}).every(L=>Array.isArray(L.blocks))`),true);
  }
  const book=catalog.find(b=>b.chapters.length>1);
  const chapter=book.chapters[0];
  run(`bookGo(${JSON.stringify(book.level)},${JSON.stringify(book.id)},${JSON.stringify(chapter.id)})`);
  await drain(run);
  assert.match(run('app.innerHTML'),/book-block/);
  assert.equal(run('bookCurrentText().blocks.length'),json(chapter._data).blocks.length);
  const requested=counts.get(chapter._data.url);
  run('render()'); await tick();
  assert.equal(counts.get(chapter._data.url),requested);
  assert.equal(counts.has(book.chapters[1]._data.url),false,'never fetch neighbouring chapter');
});

test('all grammar catalogs hydrate without changing routes, answers, attempts or progress', async () => {
  const storage=new Map([['espanol-cada-dia.v1',JSON.stringify({xp:123,done:{'old/id':{stars:2}},words:{'la casa':{s:3,due:1}},grammar:{'001_genero/1.1':{correct:7}}})],['espanol-cada-dia.grammar-session.v1','legacy-session']]);
  const before=[...storage];
  const {run}=harness(storage); await ready(run);
  const lessonsBefore=run('JSON.stringify(P)');
  for (const unit of shell.grammar) {
    const routes=run(`JSON.stringify(gRoutes(COURSE.grammar.find(u=>u.id===${JSON.stringify(unit.id)})))`);
    await run(`dataLoad(COURSE.grammar.find(u=>u.id===${JSON.stringify(unit.id)})._data)`);
    assert.equal(run(`JSON.stringify(gRoutes(COURSE.grammar.find(u=>u.id===${JSON.stringify(unit.id)})))`),routes);
    const loaded=JSON.parse(run(`JSON.stringify(COURSE.grammar.find(u=>u.id===${JSON.stringify(unit.id)}))`));
    delete loaded._data;
    assert.deepEqual(loaded,json(unit._data));
  }
  assert.equal(run('JSON.stringify(P)'),lessonsBefore);
  assert.deepEqual([...storage],before,'loader does not migrate or write user data');
});

test('network error and invalid JSON are retryable; concurrent fetches deduplicate',async()=> {
  let mode='offline',attempts=0;
  const {run}=harness(new Map(),{fetch:async url=>{
    attempts++;
    if(mode==='offline') throw new Error('network down');
    if(mode==='html') return new Response('<!doctype html>fallback',{status:200});
    if(mode==='404') return new Response('missing',{status:404});
    return new Response(fs.readFileSync(path.join(out,url)),{status:200});
  }});
  for(const failure of ['offline','html','404']) {
    mode=failure;run('render()');await tick();await tick();await tick();
    assert.match(run('app.innerHTML'),/Не удалось загрузить материал/);
    assert.equal(run('dataLoaded.size'),0);
  }
  mode='ok';run('dataRetry()'); await drain(run);
  assert.match(run('app.innerHTML'),/Курс по уровням/);
  const ref=shell.resources.levels.A0,old=attempts;
  await run('Promise.all([dataLoad(COURSE.resources.levels.A0),dataLoad(COURSE.resources.levels.A0)])');
  assert.equal(attempts,old+1);
  await run('dataLoad(COURSE.resources.levels.A0)');assert.equal(attempts,old+1);
});

test('late chapter response cannot override a newer navigation',async()=> {
  let release;
  const {run}=harness(new Map(),{fetch: async url=>{
    if(url.includes('/books/')) await new Promise(resolve=>release=resolve);
    return new Response(fs.readFileSync(path.join(out,url)),{status:200});
  }});
  await ready(run);
  const book=catalog.find(b=>b.chapters.length),ch=book.chapters[0];
  run(`bookGo(${JSON.stringify(book.level)},${JSON.stringify(book.id)},${JSON.stringify(ch.id)})`);
  while(!release) await tick();
  run('view.tab="home";render()');
  release();await drain(run);
  assert.equal(run('view.tab'),'home');assert.match(run('app.innerHTML'),/Курс по уровням/);
});

test('direct links, stories and collections retain their existing routes',async()=> {
  const {run}=harness(); await ready(run);
  const book=catalog.find(b=>b.chapters.length),chapter=book.chapters[0];
  run(`location.hash=${JSON.stringify('#books/C2/'+book.id+'/'+chapter.id)};bookSync();render()`);
  await drain(run);
  assert.equal(run('view.bookLevel'),book.level,'outdated level links keep opening the same chapter');
  assert.match(run('app.innerHTML'),/book-block/);
  for (const story of catalog.filter(b=>b.kind==='story')) {
    run(`bookGo(${JSON.stringify(story.level)},${JSON.stringify(story.id)})`);
    await drain(run);
    assert.equal(run('view.tab'),'book');assert.match(run('app.innerHTML'),/book-block/);
  }
  for (const collection of catalog.filter(b=>b.kind==='collection')) {
    run(`bookGo(${JSON.stringify(collection.level)},${JSON.stringify(collection.id)})`);
    assert.match(run('app.innerHTML'),/Рассказы сборника/);
  }
});

test('persistent content cache serves a fresh page without JSON network access',async()=> {
  const entries=new Map();
  const cache={match:async key=>entries.get(key)?.clone(),put:async(key,value)=>entries.set(key,value.clone()),
    keys:async()=>[...entries.keys()],delete:async key=>entries.delete(key)};
  const caches={open:async()=>cache};
  const first=harness(new Map(),{caches});await ready(first.run);
  const story=catalog.find(b=>b.kind==='story');
  first.run(`bookGo(${JSON.stringify(story.level)},${JSON.stringify(story.id)})`);
  await drain(first.run);
  let requests=0;
  const second=harness(new Map(),{caches,fetch:async()=>{requests++;throw new Error('offline')}});
  second.run(`bookGo(${JSON.stringify(story.level)},${JSON.stringify(story.id)})`);
  await drain(second.run);
  assert.match(second.run('app.innerHTML'),/book-block/);assert.equal(requests,0);
});

test('leaving a loading next lesson clears the previous result and cancels its callback',async()=> {
  let release;
  const {run}=harness(new Map(),{fetch:async url=>{
    if(url.includes('/levels/')) await new Promise(resolve=>release=resolve);
    return new Response(fs.readFileSync(path.join(out,url)),{status:200});
  }});
  await ready(run);
  run('S={kind:"result"};startLesson(0)');
  while(!release) await tick();
  run('dataLeave();view.tab="home";render()');
  release();await drain(run);
  assert.equal(run('S'),null);assert.equal(run('view.tab'),'home');
  assert.match(run('app.innerHTML'),/Курс по уровням/);
});

test('late audio metadata enables recorded voices even without browser speech synthesis',async()=> {
  const {run}=harness(new Map(),{fetch:async url=>{
    const value=JSON.parse(fs.readFileSync(path.join(out,url),'utf8'));
    if(url===shell.resources.common.url) value.audio={hola:'word-clip','@speaker|hola':'dialogue-clip'};
    return new Response(JSON.stringify(value),{status:200});
  }});
  assert.equal(run('SPEECH'),false);assert.equal(run('TTS.ok'),false);
  await ready(run);
  assert.equal(run('TTS.ok'),true);assert.equal(run('!!canSay("hola")'),true);
  assert.equal(run('audioId("hola","speaker")'),'dialogue-clip');
  run('say("hola")');assert.equal(run('player.src'),'a/word-clip.mp3');
});

process.on('exit',()=>fs.rmSync(out,{recursive:true,force:true}));
