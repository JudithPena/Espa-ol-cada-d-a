"""Theory examples must not give away the exercise items of the same unit.

13.11.2026 (просьба автора): в теории юнита 11 стояло «el del pelo corto», а в
упражнении 11.2 сразу спрашивали «¿Quién es Alberto? ___ del pelo corto.».
Упражнения взяты из книги и не меняются; меняются примеры теории. Сравнение то же,
что у мини-проверок (test_grammar_check_dedup): общий отрезок из четырёх слов подряд
или почти та же фраза. Сама изучаемая конструкция («por la tarde», «¿Qué hora es?»)
допустима — такие случаи перечислены в ALLOWED с причиной.
"""
import difflib
import json
import re

from espanol.grammar import GRAMMAR
from test_grammar_check_dedup import filled, longest_run, words

# (unit, theory text): why the overlap is unavoidable.
ALLOWED: dict[tuple[int, str], str] = {
    (9, 'Es la una y veinte.'): '«Es la una y …» — сама изучаемая форма; в упражнении другие минуты.',
    (9, '¿Qué hora es? Es la una y veinte.'): 'Вопрос «¿Qué hora es?» и форма «Es la una» — сама изучаемая конструкция.',
    (9, 'por la noche'): 'Выражения por la mañana / tarde / noche — само правило, их нельзя не назвать.',
    (9, 'por la tarde'): 'Выражения por la mañana / tarde / noche — само правило, их нельзя не назвать.',
    (51, 'la semana que viene'): 'Список выражений будущего времени — сама изучаемая лексика.',
    (51, 'el año que viene'): 'Список выражений будущего времени — сама изучаемая лексика.',
    (52, '¿Cuánto tiempo hace que…?'): 'Рамка вопроса «¿Cuánto tiempo hace que…?» — сама изучаемая конструкция.',
    (52, '¿Cuánto tiempo hace que trabajas aquí?'): 'Рамка «¿Cuánto tiempo hace que…?» — сама конструкция; продолжение другое.',
    (55, 'A mí me gusta'): 'Сочетание a mí + me gusta — само изучаемое правило.',
    (58, 'la semana pasada'): 'Список выражений прошедшего времени — сама изучаемая лексика.',
    (61, 'En mi vida he visto algo parecido.'): '«En mi vida he…» в значении «никогда» — сама изучаемая конструкция; глагол другой.',
    (30, '¿De quién es…?'): 'Рамка вопроса «¿De quién es…?» — сама изучаемая конструкция, без продолжения.',
}


def theory_pieces(unit: dict) -> list[tuple[str, str]]:
    out = []

    def add(value, where):
        if isinstance(value, str):
            out.extend((p.strip(), where) for p in re.split(r'→|\n', value) if p.strip())

    for i, s in enumerate(unit['sections']):
        where = f'теория, блок {i + 1}'
        for e in s.get('examples', []):
            add(e[0], where)
        for g in s.get('wordGroups', []):
            for w in g.get('words', []):
                add(w[0] if isinstance(w, list) else w, where)
        for d in s.get('dialogues', []):
            lines = [line[0] for line in d['lines']]
            for line in lines:
                add(line, where)
            for a, b in zip(lines, lines[1:]):
                add(a + ' ' + b, where)
        for e in (s.get('illustration') or {}).get('examples', []):
            add(e[0], where)
        for sc in s.get('schemes', []):
            add(sc.get('from', ''), where)
            add(sc.get('to', ''), where)
        for row in (s.get('table') or {}).get('rows', []):
            for cell in (row[:-1] if len(row) > 1 else row):
                add(cell, where)
        for text in s.get('paragraphs', []) + s.get('notes', []):
            for q in re.findall(r'`([^`]+)`', text) + re.findall(r'«([^»]+)»', text):
                add(q, where)
    return out


def repeats(unit: dict) -> list[str]:
    pieces = [(words(t), t, where) for t, where in theory_pieces(unit)]
    found = []
    for e in unit['exercises']:
        for n, q in enumerate(e['questions'], 1):
            sentence = words(filled(q))
            if len(sentence) < 3:
                continue
            for target, text, where in pieces:
                if len(target) < 3 or (unit['number'], text) in ALLOWED:
                    continue
                ratio = difflib.SequenceMatcher(None, sentence, target, autojunk=False).ratio()
                if longest_run(sentence, target) >= 4 or ratio >= 0.75:
                    found.append(f'юнит {unit["number"]}, {where}: «{text}» повторяет упражнение '
                                 f'{e["id"]} №{n}: «{filled(q)}»')
    return found


def units():
    return [json.loads(p.read_text(encoding='utf-8')) for p in sorted(GRAMMAR.glob('[0-9]*.json'))]


def test_theory_does_not_repeat_exercises():
    found = [line for u in units() for line in repeats(u)]
    assert not found, f'{len(found)}:\n' + '\n'.join(found)


def preview_text(pv: dict) -> str:
    if pv.get('gapParts'):
        answers = pv.get('gapAnswers', [])
        return ''.join(part + (answers[i] if i < len(answers) else '') for i, part in enumerate(pv['gapParts']))
    if pv.get('sentenceParts'):
        first, rest = pv['sentenceParts']
        return first + (pv.get('displayAnswer') or pv['answer']) + rest
    return pv.get('source', '').replace('___', pv.get('answer', ''))


def test_exercise_samples_do_not_repeat_exercises():
    """«Образец» перед упражнением показывает ответ до вопросов — он тоже не подсказывает задания."""
    found = []
    for u in units():
        for e in u['exercises']:
            pv = e.get('preview') or {}
            if not pv.get('source'):
                continue
            sample = words(preview_text(pv))
            for e2 in u['exercises']:
                for n, q in enumerate(e2['questions'], 1):
                    sentence = words(filled(q))
                    if not sentence:
                        continue
                    same = sentence == sample
                    close = min(len(sentence), len(sample)) >= 3 and (
                        longest_run(sentence, sample) >= 4
                        or difflib.SequenceMatcher(None, sentence, sample, autojunk=False).ratio() >= 0.75)
                    if same or close:
                        found.append(f'юнит {u["number"]}, образец {e["id"]}: «{preview_text(pv)}» повторяет '
                                     f'{e2["id"]} №{n}: «{filled(q)}»')
    assert not found, '\n'.join(found)


def test_allowed_overlaps_still_exist():
    texts = {u['number']: {t for t, _ in theory_pieces(u)} for u in units()}
    assert all(text in texts[unit] for unit, text in ALLOWED), [k for k in ALLOWED if k[1] not in texts[k[0]]]


def test_detector_catches_the_reported_repeat():
    unit = {'number': 0, 'sections': [{'wordGroups': [{'words': [['el del pelo corto', '…']]}]}],
            'exercises': [{'id': '11.2', 'questions': [{'prompt': '¿Quién es Alberto? ___ del pelo corto.',
                                                       'answers': ['el']}]}]}
    assert repeats(unit)
    unit['sections'][0]['wordGroups'][0]['words'][0][0] = 'la de los ojos verdes'
    assert not repeats(unit)
