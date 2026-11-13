"""A question must not be the previous sentence again with the answer already shown.

13.11.2026 (жалоба автора на 11.3): «¿Qué pendientes quieres, ___ largos o los cortos?»
и сразу «¿Los largos o ___ cortos?» — ответ второго вопроса уже стоял в первом.
Задание книги с двумя пропусками не делим на два соседних вопроса по одной фразе.
"""
import re

from espanol.grammar import load_grammar


def norm(text: str) -> str:
    return ' '.join(re.sub(r'[¿?¡!.,;:—–«»"…()*]', ' ', text.lower()).split())


def filled(q: dict) -> str | None:
    prompt, answers = q.get('prompt', ''), q.get('answers') or []
    if prompt.count('___') != 1 or not prompt.replace('___', '').strip() or not answers:
        return None
    answer = '' if answers[0].lower().startswith('без') else answers[0]
    return norm(prompt.replace('___', f' {answer} '))


def test_no_question_repeats_the_previous_sentence_with_its_answer():
    leaks = []
    for unit in load_grammar():
        groups = [s['check'] for s in unit['sections'] if s.get('check')] + unit['exercises']
        for group in groups:
            qs = group['questions']
            for j, later in enumerate(qs):
                text = filled(later)
                if not text or len(text.split()) < 3:
                    continue
                for earlier in qs[max(0, j - 2):j]:
                    shown = filled(earlier)
                    if shown and earlier['prompt'] != later['prompt'] and re.search(rf'(^| ){re.escape(text)}( |$)', shown):
                        leaks.append((group['id'], j + 1, later['prompt']))
    assert not leaks, leaks
