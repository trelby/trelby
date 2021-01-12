rd /s /q dist
rename setup.cfg setup.cfg.bak
python3 -OO setup.py py2exe
rename setup.cfg.bak setup.cfg
python3 setup.py nsis
