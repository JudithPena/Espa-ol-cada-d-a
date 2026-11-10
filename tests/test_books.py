from espanol.site import load_books


def test_vacaciones_first_chapter_matches_supplied_pdf_and_catalog():
    import hashlib
    import re

    books = [b for b in load_books() if b['id'] == 'lola-lago-vacaciones-al-sol']
    assert len(books) == 1
    book = books[0]
    assert book['title'] == 'Lola Lago - Vacaciones al sol'
    assert (book['level'], book['vocabulary_min_level']) == ('A1', 'A1')
    assert len(book['chapters']) == 23
    chapter = book['chapters'][0]
    assert (chapter['id'], chapter['number'], chapter['order'], chapter['title']) == ('1', 1, 1, '')
    # Hash of the entire first chapter, independently extracted from PDF page 3.
    # Only whitespace and the presentation of footnote numerals are normalized.
    original = ' '.join(b['es'] for b in chapter['blocks']).replace('¹', '1').replace('²', '2')
    original = re.sub(r'\s+', ' ', original).strip()
    assert hashlib.sha256(original.encode()).hexdigest() == 'b5ab6727ae69fbdcb8abd4ce82fbe021d942a496ff563cc677351ede8e8a8a2e'
    terms = [n['term'] for b in chapter['blocks'] for n in b['notes']]
    assert len(terms) == len(set(terms))
    # Elementary A0 course words are deliberately not re-taught.
    assert not {'la oficina', 'la mujer', 'pequeño', 'el amigo', 'la mesa', 'el año', 'la palabra', 'muy', 'pero'} & set(terms)
    assert chapter['blocks'][0]['pronouns'] == chapter['blocks'][2]['pronouns'] == []
    assert 'pasiva refleja' in chapter['blocks'][1]['pronouns'][0]['explanation']
    for block in chapter['blocks']:
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[–—][^\n]*\n\n[–—]', block[lang])


def test_vacaciones_complete_source_order_and_learning_progress():
    import hashlib
    import json
    import re
    import unicodedata
    from pathlib import Path

    book = next(b for b in load_books() if b['id'] == 'lola-lago-vacaciones-al-sol')
    signatures = json.loads(Path('tests/data/vacaciones_source_signatures.json').read_text(encoding='utf-8'))
    assert [c['number'] for c in book['chapters']] == list(range(1, 24))
    assert [c['order'] for c in book['chapters']] == list(range(1, 24))
    assert all(c['title'] == '' for c in book['chapters'])
    assert len({c['icon'] for c in book['chapters']}) == 23
    learned = set()
    for chapter in book['chapters']:
        source = ' '.join(b['es'] for b in chapter['blocks'])
        source = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', source)).strip()
        assert hashlib.sha256(source.encode()).hexdigest() == signatures[chapter['id']]['sha256']
        for block in chapter['blocks']:
            for note in block['notes']:
                if isinstance(note, dict):
                    assert note['term'] not in learned, (chapter['number'], note['term'])
                    learned.add(note['term'])
            for lang in ('es', 'ru'):
                assert not re.search(r'(?m)^[–—][^\n]*\n\n[–—]', block[lang])
    assert {'la oficina', 'la mesa', 'el médico', 'el abogado', 'trabajar', 'estudiar', 'el año'}.isdisjoint(learned)
    assert sum(len(b.get('images', [])) for c in book['chapters'] for b in c['blocks']) == 3
    assert book['chapters'][-1]['blocks'][-1]['es'].endswith('–No me llames «nena».')


def test_lola_series_levels_illustrations_and_all_original_exercise_groups():
    books = {b['id']: b for b in load_books()}
    vacaciones = books['lola-lago-vacaciones-al-sol']
    nota = books['lola-lago-nota-falsa']
    assert [(b['series']['number'], b['level'], b['vocabulary_min_level']) for b in (vacaciones, nota)] == [
        (1, 'A1', 'A1'), (2, 'A2', 'A1')]
    for book, chapters in ((vacaciones, [8, 15, 21]), (nota, [2, 9, 17])):
        assert [c['number'] for c in book['chapters'] if any(b.get('images') for b in c['blocks'])] == chapters
        assert sum(len(b.get('images', [])) for c in book['chapters'] for b in c['blocks']) == 3
    exercises = [(c['number'], e) for c in vacaciones['chapters'] for e in c.get('exercises', [])]
    assert [(n, len(e['questions'])) for n, e in exercises] == [
        (2, 6), (3, 9), (5, 7), (8, 3), (9, 12), (12, 9),
        (14, 7), (14, 6), (14, 1), (15, 2), (17, 8), (18, 5), (19, 6), (23, 6)]
    assert {p for _, e in exercises for p in e['source']['pdf_pages']} == set(range(40, 47))
    assert all(n == max(e['source']['chapters']) for n, e in exercises)
    questions = [q for _, e in exercises for q in e['questions']]
    assert sum(q.get('kind') == 'reflection' for q in questions) == 10
    for q in questions:
        if q.get('kind') != 'reflection':
            assert len(q['options']) == len(set(q['options']))
    ambiguous = vacaciones['chapters'][2]['exercises'][0]['questions'][6]
    assert ambiguous['options'][ambiguous['answer']] == 'No se dice en el texto'
    beach = vacaciones['chapters'][17]['exercises'][0]['questions'][4]
    assert beach['options'][beach['answer']] == 'No se dice en el texto'


def test_book_series_rejects_invalid_and_duplicate_numbers(tmp_path):
    import json
    import pytest
    base = {'id':'first','title':'First','author':'Author','level':'A1','vocabulary_min_level':'A1',
            'series':{'id':'lola','title':'Lola Lago','number':1}}
    first = tmp_path / 'first'; first.mkdir()
    path = first / 'book.json'
    for invalid in (0, -1, True, '1', None):
        base['series']['number'] = invalid
        path.write_text(json.dumps(base), encoding='utf-8')
        with pytest.raises(ValueError, match='у серии'):
            load_books(tmp_path)
    base['series']['number'] = 2
    path.write_text(json.dumps(base), encoding='utf-8')
    second = tmp_path / 'second'; second.mkdir()
    base['id'] = 'second'; base['series']['number'] = 1
    (second / 'book.json').write_text(json.dumps(base), encoding='utf-8')
    assert [b['id'] for b in load_books(tmp_path)] == ['second', 'first']
    base['series']['number'] = 2
    (second / 'book.json').write_text(json.dumps(base), encoding='utf-8')
    with pytest.raises(ValueError, match='повторный номер'):
        load_books(tmp_path)


def test_library_covers_are_distinct_and_lola_titles_use_the_same_format():
    import hashlib
    import json
    from pathlib import Path
    from PIL import Image

    digests = set()
    for metadata_path in Path('content/books').glob('*/book.json'):
        book = json.loads(metadata_path.read_text(encoding='utf-8'))
        cover = metadata_path.parent / book['cover']
        assert cover.is_file(), metadata_path
        with Image.open(cover) as image:
            assert image.width >= 768 and image.height >= 1152
            assert image.width * 3 == image.height * 2
            image.verify()
        digest = hashlib.sha256(cover.read_bytes()).digest()
        assert digest not in digests, metadata_path
        digests.add(digest)
        if book.get('series', {}).get('id') == 'lola-lago-detective':
            assert book['title'].startswith('Lola Lago - ')
            assert book['title'].count('Lola Lago') == 1


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
                # Пустой список — в блоке нет конструкций с местоимениями, спойлер не показывается.
                assert isinstance(pronouns, list)
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
    assert [(c['number'], c['title']) for c in book['chapters']] == [(1, 'El niño que vivió'), (2, 'El vidrio que se desvaneció')]


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


def test_lola_dialogue_turns_are_compact_in_both_languages():
    import re
    lola = next(b for b in load_books() if b['id'] == 'lola-lago-nota-falsa')
    for chapter in lola['chapters']:
        for block in chapter['blocks']:
            for lang in ('es', 'ru'):
                # An actual change of scene may deserve a paragraph; none of Lola's
                # reviewed adjacent turns here has one. Narration boundaries remain legal.
                assert not re.search(r'(?m)^[ \t]*[—–][^\n]*\n[ \t]*\n[ \t]*[—–]', block[lang]), (chapter['number'], block['title'], lang)
    first = lola['chapters'][0]['blocks']
    assert '–¿Y…? –pregunta Lola.\n–Que va a venir' in first[3]['es']
    assert '— И?.. — спрашивает Лола.\n— Говорит, придёт' in first[3]['ru']
    assert '\n\nLola tiene una agencia' in first[0]['es']
    assert '\n\nУ Лолы есть агентство' in first[0]['ru']
    assert '\n\nPaco y Miguel son' in first[2]['es']
    assert '\n\nПако и Мигель — замечательные' in first[2]['ru']


def test_harry_dialogue_preserves_real_paragraphs_and_joins_page_continuations():
    blocks = next(b for b in load_books() if b['id'] == 'harry-potter-piedra')['chapters'][0]['blocks']
    assert '\n\n' not in blocks[19]['es']  # Continuous lemon-sweet conversation.
    assert '\n\n' not in blocks[19]['ru']
    assert 'Voldemort apareció' in blocks[22]['es']
    assert 'Sus tíos podrán' in blocks[24]['es']
    # Independent description and the later farewell still have their own paragraphs.
    assert '\n\n' in blocks[0]['es'] and '\n\n' in blocks[0]['ru']
    assert '\n\n—Bueno' in blocks[29]['es']
    assert '\n\n— Ну вот' in blocks[29]['ru']


def test_harry_second_chapter_contains_the_complete_supplied_source_in_order():
    import hashlib
    import re
    book = next(b for b in load_books() if b['id'] == 'harry-potter-piedra')
    chapter = next(c for c in book['chapters'] if c['number'] == 2)
    assert (chapter['id'], chapter['order'], chapter['title']) == ('2', 2, 'El vidrio que se desvaneció')
    assert chapter['icon'] == '🎂'
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in chapter['blocks'])).strip()
    # Canonical text independently extracted from the supplied PDF, printed pp. 12–20.
    # Page counters/headings removed, wrapped lines and discretionary hyphenation joined.
    assert len(original.split()) == 3527
    assert hashlib.sha256(original.encode()).hexdigest() == 'dd5be8eee949baadd9ba6780de96e3113a4aaf890b4ec3c9f8279f535ecb375b'
    assert original.startswith('Habían pasado aproximadamente diez años')
    assert original.endswith('estar en contra de la banda de Dudley.')
    assert len(chapter['blocks']) == 26
    assert all(len(b['es'].split()) >= 60 for b in chapter['blocks'])
    # Longer scenes stay whole: the guardianship discussion, the motorcycle dispute,
    # and the final recollections/contrast with school each form one coherent episode.
    assert max(len(b['es'].split()) for b in chapter['blocks']) <= 220


def test_harry_second_chapter_vocabulary_pronouns_and_compact_dialogues():
    import re
    chapter = next(c for b in load_books() if b['id'] == 'harry-potter-piedra' for c in b['chapters'] if c['number'] == 2)
    entries = {n['term'] for block in chapter['blocks'] for n in block['notes'] if isinstance(n, dict)}
    assert {'el latón', 'la repisa', 'enjuto', 'huesudo', 'la filmadora', 'el envoltorio',
            'la manzana', 'el sollozo', 'el flequillo', 'remendado', 'encogerse', 'el nudillo',
            'el espécimen', 'el cubículo', 'conmocionado', 'la quemadura', 'estrafalario'} <= entries
    pronouns = {p['es']:p for block in chapter['blocks'] for p in block['pronouns']}
    assert 'не заменяет le' in pronouns['se los puso']['explanation']
    assert 'заменённое перед lo' in pronouns['pasárselo por la cabeza']['explanation']
    assert 'не замена les' in pronouns['se los había llevado']['explanation']
    assert 'Пассивное se' in pronouns['se debía observar']['explanation']
    assert 'Безличное se' in pronouns['si se quería vivir']['explanation']
    assert 'dormidos' in pronouns['Hasta que lo estuvieran']['explanation']
    for block in chapter['blocks']:
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[ \t]*—[^\n]*\n[ \t]*\n[ \t]*—', block[lang])


def _story():
    return next(b for b in load_books() if b['id'] == 'los-tres-cerditos')


def test_tres_cerditos_is_a2_story_without_chapters():
    book = _story()
    assert (book['kind'], book['level'], book['vocabulary_min_level']) == ('story', 'A2', 'A2')
    assert book['title'] == 'Los tres cerditos y el Lobo'
    assert book['chapters'] == []
    assert book['story']['status'] == 'published' and book['story']['icon'] == '🐷'
    assert 'title' not in book['story'] and 'number' not in book['story']


def test_tres_cerditos_contains_the_complete_supplied_source_in_order():
    import hashlib
    import re
    blocks = _story()['story']['blocks']
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in blocks)).strip()
    # Canonical text extracted from the supplied PDF (3 pages): site links and the
    # title removed, wrapped lines and the page break inside the wolf's threat joined.
    assert len(original.split()) == 594
    assert hashlib.sha256(original.encode()).hexdigest() == '3b8527840a6953adc3e5e9cc87227144721bb9ae8491d2f61126858ab7c9bcda'
    assert original.startswith('Había una vez tres cerditos')
    assert original.endswith('al Lobo Feroz, al Lobo Feroz!')
    assert len(blocks) == 5
    assert all(len(b['es'].split()) >= 60 for b in blocks)
    assert 'Pues si no me abrís... ¡Soplaré' in blocks[2]['es']


def test_tres_cerditos_dialogue_is_compact_and_paragraphs_are_real():
    import re
    blocks = _story()['story']['blocks']
    for block in blocks:
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[ \t]*[-—–][^\n]*\n[ \t]*\n[ \t]*[-—–]', block[lang]), (block['title'], lang)
    assert '- ¡Cerdito, ábreme la puerta!\n- No, no, no, no te voy a abrir.\n- Pues si no me abres' in blocks[1]['es']
    assert '— Поросёнок, открой мне дверь!\n— Нет, нет, нет, не открою.\n— Ну, раз ты мне не откроешь' in blocks[1]['ru']
    assert blocks[0]['es'].count('\n\n') == 1 and blocks[0]['ru'].count('\n\n') == 1
    assert '\n\nSe deslizó hacia abajo' in blocks[3]['es'] and '\n\nОн соскользнул вниз' in blocks[3]['ru']


def test_tres_cerditos_vocabulary_marks_and_pronouns():
    import re
    blocks = _story()['story']['blocks']
    def found(text, mark):
        return any(not (re.match(r'\w', mark[0]) and m.start() and re.match(r'\w', text[m.start() - 1]))
                   and not (re.match(r'\w', mark[-1]) and m.end() < len(text) and re.match(r'\w', text[m.end()]))
                   for m in re.finditer(re.escape(mark), text))
    terms = []
    for block in blocks:
        for note in block['notes']:
            if isinstance(note, str):
                continue
            terms.append(note['term'])
            assert note['explanation'].strip()
            for lang in ('es', 'ru'):
                assert note[lang], (note['term'], lang)
                for mark in note[lang]:
                    assert found(block[lang], mark), (block['title'], lang, mark)
    assert len(terms) == len(set(terms))
    # A2 threshold: useful words from A2 up are explained, not only rare ones.
    assert {'el cerdito', 'la paja', 'la madera', 'el ladrillo', 'soplar', 'derribar', 'venirse abajo',
            'esconderse', 'estar a salvo', 'en un santiamén', 'temer a (alguien / algo)', 'el bosque',
            'regañar a (alguien) por (algo)', 'volver a (infinitivo)', 'ponerse a (infinitivo)'} <= set(terms)
    pronouns = {p['es']: p for block in blocks for p in block['pronouns']}
    assert 'Пассивно-безличное se' in pronouns['se puede sujetar']['explanation']
    assert 'a sus hermanos' in pronouns['El más grande les dijo a sus hermanos']['explanation']
    assert 'la casita de ladrillos' in pronouns['no conseguía derribarla']['explanation']
    assert 'волк' in pronouns['Los cerditos no lo volvieron a ver']['explanation']
    assert 'не местоимение-дополнение' in pronouns['La mía será de paja']['explanation']


def test_story_loader_requires_story_file_and_rejects_chapters(tmp_path):
    import json
    import pytest
    folder = tmp_path / 'cuento'
    folder.mkdir()
    meta = {'id': 'cuento', 'kind': 'story', 'title': 'Cuento', 'author': 'Autor', 'level': 'A1', 'vocabulary_min_level': 'A1'}
    (folder / 'book.json').write_text(json.dumps(meta), encoding='utf-8')
    with pytest.raises(ValueError):
        load_books(tmp_path)
    (folder / 'story.json').write_text(json.dumps({'status': 'published', 'blocks': []}), encoding='utf-8')
    with pytest.raises(ValueError):
        load_books(tmp_path)
    (folder / 'story.json').write_text(json.dumps({'status': 'draft', 'blocks': []}), encoding='utf-8')
    assert load_books(tmp_path) == []
    (folder / 'story.json').write_text(json.dumps({'status': 'published', 'blocks': [{'title': 'x'}]}), encoding='utf-8')
    [story] = load_books(tmp_path)
    assert story['chapters'] == [] and story['story']['icon'] == '📖'
    (folder / 'chapters').mkdir()
    with pytest.raises(ValueError):
        load_books(tmp_path)
    (folder / 'chapters').rmdir()
    (folder / 'book.json').write_text(json.dumps({**meta, 'kind': 'poem'}), encoding='utf-8')
    with pytest.raises(ValueError):
        load_books(tmp_path)


def test_tres_cerditos_illustrations_follow_the_plot():
    blocks = _story()['story']['blocks']
    placed = [(i, im.get('before')) for i, b in enumerate(blocks) for im in b.get('images', [])]
    assert placed == [(0, None), (0, '- La mía será de paja'), (1, 'Y sopló con todas sus fuerzas'),
                      (2, 'La madera crujió'), (3, 'Y se puso a soplar tan fuerte')]
    for block in blocks:
        for image in block.get('images', []):
            assert image['src'].startswith('data:image/webp;base64,') and 'file' not in image
            assert image['alt'].strip()


def test_tres_cerditos_vocabulary_has_no_random_word_chains():
    terms = {n['term'] for b in _story()['story']['blocks'] for n in b['notes'] if isinstance(n, dict)}
    assert not {'irse por el mundo', 'conseguir fortuna', 'más (adjetivo) que antes', 'el mayor de (un grupo)'} & terms
    assert {'irse', 'conseguir (algo)', 'la fortuna'} <= terms
    # A2 threshold: plain A1 words are not listed.
    assert not {'el hermano', 'el mundo', 'jugar', 'cantar', 'el árbol', 'correr', 'antes', 'mayor',
                'el viento', 'el invierno', 'la vida', 'gustar (algo) a (alguien)'} & terms


def test_book_images_are_validated(tmp_path):
    import json
    import pytest
    folder = tmp_path / 'cuento'
    (folder / 'images').mkdir(parents=True)
    (folder / 'images' / 'a.webp').write_bytes(b'RIFF')
    (folder / 'book.json').write_text(json.dumps({'id': 'cuento', 'kind': 'story', 'title': 'C', 'author': 'A',
                                                  'level': 'A1', 'vocabulary_min_level': 'A1'}), encoding='utf-8')
    def story(image):
        (folder / 'story.json').write_text(json.dumps({'status': 'published', 'blocks': [
            {'title': 't', 'es': 'Uno.\nDos.', 'images': [image]}]}), encoding='utf-8')
    story({'file': 'images/a.webp', 'alt': 'x', 'before': 'Dos.'})
    assert load_books(tmp_path)[0]['story']['blocks'][0]['images'][0]['src'].startswith('data:image/webp;base64,')
    for bad in ({'file': 'images/a.webp', 'alt': ''}, {'file': '../a.webp', 'alt': 'x'},
                {'file': 'images/a.webp', 'alt': 'x', 'before': 'Tres'},
                {'file': 'images/a.webp', 'alt': 'x', 'before': 'os.'}):
        story(bad)
        with pytest.raises(ValueError):
            load_books(tmp_path)


def _ana():
    return next(b for b in load_books() if b['id'] == 'pobre-ana')


def test_pobre_ana_metadata_and_first_chapter():
    book = _ana()
    assert (book['title'], book['author'], book['level'], book['vocabulary_min_level']) == ('Pobre Ana', 'Blaine Ray', 'A1', 'A1')
    assert book['icon'] == '🎒' and book.get('kind', 'book') == 'book'
    assert [b['id'] for b in load_books() if b['level'] == 'A1'].count('pobre-ana') == 1
    chapter = book['chapters'][0]
    assert (chapter['id'], chapter['number'], chapter['order'], chapter['title']) == ('1', 1, 1, '')
    assert chapter['icon'] == '👕' and chapter['status'] == 'published'


def test_pobre_ana_first_chapter_contains_the_complete_source_in_order():
    import hashlib
    import re
    blocks = _ana()['chapters'][0]['blocks']
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in blocks)).strip()
    # «Capítulo uno» from the supplied PDF (printed pp. 1–5): running heads, page numbers and
    # ornaments removed, hyphenated words and the page breaks inside sentences joined.
    assert len(original.split()) == 731
    assert hashlib.sha256(original.encode()).hexdigest() == '78002239f50c7e0339cc81ab46fbb431d886169288eb08581139f540868b31d7'
    assert original.startswith('Ana es una chica con problemas.')
    assert original.endswith('no comen mucha carne porque quieren economizar.')
    assert 'Él trabaja en un hospital' in original  # опечатка книги (El) исправлена
    assert len(blocks) == 7 and all(len(b['es'].split()) >= 60 for b in blocks)
    for block in blocks:
        assert block['es'].count('\n\n') == block['ru'].count('\n\n'), block['title']
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[ \t]*[—–][^\n]*\n[ \t]*\n[ \t]*[—–]', block[lang])
    assert 'le grita:\n—¡Ana, levanta' in blocks[1]['es'] and 'на неё:\n— Ана, подними' in blocks[1]['ru']
    assert 'restaurante.\nEl papá le responde:\n—No tengo' in blocks[1]['es']


def test_pobre_ana_second_chapter_contains_the_complete_source_in_order():
    import hashlib
    import re
    chapter = _ana()['chapters'][1]
    assert (chapter['id'], chapter['number'], chapter['order'], chapter['title']) == ('2', 2, 2, '')
    assert chapter['icon'] == '📒' and chapter['status'] == 'published'
    blocks = chapter['blocks']
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in blocks)).strip()
    # «Capítulo dos» (printed pp. 6–9): running heads and page numbers removed, hyphenation joined.
    assert len(original.split()) == 575
    assert hashlib.sha256(original.encode()).hexdigest() == 'c9cfc084d6a9b3157c6261a5d07fbbacac0336ba894a46be3f69a175a165085a'
    assert original.startswith('Un día Ana se levanta a las siete de la mañana.')
    assert original.endswith('Ana, no hay problema. Puedes ir a México.')
    assert 'Él le dice:' in original and 'El le dice' not in original  # опечатка книги исправлена
    assert len(blocks) == 5 and all(len(b['es'].split()) >= 60 for b in blocks)
    for block in blocks:
        assert block['es'].count('\n\n') == block['ru'].count('\n\n'), block['title']
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[ \t]*[—–][^\n]*\n[ \t]*\n[ \t]*[—–]', block[lang])
    terms = {n['term'] for b in blocks for n in b['notes'] if isinstance(n, dict)}
    assert {'levantarse', 'enojarse', 'gustar (a alguien)', 'ver a (alguien)', 'poder + infinitivo',
            'ir a + infinitivo', 'costar', 'para mí'} <= terms
    assert not terms & {'el libro', 'la escuela', 'el hermano', 'la profesora', 'el estudiante', 'vivir'}


def test_pobre_ana_third_chapter_contains_the_complete_source_in_order():
    import hashlib
    import re
    chapter = _ana()['chapters'][2]
    assert (chapter['id'], chapter['number'], chapter['order'], chapter['title']) == ('3', 3, 3, '')
    assert chapter['icon'] == '✈️' and chapter['status'] == 'published'
    blocks = chapter['blocks']
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in blocks)).strip()
    # «Capítulo tres» (printed pp. 10–18): running heads and page numbers removed, hyphenation joined.
    assert len(original.split()) == 1171
    assert hashlib.sha256(original.encode()).hexdigest() == '4aaa9afacf3957b264e76e9026599cc677103495f774fa950668986060ba22df'
    assert original.startswith('Tres meses más tarde Ana está emocionada')
    assert original.endswith('A Ana le gusta su familia nueva. Le gusta México.')
    assert 'Los Ángeles' in original and 'Los Angeles' not in original and '¡Oh, no!' in original
    assert len(blocks) == 11 and all(len(b['es'].split()) >= 60 for b in blocks)
    for block in blocks:
        assert block['es'].count('\n\n') == block['ru'].count('\n\n'), block['title']
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[ \t]*[—–][^\n]*\n[ \t]*\n[ \t]*[—–]', block[lang])
    terms = {n['term'] for b in blocks for n in b['notes'] if isinstance(n, dict)}
    earlier = {n['term'] for ch in _ana()['chapters'][:2] for b in ch['blocks'] for n in b['notes'] if isinstance(n, dict)}
    assert not terms & earlier  # слова прошлых глав заново не разбираем
    assert {'irse (a un lugar)', 'tener miedo', 'comprender', 'el agua', 'dormir', 'tocar a la puerta'} <= terms
    assert not terms & {'el taxi', 'gracias', 'adiós', 'el novio', 'el hijo / la hija', 'pequeño'}


def test_pobre_ana_fourth_chapter_contains_the_complete_source_in_order():
    import hashlib
    import re
    chapter = _ana()['chapters'][3]
    assert (chapter['id'], chapter['number'], chapter['order'], chapter['title']) == ('4', 4, 4, '')
    assert chapter['icon'] == '🌮' and chapter['status'] == 'published'
    blocks = chapter['blocks']
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in blocks)).strip()
    # «Capítulo cuatro» (printed pp. 19–21).
    assert len(original.split()) == 417
    assert hashlib.sha256(original.encode()).hexdigest() == '93720f13c2657977b95d5964fe2fd85230f706e00a2c107730a36fa56abbe79f'
    assert original.startswith('A las nueve de la mañana Ana se despierta.')
    assert original.endswith('En la noche está muy cansada y duerme muy bien.')
    assert len(blocks) == 4 and all(len(b['es'].split()) >= 60 for b in blocks)
    for block in blocks:
        assert block['es'].count('\n\n') == block['ru'].count('\n\n'), block['title']
    terms = {n['term'] for b in blocks for n in b['notes'] if isinstance(n, dict)}
    earlier = {n['term'] for ch in _ana()['chapters'][:3] for b in ch['blocks'] for n in b['notes'] if isinstance(n, dict)}
    assert not terms & earlier
    assert {'despertarse', 'estar + gerundio', 'prender', 'el radio', 'en la noche', 'oír'} <= terms
    assert 'la tortilla' not in terms  # слово A0; мексиканское значение — в пометке


def test_pobre_ana_fifth_chapter_contains_the_complete_source_in_order():
    import hashlib
    import re
    chapter = _ana()['chapters'][4]
    assert (chapter['id'], chapter['number'], chapter['order'], chapter['title']) == ('5', 5, 5, '')
    assert chapter['icon'] == '🏫' and chapter['status'] == 'published'
    blocks = chapter['blocks']
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in blocks)).strip()
    # «Capítulo cinco» (printed pp. 22–25); опечатки книги исправлены и отмечены в разборе.
    assert len(original.split()) == 523
    assert hashlib.sha256(original.encode()).hexdigest() == '65eaba736db88cd2b5f39a600f28dfbcd8c29ff6988c19fe0e64412a9b9e32a0'
    assert original.startswith('Ana se despierta el próximo día y va sola al gimnasio.')
    assert original.endswith('En la noche Ana se duerme.')
    for fixed in ('—le dice Ana—. El gusto es mío.', 'todos los tipos de música', 'papas… muchas cosas', 'Los Ángeles'):
        assert fixed in original
    assert len(blocks) == 5 and all(len(b['es'].split()) >= 60 for b in blocks)
    for block in blocks:
        assert block['es'].count('\n\n') == block['ru'].count('\n\n'), block['title']
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[ \t]*[—–][^\n]*\n[ \t]*\n[ \t]*[—–]', block[lang])
    terms = {n['term'] for b in blocks for n in b['notes'] if isinstance(n, dict)}
    earlier = {n['term'] for ch in _ana()['chapters'][:4] for b in ch['blocks'] for n in b['notes'] if isinstance(n, dict)}
    assert not terms & earlier
    assert {'conocer a (alguien)', 'el gusto es mío', 'Uds. (ustedes)', 'la papa', 'dormirse'} <= terms


def test_pobre_ana_sixth_chapter_contains_the_complete_source_in_order():
    import hashlib
    import re
    chapter = _ana()['chapters'][5]
    assert (chapter['id'], chapter['number'], chapter['order'], chapter['title']) == ('6', 6, 6, '')
    assert chapter['icon'] == '💃' and chapter['status'] == 'published'
    blocks = chapter['blocks']
    original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in blocks)).strip()
    # «Capítulo seis» (printed pp. 26–29); casa de Ricardo → casa de Patricia исправлено и отмечено.
    assert len(original.split()) == 491
    assert hashlib.sha256(original.encode()).hexdigest() == '8091d9a9e89220f8f230c21956e696cfa3e60d69fb2ad904aa7909777758fcf7'
    assert original.startswith('Una noche hay un baile.')
    assert original.endswith('También está triste porque pronto regresa a California.')
    assert 'Los tres andan a la casa de Patricia.' in original
    assert len(blocks) == 5 and all(len(b['es'].split()) >= 60 for b in blocks)
    for block in blocks:
        assert block['es'].count('\n\n') == block['ru'].count('\n\n'), block['title']
        for lang in ('es', 'ru'):
            assert not re.search(r'(?m)^[ \t]*[—–][^\n]*\n[ \t]*\n[ \t]*[—–]', block[lang])
    terms = {n['term'] for b in blocks for n in b['notes'] if isinstance(n, dict)}
    earlier = {n['term'] for ch in _ana()['chapters'][:5] for b in ch['blocks'] for n in b['notes'] if isinstance(n, dict)}
    assert not terms & earlier
    assert {'saber + infinitivo', 'venir (de)', 'enseñar a (alguien) a + infinitivo', 'regresar a (un lugar)'} <= terms


def test_pobre_ana_last_chapters_contain_the_complete_source_in_order():
    import hashlib
    import re
    book = _ana()
    assert [c['number'] for c in book['chapters']] == list(range(1, 10))  # вся книга, 9 глав
    expected = {
        7: ('👋', 397, '58e35cc4d04422d5240d4bd56ca2df38947548cd0ba3f7f06816eafb676a4db9',
            'Mañana Ana regresa a California.', 'Está triste también porque no está en México.'),
        8: ('✉️', 473, 'cdbf77f144e5881304e57c18d94e9c77f6e345697b5246e10aede62e9b149c1f',
            'Ana se sube al carro de la familia', 'Con mucho cariño, Ana'),
        9: ('📦', 318, '82239968fdeb01150ed4f114f91cd891aa6afd671739f2000e5f9409a59c95af',
            'Ana mira todo con admiración.', 'Ana sonríe porque la vida es perfecta.'),
    }
    earlier = set()
    for chapter in book['chapters']:
        terms = {n['term'] for b in chapter['blocks'] for n in b['notes'] if isinstance(n, dict)}
        if chapter['number'] in expected:
            icon, words, digest, start, end = expected[chapter['number']]
            n = chapter['number']
            assert (chapter['id'], chapter['order'], chapter['title'], chapter['icon']) == (str(n), n, '', icon)
            original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in chapter['blocks'])).strip()
            assert len(original.split()) == words
            assert hashlib.sha256(original.encode()).hexdigest() == digest
            assert original.startswith(start) and original.endswith(end)
            assert all(len(b['es'].split()) >= 60 for b in chapter['blocks'])
            for block in chapter['blocks']:
                assert block['es'].count('\n\n') == block['ru'].count('\n\n'), block['title']
            assert not terms & earlier, n
        earlier |= terms
    text7 = ' '.join(b['es'] for b in book['chapters'][6]['blocks'])
    assert 'California es bonita' in text7 and 'Los Ángeles' in text7 and '\n—Ana, tú eres' in text7
    assert "Levi's" in ' '.join(b['es'] for b in book['chapters'][8]['blocks'])


def test_pobre_ana_highlights_exist_and_never_overlap():
    import re
    word = re.compile(r'\w')
    def spans(text, mark):
        out, at = [], text.find(mark)
        while at != -1:
            end = at + len(mark)
            if not ((word.match(mark[0]) and at and word.match(text[at - 1]))
                    or (word.match(mark[-1]) and end < len(text) and word.match(text[end]))):
                out.append((at, end))
            at = text.find(mark, at + 1)
        return out
    terms, chapter_terms = [], []
    for block in [b for ch in _ana()['chapters'] for b in ch['blocks']]:
        for lang in ('es', 'ru'):
            taken = []
            for note in block['notes']:
                if isinstance(note, str):
                    continue
                for mark in note[lang]:
                    found = spans(block[lang], mark)
                    chosen = note.get('occurrences', {}).get(lang, {}).get(mark)
                    if chosen is not None:
                        assert max(chosen) < len(found), (note['term'], mark)
                        found = [found[i] for i in chosen]
                    assert found, (block['title'], lang, mark)
                    for at, end in found:
                        assert all(end <= a or b <= at for a, b in taken), (block['title'], lang, mark)
                        taken.append((at, end))
        terms += [n['term'] for n in block['notes'] if isinstance(n, dict)]
        for item in block['pronouns']:
            assert item['es'] in block['es'] and item['explanation'].strip()
    for ch in _ana()['chapters']:
        chapter_terms = [n['term'] for b in ch['blocks'] for n in b['notes'] if isinstance(n, dict)]
        assert len(chapter_terms) == len(set(chapter_terms)), ch['number']
    assert {'el problema', 'asistir a (un lugar)', 'no + presente de subjuntivo',
            'reírse de (algo / alguien)', 'pobre (перед существительным)', 'el carro', 'ir en (transporte)',
            'estar triste', 'sacar notas', 'pedir (algo) a (alguien)', 'economizar'} <= set(terms)
    blocks = _ana()['chapters'][0]['blocks']
    pronouns = {p['es']: p for block in blocks for p in block['pronouns']}
    assert 'el libro' in pronouns['no lo encuentra']['explanation']
    assert 'дублирует' in pronouns['Ana le dice a su papá']['explanation']
    assert blocks[-1]['pronouns'] == []


def test_book_icon_is_optional_and_validated(tmp_path):
    import json
    import pytest
    folder = tmp_path / 'libro'
    (folder / 'chapters').mkdir(parents=True)
    meta = {'id': 'libro', 'title': 'Libro', 'author': 'Autor', 'level': 'A1', 'vocabulary_min_level': 'A1'}
    (folder / 'book.json').write_text(json.dumps(meta), encoding='utf-8')
    assert 'icon' not in load_books(tmp_path)[0]
    (folder / 'book.json').write_text(json.dumps({**meta, 'icon': ' 🎒 '}), encoding='utf-8')
    assert load_books(tmp_path)[0]['icon'] == '🎒'
    (folder / 'book.json').write_text(json.dumps({**meta, 'icon': ''}), encoding='utf-8')
    with pytest.raises(ValueError, match='иконка книги'):
        load_books(tmp_path)


def test_a1_books_skip_words_of_the_site_a0_course():
    """Порог A1: слова, пройденные в темах A0 сайта, в разбор не попадают."""
    import re
    from espanol.course import load_course
    def key(text):
        text = re.sub(r'\(.*?\)|[¿?¡!.…]', ' ', text.lower())
        text = re.sub(r'^(el|la|los|las|un|una)\s+|/a\b', '', text.strip())
        return re.sub(r'\s+', ' ', text).strip()
    a0 = set()
    for unit in load_course('content/site').units:
        if unit.level == 'A0':
            for lesson in unit.lessons:
                for word in lesson.vocab or []:
                    a0 |= {key(part) for part in word.es.split(' / ')}
    assert {'él', 'once', 'también', 'familia', 'llamarse'} <= a0
    # Слова A0 остаются только с необычным значением в контексте (estudiar — «разобрать запись»,
    # el señor — «хозяин дома»).
    unusual = {'estudiar', 'el señor'}
    # The guide also allows a familiar A0 word in an unfamiliar function.
    # These specific entries teach emphasis, approximate numbers and a vocative,
    # rather than re-teaching sí, unos or mujer in their elementary meanings.
    unusual_by_book = {'lola-lago-vacaciones-al-sol': {
        'sí (усилительное)', 'unos (приблизительное количество)', 'mujer (обращение)'}}
    for book in load_books():
        if book['vocabulary_min_level'] != 'A1':
            continue
        terms = [n['term'] for c in book['chapters'] for b in c['blocks'] for n in b['notes'] if isinstance(n, dict)]
        permitted = unusual | unusual_by_book.get(book['id'], set())
        assert not [t for t in terms if key(t) in a0 and t not in permitted], book['id']
