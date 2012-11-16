rd /s /q dist
rename setup.cfg setup.cfg.bak
python -OO setup.py py2exe
rename setup.cfg.bak setup.cfg
python setup.py nsis
