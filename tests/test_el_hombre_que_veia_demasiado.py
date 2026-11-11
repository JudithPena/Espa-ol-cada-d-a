"""Source- and structure-level checks for the A1 graded reader."""
import re

from espanol.site import load_books


def test_el_hombre_que_veia_demasiado_is_a_published_a1_story():
    matched = [book for book in load_books() if book["id"] == "el-hombre-que-veia-demasiado"]
    assert len(matched) == 1
    book = matched[0]
    assert book["kind"] == "story"
    assert (book["level"], book["vocabulary_min_level"]) == ("A1", "A1")
    assert book["title"] == "El hombre que veía demasiado"
    assert book["author"] == "Loreto de Miguel y Alba Santos"
    assert book["annotation"] and len(book["annotation"]) <= 350
    assert book["cover"].startswith("data:image/webp;base64,")
    assert book["icon"] == "📷"

    story = book["story"]
    assert story["status"] == "published"
    assert len(story["blocks"]) == 29
    text = "\n".join(block["es"] for block in story["blocks"])
    assert text.startswith("—Buenos días. ¿El detective Rey, por favor?")
    assert text.endswith("unos maravillosos ojos azules.")
    assert len(re.findall(r"\w+", text)) > 3400

    images = [image for block in story["blocks"] for image in block.get("images", [])]
    assert len(images) == 3
    assert all(image["src"].startswith("data:image/webp;base64,") and image["alt"] for image in images)


def test_el_hombre_que_veia_demasiado_glosses_and_pronouns_have_anchors():
    book = next(b for b in load_books() if b["id"] == "el-hombre-que-veia-demasiado")
    story = book["story"]
    notes_count = pronouns_count = 0
    for block in story["blocks"]:
        assert block["title"] and block["es"] and block["ru"]
        assert block["pronouns"] is not None
        assert 50 <= len(re.findall(r"\w+", block["es"])) <= 185
        for note in block["notes"]:
            if isinstance(note, str):
                continue  # Historical / cultural context, not a lexical highlight.
            notes_count += 1
            assert note["term"] and note["explanation"]
            for language in ("es", "ru"):
                assert note[language]
                for fragment in note[language]:
                    assert fragment in block[language], (block["title"], language, fragment)
        for point in block["pronouns"]:
            pronouns_count += 1
            assert point["es"] and point["translation"] and point["explanation"] and point["base"]
        for image in block.get("images", []):
            before = image.get("before")
            if before:
                assert block["es"].count(before) == 1
                at = block["es"].index(before)
                assert at == 0 or block["es"][at - 1] == "\n"
    assert notes_count >= 160
    assert pronouns_count >= 80
    # These words are taught already in the site's A0 course.
    terms = {note["term"] for b in story["blocks"] for note in b["notes"] if isinstance(note, dict)}
    assert not terms.intersection({"el italiano", "la foto", "el bolígrafo", "el/la periodista"})
