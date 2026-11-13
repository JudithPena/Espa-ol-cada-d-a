"""Mini-checks must not repeat theory examples or exercise items of the same unit.

GRAMMAR_UNIT_GUIDE.md §6.6 and §7: «Предложения не повторяют примеры теории и вопросы
упражнений». A mini-check sentence (prompt with the correct answer filled in) is compared
with every Spanish example of the unit's theory and every exercise item. It fails when it
shares four words in a row with one of them or has nearly the same word sequence (the same
sentence with one word swapped). Sharing only the studied construction itself
(«a El Salvador», «la una», «ese mismo año») is allowed.
"""
import difflib
import json
import re
from pathlib import Path

from espanol.grammar import GRAMMAR

# (unit, section index, question index from 1): why the overlap is unavoidable.
ALLOWED = {
    (42, 3, 1): 'Вопрос «¿Qué hora es?» — сама изучаемая реплика; ответ на него проверяется вариантами.',
    (55, 1, 2): '«¿Le gusta a usted…?» — сама изучаемая конструкция с уточнением a usted; остальная фраза другая.',
}

CYRILLIC = re.compile('[а-яё]', re.I)


def words(text: str) -> list[str]:
    text = re.sub(r'(?i)без артикля|∅', ' ', text.replace('**', '').replace('`', ''))
    return [w for w in re.sub(r'[^\wñáéíóúü]+', ' ', text.lower()).split() if not CYRILLIC.search(w)]


def filled(q: dict) -> str:
    prompt, answer = q.get('prompt', ''), (q.get('answers') or [''])[0]
    gaps = prompt.count('___')
    if gaps > 1 and ' / ' in answer:
        parts = answer.split(' / ')
    elif gaps > 1 and len(answer.split()) == gaps:
        parts = answer.split()
    else:
        parts = [answer] * max(gaps, 1)
    for part in parts:
        prompt = prompt.replace('___', part, 1)
    return prompt


def theory_texts(unit: dict) -> list[tuple[str, str]]:
    out = []

    def add(value, where):
        if isinstance(value, list):
            for item in value:
                add(item, where)
        elif isinstance(value, str):
            out.extend((piece, where) for piece in re.split(r'→|\n', value) if piece.strip())

    for i, s in enumerate(unit['sections']):
        where = f'теория, блок {i + 1}'
        for e in s.get('examples', []):
            add(e[0], where)
        for g in s.get('wordGroups', []):
            for w in g.get('words', []):
                add(w[0] if isinstance(w, list) else w, where)
        lines_sets = [[l[0] for l in d['lines']] for d in s.get('dialogues', [])]
        lines_sets.append([e[0] for e in (s.get('illustration') or {}).get('examples', [])])
        for lines in lines_sets:
            add(lines, where)
            add([a + ' ' + b for a, b in zip(lines, lines[1:])], where)
        for sc in s.get('schemes', []):
            add([sc.get('from', ''), sc.get('to', '')], where)
        for row in (s.get('table') or {}).get('rows', []):
            add(row[:-1] if len(row) > 1 else row, where)
        for text in s.get('paragraphs', []) + s.get('notes', []):
            add(re.findall(r'`([^`]+)`', text) + re.findall(r'«([^»]+)»', text), where)
    return out


def longest_run(a: list[str], b: list[str]) -> int:
    match = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return match.size


def repeats(unit: dict) -> list[str]:
    targets = theory_texts(unit) + [
        (filled(q), f'упражнение {e["id"]} №{n}')
        for e in unit['exercises'] for n, q in enumerate(e['questions'], 1)]
    targets = [(words(text), text, where) for text, where in targets]
    found = []
    for si, s in enumerate(unit['sections']):
        for qi, q in enumerate((s.get('check') or {}).get('questions', []), 1):
            if (unit['number'], si, qi) in ALLOWED:
                continue
            sentence = words(filled(q))
            if len(sentence) < 3:
                continue
            for target, text, where in targets:
                if len(target) < 3:
                    continue
                ratio = difflib.SequenceMatcher(None, sentence, target, autojunk=False).ratio()
                if longest_run(sentence, target) >= 4 or ratio >= 0.75:
                    found.append(f'юнит {unit["number"]}, мини-проверка блока {si + 1}, вопрос {qi}: '
                                 f'«{filled(q)}» повторяет {where}: «{text}»')
                    break
    return found


def test_mini_checks_do_not_repeat_theory_or_exercises():
    found = []
    for path in sorted(GRAMMAR.glob('[0-9]*.json')):
        found += repeats(json.loads(path.read_text(encoding='utf-8')))
    assert not found, '\n'.join(found)


def test_allowed_overlaps_still_exist():
    units = {json.loads(p.read_text(encoding='utf-8'))['number']: json.loads(p.read_text(encoding='utf-8'))
             for p in GRAMMAR.glob('[0-9]*.json')}
    for unit, section, question in ALLOWED:
        assert units[unit]['sections'][section]['check']['questions'][question - 1]


def test_detector_catches_the_reported_repeat():
    unit = {'number': 0, 'sections': [{
        'wordGroups': [{'words': [['el del pelo corto', 'тот, у которого короткие волосы']]}],
        'check': {'questions': [{'prompt': '¿Quién es Alberto? ___ del pelo corto.', 'answers': ['el']}]}}],
        'exercises': [{'id': '11.2', 'questions': [
            {'prompt': '¿Quién es Alberto? ___ del pelo corto.', 'answers': ['el']}]}]}
    assert repeats(unit)
    unit['sections'][0]['check']['questions'][0] = {'prompt': '¿Quién es tu profesor? ___ de las gafas.',
                                                    'answers': ['el']}
    assert not repeats(unit)
