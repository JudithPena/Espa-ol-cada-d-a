"""Render actual summary topic maps, test responsive scroll, export screenshot deliverables."""
import argparse
import functools
import json
import os
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

PREPARE = """async n => {
 const u=COURSE.grammar.find(u=>u.number===n); await dataLoad(u._data);
 P.grammar ||= {}; P.grammarRead ||= {};
 for(const g of [...u.sections.map(s=>s.check),...u.exercises])
  P.grammar[grammarKey(u,g)]={correct:g.questions.length,total:g.questions.length};
 gStart(u.id,'summary');render();
}"""

EXPORT_CSS = """
html,body {height:auto!important;overflow:visible!important;}
.gplayer-topic-map {position:relative!important;inset:auto!important;height:auto!important;min-height:100vh;display:block!important;overflow:visible!important;}
.gplayer-topic-map .pbody {height:auto!important;overflow:visible!important;}
.gplayer-topic-map .pfoot {position:static!important;}
"""

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--site',default='site')
    parser.add_argument('--url')
    parser.add_argument('--output',default='docs/grammar_units/summary_map_browser')
    args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    server=None
    if args.url:
        origin=args.url
    else:
        class QuietHandler(SimpleHTTPRequestHandler):
            def log_message(self,*args): pass
        server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=args.site))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        origin=f'http://127.0.0.1:{server.server_port}'
    report={'source':origin,'widths':[320,390,768,1440],'checks':[],'screenshots':[]}
    try:
        with sync_playwright() as p:
            options={'headless':True}
            if os.environ.get('ECD_CHROME'):options['executable_path']=os.environ['ECD_CHROME']
            browser=p.chromium.launch(**options)
            for width in report['widths']:
                for number in (60,61):
                    ctx=browser.new_context(viewport={'width':width,'height':1000 if width>600 else 900},device_scale_factor=1,color_scheme='light')
                    page=ctx.new_page();errors=[]
                    page.on('pageerror',lambda e:errors.append(e.stack))
                    page.goto(origin,wait_until='domcontentloaded')
                    page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
                    page.evaluate(PREPARE,number)
                    page.locator('.gmap').wait_for()
                    page.evaluate('document.fonts.ready')
                    for img in page.locator('.gmap img').all():
                        img.scroll_into_view_if_needed()
                        img.evaluate("im=>im.loading='eager'")
                    page.wait_for_function("()=>[...document.querySelectorAll('.gmap img')].every(im=>im.complete&&im.naturalWidth>0)")
                    page.evaluate("document.querySelector('.pbody').scrollTop=0")
                    layout=page.evaluate("""()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
                        columns:getComputedStyle(document.querySelector('.gmap-grid')).gridTemplateColumns.split(' ').length,
                        cards:[...document.querySelectorAll('.gmap-card')].map(e=>({left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right,width:e.clientWidth,scroll:e.scrollWidth})),
                        mapWidth:document.querySelector('.gmap').scrollWidth,footerTop:document.querySelector('.pfoot').getBoundingClientRect().top})""")
                    assert layout['documentWidth']<=width+1,layout
                    assert layout['columns']==(1 if width<=580 else 2 if width<=1020 else 3),layout
                    assert all(c['left']>=0 and c['right']<=width+1 and c['scroll']<=c['width']+1 for c in layout['cards']),layout
                    page.screenshot(path=str(output/f'unit{number}-{width}-viewport.png'))
                    page.locator('.gmap-takeaway').scroll_into_view_if_needed()
                    bottom=page.locator('.gmap-takeaway').bounding_box()
                    assert bottom['y']>=0 and bottom['y']+bottom['height']<=layout['footerTop']+1,(layout,bottom)
                    assert page.locator('.gmap-card').count()==6
                    # Full-content export preserves CSS width, fonts and card layout; only expands the scroll container.
                    style=page.add_style_tag(content=EXPORT_CSS)
                    page.screenshot(path=str(output/f'unit{number}-{width}-full.png'),full_page=True)
                    style.evaluate('e=>e.remove()')
                    page.evaluate("document.querySelector('.pbody').scrollTop=0")
                    before=page.evaluate('JSON.stringify(P.grammar)')
                    page.locator('[data-gnext]').click()
                    assert page.evaluate("gRouteDone(gUnit(),'summary')")
                    assert page.evaluate('JSON.stringify(P.grammar)')==before
                    if number==60 and width==390:
                        page.locator('[data-gnext-unit]').click()
                        page.wait_for_function("gUnit()?.number===61 && document.querySelector('.gplayer')")
                        assert page.evaluate('JSON.stringify(P.grammar)')==before
                    assert not errors,errors
                    report['checks'].append({'unit':number,'width':width,'layout':layout,'status':'passed'})
                    report['screenshots'].append(f'unit{number}-{width}-full.png')
                    ctx.close()
            # Other units retain their original table/schemes and narrow player.
            ctx=browser.new_context();page=ctx.new_page();page.goto(origin)
            page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
            for number in (1,59):
                page.evaluate(PREPARE,number)
                assert page.locator('.gmap').count()==0
                assert page.locator('.gplayer-topic-map').count()==0
            ctx.close()
            # Dark colors and effective narrow width after zoom still retain readable, unclipped cards.
            ctx=browser.new_context(viewport={'width':390,'height':900},color_scheme='dark')
            page=ctx.new_page();page.goto(origin);page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
            page.evaluate(PREPARE,61)
            page.screenshot(path=str(output/'unit61-390-dark.png'))
            page.add_style_tag(content='body {zoom:1.25}')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            ctx.close();browser.close()
    finally:
        if server:server.shutdown()
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'checks':len(report['checks']),'widths':report['widths'],'output':str(output)},ensure_ascii=False))

if __name__=='__main__':main()
