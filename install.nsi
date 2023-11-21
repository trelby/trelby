; below is copied from: http://nsis.sourceforge.net/wiki/FileAssoc

; !defines for use with SHChangeNotify
!ifdef SHCNE_ASSOCCHANGED
!undef SHCNE_ASSOCCHANGED
!endif
!define SHCNE_ASSOCCHANGED 0x08000000
!ifdef SHCNF_FLUSH
!undef SHCNF_FLUSH
!endif
!define SHCNF_FLUSH        0x1000

RequestExecutionLevel admin

!macro UPDATEFILEASSOC
; Using the system.dll plugin to call the SHChangeNotify Win32 API function
; so we can update the shell.
  System::Call "shell32::SHChangeNotify(i,i,i,i) (${SHCNE_ASSOCCHANGED}, ${SHCNF_FLUSH}, 0, 0)"
!macroend

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "Trelby"
!define PRODUCT_VERSION "2.3.0.0-dev"
!define PRODUCT_PUBLISHER "Trelby.org"
!define PRODUCT_WEB_SITE "http://www.trelby.org/"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\trelby.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

Caption "${PRODUCT_NAME} installer"
VIProductVersion ${PRODUCT_VERSION}
VIAddVersionKey ProductName "${PRODUCT_NAME}"
VIAddVersionKey Comments "Installer for Trelby."
VIAddVersionKey CompanyName Trelby.org
VIAddVersionKey LegalCopyright Trelby.org
VIAddVersionKey FileDescription "${PRODUCT_NAME} ${PRODUCT_VERSION} installer"
VIAddVersionKey ProductVersion "${PRODUCT_VERSION}"

SetCompressor lzma

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "icon32.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; Reserve files
!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS

; MUI end ------

Name "${PRODUCT_NAME}"
OutFile "Setup-${PRODUCT_NAME}-${PRODUCT_VERSION}.exe"
InstallDir "C:\Program Files\Trelby"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Function .onInit

  ReadRegStr $R0 ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" \
  "UninstallString"
  StrCmp $R0 "" done

  MessageBox MB_OK "${PRODUCT_NAME} is already installed. You need to uninstall the old version first before installing this new version."
  Abort

done:

FunctionEnd

Section MFCRUNTIME
  SetOutPath "$INSTDIR"
  File "vcredist_x86.exe"
  ExecWait `vcredist_x86.exe /q:a /c:"VCREDI~1.EXE /q:a /c:""msiexec /i vcredist.msi /qn"" "`
SectionEnd

Section "MainSection" SEC01
  SetShellVarContext all
  SetOutPath "$INSTDIR"
  SetOverwrite on
  File /r "dist\*"
  CreateDirectory "$SMPROGRAMS\Trelby"
  CreateShortCut "$SMPROGRAMS\Trelby\Trelby.lnk" "$INSTDIR\trelby.exe"
  CreateShortCut "$DESKTOP\Trelby.lnk" "$INSTDIR\trelby.exe"
  Delete "$INSTDIR\vcredist_86.exe"
SectionEnd

Section -AdditionalIcons
  SetShellVarContext all
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\Trelby\Manual.lnk" "$INSTDIR\manual.html"
  CreateShortCut "$SMPROGRAMS\Trelby\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\Trelby\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\trelby.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "Path" "$INSTDIR"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\trelby.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"

  ; file associations
  WriteRegStr HKCR ".trelby" "" "Trelby.Screenplay"
  WriteRegStr HKCR "Trelby.Screenplay" "" "Trelby Screenplay"
  WriteRegStr HKCR "Trelby.Screenplay\DefaultIcon" "" "$INSTDIR\trelby.exe,0"
  WriteRegStr HKCR "Trelby.Screenplay\shell" "" "open"
  WriteRegStr HKCR "Trelby.Screenplay\shell\open\command" "" '"$INSTDIR\trelby.exe" "%1"'

 !insertmacro UPDATEFILEASSOC
SectionEnd


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\zlib.pyd"
  Delete "$INSTDIR\_sre.pyd"
  Delete "$INSTDIR\trelby.exe"
  Delete "$INSTDIR\datetime.pyd"
  Delete "$INSTDIR\pyexpat.pyd"
  Delete "$INSTDIR\htmlc.pyd"
  Delete "$INSTDIR\names.txt.gz"
  Delete "$INSTDIR\dict_en.dat.gz"
  Delete "$INSTDIR\bz2.pyd"
  Delete "$INSTDIR\_hashlib.pyd"
  Delete "$INSTDIR\python27.dll"
  Delete "$INSTDIR\select.pyd"
  Delete "$INSTDIR\vcredist_x86.exe"
  Delete "$INSTDIR\lxml.etree.pyd"
  Delete "$INSTDIR\wxbase28uh_net_vc.dll"
  Delete "$INSTDIR\wxbase28uh_vc.dll"
  Delete "$INSTDIR\wx._controls_.pyd"
  Delete "$INSTDIR\wx._core_.pyd"
  Delete "$INSTDIR\wx._gdi_.pyd"
  Delete "$INSTDIR\wx._html.pyd"
  Delete "$INSTDIR\wx._misc_.pyd"
  Delete "$INSTDIR\wxmsw28uh_adv_vc.dll"
  Delete "$INSTDIR\wxmsw28uh_core_vc.dll"
  Delete "$INSTDIR\wxmsw28uh_html_vc.dll"
  Delete "$INSTDIR\wx._windows_.pyd"
  Delete "$INSTDIR\unicodedata.pyd"
  Delete "$INSTDIR\w9xpopen.exe"
  Delete "$INSTDIR\library.zip"
  Delete "$INSTDIR\wxc.pyd"
  Delete "$INSTDIR\sample.trelby"
  Delete "$INSTDIR\_socket.pyd"
  Delete "$INSTDIR\_ssl.pyd"
  Delete "$INSTDIR\_winreg.pyd"
  Delete "$INSTDIR\_ctypes.pyd"
  Delete "$INSTDIR\manual.html"
  Delete "$INSTDIR\fileformat.txt"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\README.md"

  SetShellVarContext all
  Delete "$SMPROGRAMS\Trelby\Uninstall.lnk"
  Delete "$SMPROGRAMS\Trelby\Website.lnk"
  Delete "$DESKTOP\Trelby.lnk"
  Delete "$SMPROGRAMS\Trelby\Trelby.lnk"
  Delete "$SMPROGRAMS\Trelby\Manual.lnk"

  RMDir /r "$INSTDIR\resources"
  RMDir "$SMPROGRAMS\Trelby"
  RMDir "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  DeleteRegKey HKCR ".trelby"
  DeleteRegKey HKCR "Trelby.Screenplay\DefaultIcon"
  DeleteRegKey HKCR "Trelby.Screenplay\shell"
  DeleteRegKey HKCR "Trelby.Screenplay\shell\open\command"
  DeleteRegKey HKCR "Trelby.Screenplay"

 !insertmacro UPDATEFILEASSOC

  SetAutoClose true
SectionEnd
