"""Publication regressions: current data, failed dependencies and immutable archives."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('import_portal', ROOT/'scripts/import_portal.py')
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def snapshot():
    return dict(generatedAt='2020-10-03T09:00:00Z',
                market=dict(riskLevel='Level 5', riskScore=0.1, targetExposure=0.35,
                            signalDate='2020-10-02', effectiveDate='2020-10-05',
                            regimeDate='2020-10-02', regimeState='防御', regimeScore=66.8,
                            breadth=0.42, breadthDate='2020-10-02',
                            pillars=[dict(name=n, state='中性', score=50) for n in ('Stress', 'Fragility', 'Risk', 'Participation')]),
                sources=[dict(id='marketResearch', asOf='2020-10-02', status='current', quality=dict(status='pass'))],
                errors=[dict(source='riskFactors', detail='An unrelated updater failed')],
                holdings=dict(password='private-value', positions=['PRIVATE-HOLDING']),
                dashboards=dict(marketResearch='http://localhost:8501'),
                dailyBrief=dict(posture='private summary'))


class ImportTests(unittest.TestCase):
    def test_unrelated_failure_does_not_block_valid_market_and_private_fields_are_excluded(self):
        clean = importer.export_current(snapshot())
        self.assertEqual(clean['market']['regimeScore'], 66.8)
        self.assertEqual(clean['brief']['asOf'], '2020-10-02')
        self.assertEqual(set(clean), {'kind', 'observationDate', 'capturedAt', 'market', 'brief', 'sources'})
        encoded = importer.public_json(clean)
        for private in ('private-value', 'PRIVATE-HOLDING', 'localhost', 'private summary', 'riskFactors'):
            self.assertNotIn(private, encoded)

    def test_invalid_or_unavailable_market_is_not_publishable(self):
        for mutate in (lambda s: s['sources'][0]['quality'].update(status='fail'),
                       lambda s: s['sources'][0].update(status='error'),
                       lambda s: s['errors'].append(dict(source='marketResearch')),
                       lambda s: s['market'].update(regimeScore=float('nan')),
                       lambda s: s['market'].update(targetExposure=1.01),
                       lambda s: s['market'].update(breadth=-0.1),
                       lambda s: s['market']['pillars'].pop(),
                       lambda s: s['market'].update(effectiveDate='2020-09-01')):
            s = snapshot()
            mutate(s)
            with self.assertRaises((ValueError, TypeError)):
                importer.export_current(s)

    def test_sync_is_idempotent_and_rejects_older_or_failed_market(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'content/market').mkdir(parents=True)
            (root/'public').mkdir()
            previous = importer.export_current(snapshot())
            (root/'content/market/latest.json').write_text(importer.public_json(previous), encoding='utf-8')
            archived = copy.deepcopy(previous)
            archived['market']['regimeDate'] = '2020-10-01'
            current = snapshot()
            current['generatedAt'] = '2020-10-03T10:00:00Z'
            with patch.object(importer, 'ROOT', root):
                for change in ('same', 'older', 'failed', 'new'):
                    s = copy.deepcopy(current)
                    if change == 'older': s['market']['breadthDate'] = '2020-09-30'
                    if change == 'failed': s['sources'][0]['quality']['status'] = 'fail'
                    if change == 'new': s['market']['regimeScore'] = 67
                    (root/'public/portal-data.json').write_text(json.dumps(s), encoding='utf-8')
                    clean = importer.current_reading(root, archived)
                    if change == 'new':
                        self.assertEqual(clean['market']['regimeScore'], 67)
                        self.assertEqual(clean['capturedAt'], s['generatedAt'])
                    else:
                        self.assertEqual(clean, previous)

    def test_modified_archive_aborts_before_any_public_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            daily = root/'portal/.runtime/lineage/daily'
            daily.mkdir(parents=True)
            record = dict(observationDate='2020-10-03', capturedAt='2020-10-03T09:00:00Z', snapshot=snapshot())
            (daily/'2020-10-03.json').write_text(json.dumps(record), encoding='utf-8')
            public = root/'content/snapshots'
            public.mkdir(parents=True)
            (public/'2020-10-03.json').write_text('original reviewed archive', encoding='utf-8')
            with patch.object(importer, 'ROOT', root), patch('sys.argv', ['import', '--portal', str(root/'portal')]), patch.object(importer, 'import_regime_history') as history:
                with self.assertRaisesRegex(SystemExit, 'Archive changed'):
                    importer.main()
                history.assert_not_called()
            self.assertEqual((public/'2020-10-03.json').read_text(encoding='utf-8'), 'original reviewed archive')


if __name__ == '__main__':
    unittest.main()
