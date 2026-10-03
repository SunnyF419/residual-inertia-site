"""Read-only import of explicitly selected public fields from local portal archives."""
import argparse
import hashlib
import json
import re
import math
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def import_regime_history(portal, asof, expected_score=None):
    import duckdb  # Local importer only; GitHub builds from the exported JSON.
    config = json.loads((portal/'portal.config.json').read_text(encoding='utf-8-sig'))
    signals = Path(config['sources']['marketResearch']).resolve()
    project = signals.parent.parent
    dashboard_config = project/'config.yaml'
    if dashboard_config.exists():
        import yaml  # Existing local dashboard dependency; not needed on GitHub Pages.
        settings = yaml.safe_load(dashboard_config.read_text(encoding='utf-8-sig'))
        database = Path(settings['paths']['duckdb_path'])
        if not database.is_absolute():
            database = project/database
    else:
        database = project/'data/dashboard.duckdb'
    if not database.is_file():
        raise FileNotFoundError('Configured market history database is unavailable')
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
    if expected_score is not None:
        assert points[-1]['date'] == end.isoformat() and math.isclose(points[-1]['score'], expected_score, abs_tol=0.01), 'Latest reading and history disagree'
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


def public_json(value):
    encoded = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if re.search(r'(?i)localhost|127\.0\.0\.1|\b[A-Z]:[\\/]|api[_-]?key|password|access_token|BEGIN .*PRIVATE KEY', encoded):
        raise ValueError('Private content found in public export')
    return encoded


def export_current(snapshot):
    """Export a validated market reading independently of full-portal daily archiving."""
    source = next((s for s in snapshot.get('sources', []) if s.get('id') == 'marketResearch'), {})
    if source.get('quality', {}).get('status') not in ('pass', 'warning') or source.get('status') == 'error':
        raise ValueError('Market source did not pass quality checks')
    if any(e.get('source') == 'marketResearch' for e in snapshot.get('errors', [])):
        raise ValueError('Market source is unavailable')
    clean = export_record({'snapshot': snapshot, 'sourceState': []})
    market = clean['market']
    for field in ('signalDate', 'effectiveDate', 'regimeDate', 'breadthDate'):
        date.fromisoformat(market[field][:10])
    if market['effectiveDate'][:10] < market['signalDate'][:10]:
        raise ValueError('Effective date precedes signal')
    for field, maximum in (('regimeScore', 100), ('breadth', 1), ('targetExposure', 1)):
        value = market[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= maximum:
            raise ValueError('Invalid market value: ' + field)
    if not market['riskLevel'] or not market['regimeState']:
        raise ValueError('Market state is missing')
    pillars = market['pillars']
    if len(pillars) < 4 or len({p['name'] for p in pillars}) != len(pillars):
        raise ValueError('Incomplete or duplicate market pillars')
    for p in pillars:
        if not p['name'] or not p['state'] or isinstance(p['score'], bool) or not isinstance(p['score'], (int, float)) or not math.isfinite(p['score']) or not 0 <= p['score'] <= 100:
            raise ValueError('Invalid market pillar')
    captured = datetime.fromisoformat(snapshot['generatedAt'].replace('Z', '+00:00'))
    if captured.tzinfo is None:
        raise ValueError('Missing reading timezone')
    if captured > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError('Reading timestamp is in the future')
    result = dict(kind='current', observationDate=captured.astimezone(timezone(timedelta(hours=8))).date().isoformat(),
                  capturedAt=snapshot['generatedAt'], market=market,
                  brief=dict(asOf=market['regimeDate'][:10], posture=f"综合状态 {market['regimeState']}，得分 {market['regimeScore']:.1f} / 100，市场宽度 {market['breadth']:.0%}。"),
                  sources=[dict(id='marketResearch', name='市场研究', asOf=source['asOf'], status=source['status'], qualityStatus=source['quality']['status'])])
    public_json(result)
    return result


def newer_market(candidate, baseline):
    """Never roll any independently dated market component backwards."""
    return all(candidate['market'][key][:10] >= baseline['market'][key][:10]
               for key in ('regimeDate', 'signalDate', 'breadthDate'))


def current_reading(portal, archived):
    target = ROOT/'content/market/latest.json'
    previous = json.loads(target.read_text(encoding='utf-8')) if target.exists() else archived
    try:
        snapshot = json.loads((portal/'public/portal-data.json').read_text(encoding='utf-8-sig'))
        candidate = export_current(snapshot)
        if not newer_market(candidate, archived) or not newer_market(candidate, previous):
            raise ValueError('Market dates would move backwards')
        if previous.get('kind') == 'current' and candidate['capturedAt'] < previous['capturedAt']:
            raise ValueError('Reading timestamp would move backwards')
        # Other local sources may refresh without changing the public market reading.
        relevant = lambda s: {k: v for k, v in s.items() if k not in ('capturedAt', 'observationDate')}
        if previous.get('kind') == 'current' and relevant(candidate) == relevant(previous):
            candidate = previous
        return candidate
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f'Latest market reading retained: {error}.')
        return previous if newer_market(previous, archived) else archived


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
        encoded = public_json(clean)
        target = ROOT / 'content/snapshots' / path.name
        if target.exists() and target.read_text(encoding='utf-8') != encoded:
            raise SystemExit(f'Archive changed: {path.name}; review the revision before replacing its public copy.')
        pending.append((target, encoded))
    archived = json.loads(pending[-1][1])
    latest = current_reading(args.portal, archived)
    # Validate history before writing public content; preserve the last good publication on failure.
    import_regime_history(args.portal, latest['market']['regimeDate'], latest['market']['regimeScore'] if latest.get('kind') == 'current' else None)
    for target, encoded in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(encoded, encoding='utf-8')

    if latest.get('kind') == 'current':
        target = ROOT/'content/market/latest.json'
        temporary = target.with_suffix('.json.tmp')
        temporary.write_text(public_json(latest), encoding='utf-8')
        temporary.replace(target)
        print(f'Latest valid market reading: {latest["market"]["regimeDate"][:10]}, {latest["market"]["regimeScore"]:.1f}.')

    # Formal market letters are uploaded by the author; portal reports stay local.
    print(f'Imported {len(pending)} daily archives; original portal files unchanged.')


if __name__ == '__main__':
    main()
