"""Public article figures must resolve locally and preserve accessible captions."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('insight_site_build', ROOT / 'scripts/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class InsightFigures(unittest.TestCase):
    def test_bilingual_figures_and_method_disclosures(self):
        r = json.loads((ROOT/'content/research/what-margin-debt-tells-us.json').read_text(encoding='utf8'))
        for lang, label in [('zh','数据说明与参考来源'),('en','Data notes and methodology')]:
            build.LANG = lang
            rendered = build.research_article(r)
            self.assertEqual(rendered.count('<figure class="insight-figure">'), 2)
            self.assertIn('<details class="report-notes"><summary>'+label, rendered)
            self.assertIn('alt="', rendered)
            self.assertNotIn('![', rendered)
            self.assertIn(f'/assets/insights/margin-debt-cycles-{lang}.svg?v=', rendered)

    def test_figures_cannot_escape_the_public_asset_directory(self):
        with self.assertRaises(AssertionError):
            build.markdown('![caption](assets/insights/../../site.svg)')
        rendered = build.markdown('![caption](https://example.com/chart.svg)')
        self.assertNotIn('<img', rendered)


if __name__ == '__main__':
    unittest.main()
