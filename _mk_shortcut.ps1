$WScript = New-Object -ComObject WScript.Shell
$shortcut = $WScript.CreateShortcut("$env:USERPROFILE\Desktop\写日记.lnk")
$shortcut.TargetPath = "C:\Users\HEBE\Desktop\journal\日记.bat"
$shortcut.WorkingDirectory = "C:\Users\HEBE\Desktop\journal"
$shortcut.IconLocation = "notepad.exe,0"
$shortcut.Save()
Write-Host "Done"
