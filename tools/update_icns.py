#!/usr/bin/env python
import icnsutil
import glob
import os

IN_DIR = "../resources"
OUT_DIR = "../resources_mac"

img = icnsutil.IcnsFile()
for name in glob.glob(os.path.join(IN_DIR, "icon*.png")):
    try:
        img.add_media(file=name)
    except icnsutil.IcnsType.CanNotDetermine:
        print(f"Skipping {name}")
img.write(os.path.join(OUT_DIR, "icon.icns"))

