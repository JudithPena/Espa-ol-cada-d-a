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
  const book = JSON.parse(fs.readFileSync('content/books/harry_potter_01.json', 'utf8'));
  assert.equal(book.blocks.length, 29);
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
