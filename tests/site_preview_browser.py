"""Verify the deployed PR60 preview with real MP3 and a legacy-page upgrade."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def wait_home(page):
    page.wait_for_selector('[data-level="A0"]', timeout=60000)
    page.wait_for_function('!COURSE.resources || dataLoaded.has(COURSE.resources.common.url)', timeout=60000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--allow-production', action='store_true')
    parser.add_argument('--legacy-html', type=Path)
    parser.add_argument('--legacy-meta', type=Path)
    parser.add_argument('--production', default='https://espanolcadadia.pages.dev/')
    parser.add_argument('--report', type=Path, default=Path('/tmp/site-preview-browser.json'))
    args = parser.parse_args()
    url = args.url.rstrip('/') + '/'
    host = urlparse(url).hostname
    assert (args.allow_production and host=='espanolcadadia.pages.dev') or (host and host.endswith('.espanolcadadia.pages.dev') and host!='espanolcadadia.pages.dev'), 'Explicit production opt-in required'
    report = {'preview': url, 'widths': []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            if args.legacy_html:
                assert args.legacy_meta and args.legacy_meta.is_file()
                old_html=args.legacy_html.read_bytes()
                meta=json.loads(args.legacy_meta.read_text())
                old_cache=meta['cache_control']
                report['legacy_capture']='actual production DOM captured before merge'
            else:
                legacy_context=browser.new_context()
                legacy_page=legacy_context.new_page()
                legacy_response=legacy_page.goto(args.production,wait_until='domcontentloaded',timeout=60000)
                assert legacy_response.status==200
                old_html=legacy_page.content().encode('utf-8')
                old_cache=legacy_response.headers.get('cache-control','max-age=0, must-revalidate')
                legacy_context.close()
            assert b'const COURSE = ' in old_html
            report.update(legacy_dom_sha256=hashlib.sha256(old_html).hexdigest(),legacy_dom_bytes=len(old_html),legacy_cache_control=old_cache)
            for width in (390, 1280):
                context = browser.new_context(viewport={'width': width, 'height': 850})
                # No writes to any server: only isolated browser storage contains test progress.
                context.route('**/*', lambda route: route.continue_() if route.request.method in ('GET','HEAD') else route.abort())
                page = context.new_page()
                errors, responses = [], {}
                page.on('response', lambda response: responses.update({response.url:response}))
                page.on('pageerror', lambda error: errors.append(str(error)))
                # Simulate replacing an old release on the SAME origin: seed old progress,
                # let the actual old player save a grammar session, then fetch the real new HTML.
                page.route(url, lambda route: route.fulfill(status=200, body=old_html, headers={'content-type':'text/html; charset=utf-8', 'cache-control':old_cache}))
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                wait_home(page)
                page.evaluate('''() => {
                  P.openAll=true; P.xp=1234; P.done[LESSONS[0].id]={stars:3}; P.ver[LESSONS[0].id]={v:LESSONS[0].version};
                  P.words[LESSONS[0].words[0].es]={s:3,due:1}; saveLocal();
                  localStorage.setItem('preview-unrelated-key','keep');
                  view.grammar=COURSE.grammar[0].id;view.tab='grammar';gStart(view.grammar,'all');gSave();
                }''')
                before = page.evaluate('({p:JSON.parse(localStorage.getItem(KEY)),session:localStorage.getItem(G_SESSION_KEY)})')
                page.unroute(url)
                response = page.reload(wait_until='domcontentloaded', timeout=60000)
                wait_home(page)
                assert page.evaluate('(expected)=>COURSE.preview===expected && !!COURSE.resources', not args.allow_production)
                assert 'no-cache' in response.headers.get('cache-control', '')
                after = page.evaluate('({p:JSON.parse(localStorage.getItem(KEY)),session:localStorage.getItem(G_SESSION_KEY)})')
                assert before == after, 'Progress/session changed during old-to-new upgrade'
                assert page.evaluate('localStorage.getItem("preview-unrelated-key")') == 'keep'
                resource_url = page.evaluate('COURSE.resources.common.url')
                resource = responses.get(url + resource_url)
                assert resource and resource.status == 200
                assert 'immutable' in resource.headers.get('cache-control', '')
                assert hashlib.sha256(resource.body()).hexdigest() == Path(urlparse(resource_url).path).stem
                audio_count = page.evaluate('Object.keys(AUDIO).length')
                assert audio_count > 3000
                # New tab / entry from each level's real catalog. Existing course routes use history.state.
                lessons = []
                for level in ('A0', 'A1'):
                    page.evaluate('(level)=>{S=null;G=null;view.tab="course";view.level=level;render()}', level)
                    li = page.evaluate('(level)=>LESSONS.findIndex(L=>L.level===level && L.words.length)', level)
                    page.locator(f'[data-lesson="{li}"]').first.click()
                    page.wait_for_function('S && S.steps.length>0', timeout=60000)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                    phrase = page.evaluate('(i)=>LESSONS[i].words.find(w=>audioId(w.say))?.say', li)
                    assert phrase
                    page.evaluate('(text)=>say(text)', phrase)
                    page.wait_for_function('player && player.readyState>=2 && player.duration>0 && player.currentTime>0 && !player.error', timeout=30000)
                    clip = page.evaluate('({src:player.src,duration:player.duration,time:player.currentTime})')
                    assert urlparse(clip['src']).hostname == host
                    lessons.append({'level':level,'id':page.evaluate('(i)=>LESSONS[i].id',li),'audio':clip})
                    page.go_back()
                    # Browser back is previous slide when one is available; at first slide it exits.
                    page.wait_for_function('S===null', timeout=30000)
                    assert page.evaluate('view.tab==="course"')
                # Independent grammar, including the actual old saved session.
                page.evaluate('view.tab="grammar";view.grammar=COURSE.grammar[0].id;render()')
                page.wait_for_selector('[data-gresume]', timeout=60000)
                page.locator('[data-gresume]').click()
                page.wait_for_selector('.gplayer')
                assert page.evaluate('G.unit===COURSE.grammar[0].id')
                page.locator('[data-gexit]').first.click()
                page.wait_for_selector('[data-gstart]')
                checked_units=[]
                for unit_id in page.evaluate('COURSE.grammar.filter(u=>[1,13,47].includes(u.number)).map(u=>u.id)'):
                    page.evaluate('(id)=>{view.tab="grammar";view.grammar=id;render()}',unit_id)
                    page.wait_for_selector('[data-gstart]',timeout=60000)
                    page.locator('[data-gstart]').first.click()
                    page.wait_for_selector('.gplayer')
                    assert page.evaluate('G.unit')==unit_id
                    checked_units.append(unit_id)
                    page.locator('[data-gexit]').first.click()
                    page.wait_for_selector('[data-gstart]')
                assert len(checked_units)==3
                # Character-specific prerecorded clip, fetched and decoded from Cloudflare.
                dialogue = page.evaluate('''() => {
                  const key=Object.keys(AUDIO).find(k=>k.startsWith('@'));
                  const split=key.indexOf('|');return {voice:key.slice(1,split),text:key.slice(split+1),id:AUDIO[key]};
                }''')
                page.evaluate('(d)=>playClip(d.text,{voice:d.voice})', dialogue)
                page.wait_for_function('player && player.readyState>=2 && player.currentTime>0 && !player.error', timeout=30000)
                assert page.evaluate('player.src').endswith('/a/' + dialogue['id'] + '.mp3')
                page.evaluate('stopSpeech();view.tab="books";render()')
                page.wait_for_function('COURSE.books.length>0', timeout=60000)
                book = page.evaluate('COURSE.books.find(b=>b.kind!=="collection" && b.chapters.length>1)')
                book_hash = '#books/' + book['level'] + '/' + book['id']
                page.goto(url + book_hash)
                page.wait_for_selector('[data-book-chapter]')
                assert page.url.endswith(book_hash)
                assert page.locator('.book-availability').count() == 0
                chapter = book['chapters'][0]
                chapter_hash = book_hash + '/' + chapter['id']
                for direct_hash, selector in ((book_hash, '[data-book-chapter]'), (chapter_hash, '.book-block')):
                    direct = context.new_page()
                    direct.goto(url + direct_hash, wait_until='domcontentloaded', timeout=60000)
                    direct.wait_for_selector(selector, timeout=60000)
                    assert direct.url.endswith(direct_hash)
                    direct.close()
                page.goto(url + chapter_hash)
                page.wait_for_selector('.book-block')
                assert page.url.endswith(chapter_hash)
                assert page.get_by_role('heading', name='Разбор текста', exact=True).count() == 0
                assert page.locator('[data-book-jump]').count() > 0
                page.locator('[data-book-nav="chapters"]').first.click()
                page.wait_for_selector('[data-book-chapter]')
                page.go_back();page.wait_for_selector('.book-block')
                page.go_forward();page.wait_for_selector('[data-book-chapter]')
                # Preserve the latest approved book cover and removal of obsolete labels.
                story = page.evaluate('COURSE.books.find(b=>b.id==="el-hombre-que-veia-demasiado")')
                assert story, 'Current story missing from the independently loaded catalog'
                page.goto(url + '#books/' + story['level'] + '/' + story['id'])
                page.wait_for_selector('.book-block', timeout=60000)
                assert page.get_by_role('heading', name='Разбор текста', exact=True).count() == 0
                assert page.locator('.book-availability').count() == 0
                cover_sha = hashlib.sha256(Path('content/books/el-hombre-que-veia-demasiado/cover-generated.webp').read_bytes()).hexdigest()
                assert story['cover'] == 'i/' + cover_sha + '.webp'
                page.wait_for_function('''() => {
                  const img=document.querySelector('.book-cover-large');return img && img.complete && img.naturalWidth>0;
                }''', timeout=30000)
                dimensions=page.locator('.book-cover-large').evaluate('(img)=>({width:img.naturalWidth,height:img.naturalHeight})')
                assert 1.45 < dimensions['height']/dimensions['width'] < 1.55
                # Fail only one previously unopened JSON and then retry on the actual preview.
                other = book['chapters'][1]
                target = '**/' + other['_data']['url']
                page.route(target, lambda route: route.abort())
                page.evaluate('(v)=>bookGo(...v)', [book['level'],book['id'],other['id']])
                page.wait_for_selector('[data-retry-data]')
                assert page.evaluate('P.xp') == 1234
                page.unroute(target)
                page.locator('[data-retry-data]').click()
                page.wait_for_selector('.book-block')
                # JSON persisted in Cache API works with the JSON network disabled after reload.
                page.route('**/d/**/*.json', lambda route: route.abort())
                page.reload(wait_until='domcontentloaded', timeout=60000)
                page.wait_for_selector('.book-block', timeout=60000)
                assert page.evaluate('P.xp') == 1234
                assert not errors, errors
                report['widths'].append({'width':width,'status':'passed','old_to_new_progress':'identical',
                    'root_cache_control':response.headers.get('cache-control'),'audio_keys':audio_count,
                    'lessons':lessons,'dialogue':dialogue,'grammar_units':checked_units,
                    'approved_story_cover':{'id':story['id'],'sha256':cover_sha,'dimensions':dimensions,'removed_labels':'absent'},'book_url':url+book_hash,'chapter_url':url+chapter_hash,'fresh_direct_links':'passed','retry':'passed','offline_cached_json':'passed','errors':errors})
                context.close()
            browser.close()
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(('PRODUCTION_CHECK_REPORT ' if args.allow_production else 'DEPLOYED_PREVIEW_REPORT ') + json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
