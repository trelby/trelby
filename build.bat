python -OO setup.py py2exe
xcopy /i resources dist\resources
copy vcredist_x86.exe dist
copy names.txt.gz dist
copy sample.blyte dist
copy manual.html dist
copy fileformat.txt dist
copy LICENSE dist
copy dict_en.dat.gz dist
