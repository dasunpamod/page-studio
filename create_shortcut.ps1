$WshShell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop "PageStudio.lnk"
$Shortcut = $WshShell.CreateShortcut($shortcutPath)
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonw = "pythonw.exe"
}
$Shortcut.TargetPath = $pythonw
$Shortcut.Arguments = 'PageStudio.pyw'
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "PageStudio - Visual GUI Generator for Python Tkinter"
$Shortcut.Save()
Write-Output "SUCCESS: Shortcut created at $shortcutPath"
