"""Real Chromium regression for a built Pages directory (no deployment/credentials).

python tests/site_static_browser.py --site site --report /tmp/site-browser.json
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=Path('site'))
    parser.add_argument('--report', type=Path, default=Path('/tmp/site-static-browser.json'))
    args = parser.parse_args()
    handler = partial(SimpleHTTPRequestHandler, directory=str(args.site.resolve()))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}/'
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for width in (320, 390, 768, 1280):
                context = browser.new_context(viewport={'width': width, 'height': 800})
                page = context.new_page()
                errors, requests = [], []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: requests.append(request.url))
                # Existing v1 progress and unrelated keys must survive every navigation/load.
                page.add_init_script("""if(!localStorage.getItem('seeded')) {
                  localStorage.setItem('seeded','yes');
                  localStorage.setItem('unrelated-test-key','keep');
                  localStorage.setItem('espanol-cada-dia.v1',JSON.stringify({xp:123,done:{'legacy/id':{stars:2}},words:{'la casa':{s:3,due:1}},grammar:{},grammarRead:{}}));
                }""")
                page.goto(url)
                page.wait_for_selector('[data-level="A0"]')
                before = page.evaluate('JSON.stringify(localStorage)')
                assert not any('/levels/' in r or '/books/' in r or '/grammar/' in r for r in requests)
                cold = page.evaluate('({dom:performance.getEntriesByType("navigation")[0].domContentLoadedEventEnd, resources:performance.getEntriesByType("resource").map(r=>({name:r.name,bytes:r.transferSize}))})')
                # Book deep link must load exactly one chapter, retain URL, lexical links/translations.
                page.locator('[data-tab="books"]').first.click()
                page.wait_for_function('COURSE.books.length>0')
                book = page.evaluate('COURSE.books.find(b=>b.chapters.length>1)')
                chapter = book['chapters'][0]
                deep = '#books/' + book['level'] + '/' + book['id'] + '/' + chapter['id']
                page.goto(url + deep)
                page.wait_for_selector('.book-block')
                assert page.url.endswith(deep)
                assert page.locator('.book-note-item').count() or page.locator('[data-book-jump]').count()
                assert page.evaluate('bookCurrentText().blocks.length') > 0
                assert not any(book['chapters'][1]['_data']['url'] in r for r in requests)
                loaded = len([r for r in requests if chapter['_data']['url'] in r])
                # Existing UI navigation and browser history.
                page.locator('[data-book-nav="chapters"]').first.click()
                page.wait_for_selector('[data-book-chapter]')
                page.go_back()
                page.wait_for_selector('.book-block')
                page.go_forward()
                page.wait_for_selector('[data-book-chapter]')
                assert len([r for r in requests if chapter['_data']['url'] in r]) == loaded
                # Every main course loads through the production startLesson entry point.
                for level in ('A0', 'A1'):
                    page.evaluate("""level=>{S=null;G=null;P.openAll=true;P.sound=false;P.autoDlg=false;
                      view.tab='course';view.level=level;render();startLesson(LESSONS.findIndex(L=>L.level===level));} """, level)
                    page.wait_for_function('S && S.steps.length>0')
                    assert page.evaluate('S.steps.some(st=>st.type!=="intro")')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    # Source/rule indices still point to blocks after asynchronous hydration.
                    assert page.evaluate('S.steps.every(st=>st.src==null || !!LESSONS[st.li].blocks[st.src])')
                    page.evaluate('S=null;render()')
                # Independent grammar: catalog -> unit -> theory, saved attempt keys unchanged.
                page.evaluate("view.tab='grammar';view.grammar=COURSE.grammar[0].id;render()")
                page.wait_for_selector('[data-gstart]')
                page.locator('[data-gstart]').first.click()
                page.wait_for_selector('.gplayer')
                assert page.evaluate('gUnit().sections.length>0')
                session_unit = page.evaluate('G.unit')
                page.evaluate('gSave();G=null;render()')
                page.wait_for_selector('[data-gresume]')
                page.locator('[data-gresume]').click()
                page.wait_for_selector('.gplayer')
                assert page.evaluate('G.unit') == session_unit
                page.evaluate("G=null;view.tab='home';render()")
                # Only loading and navigation so far: xp, done, word SRS, unrelated key unchanged.
                assert page.evaluate('P.xp') == 123
                assert page.evaluate('P.done["legacy/id"].stars') == 2
                assert page.evaluate('P.words["la casa"].s') == 3
                assert page.evaluate('localStorage.getItem("unrelated-test-key")') == 'keep'
                # Failed new text: explicit retry and isolation from other sections.
                failing = book['chapters'][1]
                target = '**/' + failing['_data']['url']
                page.route(target, lambda route: route.abort())
                page.evaluate('(parts)=>bookGo(...parts)', [book['level'], book['id'], failing['id']])
                page.wait_for_selector('[data-retry-data]')
                assert page.evaluate('P.xp') == 123
                page.unroute(target)
                page.locator('[data-retry-data]').click()
                page.wait_for_selector('.book-block')
                # Cached text opens even when JSON fetches are unavailable after a reload.
                page.route('**/d/**/*.json', lambda route: route.abort())
                page.reload()
                page.wait_for_selector('.book-block')
                assert page.url.endswith('/' + failing['id'])
                assert not errors, errors
                results.append({'width': width, 'status': 'passed', 'cold_home': cold,
                                'json_requests': len([r for r in requests if '.json' in r]),
                                'initial_storage': before, 'errors': errors})
                context.close()
            browser.close()
    finally:
        server.shutdown()
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f'Browser regression passed at {len(results)} widths; report: {args.report}')


if __name__ == '__main__':
    main()
