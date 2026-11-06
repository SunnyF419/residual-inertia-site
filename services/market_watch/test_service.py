import io
import json
from pathlib import Path
TEST_ROOT=Path(__file__).resolve().parents[2]/".runtime"/"market-watch-tests"
TEST_ROOT.mkdir(parents=True,exist_ok=True)
import tempfile
import unittest
import zipfile
from datetime import date
from service import buyer_mix, Store, parse_ftd, parse_ownership


class MarketWatchTests(unittest.TestCase):
    def test_forms_and_footnotes(self):
        for form in ('3', '4', '5', '4/A'):
            xml = f'''<ownershipDocument><documentType>{form}</documentType>
            <issuer><issuerName>Example &amp; Co</issuerName><issuerTradingSymbol>EX</issuerTradingSymbol></issuer>
            <reportingOwner><reportingOwnerId><rptOwnerName>Person</rptOwnerName></reportingOwnerId>
            <reportingOwnerRelationship><isDirector>1</isDirector></reportingOwnerRelationship></reportingOwner>
            <derivativeTable><derivativeTransaction><securityTitle><value>Option</value></securityTitle>
            <transactionCoding><transactionCode>M</transactionCode></transactionCoding>
            <transactionAmounts><transactionShares><value>100</value></transactionShares>
            <transactionPricePerShare><footnoteId id="F1"/></transactionPricePerShare></transactionAmounts>
            </derivativeTransaction></derivativeTable><footnotes><footnote id="F1">See terms.</footnote></footnotes>
            </ownershipDocument>'''
            p = parse_ownership(xml.encode())
            self.assertEqual(p['form'], form)
            self.assertEqual(p['issuer'], 'Example & Co')
            self.assertTrue(p['owners'][0]['director'])
            self.assertTrue(p['transactions'][0]['derivative'])
            self.assertIsNone(p['transactions'][0]['price'])
            self.assertIsNone(p['transactions'][0]['value'])
            self.assertEqual(p['transactions'][0]['footnotes'], ['F1'])

    def test_buyer_mix_attributes_only_eligible_purchases(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            store = Store(directory)
            with store.connect() as db:
                def add(key, names, value, **overrides):
                    trade = dict(transaction=True, derivative=False, code='P', acquired_disposed='A',
                                 date='2026-10-29', value=value)
                    trade.update(overrides)
                    filing = dict(issuer_cik='123', form='4', period='2026-10-29',
                                  owners=[dict(cik=name, name=name) for name in names], transactions=[trade])
                    db.execute('INSERT INTO filings(accession,filed,form,name,source,payload) VALUES(?,?,?,?,?,?)',
                               (key, '2026-10-30', '4', '', '', json.dumps(filing)))
                add('a', ['Buyer A'], 200)
                add('b', ['Buyer A'], 100)
                add('c', ['Buyer B'], 100)
                add('d', ['Buyer A', 'Buyer B'], 600)
                add('e', ['Buyer A'], 1000, derivative=True)
                add('f', ['Buyer A'], None)
                add('g', ['Buyer B'], 500, date='2026-09-15')
                result = buyer_mix(db, '123', date(2026, 10, 30))
                self.assertEqual([b['amount'] for b in result['buyers']], [300, 100])

    def test_ftd_balances_are_not_summed(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            z.writestr('batch.txt', 'SETTLEMENT DATE|CUSIP|SYMBOL|QUANTITY (FAILS)|DESCRIPTION|PRICE\n20261001|123|EX|100|Example|10\n20261002|123|EX|20|Example|.\n')
        rows = list(parse_ftd(data.getvalue()))
        self.assertEqual([r[4] for r in rows], [100, 20])
        self.assertIsNone(rows[-1][5])
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            store = Store(directory)
            with store.connect() as db:
                db.executemany('INSERT INTO ftd VALUES(?,?,?,?,?,?,?)', [(*r, 'batch') for r in rows])
            result = store.listings('ftd')
            self.assertEqual(result['rows'][0]['quantity'], 20)
            self.assertEqual(len(store.detail('ftd', '123')['history']), 2)

    def test_filing_deduplication_and_window(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as directory:
            store = Store(directory)
            for _ in range(2):
                store.add('0000000001-26-000001', date.today().strftime('%Y%m%d'), '4', 'Example', 'https://www.sec.gov/')
            store.add('0000000001-20-000001', '2020-01-01', '4', 'Old', 'https://www.sec.gov/')
            self.assertEqual(store.status()['filings'], 1)
            self.assertEqual(store.status()['pending'], 1)


if __name__ == '__main__':
    unittest.main()
