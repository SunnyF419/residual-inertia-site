"""Validate generated links, public-content boundaries, and source/output counts."""
import json
import re
import math
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets=[]
        self.ids=set()

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get('id'): self.ids.add(attrs['id'])
        for key in ['href','src']:
            if attrs.get(key): self.targets.append(attrs[key])


def main():
    pages=list(OUT.rglob('*.html'))
    assert pages, 'Build first'
    parsed={}
    for p in pages:
        parser=Links()
        text=p.read_text(encoding='utf-8')
        parser.feed(text)
        parsed[p.resolve()]=parser
        assert '<h1>' in text and '<title>' in text, p
        for target in parser.targets:
            assert not urlsplit(target).path.endswith('.html') or (p.name == '404.html' and urlsplit(target).path in ('/404.html', '/en/404.html')), (p, 'Non-clean page link', target)
        if p.name != 'index.html' and p.name != '404.html':
            target = '/' + p.relative_to(OUT).with_suffix('').as_posix() + '/'
            assert f'content="0;url={target}"' in text, (p, 'Missing legacy redirect')
            assert (OUT / target.strip('/') / 'index.html').is_file(), p
    for p,parser in parsed.items():
        for target in parser.targets:
            u=urlsplit(target)
            if u.scheme or u.netloc: continue
            path=unquote(u.path)
            dest=((OUT/path.lstrip('/')) if path.startswith('/') else p.parent/path).resolve() if path else p
            assert dest.is_relative_to(OUT.resolve()), (p,target)
            if dest.is_dir(): dest=dest/'index.html'
            assert dest.is_file(), (p,target)
            if u.fragment and dest in parsed: assert u.fragment in parsed[dest].ids, (p,target)
    for css in (OUT/'assets').rglob('*.css'):
        for target in re.findall(r'url\([\'"]?([^\)\'\"]+)',css.read_text(encoding='utf-8')):
            assert (css.parent/target).is_file(), target
    forbidden=re.compile(r'(?i)localhost|127\.0\.0\.1|\b[A-Z]:[\\/]|api[_-]?key|access_token|BEGIN .*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{30,}')
    for folder in [ROOT/'content',OUT]:
        for p in folder.rglob('*'):
            if p.suffix in {'.json','.html','.css','.js','.md','.txt'}:
                assert not forbidden.search(p.read_text(encoding='utf-8')), f'Private content pattern in {p.relative_to(ROOT)}'
    snapshots=list((ROOT/'content/snapshots').glob('*.json'))
    for p in snapshots:
        s=json.loads(p.read_text(encoding='utf-8'))
        assert set(s)=={'observationDate','capturedAt','snapshotId','contentHash','market','brief','sources','alerts'}
        assert s['observationDate']==p.stem
        assert (OUT/'snapshots'/f'{p.stem}.html').is_file()
        assert (OUT/'snapshots'/p.stem/'index.html').is_file()
        assert (OUT/'en/snapshots'/f'{p.stem}.html').is_file()
        assert (OUT/'en/snapshots'/p.stem/'index.html').is_file()
    assert '.html' not in (OUT/'sitemap.xml').read_text(encoding='utf-8')
    history = json.loads((ROOT/'content/market/regime-history.json').read_text(encoding='utf-8'))
    start, end = date.fromisoformat(history['windowStart']), date.fromisoformat(history['windowEnd'])
    assert end.year-start.year == 5 and 1825 <= (end-start).days <= 1827
    days = [date.fromisoformat(p['date']) for p in history['points']]
    assert days == sorted(set(days)) and start <= days[0] <= days[-1] <= end
    assert (days[0]-start).days <= 7 and (end-days[-1]).days <= 7
    assert all(math.isfinite(p['score']) and 0 <= p['score'] <= 100 for p in history['points'])
    overview = (OUT/'overview/index.html').read_text(encoding='utf-8')
    assert history['windowStart'] in overview and history['windowEnd'] in overview and '滚动 5 年' in overview
    overview_en = (OUT/'en/overview/index.html').read_text(encoding='utf-8')
    assert history['windowStart'] in overview_en and history['windowEnd'] in overview_en and 'Rolling 5-year' in overview_en
    assert (OUT/'CNAME').read_text().strip()=='residualinertia.com'
    for route in ('global/index.html', 'en/global/index.html'):
        embedded=(OUT/route).read_text(encoding='utf-8')
        assert '<iframe class="global-frame"' in embedded
        assert 'src="https://global.residualinertia.com/?embed=1"' in embedded
        assert 'allowfullscreen' in embedded
        assert 'width="1280" height="800"' in embedded and 'flex:1;min-height:0;width:100%;height:0;' in embedded
        assert '<body class="global-page">' in embedded
        assert re.search(r'href="/assets/site\.css\?v=[a-f0-9]{12}"',embedded)
        assert 'https://global.residualinertia.com/' in embedded
        assert 'class="global-actions"' in embedded
        assert 'class="global-login" href="https://global.residualinertia.com/auth/login" target="_blank" rel="noopener"' in embedded
        assert ('https://residualinertia.com/'+route.replace('index.html','')) in embedded
    assert 'href="/global/"' in (OUT/'index.html').read_text(encoding='utf-8')
    assert 'href="/en/global/"' in (OUT/'en/index.html').read_text(encoding='utf-8')
    assert not list(OUT.rglob('*.py')) and not (OUT/'.git').exists()
    print(f'PASS: {len(pages)} pages, all local links/assets, {len(snapshots)} snapshot exports, public-content scan.')


if __name__=='__main__':
    main()
