Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

' Run pythonw.exe hidden (0 = hidden window, False = don't wait)
pythonwExe = "C:\Users\ROG\AppData\Local\Programs\Python\Python312\pythonw.exe"
If Not FSO.FileExists(pythonwExe) Then
    pythonwExe = "pythonw.exe"
End If

WshShell.Run """" & pythonwExe & """ """ & scriptDir & "\pc_bridge.py""", 0, False
Set WshShell = Nothing
Set FSO = Nothing
