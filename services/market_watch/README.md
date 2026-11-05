# SEC Market Watch

Independent public read-only API, using Python standard library and SQLite. The website owns this service; it does not read research databases or account records.

## Local validation

From the website root:

    python -m unittest discover -s services/market_watch -p test_service.py
    python scripts/build.py
    python scripts/check.py
    python services/market_watch/service.py --data .runtime/market-watch --once --limit 100
    python services/market_watch/service.py --data .runtime/market-watch --static dist --port 8775

Open `/market-watch/` or `/en/market-watch/` on the preview server. Local HTML receives a same-origin API override; published assets contain no development hostnames.

## Collection and semantics

- Contact User-Agent: `Residual Inertia Research data@residualinertia.com`.
- Atom latest ownership filings every 60 seconds; daily indexes recover the previous 29 US Eastern calendar days every six hours.
- Forms 3, 4, 5 and amendments are separate records keyed by accession. Missing prices are null, never zero. Original SEC links and footnotes are retained.
- FTD latest two official half-month batches are checked every six hours. The list shows the latest available settlement date. Daily balances are never summed; missing days are not filled with zeros.
- One collector throttles requests below three per second. Access/rate rejections pause all SEC requests for 15 minutes, persisted in SQLite. No proxy rotation or access workaround.
- Failed updates preserve the previous data. Indexed filings and parsed details are counted separately. Initial backfill can take hours and is not reported as complete prematurely.

## DOCN deployment

Copy `service.py`, `install_remote.py`, and a SQLite **backup** named `market-watch.sqlite3` to a dedicated staging directory on the authorized server. Run the installer there. It creates only the dedicated service, data directory and one nginx prefix, backing up nginx before editing and validating before reload.

Service: `ri-market-watch`; code: `/opt/ri-market-watch`; state: `/var/lib/ri-market-watch`; loopback port: 8774. API: `https://global.residualinertia.com/api/market-watch/`. Public GET only, CORS main domain. Existing account/global services are not restarted. Never copy an active SQLite file without its WAL; use `sqlite3.Connection.backup`.

Rollback: remove the added `location ^~ /api/market-watch/` block, run `nginx -t`, reload nginx, then disable/stop only `ri-market-watch`. Preserve its database. Do not restore an old nginx backup over subsequent unrelated edits.

## Validation checkpoint — 2026-11-06 Beijing

Dedicated DOCN service and public API are running. Main-site bilingual navigation is included in this release. Automatic translation is disabled; SEC footnotes remain in their original English.

At 01:31 Beijing: 7,235 indexed filings, 3,756 parsed and 3,479 pending. Latest feed checks succeed and parsing has progressed; index backfill still reports an SEC HTTP 403 and uses the persisted cooldown. Coverage remains partial and the page displays parsed/pending counts. FTD batches cover 2026-09-15 through 2026-10-14; this is the latest imported settlement data, not live trading data.

Validation: 3 service tests, 58 website Python tests, seven JS suites, build and public-content/link scan. Shared header geometry verified across pages and mobile widths. Font preloading, stable scrollbar allocation, reserved account/search space and document transitions reduce navigation shifts and flashes.
