# Publish committed origin/main code in its own clone; never copy development
# files, local commits, credentials, reports or drafts from the source checkout.
function Invoke-MarketPublication {
    param([string]$SourceRoot, [string]$PortalPath, [string]$ResultPath)
    $publicationRoot = Join-Path $SourceRoot '.runtime\website-sync\publication'
    function Invoke-PublicationGit([string[]]$Arguments) {
        # stderr is diagnostic text, never a file path or commit identifier.
        # JSON exporters use Windows newlines even when Git normalizes to LF.
        $info = New-Object System.Diagnostics.ProcessStartInfo
        $gitCommand = Get-Command git -CommandType Application -ErrorAction Stop | Select-Object -First 1
        $info.FileName = $gitCommand.Source
        $nativeArguments = @('-c', "safe.directory=$SourceRoot", '-c', "safe.directory=$publicationRoot") + $Arguments
        $info.Arguments = ($nativeArguments | ForEach-Object {
            '"' + ($_ -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
        }) -join ' '
        $info.WorkingDirectory = (Get-Location).ProviderPath
        $info.UseShellExecute = $false
        $info.CreateNoWindow = $true
        $info.RedirectStandardOutput = $true
        $info.RedirectStandardError = $true
        $info.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $info.StandardErrorEncoding = New-Object System.Text.UTF8Encoding($false)
        $child = New-Object System.Diagnostics.Process
        $child.StartInfo = $info
        try {
            [void]$child.Start()
            $stdout = $child.StandardOutput.ReadToEndAsync()
            $stderr = $child.StandardError.ReadToEndAsync()
            if (-not $child.WaitForExit(180000)) {
                $child.Kill()
                throw 'Git publication operation timed out; local files are preserved.'
            }
            if ($stderr.Result) { Write-Host $stderr.Result.TrimEnd() }
            if ($child.ExitCode -ne 0) { throw ('Git publication operation failed (exit {0}); local files are preserved.' -f $child.ExitCode) }
            return @($stdout.Result -split '\r?\n' | Where-Object { $_ })
        } finally { $child.Dispose() }
    }
    function Assert-DataPaths($Paths) {
        foreach ($path in $Paths) {
            if ($path -and $path -notmatch '^content/(market|snapshots)/') {
                throw 'The publication clone contains unrelated changes; review them before retrying. Development files are preserved.'
            }
        }
    }
    function Validate-Publication {
        python scripts/build.py
        if ($LASTEXITCODE -ne 0) { throw 'Build failed; the previous website is preserved.' }
        python scripts/check.py
        if ($LASTEXITCODE -ne 0) { throw 'Public output validation failed; the previous website is preserved.' }
    }
    $origin = (Invoke-PublicationGit -Arguments @('-C', $SourceRoot, 'config', '--get', 'remote.origin.url')) -join ''
    if ($origin -notmatch '^https://github\.com/SunnyF419/residual-inertia-site(?:\.git)?$') {
        throw 'The website origin is not the verified Residual Inertia repository.'
    }
    if (-not (Test-Path -LiteralPath $publicationRoot)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $publicationRoot) | Out-Null
        Invoke-PublicationGit -Arguments @('clone', '--branch', 'main', '--single-branch', '--', $origin, $publicationRoot) | Write-Output
    }
    $cloneOrigin = (Invoke-PublicationGit -Arguments @('-C', $publicationRoot, 'config', '--get', 'remote.origin.url')) -join ''
    if ($cloneOrigin -ne $origin) { throw 'Unexpected publication clone origin; no files were changed.' }
    Push-Location $publicationRoot
    try {
        $branch = (Invoke-PublicationGit -Arguments @('branch', '--show-current')) -join ''
        if ($branch -ne 'main') { throw 'The publication clone must remain on main.' }
        $mergeHead = (Invoke-PublicationGit -Arguments @('rev-parse', '--git-path', 'MERGE_HEAD')) -join ''
        if (Test-Path -LiteralPath $mergeHead) { throw 'The previous publication merge needs review; its files are preserved.' }
        Assert-DataPaths (Invoke-PublicationGit -Arguments @('diff', '--no-renames', '--name-only'))
        Assert-DataPaths (Invoke-PublicationGit -Arguments @('diff', '--cached', '--no-renames', '--name-only'))
        Assert-DataPaths (Invoke-PublicationGit -Arguments @('ls-files', '--others', '--exclude-standard'))
        Invoke-PublicationGit -Arguments @('fetch', 'origin', 'main') | Write-Output
        # A failed push may leave legitimate data commits for the next retry.
        Assert-DataPaths (Invoke-PublicationGit -Arguments @('log', '--no-merges', '--pretty=format:', '--name-only', 'origin/main..HEAD'))
        # Combined diffs expose files changed by a local merge beyond both
        # parents, while ordinary author-upload merges need no exception.
        $pendingMerges = @(Invoke-PublicationGit -Arguments @('log', '--merges', '--format=%H', 'origin/main..HEAD'))
        foreach ($commit in $pendingMerges) {
            Assert-DataPaths (Invoke-PublicationGit -Arguments @('diff-tree', '--cc', '--no-commit-id', '--name-only', '-r', $commit))
        }
        Invoke-PublicationGit -Arguments @('merge', '--no-edit', 'origin/main') | Write-Output
        Assert-DataPaths (Invoke-PublicationGit -Arguments @('diff', '--no-renames', '--name-only', 'origin/main', 'HEAD'))
        foreach ($key in @('user.name', 'user.email')) {
            $value = (Invoke-PublicationGit -Arguments @('-C', $SourceRoot, 'config', '--get', $key)) -join ''
            Invoke-PublicationGit -Arguments @('config', $key, $value) | Out-Null
        }
        python scripts/import_portal.py --portal $PortalPath
        if ($LASTEXITCODE -ne 0) { throw 'Import failed; original archives and the previous website are preserved.' }
        Validate-Publication
        Assert-DataPaths (Invoke-PublicationGit -Arguments @('diff', '--no-renames', '--name-only'))
        Assert-DataPaths (Invoke-PublicationGit -Arguments @('ls-files', '--others', '--exclude-standard'))
        Invoke-PublicationGit -Arguments @('add', '--', 'content/market', 'content/snapshots') | Out-Null
        $staged = @(Invoke-PublicationGit -Arguments @('diff', '--cached', '--no-renames', '--name-only'))
        Assert-DataPaths $staged
        if ($staged.Count -gt 0) {
            Invoke-PublicationGit -Arguments @('commit', '-m', 'content: sync validated market readings and daily archives') | Write-Output
        }
        $pushed = $false
        for ($attempt = 0; $attempt -lt 3; $attempt++) {
            try {
                Invoke-PublicationGit -Arguments @('push', 'origin', 'main') | Write-Output
                $pushed = $true
                break
            } catch {
                if ($attempt -eq 2) { throw 'Push failed; validated content remains in the publication clone for retry.' }
                Invoke-PublicationGit -Arguments @('fetch', 'origin', 'main') | Write-Output
                Invoke-PublicationGit -Arguments @('merge', '--no-edit', 'origin/main') | Write-Output
                # Preserve concurrent uploaded reports and validate the merged build.
                Validate-Publication
                Assert-DataPaths (Invoke-PublicationGit -Arguments @('diff', '--no-renames', '--name-only'))
                Assert-DataPaths (Invoke-PublicationGit -Arguments @('ls-files', '--others', '--exclude-standard'))
            }
        }
        if (-not $pushed) { throw 'Publication did not complete.' }
        $market = Get-Content -LiteralPath 'content/market/latest.json' -Raw | ConvertFrom-Json
        $result = [ordered]@{ status = 'pushed'; finishedAt = (Get-Date).ToUniversalTime().ToString('o'); dataAsOf = $market.market.regimeDate; score = $market.market.regimeScore; commit = ((Invoke-PublicationGit -Arguments @('rev-parse', 'HEAD')) -join '') }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ResultPath) | Out-Null
        $result | ConvertTo-Json | Set-Content -LiteralPath ($ResultPath + '.tmp') -Encoding UTF8
        Move-Item -LiteralPath ($ResultPath + '.tmp') -Destination $ResultPath -Force
    } finally {
        Pop-Location
    }
}
