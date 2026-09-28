param(
    [Parameter(Mandatory=$true)][string]$PortalPath,
    [switch]$Publish
)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if ($Publish) {
        git diff --cached --quiet
        if ($LASTEXITCODE -ne 0) { throw 'Review or commit already-staged changes before publishing website content.' }
        $branch = git branch --show-current
        if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') { throw 'Publish from the main branch.' }
    }
    python scripts/import_portal.py --portal $PortalPath
    if ($LASTEXITCODE -ne 0) { throw 'Import failed.' }
    python scripts/build.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    python scripts/check.py
    if ($LASTEXITCODE -ne 0) { throw 'Public output validation failed.' }
    if ($Publish) {
        git add -- content
        if ($LASTEXITCODE -ne 0) { throw 'Could not stage public content.' }
        git diff --cached --quiet
        $stagedExit = $LASTEXITCODE
        if ($stagedExit -eq 1) {
            git commit -m "content: update published research archives"
            if ($LASTEXITCODE -ne 0) { throw 'Commit failed.' }
        } elseif ($stagedExit -ne 0) { throw 'Could not inspect staged changes.' }
        git push origin main
        if ($LASTEXITCODE -ne 0) { throw 'Push failed; local content remains available.' }
    }
} finally { Pop-Location }
