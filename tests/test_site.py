"""Regressions for the dashboard's score boundaries and public research paths."""
import importlib.util
import hashlib
import json
import math
import re
import unittest
from unittest.mock import patch
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('site_build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def with_class(self, cls):
        return [attrs for _, attrs in self.elements if cls in attrs.get('class', '').split()]


class SiteTests(unittest.TestCase):
    def test_search_indexes_complete_collections_without_extra_visible_cards(self):
        reports = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'content/research').glob('*.json')]
        scopes = {'research/index.html': reports,
                  'research/page/2/index.html': reports,
                  'research/personal/index.html': [r for r in reports if build.collection(r) == 'personal'],
                  'research/weekly/index.html': [r for r in reports if build.report_variant(r) == 'weekly'],
                  'research/monthly/index.html': [r for r in reports if build.report_variant(r) == 'monthly']}
        for prefix in ('', 'en/'):
            for route, expected in scopes.items():
                page = (ROOT / 'dist' / prefix / route).read_text(encoding='utf-8')
                payload = re.search(r'<script type="application/json" data-search-data>(.*?)</script>', page, re.S).group(1)
                self.assertNotIn('<', payload)
                entries = json.loads(payload)
                self.assertEqual(len(entries), len(expected))
                self.assertLessEqual(len(Elements(page).with_class('research-card')), 6)
                for report in expected:
                    entry = next(item for item in entries if report['title'] in item['text'])
                    with patch.object(build, 'LANG', 'en' if prefix else 'zh'):
                        self.assertIn(build.author_display(report), entry['text'])
                    self.assertIn(report['published'], entry['text'])
                    if report.get('ssrnUrl'):
                        self.assertIn(report['ssrnUrl'], entry['text'])
                    self.assertIn('/' + prefix + 'research/' + report['slug'] + '/', entry['html'])

    def test_research_pagination_boundaries_and_category_links(self):
        original_lang = build.LANG
        try:
            for lang, prefix in [('zh','/'),('en','/en/')]:
                build.LANG = lang
                for count in (0, 1, 6, 7, 12, 13, 60):
                    reports = list(range(count))
                    seen = []
                    for page in range(1, build.research_page_count(reports) + 1):
                        def cards(items):
                            seen.extend(items)
                            self.assertLessEqual(len(items), 6)
                            return ''.join(f'<article data-test-report="{item}"></article>' for item in items)
                        with patch.object(build, 'research_cards', side_effect=cards):
                            body = build.research_library(reports, page, 'research/weekly', '<p>Empty</p>')
                        dom = Elements(body)
                        if count > 6:
                            current = [a for tag,a in dom.elements if a.get('aria-current') == 'page']
                            self.assertEqual(len(current), 1)
                            expected = prefix + 'research/weekly/' + (f'page/{page}/' if page > 1 else '')
                            self.assertEqual(current[0]['href'], expected)
                            directions = [a for a in dom.with_class('research-page-direction') if 'href' in a]
                            self.assertEqual(len(directions), int(page > 1) + int(page < build.research_page_count(reports)))
                            for tag, attrs in dom.elements:
                                if tag == 'a':
                                    self.assertTrue(attrs['href'].startswith(prefix+'research/weekly/'))
                        else:
                            self.assertFalse(dom.with_class('research-pagination'))
                    self.assertEqual(seen, reports)
                with self.assertRaises(AssertionError):
                    build.research_library([], 2)
        finally:
            build.LANG = original_lang

    def test_registered_report_versions_match_published_pdf_bytes(self):
        registry = json.loads((ROOT/'content/research-registry.json').read_text(encoding='utf-8'))
        for entry in registry['reports']:
            report = json.loads((ROOT/'content/research'/(entry['slug']+'.json')).read_text(encoding='utf-8'))
            data = (ROOT/report['pdf']).read_bytes()
            self.assertTrue(data.startswith(b'%PDF-'))
            self.assertEqual(hashlib.sha256(data).hexdigest(), report['pdfSha256'])
            self.assertEqual(report['pdfSha256'], entry['pdfSha256'])
            self.assertEqual(report['version'], entry['version'])
            self.assertEqual(report['researchId'], entry['researchId'])
            self.assertEqual(report['periodDate'], entry['periodDate'])

    def test_report_types_and_weekly_monthly_filters(self):
        for record, expected in [({'category':'周报','collection':'market'},'weekly'),
                                 ({'category':'月报','collection':'market'},'monthly'),
                                 ({'category':'SSRN 论文','collection':'personal'},'personal'),
                                 ({'category':'FOMC研究','collection':'fomc'},'fomc')]:
            self.assertEqual(build.report_variant(record), expected)
        research = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'content/research').glob('*.json')]
        for prefix in ('','en/'):
            for kind in ('weekly','monthly','personal','fomc'):
                page = (ROOT/'dist'/prefix/'research'/kind/'index.html').read_text(encoding='utf-8')
                matching = [r for r in research if build.report_variant(r) == kind]
                self.assertEqual(len(Elements(page).with_class('report-cover-'+kind)), len(matching))
                active = [attrs for _,attrs in Elements(page).elements if attrs.get('aria-current') == 'page']
                self.assertEqual(len(active), 1)
                self.assertEqual(active[0]['href'], '/'+prefix+'research/'+kind+'/')
                for r in matching:
                    article = (ROOT/'dist'/prefix/'research'/r['slug']/'index.html').read_text(encoding='utf-8')
                    self.assertIn('href="/'+prefix+'research/'+kind+'/"', article)

    def test_dashboard_score_boundaries_before_rounding(self):
        # 34.99 and 64.99 round up in display, but must keep their original colors.
        cases = [(0, 'constructive'), (34.99, 'constructive'), (35, 'neutral'),
                 (49.99, 'neutral'), (50, 'caution'), (64.99, 'caution'),
                 (65, 'defensive'), (67.3, 'defensive'), (79.99, 'defensive'),
                 (80, 'stress'), (100, 'stress'), (None, 'unknown'),
                 (math.nan, 'unknown'), (math.inf, 'unknown')]
        for score, expected in cases:
            with self.subTest(score=score):
                self.assertEqual(build.score_tone(score), expected)
        css = (ROOT / 'assets/site.css').read_text(encoding='utf-8').lower()
        palette = {'constructive': '#5d8f7e', 'neutral': '#526260', 'caution': '#c79242',
                   'defensive': '#c86159', 'stress': '#853f39', 'unknown': '#526260'}
        for tone, color in palette.items():
            self.assertIn(f'.tone-{tone}{{--score-color:{color}}}', css)
        self.assertIn('.score-value,.reading-state{color:var(--score-color,var(--slate))}', css)
        self.assertIn('background:var(--score-color,var(--slate))', css)

    def test_actual_research_and_archive_paths_in_both_languages(self):
        research = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'content/research').glob('*.json')]
        snapshots = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT / 'content/snapshots').glob('*.json'))]
        latest = build.latest_reading(snapshots)
        for prefix in ('', 'en/'):
            with self.subTest(language=prefix or 'zh'):
                home = (ROOT / 'dist' / prefix / 'index.html').read_text(encoding='utf-8')
                dom = Elements(home)
                self.assertEqual(len(dom.with_class('home-featured')), 1)
                self.assertEqual(len(dom.with_class('home-updates')), 1)
                self.assertFalse(dom.with_class('reading-card'))
                motif = dom.with_class('cover-kline')
                self.assertEqual(len(motif), 1)
                self.assertEqual(motif[0]['aria-hidden'], 'true')
                self.assertIn('/assets/site-motion.js?v=', home)
                self.assertEqual(len(dom.with_class('cover-primary')), 1)
                self.assertEqual(len(dom.with_class('cover-secondary')), 1)
                self.assertTrue(Elements(home).with_class('action-icon'))
                self.assertEqual(len(dom.with_class('cover-emblem')), 1)
                library = (ROOT / 'dist' / prefix / 'research/index.html').read_text(encoding='utf-8')
                self.assertEqual(len(Elements(library).with_class('research-card')), min(6, len(research)))
                self.assertFalse(Elements(library).with_class('folder-card'))
                owner_link = Elements(library).with_class('report-import')[0]
                self.assertIn('hidden', owner_link)
                self.assertEqual(owner_link['href'], 'https://global.residualinertia.com/auth/login?next=/research/manage')
                archive_pages = [library] + [(ROOT/'dist'/prefix/'research'/'page'/str(page)/'index.html').read_text(encoding='utf-8') for page in range(2, build.research_page_count(research)+1)]
                for page in archive_pages:
                    self.assertLessEqual(len(Elements(page).with_class('research-card')), 6)
                self.assertEqual(sum(len(Elements(page).with_class('research-card')) for page in archive_pages),len(research))
                sitemap = (ROOT/'dist'/'sitemap.xml').read_text(encoding='utf-8')
                for page in range(2, build.research_page_count(research)+1):
                    self.assertIn('https://residualinertia.com/'+prefix+f'research/page/{page}/', sitemap)
                for r in research:
                    path = f'/{prefix}research/{r["slug"]}/'
                    # Contextual category links may repeat a destination; each report card belongs to one page.
                    self.assertEqual(sum(a.get('href') == path for page in archive_pages for a in Elements(page).with_class('report-card-link')),1)
                    article = (ROOT / 'dist' / prefix / 'research' / r['slug'] / 'index.html').read_text(encoding='utf-8')
                    self.assertIn(r['published'], article)
                    pdf_links = [attrs for _,attrs in Elements(article).elements if urlsplit(attrs.get('href','')).path == '/'+r['pdf']]
                    self.assertTrue(pdf_links)
                    self.assertTrue(all('download' not in attrs for attrs in pdf_links))
                    action = Elements(article).with_class('cover-primary')[0]
                    self.assertEqual(urlsplit(action['href']).path, '/'+r['pdf'])
                    self.assertTrue(urlsplit(action['href']).query.startswith('v='))
                    self.assertNotIn('target', action)
                    self.assertFalse(Elements(article).with_class('pdf-document'))
                    self.assertNotIn('id="pdf-reader"',article)
                    self.assertIn('article-intro', article)
                overview = (ROOT / 'dist' / prefix / 'overview/index.html').read_text(encoding='utf-8')
                dom = Elements(overview)
                reading = dom.with_class('reading-card')[0]
                self.assertIn('tone-' + build.score_tone(latest['market']['regimeScore']), reading['class'].split())
                self.assertEqual(len(dom.with_class('snapshot-item')), len(snapshots))
                self.assertEqual(len(dom.with_class('overview-current')), 1)
                self.assertEqual(len(dom.with_class('score-legend')), 1)
                # State cutoff comes from the daily state model, not the weekly risk model.
                self.assertIn(latest['market']['regimeDate'][:10], overview)
                self.assertEqual(len(dom.with_class('overview-pillar')), len(latest['market']['pillars']))
                for p in latest['market']['pillars']:
                    width = f'width:{p["score"]:.4f}%'
                    matching = [attrs for _, attrs in dom.elements if attrs.get('style') == width]
                    self.assertEqual(len(matching), 1)
                    self.assertIn('tone-' + build.score_tone(p['score']), matching[0]['class'])


if __name__ == '__main__':
    unittest.main()
