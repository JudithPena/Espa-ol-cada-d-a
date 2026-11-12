#!/usr/bin/env python3
"""Chromium QA for grammar unit 57 on 320, 390, 768 and 1280 pixels."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

PREPARE = r"""async ({route,qi=0}) => {
  const u=COURSE.grammar.find(u=>u.number===57);
  if(!u)throw Error('Unit 57 missing');
  if(u._data && (!u.sections?.[0]?.check?.questions || !u.exercises?.[0]?.questions))await dataLoad(u._data);
  P.grammar ||= {};P.grammarRead ||= {};
  const idx=gRoutes(u).indexOf(route);if(idx<0)throw Error('No route '+route);
  for(const stage of gRoutes(u).slice(0,idx)){
    const g=stage.startsWith('section:')?u.sections[+stage.split(':')[1]].check:u.exercises.find(x=>stage==='exercise:'+x.id);
    if(g)P.grammar[grammarKey(u,g)]={correct:1,total:g.questions.length};
    else P.grammarRead[u.id+'/'+stage]=true;
  }
  const g=route.startsWith('section:')?u.sections[+route.split(':')[1]].check:u.exercises.find(x=>route==='exercise:'+x.id);
  const records=gAttempts();delete records[grammarKey(u,g)];store.set(G_ATTEMPTS_KEY,JSON.stringify(records));
  save();gStart(u.id,route);gMove(1);
  G.at=G.steps.findIndex(s=>s.type==='question'&&s.group===g.id&&s.qi===qi);
  if(G.at<0)throw Error('Question absent '+route+'/'+qi);gSave();render();
}"""

def layout(page,tag):
    info=page.evaluate("""() => ({
        width:innerWidth,document:document.documentElement.scrollWidth,
        player:document.querySelector('.gplayer')?.scrollWidth,
        controls:[...document.querySelectorAll('.gplayer input,.gplayer button')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&(r.left< -2||r.right>innerWidth+2)}).length,
        img:document.querySelector('img.gquestion-picture')?.getBoundingClientRect().toJSON()
    })""")
    assert info['document']<=info['width']+2,(tag,info)
    assert (info['player'] or 0)<=info['width']+2,(tag,info)
    assert info['controls']==0,(tag,info)
    if info['img']:
        assert info['img']['left']>=-2 and info['img']['right']<=info['width']+2,(tag,info)

def wrong(page,qi,values):
    page.evaluate("""qi => {G.at=G.steps.findIndex(s=>s.type==='question'&&s.group==='57.1'&&s.qi===qi);gSave();render()}""",qi)
    gaps=page.locator('[data-ggap]')
    assert gaps.count()==len(values),(qi,values,gaps.count())
    for i,v in enumerate(values): gaps.nth(i).fill(v)
    page.locator('[data-gcheck]').click()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--site',type=Path,default=Path('site'))
    ap.add_argument('--report',type=Path,default=Path('/tmp/grammar-unit57-browser.json'));args=ap.parse_args()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    screenshots=args.report.parent/'grammar57-screenshots';screenshots.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(args.site.resolve())))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            for width in (320,390,768,1280):
                ctx=browser.new_context(viewport={'width':width,'height':820})
                page=ctx.new_page();errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.route('https://**/*',lambda r:r.abort())
                page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='domcontentloaded')
                page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
                page.evaluate(PREPARE,{'route':'exercise:57.1','qi':0})
                for qi in (0,2,5):
                    page.evaluate("""qi=>{G.at=G.steps.findIndex(s=>s.type==='question'&&s.group==='57.1'&&s.qi===qi);gSave();render()}""",qi)
                    img=page.locator('img.gquestion-picture')
                    assert img.count()==1,(width,qi,'picture missing')
                    page.wait_for_function("document.querySelector('img.gquestion-picture')?.naturalWidth===384")
                    assert img.get_attribute('alt'),(width,qi,'alt')
                    layout(page,f'{width}:57.1:{qi}')
                    page.screenshot(path=str(screenshots/f'unit57-{width}-picture-{qi}.png'),animations='disabled')
                # All theory/mini-checks render without horizontal clipping.
                for i in range(4):
                    page.evaluate(PREPARE,{'route':f'section:{i}','qi':1})
                    layout(page,f'{width}:section:{i}')
                    assert page.locator('[data-gpick]').count()>=2
                # Multiple gaps: accept the correct two-person response.
                page.evaluate(PREPARE,{'route':'exercise:57.1','qi':0})
                gaps=page.locator('[data-ggap]');assert gaps.count()==2
                gaps.nth(0).fill('toca');gaps.nth(1).fill('toca')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).good')
                # Three real errors -> stay on explanation and allow voluntary retry.
                page.evaluate(PREPARE,{'route':'exercise:57.1','qi':0})
                wrong(page,0,['tocan','tocan'])
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==1
                page.locator('[data-gnext]').click()
                wrong(page,1,['tocan','jugamos'])
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==2
                page.locator('[data-gnext]').click()
                page.locator('#g-answer').fill('doy')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).status')=='failed'
                assert page.locator('[data-greview-theory]').count()==1
                page.locator('[data-greview-theory]').click()
                assert page.evaluate('Boolean(G.recovery)')
                page.locator('[data-greview-mistake]').click()
                page.locator('[data-grepeat-exercise]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==0
                # Both normative answers to «¿Qué ___? — Un concurso» are accepted.
                for ans in ('ves','estás viendo'):
                    page.evaluate(PREPARE,{'route':'exercise:57.4','qi':2})
                    page.locator('#g-answer').fill(ans)
                    page.locator('[data-gcheck]').click()
                    assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,ans)
                    layout(page,f'{width}:57.4:alt')
                page.evaluate(PREPARE,{'route':'exercise:57.4','qi':2})
                page.locator('#g-answer').fill('estas viendo')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).status')=='wrong'
                # Real choice prompt and three-gap dialogue visible.
                page.evaluate(PREPARE,{'route':'exercise:57.3','qi':0})
                assert page.locator('[data-gpick]').count()>=2
                layout(page,f'{width}:57.3:choice')
                page.evaluate(PREPARE,{'route':'exercise:57.4','qi':6})
                assert page.locator('[data-ggap]').count()==3
                layout(page,f'{width}:57.4:3gaps')
                assert not errors,(width,errors)
                results.append({'width':width,'illustrations':3,'accepted_normative_answers':2,'accent_strict':True,'three_lives':True,'overflow':False,'js_errors':errors})
                ctx.close()
            browser.close()
    finally:
        server.shutdown()
        args.report.write_text(json.dumps({'unit':57,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    assert len(results)==4
    print('Unit 57 Chromium QA passed: 320/390/768/1280, 3 illustrations, 3 lives, answer alternatives, no overflow')

if __name__=='__main__':
    main()
