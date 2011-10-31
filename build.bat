python -OO setup.py py2exe
xcopy /i icons dist\icons
copy vcredist_x86.exe dist
copy names.dat dist
copy sample.blyte dist
copy manual.pdf dist
copy fileformat.txt dist
copy LICENSE dist
copy dict_en.dat.gz dist
