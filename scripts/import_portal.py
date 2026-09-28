"""Read-only import of explicitly selected public fields from local portal archives."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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

    reports = [
        ('residual-inertia-monthly-2026-08-15T03-06-59-344Z.md', '2026-08-15-market-review', '2026-08-15', '2026-08-14', '市场月报 · 2026 年 8 月', '月报'),
        ('residual-inertia-weekly-2026-08-12T05-20-09-343Z.md', '2026-08-12-market-review', '2026-08-12', '2026-08-11', '市场周报 · 2026 年 8 月 12 日', '周报'),
    ]
    for filename, slug, date, asof, title, category in reports:
        target = ROOT / 'content/research' / (slug + '.json')
        if target.exists():
            continue
        path = args.portal / 'reports' / filename
        if not path.exists():
            continue
        raw = path.read_text(encoding='utf-8-sig')
        # Keep research findings and their caveats, remove local task/error logs.
        body = raw.split('## 每日决策简报', 1)[1].split('最近任务：', 1)[0]
        body = '## 每日决策简报' + body
        item = dict(slug=slug, title=title, published=date, dataThrough=asof, category=category,
                    summary='市场状态、策略收益归因与组合情景分析，保留原始报告的数据时点和方法说明。',
                    source=filename, sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    note='整理自当时生成的门户报告；保留历史模型与策略口径，移除本机任务日志。不是当前市场判断。',
                    markdown=body.strip())
        encoded = json.dumps(item, ensure_ascii=False, indent=2) + '\n'
        assert not re.search(r'(?i)localhost|127\.0\.0\.1|\b[A-Z]:[\\/]|api[_-]?key|password', encoded)
        target.write_text(encoded, encoding='utf-8')
    print(f'Imported {len(pending)} daily archives; original portal files unchanged.')


if __name__ == '__main__':
    main()
