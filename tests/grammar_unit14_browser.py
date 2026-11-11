#!/usr/bin/env python3
"""Fable stage 9: real Chromium acceptance and progress checks for unit 14."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

import grammar_immediate_feedback_browser as base


WIDTHS = (320, 390, 768, 1280)
OUT = Path("docs/grammar_unit14_browser")
base.OUT = OUT
base.SHOTS = OUT / "screenshots"
base.SHOTS.mkdir(parents=True, exist_ok=True)
base.REPORT = {
    "browser": "Chromium via Playwright",
    "widths": WIDTHS,
    "cases": [],
    "failures": [],
    "limitations": [
        "Linux Chromium with a 520px viewport is not a real Android/iOS input method."
    ],
}
REPORT = base.REPORT
WRONG_CASES = (
    ("section:0", "choice", 0),
    ("section:1", "choice", 0),
    ("section:2", "choice", 0),
    ("exercise:14.1", "choice", 0),
    ("exercise:14.1", "input", 7),
    ("exercise:14.2", "input", 6),
    ("exercise:14.3", "input", 2),
)
CORRECT_CASES = (
    ("exercise:14.1", 7, "iraníes", "correct"),
    ("exercise:14.1", 7, "iranís", "correct"),
    ("exercise:14.1", 7, "iraní", "wrong"),
    ("exercise:14.3", 2, "marroquíes", "correct"),
    ("exercise:14.3", 2, "marroquís", "correct"),
    ("exercise:14.3", 2, "marroquí", "wrong"),
    ("exercise:14.1", 14, "japonés", "correct"),
    ("exercise:14.1", 14, "japones", "almost"),
    ("exercise:14.1", 0, "Страна: Chile; прилагательное: chileno", "correct"),
    ("exercise:14.1", 0, "Страна: chileno; прилагательное: Chile", "wrong"),
    ("exercise:14.2", 5, "una", "correct"),
    ("exercise:14.2", 6, "una amiga chilena", "correct"),
    ("exercise:14.3", 4, "chilena", "correct"),
)


def new_context(browser, width):
    return browser.new_context(
        viewport={"width": width, "height": 820},
        is_mobile=width <= 390,
        has_touch=width <= 390,
        device_scale_factor=1,
    )


def ready(page, route, qi):
    page.goto(base.ORIGIN, wait_until="domcontentloaded", timeout=45000)
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function(
        "typeof gStart==='function' && Array.isArray(COURSE.grammar) && COURSE.grammar.length>0",
        timeout=30000,
    )
    page.evaluate(base.PREPARE, {"number": 14, "route": route, "qi": qi})
    state = page.evaluate("""() => ({
        number:gUnit().number,
        id:gUnit().id,
        group:G.steps[G.at].group,
        qi:G.steps[G.at].qi
    })""")
    assert state == {
        "number": 14,
        "id": "014_gentilicios",
        "group": ("check-" + "abc"[int(route[-1])] if route.startswith("section:") else route.split(":")[1]),
        "qi": qi,
    }, "Wrong unit route: " + repr(state)
    return base.check_layout(page, "u14 start " + route)


def run_answer(browser, width, route, qi, answer, expected):
    context = new_context(browser, width)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    item = {"unit": 14, "width": width, "route": route, "qi": qi,
            "answer": answer, "expected": expected}
    try:
        item["before"] = ready(page, route, qi)
        q = page.evaluate(base.QUESTION)
        if q["mode"] == "choice":
            assert answer in q["options"], "Choice not available: " + repr(answer)
            page.evaluate("""value => {
                const b=[...document.querySelectorAll('[data-gvalue]')]
                    .find(e=>e.dataset.gvalue===value);
                if(!b)throw Error('Missing button for '+value);
                b.click();
            }""", answer)
        else:
            assert q["mode"] == "input", "Expected input control, got " + str(q["mode"])
            field = page.locator("#g-answer")
            assert field.count() == 1, "Text input not rendered"
            if width == 390 and answer == "japonés":
                for character in "áéíóúñ":
                    assert page.locator('[data-gchar="' + character + '"]').count() == 1, (
                        "Missing Spanish-character button " + character
                    )
            field.fill(answer)
            assert field.input_value() == answer, "Field rejected valid characters"
            button = page.locator("[data-gcheck]")
            assert button.count() == 1 and button.is_enabled(), "Submit button is absent"
            button.click()
        result = page.evaluate("""() => {
            const s=G.steps[G.at];
            const g=gGroups(gUnit()).find(g=>g.id===s.group);
            const r=gResponse(s),a=gAttempt(gUnit(),g);
            return {
                status:r.status,good:r.good,checked:r.checked,
                errors:a.errors,feedback:gPlayerView()
            };
        }""")
        assert result["status"] == expected and result["checked"], (
            "Answer status mismatch: " + repr(result)
        )
        if expected == "wrong":
            assert result["good"] is False and result["errors"] == 1, repr(result)
            assert "Верный ответ:" in result["feedback"], "Missing immediate disclosure"
            assert "Почему:" in result["feedback"], "Missing explanation"
        else:
            assert result["good"] is True and result["errors"] == 0, repr(result)
            if expected == "almost":
                assert page.locator(".pfoot.almost").count() == 1, (
                    "Accent omission did not show yellow status"
                )
        item["after"] = base.check_layout(page, "u14 response " + route)
        if width == 390 and (qi in (7, 14, 2, 6) or expected == "wrong"):
            item["screenshots"] = [
                base.picture(page, width, 14, "accepted_" + route.replace(":", "_").replace(".", "_")
                             + "_" + str(qi) + "_" + expected + "_"
                             + hashlib.sha256(answer.encode("utf-8")).hexdigest()[:10])
            ]
        assert not errors, "JavaScript errors: " + repr(errors)
        item["status"] = "passed"
    except Exception as error:
        item["status"] = "failed"
        item["error"] = repr(error)
        REPORT["failures"].append({"case": item.copy()})
        try:
            item["screenshots"] = [base.picture(page, width, 14, "accepted_FAILED_" + str(qi))]
        except Exception:
            pass
    finally:
        REPORT["cases"].append(item)
        context.close()


def run_migration(browser, width):
    context = new_context(browser, width)
    page = context.new_page()
    item = {"unit": 14, "width": width, "scenario": "revision reset keeps best score / XP"}
    try:
        ready(page, "exercise:14.1", 0)
        result = page.evaluate("""() => {
            const u=gUnit(),g=u.exercises.find(x=>x.id==='14.1');
            const key=grammarKey(u,g),score={correct:17,total:24};
            P.grammar[key]=score;P.xp=777;
            const old=gNewAttempt({...g,revision:2},
                {0:{value:'japoneses',checked:true,good:true}});
            gStoreAttempt(u,g,old);
            G.responses[g.id]=old.responses;
            G.groupRevisions[g.id]=2;
            const before=JSON.stringify(P.grammar[key]);
            gRefreshAttemptVersions(u);
            const current=gAttempt(u,g);
            return {
                revision:current.revision,oldRevision:old.revision,
                previousId:old.id,currentId:current.id,
                errors:current.errors,responseCount:Object.keys(current.responses).length,
                scoreIntact:JSON.stringify(P.grammar[key])===before,
                xp:P.xp
            };
        }""")
        assert result["revision"] == 3 and result["oldRevision"] == 2, repr(result)
        assert result["previousId"] != result["currentId"], repr(result)
        assert result["responseCount"] == 0 and result["errors"] == 0, repr(result)
        assert result["scoreIntact"] and result["xp"] == 777, repr(result)
        item["result"] = result
        item["status"] = "passed"
    except Exception as error:
        item["status"] = "failed"
        item["error"] = repr(error)
        REPORT["failures"].append({"case": item.copy()})
    finally:
        REPORT["cases"].append(item)
        context.close()


def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8765", "--directory", "site"],
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
    )
    try:
        time.sleep(2)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            REPORT["browser_version"] = browser.version
            for width in WIDTHS:
                for route, mode, qi in WRONG_CASES:
                    base.run_case(browser, width, 14, route, mode, qi)
                    print("u14", width, route, qi, REPORT["cases"][-1]["status"], flush=True)
                for route, qi, answer, expected in CORRECT_CASES:
                    run_answer(browser, width, route, qi, answer, expected)
                    print("u14", width, route, qi, answer, REPORT["cases"][-1]["status"], flush=True)
                run_migration(browser, width)
                print("u14", width, "revision", REPORT["cases"][-1]["status"], flush=True)
            browser.close()
    finally:
        server.terminate()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(
        json.dumps(REPORT, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "passed": sum(case["status"] == "passed" for case in REPORT["cases"]),
        "failed": REPORT["failures"],
    }, ensure_ascii=False), flush=True)
    return 1 if REPORT["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
