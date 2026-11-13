"""A2 на сайте: формы прошедшего времени и императива, шаблоны ответов, письмо (compose) и разговор (chat)."""

from pathlib import Path

import pytest

from espanol import morphology as m
from espanol.course import ContentError, _alts, load_course, parse_block
from espanol.lexicon import Lexicon, generated_forms
from espanol.scenario import check, compose_passes
from espanol.site import site_data
from espanol.site_audio import audio_texts
from espanol.wordcards import load_cards

CONTENT = Path(__file__).resolve().parent.parent / "content"


@pytest.fixture(scope="module")
def site():
    return load_course(CONTENT / "site")


# ---------------------------------------------------------------- морфология A2

@pytest.mark.parametrize("verb, forms", [
    ("hablar", "hablé hablaste habló hablamos hablasteis hablaron"),
    ("comer", "comí comiste comió comimos comisteis comieron"),
    ("vivir", "viví viviste vivió vivimos vivisteis vivieron"),
    ("buscar", "busqué buscaste buscó buscamos buscasteis buscaron"),
    ("llegar", "llegué llegaste llegó llegamos llegasteis llegaron"),
    ("empezar", "empecé empezaste empezó empezamos empezasteis empezaron"),
    ("leer", "leí leíste leyó leímos leísteis leyeron"),
    ("pedir", "pedí pediste pidió pedimos pedisteis pidieron"),
    ("dormir", "dormí dormiste durmió dormimos dormisteis durmieron"),
    ("ir", "fui fuiste fue fuimos fuisteis fueron"),
    ("ser", "fui fuiste fue fuimos fuisteis fueron"),
    ("estar", "estuve estuviste estuvo estuvimos estuvisteis estuvieron"),
    ("tener", "tuve tuviste tuvo tuvimos tuvisteis tuvieron"),
    ("hacer", "hice hiciste hizo hicimos hicisteis hicieron"),
    ("decir", "dije dijiste dijo dijimos dijisteis dijeron"),
    ("dar", "di diste dio dimos disteis dieron"),
    ("ver", "vi viste vio vimos visteis vieron"),
    ("levantarse", "levanté levantaste levantó levantamos levantasteis levantaron"),
])
def test_preterite(verb, forms):
    assert m.preterite(verb) == forms.split()


@pytest.mark.parametrize("verb, forms", [
    ("hablar", "hablaba hablabas hablaba hablábamos hablabais hablaban"),
    ("comer", "comía comías comía comíamos comíais comían"),
    ("ser", "era eras era éramos erais eran"),
    ("ir", "iba ibas iba íbamos ibais iban"),
    ("ver", "veía veías veía veíamos veíais veían"),
])
def test_imperfect(verb, forms):
    assert m.imperfect(verb) == forms.split()


@pytest.mark.parametrize("verb, forms", [
    ("hablar", "habla hable hablad hablen"),
    ("comer", "come coma comed coman"),
    ("cerrar", "cierra cierre cerrad cierren"),
    ("volver", "vuelve vuelva volved vuelvan"),
    ("tener", "ten tenga tened tengan"),
    ("hacer", "haz haga haced hagan"),
    ("ir", "ve vaya id vayan"),
    ("decir", "di diga decid digan"),
    ("buscar", "busca busque buscad busquen"),
    ("seguir", "sigue siga seguid sigan"),
])
def test_imperative(verb, forms):
    assert m.imperative(verb) == forms.split()


def test_past_forms_are_unlocked_by_their_own_features(site):
    """Правильные формы indefinido открывает preterite, особые основы — только preterite_irregular."""
    by_es = {item.es: item for item in site.items}
    hablar, tener = by_es["hablar"], by_es["tener"]
    assert "hablé" in generated_forms(hablar, {"preterite"})
    assert "tuve" not in generated_forms(tener, {"preterite"})
    assert "tuve" in generated_forms(tener, {"preterite_irregular"})
    assert "hablaba" in generated_forms(hablar, {"imperfect"}) and "hable" in generated_forms(hablar, {"imperative"})
    assert "hablé" not in generated_forms(hablar, {"present_ar", "participle"})


# ---------------------------------------------------------------- шаблоны ответов

def test_answer_templates_expand_optional_parts_and_alternatives():
    assert _alts("(Yo) vivo en Madrid (desde enero) | Vivo aquí") == [
        "Yo vivo en Madrid desde enero", "Yo vivo en Madrid", "Vivo en Madrid desde enero", "Vivo en Madrid", "Vivo aquí"]
    assert _alts("[Tienes que/Puedes/Lo mejor es] hablar más") == ["Tienes que hablar más", "Puedes hablar más", "Lo mejor es hablar más"]
    assert _alts("(Sí,) sé hablar inglés") == ["Sí, sé hablar inglés", "Sé hablar inglés"]
    assert _alts("Un café, por favor | Por favor, un café") == ["Un café, por favor", "Por favor, un café"]   # обычный перечень не меняется
    assert _alts("14/11") == ["14/11"]   # «/» вне квадратных скобок — обычный знак


def test_answer_template_errors():
    with pytest.raises(ContentError):
        _alts("(Yo vivo en Madrid")
    with pytest.raises(ContentError):
        _alts(" ".join("[a/b/c/d]" for _ in range(6)))


# ---------------------------------------------------------------- письмо и разговор

COMPOSE = {"compose": {"title": "О себе", "free": True, "items": [{
    "q": "Напишите, зачем вы учите испанский.", "words": [3, 20],
    "checks": [{"label": "есть para или porque", "any": ["para", "porque"]},
               {"label": "после para — инфинитив", "if": ["para"], "re": r"para \w+(ar|er|ir)\b"}],
    "sample": "Estudio español para viajar."}]}}


def test_compose_checks_match_the_page_rules():
    it = parse_block(COMPOSE, "t").data["items"][0]
    assert all(compose_passes(it, "Estudio español para viajar."))
    assert all(compose_passes(it, "ESTUDIO ESPAÑOL PORQUE VIVO AQUÍ"))          # регистр и знаки не важны
    assert compose_passes(it, "Para viajar") == [False, True, True]             # мало слов
    assert compose_passes(it, "Estudio español para viajo mucho") == [True, True, False]   # после para не инфинитив
    assert compose_passes(it, "Me gusta mucho el idioma") == [True, False, True]            # условие if не сработало → не мешает


def test_compose_regex_ignores_accents_like_the_text():
    """Текст ученика сравнивается без ударений: выражение с ударениями должно находить и «vivía», и «vivia»."""
    item = {"compose": {"title": "О себе", "free": True, "items": [{
        "q": "Где вы жили?", "checks": [{"label": "imperfecto", "re": r"\b\w+(aba|ía)\b|\b(éramos|íbamos)\b"}],
        "sample": "Vivía en Kiev."}]}}
    it = parse_block(item, "t").data["items"][0]
    assert "í" not in it["checks"][0]["re"] and "é" not in it["checks"][0]["re"]
    assert all(compose_passes(it, "Vivía en Kiev."))
    assert all(compose_passes(it, "Vivia en Kiev"))                 # ученик забыл ударение — признак всё равно есть
    assert all(compose_passes(it, "Íbamos al mar."))
    assert compose_passes(it, "Vivo en Kiev.") == [False]


def test_compose_sample_must_pass_its_own_checks():
    bad = {"compose": {"items": [{"q": "Зачем?", "checks": [{"label": "есть para", "any": ["para"]}], "sample": "Porque sí."}]}}
    with pytest.raises(ContentError):
        parse_block({"compose": {"items": [{"q": "Зачем?", "checks": [{"label": "x"}], "sample": "Para viajar."}]}}, "t")
    from espanol.scenario import _compose_issues
    assert _compose_issues(parse_block(bad, "t").data["items"][0], "compose")


def test_chat_block_shapes():
    block = parse_block({"chat": {"title": "В кафе", "with": "Camarero", "turns": [
        {"say": "¡Hola! | Привет!", "build": "Muy bien, gracias."},
        {"say": "¿Cómo te llamas? | Как тебя зовут?", "task": "Вас зовут Ана.", "write": "(Yo) me llamo Ana | Soy Ana"},
        {"say": "¿Café? | Кофе?", "task": "Вы согласны.", "choose": "Sí, por favor. | No, gracias."},
        {"say": "¡Hasta luego! | Пока!"}]}}, "t")
    d = block.data
    assert [it["kind"] for it in d["items"]] == ["build", "write", "choose"]
    assert d["items"][1]["answers"] == ["Yo me llamo Ana", "Me llamo Ana", "Soy Ana"]
    assert d["end"] == [("Camarero", "¡Hasta luego!", "Пока!")]
    with pytest.raises(ContentError):   # реплика без ответа — только в конце
        parse_block({"chat": {"with": "Ana", "turns": [{"say": "Hola"}, {"say": "¿Qué tal?", "build": "Muy bien."}]}}, "t")


def test_a2_units_validate_and_build(site):
    a2 = [u for u in site.units if u.level == "A2"]
    assert a2 and a2[0].id == "espanol_y_yo"
    lex = Lexicon(site)
    assert [str(i) for i in lex.check() + check(site, lex)] == []
    data = site_data(site, load_cards(CONTENT), units={a2[0].number})
    kinds = {b["t"] for lesson in data["lessons"] for b in lesson["blocks"]}
    assert {"compose", "chat"} <= kinds
    chat = next(b for lesson in data["lessons"] for b in lesson["blocks"] if b["t"] == "chat")
    voice = chat["cast"][chat["who"]]["v"]
    texts = audio_texts(data)
    assert all(f"@{voice}|{it['line'][3]}" in texts for it in chat["items"])   # реплики собеседника — его голосом


def test_open_tasks_are_not_review_material(site):
    """Навык, который стоит у письма или разговора, обязан иметь и обычное задание: только оно идёт в повторение."""
    from espanol.scenario import _skill_material
    assert _skill_material(site) == []
