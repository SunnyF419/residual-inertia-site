# Market data publication

`Update Website.ps1 -Publish` publishes from a dedicated independent Git clone at
`.runtime/website-sync/publication`, on `main`. The source checkout's tracked edits,
staged files, untracked drafts and unpublished development commits are preserved
and are never copied to that clone. The clone fetches the verified website origin
and uses its committed importer, builder and public-content checks.

The portal path is resolved before changing directories. Both the daily archive
task and `Run Website Sync.ps1` use this publication path and the existing named
publication mutex. A second publisher stops; the helper does not acquire a second
mutex or run research updates.

Only `content/market/` and `content/snapshots/` can be staged or committed by the
publisher. Unrelated clone edits, staging, untracked files or unpublished commits
stop publication without removing them. A failed push's data commits remain for
the next attempt. Uploaded author reports are fetched and merged from `origin/main`;
a concurrent upload causes the merged site to be rebuilt and checked before retry.

Existing source archive revision checks, data quality checks and protection against
backwards market dates remain in the importer. Import, build or validation failure
does not push a new site. A merge conflict is retained in the publication clone for
review. No automatic reset, stash, recursive cleanup or draft submission is used.
Git diagnostics are logged separately from its returned file paths and commit IDs;
Windows line-ending warnings cannot be mistaken for unrelated changes.

After a successful push, `publication-result.json` records the actual clone's
market date, score and pushed commit. `Run Website Sync.ps1` checks that this result
belongs to the current run before writing its status. Its status no longer reads
the possibly older development checkout. Check-only mode retains the existing
local import and preview behavior. The daily task schedule is unchanged.

## Local regression tests

On Windows, run `python tests/test_market_publication.py -v`. Tests create private
temporary repositories and use a Git URL rewrite to resolve the public repository
address to a local bare origin. They do not access GitHub, update real dashboards,
install tasks or edit the real Git configuration.

The tests exercise draft preservation, content-only publication, rejected clone
contamination, pending data recovery, import and validation failure, publication
mutex exclusion, concurrent author uploads, repeated no-change runs, relative portal
paths and accurate synchronization status. Tests skip on platforms without Windows
PowerShell and Git.

## Dashboard migration repair — 2026-10-23

The site had retained the October 13 reading. Publication failed because the
importer selected the legacy `config.yaml` database and `market_regime_history`,
while the dashboard now uses `config/paths.yaml` and the explicitly authorized
`HML_DUAL99_ESTIMATE_REGIME_V1` estimate series. The endpoint consistency gate
correctly stopped the mismatched publication. The directory migration also broke
the assumption that the portal and website were sibling folders.

The website now reads the existing `reports/latest_signals.json` directly. It does
not refresh portal data, run models, write dashboard databases, or create archives.
Portal configuration supplies the read-only source location and existing archives.
`resolve_portal.mjs` supports the migrated Hub layout, legacy sibling layout, and
an explicit `RI_PORTAL_PATH` or local `paths.json` `portal` setting. An invalid
explicit path fails instead of creating a new portal folder.

The dashboard runtime database configuration takes priority over its legacy file.
Model versions select an allowlisted history table; unknown versions stop for
review. History and headline endpoints must agree before content is written.
Null history observations remain gaps in both initial HTML and interactive charts.
Archived snapshots keep their original values and are not rewritten to the new model.

The public whitelist covers weekly risk, breadth, financial conditions, effective
WQS observations, Livermore S2, factor crowding, HML/UMD, AI hardware pillars and
ETF/group returns, and independent liquidity source availability. Local paths,
holdings, raw errors and credentials are excluded. Future-effective WQS rows are
not current observations. Low-quality or older-than-14-day liquidity values are
not shown as current market signals. Composite estimates, pending source updates,
and each module's own date are visible in both languages.

The completion checker also fingerprints the completed dashboard export so a
missed portal event does not permanently prevent a later scheduled check from
publishing. A fingerprint is recorded only after a successful publication. The
existing Windows schedule is retained. All temporary test repositories, browser
profiles, logs and screenshots belong under this website's `.runtime/website-sync`.
Set `TEMP` and `TMP` there before local publication tests.

Rollback: revert the website repair commit through Git. Do not restore or modify
research databases. Reverting only the importer while retaining the new public
model will deliberately fail the consistency gate; keep the last good deployed
site until code and exported model agree again.
