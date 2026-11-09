from espanol.site import load_books


def test_book_chapters_have_complete_readable_blocks():
    books = load_books()
    assert books
    for book in books:
        assert book['title'] and book['author'] and book['chapter']
        assert book['blocks']
        for block in book['blocks']:
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
    first = book['blocks'][0]
    entries = {n['term']: n for n in first['notes'] if isinstance(n, dict)}
    for term, es, ru in [('corpulento', 'corpulento', 'крупный'),
                         ('rollizo', 'rollizo', 'полный'),
                         ('el taladro', 'taladros', 'дрели')]:
        assert es in entries[term]['es'] and es in first['es']
        assert ru in entries[term]['ru'] and ru in first['ru']


def test_pronoun_distinctions_in_first_chapter():
    book = next(b for b in load_books() if b['title'] == 'Harry Potter y la piedra filosofal')
    def entry(form):
        return next(x for block in book['blocks'] for x in block['pronouns'] if x['es'] == form)
    assert 'пассивной' in entry('Se supiera')['explanation']
    assert 'пассивной' in entry('Se descubría')['explanation']
    assert 'безличную' in entry('Si se la comparaba')['explanation']
    assert 'заменяет le' in entry('Explicárselo')['explanation']
    assert 'не заменяет le' in entry('Se lo pasó por los ojos')['explanation']
