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



def test_all_books_have_short_spoiler_free_annotations():
    import json
    from pathlib import Path
    from espanol.site import load_books

    files = sorted(Path("content/books").glob("*/book.json"))
    assert len(files) >= 14
    annotations = {}
    for path in files:
        meta = json.loads(path.read_text(encoding="utf-8"))
        summary = meta.get("annotation")
        assert isinstance(summary, str) and 85 <= len(summary) <= 350, path
        assert summary == summary.strip() and "\\n" not in summary and "<" not in summary and ">" not in summary, path
        annotations[meta["id"]] = summary
    # A collection has its own introduction; each member describes its own story.
    anthology = json.loads(Path("content/books/olly-richards-short-stories-beginners/book.json").read_text(encoding="utf-8"))
    assert all(annotations[child] != annotations[anthology["id"]] for child in anthology["books"])
    for book in load_books():
        assert book["annotation"] == annotations[book["id"]]


def test_book_annotation_is_validated_when_present(tmp_path):
    import json
    import pytest
    from espanol.site import load_books
    folder = tmp_path / "test-book"
    folder.mkdir()
    base = {"id": "test-book", "title": "Libro", "author": "Autor",
            "level": "A1", "vocabulary_min_level": "A1"}
    for invalid in ("", "   ", 7, {"text": "wrong"}, "a" * 351, "dos\nlíneas"):
        (folder / "book.json").write_text(json.dumps({**base, "annotation": invalid}), encoding="utf-8")
        with pytest.raises(ValueError, match="аннотация"):
            load_books(tmp_path)


def test_olly_collection_has_one_parent_and_complete_contents():
    books = [b for b in load_books() if b.get('series', {}).get('id') == 'olly-richards-short-stories-beginners']
    assert [b['series']['number'] for b in books] == list(range(1, 9))
    assert [b['level'] for b in books] == ['B1'] * 8
    parent = next(b for b in load_books() if b['id'] == 'olly-richards-short-stories-beginners')
    assert parent['kind'] == 'collection' and parent['level'] == 'B1'
    assert parent['vocabulary_min_level'] == 'A2'
    assert parent['books'] == [b['id'] for b in books]
    assert all(b['collection'] == parent['id'] for b in books)
    assert parent['chapters'] == parent['chapter_catalog'] == []
    assert all(b['vocabulary_min_level'] == 'A2' for b in books)
    assert [len(b['chapter_catalog']) for b in books] == [4, 3, 3, 3, 3, 3, 3, 3]
    for book in books:
        expected = ([1, 2, 3, 4] if book['id'] == 'olly-richards-la-paella-loca' else
                    [1, 2, 3] if book['id'] in {'olly-richards-la-criatura', 'olly-richards-el-caballero', 'olly-richards-el-reloj', 'olly-richards-el-cofre'} else [1])
        assert [c['number'] for c in book['chapters']] == expected
        assert [c['status'] for c in book['chapter_catalog']] == (
            ['published'] * len(expected) + ['draft'] * (len(book['chapter_catalog']) - len(expected)))
        assert all(c['title'].strip() for c in book['chapter_catalog'])
        for chapter in book['chapters']:
            assert len(chapter['exercises']) == 1
            assert len(chapter['exercises'][0]['questions']) == 5
            assert all(block['es'] and block['ru'] and block['notes'] for block in chapter['blocks'])
    assert sum(len(b.get('images', [])) for book in books for chapter in book['chapters']
               for b in chapter['blocks']) == 7
    assert sum(len(book.get('pending_illustrations', [])) for book in books) == 1


def test_el_cofre_complete_chapters_source_and_publisher_quizzes():
    """Fifth anthology story: all source, original quiz answers and linked vocabulary."""
    import hashlib
    import re

    book = next(b for b in load_books() if b['id'] == 'olly-richards-el-cofre')
    assert book['vocabulary_min_level'] == 'A2'
    assert [c['title'] for c in book['chapters']] == ['Madrid', 'Mallorca', 'Bilbao']
    assert [c['status'] for c in book['chapters']] == ['published'] * 3
    assert [len(c['blocks']) for c in book['chapters'][1:]] == [9, 11]
    expected = [
        (2, 1009, '3071433c393ee24a145840a40c08419cb122026836c0647fad37e28977c938bc',
         57, 43, [0, 0, 1, 0, 0], 108, list(range(108, 115))),
        (3, 1341, 'd43cc9187ec36d8bddc8f5761c77cc3a43a436517b61ed5f59cf9ae10d6308e5',
         62, 56, [2, 2, 3, 1, 1], 115, list(range(115, 123))),
    ]
    learned = {n['term'].casefold() for b in book['chapters'][0]['blocks']
               for n in b['notes'] if isinstance(n, dict) and n.get('term')}
    for chapter, (number, word_count, digest, note_count, pronoun_count,
                  answers, heading_page, pages) in zip(book['chapters'][1:], expected):
        original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in chapter['blocks'])).strip()
        assert len(original.split()) == word_count
        assert hashlib.sha256(original.encode('utf-8')).hexdigest() == digest
        assert chapter['number'] == number and chapter['source']['heading_page'] == heading_page
        assert all(60 <= len(b['es'].split()) <= 190 and b['ru'] for b in chapter['blocks'])
        assert sum(len(b['pronouns']) for b in chapter['blocks']) == pronoun_count
        notes = [n for b in chapter['blocks'] for n in b['notes']]
        assert len(notes) == note_count
        terms = {n['term'].casefold() for n in notes}
        assert len(terms) == note_count
        assert terms.isdisjoint(learned)
        learned.update(terms)
        for block in chapter['blocks']:
            for note in block['notes']:
                assert note['term'] and note['explanation']
                for lang in ('es', 'ru'):
                    assert note[lang], note['term']
                    for marker in note[lang]:
                        assert re.search(r'(?<!\w)' + re.escape(marker) + r'(?!\w)',
                                         block[lang], re.I), (
                            number, block['title'], note['term'], lang, marker)
            for pronoun in block['pronouns']:
                assert pronoun['es'] and pronoun['translation'] and pronoun['explanation']
                assert pronoun['base'] and pronoun['es'] in block['es']
        assert len(chapter['exercises']) == 1
        ex = chapter['exercises'][0]
        assert ex['source']['pdf_pages'] == pages
        assert ex['source']['answer_key_page'] == 190
        assert ex['source']['chapters'] == [number]
        assert [len(q['options']) for q in ex['questions']] == [4] * 5
        assert [q['answer'] for q in ex['questions']] == answers
    corrections = book['chapters'][2]['source']['editorial_corrections']
    assert {(fix['pdf_page'], fix['printed'], fix['edited']) for fix in corrections} == {
        (116, '–Ah, no –Arturo dijo Arturo. Me llamo Arturo –continuó–.',
         '–Ah, no –dijo Arturo–. Me llamo Arturo –continuó–.'),
        (118, 'Ilamaban', 'llamaban'),
    }
    # Distinct semantic units already covered in chapter 1 are not repeated as new notes.
    assert not {'el cofre', 'el collar', 'recordar', 'a través de', 'con recelo'} & learned

def test_el_reloj_complete_chapters_source_notes_pronouns_and_quizzes():
    """Fourth anthology story: strict source fidelity, teaching data, and complete printed quizzes."""
    import hashlib
    import re

    book = next(b for b in load_books() if b['id'] == 'olly-richards-el-reloj')
    assert book['vocabulary_min_level'] == 'A2'
    assert [ch['title'] for ch in book['chapters']] == ['Leyenda', 'El Caribe', 'La batalla']
    assert [ch['status'] for ch in book['chapters']] == ['published'] * 3
    assert [len(ch['blocks']) for ch in book['chapters']] == [9, 9, 9]
    expected = [
        (2, 997, '749b8b2675d166765882ab015c45b78d2a628f1cf56814ca333044c5a33826b8',
         50, 33, [1, 0, 2, 0, 1], 86, list(range(86, 93))),
        (3, 1138, '1773b8e552bc6c404e488e3b8cf3c15886c6b357addd0be7a7df0903c2c582ad',
         54, 30, [2, 1, 1, 3, 1], 93, list(range(93, 100))),
    ]
    learned = {note.get('term') for block in book['chapters'][0]['blocks']
               for note in block['notes'] if isinstance(note, dict) and note.get('term')}
    for chapter, (number, count, digest, n_notes, n_pronouns, answers, page, pdf_pages) in zip(
            book['chapters'][1:], expected):
        assert chapter['number'] == number
        source = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in chapter['blocks'])).strip()
        assert len(source.split()) == count
        assert hashlib.sha256(source.encode('utf-8')).hexdigest() == digest
        assert chapter['source']['heading_page'] == page
        assert all(50 <= len(block['es'].split()) <= 180 for block in chapter['blocks'])
        assert all(block['ru'] and block['pronouns'] for block in chapter['blocks'])
        assert sum(len(block['pronouns']) for block in chapter['blocks']) == n_pronouns
        notes = [note for block in chapter['blocks'] for note in block['notes']]
        assert len(notes) == n_notes
        terms = {note['term'] for note in notes}
        assert len(terms) == len(notes) and terms.isdisjoint(learned)
        learned |= terms
        for block in chapter['blocks']:
            for note in block['notes']:
                assert note['explanation'] and len(note['es']) >= 1 and len(note['ru']) >= 1
                for lang in ('es', 'ru'):
                    for mark in note[lang]:
                        assert re.search(r'(?<!\w)' + re.escape(mark) + r'(?!\w)', block[lang], re.I), (
                            number, block['title'], lang, note['term'], mark)
            for pronoun in block['pronouns']:
                assert pronoun['es'] in block['es'], (number, block['title'], pronoun['es'])
                assert pronoun['translation'] and pronoun['explanation']
        assert len(chapter['exercises']) == 1
        exercise = chapter['exercises'][0]
        assert exercise['source']['pdf_pages'] == pdf_pages
        assert exercise['source']['chapters'] == [number]
        assert exercise['source']['answer_key_page'] == 190
        assert len(exercise['questions']) == 5
        assert [len(q['options']) for q in exercise['questions']] == [4] * 5
        assert [q['answer'] for q in exercise['questions']] == answers

    ch2 = ' '.join(block['es'] for block in book['chapters'][1]['blocks'])
    assert '¿Volver al siglo XVII?' in ch2 and 'al sigo XVII' not in ch2
    assert 'los hombres sí prestaron atención' in ch2
    assert 'Los ingleses se estaban acercando' in ch2
    assert any('нестыковка' in note['explanation']
               for block in book['chapters'][1]['blocks'] for note in block['notes'])
    introduced = {note['term'] for chapter in book['chapters'][1:]
                  for block in chapter['blocks'] for note in block['notes']}
    assert not {'moreno', 'el reloj', 'el siglo', 'la leyenda'} & introduced


def test_el_caballero_finished_chapters_source_notes_and_exercises():
    import hashlib
    import re

    book = next(b for b in load_books() if b['id'] == 'olly-richards-el-caballero')
    assert [c['title'] for c in book['chapters']] == [
        'El oro', 'El bosque', 'El secreto']
    assert [c['status'] for c in book['chapters']] == ['published'] * 3
    assert [len(c['blocks']) for c in book['chapters']] == [9, 9, 8]
    expected = (
        (2, 1094, 'f5c11733c88ce91be1cb75e14667f95c2b7eed66d7da676903db5b735716eec4',
         68, 21, [0, 0, 1, 2, 3]),
        (3, 922, '46235c7754c9a1326d5509c724e1ed8ca3fc69d4920567d0833fa5a021d950c5',
         55, 19, [2, 1, 2, 2, 0]),
    )
    learned = {n.get('term') for b in book['chapters'][0]['blocks']
               for n in b['notes'] if isinstance(n, dict) and n.get('term')}
    for chapter, (number, words, digest, notes_count, pronoun_count, answers) in zip(
            book['chapters'][1:], expected):
        assert chapter['number'] == number
        original = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in chapter['blocks'])).strip()
        assert len(original.split()) == words
        assert hashlib.sha256(original.encode('utf-8')).hexdigest() == digest
        notes = [n for b in chapter['blocks'] for n in b['notes']]
        assert len(notes) == notes_count
        terms = {n['term'] for n in notes}
        assert len(terms) == len(notes)
        assert not terms & learned, (number, terms & learned)
        learned |= terms
        assert sum(len(b['pronouns']) for b in chapter['blocks']) == pronoun_count
        assert all(60 <= len(b['es'].split()) <= 180 for b in chapter['blocks'])
        assert all(b['ru'] and b['pronouns'] for b in chapter['blocks'])
        assert [len(q['options']) for q in chapter['exercises'][0]['questions']] == [4] * 5
        assert chapter['source']['heading_page'] == (64 if number == 2 else 71)
        assert chapter['exercises'][0]['source']['answer_key_page'] == 190
        assert [q['answer'] for q in chapter['exercises'][0]['questions']] == answers
    chapter2, chapter3 = book['chapters'][1:]
    assert '¿Y qué pasó?' in ' '.join(b['es'] for b in chapter2['blocks'])
    assert '¿Y qué paso?' not in ' '.join(b['es'] for b in chapter2['blocks'])
    assert 'Los guardias de Authuran' in ' '.join(b['es'] for b in chapter3['blocks'])
    assert 'Los guardias de Arthuran' not in ' '.join(b['es'] for b in chapter3['blocks'])


def test_la_criatura_finished_chapters_match_source_and_exercises():
    import hashlib
    import re

    book = next(b for b in load_books() if b['id'] == 'olly-richards-la-criatura')
    assert [c['title'] for c in book['chapters']] == [
        'La excursión', 'La búsqueda', 'La sorpresa']
    assert [c['status'] for c in book['chapters']] == ['published'] * 3
    assert [len(c['blocks']) for c in book['chapters'][1:]] == [8, 7]
    expected = [
        (2, 1030, 'b68d15ee5e47afdbcbea970c263cad0ae254f9fd89df70f95fd84f8ead2719da',
         64, [1, 3, 2, 0, 1]),
        (3, 902, '09517c043b086f6d892a89a69c70536fc1e1196cea09b8a3ee126836e147c318',
         48, [2, 0, 3, 0, 2]),
    ]
    seen = {n.get('term') for b in book['chapters'][0]['blocks']
            for n in b['notes'] if isinstance(n, dict) and n.get('term')}
    for chapter, (number, words, digest, note_count, answers) in zip(book['chapters'][1:], expected):
        assert chapter['number'] == number
        source = re.sub(r'\s+', ' ', ' '.join(b['es'] for b in chapter['blocks'])).strip()
        assert len(source.split()) == words
        assert hashlib.sha256(source.encode()).hexdigest() == digest
        assert chapter['source']['heading_page'] == (45 if number == 2 else 51)
        notes = [n for b in chapter['blocks'] for n in b['notes']]
        assert len(notes) == note_count
        terms = {n['term'] for n in notes}
        assert len(terms) == len(notes) and not (terms & seen)
        seen |= terms
        assert all(60 <= len(b['es'].split()) <= 160 for b in chapter['blocks'])
        assert all(b['ru'] and b['pronouns'] for b in chapter['blocks'])
        exercises = chapter['exercises'][0]
        assert exercises['source']['answer_key_page'] == 190
        assert [q['answer'] for q in exercises['questions']] == answers


def test_la_paella_loca_complete_chapters_notes_and_source_keys():
    book = next(b for b in load_books() if b['id'] == 'olly-richards-la-paella-loca')
    assert [chapter['title'] for chapter in book['chapters']] == [
        'El avión', 'España', 'La carretera', 'El regreso']
    assert [len(chapter['blocks']) for chapter in book['chapters']] == [6, 9, 8, 7]
    assert sum(len(chapter['exercises'][0]['questions']) for chapter in book['chapters']) == 20
    for chapter, answers in zip(book['chapters'][1:], (
            [3, 1, 1, 0, 2], [1, 2, 3, 3, 1], [2, 3, 0, 2, 0])):
        assert [q['answer'] for q in chapter['exercises'][0]['questions']] == answers
    learned = set()
    for chapter in book['chapters']:
        for block in chapter['blocks']:
            assert 45 <= len(block['es'].split()) <= 150
            for language in ('es', 'ru'):
                assert not __import__('re').search(r'(?m)^[–—][^\n]*\n\n[–—]', block[language])
            for note in block['notes']:
                assert note['term'] not in learned, (chapter['number'], note['term'])
                learned.add(note['term'])
    image_blocks = [(chapter['number'], block) for chapter in book['chapters']
                    for block in chapter['blocks'] if block.get('images')]
    assert len(image_blocks) == 1
    assert image_blocks[0][0] == 3
    assert image_blocks[0][1]['images'][0]['before'] == 'Cuando salgo del hotel'



def test_olly_a2_vocabulary_avoids_words_taught_in_course_a0_and_a1():
    """Аудит 11.11.2026: не возвращаем уже изученные значения в словарные notes.

    Список выверен по vocab в content/site/units 00–23 и по контексту книги.
    Не блокируем новые значения, грамматические конструкции и идиомы.
    """
    books = {b['id']: b for b in load_books()}
    removed = {
        'olly-richards-la-paella-loca': {
            1: {'vestirse', 'despertarse', 'ducharse'},
            2: {'tímido', 'costar', 'la camisa', 'pasear', 'el camarero'},
            3: {'pedir', 'entre'},
            4: {'la llave'},
        },
        'olly-richards-la-criatura': {
            1: {'nublado', 'quedar', 'comer algo'},
        },
        'olly-richards-el-cofre': {
            1: {'levantarse'},
        },
        'olly-richards-la-capsula': {
            1: {'terminar'},
        },
    }
    for book_id, chapters in removed.items():
        book = books[book_id]
        assert book['vocabulary_min_level'] == 'A2'
        for chapter in book['chapters']:
            if chapter['number'] not in chapters:
                continue
            terms = {note['term'] for block in chapter['blocks']
                     for note in block['notes'] if isinstance(note, dict)}
            assert terms.isdisjoint(chapters[chapter['number']]), (book_id, chapter['number'])

    # Эти совпадения с A0/A1 намеренно сохранены из-за нового значения или управления.
    kept = {
        ('olly-richards-la-paella-loca', 2): 'encantado de (infinitivo)',
        ('olly-richards-la-paella-loca', 3): 'el trabajador',
        ('olly-richards-tierras-desconocidas', 1): 'el jefe',
        ('olly-richards-la-capsula', 1): 'quedar',
    }
    for (book_id, number), term in kept.items():
        chapter = next(c for c in books[book_id]['chapters'] if c['number'] == number)
        terms = {n['term'] for block in chapter['blocks']
                 for n in block['notes'] if isinstance(n, dict)}
        assert term in terms




def test_remaining_book_vocabulary_respects_cumulative_prior_course_levels():
    """Only re-teach words that have a new sense, construction or government.

    Guide §7: min A1 excludes material taught in course A0;
    min A2 or B1 excludes material from A0 and A1 while A2 lessons do not exist.
    """
    books = {book['id']: book for book in load_books()}
    excluded = {
        ('harry-potter-piedra', '1'): {'nublado'},
        ('harry-potter-piedra', '2'): {'peinarse', 'el dormitorio', 'repetir'},
        ('lola-lago-nota-falsa', '1'): {'escribir'},
        ('lola-lago-nota-falsa', '14'): {'estudiar'},
    }
    for (book_id, chapter_id), terms_to_exclude in excluded.items():
        chapter = next(c for c in books[book_id]['chapters'] if c['id'] == chapter_id)
        notes = {n['term'] for b in chapter['blocks'] for n in b['notes'] if isinstance(n, dict)}
        assert terms_to_exclude.isdisjoint(notes), (book_id, chapter_id)

    story_notes = {n['term'] for b in books['los-tres-cerditos']['story']['blocks']
                   for n in b['notes'] if isinstance(n, dict)}
    assert 'el estómago' not in story_notes

    # Same spelling is not necessarily the same sense or grammatical construction.
    retained = {
        ('harry-potter-piedra', '1'): {'la cuenta', 'la tapa', 'entre'},
        ('harry-potter-piedra', '2'): {'la manzana', 'la cuenta'},
        ('lola-lago-nota-falsa', '11'): {'el señor'},
        ('lola-lago-vacaciones-al-sol', '10'): {'el músico / la música'},
    }
    for (book_id, chapter_id), terms_to_retain in retained.items():
        chapter = next(c for c in books[book_id]['chapters'] if c['id'] == chapter_id)
        notes = {n['term'] for b in chapter['blocks'] for n in b['notes'] if isinstance(n, dict)}
        assert terms_to_retain.issubset(notes), (book_id, chapter_id)


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
    assert [c['id'] for c in first['chapter_catalog']] == ['one', 'two', 'three']
    assert first['chapter_catalog'][-1]['status'] == 'draft'
    assert all(set(c) == {'id', 'number', 'order', 'title', 'icon', 'status'} for c in first['chapter_catalog'])
    assert 'example' not in str(first['chapter_catalog'])
    assert (first['level'], first['vocabulary_min_level']) == ('B2', 'B1')
    assert next(b for b in books if b['id'] == 'other')['vocabulary_min_level'] == 'A1'


def test_harry_level_and_vocabulary_threshold_are_independent():
    book = next(b for b in load_books() if b['id'] == 'harry-potter-piedra')
    assert book['level'] == 'B2'
    assert book['vocabulary_min_level'] == 'B1'
    assert [(c['number'], c['title']) for c in book['chapters']] == [(1, 'El niño que vivió'), (2, 'El vidrio que se desvaneció')]
    catalog = book['chapter_catalog']
    assert [c['number'] for c in catalog] == list(range(1, 18))
    assert [c['order'] for c in catalog] == list(range(1, 18))
    assert [c['status'] for c in catalog] == ['published'] * 2 + ['draft'] * 15
    assert catalog[5]['title'] == 'El viaje desde el andén nueve y tres cuartos'
    assert catalog[13]['title'] == 'Norberto, el ridgeback noruego'
    assert catalog[-1]['title'] == 'El hombre con dos caras'


def test_draft_chapter_contents_do_not_leak_into_the_site(tmp_path):
    import json
    folder = tmp_path / 'book'
    (folder / 'chapters').mkdir(parents=True)
    (folder / 'book.json').write_text(json.dumps({'id': 'book', 'title': 'Book', 'author': 'Author',
        'level': 'B2', 'vocabulary_min_level': 'B1'}), encoding='utf-8')
    path = folder / 'chapters' / '1.json'
    draft = {'id': '1', 'number': 1, 'order': 1, 'title': 'First', 'status': 'draft',
             'blocks': [{'es': 'PRIVATE DRAFT'}], 'exercises': [{'prompt': 'PRIVATE EXERCISE'}]}
    path.write_text(json.dumps(draft), encoding='utf-8')
    book = load_books(tmp_path)[0]
    assert book['chapters'] == []
    assert len(book['chapter_catalog']) == 1
    assert 'PRIVATE' not in json.dumps(book)
    draft['status'] = 'published'
    draft['blocks'] = []
    path.write_text(json.dumps(draft), encoding='utf-8')
    import pytest
    with pytest.raises(ValueError):
        load_books(tmp_path)


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


def test_collection_rejects_broken_links_duplicates_and_nested_collections(tmp_path):
    import json
    import pytest
    base = dict(title='Title', author='Author', level='B1', vocabulary_min_level='A2')
    parent = dict(base, id='collection', kind='collection', books=['member'])
    member = dict(base, id='member', collection='collection')
    for name in ('collection', 'member'):
        (tmp_path / name).mkdir()
    def write(p, m):
        for name, data in (('collection', p), ('member', m)):
            (tmp_path / name / 'book.json').write_text(json.dumps(data), encoding='utf-8')
    write(parent, member)
    assert len(load_books(tmp_path)) == 2
    for p, m in [({**parent, 'books': ['member', 'member']}, member),
                 ({**parent, 'books': ['missing']}, member),
                 (parent, {**member, 'collection': 'missing'}),
                 (parent, {**member, 'level': 'A2'}),
                 (parent, {**member, 'kind': 'collection', 'books': ['collection']})]:
        write(p, m)
        with pytest.raises(ValueError):
            load_books(tmp_path)
