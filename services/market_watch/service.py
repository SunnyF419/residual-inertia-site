"""RI SEC Market Watch: isolated, read-only API and incremental SEC collector.

Only public SEC records are stored. SQLite and all runtime files stay in --data.
The HTTP server never triggers collection. A single collector limits SEC requests.
"""
import argparse
import csv
import io
import json
import logging
import os
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit
from zoneinfo import ZoneInfo

SEC = 'https://www.sec.gov'
FTD_URL = SEC + '/data-research/sec-markets-data/fails-deliver-data'
FEED = SEC + '/cgi-bin/browse-edgar?action=getcurrent&owner=only&count=100&output=atom'
FORMS = {'3', '4', '5', '3/A', '4/A', '5/A'}
NS = {'a': 'http://www.w3.org/2005/Atom'}
LOG = logging.getLogger('market-watch')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sec_today():
    return datetime.now(ZoneInfo('America/New_York')).date()


def number(value):
    try:
        n = Decimal(value)
        return float(n) if n.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def parse_ownership(raw):
    """Parse SEC ownership XML, including multiple owners and derivative tables."""
    text = raw.decode('utf-8', errors='replace')
    match = re.search(r'<ownershipDocument[\s>].*?</ownershipDocument>', text, re.S | re.I)
    if not match:
        raise ValueError('Ownership XML absent')
    root = ET.fromstring(match.group())
    for node in root.iter():
        node.tag = node.tag.rsplit('}', 1)[-1]
    def val(node, path):
        return (node.findtext(path) or '').strip()
    owners = []
    for owner in root.findall('reportingOwner'):
        rel = owner.find('reportingOwnerRelationship')
        owners.append({'name': val(owner, 'reportingOwnerId/rptOwnerName'),
                       'cik': val(owner, 'reportingOwnerId/rptOwnerCik'),
                       'officer_title': val(rel, 'officerTitle') if rel is not None else '',
                       'director': val(rel, 'isDirector') in ('1', 'true') if rel is not None else False,
                       'officer': val(rel, 'isOfficer') in ('1', 'true') if rel is not None else False,
                       'ten_percent': val(rel, 'isTenPercentOwner') in ('1', 'true') if rel is not None else False})
    rows = []
    for table, derivative in [('nonDerivativeTable', False), ('derivativeTable', True)]:
        node = root.find(table)
        if node is None:
            continue
        for item in node:
            transaction = item.tag.endswith('Transaction')
            shares = number(val(item, 'transactionAmounts/transactionShares/value'))
            price = number(val(item, 'transactionAmounts/transactionPricePerShare/value'))
            rows.append({'security': val(item, 'securityTitle/value'), 'derivative': derivative,
                         'transaction': transaction, 'date': val(item, 'transactionDate/value'),
                         'code': val(item, 'transactionCoding/transactionCode'),
                         'acquired_disposed': val(item, 'transactionAmounts/transactionAcquiredDisposedCode/value'),
                         'shares': shares, 'price': price,
                         'value': shares * price if shares is not None and price is not None else None,
                         'held_after': number(val(item, 'postTransactionAmounts/sharesOwnedFollowingTransaction/value')),
                         'ownership': val(item, 'ownershipNature/directOrIndirectOwnership/value'),
                         'nature': val(item, 'ownershipNature/natureOfOwnership/value'),
                         'footnotes': [x.get('id') for x in item.iter('footnoteId')]})
    return {'issuer': val(root, 'issuer/issuerName'), 'ticker': val(root, 'issuer/issuerTradingSymbol'),
            'issuer_cik': val(root, 'issuer/issuerCik'), 'form': val(root, 'documentType'),
            'period': val(root, 'periodOfReport'), 'owners': owners, 'transactions': rows,
            'plan_10b5_1': val(root, 'aff10b5One'),
            'remarks': val(root, 'remarks'),
            'footnotes': {x.get('id', ''): ''.join(x.itertext()) for x in root.findall('footnotes/footnote')}}


def buyer_mix(db, issuer_cik, today):
    """Attribute priced purchases to identified single filers within the transaction window."""
    start = (today - timedelta(days=29)).isoformat()
    end = today.isoformat()
    totals = {}
    if issuer_cik:
        records = db.execute("""
            SELECT payload FROM filings
            WHERE json_extract(payload, '$.issuer_cik')=? AND filed BETWEEN ? AND ?
            ORDER BY filed DESC, accession DESC
        """, (issuer_cik, start, end))
        filings = [json.loads(row[0]) for row in records]
        # An amendment may replace only part of the original report. Omit the
        # affected owner/period until reconciliation, instead of double counting.
        corrected = {(owner['cik'], filing['period']) for filing in filings
                     if filing['form'].endswith('/A') for owner in filing['owners']}
        for filing in filings:
            if filing['form'] not in ('4', '5') or len(filing['owners']) != 1:
                continue
            owner = filing['owners'][0]
            if not owner['cik'] or (owner['cik'], filing['period']) in corrected:
                continue
            for trade in filing['transactions']:
                if not (trade['transaction'] and not trade['derivative'] and trade['code'] == 'P'
                        and trade['acquired_disposed'] == 'A' and start <= trade['date'] <= end
                        and trade['value'] is not None and trade['value'] > 0):
                    continue
                buyer = totals.setdefault(owner['cik'], {'name': owner['name'], 'amount': 0})
                buyer['amount'] += trade['value']
    buyers = sorted(totals.values(), key=lambda item: (-item['amount'], item['name']))
    return {'start': start, 'end': end, 'buyers': buyers}


def parse_ftd(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = [x for x in archive.infolist() if x.filename.lower().endswith('.txt')]
        if not entries or sum(x.file_size for x in entries) > 100_000_000:
            raise ValueError('Invalid FTD archive')
        for entry in entries:
            with archive.open(entry) as stream:
                for row in csv.DictReader(io.TextIOWrapper(stream, encoding='utf-8-sig', errors='replace'), delimiter='|'):
                    dt = row.get('SETTLEMENT DATE', '').strip()
                    if not re.fullmatch(r'\d{8}', dt):
                        continue
                    quantity = number(row.get('QUANTITY (FAILS)'))
                    if quantity is None or quantity < 0:
                        raise ValueError('Invalid FTD quantity')
                    yield (f'{dt[:4]}-{dt[4:6]}-{dt[6:]}', row['CUSIP'].strip(), row['SYMBOL'].strip(),
                           row['DESCRIPTION'].strip(), int(quantity), number(row.get('PRICE')))


class Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


class Store:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'market-watch.sqlite3'
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS filings(accession TEXT PRIMARY KEY, filed TEXT NOT NULL,
              form TEXT NOT NULL, name TEXT NOT NULL, source TEXT NOT NULL, payload TEXT,
              attempts INTEGER NOT NULL DEFAULT 0, error TEXT, updated TEXT);
            CREATE INDEX IF NOT EXISTS filing_issuer ON filings(json_extract(payload, '$.issuer_cik'), filed);
            CREATE INDEX IF NOT EXISTS filing_date ON filings(filed DESC);
            CREATE TABLE IF NOT EXISTS ftd(day TEXT, cusip TEXT, ticker TEXT, name TEXT,
              quantity INTEGER, price REAL, batch TEXT, PRIMARY KEY(day,cusip));
            CREATE INDEX IF NOT EXISTS ftd_ticker ON ftd(ticker,day);
            CREATE TABLE IF NOT EXISTS batches(url TEXT PRIMARY KEY, loaded TEXT, first_day TEXT, last_day TEXT);
            ''')
            db.execute("UPDATE filings SET filed=substr(filed,1,4)||'-'||substr(filed,5,2)||'-'||substr(filed,7,2) WHERE length(filed)=8 AND filed NOT LIKE '%-%'")

    def connect(self):
        db = sqlite3.connect(self.path, timeout=20, factory=Connection)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA busy_timeout=20000')
        return db

    def set(self, key, value):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO meta VALUES(?,?)', (key, json.dumps(value)))

    def get(self, key, fallback=None):
        with self.connect() as db:
            row = db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else fallback

    def add(self, accession, filed, form, name, source):
        if re.fullmatch(r'\d{8}', filed):
            filed = datetime.strptime(filed, '%Y%m%d').date().isoformat()
        if form not in FORMS or not re.fullmatch(r'\d{10}-\d{2}-\d{6}', accession):
            return
        if filed[:10] < (sec_today() - timedelta(days=29)).isoformat():
            return
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO filings(accession,filed,form,name,source) VALUES(?,?,?,?,?)',
                       (accession, filed[:10], form, name, source))

    def status(self):
        with self.connect() as db:
            count, parsed = db.execute('SELECT COUNT(*),COUNT(payload) FROM filings').fetchone()
            dates = db.execute('SELECT MIN(day),MAX(day) FROM ftd').fetchone()
            batches = [dict(x) for x in db.execute('SELECT * FROM batches ORDER BY last_day DESC')]
        return {'checked': self.get('feed_checked'), 'feed_error': self.get('feed_error'),
                'index_checked': self.get('index_checked'), 'index_error': self.get('index_error'),
                'ftd_checked': self.get('ftd_checked'), 'ftd_error': self.get('ftd_error'),
                'filings': count, 'parsed': parsed, 'pending': count - parsed,
                'window_start': (sec_today() - timedelta(days=29)).isoformat(),
                'ftd_start': dates[0], 'ftd_end': dates[1], 'batches': batches,
                'poll_seconds': 60, 'ftd_poll_seconds': 21600}

    def listings(self, kind, query='', category='all', page=1):
        page = max(1, min(page, 10000)); limit = 50
        query = query.strip().upper()[:100]
        with self.connect() as db:
            if kind == 'insider':
                clauses = ['1=1']; args = []
                if query:
                    clauses.append('(instr(upper(name),?)>0 OR instr(upper(payload),?)>0)'); args += [query, query]
                if category in FORMS:
                    clauses.append('form=?'); args.append(category)
                where = ' AND '.join(clauses)
                total = db.execute('SELECT COUNT(*) FROM filings WHERE ' + where, args).fetchone()[0]
                data = db.execute('SELECT * FROM filings WHERE ' + where + ' ORDER BY filed DESC,accession DESC LIMIT ? OFFSET ?', args + [limit, (page-1)*limit]).fetchall()
                rows = []
                for row in data:
                    p = json.loads(row['payload']) if row['payload'] else {}
                    codes = sorted({t['code'] for t in p.get('transactions', []) if t['code']})
                    rows.append({'accession': row['accession'], 'filed': row['filed'], 'form': row['form'],
                                 'issuer': p.get('issuer', row['name']), 'ticker': p.get('ticker', ''),
                                 'owners': p.get('owners', []), 'codes': codes,
                                 'parsed': bool(p), 'source': row['source']})
            else:
                latest = db.execute('SELECT MAX(day) FROM ftd').fetchone()[0]
                args = [latest]
                where = 'day=?'
                if query:
                    where += ' AND (instr(upper(ticker),?)>0 OR instr(upper(name),?)>0 OR instr(cusip,?)>0)'
                    args += [query, query, query]
                total = db.execute('SELECT COUNT(*) FROM ftd WHERE ' + where, args).fetchone()[0]
                rows = [dict(x) for x in db.execute('SELECT * FROM ftd WHERE ' + where + ' ORDER BY quantity DESC,cusip LIMIT ? OFFSET ?', args + [limit, (page-1)*limit])]
        return {'rows': rows, 'total': total, 'page': page, 'page_size': limit, 'status': self.status()}

    def detail(self, kind, key):
        with self.connect() as db:
            if kind == 'insider':
                row = db.execute('SELECT * FROM filings WHERE accession=?', (key,)).fetchone()
                if not row:
                    return None
                payload = json.loads(row['payload']) if row['payload'] else None
                return {'buyer_mix': buyer_mix(db, payload['issuer_cik'], sec_today()) if payload else None,
                        'accession': key, 'filed': row['filed'], 'source': row['source'],
                        'payload': payload}
            rows = [dict(x) for x in db.execute('SELECT * FROM ftd WHERE cusip=? ORDER BY day', (key,))]
            return {'cusip': key, 'history': rows} if rows else None


class Collector:
    def __init__(self, store, user_agent):
        self.store = store; self.user_agent = user_agent; self.last_request = 0
        self.blocked_until = store.get('sec_blocked_until', 0)

    def fetch(self, url):
        if time.time() < self.blocked_until:
            raise RuntimeError('SEC access paused after a rate-limit or access rejection')
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.hostname != 'www.sec.gov':
            raise ValueError('Only SEC HTTPS sources allowed')
        time.sleep(max(0, .35 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        request = urllib.request.Request(url, headers={'User-Agent': self.user_agent, 'Accept-Encoding': 'identity'})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read(60_000_001)
                if len(body) > 60_000_000:
                    raise ValueError('SEC response too large')
                return body
        except urllib.error.HTTPError as error:
            if error.code in (403, 429):
                self.blocked_until = time.time() + 900
                self.store.set('sec_blocked_until', self.blocked_until)
            raise

    def feed(self):
        # Paginate so bursts above 100 filings are not silently missed.
        for start in range(0, 1000, 100):
            root = ET.fromstring(self.fetch(FEED + f'&start={start}'))
            entries = root.findall('a:entry', NS)
            known = 0
            for entry in entries:
                title = entry.findtext('a:title', '', NS)
                form = title.split(' - ', 1)[0].strip()
                link = entry.find('a:link', NS)
                href = link.get('href', '') if link is not None else ''
                match = re.search(r'(\d{10}-\d{2}-\d{6})', href)
                if not match or form not in FORMS:
                    continue
                accession = match.group(1)
                with self.store.connect() as db:
                    known += bool(db.execute('SELECT 1 FROM filings WHERE accession=?', (accession,)).fetchone())
                source = urljoin(SEC, href)
                self.store.add(accession, entry.findtext('a:updated', '', NS), form, title, source)
            if len(entries) < 100 or known >= 90:
                break
        self.store.set('feed_checked', now()); self.store.set('feed_error', None)

    def indices(self):
        """Daily indices recover filing bursts, outages, and the last 30 days."""
        complete = set(self.store.get('index_days', []))
        today = sec_today()
        for offset in range(1, 30):
            day = today - timedelta(days=offset)
            if day.weekday() > 4 or day.isoformat() in complete:
                continue
            url = f'{SEC}/Archives/edgar/daily-index/{day.year}/QTR{(day.month-1)//3+1}/master.{day:%Y%m%d}.idx'
            try:
                text = self.fetch(url).decode('latin-1')
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    continue  # Holiday or not yet published; check again next cycle.
                raise
            if 'CIK|Company Name|Form Type|Date Filed|File Name' not in text:
                raise ValueError('Invalid SEC daily index')
            for line in text.splitlines():
                fields = line.split('|')
                if len(fields) != 5 or fields[2] not in FORMS:
                    continue
                match = re.search(r'(\d{10}-\d{2}-\d{6})', fields[4])
                if match:
                    self.store.add(match.group(1), fields[3], fields[2], fields[1], SEC + '/Archives/' + fields[4])
            complete.add(day.isoformat())
            self.store.set('index_days', sorted(d for d in complete if d >= (today-timedelta(days=29)).isoformat()))
        self.store.set('index_checked', now()); self.store.set('index_error', None)

    def process(self, limit=100):
        if time.time() < self.blocked_until:
            return
        with self.store.connect() as db:
            rows = db.execute('SELECT * FROM filings WHERE payload IS NULL AND attempts<5 ORDER BY filed DESC,accession DESC LIMIT ?', (limit,)).fetchall()
        for row in rows:
            try:
                source = row['source']
                if source.endswith('-index.htm') or source.endswith('-index.html'):
                    source = re.sub(r'-index\.html?$', '.txt', source)
                payload = parse_ownership(self.fetch(source))
                with self.store.connect() as db:
                    db.execute('UPDATE filings SET payload=?,error=NULL,updated=? WHERE accession=?', (json.dumps(payload), now(), row['accession']))
            except Exception as error:
                with self.store.connect() as db:
                    db.execute('UPDATE filings SET attempts=attempts+1,error=?,updated=? WHERE accession=?', (str(error)[:200], now(), row['accession']))
                if isinstance(error, urllib.error.HTTPError) and error.code in (403, 429):
                    raise  # Back off globally, never bypass SEC restrictions.
                LOG.warning('Filing %s: %s', row['accession'], error)

    def ftd(self):
        html = self.fetch(FTD_URL).decode('utf-8')
        links = sorted(set(re.findall(r'href=["\']([^"\']*cnsfails\d{6}[ab]\.zip)["\']', html)),
                       key=lambda x: re.search(r'cnsfails(\d{6}[ab])', x).group(1), reverse=True)[:2]
        if len(links) < 2:
            raise ValueError('SEC FTD batch links unavailable')
        for link in links:
            url = urljoin(SEC, link)
            with self.store.connect() as db:
                exists = db.execute('SELECT 1 FROM batches WHERE url=?', (url,)).fetchone()
            if exists:
                continue
            rows = list(parse_ftd(self.fetch(url)))
            if not rows:
                raise ValueError('Empty SEC FTD batch')
            dates = [r[0] for r in rows]
            with self.store.connect() as db:
                db.executemany('INSERT OR REPLACE INTO ftd VALUES(?,?,?,?,?,?,?)', [(*r, url) for r in rows])
                db.execute('INSERT OR REPLACE INTO batches VALUES(?,?,?,?)', (url, now(), min(dates), max(dates)))
        # Only prune after both latest batches have been successfully imported.
        urls = [urljoin(SEC, x) for x in links]
        with self.store.connect() as db:
            db.execute('DELETE FROM ftd WHERE batch NOT IN (?,?)', urls)
            db.execute('DELETE FROM batches WHERE url NOT IN (?,?)', urls)
        self.store.set('ftd_checked', now()); self.store.set('ftd_error', None)

    def run(self):
        due = {'feed': 0, 'indices': 0, 'ftd': 0}
        periods = {'feed': 60, 'indices': 21600, 'ftd': 21600}
        while True:
            if time.time() < self.blocked_until:
                time.sleep(min(30, self.blocked_until - time.time()))
                continue
            # Fill recent filing details before historical backfill can trigger a pause.
            try:
                self.process(30)
            except Exception:
                LOG.exception('SEC detail collection paused')
                continue
            for task in due:
                if time.time() < self.blocked_until:
                    break
                if time.time() < due[task]:
                    continue
                try:
                    getattr(self, task)()
                except Exception as error:
                    LOG.exception('SEC %s update failed', task)
                    self.store.set({'indices': 'index_error'}.get(task, task+'_error'), str(error)[:200])
                    due[task] = time.time() + (21600 if task == 'indices' else 900)
                else:
                    due[task] = time.time() + periods[task]
            with self.store.connect() as db:
                db.execute('DELETE FROM filings WHERE filed<?', ((sec_today()-timedelta(days=29)).isoformat(),))
                # Retry transient failures after an hour without hammering a bad filing.
                db.execute('UPDATE filings SET attempts=0 WHERE payload IS NULL AND updated<?', ((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),))
            time.sleep(2)


def handler(store, static_root=None):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlsplit(self.path); params = parse_qs(parsed.query)
            path = parsed.path.removeprefix('/api/market-watch')
            def arg(key, default=''):
                return params.get(key, [default])[0]
            try:
                if path == '/status':
                    result = store.status()
                elif path in ('/insider', '/ftd'):
                    result = store.listings(path[1:], arg('q'), arg('form', 'all'), int(arg('page', '1')))
                elif path in ('/insider/detail', '/ftd/detail'):
                    result = store.detail(path.split('/')[1], arg('id'))
                    if result is None:
                        return self.reply({'error': 'Record not found'}, 404)
                elif static_root:
                    target = (Path(static_root) / parsed.path.lstrip('/')).resolve()
                    if not target.is_relative_to(Path(static_root).resolve()):
                        return self.reply({'error': 'Not found'}, 404)
                    if target.is_dir(): target = target/'index.html'
                    if not target.is_file(): return self.reply({'error': 'Not found'}, 404)
                    import mimetypes
                    raw = target.read_bytes()
                    if target.suffix == '.html':
                        raw = raw.replace(b'data-market-watch>', b'data-market-watch data-api="/api/market-watch">')
                    self.send_response(200)
                    self.send_header('Content-Type', mimetypes.guess_type(str(target))[0] or 'application/octet-stream')
                    self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw); return
                else:
                    return self.reply({'error': 'Not found'}, 404)
                self.reply(result)
            except (ValueError, OverflowError):
                self.reply({'error': 'Invalid request'}, 400)
            except Exception:
                LOG.exception('API error'); self.reply({'error': 'Data temporarily unavailable'}, 503)

        def reply(self, result, status=200):
            body = json.dumps(result, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'public, max-age=20' if status==200 else 'no-store')
            self.send_header('Access-Control-Allow-Origin', 'https://residualinertia.com')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(body)
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True); parser.add_argument('--port', type=int, default=8774)
    parser.add_argument('--static'); parser.add_argument('--collect', action='store_true')
    parser.add_argument('--once', action='store_true'); parser.add_argument('--limit', type=int, default=50)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    store = Store(args.data)
    agent = os.environ.get('SEC_USER_AGENT', 'Residual Inertia Research data@residualinertia.com')
    collector = Collector(store, agent)
    if args.once:
        for task in ('ftd', 'feed', 'indices'):
            try: getattr(collector, task)()
            except Exception as error:
                store.set({'indices':'index_error'}.get(task, task+'_error'), str(error)); LOG.exception(task)
        collector.process(args.limit)
        print(json.dumps(store.status(), indent=2)); return
    if args.collect:
        threading.Thread(target=collector.run, daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1', args.port), handler(store, args.static)).serve_forever()


if __name__ == '__main__':
    main()
