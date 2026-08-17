$pythonwPath = "C:\Users\ROG\AppData\Local\Programs\Python\Python312\pythonw.exe"
$scriptDir = $PSScriptRoot
$bridgeScript = Join-Path $scriptDir "pc_bridge.py"

$cmdLine = "`"$pythonwPath`" `"$bridgeScript`""

$processClass = [wmiclass]"Win32_Process"
$result = $processClass.Create($cmdLine, $scriptDir, $null)

if ($result.ReturnValue -eq 0) {
    Write-Host "✅ J.A.R.V.I.S. PC Bridge successfully spawned as persistent Windows process! (PID: $($result.ProcessId))" -ForegroundColor Green
    Write-Host "This process is completely independent of any terminal or command prompt."
} else {
    Write-Host "❌ Failed to create process. Return value: $($result.ReturnValue)" -ForegroundColor Red
}
