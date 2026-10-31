"""Public lookup stays separate from the private factor workspace."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class FactorEntryTests(unittest.TestCase):
    def test_public_entry_in_both_languages(self):
        for prefix, label in [('', '股票代码或公司名称'), ('en/', 'Ticker or company name')]:
            page = (ROOT / 'dist' / prefix / 'factors/index.html').read_text(encoding='utf-8')
            self.assertIn(label, page)
            self.assertIn('data-profile hidden', page)
            self.assertIn('data-factor-owner hidden', page)
            self.assertNotIn('data-factor-denied', page)
            self.assertIn('factors/', (ROOT / 'dist' / prefix / 'index.html').read_text(encoding='utf-8'))

    def test_no_private_snapshot_in_static_output(self):
        self.assertFalse((ROOT / 'dist/factor-query/app.js').exists())
        self.assertFalse(list((ROOT / 'dist').rglob('*.duckdb'))) 
