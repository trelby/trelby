#!/bin/bash
rm -rf dist
mv setup.cfg setup.cfg.tmp
python3 setup.py py2app
mv setup.cfg.tmp setup.cfg

