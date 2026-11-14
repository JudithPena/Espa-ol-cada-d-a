"""Editorial changes must not discard exceptions, exercise content, or course identity."""
import hashlib
import json
from pathlib import Path

from espanol.grammar import GRAMMAR, load_grammar


def test_all_units_preserve_notes_checks_practice_order_and_summaries():
    snapshots = json.loads((Path(__file__).parent / 'data/grammar_theory_preservation.json').read_text())
    paths = sorted(GRAMMAR.glob('[0-9]*.json'))
    assert len(paths) == len(snapshots) == 63
    for path in paths:
        u = json.loads(path.read_text())
        protected = {'titles': [s['title'] for s in u['sections']],
                     'notes': [s.get('notes', []) for s in u['sections']],
                     'checks': [s.get('check') for s in u['sections']],
                     'exercises': u['exercises'], 'learningOrder': u['learningOrder'], 'summary': u['summary']}
        digest = hashlib.sha256(json.dumps(protected, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        assert digest == snapshots[str(u['number'])], u['number']


def test_indefinite_article_forms_have_one_visual_paradigm():
    s = load_grammar()[3]['sections'][0]
    assert [r[0] for r in s['table']['rows']] == ['un', 'una', 'unos', 'unas']
    assert not s.get('wordGroups') and not s.get('formulas')
    assert all(phrase not in ' '.join(s['paragraphs']) for phrase in ['un libro', 'una mesa', 'unos libros', 'unas mesas'])
    assert s['illustration']['captionExamples'] is False
    # Original bilingual art legends still explain an enlarged image.
    assert s['illustration']['examples']


def test_theory_keeps_varied_presentations_and_distinctive_rules():
    units = load_grammar()
    assert sum(len(u['sections']) for u in units) == 259
    assert {s['presentation'] for u in units for s in u['sections']} == {'examples', 'comparison', 'paradigm'}
    required = {1: ['la pilota', 'la dependienta', 'la jefe'], 2: ['el radio', 'la pijama', 'gorila'],
                3: ['champúes', 'cómic', 'gafas'], 4: ['una pequeña águila', 'una águila'],
                5: ['Quiero ser bailarina', 'protestantes'], 6: ['la otra aula', 'las aulas'],
                7: ['de Ana', 'bombones'], 8: ['El Salvador', 'El Cairo', 'la India'],
                9: ['Hoy es', 'a la semana'], 10: ['jugar fútbol', 'He comprado una televisión'],
                11: ['pelo corto', 'lo'], 12: ['esta agua', 'В воспоминаниях нередко возможны оба варианта.'], 13: ['persona encantadora', 'charlatán'],
                14: ['nicaragüense', 'iranís'], 15: ['más bueno', 'más viejo', 'que mí'],
                16: ['No soy tan fuerte como tú', 'igual de'], 17: ['el libro más viejo', 'que he leído']}
    for number, phrases in required.items():
        text = json.dumps([{k: v for k, v in s.items() if k not in {'check', 'illustration'}} for s in units[number-1]['sections']], ensure_ascii=False)
        for phrase in phrases:
            assert phrase in text, (number, phrase)
