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
