from setuptools import setup
import os

APP = ["trelby.py"]
DATA_FILES = [
    ("trelby", ["trelby/dict_en.dat.gz", "trelby/names.txt.gz", "trelby/manual.html", "trelby/sample.trelby"]),
    ("trelby/resources", [f"trelby/resources/{f}" for f in os.listdir("trelby/resources") if os.path.isfile(f"trelby/resources/{f}")]),
]

OPTIONS = {
    "argv_emulation": True,
    "iconfile": "resources_mac/icon.icns",
    "site_packages": True,
    "includes": ["wx", "lxml", "reportlab"],
    "excludes": ["tkinter"],
    "strip": False,
    "optimize": 2,
    "plist": {
        "CFBundleName": "Trelby",
        "CFBundleDisplayName": "Trelby",
        "CFBundleIdentifier": "org.trelby.trelby",
        "CFBundleVersion": "2.4.16.2",
        "CFBundleShortVersionString": "2.4.16.2",
        "CFBundleGetInfoString": "Trelby 2.4.16.2 - Free, multiplatform, feature-rich screenwriting program",
        "CFBundleExecutable": "Trelby",
        "CFBundleIconFile": "icon.icns",
        "NSHumanReadableCopyright": "Copyright © 2023 Trelby Team. Licensed under GPL-3.0-or-later.",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.14",
        "LSApplicationCategoryType": "public.app-category.productivity",
        "NSRequiresAquaSystemAppearance": False,
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Trelby Screenplay",
                "CFBundleTypeExtensions": ["trelby"],
                "CFBundleTypeRole": "Editor",
                "CFBundleTypeIconFile": "icon.icns"
            }
        ]
    },
    "packages": ["wx", "lxml", "reportlab"],
    "site_packages": True,
}

setup(
    name="Trelby",
    version="2.4.16.2",
    description="Free, multiplatform, feature-rich screenwriting program",
    author="Osku Salerma",
    url="https://www.trelby.org",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
