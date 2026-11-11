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
      if(gOutOfLives(group,attempt.errors)) { attempt.status='failed'; G.recovery=group.id; }
    } else if(group.questions.every((_,i)=>attempt.responses[i]?.good || attempt.responses[i]?.correction?.good)) {
"""
    if i in (3,5,6):
        return theirs
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
    p=replace_once(p,
      '<button class="btn wide" data-greview-theory>Вернуться к теории</button>',
      '<button class="btn ghost" data-greview-theory>Повторить правило</button><button class="btn" data-grepeat-exercise>Попробовать заново</button>')
    p=replace_once(p,
      "  attempt.status='failed';\n  gStoreAttempt(unit,group,attempt);\n  G.recovery=null;\n  gSave(); render();",
      "  attempt.status='failed';\n  gStoreAttempt(unit,group,attempt);\n  G.recovery=group.id;\n  gSave(); render();")
    PLAYER.write_text(p)
    subprocess.check_call(["git","add",str(PLAYER),str(TEST)])
    subprocess.check_call(["git","diff","--check"])
    print("Merged code has no conflict markers.",flush=True)
if __name__=="__main__":
    main()
