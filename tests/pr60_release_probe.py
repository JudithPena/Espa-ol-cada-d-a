"""Capture pre-release production HTML, then wait for the approved split-data release."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

URL='https://espanolcadadia.pages.dev/'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['capture','wait'])
    parser.add_argument('--directory',type=Path,default=Path('/tmp/pr60-production-check'))
    args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context()
        context.route('**/*',lambda route:route.continue_() if route.request.method in ('GET','HEAD') else route.abort())
        page=context.new_page()
        response=page.goto(URL,wait_until='domcontentloaded',timeout=60000)
        assert response.status==200, f'Production HTTP {response.status}'
        page.wait_for_selector('[data-level="A0"]',timeout=60000)
        if args.mode=='capture':
            assert page.evaluate('!COURSE.resources'),'Release is already active; do not overwrite legacy snapshot'
            html=page.content().encode('utf-8')
            metadata={'url':URL,'bytes':len(html),'sha256':hashlib.sha256(html).hexdigest(),
                      'cache_control':response.headers.get('cache-control','max-age=0, must-revalidate'),
                      'etag':response.headers.get('etag'),'captured_at':time.time()}
            (args.directory/'legacy.html').write_bytes(html)
            (args.directory/'legacy-meta.json').write_text(json.dumps(metadata,indent=2))
            print('LEGACY_CAPTURE_READY '+json.dumps(metadata),flush=True)
        else:
            deadline=time.monotonic()+25*60
            while time.monotonic()<deadline:
                headers=page.evaluate('''async()=>{
                  const r=await fetch(location.origin+'/?pr60-release-check='+Date.now(),{method:'HEAD',cache:'no-store'});
                  return {status:r.status,cache:r.headers.get('cache-control'),etag:r.headers.get('etag')};
                }''')
                assert headers['status']==200, f'HEAD failed: {headers}'
                if 'no-cache' in (headers['cache'] or ''):
                    page.reload(wait_until='domcontentloaded',timeout=60000)
                    page.wait_for_selector('[data-level="A0"]',timeout=60000)
                    if page.evaluate('!!COURSE.resources && COURSE.preview===false'):
                        print('PRODUCTION_RELEASE_VISIBLE '+json.dumps(headers),flush=True)
                        break
                time.sleep(10)
            else:
                raise TimeoutError('Split-data production release did not become visible within 25 minutes')
        context.close()
        browser.close()


if __name__=='__main__':
    main()
