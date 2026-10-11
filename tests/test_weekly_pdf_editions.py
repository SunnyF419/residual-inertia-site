"""Published bilingual pages must select the correct complete PDF edition."""
import hashlib
import json
import unittest
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit
from test_seo import ROOT, Head

class PDFLinks(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.pdfs=[]; self.images=[]; self.feed(html)
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=='a' and '.pdf' in a.get('href',''):
            self.pdfs.append(a['href'])
        if tag=='img': self.images.append(a.get('src',''))

class WeeklyPDFEditionTests(unittest.TestCase):
    def test_every_weekly_selects_locale_pdf_with_matching_hash(self):
        records=[json.loads(p.read_text(encoding='utf8')) for p in (ROOT/'content/research').glob('market-letter-*.json')]
        records=[r for r in records if r.get('pdf_en')]
        self.assertGreaterEqual(len(records),6)
        for r in records:
            for prefix, suffix, language in [('', '', 'zh-CN'),('en/', '_en', 'en')]:
                with self.subTest(slug=r['slug'],language=language):
                    html=(ROOT/'dist'/prefix/'research'/r['slug']/'index.html').read_text(encoding='utf8')
                    urls=PDFLinks(html).pdfs
                    self.assertEqual(len(urls),1)
                    url=urlsplit(urls[0])
                    self.assertEqual(url.path,'/'+r['pdf'+suffix])
                    data=(ROOT/r['pdf'+suffix]).read_bytes()
                    digest=hashlib.sha256(data).hexdigest()
                    self.assertEqual(digest,r['pdfSha256'+suffix])
                    self.assertEqual(parse_qs(url.query)['v'],[digest[:12]])
                    self.assertEqual(r['pdfLanguage'+suffix],language)
                    if prefix:
                        self.assertIn('/'+r['coverImage_en'],PDFLinks(html).images)
                        self.assertIn('PDF · English',html)
                        self.assertNotIn('PDF is in Chinese',html)
                        self.assertIn('English edition prepared',html)
                    article=next(n for n in Head(html).graphs[0]['@graph'] if n['@type']=='Article')
                    self.assertEqual(article['datePublished'],r['published'])
                    self.assertEqual(article.get('dateModified'),r.get('updated'))
                    self.assertEqual(article['identifier'],r['researchId'])

    def test_translation_registry_preserves_original_versions(self):
        registry=json.loads((ROOT/'content/research-registry.json').read_text(encoding='utf8'))
        editions=registry['englishEditions']
        self.assertGreaterEqual(len(editions),6)
        self.assertEqual(len({e['researchId'] for e in editions}),len(editions))
        for e in editions:
            r=json.loads((ROOT/'content/research'/(e['slug']+'.json')).read_text(encoding='utf8'))
            self.assertEqual(e['sourcePdfSha256'],r['pdfSha256'])
            self.assertEqual(e['pdfSha256'],r['pdfSha256_en'])
            self.assertEqual(e['version'],r['version'])
            self.assertEqual(e['originalPreparedOrPublishedDate'],r['published'])
            self.assertEqual(e['dataThrough'],r['dataThrough'])
