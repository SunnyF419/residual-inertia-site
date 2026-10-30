"""The public Pages output is an access notice, never a factor data export."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]

class FactorEntryTests(unittest.TestCase):
    def test_bilingual_access_notice_and_visible_navigation(self):
        for language,title in [('', '因子查询暂未开放'),('en/','Factor research is not available yet')]:
            page=(ROOT/'dist'/language/'factors/index.html').read_text(encoding='utf-8')
            self.assertIn(title,page);self.assertIn('data-factor-access',page)
            self.assertIn('noindex, follow',page)
            self.assertIn('assets/factor-access.js',page)
            self.assertIn('factors/',(ROOT/'dist'/language/'index.html').read_text(encoding='utf-8'))
    def test_no_private_app_or_snapshot_in_static_output(self):
        self.assertFalse((ROOT/'dist/factor-query').exists())
        self.assertFalse(list((ROOT/'dist').rglob('*.duckdb')))
        self.assertNotIn('/factors/',(ROOT/'dist/sitemap.xml').read_text(encoding='utf-8'))
    def test_navigation_check_uses_explicit_owner_capability(self):
        script=(ROOT/'assets/factor-access.js').read_text(encoding='utf-8')
        self.assertIn('session.canQueryFactors===true',script)
        self.assertIn("fetch('/api/research/session'",script)
        self.assertNotIn('localStorage',script)
        self.assertNotIn('canPublish',script)

if __name__=='__main__':unittest.main()
