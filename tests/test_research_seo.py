"""P1 acceptance tests: identity, coauthorship, external records and archive governance."""
import copy
import json
import unittest
from unittest.mock import patch

from test_seo import ROOT, ORIGIN, Head, build, sitemap_urls


def graph(head):
    assert len(head.graphs) == 1
    nodes = head.graphs[0]['@graph']
    assert len(nodes) == len({n['@id'] for n in nodes})
    return {n['@id']: n for n in nodes}


class ResearchSEOTests(unittest.TestCase):
    def setUp(self):
        self.records = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'content/research').glob('*.json')]
        self.snapshots = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / 'content/snapshots').glob('*.json'))]

    def test_about_is_author_entity_page_without_invented_profile(self):
        for prefix in ('', 'en/'):
            html = (ROOT / 'dist' / prefix / 'about/index.html').read_text(encoding='utf-8')
            nodes = graph(Head(html))
            person = nodes[ORIGIN + '#taiyang-feng']
            self.assertEqual(person['jobTitle'], 'Founder and Researcher')
            self.assertEqual(person['alternateName'], 'Sunny')
            self.assertEqual(person['founderOf'], {'@id': ORIGIN + '#organization'})
            self.assertIn('Asset pricing', person['knowsAbout'])
            self.assertNotIn('sameAs', person)  # Paper landing pages are not identity pages.
            self.assertNotIn('worksFor', person)  # A dated manuscript affiliation is not a current employer.
            self.assertEqual(nodes[ORIGIN + prefix + 'about/']['mainEntity'], {'@id': person['@id']})
            self.assertIn('id="founder"', html)
            self.assertIn('Taiyang Feng', html)
            self.assertIn('Sunny', html)
            for record in self.records:
                if record.get('ssrnUrl'):
                    self.assertIn('/' + prefix + 'research/' + record['slug'] + '/', html)
                    paper = (ROOT / 'dist' / prefix / 'research' / record['slug'] / 'index.html').read_text(encoding='utf-8')
                    self.assertIn(record['ssrnUrl'].replace('&', '&amp;'), paper)

    def test_all_research_types_authors_breadcrumb_and_social_metadata(self):
        expected_coauthors = {
            'winners-glide-losers-stumble': ['Juncheng Wen', 'Taiyang Feng'],
            'when-winners-stop-winning': ['Taiyang Feng', 'Jingyi Feng'],
        }
        for prefix in ('', 'en/'):
            for record in self.records:
                with self.subTest(prefix=prefix, slug=record['slug']):
                    html = (ROOT / 'dist' / prefix / 'research' / record['slug'] / 'index.html').read_text(encoding='utf-8')
                    head = Head(html)
                    canonical = ORIGIN + prefix + 'research/' + record['slug'] + '/'
                    nodes = graph(head)
                    article = nodes[canonical + '#article']
                    self.assertEqual(head.canonical(), canonical)
                    self.assertEqual(article['url'], canonical)
                    self.assertEqual(article['mainEntityOfPage'], {'@id': canonical})
                    self.assertEqual(article['datePublished'], record['published'])
                    self.assertEqual(article.get('dateModified'), record.get('updated'))
                    names = [nodes[a['@id']]['name'] for a in article['author']]
                    self.assertEqual(names, expected_coauthors.get(record['slug'], ['Taiyang Feng']))
                    scholarly = bool(record.get('ssrnUrl'))
                    self.assertEqual(article['@type'], 'ScholarlyArticle' if scholarly else 'Article')
                    if scholarly:
                        self.assertEqual(article['sameAs'], [record['ssrnUrl']])
                        self.assertEqual(article['keywords'], record['keywords'])
                        self.assertNotIn('publisher', article)
                        self.assertEqual(nodes[canonical]['publisher'], {'@id': ORIGIN + '#organization'})
                        self.assertIn('rel="noopener noreferrer"', html)
                        self.assertNotEqual(canonical, record['ssrnUrl'])
                    else:
                        self.assertEqual(article['publisher'], {'@id': ORIGIN + '#organization'})
                    self.assertIn('rel="author" href="/' + prefix + 'about/#founder"', html)
                    crumb = nodes[canonical + '#breadcrumb']['itemListElement']
                    self.assertEqual([c['position'] for c in crumb], [1, 2, 3, 4])
                    self.assertEqual([c['item'] for c in crumb], [ORIGIN + prefix, ORIGIN + prefix + 'research/',
                                     ORIGIN + prefix + 'research/' + build.report_variant(record) + '/', canonical])
                    properties = {m.get('property'): m['content'] for m in head.meta if m.get('property')}
                    meta = {m.get('name'): m['content'] for m in head.meta if m.get('name')}
                    self.assertEqual(properties['og:url'], canonical)
                    self.assertEqual(properties['og:type'], 'article')
                    self.assertEqual(properties['og:description'], article['description'])
                    self.assertEqual(meta['twitter:title'], properties['og:title'])
                    self.assertEqual(meta['twitter:description'], properties['og:description'])
                    self.assertEqual(meta['twitter:card'], 'summary')

    def test_aliases_preserve_coauthors_and_organization_publication(self):
        for alias in ('Sunny', 'Sunny Feng', 'Taiyang Feng', 'Taiyang Feng（Sunny）'):
            self.assertEqual(build.research_authors({'author': alias})[0]['@id'], ORIGIN + '#taiyang-feng')
        self.assertEqual([a['name'] for a in build.research_authors({'author': 'Juncheng Wen；Sunny'})], ['Juncheng Wen', 'Taiyang Feng'])
        for author in ('Residual Inertia Research', 'admin', ''):
            self.assertEqual(build.research_authors({'author': author})[0]['@type'], 'Organization')

    def test_doi_is_recorded_not_inferred_and_pdf_is_not_landing_page(self):
        # Published DOI example is a test fixture only, never assigned to an RI paper.
        links = build.external_publications({'doi': '10.1000/182'})
        self.assertEqual(links, [{'kind': 'DOI', 'url': 'https://doi.org/10.1000/182', 'value': '10.1000/182'}])
        links = build.external_publications({'ssrnUrl': 'https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7019599'})
        self.assertEqual([p['kind'] for p in links], ['SSRN'])
        for invalid in ('http://papers.ssrn.com/sol3/papers.cfm?abstract_id=7019599',
                        'https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID7019599_code.pdf'):
            with self.assertRaises(AssertionError):
                build.external_publications({'ssrnUrl': invalid})

    def test_snapshot_decision_uses_vintage_state_prose_and_verification(self):
        previous = copy.deepcopy(self.snapshots[0])
        current = copy.deepcopy(previous)
        current['observationDate'] = '2026-08-25'
        current['market']['regimeScore'] += 0.01
        current['brief']['posture'] = previous['brief']['posture'].replace('100', '99')
        self.assertFalse(build.should_index_snapshot(current, [previous]))
        current['market']['regimeDate'] = '2026-08-25'
        self.assertTrue(build.should_index_snapshot(current, [previous]))
        current['market']['regimeDate'] = previous['market']['regimeDate']
        current['brief']['posture'] += ' A independently verified change in market participation.'
        self.assertTrue(build.should_index_snapshot(current, [previous]))
        current['brief']['posture'] = previous['brief']['posture']
        current['market']['regimeState'] = '防御'
        if previous['market']['regimeState'] == '防御': current['market']['regimeState'] = '谨慎'
        self.assertTrue(build.should_index_snapshot(current, [previous]))
        for mutation in ('hash', 'source', 'pillar', 'commentary'):
            bad = copy.deepcopy(current)
            if mutation == 'hash': bad['contentHash'] = None
            if mutation == 'source': bad['sources'][0]['qualityStatus'] = 'fail'
            if mutation == 'pillar': bad['market']['pillars'].pop()
            if mutation == 'commentary': bad['brief']['posture'] = ''
            with self.subTest(mutation=mutation): self.assertFalse(build.should_index_snapshot(bad, [previous]))

    def test_editorial_override_requires_reason_and_cannot_bypass_completeness(self):
        s = copy.deepcopy(self.snapshots[0])
        policy = {'version': 1, 'overrides': {s['observationDate']: {'index': False, 'reason': 'Unreviewed commentary'}}}
        with patch.object(build, 'SNAPSHOT_INDEXING', policy):
            self.assertFalse(build.should_index_snapshot(s))
            policy['overrides'][s['observationDate']]['index'] = True
            self.assertTrue(build.should_index_snapshot(s))
            s['contentHash'] = ''
            self.assertFalse(build.should_index_snapshot(s))
            policy['overrides'][s['observationDate']]['reason'] = ''
            with self.assertRaises(AssertionError): build.should_index_snapshot(s)

    def test_snapshot_html_and_sitemap_respect_shared_policy_with_self_canonical(self):
        urls = set(sitemap_urls(ROOT / 'dist'))
        for prefix in ('', 'en/'):
            for i, s in enumerate(self.snapshots):
                canonical = ORIGIN + prefix + 'snapshots/' + s['observationDate'] + '/'
                head = Head((ROOT / 'dist' / prefix / 'snapshots' / s['observationDate'] / 'index.html').read_text(encoding='utf-8'))
                expected = build.should_index_snapshot(s, self.snapshots[:i])
                self.assertEqual(head.canonical(), canonical)
                self.assertEqual(head.robots(), 'index, follow' if expected else 'noindex, follow')
                self.assertEqual(canonical in urls, expected)
                nodes = graph(head)
                self.assertEqual(nodes[canonical + '#dataset']['identifier'][0], s['snapshotId'])
                self.assertEqual(len(nodes[canonical + '#dataset']['variableMeasured']), 8)
                crumbs = nodes[canonical + '#breadcrumb']['itemListElement']
                self.assertEqual(crumbs[-2]['item'], ORIGIN + prefix + 'overview/#daily-snapshots')
                self.assertEqual(crumbs[-1]['item'], canonical)
            for kind in ('', 'weekly/', 'monthly/', 'personal/', 'fomc/', 'page/2/'):
                page = Head((ROOT / 'dist' / prefix / 'research' / kind / 'index.html').read_text(encoding='utf-8'))
                self.assertIn(page.canonical() + '#breadcrumb', graph(page))

    def test_future_thematic_and_monthly_use_article_not_scholarly(self):
        record = copy.deepcopy(next(r for r in self.records if r['category'] == '周报'))
        with patch.object(build, 'LANG', 'en'), patch.object(build, 'ROUTE', 'research/example/index.html'):
            for category in ('月报', '专题研究'):
                record['category'] = category
                nodes = build.research_nodes(record)
                self.assertEqual(nodes[0]['@type'], 'Article')
                self.assertEqual(nodes[0]['author'], [{'@id': ORIGIN + '#taiyang-feng'}])


if __name__ == '__main__':
    unittest.main()
