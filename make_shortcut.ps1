$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut("$desktop\Purrfectly Chaotic.lnk")
$lnk.TargetPath = "$root\.venv\Scripts\pythonw.exe"
$lnk.Arguments = "`"$root\launcher.pyw`""
$lnk.WorkingDirectory = $root
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (Test-Path $edge) { $lnk.IconLocation = "$edge,0" }
$lnk.Description = "Purrfectly Chaotic dashboard"
$lnk.Save()
Write-Output "Shortcut created: $desktop\Purrfectly Chaotic.lnk"
