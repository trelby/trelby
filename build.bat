rd /s /q winbuild
rd /s /q dist
mkdir winbuild\dist

xcopy /i src\* winbuild
xcopy /i nsis.bat winbuild
xcopy /i install.nsi winbuild
xcopy /i icon32.ico winbuild
xcopy /i setup.py winbuild
xcopy /i vcredist_x86.exe winbuild

xcopy /i names.txt.gz winbuild\dist
xcopy /i sample.trelby winbuild\dist
xcopy /i manual.html winbuild\dist
xcopy /i fileformat.txt winbuild\dist
xcopy /i LICENSE winbuild\dist
xcopy /i dict_en.dat.gz winbuild\dist

xcopy /i /y resources winbuild\dist\resources

cd winbuild
python -OO setup.py py2exe
call nsis.bat
move /y setup*.exe .. 
move /y dist ..\dist

cd ..
