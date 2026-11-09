from espanol.site import load_books


def test_book_chapters_have_complete_readable_blocks():
    books = load_books()
    assert books
    for book in books:
        assert book['title'] and book['author'] and book['id']
        assert book['level'] and book['vocabulary_min_level']
        for block in (block for chapter in book['chapters'] for block in chapter['blocks']):
            assert all(block[key].strip() for key in ('title', 'es', 'ru'))
            pronouns = block.get('pronouns')
            if isinstance(pronouns, str):
                assert pronouns.strip()
            else:
                assert pronouns
                for item in pronouns:
                    assert all(item[key].strip() for key in ('es', 'translation', 'explanation'))
                    assert item['es'].casefold() in block['es'].casefold()
            assert block['notes']
            for note in block['notes']:
                if isinstance(note, str):
                    assert note.strip()
                    continue
                assert note['term'].strip() and note['explanation'].strip()
                for lang in ('es', 'ru'):
                    assert note[lang] and all(mark in block[lang] for mark in note[lang])
            for lang in ('es', 'ru'):
                assert all(mark in block[lang] for mark in block.get('marks', {}).get(lang, []))


def test_first_book_includes_descriptive_b1_vocabulary():
    book = next(b for b in load_books() if b['title'] == 'Harry Potter y la piedra filosofal')
    first = book['chapters'][0]['blocks'][0]
    entries = {n['term']: n for n in first['notes'] if isinstance(n, dict)}
    for term, es, ru in [('corpulento', 'corpulento', 'крупный'),
                         ('rollizo', 'rollizo', 'полный'),
                         ('el taladro', 'taladros', 'дрели')]:
        assert es in entries[term]['es'] and es in first['es']
        assert ru in entries[term]['ru'] and ru in first['ru']


def test_pronoun_distinctions_in_first_chapter():
    book = next(b for b in load_books() if b['title'] == 'Harry Potter y la piedra filosofal')
    def entry(form):
        return next(x for chapter in book['chapters'] for block in chapter['blocks'] for x in block['pronouns'] if x['es'] == form)
    assert 'пассивной' in entry('Se supiera')['explanation']
    assert 'пассивной' in entry('Se descubría')['explanation']
    assert 'безличную' in entry('Si se la comparaba')['explanation']
    assert 'заменяет le' in entry('Explicárselo')['explanation']
    assert 'не заменяет le' in entry('Se lo pasó por los ojos')['explanation']


def test_book_vocabulary_keeps_required_government_without_extra_conjunction():
    book = next(b for b in load_books() if b['title'] == 'Harry Potter y la piedra filosofal')
    entries = [n for chapter in book['chapters'] for block in chapter['blocks'] for n in block['notes'] if isinstance(n, dict)]
    terms = {n['term'] for n in entries}
    assert 'fingir' in terms and 'fingir que' not in terms
    fingir = next(n for n in entries if n['term'] == 'fingir')
    assert fingir['es'] == ['fingía'] and 'que' in fingir['explanation']
    assert 'darse cuenta de (algo)' in terms
    assert 'referirse a (alguien / algo)' in terms
    assert 'juntarse con (alguien)' in terms


def test_catalog_groups_chapters_and_preserves_independent_levels(tmp_path):
    import json
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')
    def book(folder, ident, level, threshold):
        write(tmp_path / folder / 'book.json', {'id': ident, 'title': ident, 'author': 'Autor',
              'level': level, 'vocabulary_min_level': threshold})
    def chapter(folder, ident, number, order, status):
        write(tmp_path / folder / 'chapters' / (ident + '.json'),
              {'id': ident, 'number': number, 'order': order, 'status': status,
               'title': ident, 'blocks': [{'title': 'example'}]})
    book('first', 'first', 'B2', 'B1')
    chapter('first', 'two', 2, 2, 'published')
    chapter('first', 'one', 1, 1, 'published')
    chapter('first', 'three', 3, 3, 'draft')
    book('same', 'same', 'B2', 'B2'); chapter('same', 'one', 1, 1, 'published')
    book('other', 'other', 'A1', 'A1'); chapter('other', 'one', 1, 1, 'published')
    books = load_books(tmp_path)
    assert len(books) == 3
    assert sum(b['level'] == 'B2' for b in books) == 2
    first = next(b for b in books if b['id'] == 'first')
    assert [c['id'] for c in first['chapters']] == ['one', 'two']
    assert (first['level'], first['vocabulary_min_level']) == ('B2', 'B1')
    assert next(b for b in books if b['id'] == 'other')['vocabulary_min_level'] == 'A1'


def test_harry_level_and_vocabulary_threshold_are_independent():
    book = next(b for b in load_books() if b['id'] == 'harry-potter-piedra')
    assert book['level'] == 'B2'
    assert book['vocabulary_min_level'] == 'B1'
    assert [(c['number'], c['title']) for c in book['chapters']] == [(1, 'El niño que vivió')]


def test_local_cover_is_packaged_and_cannot_escape_book_folder(tmp_path):
    import json
    import pytest
    root = tmp_path / 'book'; root.mkdir()
    metadata = {'id': 'book', 'title': 'Book', 'author': 'Author', 'level': 'A1',
                'vocabulary_min_level': 'A1', 'cover': 'cover.png'}
    (root / 'cover.png').write_bytes(b'example')
    (root / 'book.json').write_text(json.dumps(metadata))
    assert load_books(tmp_path)[0]['cover'] == 'data:image/png;base64,ZXhhbXBsZQ=='
    metadata['cover'] = '../outside.png'
    (tmp_path / 'outside.png').write_bytes(b'example')
    (root / 'book.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError, match='обложке'):
        load_books(tmp_path)


def test_exercise_validation_accepts_alternative_answers_and_rejects_invalid(tmp_path):
    import json
    import pytest
    root = tmp_path / 'book'; (root / 'chapters').mkdir(parents=True)
    (root / 'book.json').write_text(json.dumps({'id':'book','title':'Book','author':'Author','level':'A1','vocabulary_min_level':'A1'}))
    chapter = {'id':'1','number':1,'order':1,'title':'One','status':'published','blocks':[{'title':'text'}],
               'exercises':[{'id':'ex','instruction':'Completa','questions':[{'prompt':'¿Cuál?', 'options':['3','4','5'], 'answer':[0,1]}]}]}
    path = root / 'chapters' / '1.json'
    path.write_text(json.dumps(chapter)); assert load_books(tmp_path)[0]['chapters'][0]['exercises'][0]['questions'][0]['answer'] == [0,1]
    chapter['exercises'][0]['questions'][0]['answer'] = [3]
    path.write_text(json.dumps(chapter))
    with pytest.raises(ValueError, match='вопрос или ответ'):
        load_books(tmp_path)


def test_chapter_titles_may_be_absent_and_legacy_placeholders_are_hidden(tmp_path):
    import json
    root = tmp_path / 'book'
    (root / 'chapters').mkdir(parents=True)
    (root / 'book.json').write_text(json.dumps({'id': 'book', 'title': 'Book', 'author': 'Author',
                                              'level': 'A1', 'vocabulary_min_level': 'A1'}))
    titles = [None, '', 'Sin título', 'UNTITLED', 'Без названия', 'El niño que vivió']
    for number, title in enumerate(titles, 1):
        chapter = {'id': str(number), 'number': number, 'order': number, 'status': 'published',
                   'blocks': [{'title': 'example'}]}
        if number != 1:
            chapter['title'] = title
        (root / 'chapters' / f'{number}.json').write_text(json.dumps(chapter))
    chapters = load_books(tmp_path)[0]['chapters']
    assert [c['title'] for c in chapters] == ['', '', '', '', '', 'El niño que vivió']
    assert all(c['icon'] == '📖' for c in chapters)  # Unknown, legacy content has a neutral fallback.
    chapter['icon'] = []
    (root / 'chapters' / '6.json').write_text(json.dumps(chapter))
    import pytest
    with pytest.raises(ValueError, match='иконка главы'):
        load_books(tmp_path)


def test_existing_chapters_have_persisted_thematic_icons_and_original_titles():
    import json
    from pathlib import Path
    for path in Path('content/books').glob('*/chapters/*.json'):
        chapter = json.loads(path.read_text())
        assert isinstance(chapter.get('icon'), str) and chapter['icon'].strip(), path
    books = load_books()
    lola = next(b for b in books if b['id'] == 'lola-lago-nota-falsa')
    assert len(lola['chapters']) == 19
    assert all(c['title'] == '' for c in lola['chapters'])
    assert len({c['icon'] for c in lola['chapters']}) == 19
    harry = next(b for b in books if b['id'] == 'harry-potter-piedra')
    assert harry['chapters'][0]['title'] == 'El niño que vivió'
