Start-ChocolateyProcessAsAdmin "pip3 install trelby==2.4.16"
Install-ChocolateyShortcut -ShortcutFilePath "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\trelby.lnk" -TargetPath "C:\Python313\Scripts\trelby.exe" -IconLocation "C:\Python313\Lib\site-packages\trelby\resources\icon256.ico"
