@ECHO OFF

CD /D "%~dp0"

SET PYTHONPATH="bin;src"

python3 bin\trelby
