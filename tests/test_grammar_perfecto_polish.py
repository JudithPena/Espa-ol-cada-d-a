"""Published source items and safe revision boundaries for the perfecto rework."""
import json
from pathlib import Path
from espanol.grammar import load_grammar

def test_polish_preserves_every_published_source_item_and_answer():
    baseline=json.loads(Path('tests/data/grammar60_61_source_baseline.json').read_text(encoding='utf8'))
    for u in load_grammar():
        if str(u['number']) not in baseline: continue
        questions={q['sourceRef']:q for g in u['exercises'] for q in g['questions'] if q['sourceRef']!='extra'}
        assert set(questions)=={q['ref'] for q in baseline[str(u['number'])]}
        for q in baseline[str(u['number'])]:
            assert questions[q['ref']]['answers']==q['answers']

def test_changed_attempts_have_revisions_and_both_final_situations_are_routed():
    for u in [u for u in load_grammar() if u['number'] in (60,61)]:
        assert u['revision']==2
        final=u['exercises'][-1]
        assert u['learningOrder'][-2]=='exercise:'+final['id']
        assert set(final['theorySections'])==set(range(len(u['sections'])))
        changed=['check-2','check-3','60.2'] if u['number']==60 else ['check-1','check-2','61.3','61.4']
        groups={g['id']:g for g in [*[s['check'] for s in u['sections']],*u['exercises']]}
        assert all(groups[key]['revision']==2 for key in changed)
        if u['number']==61:
            assert all('has' not in q['inputFormat']['instruction'] for q in groups['61.4']['questions'])
