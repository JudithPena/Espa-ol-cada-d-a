from espanol.site import load_books


def test_book_chapters_have_complete_readable_blocks():
    books = load_books()
    assert books
    for book in books:
        assert book['title'] and book['author'] and book['chapter']
        assert book['blocks']
        for block in book['blocks']:
            assert all(block[key].strip() for key in ('title', 'es', 'ru', 'pronouns'))
            assert block['notes'] and all(note.strip() for note in block['notes'])
            for lang in ('es', 'ru'):
                assert all(mark in block[lang] for mark in block.get('marks', {}).get(lang, []))
