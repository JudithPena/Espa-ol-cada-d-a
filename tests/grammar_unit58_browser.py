#!/usr/bin/env python3
"""Real Chromium QA for new grammar unit 58, four screen widths and strict accents."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

PREPARE = r"""async ({route,qi=0}) => {
  const u=COURSE.grammar.find(u=>u.number===58);
  if(!u)throw Error('Unit 58 missing');
  if(u._data && (!u.sections?.[0]?.check?.questions || !u.exercises?.[0]?.questions))await dataLoad(u._data);
  P.grammar ||= {};P.grammarRead ||= {};
  const idx=gRoutes(u).indexOf(route);
  if(idx<0)throw Error('Route absent: '+route);
  for(const stage of gRoutes(u).slice(0,idx)){
    const g=stage.startsWith('section:')?u.sections[+stage.split(':')[1]].check:u.exercises.find(x=>stage==='exercise:'+x.id);
    if(g)P.grammar[grammarKey(u,g)]={correct:1,total:g.questions.length};
    else P.grammarRead[u.id+'/'+stage]=true;
  }
  const group=route.startsWith('section:')?u.sections[+route.split(':')[1]].check:u.exercises.find(g=>route==='exercise:'+g.id);
  const records=gAttempts();delete records[grammarKey(u,group)];store.set(G_ATTEMPTS_KEY,JSON.stringify(records));
  save();gStart(u.id,route);gMove(1);
  G.at=G.steps.findIndex(s=>s.type==='question'&&s.group===group.id&&s.qi===qi);
  if(G.at<0)throw Error('Question not found '+route+'/'+qi);
  gSave();render();
}"""

def check_layout(page,label):
    info=page.evaluate("""() => ({
        width:innerWidth,doc:document.documentElement.scrollWidth,
        player:document.querySelector('.gplayer')?.scrollWidth,
        outside:[...document.querySelectorAll('.gplayer input,.gplayer button')].filter(e=> {
          const r=e.getBoundingClientRect();
          return r.width>0&&(r.left< -2||r.right>innerWidth+2)
        }).map(e=>e.outerHTML.slice(0,120))
    })""")
    assert info['doc']<=info['width']+2,(label,info)
    assert (info['player'] or 0)<=info['width']+2,(label,info)
    assert not info['outside'],(label,info)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--site',type=Path,default=Path('site'))
    ap.add_argument('--report',type=Path,default=Path('/tmp/grammar-unit58-browser.json'))
    args=ap.parse_args()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    shots=args.report.parent/'grammar58-screenshots'
    shots.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(args.site.resolve())))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            for width in (320,390,768,1280):
                ctx=browser.new_context(viewport={'width':width,'height':820})
                page=ctx.new_page()
                errors=[]
                page.on('pageerror',lambda exc:errors.append(str(exc)))
                page.route('https://**/*',lambda route:route.abort())
                page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='domcontentloaded')
                page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
                for i in range(4):
                    page.evaluate(PREPARE,{'route':f'section:{i}','qi':0})
                    check_layout(page,f'{width}:theory:{i}')
                    assert page.locator('[data-gpick]').count()>1
                    if i in (0,1):
                        page.screenshot(path=str(shots/f'unit58-{width}-check-{i}.png'),animations='disabled')
                # Multi-gap question checks two separate answers.
                page.evaluate(PREPARE,{'route':'exercise:58.1','qi':0})
                gaps=page.locator('[data-ggap]')
                assert gaps.count()==2,(width,gaps.count())
                gaps.nth(0).fill('salí');gaps.nth(1).fill('me levanté')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'two gaps')
                # Strict accents for required -é/-ó, no added accents for vi/di/vio/dio.
                for route,qi,answer in [
                    ('exercise:58.1',11,'trabajó'),
                    ('exercise:58.2',7,'saqué'),
                    ('exercise:58.3',3,'vi'),
                    ('exercise:58.3',6,'di'),
                    ('exercise:58.4',0,'se trasladó')
                ]:
                    page.evaluate(PREPARE,{'route':route,'qi':qi})
                    page.locator('#g-answer').fill(answer)
                    page.locator('[data-gcheck]').click()
                    assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,route,qi,answer)
                    check_layout(page,f'{width}:{route}:{qi}')
                page.evaluate(PREPARE,{'route':'exercise:58.1','qi':11})
                page.locator('#g-answer').fill('trabajo')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).status')=='wrong'
                # Three lives + stay on wrong question until voluntary review.
                page.evaluate(PREPARE,{'route':'exercise:58.1','qi':0})
                for n in (1,2):
                    for field in page.locator('[data-ggap]').all():field.fill('incorrecto')
                    page.locator('[data-gcheck]').click()
                    assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==n
                    page.locator('[data-gnext]').click()
                page.locator('#g-answer').fill('incorrecto')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).status')=='failed'
                assert page.locator('[data-greview-theory]').count()==1
                page.locator('[data-greview-theory]').click()
                assert page.evaluate('Boolean(G.recovery)')
                page.locator('[data-greview-mistake]').click()
                page.locator('[data-grepeat-exercise]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==0
                # Longer biographical section and source reading on a narrow device.
                page.evaluate(PREPARE,{'route':'exercise:58.4','qi':5})
                check_layout(page,f'{width}:biography')
                assert not errors,(width,errors)
                results.append({'width':width,'mini_checks':4,'multi_gap':True,
                                'accent_strict':True,'three_lives':True,
                                'overflow':False,'js_errors':errors})
                ctx.close()
            browser.close()
    finally:
        server.shutdown()
        args.report.write_text(json.dumps({'unit':58,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    assert len(results)==4
    print('Unit 58 browser QA passed on 320/390/768/1280: mini checks, gaps, accents, 3 lives, no overflow')

if __name__=='__main__':
    main()
