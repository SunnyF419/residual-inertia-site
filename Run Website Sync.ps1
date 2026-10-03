param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.runtime\website-sync'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$log = Join-Path $runtime 'sync.log'
$statusPath = Join-Path $runtime 'latest.json'
$lease = New-Object System.Threading.Mutex($false, 'Local\ResidualInertiaWebsiteSync')
try { $acquired = $lease.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $acquired = $true }
if (-not $acquired) { $lease.Dispose(); exit 0 }
function Write-SyncLog([string]$Message) {
    Add-Content -LiteralPath $log -Value ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message) -Encoding UTF8
}
$started = (Get-Date).ToUniversalTime().ToString('o')
try {
    $paths = Get-Content -LiteralPath (Join-Path $runtime 'paths.json') -Raw | ConvertFrom-Json
    $env:PATH = (@($paths.node, $paths.python, $paths.git) | ForEach-Object { Split-Path -Parent $_ }) -join ';'
    $env:PATH += ';' + [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH', 'User')
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $portal = Join-Path (Split-Path -Parent $PSScriptRoot) 'quant_research_portal'
    Write-SyncLog 'Refreshing the local summary and publishing validated market data.'
    # Read committed dashboard outputs only. Do not run updates or create a daily archive.
    $refreshOutput = & $paths.node (Join-Path $portal 'scripts\sync-portal-data.mjs') 2>&1
    $refreshExit = $LASTEXITCODE
    foreach ($line in $refreshOutput) { Write-SyncLog ([string]$line) }
    if ($refreshExit -ne 0) { throw 'Local summary refresh failed; the previous website remains online.' }
    $arguments = @{ PortalPath = $portal }
    if (-not $CheckOnly) { $arguments.Publish = $true }
    & (Join-Path $PSScriptRoot 'Update Website.ps1') @arguments 2>&1 | ForEach-Object { Write-SyncLog ([string]$_) }
    $market = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'content\market\latest.json') -Raw | ConvertFrom-Json
    $result = [ordered]@{ status = $(if ($CheckOnly) { 'validated' } else { 'pushed' }); startedAt = $started; finishedAt = (Get-Date).ToUniversalTime().ToString('o'); dataAsOf = $market.market.regimeDate; score = $market.market.regimeScore; message = 'Public content validated; GitHub Pages deployment follows a changed push.' }
    $result | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    Write-SyncLog 'Sync completed. Historical archives and author reports are preserved.'
} catch {
    Write-SyncLog ('FAILED: ' + $_.Exception.Message)
    [ordered]@{ status = 'error'; startedAt = $started; finishedAt = (Get-Date).ToUniversalTime().ToString('o'); message = $_.Exception.Message } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    exit 1
} finally {
    $lease.ReleaseMutex()
    $lease.Dispose()
}
