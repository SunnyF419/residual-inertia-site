# Research language editions

New formal RI research PDFs default to English. Website reading pages continue
to have separate Chinese and English text. Historical Chinese originals remain
available at their existing URLs.

For existing bilingual editions, records use `pdf` / `pdfSha256` for the original
Chinese PDF and `pdf_en` / `pdfSha256_en` for the complete English PDF. Set
`pdfLanguage` to `zh-CN` and `pdfLanguage_en` to `en`. The shared article builder
selects the active language edition, validates its hash and adds the selected
hash to the download URL. Articles without an alternate edition retain the
existing fallback.

The optional `coverImage_en` selects an English cover without replacing
`coverImage`. When a historical article has no Chinese cover asset, its Chinese
page is not given a new cover solely for this retrofit.

`englishEditionDate` records when the translation was prepared; it does not
replace `published`, `updated`, `dataThrough`, `researchId` or `version`. The
English PDF and visible article note distinguish the translation date from the
original preparation/publication date. Translation details and original hashes
are registered in `content/research-registry.json` under `englishEditions`.

The 2026-10-11 retrofit covers six weekly reports, September 5 through October 10.
English manuscripts, report-generation sources, six PDF/PNG outputs and rendered
QA pages are stored in the research artifact directory
`E:/QuantResearchHub/05_reports_and_figures/RI_weekly_english_20261011`.
Only approved public assets and article records enter the website bundle.
