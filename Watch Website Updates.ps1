$ErrorActionPreference = 'Stop'
$paths = Get-Content -LiteralPath (Join-Path $PSScriptRoot '.runtime\website-sync\paths.json') -Raw | ConvertFrom-Json
$env:PATH = (@($paths.node, $paths.python, $paths.git) | ForEach-Object { Split-Path -Parent $_ }) -join ';'
$env:PATH += ';' + [Environment]::GetEnvironmentVariable('PATH', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH', 'User')
$env:PYTHONDONTWRITEBYTECODE = '1'
& $paths.node (Join-Path $PSScriptRoot 'scripts\watch_dashboard_updates.mjs')
exit $LASTEXITCODE
