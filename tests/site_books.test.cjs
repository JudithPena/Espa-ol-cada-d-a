const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('espanol/site_template.html', 'utf8');
const code = source.slice(source.indexOf('function bookText('), source.indexOf('function bookView()'));
const ctx = { esc: s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;'})[c]) };
vm.createContext(ctx); vm.runInContext(code, ctx);
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

test('Harry chapter annotations exist independently without duplicates or overlapping spans', () => {
  const chapter = JSON.parse(fs.readFileSync('content/books/harry-potter-piedra/chapters/001.json','utf8'));
  const word = c => c != null && /[\p{L}\p{M}\p{Nd}_]/u.test(c);
  for (const block of chapter.blocks) for (const lang of ['es','ru']) {
    assert.deepEqual(block.marks?.[lang] || [], [], 'Vocabulary must belong to a lexical note');
    const spans = [];
    for (const [unit, note] of block.notes.entries()) {
      if (typeof note === 'string') continue;
      assert.equal(new Set(note[lang]).size, note[lang].length, `${block.title}: duplicate annotation`);
      for (const mark of note[lang]) {
        let found = false;
        for (let at = block[lang].indexOf(mark); at !== -1; at = block[lang].indexOf(mark,at+1)) {
          const end = at+mark.length;
          if (word(mark[0]) && at && word(block[lang][at-1]) || word(mark.at(-1)) && word(block[lang][end])) continue;
          found = true; spans.push({at,end,unit,mark});
        }
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
