#!/usr/bin/env python3
"""Chromium QA for the irregular preterite unit 59 (responsive + answers + recovery)."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

PREPARE = r"""async ({route, qi=0}) => {
  const u=COURSE.grammar.find(u=>u.number===59);
  if(!u)throw Error('Unit 59 missing');
  if(u._data && (!u.sections?.[0]?.check?.questions || !u.exercises?.[0]?.questions))await dataLoad(u._data);
  P.grammar ||= {}; P.grammarRead ||= {};
  const ix=gRoutes(u).indexOf(route);if(ix<0)throw Error('Invalid route '+route);
  for(const prev of gRoutes(u).slice(0,ix)){
    const g=prev.startsWith('section:')?u.sections[+prev.split(':')[1]].check:u.exercises.find(e=>prev==='exercise:'+e.id);
    if(g)P.grammar[grammarKey(u,g)]={correct:1,total:g.questions.length};
    else P.grammarRead[u.id+'/'+prev]=true;
  }
  const group=route.startsWith('section:')?u.sections[+route.split(':')[1]].check:u.exercises.find(g=>route==='exercise:'+g.id);
  const records=gAttempts(); delete records[grammarKey(u,group)];store.set(G_ATTEMPTS_KEY,JSON.stringify(records));
  save();gStart(u.id,route);gMove(1);
  G.at=G.steps.findIndex(s=>s.type==='question'&&s.group===group.id&&s.qi===qi);
  if(G.at<0)throw Error('Missing question '+route+'/'+qi);
  gSave(); render();
}"""

def assert_layout(page,tag):
    info=page.evaluate("""() => ({
      inner:innerWidth, doc:document.documentElement.scrollWidth,
      player:document.querySelector('.gplayer')?.scrollWidth,
      outside:[...document.querySelectorAll('.gplayer input,.gplayer button')].filter(e=>{
        const r=e.getBoundingClientRect();return r.width>0&&(r.left < -2||r.right>innerWidth+2)
      }).map(e=>e.outerHTML.slice(0,110))
    })""")
    assert info['doc']<=info['inner']+2,(tag,info)
    assert (info['player'] or 0)<=info['inner']+2,(tag,info)
    assert not info['outside'],(tag,info)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--site',type=Path,default=Path('site'))
    ap.add_argument('--report',type=Path,default=Path('/tmp/grammar-unit59-browser.json'))
    args=ap.parse_args()
    args.report.parent.mkdir(parents=True,exist_ok=True)
    shots=args.report.parent/'grammar59-screenshots'
    shots.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(args.site.resolve())))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    outcomes=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            for width in (320,390,768,1280):
                ctx=browser.new_context(viewport={'width':width,'height':820})
                page=ctx.new_page()
                errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.route('https://**/*',lambda route:route.abort())
                page.goto(f'http://127.0.0.1:{server.server_port}/',wait_until='domcontentloaded')
                page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
                # Each new theory mini-check and all tables must fit a narrow viewport.
                for i in range(5):
                    page.evaluate(PREPARE,{'route':f'section:{i}','qi':0})
                    assert page.locator('[data-gpick]').count()>=2
                    assert_layout(page,f'{width}:theory:{i}')
                    if i in (0,2,4):
                        page.screenshot(path=str(shots/f'unit59-{width}-theory-{i}.png'),animations='disabled')
                # Correct and incorrect accents in the current verb topic.
                for route,qi,answer in [
                    ('exercise:59.1a',0,'murieron'),
                    ('exercise:59.1a',2,'divirtió'),
                    ('exercise:59.1b',0,'construyó'),
                    ('exercise:59.1b',2,'oí'),
                    ('exercise:59.1c',0,'tuvieron'),
                    ('exercise:59.1d',0,'condujo'),
                    ('exercise:59.2',0,'murió'),
                    ('exercise:59.3',0,'fui'),
                ]:
                    page.evaluate(PREPARE,{'route':route,'qi':qi})
                    page.locator('#g-answer').fill(answer)
                    page.locator('[data-gcheck]').click()
                    assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,route,qi,answer)
                    assert_layout(page,f'{width}:{route}:{qi}')
                page.evaluate(PREPARE,{'route':'exercise:59.1b','qi':0})
                page.locator('#g-answer').fill('construyo')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).status')=='wrong'
                # Real multi-gap response.
                page.evaluate(PREPARE,{'route':'exercise:59.1c','qi':1})
                gap=page.locator('[data-ggap]')
                assert gap.count()==2
                gap.nth(0).fill('vinieron');gap.nth(1).fill('quisieron')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'two gaps')
                page.evaluate(PREPARE,{'route':'exercise:59.1c','qi':4})
                gap=page.locator('[data-ggap]')
                assert gap.count()==3
                for i,answer in enumerate(('hicieron','estuvimos','quiso')): gap.nth(i).fill(answer)
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'three gaps')
                # Check source-based choice: ser as a title, not movement.
                page.evaluate(PREPARE,{'route':'exercise:59.2','qi':4})
                page.locator('[data-gpick][data-gvalue="fue"]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'ser choice')
                # New tests: independently choose the verb, not just conjugate a provided infinitive.
                for qi,form in ((3,'dijo'),(6,'pude'),(9,'hizo')):
                    page.evaluate(PREPARE,{'route':'exercise:59.1c','qi':qi})
                    picks=page.locator('[data-gpick]')
                    assert picks.count() == 3
                    page.locator(f'[data-gpick][data-gvalue="{form}"]').click()
                    assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'semantic stem choice',qi)
                # Both generated illustrations describe different meanings of fue.
                for qi,lemma in ((8,'ir'),(9,'ser')):
                    page.evaluate(PREPARE,{'route':'exercise:59.2','qi':qi})
                    img=page.locator('img.gquestion-picture')
                    assert img.count()==1,(width,qi,'image missing')
                    page.wait_for_function("document.querySelector('img.gquestion-picture')?.naturalWidth === 384")
                    assert img.get_attribute('alt')
                    assert_layout(page,f'{width}:ser-ir-image:{qi}')
                    page.screenshot(path=str(shots/f'unit59-{width}-ser-ir-{qi}.png'),animations='disabled')
                    page.locator(f'[data-gpick][data-gvalue="{lemma}"]').click()
                    assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'ser/ir meaning',qi)
                page.evaluate(PREPARE,{'route':'exercise:59.3','qi':8})
                two=page.locator('[data-ggap]')
                assert two.count()==2
                two.nth(0).fill('fui');two.nth(1).fill('fue')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gResponse(G.steps[G.at]).good'),(width,'independent ir+ser production')
                # Three distinct failed submissions, explanation, voluntary review.
                page.evaluate(PREPARE,{'route':'exercise:59.1a','qi':0})
                page.locator('#g-answer').fill('morieron')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==1
                assert 'murieron' in page.locator('.pfoot').inner_text().lower()
                page.locator('[data-gnext]').click()
                page.locator('[data-gpick][data-gvalue="pedieron"]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==2
                page.locator('[data-gnext]').click()
                page.locator('#g-answer').fill('divertió')
                page.locator('[data-gcheck]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).status')=='failed'
                assert page.locator('[data-greview-theory]').count()==1
                page.locator('[data-greview-theory]').click()
                assert page.evaluate('Boolean(G.recovery)')
                page.locator('[data-greview-mistake]').click()
                page.locator('[data-grepeat-exercise]').click()
                assert page.evaluate('gAttempt(gUnit(),gUnit().exercises[0]).errors')==0
                # Two dialogue branches and word-bank exercise fit the phone.
                page.evaluate(PREPARE,{'route':'exercise:59.3','qi':2})
                assert page.locator('[data-ggap]').count()==2
                assert_layout(page,f'{width}:dialogue-pairs')
                page.evaluate(PREPARE,{'route':'exercise:59.3','qi':9})
                assert page.locator('[data-gcheck]').count()==1
                assert_layout(page,f'{width}:dialogue-build')
                assert not errors,(width,errors)
                outcomes.append({'width':width,'mini_check_sections':5,
                    'valid_irregular_forms':8,'two_and_three_gaps':True,
                    'three_lives_and_recovery':True,'strict_accents':True,
                    'correct_semantic_ser_choice':True,'overflow':False,'js_errors':errors})
                ctx.close()
            browser.close()
    finally:
        server.shutdown()
        args.report.write_text(json.dumps({'unit':59,'results':outcomes},ensure_ascii=False,indent=2),encoding='utf-8')
    assert len(outcomes)==4
    print('Grammar 59 Chromium QA passed at 320/390/768/1280: irregulars, mini-checks, gaps, accents and recovery')


if __name__=='__main__':
    main()
