"""Regressions for the dashboard's score boundaries and public research paths."""
import importlib.util
import json
import math
import unittest
from html.parser import HTMLParser
from pathlib import Path

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
        latest = snapshots[-1]
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
                self.assertEqual(len(dom.with_class('button-icon')), 2)
                self.assertEqual(len(dom.with_class('cover-emblem')), 1)
                library = (ROOT / 'dist' / prefix / 'research/index.html').read_text(encoding='utf-8')
                self.assertEqual(len(Elements(library).with_class('research-card')), len(research))
                self.assertFalse(Elements(library).with_class('folder-card'))
                owner_link = Elements(library).with_class('report-import')[0]
                self.assertIn('hidden', owner_link)
                self.assertEqual(owner_link['href'], 'https://global.residualinertia.com/auth/login?next=/research/manage')
                for r in research:
                    path = f'/{prefix}research/{r["slug"]}/'
                    self.assertIn(f'href="{path}"', library)
                    article = (ROOT / 'dist' / prefix / 'research' / r['slug'] / 'index.html').read_text(encoding='utf-8')
                    self.assertIn(r['published'], article)
                    self.assertIn(f'href="/{r["pdf"]}"', article)
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
