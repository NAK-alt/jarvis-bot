$found = @()
Get-CimInstance Win32_Process | ForEach-Object {
    if ($_.CommandLine -and ($_.CommandLine -match 'pc_bridge\.py|main\.py|server\.py|tray\.py')) {
        $found += $_
    }
}

if ($found.Count -gt 0) {
    foreach ($p in $found) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "[+] Terminated J.A.R.V.I.S. process ID: $($p.ProcessId)" -ForegroundColor Green
    }
    Write-Host "✅ J.A.R.V.I.S. has been stopped." -ForegroundColor Green
} else {
    Write-Host "ℹ️ No active J.A.R.V.I.S. processes found." -ForegroundColor Yellow
}
