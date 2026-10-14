param(
    [string]$PortalPath = (Join-Path (Split-Path -Parent $PSScriptRoot) 'quant_research_portal'),
    [switch]$Publish,
    [string]$ResultPath = (Join-Path $PSScriptRoot '.runtime\website-sync\publication-result.json')
)
$ErrorActionPreference = 'Stop'
$PortalPath = (Resolve-Path -LiteralPath $PortalPath).ProviderPath
$ResultPath = [System.IO.Path]::GetFullPath($ResultPath)
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'Never'
$env:GIT_CONFIG_COUNT = '1'
$env:GIT_CONFIG_KEY_0 = 'http.sslBackend'
$env:GIT_CONFIG_VALUE_0 = 'openssl'
if ($Publish) {
    $lease = New-Object System.Threading.Mutex($false, 'Local\ResidualInertiaWebsitePublish')
    try { $acquired = $lease.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { $lease.Dispose(); throw 'Another website publication is running; retry later.' }
    try {
        . (Join-Path $PSScriptRoot 'scripts\publish_market.ps1')
        Invoke-MarketPublication -SourceRoot $PSScriptRoot -PortalPath $PortalPath -ResultPath $ResultPath
    } finally {
        $lease.ReleaseMutex()
        $lease.Dispose()
    }
    return
}
# Check-only mode preserves the existing local preview workflow.
Push-Location $PSScriptRoot
try {
    python scripts/import_portal.py --portal $PortalPath
    if ($LASTEXITCODE -ne 0) { throw 'Import failed.' }
    python scripts/build.py
    if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
    python scripts/check.py
    if ($LASTEXITCODE -ne 0) { throw 'Public output validation failed.' }
} finally {
    Pop-Location
}
