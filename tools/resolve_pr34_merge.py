#!/usr/bin/env python3
"""Resolve precisely the two known PR34 conflicts after git merge --no-commit."""
from pathlib import Path
import re
import subprocess

PLAYER=Path("espanol/grammar_player.js")
TEST=Path("tests/site_grammar.test.cjs")
PAT=re.compile(r"(?ms)^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> origin/claude/charming-cerf-bzze60\n")

def replace_once(s,a,b):
    if s.count(a)!=1:
        raise RuntimeError(f"Expected one match, got {s.count(a)}: {a[:120]}")
    return s.replace(a,b,1)

def select_player(i, ours, theirs):
    if i in (0,1,4):
        return ours
    if i==2:
        return """    if(!response.good) {
      gRecordError(attempt,step.qi,response.value);
      if(gOutOfLives(group,attempt.errors)) attempt.status='failed';
    } else if(group.questions.every((_,i)=>attempt.responses[i]?.good || attempt.responses[i]?.correction?.good)) {
"""
    if i==3:
        return "  if(!response.good) gRecordError(attempt,step.qi,response.value);\n  if(gOutOfLives(group,attempt.errors)) attempt.status='failed';\n"
    if i in (5,6):
        return ours
    raise RuntimeError(f"Unexpected player conflict #{i}")

def resolve(path,choose,expected):
    s=path.read_text()
    out=[]
    end=0
    conflicts=[]
    for i,m in enumerate(PAT.finditer(s)):
        out.append(s[end:m.start()])
        ours,theirs=m.group(1),m.group(2)
        conflicts.append((len(ours),len(theirs)))
        out.append(choose(i,ours,theirs))
        end=m.end()
    out.append(s[end:])
    if len(conflicts)!=expected:
        raise RuntimeError(f"{path}: expected {expected} conflicts, got {len(conflicts)}: {conflicts}")
    merged="".join(out)
    if "<<<<<<<" in merged or ">>>>>>>" in merged:
        raise RuntimeError(f"Unresolved markers in {path}")
    path.write_text(merged)
    print(path,len(conflicts),"resolved",conflicts,flush=True)

def main():
    missing=subprocess.check_output(["git","diff","--name-only","--diff-filter=U"],text=True).splitlines()
    if set(missing)!={str(PLAYER),str(TEST)}:
        raise RuntimeError(f"Unexpected conflicts: {missing}")
    resolve(PLAYER,select_player,7)
    resolve(TEST,lambda i,ours,theirs:ours,10)
    p=PLAYER.read_text()
    # Keep the target branch's detailed three-error history and both voluntary controls.
    # The third mistake stays at the original question but now includes every
    # saved wrong submission and the accepted solutions from the target branch.
    token=chr(36)
    p=replace_once(p, token+'{content}</div></div>',
      token+'{content}'+token+'{failed ? gFailureAnalysis(attempt,unit,group) : ""}</div></div>')
    p=replace_once(p,
      "  if(!exhausted)return wrong.length\n    ? '<p>Проверь '+wrong.map(i=>'пропуск '+(i+1)).join(', ')+'. Правильные слова пока скрыты.</p>'\n    : '<p>Проверь правило и попробуй ещё раз. Правильный ответ пока скрыт.</p>';",
      "  if(!exhausted) return (wrong.length\n    ? '<p>Проверь '+wrong.map(i=>'пропуск '+(i+1)).join(', ')+'. Правильные слова пока скрыты.</p>'\n    : '<p>Проверь правило и попробуй ещё раз. Правильный ответ пока скрыт.</p>') + (q.retryHint ? '<p>'+esc(q.retryHint)+'</p>' : '');")
    # Existing new tests in the target expect the old internal recovery flag.
    # With this PR, failure stays on the original question; only an explicit click
    # uses G.recovery to open theory. Preserve their actual coverage and update
    # those internal-state assertions to match the approved behavior.
    t=TEST.read_text()
    t=replace_once(t,"gGroups(gUnit()).find(g=>g.id===G.recovery),a=gAttempt","gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group),a=gAttempt")
    t=replace_once(t,"gGroups(gUnit()).find(g=>g.id===G.recovery)).status","gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group)).status")
    t=replace_once(t,"data-greview-theory>Вернуться к теории","data-greview-theory>Повторить правило")
    t=replace_once(t,"assert.ok(r('gPlayerView()').includes('Вернуться к теории'));","assert.ok(r('gPlayerView()').includes('Повторить правило'));")
    t=replace_once(t,"assert.equal(r('G.recovery'),'15.3');","assert.ok(!r('G.recovery'));")
    t=t.replace("assert.ok(r('G.recovery'));","assert.ok(!r('G.recovery'));")
    t=replace_once(t,'assert.equal(r("gErrorLimit(COURSE.grammar[0].sections[0].check)"),null);','assert.equal(r("gErrorLimit(COURSE.grammar[0].sections[0].check)"),3);')
    TEST.write_text(t)
    PLAYER.write_text(p)
    subprocess.check_call(["git","add",str(PLAYER),str(TEST)])
    subprocess.check_call(["git","diff","--check"])
    print("Merged code has no conflict markers.",flush=True)
if __name__=="__main__":
    main()
