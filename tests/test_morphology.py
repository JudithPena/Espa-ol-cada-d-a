import pytest

from espanol import morphology as m


@pytest.mark.parametrize("word, expected", [
    ("libro", "libros"),
    ("café", "cafés"),
    ("hotel", "hoteles"),
    ("reloj", "relojes"),
    ("lápiz", "lápices"),
    ("canción", "canciones"),
    ("inglés", "ingleses"),
    ("autobús", "autobuses"),
    ("lunes", "lunes"),
    ("mes", "meses"),
    ("móvil", "móviles"),
    ("fin de semana", "fines de semana"),
])
def test_plural(word, expected):
    assert m.plural(word) == expected


@pytest.mark.parametrize("spec, expected", [
    ("alto/a", ["alto", "alta"]),
    ("español/a", ["español", "española"]),
    ("inglés/a", ["inglés", "inglesa"]),
    ("alemán/a", ["alemán", "alemana"]),
    ("trabajador/a", ["trabajador", "trabajadora"]),
    ("grande", ["grande"]),
])
def test_adjective_forms(spec, expected):
    assert m.adjective_forms(spec) == expected


@pytest.mark.parametrize("verb, forms", [
    ("hablar", "hablo hablas habla hablamos habláis hablan"),
    ("comer", "como comes come comemos coméis comen"),
    ("vivir", "vivo vives vive vivimos vivís viven"),
    ("querer", "quiero quieres quiere queremos queréis quieren"),
    ("poder", "puedo puedes puede podemos podéis pueden"),
    ("pedir", "pido pides pide pedimos pedís piden"),
    ("jugar", "juego juegas juega jugamos jugáis juegan"),
    ("tener", "tengo tienes tiene tenemos tenéis tienen"),
    ("hacer", "hago haces hace hacemos hacéis hacen"),
    ("salir", "salgo sales sale salimos salís salen"),
    ("levantarse", "levanto levantas levanta levantamos levantáis levantan"),
    ("acostarse", "acuesto acuestas acuesta acostamos acostáis acuestan"),
    ("ser", "soy eres es somos sois son"),
    ("ir", "voy vas va vamos vais van"),
])
def test_present(verb, forms):
    assert m.present(verb) == forms.split()


@pytest.mark.parametrize("verb, gerund, participle", [
    ("hablar", "hablando", "hablado"),
    ("comer", "comiendo", "comido"),
    ("leer", "leyendo", "leído"),
    ("dormir", "durmiendo", "dormido"),
    ("pedir", "pidiendo", "pedido"),
    ("ir", "yendo", "ido"),
    ("hacer", "haciendo", "hecho"),
    ("ver", "viendo", "visto"),
    ("escribir", "escribiendo", "escrito"),
    ("volver", "volviendo", "vuelto"),
])
def test_gerund_and_participle(verb, gerund, participle):
    assert m.gerund(verb) == gerund
    assert m.participle(verb) == participle


def test_verb_detection():
    assert m.is_verb("hablar") and m.is_verb("ir") and m.is_verb("levantarse")
    assert not m.is_verb("ayer") and not m.is_verb("mujer") and not m.is_verb("casa")


def test_present_groups():
    assert m.present_group("hablar") == "regular_ar"
    assert m.present_group("vivir") == "regular_er_ir"
    assert m.present_group("hacer") == "regular_er_ir"  # неправильная только форма yo
    assert m.present_group("querer") == "stem"
    assert m.present_group("ser") == "irregular"


def test_reflexive_infinitives():
    assert m.reflexive_infinitives("levantarse") == [
        "levantarme", "levantarte", "levantarse", "levantarnos", "levantaros"]
    assert m.reflexive_infinitives("hablar") == []
