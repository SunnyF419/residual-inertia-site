import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.dashboard_public import dashboard_paths, history_table, effective_row, ESTIMATE_VERSION
from scripts.market_modules import render_modules

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('refresh_importer', ROOT/'scripts/import_portal.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class RefreshTests(unittest.TestCase):
    def test_unknown_model_is_not_silently_published_as_legacy(self):
        self.assertEqual(history_table(ESTIMATE_VERSION), 'market_regime_estimate_history')
        with self.assertRaises(ValueError):
            history_table('unreviewed-version')

    def test_all_modules_are_localized_and_future_wqs_is_not_displayed(self):
        market = json.loads((ROOT/'content/market/latest.json').read_text(encoding='utf-8'))['market']
        for lang in ['zh','en']:
            page = render_modules(market,lang)
            for key in ['weekly','breadth','nfci','livermore','wqs','crowding','hml','umd','ai','liquidity']:
                self.assertIn('id="module-'+key+'"',page)
            self.assertLessEqual(market['modules']['wqs']['date'], market['breadthDate'][:10])
            self.assertNotIn('source_file',page)
        self.assertNotIn('供应链',render_modules(market,'en'))

    def test_history_model_matches_current_and_missing_dates_are_not_filled(self):
        market = json.loads((ROOT/'content/market/latest.json').read_text(encoding='utf-8'))['market']
        history = json.loads((ROOT/'content/market/regime-history.json').read_text(encoding='utf-8'))
        self.assertEqual(history['modelVersion'],market['modelVersion'])
        self.assertAlmostEqual(history['points'][-1]['score'],market['regimeScore'],places=4)
        missing = set(history['missingDates'])
        self.assertFalse(missing & {p['date'] for p in history['points']})
        self.assertTrue(all('data-chart-series d=' in (ROOT/f'dist/{prefix}overview/index.html').read_text(encoding='utf-8') for prefix in ['', 'en/']))


@unittest.skipUnless(importlib.util.find_spec('duckdb') and importlib.util.find_spec('yaml'), 'Local importer dependencies')
class ReadOnlyDatabaseTests(unittest.TestCase):
    def test_migrated_configuration_selects_matching_history_and_preserves_gaps(self):
        import duckdb
        import yaml
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); project=root/'dashboard'; portal=root/'portal'
            (project/'config').mkdir(parents=True); (project/'reports').mkdir(); portal.mkdir()
            newdb=project/'current.duckdb'; olddb=project/'obsolete.duckdb'; olddb.touch()
            (portal/'portal.config.json').write_text(json.dumps({'sources':{'marketResearch':str(project/'reports/latest_signals.json')}}))
            (project/'config.yaml').write_text(yaml.safe_dump({'paths':{'duckdb_path':str(olddb)}}))
            (project/'config/paths.yaml').write_text(yaml.safe_dump({'duckdb_path':str(newdb)}))
            with duckdb.connect(str(newdb)) as con:
                con.execute('CREATE TABLE market_regime_estimate_history (date DATE, regime_score DOUBLE, regime_state_zh VARCHAR)')
                con.execute("INSERT INTO market_regime_estimate_history VALUES ('2021-10-21',50,'谨慎'),('2026-10-19',NULL,NULL),('2026-10-21',65.7,'防御')")
                con.execute('CREATE TABLE market_regime_history AS SELECT date, 1.0 AS regime_score, regime_state_zh FROM market_regime_estimate_history')
                con.execute('CREATE TABLE wqs_signals (date DATE,effective_date DATE,wqs DOUBLE)')
                con.execute("INSERT INTO wqs_signals VALUES ('2026-09-30','2026-10-01',0.024),('2026-10-31','2026-11-01',0.001)")
            before=newdb.read_bytes()
            self.assertEqual(dashboard_paths(portal)[2],newdb)
            with patch.object(importer,'ROOT',root):
                importer.import_regime_history(portal,'2026-10-21',65.7,ESTIMATE_VERSION)
            history=json.loads((root/'content/market/regime-history.json').read_text(encoding='utf-8'))
            self.assertEqual(history['missingDates'],['2026-10-19'])
            self.assertTrue(history['points'][-1]['breakBefore'])
            with duckdb.connect(str(newdb),read_only=True) as con:
                current=effective_row(con,'wqs_signals','date, effective_date, wqs','2026-10-23',effective=True)
                self.assertEqual(current['date'],'2026-09-30')
                self.assertEqual(current['wqs'],0.024)
            self.assertEqual(before,newdb.read_bytes())
            with patch.object(importer,'ROOT',root), self.assertRaises(AssertionError):
                importer.import_regime_history(portal,'2026-10-21',42,ESTIMATE_VERSION)
            self.assertEqual(history,json.loads((root/'content/market/regime-history.json').read_text(encoding='utf-8')))

if __name__ == '__main__':
    unittest.main()
