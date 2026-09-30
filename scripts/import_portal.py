"""Read-only import of explicitly selected public fields from local portal archives."""
import argparse
import hashlib
import json
import re
import math
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def import_regime_history(portal, asof):
    import duckdb  # Local importer only; GitHub builds from the exported JSON.
    config = json.loads((portal/'portal.config.json').read_text(encoding='utf-8-sig'))
    signals = Path(config['sources']['marketResearch'])
    database = signals.parent.parent/'data/dashboard.duckdb'
    end = date.fromisoformat(asof[:10])
    try:
        start = end.replace(year=end.year-5)
    except ValueError:
        start = end.replace(year=end.year-5, day=28)
    with duckdb.connect(str(database), read_only=True) as con:
        rows = con.execute('SELECT date, regime_score, regime_state_zh FROM market_regime_history WHERE date >= ? AND date <= ? ORDER BY date', [start, end]).fetchall()
    points = []
    for day, score, state in rows:
        if score is None:
            continue
        assert math.isfinite(score) and 0 <= score <= 100, 'Invalid historical regime score'
        points.append(dict(date=day.date().isoformat(), score=score, state=state))
    assert points and (date.fromisoformat(points[0]['date'])-start).days <= 7, 'Five-year history incomplete'
    assert (end-date.fromisoformat(points[-1]['date'])).days <= 7, 'Historical regime data is stale'
    assert len({p['date'] for p in points}) == len(points), 'Duplicate history dates'
    output = dict(windowStart=start.isoformat(), windowEnd=end.isoformat(), source='市场研究 Dashboard · market_regime_history', points=points)
    target = ROOT/'content/market/regime-history.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'Imported {len(points)} regime history points: {start} to {end}.')


def select(obj, keys):
    return {k: obj.get(k) for k in keys}


def export_record(record):
    s = record['snapshot']
    result = select(record, ['observationDate', 'capturedAt', 'snapshotId', 'contentHash'])
    result['market'] = select(s.get('market', {}), ['riskLevel', 'riskScore', 'targetExposure', 'signalDate', 'effectiveDate', 'regimeState', 'regimeScore', 'regimeDate', 'breadth', 'breadthDate'])
    result['market']['pillars'] = [select(p, ['name', 'state', 'score']) for p in s.get('market', {}).get('pillars', [])]
    result['brief'] = select(s.get('dailyBrief', {}), ['asOf', 'headline', 'posture', 'dataStatus'])
    result['sources'] = [select(p, ['id', 'name', 'asOf', 'status', 'qualityStatus']) for p in record.get('sourceState', [])]
    result['alerts'] = [select(a, ['severity', 'title', 'detail']) for a in s.get('monitoring', {}).get('alerts', []) if a.get('category') == '风险']
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--portal', type=Path, required=True)
    args = parser.parse_args()
    source = args.portal / '.runtime/lineage/daily'
    files = sorted(source.glob('????-??-??.json'))
    if not files:
        raise SystemExit('No daily archives found; nothing changed.')
    pending = []
    for path in files:
        record = json.loads(path.read_text(encoding='utf-8-sig'))
        assert record['observationDate'] == path.stem, path.name
        clean = export_record(record)
        encoded = json.dumps(clean, ensure_ascii=False, indent=2) + '\n'
        # No operational URLs, local paths or credential-like fields in public content.
        assert not re.search(r'(?i)localhost|127\.0\.0\.1|\b[A-Z]:[\\/]|api[_-]?key|password|access_token', encoded), path.name
        target = ROOT / 'content/snapshots' / path.name
        if target.exists() and target.read_text(encoding='utf-8') != encoded:
            raise SystemExit(f'Archive changed: {path.name}; review the revision before replacing its public copy.')
        pending.append((target, encoded))
    for target, encoded in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(encoded, encoding='utf-8')

    latest = json.loads(pending[-1][1])
    import_regime_history(args.portal, latest['market']['regimeDate'])

    # Formal market letters are uploaded by the author; portal reports stay local.
    print(f'Imported {len(pending)} daily archives; original portal files unchanged.')


if __name__ == '__main__':
    main()
