$ErrorActionPreference = "Stop"

function Write-DailyTaskLog {
  param([string]$Message)
  $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  Add-Content -LiteralPath $script:LogPath -Value "[$timestamp] $Message" -Encoding UTF8
}

function Get-PortalDailyStatus {
  return Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:3021/api/daily-archive/status" -TimeoutSec 3
}

function Publish-ArchivedWebsite {
  if (-not (Test-Path -LiteralPath $dailyPath)) {
    throw 'Website publication requires the completed daily archive.'
  }
  $publisher = Join-Path (Split-Path -Parent $projectRoot) 'residual-inertia-site\Update Website.ps1'
  Write-DailyTaskLog 'Website: importing, validating and publishing public daily archives.'
  $shell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
  $info = New-Object System.Diagnostics.ProcessStartInfo
  $info.FileName = $shell
  $info.Arguments = '-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{0}" -PortalPath "{1}" -Publish' -f $publisher, $projectRoot
  $info.UseShellExecute = $false
  $info.CreateNoWindow = $true
  $info.RedirectStandardOutput = $true
  $info.RedirectStandardError = $true
  $child = New-Object System.Diagnostics.Process
  $child.StartInfo = $info
  [void]$child.Start()
  $stdout = $child.StandardOutput.ReadToEndAsync()
  $stderr = $child.StandardError.ReadToEndAsync()
  if (-not $child.WaitForExit(600000)) {
    $child.Kill()
    throw 'Website publication timed out; retry will use the existing archive.'
  }
  foreach ($line in @($stdout.Result, $stderr.Result) -split "`r?`n" | Where-Object { $_ }) { Write-DailyTaskLog $line }
  if ($child.ExitCode -ne 0) { throw 'Website publication failed; the daily archive is retained for retry.' }
  $child.Dispose()
  Write-DailyTaskLog 'Website: public content pushed successfully; GitHub Pages handles deployment.'
}

try {
  $projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
  if (-not $projectRoot.StartsWith("E:\", [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "每日归档项目必须位于 E 盘。"
  }
  $runtimeRoot = Join-Path $projectRoot ".runtime\daily-archive"
  $tempRoot = Join-Path $runtimeRoot "temp"
  $cacheRoot = Join-Path $runtimeRoot "cache"
  $pycacheRoot = Join-Path $runtimeRoot "pycache"
  $logRoot = Join-Path $runtimeRoot "logs"
  New-Item -ItemType Directory -Force -Path $runtimeRoot, $tempRoot, $cacheRoot, $pycacheRoot, $logRoot | Out-Null
  $script:LogPath = Join-Path $logRoot "windows-task.log"

  $env:TEMP = $tempRoot
  $env:TMP = $tempRoot
  $env:TMPDIR = $tempRoot
  $env:XDG_CACHE_HOME = $cacheRoot
  $env:npm_config_cache = Join-Path $cacheRoot "npm"
  $env:PYTHONPYCACHEPREFIX = $pycacheRoot
  $env:PYTHONDONTWRITEBYTECODE = "1"

  if ((Get-Date).DayOfWeek -eq [DayOfWeek]::Sunday) {
    Write-DailyTaskLog "周日不更新、不建档。"
    exit 0
  }

  $dailyPath = Join-Path $projectRoot (".runtime\lineage\daily\{0}.json" -f (Get-Date -Format "yyyy-MM-dd"))
  if (Test-Path -LiteralPath $dailyPath) {
    Write-DailyTaskLog "今日日线快照已经存在，本次不重复更新或建档。"
    Publish-ArchivedWebsite
    exit 0
  }

  $usedPortal = $false
  $portalArchived = $false
  try {
    $health = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:3021/api/health" -TimeoutSec 3
    if ($health.ok) {
      $usedPortal = $true
      Write-DailyTaskLog "门户正在运行，交由门户执行统一更新与归档。"
      Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:3021/api/daily-archive/run" -TimeoutSec 15 | Out-Null
      $deadline = (Get-Date).AddHours(6)
      do {
        Start-Sleep -Seconds 5
        $state = Get-PortalDailyStatus
        if ($state.status -in @("archived", "archived_with_warnings")) {
          Write-DailyTaskLog $state.message
          $portalArchived = $true
          break
        }
        if ($state.status -in @("error", "update_failed")) {
          Write-DailyTaskLog ("门户执行失败，改用独立任务重试：" + $state.message)
          break
        }
      } while ((Get-Date) -lt $deadline)
    }
  } catch {
    if ($usedPortal) {
      Write-DailyTaskLog ("门户连接中断，改用独立任务继续：" + $_.Exception.Message)
    }
  }

  if ($portalArchived) {
    Publish-ArchivedWebsite
    exit 0
  }

  $nodePathFile = Join-Path $runtimeRoot "node-path.txt"
  if (-not (Test-Path -LiteralPath $nodePathFile)) {
    throw "缺少 E 盘 Node 运行路径记录，请重新运行 Install Daily Archive Task.ps1。"
  }
  $nodeExecutable = (Get-Content -LiteralPath $nodePathFile -Raw).Trim()
  if (-not (Test-Path -LiteralPath $nodeExecutable)) {
    throw "每日归档使用的 Node 运行环境已不存在，请重新安装计划任务。"
  }
  Write-DailyTaskLog "门户未运行，启动 E 盘独立更新与归档流程。"
  Set-Location -LiteralPath $projectRoot
  $processInfo = New-Object System.Diagnostics.ProcessStartInfo
  $processInfo.FileName = $nodeExecutable
  $processInfo.Arguments = ('"{0}"' -f (Join-Path $projectRoot "scripts\run-daily-archive-once.mjs"))
  $processInfo.WorkingDirectory = $projectRoot
  $processInfo.UseShellExecute = $false
  $processInfo.CreateNoWindow = $true
  $processInfo.RedirectStandardOutput = $true
  $processInfo.RedirectStandardError = $true
  $processInfo.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
  $processInfo.StandardErrorEncoding = New-Object System.Text.UTF8Encoding($false)
  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $processInfo
  [void]$process.Start()
  $standardOutput = $process.StandardOutput.ReadToEnd()
  $standardError = $process.StandardError.ReadToEnd()
  $process.WaitForExit()
  foreach ($line in @($standardOutput, $standardError) -split "`r?`n" | Where-Object { $_ }) {
    Write-DailyTaskLog $line
  }
  if ($process.ExitCode -ne 0) {
    throw "独立每日归档流程失败（退出码 $($process.ExitCode)），详情见 $script:LogPath"
  }
  Write-DailyTaskLog "每日自动更新与归档流程完成。"
  Publish-ArchivedWebsite
  exit 0
} catch {
  if ($script:LogPath) {
    Write-DailyTaskLog ("失败：" + $_.Exception.Message)
  }
  exit 1
}
