import importlib.util
from datetime import date
from pathlib import Path
import unittest
from scripts.market_calendar import regular_closure

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('calendar_importer', ROOT/'scripts/import_portal.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


class ChartCalendarTests(unittest.TestCase):
    def test_regular_closures_and_nyse_new_year_exception(self):
        for value in ['2023-09-30','2023-10-01','2024-03-29','2026-04-03','2026-06-19','2026-07-03','2021-12-24']:
            self.assertTrue(regular_closure(date.fromisoformat(value)),value)
        for value in ['2023-10-02','2021-06-18','2021-12-31','2026-11-27']:
            self.assertFalse(regular_closure(date.fromisoformat(value)),value)

    def test_closure_does_not_create_fake_points_or_break_the_line(self):
        rows=[(date(2024,3,28),40,'中性'),(date(2024,3,29),None,None),(date(2024,3,31),None,None),(date(2024,4,1),41,'中性')]
        points,missing,closures=importer.history_points(rows)
        self.assertEqual([p['score'] for p in points],[40,41])
        self.assertFalse(any(p.get('breakBefore') for p in points))
        self.assertEqual(missing,[])
        self.assertEqual(closures,['2024-03-29','2024-03-31'])

    def test_real_gap_survives_intervening_weekend_and_absent_source_row(self):
        rows=[(date(2026,10,15),40,'中性'),(date(2026,10,16),None,None),(date(2026,10,17),None,None),(date(2026,10,19),42,'中性')]
        points,missing,_=importer.history_points(rows)
        self.assertEqual(missing,['2026-10-16']);self.assertTrue(points[-1]['breakBefore'])
        # A session entirely absent from Regime must still break the series.
        points,missing,_=importer.history_points([rows[0],rows[-1]],[date(2026,10,16)])
        self.assertEqual(missing,['2026-10-16']);self.assertTrue(points[-1]['breakBefore'])

    def test_observed_session_overrides_calendar_classification(self):
        rows=[(date(2026,7,2),40,'中性'),(date(2026,7,3),None,None),(date(2026,7,6),42,'中性')]
        points,missing,closures=importer.history_points(rows,[date(2026,7,3)])
        self.assertEqual(missing,['2026-07-03']);self.assertEqual(closures,[])
        self.assertTrue(points[-1]['breakBefore'])
