"""Real Chromium checks for units 67–70. Build site --preview; serve site/ at 127.0.0.1:8765."""
import importlib.util
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

spec=importlib.util.spec_from_file_location('feedback',Path('tests/grammar_immediate_feedback_browser.py'))
f=importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
f.REPORT['browser']='Chromium via Playwright (Linux)'
f.REPORT['limitations']=['Native Android/iOS keyboards are not available; the 520px viewport checks reduced visible height only.']
OUT=Path('docs/grammar_units/browser67_70')
OUT.mkdir(parents=True,exist_ok=True)
report={'widths':[320,390,768,1280],'questions':0,'theory':0,'images':0,'failures':[],'checks':[]}

def submit(page,q,answer=None):
    value=answer or q['answers'][0]
    if q.get('options'):
        page.locator('[data-gvalue]').filter(has_text=value).count()
        page.evaluate('v=>[...document.querySelectorAll("[data-gvalue]")].find(b=>b.dataset.gvalue===v).click()',value)
    elif q.get('tiles'):
        for word in value.split():
            buttons=page.locator('.gbuild-bank [data-gadd]')
            for i in range(buttons.count()):
                if buttons.nth(i).inner_text().strip()==word and buttons.nth(i).is_enabled():
                    buttons.nth(i).click()
                    break
            else: raise AssertionError('No tile '+word)
        page.locator('[data-gcheck]').click()
    elif q.get('gapParts'):
        words=value.split();pos=0
        fields=page.locator('[data-ggap]')
        assert fields.count()==len(q['gapWordCounts'])
        for i,count in enumerate(q['gapWordCounts']):
            fields.nth(i).fill(' '.join(words[pos:pos+count]));pos+=count
        page.locator('[data-gcheck]').click()
    else:
        page.locator('#g-answer').fill(value)
        page.locator('[data-gcheck]').click()

with sync_playwright() as p:
    kwargs={'headless':True}
    exe=os.environ.get('ECD_CHROME')
    if exe:kwargs['executable_path']=exe
    browser=p.chromium.launch(**kwargs)
    for width in report['widths']:
        ctx=browser.new_context(viewport={'width':width,'height':850},device_scale_factor=1)
        page=ctx.new_page();errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(f.ORIGIN,wait_until='domcontentloaded')
        page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
        for number in [67,68,69,70]:
            unit=page.evaluate('''async number=>{const u=COURSE.grammar.find(u=>u.number===number);await dataLoad(u._data);return u;}''',number)
            for route in unit['learningOrder']:
                if route=='summary':
                    page.evaluate('''n=>{const u=COURSE.grammar.find(u=>u.number===n);P.grammarRead||={};for(const s of u.sections)P.grammar[grammarKey(u,s.check)]={correct:3,total:3};for(const g of u.exercises)P.grammar[grammarKey(u,g)]={correct:g.questions.length,total:g.questions.length};gStart(u.id,'summary');render();}''',number)
                    f.check_layout(page,f'{number} summary {width}')
                    assert 'Что запомнить' in page.locator('body').inner_text()
                    # The map scrolls inside the player: enlarge the viewport so the whole map is in one screenshot.
                    page.set_viewport_size({'width':width,'height':3200 if width<768 else 1700})
                    f.check_layout(page,f'{number} summary tall {width}')
                    clipped=page.evaluate('()=>[...document.querySelectorAll(".gplayer *")].filter(el=>{const r=el.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1}).length')
                    assert clipped==0,(number,width,'summary elements beyond the right edge',clipped)
                    page.screenshot(path=str(OUT/f'u{number}_summary_{width}.png'))
                    page.set_viewport_size({'width':width,'height':850})
                    continue
                page.evaluate(f.PREPARE,{'number':number,'route':route,'qi':0})
                group=(unit['sections'][int(route.split(':')[1])]['check'] if route.startswith('section:') else next(g for g in unit['exercises'] if g['id']==route.split(':')[1]))
                if route.startswith('section:'):
                    page.evaluate('G.at=G.steps.findIndex(s=>s.type!=="question");gSave();render()')
                    f.check_layout(page,f'{number} {route} theory {width}')
                    assert page.locator('.gplayer').inner_text().find('**')<0
                    page.wait_for_function("()=>[...document.querySelectorAll('.gplayer img')].every(im=>im.complete&&im.naturalWidth>0)")
                    report['theory']+=1
                else:
                    page.evaluate('G.at=0;gSave();render()')
                    intro=page.locator('.gplayer').inner_text()
                    assert '→ la' not in intro
                    f.check_layout(page,f'{number} {route} preview {width}')
                for qi,q in enumerate(group['questions']):
                    page.evaluate('''({id,qi})=>{G.at=G.steps.findIndex(s=>s.type==='question'&&s.group===id&&s.qi===qi);gSave();render();}''',{'id':group['id'],'qi':qi})
                    f.check_layout(page,f'{number} {route} {qi} {width}')
                    if q.get('image'):
                        page.wait_for_function('''()=>[...document.querySelectorAll('.gplayer img')].every(im=>im.complete&&im.naturalWidth>0)''')
                        report['images']+=1
                    submit(page,q)
                    result=page.evaluate('''()=>({good:gResponse(G.steps[G.at]).good,checked:gResponse(G.steps[G.at]).checked})''')
                    assert result=={'good':True,'checked':True},(number,route,qi,result)
                    f.check_layout(page,f'{number} {route} accepted {width}')
                    report['questions']+=1
                    if width==390 and qi==0:
                        page.screenshot(path=str(OUT/f'u{number}_{route.replace(":","_")}.png'))
            if number==67:
                assert page.evaluate("gNextUnit(COURSE.grammar.find(u=>u.number===61)).number")==67
            if number<70:
                page.evaluate("G.at=G.steps.length-1;gSave();render()")
                assert page.evaluate('gNextUnit(gUnit()).number')==number+1
        assert not errors,errors
        ctx.close()
    # Three-error recovery for a regular input and a dependent multi-field dialogue.
    f.OUT=OUT;f.SHOTS=OUT
    for width in report['widths']:
        f.run_case(browser,width,67,'exercise:67.1','input')
        f.run_case(browser,width,67,'exercise:67.2','gaps',qi=1)
    report['recovery']=f.REPORT
    report['failures'].extend(f.REPORT['failures'])
    # Strict acute accents through actual input controls.
    for ref,number,route,qi,bad in [('volveréis',67,'exercise:67.1',0,'volvereis'),('habrá',68,'exercise:68.1',1,'habra'),('vendrán',68,'exercise:68.3',3,'vendran')]:
        ctx=browser.new_context();page=ctx.new_page();page.goto(f.ORIGIN);page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
        page.evaluate(f.PREPARE,{'number':number,'route':route,'qi':qi})
        page.locator('#g-answer').fill(bad);page.locator('[data-gcheck]').click()
        assert page.evaluate('gResponse(G.steps[G.at]).good') is False
        assert 'Верный ответ:' in page.locator('.fb').inner_text()
        report['checks'].append(ref+' rejects omitted accent');ctx.close()
    # Alternative pronoun position and both future forms are accepted through the real input.
    for number,route,qi,alt in [(69,'exercise:69.1',0,'se van a bañar'),(69,'exercise:69.2',2,'van a alojarse'),(70,'exercise:70.1',0,'harán')]:
        ctx=browser.new_context();page=ctx.new_page();page.goto(f.ORIGIN);page.wait_for_function("typeof gStart==='function' && COURSE.grammar.length>0")
        page.evaluate(f.PREPARE,{'number':number,'route':route,'qi':qi})
        page.locator('#g-answer').fill(alt);page.locator('[data-gcheck]').click()
        assert page.evaluate('gResponse(G.steps[G.at]).good') is True,(number,route,alt)
        report['checks'].append(f'{alt} accepted');ctx.close()
    browser.close()
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='recovery'},ensure_ascii=False))
assert not report['failures']
