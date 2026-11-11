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
)
OUT = Path("docs/grammar_immediate_feedback_browser")
SHOTS = OUT / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
ORIGIN = "http://127.0.0.1:8765/index.html"
REPORT = {"browser": "Chromium via Playwright", "widths": WIDTHS, "cases": [], "failures": [],
          "limitations": ["Android/iOS native IME not available in Linux Chromium; 520px-height viewport emulates keyboard obstruction, not a real mobile keyboard."]}

PREPARE = r"""({number,route,qi=0}) => {
  const u=COURSE.grammar.find(u=>u.number===number);
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
