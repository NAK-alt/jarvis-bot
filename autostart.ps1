param(
    [switch]$Disable
)

$startupPath = [System.Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupPath 'JarvisBackground.lnk'

if ($Disable) {
    if (Test-Path $shortcutPath) {
        Remove-Item $shortcutPath -Force
        Write-Host "✅ Auto-start shortcut removed from Windows Startup." -ForegroundColor Green
    } else {
        Write-Host "ℹ️ No auto-start shortcut was found." -ForegroundColor Yellow
    }
} else {
    $ws = New-Object -ComObject WScript.Shell
    $s = $ws.CreateShortcut($shortcutPath)
    $pythonwPath = "C:\Users\ROG\AppData\Local\Programs\Python\Python312\pythonw.exe"
    if (-not (Test-Path $pythonwPath)) {
        $pythonwPath = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    }
    $s.TargetPath = $pythonwPath
    $s.Arguments = "`"$PSScriptRoot\pc_bridge.py`""
    $s.WorkingDirectory = $PSScriptRoot
    $s.Description = "Start J.A.R.V.I.S. PC Bridge in Background"
    $s.Save()
    Write-Host "✅ Auto-start shortcut created successfully in Windows Startup!" -ForegroundColor Green
    Write-Host "• Location: $shortcutPath"
    Write-Host "• Jarvis PC Bridge will now connect automatically whenever Windows boots up."
}
