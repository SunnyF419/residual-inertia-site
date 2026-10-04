"""SEO acceptance checks on the production HTML and future monthly content."""
import copy
import importlib.util
import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://residualinertia.com/'
spec = importlib.util.spec_from_file_location('seo_build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.meta, self.links, self.titles, self.graphs = [], [], [], []
        self.in_head = self.in_title = self.in_json = False
        self.title = self.script = ''
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'head': self.in_head = True
        if tag == 'meta': self.meta.append(attrs)
        if tag == 'link': self.links.append(attrs)
        if tag == 'title' and self.in_head: self.in_title = True
        if tag == 'script': self.in_json = attrs.get('type') == 'application/ld+json'

    def handle_data(self, text):
        if self.in_title: self.title += text
        if self.in_json: self.script += text

    def handle_endtag(self, tag):
        if tag == 'head': self.in_head = False
        if tag == 'title' and self.in_title:
            self.titles.append(self.title)
            self.title = ''
            self.in_title = False
        if tag == 'script' and self.in_json:
            self.graphs.append(json.loads(self.script))
            self.script = ''
            self.in_json = False

    def canonical(self):
        values = [a['href'] for a in self.links if a.get('rel') == 'canonical']
        assert len(values) == 1
        return values[0]

    def robots(self):
        values = [a['content'] for a in self.meta if a.get('name') == 'robots']
        assert len(values) == 1
        return values[0]

    def alternates(self):
        values = [a for a in self.links if a.get('hreflang')]
        assert len(values) == len({a['hreflang'] for a in values})
        return {a['hreflang']: a['href'] for a in values}


def sitemap_urls(output):
    tree = ET.parse(output / 'sitemap.xml')
    return [node.text for node in tree.findall('{*}url/{*}loc')]


class SEOTests(unittest.TestCase):
    def test_home_titles_descriptions_brand_definition_and_graph(self):
        cases = [('', 'zh-CN',
                  'Residual Inertia 余势｜独立投资研究、量化市场观察与决策系统',
                  'Residual Inertia（余势）是由 Taiyang Feng（Sunny）创立的独立投资研究与决策系统平台，聚焦量化投资、资产定价、宏观市场、市场风险与研究基础设施。'),
                 ('en/', 'en',
                  'Residual Inertia | Independent Investment Research & Decision Systems',
                  'Residual Inertia is an independent investment research and decision systems platform founded by Taiyang Feng (Sunny), focused on quantitative investing, asset pricing, macro markets, market risk, and research infrastructure.')]
        for prefix, language, title, description in cases:
            with self.subTest(language=language):
                text = (ROOT / 'dist' / prefix / 'index.html').read_text(encoding='utf-8')
                head = Head(text)
                self.assertEqual(head.titles, [title])
                self.assertEqual([a['content'] for a in head.meta if a.get('name') == 'description'], [description])
                self.assertEqual(head.canonical(), ORIGIN + prefix)
                self.assertEqual(head.alternates(), {'zh-CN': ORIGIN, 'en': ORIGIN + 'en/', 'x-default': ORIGIN})
                self.assertIn('<p class="brand-definition">' + description + '</p>', text)
                self.assertLess(text.index('class="brand-definition"'), text.index('class="home-featured"'))
                self.assertIn(build.CONFIG['hero_en' if prefix else 'hero'].replace('，', '，<br>'), text)
                self.assertEqual(len(head.graphs), 1)
                payload = head.graphs[0]
                nodes = {node['@type']: node for node in payload['@graph']}
                self.assertEqual(set(nodes), {'Organization', 'Person', 'WebSite'})
                org, person, website = (nodes[t] for t in ('Organization', 'Person', 'WebSite'))
                self.assertEqual(org['@id'], ORIGIN + '#organization')
                self.assertEqual(org['name'], 'Residual Inertia')
                self.assertEqual(org['alternateName'], '余势')
                self.assertEqual(org['description'], description)
                self.assertEqual(org['founder'], {'@id': ORIGIN + '#taiyang-feng'})
                self.assertTrue((ROOT / urlsplit(org['logo']).path.lstrip('/')).is_file())
                self.assertEqual(person['@id'], ORIGIN + '#taiyang-feng')
                self.assertEqual(person['name'], 'Taiyang Feng')
                self.assertEqual(person['alternateName'], 'Sunny')
                self.assertEqual(person['url'], ORIGIN + 'about/#founder')
                self.assertEqual(person['founderOf'], {'@id': org['@id']})
                self.assertEqual(payload['@context']['founderOf'], {'@reverse': 'https://schema.org/founder'})
                self.assertNotIn('sameAs', person)
                self.assertEqual(website['@id'], ORIGIN + '#website')
                self.assertEqual(website['publisher'], {'@id': org['@id']})
                self.assertEqual(website['inLanguage'], ['zh-CN', 'en'])

    def test_all_indexable_pages_canonicals_alternate_reciprocity_and_sitemap(self):
        output = ROOT / 'dist'
        urls = sitemap_urls(output)
        self.assertEqual(len(urls), len(set(urls)))
        indexable = set()
        for page in output.rglob('*.html'):
            with self.subTest(page=page.relative_to(output)):
                head = Head(page.read_text(encoding='utf-8'))
                self.assertEqual(len(head.titles), 1)
                canonical = head.canonical()
                self.assertTrue(canonical.startswith(ORIGIN))
                if head.robots() == 'noindex, follow':
                    # A legacy redirect may point to an indexable canonical, but its own URL is excluded.
                    self.assertNotIn(ORIGIN + page.relative_to(output).as_posix().removesuffix('index.html'), urls)
                    if not any(a.get('http-equiv') == 'refresh' for a in head.meta):
                        self.assertNotIn(canonical, urls)
                    continue
                self.assertEqual(head.robots(), 'index, follow')
                self.assertEqual(canonical, ORIGIN + page.relative_to(output).as_posix().removesuffix('index.html'))
                indexable.add(canonical)
                self.assertEqual(len([a for a in head.meta if a.get('name') == 'description']), 1)
                self.assertEqual(len(head.graphs), 1)
                ids = [node['@id'] for node in head.graphs[0]['@graph']]
                self.assertEqual(len(ids), len(set(ids)))
                self.assertIn(ORIGIN + '#organization', ids)
                self.assertIn(ORIGIN + '#taiyang-feng', ids)
                alternates = head.alternates()
                if not alternates: continue
                self.assertEqual(set(alternates), {'zh-CN', 'en', 'x-default'})
                self.assertEqual(alternates['x-default'], alternates['zh-CN'])
                self.assertIn(canonical, alternates.values())
                for target in set(alternates.values()):
                    self.assertIn(target, urls)
                    counterpart = output / urlsplit(target).path.lstrip('/') / 'index.html'
                    self.assertTrue(counterpart.is_file())
                    self.assertEqual(Head(counterpart.read_text(encoding='utf-8')).alternates(), alternates)
        self.assertEqual(set(urls), indexable)
        self.assertEqual((output / 'robots.txt').read_text(encoding='utf-8'),
                         'User-agent: *\nAllow: /\nSitemap: https://residualinertia.com/sitemap.xml\n')
        for prefix in ('', 'en/'):
            for route in ('snapshots/2026-10-01/', 'research/when-winners-stop-winning/'):
                self.assertFalse(Head((output / prefix / route / 'index.html').read_text(encoding='utf-8')).alternates())

    def test_monthly_archive_automatically_becomes_indexable_with_first_report(self):
        snapshot = json.loads(sorted((ROOT / 'content/snapshots').glob('*.json'))[-1].read_text(encoding='utf-8'))
        monthly = copy.deepcopy(json.loads((ROOT / 'content/research/market-letter-2026-10-03.json').read_text(encoding='utf-8')))
        monthly.update(category='月报', slug='monthly-seo-test')
        for reports in ([], [monthly]):
            with self.subTest(report_count=len(reports)), tempfile.TemporaryDirectory() as temp:
                with patch.object(build, 'OUT', Path(temp)), patch.object(build, 'ALL_PAGES', []), patch.object(build, 'PAGE_SEO', {}), patch.object(build, 'PATHS', []), patch.object(build, 'LANG', 'zh'):
                    for lang in ('zh', 'en'):
                        build.LANG = lang
                        build.build_language([snapshot], reports, snapshot)
                    build.add_language_alternates()
                    build.write_sitemap()
                    urls = sitemap_urls(Path(temp))
                    for prefix in ('', 'en/'):
                        page = Head((Path(temp) / prefix / 'research/monthly/index.html').read_text(encoding='utf-8'))
                        expected = 'index, follow' if reports else 'noindex, follow'
                        self.assertEqual(page.robots(), expected)
                        self.assertEqual(ORIGIN + prefix + 'research/monthly/' in urls, bool(reports))

    def test_unregistered_translation_never_emits_hreflang(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(build, 'OUT', Path(temp)), patch.object(build, 'ALL_PAGES', []), patch.object(build, 'PAGE_SEO', {}), patch.object(build, 'PATHS', []), patch.object(build, 'LANG', 'zh'):
            build.write('only-zh.html', 'Only Chinese', lambda: '<h1>中文页面</h1>')
            build.add_language_alternates()
            self.assertFalse(Head((Path(temp) / 'only-zh/index.html').read_text(encoding='utf-8')).alternates())

    def test_structured_json_cannot_close_its_script_element(self):
        with patch.object(build, 'LANG', 'zh'), patch.dict(build.I18N, {'home_desc': ('</script><script>alert(1)</script>', 'English')}):
            markup = build.structured_data(home=True)
            self.assertEqual(markup.count('</script>'), 1)
            self.assertEqual(Head(markup).graphs[0]['@graph'][0]['description'], '</script><script>alert(1)</script>')


if __name__ == '__main__':
    unittest.main()
