"""Visible knowledge-graph links, freshness and brand consistency without new SEO routes."""
import json
import unittest
from test_seo import ROOT, ORIGIN, Head, build, sitemap_urls
from test_site import Elements


class BrandAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.records = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'content/research').glob('*.json')]

    def test_about_and_research_hub_have_visible_paths_to_real_work(self):
        for prefix in ('', 'en/'):
            about = (ROOT / 'dist' / prefix / 'about/index.html').read_text(encoding='utf-8')
            links = {a.get('href') for tag, a in Elements(about).elements if tag == 'a'}
            for route in ('research/weekly/', 'research/fomc/', 'research/personal/', 'research/personal/#scholarly-research', 'overview/', 'global/'):
                self.assertIn('/' + prefix + route, links)
            self.assertIn('id="research-process"', about)
            self.assertIn('Taiyang Feng (Sunny)', about)
            hub = (ROOT / 'dist' / prefix / 'research/index.html').read_text(encoding='utf-8')
            self.assertEqual(len(Elements(hub).with_class('research-card')), 6)
            self.assertIn('id="research-directions"', hub)
            self.assertIn('rel="author" href="/' + prefix + 'about/#founder"', hub)
            nodes = {n['@id']: n for n in Head(hub).graphs[0]['@graph']}
            canonical = ORIGIN + prefix + 'research/'
            self.assertEqual(nodes[canonical]['@type'], 'CollectionPage')
            listed = nodes[canonical + '#reports']['itemListElement']
            self.assertEqual(len(listed), 6)
            self.assertEqual(len({i['item']['@id'] for i in listed}), 6)
            self.assertTrue(all(i['item']['url'] in sitemap_urls(ROOT / 'dist') for i in listed))

    def test_related_reports_follow_source_period_and_real_content(self):
        current = next(r for r in self.records if r['slug'] == 'market-letter-2026-10-03')
        previous = next(r for r in self.records if r['slug'] == 'market-letter-2026-09-26')
        self.assertEqual(build.related_reports(current, self.records)[0]['slug'], previous['slug'])
        scholarly = next(r for r in self.records if r['slug'] == 'winners-glide-losers-stumble')
        self.assertEqual([r['slug'] for r in build.related_reports(scholarly, self.records)], ['when-winners-stop-winning'])
        for prefix in ('', 'en/'):
            article = (ROOT / 'dist' / prefix / 'research' / current['slug'] / 'index.html').read_text(encoding='utf-8')
            self.assertIn('href="/' + prefix + 'research/' + previous['slug'] + '/"', article)
            self.assertIn('href="/' + prefix + 'overview/"', article)

    def test_publication_dates_and_existing_versions_are_not_rewritten(self):
        for record in self.records:
            page = Head((ROOT / 'dist/research' / record['slug'] / 'index.html').read_text(encoding='utf-8'))
            node = next(n for n in page.graphs[0]['@graph'] if n['@type'] in ('Article', 'ScholarlyArticle'))
            self.assertEqual(node['datePublished'], record['published'])
            self.assertEqual(node.get('dateModified'), record.get('updated'))
            self.assertEqual(node.get('version'), record.get('version'))
            if record.get('researchId'): self.assertEqual(node['identifier'], record['researchId'])
            if record.get('dataThrough'): self.assertEqual(node['temporalCoverage'], record['dataThrough'])

    def test_global_application_and_website_share_the_existing_organization(self):
        export = json.loads((ROOT / 'dist/assets/brand/entity.json').read_text(encoding='utf-8'))
        self.assertEqual(export['organization']['@id'], ORIGIN + '#organization')
        self.assertEqual(export['organization']['founder'], {'@id': ORIGIN + '#taiyang-feng'})
        for prefix in ('', 'en/'):
            page = Head((ROOT / 'dist' / prefix / 'global/index.html').read_text(encoding='utf-8'))
            nodes = {n['@id']: n for n in page.graphs[0]['@graph']}
            app = nodes['https://global.residualinertia.com/#application']
            self.assertEqual(app['creator'], {'@id': ORIGIN + '#organization'})
            self.assertEqual(page.canonical(), ORIGIN + prefix + 'global/')
        # No low-content methodology or tag routes are manufactured.
        for route in ('methodology', 'data-sources', 'research-process', 'topics', 'tags'):
            self.assertFalse((ROOT / 'dist' / route).exists())


if __name__ == '__main__':
    unittest.main()
