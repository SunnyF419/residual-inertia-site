$ErrorActionPreference = 'Stop'
$runtime = Join-Path $PSScriptRoot '.runtime\website-sync'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$paths = @{}
foreach ($tool in @('node', 'python', 'git')) {
    $paths[$tool] = (Get-Command $tool -ErrorAction Stop).Source
}
$paths | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'paths.json') -Encoding UTF8
$runner = Join-Path $PSScriptRoot 'Watch Website Updates.ps1'
$shell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$action = New-ScheduledTaskAction -Execute $shell -Argument ('-NoLogo -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}"' -f $runner) -WorkingDirectory $PSScriptRoot
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$logon = New-ScheduledTaskTrigger -AtLogOn -User $userId
# Restart-on-failure alone did not recover a cancelled listener (0xC000013A).
# This trigger starts only the listener; publication still requires a new,
# successful dashboard completion. IgnoreNew preserves a running listener.
$recovery = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$task = New-ScheduledTask -Action $action -Trigger @($logon, $recovery) -Settings $settings -Principal $principal -Description 'Listen for successful, committed market dashboard updates and push validated public JSON to GitHub. Recover a stopped listener every five minutes; IgnoreNew leaves a running listener alone. Event driven publication only; failed updates retain the previous website.'
$taskName = 'Residual Inertia - Website Data Sync'
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object TaskName, NextRunTime, LastTaskResult
