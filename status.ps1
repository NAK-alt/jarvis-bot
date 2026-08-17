$found = @()
Get-CimInstance Win32_Process | ForEach-Object {
    if ($_.CommandLine -and ($_.CommandLine -match 'pc_bridge\.py|main\.py|server\.py|tray\.py')) {
        $found += $_
    }
}

if ($found.Count -gt 0) {
    Write-Host "🟢 J.A.R.V.I.S. process is RUNNING in the background!" -ForegroundColor Green
    foreach ($p in $found) {
        Write-Host "• Process ID : $($p.ProcessId)"
        Write-Host "• Started    : $($p.CreationDate)"
    }
} else {
    Write-Host "🔴 J.A.R.V.I.S. process is currently NOT running." -ForegroundColor Red
}

$bridgeLog = Join-Path $PSScriptRoot "bridge.log"
if (Test-Path $bridgeLog) {
    Write-Host "`n----------------------------------------------------"
    Write-Host "Recent Bridge Logs (bridge.log):"
    Write-Host "----------------------------------------------------"
    Get-Content $bridgeLog -Tail 15
}

$jarvisLog = Join-Path $PSScriptRoot "jarvis.log"
if ((Test-Path $jarvisLog) -and !(Test-Path $bridgeLog)) {
    Write-Host "`n----------------------------------------------------"
    Write-Host "Recent Server Logs (jarvis.log):"
    Write-Host "----------------------------------------------------"
    Get-Content $jarvisLog -Tail 15
}
