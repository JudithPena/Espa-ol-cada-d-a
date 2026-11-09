from espanol.site import load_books


def test_book_chapters_have_complete_readable_blocks():
    books = load_books()
    assert books
    for book in books:
        assert book['title'] and book['author'] and book['chapter']
        assert book['blocks']
        for block in book['blocks']:
            assert all(block[key].strip() for key in ('title', 'es', 'ru', 'pronouns'))
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
