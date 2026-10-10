from espanol.markup import check_html, checkable, plain, tg_len, to_html, visible_len
from espanol.tokens import mixed_script_words, normalize_phrase, spanish_words


def test_to_html_formatting():
    html = to_html("**hola** _курсив_ ||спойлер|| ~~нет~~ `-ar`")
    assert html == ("<b>hola</b> <i>курсив</i> <tg-spoiler>спойлер</tg-spoiler> "
                    "<s>нет</s> <code>-ar</code>")
    assert check_html(html) == []


def test_html_is_escaped_and_code_is_not_formatted():
    assert to_html("a < b & c") == "a &lt; b &amp; c"
    assert to_html("`**x**`") == "<code>**x**</code>"


def test_fill_in_gap_is_not_italic():
    assert to_html("Yo ___ (hablar) español.") == "Yo ___ (hablar) español."


def test_plain_and_checkable():
    assert plain("**¡Hola!** ||Привет||") == "¡Hola! Привет"
    assert "si" not in checkable("`si` без значка")


def test_check_html_finds_problems():
    assert check_html("<b>не закрыт")
    assert check_html("<b><i>x</b></i>")
    assert check_html("<div>x</div>")


def test_lengths_count_utf16():
    assert tg_len("😀") == 2
    assert visible_len("<b>abc</b>") == 3


def test_spanish_words_skip_russian_digits_and_endings():
    text = "Глагол hablar: окончания -ar, -o; уровень A1; alto/a; nosotros/-as"
    assert spanish_words(text) == ["hablar", "alto", "nosotros"]


def test_mixed_script_detection():
    assert mixed_script_words("чоколáтэ и шоколад") == ["чоколáтэ"]


def test_normalize_phrase():
    assert normalize_phrase("¡Buenos días, María!") == " buenos días maría "
