# setup.py
from distutils.command.build_scripts import build_scripts as _build_scripts
from distutils.core import setup
from distutils.util import convert_path

import fileinput
import glob
import sys
import os.path

class build_scripts(_build_scripts):
    """build_scripts command

    This specific build_scripts command will modify the bin/trelby
    script so that it contains information on installation prefixes afterwards.
    """

    def copy_scripts (self):
        _build_scripts.copy_scripts(self)

        if ("install" in self.distribution.command_obj):
            iobj = self.distribution.command_obj["install"]
            lib_dir = iobj.install_lib
            if (iobj.root):
                lib_dir = lib_dir[len(iobj.root):]

            script = convert_path("bin/trelby")
            outfile = os.path.join(self.build_dir, os.path.basename(script))

            # Abuse fileinput to replace a line in bin/trelby
            for line in fileinput.input(outfile, inplace=1):
                if "sys.path.insert(0, \"src\")" in line:
                    line = "sys.path.insert(0, \"" + lib_dir + "src\")"
                print line,

sys.path.append(os.path.join(os.path.split(__file__)[0],"src"))
import misc

includes = [
    "encodings",
    "encodings.*",
    "lxml._elementpath"
]

options = {
    "py2exe": {
        "compressed": 1,
        "optimize": 2,
        "includes": includes,
    }
}

if sys.platform == "win32":
    import py2exe
    platform_options = dict(
        zipfile="library.zip",
        windows=[{ "script" : "bin/trelby",
           "icon_resources": [(1, "icon32.ico")],
           }]
    )
else:
    platform_options = dict()

data_files = [("resources", glob.glob(os.path.join("resources", "*.*"))),
              ("", ["names.txt.gz",
                    "dict_en.dat.gz",
                    "sample.trelby",
                    "fileformat.txt",
                    "manual.html",
                    "README"])]

setup(name="Trelby",
      cmdclass={"build_scripts": build_scripts},
      version=misc.version,
      description="Free, multiplatform, feature-rich screenwriting program",
      long_description = """\
Trelby is a simple, powerful, full-featured, multi-platform program for
writing movie screenplays. It is simple, fast and elegantly laid out to
make screenwriting simple, and it is infinitely configurable.

Features:

 * Screenplay editor: Enforces correct script format and pagination,
   auto-completion, and spell checking.
 * Multiplatform: Behaves identically on all platforms, generating the exact
   same output.
 * Choice of view: Multiple views, including draft view, WYSIWYG mode,
   and fullscreen to suit your writing style.
 * Name database: Character name database containing over 200,000 names
   from various countries.
 * Reporting: Scene/location/character/dialogue reports.
 * Compare: Ability to compare scripts, so you know what changed between
   versions.
 * Import: Screenplay formatted text, Final Draft XML (.fdx)
    and Celtx (.celtx).
 * Export: PDF, formatted text, HTML, RTF, Final Draft XML (.fdx).
 * PDF: Built-in, highly configurable PDF generator. Supports embedding your
   chosen font. Also supports generating PDFs with custom watermarks,
   to help track shared files.
 * Free software: Licensed under the GPL, Trelby welcomes developers and
   screenwriters to contribute in making it more useful.
""",
      author="Osku Salerma",
      author_email="osku.salerma@gmail.com",
      url="http://www.trelby.org/",
      license = "GPL",
      packages=["src"],
      data_files=data_files,
      scripts=["bin/trelby"],
      options=options,
      **platform_options)
