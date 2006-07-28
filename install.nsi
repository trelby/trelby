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
 
!macro UPDATEFILEASSOC
; Using the system.dll plugin to call the SHChangeNotify Win32 API function
; so we can update the shell.
  System::Call "shell32::SHChangeNotify(i,i,i,i) (${SHCNE_ASSOCCHANGED}, ${SHCNF_FLUSH}, 0, 0)"
!macroend

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "Blyte"
!define PRODUCT_VERSION "1.5.0"
!define PRODUCT_PUBLISHER "Oskusoft"
!define PRODUCT_WEB_SITE "http://www.oskusoft.com"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\blyte.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor lzma

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!define MUI_FINISHPAGE_RUN "$INSTDIR\blyte.exe"
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "English"

; Reserve files
!insertmacro MUI_RESERVEFILE_INSTALLOPTIONS

; MUI end ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "Setup-${PRODUCT_NAME}-${PRODUCT_VERSION}.exe"
InstallDir "C:\Program Files\Oskusoft\Blyte"
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

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite on
  File "dist\*"
  CreateDirectory "$SMPROGRAMS\Blyte"
  CreateShortCut "$SMPROGRAMS\Blyte\Blyte.lnk" "$INSTDIR\blyte.exe"
  CreateShortCut "$DESKTOP\Blyte.lnk" "$INSTDIR\blyte.exe"
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\Blyte\Manual.lnk" "$INSTDIR\manual.pdf"
  CreateShortCut "$SMPROGRAMS\Blyte\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\Blyte\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\blyte.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\blyte.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"

  ; file associations
  WriteRegStr HKCR ".blyte" "" "Blyte.Screenplay"
  WriteRegStr HKCR "Blyte.Screenplay" "" "Blyte Screenplay"
  WriteRegStr HKCR "Blyte.Screenplay\DefaultIcon" "" "$INSTDIR\blyte.exe,0"
  WriteRegStr HKCR "Blyte.Screenplay\shell" "" "open"
  WriteRegStr HKCR "Blyte.Screenplay\shell\open\command" "" '"$INSTDIR\blyte.exe" "%1"'

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
  Delete "$INSTDIR\blyte.exe"
  Delete "$INSTDIR\datetime.pyd"
  Delete "$INSTDIR\pyexpat.pyd"
  Delete "$INSTDIR\htmlc.pyd"
  Delete "$INSTDIR\icon16.png"
  Delete "$INSTDIR\icon32.png"
  Delete "$INSTDIR\logo.jpg"
  Delete "$INSTDIR\names.dat"
  Delete "$INSTDIR\dict_en.dat.gz"
  Delete "$INSTDIR\python23.dll"
  Delete "$INSTDIR\unicodedata.pyd"
  Delete "$INSTDIR\w9xpopen.exe"
  Delete "$INSTDIR\wxc2.pyd"
  Delete "$INSTDIR\wxc.pyd"
  Delete "$INSTDIR\wxmsw24h.dll"
  Delete "$INSTDIR\sample.blyte"
  Delete "$INSTDIR\_socket.pyd"
  Delete "$INSTDIR\_ssl.pyd"
  Delete "$INSTDIR\_winreg.pyd"
  Delete "$INSTDIR\manual.pdf"
  Delete "$INSTDIR\fileformat.txt"
  Delete "$INSTDIR\LICENSE"

  Delete "$SMPROGRAMS\Blyte\Uninstall.lnk"
  Delete "$SMPROGRAMS\Blyte\Website.lnk"
  Delete "$DESKTOP\Blyte.lnk"
  Delete "$SMPROGRAMS\Blyte\Blyte.lnk"
  Delete "$SMPROGRAMS\Blyte\Manual.lnk"

  RMDir "$SMPROGRAMS\Blyte"
  RMDir "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  DeleteRegKey HKCR ".blyte"
  DeleteRegKey HKCR "Blyte.Screenplay\DefaultIcon"
  DeleteRegKey HKCR "Blyte.Screenplay\shell"
  DeleteRegKey HKCR "Blyte.Screenplay\shell\open\command"
  DeleteRegKey HKCR "Blyte.Screenplay"

 !insertmacro UPDATEFILEASSOC

  SetAutoClose true
SectionEnd
