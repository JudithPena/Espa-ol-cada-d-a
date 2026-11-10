const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('espanol/site_template.html', 'utf8');
const code = source.slice(source.indexOf('function bookText('), source.indexOf('function bookView()'));
const ctx = { esc: s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;'})[c]) };
vm.createContext(ctx); vm.runInContext(code, ctx);
vm.runInContext(source.slice(source.indexOf("function bookChapterLabel("), source.indexOf("function bookChaptersView(")), ctx);
test('all whole-word occurrences and multiple marks are highlighted', () => {
  assert.equal(ctx.bookText('gato, gato y gatos; corazón.', ['gato','corazón']), '<strong>gato</strong>, <strong>gato</strong> y gatos; <strong>corazón</strong>.');
  assert.equal(ctx.bookText('vacaciones¹ y casas2', ['vacaciones', 'casas']), '<strong>vacaciones</strong>¹ y casas2');
});
test('overlaps choose the longest at a given position and remain unnested', () => {
  assert.equal(ctx.bookText('se dio cuenta de algo', ['se dio', 'se dio cuenta de', 'cuenta']), '<strong>se dio cuenta de</strong> algo');
});
test('markup in original, marks and structured notes is escaped', () => {
  assert.equal(ctx.bookText('<b>gato</b>', ['gato']), '&lt;b&gt;<strong>gato</strong>&lt;/b&gt;');
  assert.equal(ctx.bookNote({term:'<img>', explanation:'& unsafe'}), '<strong>&lt;img&gt;</strong> — &amp; unsafe');
  assert.equal(ctx.bookNote('<b>legacy</b>'), '&lt;b&gt;legacy&lt;/b&gt;');
});
test('structured notes and legacy marks coexist', () => {
  assert.deepEqual(Array.from(ctx.bookMarks({marks:{es:['gato']}, notes:['legacy', {es:['perro'], ru:['собака']}]}, 'es')), ['gato','perro']);
});
test('chapter vocabulary marks all appear in the rendered source and translation', () => {
  const book = JSON.parse(fs.readFileSync('content/books/harry-potter-piedra/chapters/001.json', 'utf8'));
  assert.equal(book.blocks.length, 32);
  for (const block of book.blocks) for (const lang of ['es', 'ru']) {
    const html = ctx.bookText(block[lang], ctx.bookMarks(block, lang));
    for (const note of block.notes) if (typeof note !== 'string') {
      for (const mark of note[lang]) assert.ok(html.includes(`<strong>${ctx.esc(mark)}</strong>`), `${block.title} ${lang}: ${mark}`);
    }
  }
});
test('pronoun entries render separately and escape all untrusted fields', () => {
  const html = ctx.bookPronouns([{es: '<se>', translation: '<перевод>', base: '<base>', explanation: '<script>'},
                                {es: 'lo', translation: 'его', explanation: 'прямое дополнение'}]);
  assert.equal((html.match(/class="book-pronoun-item"/g) || []).length, 2);
  for (const unsafe of ['<se>', '<перевод>', '<base>', '<script>']) assert.ok(!html.includes(unsafe));
  assert.match(html, /<strong lang="es">&lt;se&gt;<\/strong>/);
});
test('legacy string pronoun explanations remain safely readable', () => {
  assert.equal(ctx.bookPronouns('lo — <слово>'), '<p>lo — &lt;слово&gt;</p>');
  assert.equal(ctx.bookPronouns(null), '');
});


test('each book block has its own closed pronoun disclosure without an exclusive group', () => {
  const viewCode = source.slice(source.indexOf('function bookView()'), source.indexOf('function courseView()'));
  const book = JSON.parse(fs.readFileSync('content/books/harry-potter-piedra/chapters/001.json', 'utf8'));
  ctx.COURSE = {books: [{id: 'hp', title: 'Harry', chapters: [book]}]}; ctx.view = {book: 'hp', bookChapter: book.id}; ctx.bookById = id => ctx.COURSE.books.find(b => b.id === id);
  vm.runInContext(viewCode, ctx);
  const html = ctx.bookView();
  const tags = html.match(/<details class="book-pronouns"[^>]*>/g) || [];
  assert.equal(tags.length, book.blocks.length);
  for (const tag of tags) { assert.doesNotMatch(tag, /\b(?:name|open)\s*(?:=|>|\s)/); }
});

test('catalog groups books by level and chapters by book, including empty levels', () => {
  const catalogSource = source.slice(source.indexOf('function booksView()'), source.indexOf('function bookText('));
  const chapters = [{id:'1', number:1, title:'Первый'}, {id:'2', number:2, title:'Второй'}];
  const cat = {esc:ctx.esc, plural: (n,one,few,many) => n === 1 ? one : n < 5 ? few : many,
    view:{bookLevel:'B2', book:'first'}, COURSE:{books:[
      {id:'first',title:'Книга',author:'Автор',level:'B2',vocabulary_min_level:'B1',chapters},
      {id:'second',title:'Другая',author:'Автор',level:'B2',vocabulary_min_level:'B2',chapters:[]},
      {id:'third',title:'Лёгкая',author:'Автор',level:'A1',vocabulary_min_level:'A1',chapters:[]} ]}};
  vm.createContext(cat); vm.runInContext(catalogSource, cat);
  assert.equal((cat.booksView().match(/data-book-level=/g) || []).length, 6);
  assert.equal((cat.bookLevelView().match(/data-book-id=/g) || []).length, 2);
  assert.equal((cat.bookChaptersView().match(/data-book-chapter=/g) || []).length, 2);
  cat.view.bookLevel='A1'; assert.equal((cat.bookLevelView().match(/data-book-id=/g) || []).length, 1);
  cat.view.bookLevel='C2'; assert.match(cat.bookLevelView(), /На этом уровне пока нет книг/);
  cat.location = {hash:'#books/B2/first/2'}; assert.equal(cat.bookSync(), true);
  assert.equal(cat.view.tab, 'book'); assert.equal(cat.view.bookChapter, '2');
  cat.location.hash = '#books/B2/first/draft'; cat.bookSync();
  assert.equal(cat.view.tab, 'book-chapters');
});

test('published book vocabulary renders every selected form', () => {
  for (const folder of fs.readdirSync('content/books', {withFileTypes:true}).filter(x => x.isDirectory())) {
    const dir = `content/books/${folder.name}/chapters`;
    if (!fs.existsSync(dir)) continue;
    for (const file of fs.readdirSync(dir).filter(x => x.endsWith('.json'))) {
      const chapter = JSON.parse(fs.readFileSync(`${dir}/${file}`, 'utf8'));
      if (chapter.status !== 'published') continue;
      for (const block of chapter.blocks) for (const lang of ['es','ru']) {
        const html = ctx.bookText(block[lang], ctx.bookMarks(block, lang));
        for (const note of block.notes) if (typeof note !== 'string') for (const mark of note[lang])
          assert.ok(html.includes(`<strong>${ctx.esc(mark)}</strong>`), `${folder.name}/${file}: ${block.title} ${lang}: ${mark}`);
      }
    }
  }
});

test('book exercises render escaped questions and selectable options', () => {
  const html = ctx.bookExercises({exercises:[{id:'test', instruction:'<instruction>', questions:[{prompt:'¿<qué>?', options:['<uno>','dos'],answer:0}]}]});
  assert.match(html, /&lt;instruction&gt;/); assert.match(html, /&lt;uno&gt;/);
  assert.doesNotMatch(html, /<instruction>|<uno>/);
  assert.equal((html.match(/data-book-choice=/g) || []).length, 2);
  assert.equal(ctx.bookExercises({}), '');
});

test('precise book highlights keep independent neighbours and variable arguments separate', () => {
  const render = (es, notes) => ctx.bookText(es, ctx.bookMarks({notes}, 'es'));
  assert.equal(render('fabricaba taladros con un bigote inmenso', [
    {term:'fabricar',es:['fabricaba']},{term:'el taladro',es:['taladros']},
    {term:'el bigote',es:['bigote']},{term:'inmenso',es:['inmenso']}
  ]), '<strong>fabricaba</strong> <strong>taladros</strong> con un <strong>bigote</strong> <strong>inmenso</strong>');
  assert.equal(render('se dio cuenta de su error', [{term:'darse cuenta de (algo)',es:['se dio cuenta de']}]),
    '<strong>se dio cuenta de</strong> su error');
  assert.equal(render('no estaban para tales tonterías', [{term:'no estar para (algo)',es:['no estaban para']}]),
    '<strong>no estaban para</strong> tales tonterías');
  assert.equal(render('volvió a gritar. Al llegar a casa', [{term:'volver a (infinitivo)',es:['volvió a']},{term:'al + infinitivo',es:['Al llegar']}]),
    '<strong>volvió a</strong> gritar. <strong>Al llegar</strong> a casa');
  assert.equal(render('taladros y taladros; taladrosos', [{term:'el taladro',es:['taladros']}]),
    '<strong>taladros</strong> y <strong>taladros</strong>; taladrosos');
  assert.equal(render('apartó los taladros de su mente', [{term:'apartar (algo) de la mente',es:['apartó','de su mente']}]),
    '<strong>apartó</strong> los taladros <strong>de su mente</strong>');
});

test('all published book annotations exist without duplicates or overlapping spans', () => {
  const chapters = fs.readdirSync('content/books', {withFileTypes:true}).filter(x=>x.isDirectory()).flatMap(folder=>{
    const dir = `content/books/${folder.name}/chapters`;
    return fs.existsSync(dir) ? fs.readdirSync(dir).filter(x=>x.endsWith('.json')).map(file=>JSON.parse(fs.readFileSync(`${dir}/${file}`,'utf8'))).filter(c=>c.status==='published') : [];
  });
  const word = c => c != null && /[\p{L}\p{M}\p{Nd}_]/u.test(c);
  for (const chapter of chapters) for (const block of chapter.blocks) for (const lang of ['es','ru']) {
    assert.deepEqual(block.marks?.[lang] || [], [], 'Vocabulary must belong to a lexical note');
    const spans = [];
    for (const [unit, note] of block.notes.entries()) {
      if (typeof note === 'string') continue;
      assert.equal(new Set(note[lang]).size, note[lang].length, `${block.title}: duplicate annotation`);
      for (const mark of note[lang]) {
        let found = false, occurrence = 0;
        const selected = note.occurrences?.[lang]?.[mark];
        const seen = [];
        for (let at = block[lang].indexOf(mark); at !== -1; at = block[lang].indexOf(mark,at+1)) {
          const end = at+mark.length;
          if (word(mark[0]) && at && word(block[lang][at-1]) || word(mark.at(-1)) && word(block[lang][end])) continue;
          const index = occurrence++;
          if (selected && !selected.includes(index)) continue;
          seen.push(index);
          found = true; spans.push({at,end,unit,mark});
        }
        if (selected) assert.deepEqual([...new Set(selected)].sort((a,b)=>a-b),seen, `${block.title}: invalid occurrence selection`);
        assert.ok(found, `${block.title}: ${lang} missing ${note.term}: ${mark}`);
      }
    }
    spans.sort((a,b)=>a.at-b.at || b.end-a.end);
    for (let i=1;i<spans.length;i++) assert.ok(spans[i].at >= spans[i-1].end,
      `${block.title}: ${lang} conflicting notes ${JSON.stringify(spans.slice(i-1,i+1))}`);
  }
});

test('Harry vocabulary retains reviewed minimal boundaries for the actual reading', () => {
  const {blocks} = JSON.parse(fs.readFileSync('content/books/harry-potter-piedra/chapters/001.json','utf8'));
  const first = blocks[0], note = term => first.notes.find(n=>n.term===term);
  assert.deepEqual(note('no estar para (algo)').es,['no estaban para']);
  assert.deepEqual(note('estar orgulloso de (algo / alguien)').es,['estaban orgullosos de']);
  assert.deepEqual(note('el doble de').es,['el doble de']);
  const html = ctx.bookText(first.es,ctx.bookMarks(first,'es'));
  assert.match(html, /<strong>fabricaba<\/strong> <strong>taladros<\/strong>/);
  assert.match(html, /<strong>bigote<\/strong> <strong>inmenso<\/strong>/);
  assert.match(html, /<strong>no estaban para<\/strong> tales tonterías/);
  assert.doesNotMatch(html, /<strong>[^<]*tales tonterías/);
});

test('Lola doler and dormir highlight only the studied verb forms', () => {
  for (const file of ['001','004','013']) {
    const {blocks} = JSON.parse(fs.readFileSync(`content/books/lola-lago-nota-falsa/chapters/${file}.json`,'utf8'));
    for (const block of blocks) for (const note of block.notes.filter(n=>n.term==='doler')) {
      assert.deepEqual(note.es,['duele']);
      assert.deepEqual(note.ru,['болит']);
      const html = ctx.bookText(block.es,ctx.bookMarks(block,'es'));
      assert.match(html, /<strong>duele<\/strong>/);
      assert.doesNotMatch(html, /<strong>[^<]*duele[^<]*muela<\/strong>/);
    }
  }
  const {blocks} = JSON.parse(fs.readFileSync('content/books/lola-lago-nota-falsa/chapters/001.json','utf8'));
  assert.deepEqual(blocks[0].notes.find(n=>n.term==='dormir').es,['ha dormido']);
  const html = ctx.bookText(blocks[0].es,ctx.bookMarks(blocks[0],'es'));
  assert.match(html, /Le <strong>duele<\/strong> una muela/);
  assert.match(html, /<strong>ha dormido<\/strong> muy mal/);
});

test('a separated preposition belongs only to the selected occurrence', () => {
  const block = {es:'Hablan en casa. Confían el uno en el otro.', notes:[
    {term:'confiar en (alguien)',es:['Confían','en'],occurrences:{es:{en:[1]}}}
  ]};
  assert.equal(ctx.bookText(block.es,ctx.bookMarks(block,'es')),
    'Hablan en casa. <strong>Confían</strong> el uno <strong>en</strong> el otro.');
  assert.equal(ctx.bookText('<en> en', [{text:'en',occurrences:[1]}]),'&lt;en&gt; <strong>en</strong>');
});

test('chapters with exercises open on analysis and keep both panels mounted', () => {
  const viewCode = source.slice(source.indexOf('function bookView()'), source.indexOf('function courseView()'));
  const chapter = JSON.parse(fs.readFileSync('content/books/lola-lago-nota-falsa/chapters/001.json','utf8'));
  ctx.COURSE = {books:[{id:'lola',title:'Book',chapters:[chapter]}]};
  ctx.view = {book:'lola',bookChapter:chapter.id};
  ctx.bookById = id=>ctx.COURSE.books.find(b=>b.id===id);
  vm.runInContext(viewCode,ctx);
  const html = ctx.bookView();
  assert.match(html,/role="tablist"/);
  assert.match(html,/aria-selected="true" data-book-panel-tab="analysis"/);
  assert.match(html,/aria-selected="false" tabindex="-1" data-book-panel-tab="exercises"/);
  assert.match(html,/id="book-panel-exercises"[^>]* hidden>/);
  assert.match(html,/data-book-progress[^>]*>Выполнено: 0 из 4/);
  assert.match(html,/data-book-check disabled/);
  assert.match(html,/data-book-choice-status/);
  chapter.exercises = [];
  const empty = ctx.bookView();
  assert.doesNotMatch(empty,/role="tablist"|id="book-panel-exercises"|data-book-check/);
  assert.match(empty,/class="vseg book-block"/);
});

test('chapter labels omit missing titles and technical placeholders without inventing names', () => {
  for (const title of [undefined, null, '', '  ', 'Sin título', 'sin titulo', ' UNTITLED ', 'Без названия', 'No title', '—'])
    assert.equal(ctx.bookChapterLabel({number:3,title}), 'Глава 3');
  assert.equal(ctx.bookChapterLabel({number:1,title:'El niño que vivió'}),'Глава 1. El niño que vivió');
});

test('reading parts are numbered in order independently of author chapter numbers', () => {
  const viewCode = source.slice(source.indexOf('function bookView()'), source.indexOf('function courseView()'));
  const chapter = JSON.parse(fs.readFileSync('content/books/lola-lago-vacaciones-al-sol/chapters/001.json', 'utf8'));
  const context = {esc:ctx.esc, view:{book:'vacaciones',bookChapter:'1'},
    bookById:() => ({title:'Lola Lago - Vacaciones al sol',chapters:[chapter]}),
    bookChapterLabel:ctx.bookChapterLabel, bookTitle:ctx.bookTitle, bookOriginal:ctx.bookOriginal, bookText:ctx.bookText,
    bookMarks:ctx.bookMarks, bookNote:ctx.bookNote, bookPronouns:ctx.bookPronouns};
  vm.createContext(context); vm.runInContext(viewCode, context);
  const html = context.bookView();
  assert.deepEqual([...html.matchAll(/class="book-part">([^<]+)<\/span>/g)].map(m=>m[1]),
    ['Часть 1 из 3', 'Часть 2 из 3', 'Часть 3 из 3']);
  assert.match(html, /Lola Lago - Vacaciones al sol · Глава 1<\/p>/);
  assert.doesNotMatch(html, /role="tablist"|Sin título|Untitled/);
  assert.equal((html.match(/<summary>Перевод<\/summary>/g) || []).length, 3);
  assert.equal((html.match(/<details class="book-pronouns">/g) || []).length, 1);
  chapter.number = 2;
  assert.match(context.bookView(), /Глава 2<\/p>/);
  assert.match(context.bookView(), /Часть 1 из 3/);
});

test('chapter cards use stable individual icons and escape labels and icon text', () => {
  const catalog = source.slice(source.indexOf('function booksView()'),source.indexOf('function bookText('));
  const context = {esc:ctx.esc, view:{book:'test'}, COURSE:{books:[{id:'test',title:'Test',author:'Author',level:'A1',chapters:[
    {id:'one',number:1,title:'Sin título',icon:'☀️'},
    {id:'two',number:2,title:'<img>',icon:'<svg>'},
    {id:'three',number:3,title:''}
  ]}]}};
  vm.createContext(context); vm.runInContext(catalog,context);
  const html = context.bookChaptersView();
  assert.match(html, /aria-hidden="true">☀️<\/span>/);
  assert.match(html, />Глава 1<\/b>/);
  assert.match(html, />Глава 2\. &lt;img&gt;<\/b>/);
  assert.match(html, /aria-hidden="true">&lt;svg&gt;<\/span>/);
  assert.match(html, /aria-hidden="true">📖<\/span>/);
  assert.doesNotMatch(html, /Sin título|<img>|<svg>|Глава 3\./);
});

test('series numbers appear in titles without changing unnumbered books', () => {
  assert.equal(ctx.bookTitle({title:'Vacaciones al sol',series:{number:1}}), '1. Vacaciones al sol');
  assert.equal(ctx.bookTitle({title:'Una nota falsa',series:{number:2}}), '2. Una nota falsa');
  assert.equal(ctx.bookTitle({title:'Other book'}), 'Other book');
  const catalog = source.slice(source.indexOf('function booksView()'), source.indexOf('function bookText('));
  const context = {esc:ctx.esc, view:{bookLevel:'A2',book:'nota'},
    COURSE:{books:[{id:'nota',title:'Una nota falsa',author:'Author',level:'A2',chapters:[{id:'7',number:7,title:''}],
      series:{id:'lola',title:'Lola Lago, detective',number:2}}]},
    plural:(n,one)=>one};
  vm.createContext(context); vm.runInContext(catalog,context);
  assert.match(context.bookLevelView(), />2\. Una nota falsa<\/b>/);
  assert.match(context.bookLevelView(), /Lola Lago, detective/);
  assert.match(context.bookChaptersView(), /<h2>2\. Una nota falsa<\/h2>/);
  context.bookRoute(['books','A1','nota','7']);
  assert.equal(context.view.tab,'book');
  assert.equal(context.view.bookLevel,'A2');
  assert.equal(context.view.bookChapter,'7');
  assert.equal(context.bookHash(),'#books/A2/nota/7');
});

test('book text preserves single dialogue line breaks and real paragraph breaks', () => {
  const text = 'Un párrafo.\n\n— ¿Dónde estás?\n— Estoy aquí.\nDice, sonriendo.\n— Entonces ven conmigo.\n\nOtra escena.';
  assert.equal(ctx.bookText(text,['aquí']), text.replace('aquí','<strong>aquí</strong>'));
  assert.match(source,/\.book-block p\s*\{[^}]*white-space:\s*pre-line/);
  const chapter = JSON.parse(fs.readFileSync('content/books/lola-lago-nota-falsa/chapters/001.json','utf8'));
  const html = ctx.bookText(chapter.blocks[3].es,ctx.bookMarks(chapter.blocks[3],'es'));
  assert.match(html,/–¿Y…\? –pregunta Lola\.\n–Que/);
  assert.doesNotMatch(html,/–¿Y…\? –pregunta Lola\.\n\n–Que/);
  assert.match(html,/\n\nLola cierra la puerta/);
});

test('story without chapters opens straight from its card and shows no chapter label', () => {
  const catalogSource = source.slice(source.indexOf('function booksView()'), source.indexOf('function bookText('));
  const viewCode = source.slice(source.indexOf('function bookView()'), source.indexOf('function courseView()'));
  const story = JSON.parse(fs.readFileSync('content/books/los-tres-cerditos/story.json', 'utf8'));
  const meta = JSON.parse(fs.readFileSync('content/books/los-tres-cerditos/book.json', 'utf8'));
  const cat = {esc:ctx.esc, plural:(n,one,few,many) => n === 1 ? one : n < 5 ? few : many,
    bookText:ctx.bookText, bookOriginal:ctx.bookOriginal, bookMarks:ctx.bookMarks, bookNote:ctx.bookNote, bookPronouns:ctx.bookPronouns, bookExercises:() => '',
    view:{bookLevel:'A2'}, COURSE:{books:[{...meta, chapters:[], story}]}};
  vm.createContext(cat); vm.runInContext(catalogSource + viewCode, cat);
  const card = cat.bookLevelView();
  assert.match(card, /data-book-id="los-tres-cerditos"/); assert.match(card, /рассказ/); assert.match(card, /🐷/);
  assert.doesNotMatch(card, /глав/);
  cat.location = {hash:'#books/A2/los-tres-cerditos'}; assert.equal(cat.bookSync(), true);
  assert.equal(cat.view.tab, 'book'); assert.equal(cat.view.bookChapter, null);
  const html = cat.bookView();
  assert.doesNotMatch(html, /Глава/); assert.match(html, /data-book-nav="level"/); assert.match(html, /Los tres cerditos y el Lobo · Cuento popular/);
  assert.equal((html.match(/class="vseg book-block"/g) || []).length, story.blocks.length);
  assert.equal((html.match(/<details class="book-pronouns">/g) || []).length, story.blocks.length);
  assert.equal((html.match(/class="book-figure"/g) || []).length, 5);
  assert.equal(cat.bookHash(), '#books/A2/los-tres-cerditos');
});

test('story vocabulary renders every selected form', () => {
  const story = JSON.parse(fs.readFileSync('content/books/los-tres-cerditos/story.json', 'utf8'));
  for (const block of story.blocks) for (const lang of ['es','ru']) {
    const html = ctx.bookText(block[lang], ctx.bookMarks(block, lang));
    for (const note of block.notes) if (typeof note !== 'string') for (const mark of note[lang])
      assert.ok(html.includes(`<strong>${ctx.esc(mark)}</strong>`), `${block.title} ${lang}: ${mark}`);
  }
});

test('block illustrations are placed before their line and keep highlights intact', () => {
  const block = {es: 'Había **una** vez.\n\nYa vez.\nY sopló.', notes: [{term:'vez', es:['vez'], ru:[]}],
    images: [{src:'data:image/webp;base64,AA', alt:'<top>'}, {src:'data:image/webp;base64,BB', alt:'sopla', before:'Y sopló.'}]};
  const html = ctx.bookOriginal(block);
  assert.ok(html.startsWith('<figure class="book-figure"><img src="data:image/webp;base64,AA" alt="&lt;top&gt;"'));
  assert.match(html, /Ya <strong>vez<\/strong>\.<\/p><figure class="book-figure"><img src="data:image\/webp;base64,BB" alt="sopla" loading="lazy"><\/figure><p lang="es">Y sopló\.<\/p>$/);
  assert.equal((html.match(/<strong>vez<\/strong>/g) || []).length, 2);
  assert.equal(ctx.bookOriginal({es:'Texto', notes:[]}), '<p lang="es">Texto</p>');
});
