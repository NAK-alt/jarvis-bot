Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

' Run pyw -3.12 main.py hidden (0 = hidden window, False = don't wait)
WshShell.Run "pyw -3.12 main.py", 0, False
Set WshShell = Nothing
Set FSO = Nothing
