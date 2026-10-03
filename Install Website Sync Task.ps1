$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.runtime\website-sync'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$paths = @{}
foreach ($tool in @('node', 'python', 'git')) {
    $paths[$tool] = (Get-Command $tool -ErrorAction Stop).Source
}
$paths | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'paths.json') -Encoding UTF8
$runner = Join-Path $PSScriptRoot 'Run Website Sync.ps1'
$shell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$action = New-ScheduledTaskAction -Execute $shell -Argument ('-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $runner) -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) -RepetitionInterval (New-TimeSpan -Minutes 15)
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$logon = New-ScheduledTaskTrigger -AtLogOn -User $userId
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger @($trigger, $logon) -Settings $settings -Principal $principal -Description 'Every 15 minutes and at login, publish validated public market data independently of full-portal daily archiving. Do not calculate dashboard signals or publish author reports.'
$taskName = 'Residual Inertia - Website Data Sync'
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object TaskName, NextRunTime, LastTaskResult
