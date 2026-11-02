"""Public entry uses the same full workspace; raw databases never enter Pages."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class FactorEntryTests(unittest.TestCase):
    def test_public_entry_in_both_languages(self):
        for prefix, label in [('', '完整公司因子研究台'), ('en/', 'Full company factor research dashboard')]:
            page = (ROOT / 'dist' / prefix / 'factors/index.html').read_text(encoding='utf-8')
            self.assertIn(label, page)
            self.assertIn('class="factor-frame"', page)
            self.assertIn('/account?view=factors&amp;embed=1&amp;lang=', page)
            self.assertIn('class="factors-page"', page)
            self.assertNotIn('data-factor-owner', page)
            self.assertNotIn('data-factor-access', page)
            self.assertNotIn('factor-access.js', page)
            self.assertIn('factors/', (ROOT / 'dist' / prefix / 'index.html').read_text(encoding='utf-8'))

    def test_no_private_snapshot_in_static_output(self):
        self.assertFalse((ROOT / 'dist/factor-query/app.js').exists())
        self.assertFalse(list((ROOT / 'dist').rglob('*.duckdb'))) 

    def test_legacy_address_reaches_current_public_entry(self):
        for prefix in ('', 'en/'):
            page=(ROOT/'dist'/prefix/'factor-query/index.html').read_text(encoding='utf-8')
            self.assertIn('/'+prefix+'factors/',page)
        self.assertFalse((ROOT/'dist/assets/factor-access.js').exists())
