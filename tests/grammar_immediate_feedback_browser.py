#!/usr/bin/env python3
"""Actual Chromium responsive and three-life immediate-feedback regression (grammar only)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

WIDTHS = (320, 390, 768, 1280)
CASES = (
    (1, "exercise:1.1", "choice"),
    (5, "section:0", "choice"),
    (5, "section:1", "choice"),
    (5, "section:2", "choice"),
    (5, "exercise:5.1", "choice"),
    (5, "exercise:5.2", "input"),
    (5, "exercise:5.3", "choice"),
    (2,"section:0","choice"), (2,"section:1","choice"),
    (2,"section:2","choice"), (2,"section:3","choice"),
    (2,"section:4","choice"), (2,"section:5","choice"),
    (2,"section:6","choice"), (2,"exercise:2.1","choice"),
    (2,"exercise:2.2","input"), (2,"exercise:2.3","input"),
    (8, "section:0", "choice"),
    (8, "section:1", "choice"),
    (8, "section:2", "choice"),
    (8, "section:3", "choice"),
    (8, "exercise:8.1", "choice"),
    (8, "exercise:8.2", "choice"),
    (8, "exercise:8.3", "choice"),
    (8, "exercise:8.4", "choice"),
    (13, "section:0", "choice"),
    (13, "section:1", "choice"),
    (13, "section:2", "choice"),
    (13, "exercise:13.1", "input"),
    (13, "exercise:13.2", "choice"),
    (13, "exercise:13.3", "choice"),
    (13, "exercise:13.3", "build", 8),
    (13, "exercise:13.3", "build", 10),
    (7, "exercise:7.1", "choice"),
    (7, "exercise:7.2", "choice"),
    (7, "exercise:7.3", "input"),
    (15, "exercise:15.2", "build"),
    (38, "exercise:38.1b", "gaps"),
    (45, "exercise:45.2", "gaps"),
    (48, "section:0", "choice"), (48, "section:1", "choice"),
    (48, "section:2", "choice"), (48, "section:3", "choice"),
    (48, "exercise:48.1", "choice"), (48, "exercise:48.1", "gaps", 10),
    (48, "exercise:48.2", "input"),
    (48, "exercise:48.2", "gaps", 1), (48, "exercise:48.3", "choice"),
    (49, "section:0", "choice"), (49, "section:1", "choice"),
    (49, "section:2", "choice"), (49, "section:3", "choice"),
    (49, "exercise:49.1", "choice"), (49, "exercise:49.1", "gaps", 3),
    (49, "exercise:49.2", "choice"),
    (49, "exercise:49.3", "input"), (49, "exercise:49.4", "choice"),
    (49, "exercise:49.4", "gaps", 1),
    (50, "section:0", "choice"), (50, "section:1", "choice"), (50, "section:2", "choice"),
    (50, "section:3", "choice"), (50, "section:4", "choice"),
    (50, "exercise:50.1", "choice"), (50, "exercise:50.1", "gaps", 7),
    (50, "exercise:50.2", "input"), (50, "exercise:50.3", "input"),
    (50, "exercise:50.4", "choice"), (50, "exercise:50.5", "choice"),
    (50, "exercise:50.5", "gaps", 2),
    (53, "section:0", "choice"), (53, "section:1", "choice"), (53, "section:2", "choice"),
    (53, "exercise:53.1", "choice"), (53, "exercise:53.1", "input", 1),
    (53, "exercise:53.2", "input", 1), (53, "exercise:53.3", "input"),
    (53, "exercise:53.4", "input"), (53, "exercise:53.4", "gaps", 1),
    (54, "section:0", "choice"), (54, "section:1", "choice"), (54, "section:2", "choice"),
    (54, "exercise:54.1", "input"), (54, "exercise:54.1", "choice", 2),
    (54, "exercise:54.2", "gaps", 1), (54, "exercise:54.2", "input", 3),
    (54, "exercise:54.3", "choice"), (54, "exercise:54.3", "input", 2),
    (54, "exercise:54.4", "choice"), (54, "exercise:54.4", "input", 2),
    (51, "section:0", "choice"), (51, "section:1", "choice"), (51, "section:2", "choice"),
    (51, "section:3", "choice"), (51, "section:4", "choice"),
    (51, "exercise:51.1", "input"), (51, "exercise:51.2", "input"), (51, "exercise:51.2", "gaps", 3),
    (51, "exercise:51.3", "input"), (51, "exercise:51.4", "input"), (51, "exercise:51.5", "gaps", 2),
    (52, "section:0", "choice"), (52, "section:1", "choice"), (52, "section:2", "choice"),
    (52, "exercise:52.1", "input"), (52, "exercise:52.1", "input", 3), (52, "exercise:52.2", "input"),
    (52, "exercise:52.3", "gaps", 2), (52, "exercise:52.3", "input", 6),
    (55, "section:0", "choice"), (55, "section:1", "choice"), (55, "section:2", "choice"),
    (55, "section:3", "choice"),
    (55, "exercise:55.1", "input"), (55, "exercise:55.1", "choice", 2), (55, "exercise:55.1", "gaps", 3),
    (55, "exercise:55.2", "gaps"), (55, "exercise:55.2", "gaps", 2), (55, "exercise:55.3", "input"),
    (55, "exercise:55.3", "input", 5), (55, "exercise:55.4", "input"), (55, "exercise:55.4", "choice", 2),
    (55, "exercise:55.4", "gaps", 3),
    (62, "section:0", "choice"), (62, "section:1", "choice"), (62, "section:2", "choice"),
    (62, "section:3", "choice"), (62, "exercise:62.1", "choice"), (62, "exercise:62.2", "choice"),
    (62, "exercise:62.3", "choice"), (62, "exercise:62.4", "input"), (62, "exercise:62.4", "gaps", 4),
    (62, "exercise:62.5", "build"), (62, "exercise:62.5", "input", 1),
)
# Additional **successful submissions** with real keyboard/button interactions.
# Each case starts a fresh session: do not accidentally satisfy a later answer by previous context.
SUCCESS8 = (
    ("exercise:8.1", 2, "∅"),
    ("exercise:8.2", 1, "el"),
    ("exercise:8.3", 1, "∅"),
    ("exercise:8.3", 7, "∅"),
    ("exercise:8.3", 7, "el"),
    ("exercise:8.3", 9, "∅"),
    ("exercise:8.3", 9, "la"),
    ("exercise:8.4", 1, "al"),
    ("exercise:8.4", 3, "del"),
    ("exercise:8.4", 5, "a El"),
    ("exercise:8.4", 7, "de El"),
    ("exercise:8.4", 9, "de La"),
)
SUCCESS2 = (
    ("exercise:2.1",3,"el","correct"), ("exercise:2.1",14,"el teléfono","correct"),
    ("exercise:2.2",5,"la","correct"), ("exercise:2.2",6,"el","correct"),
    ("exercise:2.2",9,"la perra","correct"),
    ("section:5",1,"la gorila","correct"), ("section:5",1,"el gorila hembra","correct"),
    ("exercise:2.3",0,"el árbol","correct"), ("exercise:2.3",0,"el arbol","almost"),
    ("exercise:2.3",0,"la árbol","wrong"), ("exercise:2.3",1,"el tren","correct"),
    ("exercise:2.3",2,"el diccionario","correct"), ("exercise:2.3",3,"la mariposa","correct"),
    ("exercise:2.3",4,"el gorila","correct"), ("exercise:2.3",4,"la gorila","correct"),
    ("exercise:2.3",5,"la llave","correct"), ("exercise:2.3",6,"el hospital","correct"),
    ("exercise:2.3",7,"el tenedor","correct"), ("exercise:2.3",8,"el pez","correct"),
    ("exercise:2.3",9,"la nariz","correct"),
)
OUT = Path("docs/grammar_immediate_feedback_browser")
SHOTS = OUT / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
ORIGIN = "http://127.0.0.1:8765/index.html"
REPORT = {"browser": "Chromium via Playwright", "widths": WIDTHS, "cases": [], "failures": [],
          "limitations": ["Android/iOS native IME not available in Linux Chromium; 520px-height viewport emulates keyboard obstruction, not a real mobile keyboard."]}

PREPARE = r"""async ({number,route,qi=0}) => {
  const u=COURSE.grammar.find(u=>u.number===number);
  if(u?._data && (!u.exercises?.[0]?.questions || !u.sections?.[0]?.check?.questions)) await dataLoad(u._data);
  if(!u) throw Error('Unit '+number+' not found');
  P.grammar ||= {}; P.grammarRead ||= {};
  const routes=gRoutes(u), idx=routes.indexOf(route);
  if(idx<0) throw Error('Missing route '+route);
  for(const r of routes.slice(0,idx)){
    const group=r.startsWith('section:') ? u.sections[+r.split(':')[1]].check
      :u.exercises.find(g=>r==='exercise:'+g.id);
    if(group) P.grammar[grammarKey(u,group)]={correct:1,total:group.questions.length};
    else P.grammarRead[u.id+'/'+r]=true;
  }
  const group=route.startsWith('section:') ? u.sections[+route.split(':')[1]].check
    : u.exercises.find(g=>route==='exercise:'+g.id);
  if(!group)throw Error('Group absent');
  P.grammar[grammarKey(u,group)]={correct:1,total:group.questions.length};
  const score=JSON.stringify(P.grammar[grammarKey(u,group)]);
  save(); gStart(u.id,route); gMove(1);
  G.at=G.steps.findIndex(s=>s.type==='question'&&s.group===group.id&&s.qi===qi);
  if(!G || G.at<0 || G.steps[G.at]?.type!=='question') throw Error('Failed to start '+route+' index '+qi);
  gSave(); render(); // after selecting a non-first exercise question, refresh the actual player controls
  return {score,group:group.id,questions:group.questions.length};
}"""

QUESTION = """() => {
  const s=G.steps[G.at],g=gGroups(gUnit()).find(g=>g.id===s.group),q=g.questions[s.qi];
  return {at:G.at, qi:s.qi, question:q.prompt, explain:q.explain, mode:gQuestionMode(q,gResponse(s)),
          answers:q.answers, acceptedLabels:q.answers.map(a=>gOptionLabel(q,a)), options:q.options||[], gaps:q.gapParts?.length-1||0, group:g.id};
}"""

LAYOUT = """() => {
  const get=s=>document.querySelector(s), bb=el=>el?.getBoundingClientRect();
  const body=get('.gplayer .pbody'), foot=get('.gplayer .pfoot'), player=get('.gplayer');
  const bx=bb(body), fx=bb(foot), px=bb(player);
  const bad=[...document.querySelectorAll('.gplayer input,.gplayer textarea,.gplayer button')].filter(el=>{
    const r=bb(el),cs=getComputedStyle(el);return r&&r.width>0&&cs.display!=='none'&&cs.visibility!=='hidden'
      &&(r.left<-2 || r.right>innerWidth+2);
  }).slice(0,8).map(el=>({tag:el.tagName, text:(el.textContent||'').slice(0,40), className:el.className}));
  return {viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,
    playerWidth:player?.scrollWidth, bodyWidth:body?.scrollWidth, bodyClient:body?.clientWidth,
    footTop:fx?.top, bodyBottom:bx?.bottom, playerRight:px?.right,
    overflowedControls:bad, feedbackHeight:get('.pfoot .fb')?.scrollHeight||0,
    feedbackClient:get('.pfoot .fb')?.clientHeight||0};
}"""

def assert_true(cond, message):
    if not cond:
        raise AssertionError(message)

def check_layout(page, label):
    layout=page.evaluate(LAYOUT)
    width=page.viewport_size["width"]
    assert_true(layout["documentWidth"] <= width+2, f"{label}: document horizontal scroll {layout}")
    assert_true((layout["playerWidth"] or 0)<=width+2, f"{label}: player horizontal scroll {layout}")
    assert_true(not layout["overflowedControls"], f"{label}: controls outside viewport {layout}")
    if layout["footTop"] is not None and layout["bodyBottom"] is not None:
        assert_true(layout["bodyBottom"]<=layout["footTop"]+3, f"{label}: body/footer overlap {layout}")
    if layout["feedbackHeight"] > layout["feedbackClient"]+3:
        scroll=page.evaluate("""() => { const f=document.querySelector('.pfoot .fb'); const before=f.scrollTop; f.scrollTop=f.scrollHeight; const end=f.scrollTop; f.scrollTop=before; return end; }""")
        assert_true(scroll>0, f"{label}: error details not scrollable")
    return layout

def picture(page, width, unit, name):
    path=SHOTS / f"u{unit:02d}_{width}_{name}.png"
    page.screenshot(path=str(path),animations="disabled")
    return str(path)

def enter_wrong(page, question):
    if question["mode"]=="choice":
        value=next((v for v in question["options"] if v not in question["answers"]),None)
        assert_true(value is not None,"No incorrect choice available")
        page.evaluate("""(value) => {
          const b=[...document.querySelectorAll('[data-gvalue]')].find(e=>e.dataset.gvalue===value);
          if(!b) throw Error('Choice button not found');
          b.click();
        }""", value)
        return
    if question["mode"]=="build":
        buttons=page.locator(".gbuild-bank [data-gadd]")
        assert_true(buttons.count()>0,"Missing builder tiles")
        buttons.first.click()
    elif question["mode"]=="gaps":
        slots=page.locator("[data-gslot]")
        for i in range(slots.count()):
            slots.nth(i).click()
            opts=page.locator("[data-gslot-choice]")
            assert_true(opts.count()>0,"Missing guided choices")
            opts.first.click()
    elif page.locator("[data-ggap]").count()>0:
        fields=page.locator("[data-ggap]")
        for i in range(fields.count()):
            fields.nth(i).fill("incorrecto")
    else:
        field=page.locator("#g-answer")
        assert_true(field.count()>0,"Missing input")
        field.fill("incorrecto")
    check=page.locator("[data-gcheck]")
    assert_true(check.count()>0 and check.is_enabled(),"Check button missing or disabled")
    check.click()

def run_case(browser, width, number, route, expected_mode, qi=0):
    context=browser.new_context(viewport={"width":width,"height":820},
                               is_mobile=width<=390,has_touch=width<=390,
                               device_scale_factor=1)
    page=context.new_page()
    exceptions=[]
    page.on("pageerror",lambda err: exceptions.append(str(err)))
    item={"width":width,"unit":number,"route":route,"question_index":qi,"screenshots":[],"layouts":{}}
    label_id=route.replace(":","_").replace(".","_")+f"_q{qi}"
    try:
        page.goto(ORIGIN,wait_until="domcontentloaded",timeout=45000)
        page.evaluate("localStorage.clear()")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("typeof gStart==='function' && Array.isArray(COURSE.grammar) && COURSE.grammar.length>0",timeout=30000)
        initial=page.evaluate(PREPARE,{"number":number,"route":route,"qi":qi})
        item["initial"]=initial
        label=f"u{number} width {width}"
        item["layouts"]["initial"]=check_layout(page,label+" initial")
        for n in (1,2,3):
            q=page.evaluate(QUESTION)
            if n==1:
                assert_true(q["mode"]==expected_mode or expected_mode=="gaps" and q["gaps"]>0,
                            f"{label}: expected {expected_mode}, got {q['mode']}")
            if width<=390 and (q["mode"] in ("input","build") or q["gaps"]>0) and n==1:
                page.set_viewport_size({"width":width,"height":520})
                if q["mode"]!="build":
                    page.locator("[data-ggap],#g-answer").first.focus()
                page.evaluate("gSyncViewport()")
                item["layouts"]["keyboard_emulation"]=check_layout(page,label+" short height")
                if q["mode"]=="build":
                    assert_true(page.locator(".gbuild-bank [data-gadd]").count()>0,
                                label+": word-bank buttons unavailable at reduced height")
                else:
                    assert_true(page.locator("[data-gcheck]").count()>0,
                                label+": check button unavailable during compressed height")
                page.set_viewport_size({"width":width,"height":820})
                page.evaluate("gSyncViewport()")
            if number==5 and route=="exercise:5.2" and n==1:
                # A real browser click on ∅ must fill the article field without checking it or losing a life.
                omit=page.locator("[data-gno-article]")
                assert_true(omit.count()>0, "Unit 5: no-article input control is missing")
                before_omit=page.evaluate("""() => {
                    const s=G.steps[G.at],g=gGroups(gUnit()).find(g=>g.id===s.group);
                    return gAttempt(gUnit(),g).errors;
                }""")
                omit.click()
                omitted=page.evaluate("""() => {
                    const s=G.steps[G.at],g=gGroups(gUnit()).find(g=>g.id===s.group);
                    return {value:gResponse(s).value,checked:gResponse(s).checked,
                            errors:gAttempt(gUnit(),g).errors};
                }""")
                assert_true(omitted["value"]=="∅" and omitted["checked"] is False
                            and omitted["errors"]==before_omit,
                            "Unit 5: ∅ must not submit or consume a life: "+str(omitted))
                item["omission_button"]={"clicked":True,"value":omitted["value"],"errors":omitted["errors"]}
            if number==13 and route=="exercise:13.3" and q["mode"]=="build" and n==1:
                bank=page.locator(".gbuild-bank [data-gadd]")
                assert_true(bank.count()>len(q["answers"][0].split()),
                            "Unit 13 word bank must have distractors, not only required words")
                item["distractors"]={"bank":bank.count(),"needed":len(q["answers"][0].split())}
            enter_wrong(page,q)
            state=page.evaluate("""() => {
              const s=G.steps[G.at],g=gGroups(gUnit()).find(g=>g.id===s.group),a=gAttempt(gUnit(),g);
              return {errors:a.errors,lives:gErrorLimit(g)-a.errors,status:a.status,
                      recovery:G.recovery||null,at:G.at,feedback:gPlayerView()};
            }""")
            assert_true(state["errors"]==n and state["lives"]==3-n,
                        f"{label}: wrong hearts at {n}: {state['lives']}/{state['errors']}")
            assert_true("Верный ответ:" in state["feedback"],
                        f"{label}: correct answer must appear immediately after error {n}")
            footer=page.locator(".pfoot .fb").inner_text()
            assert_true("Почему:" in footer, f"{label}: missing explanation on error {n}")
            for accepted in q["acceptedLabels"]:
                assert_true(accepted in footer,
                            f"{label}: missing accepted alternative {accepted!r} after error {n}")
            assert_true(not state["recovery"],f"{label}: involuntary theory navigation")
            if n==3:
                assert_true(state["status"]=="failed",label+": not failed on third error")
                assert_true(q["explain"] in page.locator(".fb").inner_text(),
                            label+": question-specific explanation absent")
                assert_true(page.locator("[data-greview-theory]").count()>0,
                            label+": voluntary theory button absent")
                assert_true(page.locator("[data-grepeat-exercise]").count()>0,
                            label+": retry button absent")
            else:
                assert_true(state["status"]=="active",label+": failed too early")
            item["layouts"][f"error_{n}"]=check_layout(page,label+f" error {n}")
            if number==1 or n==3:
                item["screenshots"].append(picture(page,width,number,f"{label_id}_error_{n}"))
            if n<3:
                next_button=page.locator("[data-gnext]")
                assert_true(next_button.count()>0,label+": next unavailable")
                next_button.click()
        last=page.evaluate("G.steps[G.at].qi")
        page.locator("[data-greview-theory]").click()
        assert_true(page.evaluate("Boolean(G.recovery)"),label+": theory didn't open")
        item["layouts"]["theory"]=check_layout(page,label+" theory")
        if number==1 or width==390:
            item["screenshots"].append(picture(page,width,number,label_id+"_theory"))
        page.locator("[data-greview-mistake]").click()
        assert_true(page.evaluate("!G.recovery && G.steps[G.at].qi") == last,
                    label+": did not return to same failed question")
        assert_true(page.locator(".fb").inner_text().find("Верный ответ:")>=0,
                    label+": lost mistake analysis")
        if number==1 or width==390:
            item["screenshots"].append(picture(page,width,number,label_id+"_returned_to_error"))
        page.locator("[data-grepeat-exercise]").click()
        remaining=page.evaluate("""() => {
          const u=gUnit(),g=gGroups(u).find(x=>x.id===G.steps[G.at].group);
          const a=gAttempt(u,g);
          return {errors:a.errors,score:JSON.stringify(P.grammar[grammarKey(u,g)])};
        }""")
        assert_true(remaining["errors"]==0,label+": retry didn't reset lives")
        assert_true(remaining["score"]==initial["score"],label+": previous progress lost")
        item["layouts"]["retry"]=check_layout(page,label+" retry")
        if number==1 or width==390:
            item["screenshots"].append(picture(page,width,number,label_id+"_retry"))
        assert_true(not exceptions, label+": JavaScript errors: "+str(exceptions))
        item["status"]="passed"
    except Exception as error:
        item["status"]="failed"
        item["error"]=repr(error)
        REPORT["failures"].append({"width":width,"unit":number,"error":repr(error)})
        try:
            item["screenshots"].append(picture(page,width,number,label_id+"_FAILED"))
        except Exception:
            pass
    finally:
        REPORT["cases"].append(item)
        context.close()

def run_unit08_correct_case(browser, width, route, qi, answer):
    """Exercise real input controls, ∅ button, alternatives, spaced input and reload."""
    context=browser.new_context(viewport={"width":width,"height":820},
                                is_mobile=width<=390,has_touch=width<=390,
                                device_scale_factor=1)
    page=context.new_page()
    item={"unit":8,"width":width,"route":route,"question_index":qi,
          "answer":answer,"status":"pending","screenshots":[]}
    errors=[]
    page.on("pageerror",lambda exc:errors.append(str(exc)))
    try:
        page.goto(ORIGIN,wait_until="domcontentloaded",timeout=45000)
        page.evaluate("localStorage.clear()")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("typeof gStart==='function' && Array.isArray(COURSE.grammar) && COURSE.grammar.length>0",timeout=30000)
        page.evaluate(PREPARE,{"number":8,"route":route,"qi":qi})
        # The site-level lesson header lives outside .gplayer; assert the actual
        # rendered exercise route and capture the visible heading for manual review.
        item["visible_headings"]=page.locator("h1,h2,h3,.gplayer .ptitle").all_inner_texts()[:12]
        active=page.evaluate("""() => ({
          unit:gUnit().number, group:G.steps[G.at].group, qi:G.steps[G.at].qi,
          title:gUnit().title
        })""")
        assert_true(active=={"unit":8,"group":route.split(":")[1],"qi":qi,
                             "title":"El señor Alonso, la calle Mayor"},
                    f"u8 {route}: wrong active lesson or exercise {active}")
        item["initial_layout"]=check_layout(page,"unit8 correct "+route)
        assert_true(page.evaluate("gQuestionMode(gGroups(gUnit()).find(g=>g.id===G.steps[G.at].group).questions[G.steps[G.at].qi],gResponse(G.steps[G.at]))")=="input",
                    f"u8 {route} #{qi}: intended input control missing")
        old=page.evaluate("""() => {
          const s=G.steps[G.at],g=gGroups(gUnit()).find(x=>x.id===s.group);
          return {errors:gAttempt(gUnit(),g).errors,checked:gResponse(s).checked};
        }""")
        assert_true(old["errors"]==0 and not old["checked"],"fresh input not clean")
        if answer=="∅":
            button=page.locator("[data-gno-article]")
            assert_true(button.count()==1,"unit8: accessible omission button absent")
            button.click()
            state=page.evaluate("""() => {
              const s=G.steps[G.at],g=gGroups(gUnit()).find(x=>x.id===s.group);
              return {value:gResponse(s).value,checked:gResponse(s).checked,errors:gAttempt(gUnit(),g).errors};
            }""")
            assert_true(state=={"value":"∅","checked":False,"errors":0},
                        "omission button must fill ∅ without grading or losing life: "+str(state))
            item["omission_button"]=state
        else:
            field=page.locator("#g-answer")
            assert_true(field.count()==1,"u8: actual text field missing")
            field.fill(answer)
            assert_true(field.input_value()==answer,"u8: typed text truncated or normalized before submit")
        if width==390 and route=="exercise:8.4" and qi==5:
            # A two-word draft must survive page reload before submitting.
            page.reload(wait_until="domcontentloaded")
            page.wait_for_function("typeof gStart==='function' && Array.isArray(COURSE.grammar)",timeout=30000)
            page.evaluate("""async () => {
              const u=COURSE.grammar.find(u=>u.number===8);
              await dataLoad(u._data);
              gStart(u.id,'all',true);
            }""")
            restored=page.evaluate("""() => ({value:gResponse(G.steps[G.at]).value,group:G.steps[G.at].group,qi:G.steps[G.at].qi})""")
            assert_true(restored=={"value":"a El","group":"8.4","qi":5},
                        "two-word draft not restored: "+str(restored))
            item["reload_restored"]=restored
        button=page.locator("[data-gcheck]")
        assert_true(button.count()==1 and button.is_enabled(),"unit8: submit button not available")
        button.click()
        state=page.evaluate("""() => {
          const s=G.steps[G.at],g=gGroups(gUnit()).find(x=>x.id===s.group),a=gAttempt(gUnit(),g);
          return {good:gResponse(s).good,status:a.status,errors:a.errors,value:gResponse(s).value,
                  checked:gResponse(s).checked};
        }""")
        assert_true(state["good"] is True and state["checked"] is True and state["errors"]==0,
                    f"u8 {route} #{qi} {answer}: correct answer rejected: {state}")
        item["result"]=state
        item["after_layout"]=check_layout(page,"unit8 accepted "+route)
        if width==390 and (answer in ("∅","a El","de El","de La","del")):
            item["screenshots"].append(picture(page,width,8,f"accepted_{route.replace(':','_').replace('.','_')}_{qi}_{answer.replace(' ','_')}"))
        assert_true(not errors,f"u8 {route} #{qi}: JavaScript errors {errors}")
        item["status"]="passed"
    except Exception as exc:
        item["status"]="failed";item["error"]=repr(exc)
        REPORT["failures"].append({"width":width,"unit":8,"route":route,"qi":qi,"answer":answer,"error":repr(exc)})
        try:
            item["screenshots"].append(picture(page,width,8,f"accepted_{route.replace(':','_')}_{qi}_FAILED"))
        except Exception:pass
    finally:
        REPORT["cases"].append(item)
        context.close()



def run_unit02_correct_case(browser,width,route,qi,answer,expected):
    context=browser.new_context(viewport={"width":width,"height":820},
                                is_mobile=width<=390,has_touch=width<=390,
                                device_scale_factor=1)
    page=context.new_page(); errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    item={"unit":2,"width":width,"route":route,"qi":qi,
          "answer":answer,"expected":expected,"screenshots":[]}
    try:
        page.goto(ORIGIN,wait_until="domcontentloaded",timeout=45000)
        page.evaluate("localStorage.clear()");page.reload(wait_until="domcontentloaded")
        page.wait_for_function("typeof gStart==='function' && Array.isArray(COURSE.grammar) && COURSE.grammar.length>0",timeout=30000)
        page.evaluate(PREPARE,{"number":2,"route":route,"qi":qi})
        assert_true(page.evaluate("gUnit().number")==2,"Unit 2 navigation lost")
        active=page.evaluate("""() => ({group:G.steps[G.at].group,qi:G.steps[G.at].qi})""")
        assert_true(active=={"group":("check-f" if route=="section:5" else route.split(":")[1]),"qi":qi},"Wrong question route: "+str(active))
        item["before"]=check_layout(page,"unit2 before "+route)
        q=page.evaluate(QUESTION)
        if route=="exercise:2.3":
            image=page.locator("img.gquestion-picture")
            assert_true(image.count()==1,"Unit 2 illustration missing")
            info=image.evaluate("""e=>({ready:e.complete&&e.naturalWidth>0&&e.naturalHeight>0,alt:e.alt})""")
            assert_true(info["ready"] and info["alt"],"Unit 2 broken illustration: "+str(info))
            item["picture"]=info
            vocab=page.locator("details.gvocab")
            assert_true(vocab.count()==1 and vocab.get_attribute("open") is None,
                        "Unit 2 vocabulary must be collapsed until requested")
        if q["mode"]=="choice":
            page.evaluate("""a=>{const el=[...document.querySelectorAll('[data-gvalue]')].find(x=>x.dataset.gvalue===a);
                if(!el)throw Error('Missing answer button '+a);el.click();}""",answer)
        else:
            assert_true(q["mode"]=="input","Expected real input control")
            field=page.locator("#g-answer")
            assert_true(field.count()==1,"Input not rendered")
            if route=="exercise:2.3" and qi==0 and answer=="el árbol" and width==390:
                field.fill("el ")
                panel=page.locator('[data-gchar="á"]')
                assert_true(panel.count()==1,"Spanish accent button absent")
                panel.click()
                assert_true(field.input_value()=="el á","Spanish keyboard insertion failed")
            if route=="exercise:2.3" and qi==1 and width==390:
                field.fill("el tre");page.reload(wait_until="domcontentloaded")
                page.wait_for_function("typeof gStart==='function' && Array.isArray(COURSE.grammar)",timeout=30000)
                page.evaluate("""async () => {const u=COURSE.grammar.find(x=>x.number===2);await dataLoad(u._data);gStart(u.id,'all',true);}""")
                stored=page.evaluate("""() => ({group:G.steps[G.at].group,qi:G.steps[G.at].qi,value:gResponse(G.steps[G.at]).value})""")
                assert_true(stored=={"group":"2.3","qi":1,"value":"el tre"},
                            "Draft not restored: "+str(stored))
                item["draft"]=stored;field=page.locator("#g-answer")
            field.fill(answer)
            assert_true(field.input_value()==answer,"Input truncated")
            submit=page.locator("[data-gcheck]")
            assert_true(submit.count()==1 and submit.is_enabled(),"Submit not accessible")
            submit.click()
        state=page.evaluate("""() => {
            const s=G.steps[G.at],g=gGroups(gUnit()).find(g=>g.id===s.group),
                  a=gAttempt(gUnit(),g),r=gResponse(s);
            return {status:r.status,good:r.good,checked:r.checked,errors:a.errors,feedback:gPlayerView()};
        }""")
        assert_true(state["status"]==expected and state["checked"],
                    "Wrong status for "+answer+": "+str(state["status"]))
        if expected=="wrong":
            assert_true(state["good"] is False and state["errors"]==1
                        and "Верный ответ:" in state["feedback"] and "Почему:" in state["feedback"],
                        "Wrong article did not show red feedback and explanation")
        else:
            assert_true(state["good"] is True and state["errors"]==0,
                        "Correct/alternative answer cost a life")
            if expected=="almost":
                assert_true(page.locator(".pfoot.almost").count()==1,
                            "Omitted accent was not shown as yellow")
        item["after"]=check_layout(page,"unit2 after "+route)
        if width==390 and (route=="section:5" or
                          route=="exercise:2.3" and qi in (0,1,4,7)):
            name=f"stage8_{route.replace(':','_').replace('.','_')}_{qi}_{expected}_{answer.replace(' ','_')}"
            item["screenshots"].append(picture(page,width,2,name))
        assert_true(not errors,"Unit 2 JavaScript errors "+str(errors))
        item["status"]="passed"
    except Exception as e:
        item["status"]="failed";item["error"]=repr(e)
        REPORT["failures"].append({"unit":2,"width":width,"route":route,"qi":qi,"answer":answer,"error":repr(e)})
        try:item["screenshots"].append(picture(page,width,2,f"stage8_{qi}_FAILED"))
        except Exception:pass
    finally:
        REPORT["cases"].append(item);context.close()


def main():
    proc=subprocess.Popen([sys.executable,"-m","http.server","8765","--directory","site"],
                          stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    try:
        time.sleep(2)
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
            REPORT["browser_version"]=browser.version
            for width in WIDTHS:
                for case in CASES:
                    number,route,mode,*extra=case
                    run_case(browser,width,number,route,mode,extra[0] if extra else 0)
                    print(f"{width}px / unit {number}: {REPORT['cases'][-1]['status']}",flush=True)
                for route,qi,answer,status in SUCCESS2:
                    run_unit02_correct_case(browser,width,route,qi,answer,status)
                    print(f"{width}px / unit 2 accepted {route} #{qi}: {REPORT['cases'][-1]['status']}",flush=True)
                for route,qi,answer in SUCCESS8:
                    run_unit08_correct_case(browser,width,route,qi,answer)
                    print(f"{width}px / unit 8 accepted {route} #{qi}: {REPORT['cases'][-1]['status']}",flush=True)
            browser.close()
    finally:
        proc.terminate()
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"report.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"passed":sum(x["status"]=="passed" for x in REPORT["cases"]),
                      "failed":REPORT["failures"]},ensure_ascii=False),flush=True)
    return 1 if REPORT["failures"] else 0

if __name__=="__main__":
    sys.exit(main())
