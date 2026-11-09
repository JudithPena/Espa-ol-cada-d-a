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
