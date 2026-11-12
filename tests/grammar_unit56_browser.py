#!/usr/bin/env python3
"""Responsive Chromium QA of grammar unit 56 images, input, alternatives and recovery.

Run from repository root after `python -m espanol site`:
  python tests/grammar_unit56_browser.py --site site --report /tmp/grammar-unit56-browser.json
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


PREPARE = r"""async ({route,qi=0}) => {
  const u=COURSE.grammar.find(u=>u.number===56);
  if(!u)throw Error('Unit 56 missing');
  if(u._data && (!u.sections?.[0]?.check?.questions || !u.exercises?.[0]?.questions))await dataLoad(u._data);
  P.grammar ||= {};P.grammarRead ||= {};
  const idx=gRoutes(u).indexOf(route);
  if(idx<0)throw Error('Route absent: '+route);
  for(const stage of gRoutes(u).slice(0,idx)){
    const g=stage.startsWith('section:')?u.sections[+stage.split(':')[1]].check:u.exercises.find(x=>stage==='exercise:'+x.id);
    if(g)P.grammar[grammarKey(u,g)]={correct:1,total:g.questions.length};
    else P.grammarRead[u.id+'/'+stage]=true;
  }
  save();gStart(u.id,route);gMove(1);
  G.at=G.steps.findIndex(s=>s.type==='question'&&s.group===(route.startsWith('section:')?u.sections[+route.split(':')[1]].check.id:route.split(':')[1])&&s.qi===qi);
  if(G.at<0)throw Error('Question not found '+route+'/'+qi);
  gSave();render();
}"""


def check_no_overflow(page, tag):
    info = page.evaluate("""() => ({
      width:innerWidth, document:document.documentElement.scrollWidth,
      player:document.querySelector('.gplayer')?.scrollWidth,
      img:document.querySelector('img.gquestion-picture')?.getBoundingClientRect().toJSON(),
      tooWide:[...document.querySelectorAll('.gplayer input,.gplayer button')].filter(e=>{
        let r=e.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+2||r.left< -2)
      }).map(e=>e.outerHTML.slice(0,120))
    })""")
    assert info['document']<=info['width']+2, (tag,info)
    assert (info['player'] or 0)<=info['width']+2, (tag,info)
    assert not info['tooWide'], (tag,info)
    if info['img']:
        assert info['img']['left']>=-2 and info['img']['right']<=info['width']+2, (tag,info)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--site',type=Path,default=Path('site'))
    p.add_argument('--report',type=Path,default=Path('/tmp/grammar-unit56-browser.json'))
    args=p.parse_args()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    folder=args.report.parent/'grammar56-screenshots'
    folder.mkdir(parents=True,exist_ok=True)
    srv=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(args.site.resolve())))
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    result=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            for width in (320,390,768,1280):
                ctx=browser.new_context(viewport={'width':width,'height':820})
                page=ctx.new_page()
                js_errors=[]
                page.on('pageerror',lambda e:js_errors.append(str(e)))
                page.route('https://**/*',lambda route:route.abort())
                page.goto(f'http://127.0.0.1:{srv.server_port}/',wait_until='domcontentloaded')
                page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
                page.evaluate(PREPARE,{'route':'exercise:56.1','qi':0})
                images=[]
                for qi in range(8):
                    page.evaluate("""qi=>{G.at=G.steps.findIndex(s=>s.type==='question'&&s.group==='56.1'&&s.qi===qi);gSave();render()}""",qi)
                    img=page.locator('img.gquestion-picture').first
                    assert img.count()==1,(width,qi,'missing picture')
                    page.wait_for_function("document.querySelector('img.gquestion-picture')?.naturalWidth===384")
                    alt=img.get_attribute('alt')
                    assert alt and not alt.isspace(),(width,qi,'missing alt')
                    check_no_overflow(page,f'{width}:56.1:{qi}')
                    images.append(alt)
                    if qi in (0,4):
                        page.screenshot(path=str(folder/f'unit56-{width}-picture-{qi}.png'),animations='disabled')
                # A correct answer is accepted by the actual player.
                page.evaluate(PREPARE,{'route':'exercise:56.1','qi':0})
                page.locator('#g-answer').fill('Están jugando')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'visual correct failed')
                # Real keyboard flow through the three-life failure/retry path.
                page.evaluate(PREPARE,{'route':'exercise:56.1','qi':0})
                page.locator('#g-answer').fill('estoy jugando')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==1
                assert 'Están jugando' in page.locator('.pfoot').inner_text()
                page.locator('[data-gnext]').click()
                page.locator('#g-answer').fill('está lloviendo')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==2
                page.locator('[data-gnext]').click()
                gap=page.locator('[data-ggap]')
                assert gap.count()==2
                gap.nth(0).fill('estoy')
                gap.nth(1).fill('jugando')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).status')=='failed'
                assert page.locator('[data-greview-theory]').count()==1
                page.locator('[data-greview-theory]').click()
                assert page.evaluate('Boolean(G.recovery)')
                page.locator('[data-greview-mistake]').click()
                page.locator('[data-grepeat-exercise]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==0
                # Both accent-preserving clitic positions are green in the actual player.
                for answer in ('Nos estamos vistiendo.','Estamos vistiéndonos.'):
                    page.evaluate(PREPARE,{'route':'exercise:56.4','qi':8})
                    page.locator('#g-answer').fill(answer)
                    page.locator('[data-gcheck]').click()
                    assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,answer)
                    check_no_overflow(page,f'{width}:clitic')
                # Without the required accent the same answer is red.
                page.evaluate(PREPARE,{'route':'exercise:56.4','qi':8})
                page.locator('#g-answer').fill('Estamos vistiendonos.')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).status')=='wrong'
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[3]).errors')==1
                # The semantic contrast has two fields, and all expected choices render.
                page.evaluate(PREPARE,{'route':'exercise:56.2','qi':8})
                assert page.locator('[data-ggap]').count()==2
                check_no_overflow(page,f'{width}:contrast-gaps')
                page.evaluate(PREPARE,{'route':'exercise:56.2','qi':9})
                assert page.locator('[data-gchoice]').count()>0 or page.locator('[data-gpick]').count()>0 or page.locator('.goptions button').count()>0,(width,'contrast buttons')
                check_no_overflow(page,f'{width}:contrast-choice')
                assert not js_errors,(width,js_errors)
                result.append({'width':width,'pictures':len(images),'clitic_variants':2,'accent_strict':True,'three_lives':True,'overflow':False,'js_errors':js_errors})
                ctx.close()
            browser.close()
    finally:
        srv.shutdown()
        args.report.write_text(json.dumps({'unit':56,'results':result},ensure_ascii=False,indent=2),encoding='utf-8')
    assert len(result)==4
    print('Unit 56 browser QA passed on 320/390/768/1280: 8 pictures, reflexives, 3 lives, contrast, no overflow')


if __name__=='__main__':
    main()
