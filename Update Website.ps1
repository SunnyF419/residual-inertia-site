param(
    [string]$PortalPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'quant_research_portal'),
    [switch]$Publish
)
$ErrorActionPreference = 'Stop'
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'Never'
$publishLock = $null
if ($Publish) {
    $publishLock = New-Object System.Threading.Mutex($false, 'Local\ResidualInertiaWebsitePublish')
    try { $acquired = $publishLock.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { $publishLock.Dispose(); throw 'Another website publication is running; retry later.' }
}
Push-Location $PSScriptRoot
try {
    if ($Publish) {
        git -c "safe.directory=$PSScriptRoot" diff --cached --quiet
        if ($LASTEXITCODE -ne 0) { throw 'Review or commit already-staged changes before publishing website content.' }
        $branch = git -c "safe.directory=$PSScriptRoot" branch --show-current
        if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') { throw 'Publish from the main branch.' }
        git -c "safe.directory=$PSScriptRoot" diff --quiet -- . ':!content'
        if ($LASTEXITCODE -ne 0) { throw 'Commit website code changes before automatic publication.' }
        git -c "safe.directory=$PSScriptRoot" fetch origin main
        if ($LASTEXITCODE -ne 0) { throw 'Could not sync reports uploaded through the website.' }
        git -c "safe.directory=$PSScriptRoot" merge --no-edit origin/main
        if ($LASTEXITCODE -ne 0) {
            git -c "safe.directory=$PSScriptRoot" merge --abort
            throw 'Could not merge newly uploaded reports; local work is preserved.'
        }
    }
    python scripts/import_portal.py --portal $PortalPath
    if ($LASTEXITCODE -ne 0) { throw 'Import failed.' }
    python scripts/build.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    python scripts/check.py
    if ($LASTEXITCODE -ne 0) { throw 'Public output validation failed.' }
    if ($Publish) {
        git -c "safe.directory=$PSScriptRoot" add -- content
        if ($LASTEXITCODE -ne 0) { throw 'Could not stage public content.' }
        git -c "safe.directory=$PSScriptRoot" diff --cached --quiet
        $stagedExit = $LASTEXITCODE
        if ($stagedExit -eq 1) {
            git -c "safe.directory=$PSScriptRoot" commit -m "content: update published research archives"
            if ($LASTEXITCODE -ne 0) { throw 'Commit failed.' }
        } elseif ($stagedExit -ne 0) { throw 'Could not inspect staged changes.' }
        for ($publishAttempt = 0; $publishAttempt -lt 3; $publishAttempt++) {
            git -c "safe.directory=$PSScriptRoot" push origin main
            if ($LASTEXITCODE -eq 0) { break }
            if ($publishAttempt -eq 2) { throw 'Push failed; local content remains available.' }
            git -c "safe.directory=$PSScriptRoot" fetch origin main
            if ($LASTEXITCODE -ne 0) { throw 'Could not fetch concurrent report updates; local content remains available.' }
            git -c "safe.directory=$PSScriptRoot" merge --no-edit origin/main
            if ($LASTEXITCODE -ne 0) {
                git -c "safe.directory=$PSScriptRoot" merge --abort
                throw 'Concurrent updates need review; local content remains available.'
            }
            python scripts/build.py
            if ($LASTEXITCODE -ne 0) { throw 'Build failed after merging new reports.' }
            python scripts/check.py
            if ($LASTEXITCODE -ne 0) { throw 'Validation failed after merging new reports.' }
        }
    }
} finally {
    Pop-Location
    if ($publishLock) { $publishLock.ReleaseMutex(); $publishLock.Dispose() }
}
