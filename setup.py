# setup.py
from distutils.command.build_scripts import build_scripts as _build_scripts
from distutils.command.bdist_rpm import bdist_rpm as _bdist_rpm
from distutils.command.install_data import install_data as _install_data
from distutils.core import Command
from distutils.core import setup
from distutils.util import convert_path

import fileinput
import glob
import subprocess
import sys
import os.path

class build_scripts(_build_scripts):
    """build_scripts command

    This specific build_scripts command will modify the bin/trelby script
    so that it contains information on installation prefixes afterwards.
    """

    def copy_scripts(self):
        _build_scripts.copy_scripts(self)

        if "install" in self.distribution.command_obj:
            iobj = self.distribution.command_obj["install"]
            libDir = iobj.install_lib

            if iobj.root:
                libDir = libDir[len(iobj.root):]

            script = convert_path("bin/trelby")
            outfile = os.path.join(self.build_dir, os.path.basename(script))

            in_file = open(script, "rt")
            text = in_file.read()
            text = text.replace('src', libDir + 'src')
            in_file.close()
            out_file = open(outfile, "wt")
            out_file.write(text)
            out_file.close()

class bdist_rpm(_bdist_rpm):
    """bdist_rpm command

    This specific bdist_rpm command generates an RPM package that
    will install to /usr/share/trelby and /usr/bin, respectively.
    """
    def _make_spec_file(self):
        specFile = _bdist_rpm._make_spec_file(self)
        line = next(i for i, s in enumerate(specFile) if s.startswith("%install"))
        specFile[line+1] += " --prefix=/usr --install-data=/usr/share --install-lib /usr/share/trelby"
        return specFile

class install_data(_install_data):
    """install_data command

    This specific install_data command only really installs trelby.desktop
    and trelby's manpage if the target path is either /usr or /usr/local,
    or trelby's own data files if we're under Windows.
    """

    def run(self):
        dataDir = self.install_dir

        if self.root:
            dataDir = dataDir[len(self.root):]

        if (dataDir.rstrip("/") in ("/usr/share", "/usr/local/share")) \
        or (sys.platform == "win32"):
            _install_data.run(self)

class nsis(Command):
    """ nsis command
    Under Windows, call this command after the py2exe command to invoke NSIS
    to produce a Windows installer.
    """
    description = "Invoke NSIS to produce a Windows installer."
    user_options = [
        ("nsis-file=", "f",
         "NSIS file to process [default: install.nsi]"),
    ]

    def initialize_options(self):
        self.nsis_file = "install.nsi"

    def finalize_options(self):
        pass

    def executeNSIS(self, nsisCmd, nsisScript):
        subProc = subprocess.Popen([nsisCmd, nsisScript], env=os.environ)
        subProc.communicate()

        retCode = subProc.returncode

        if retCode:
            raise RuntimeError("NSIS compilation return code: %d" % retCode)

    def run(self):

        try:
            import winreg
            regPathKey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Software\NSIS")
            regPathValue, regPathType = winreg.QueryValueEx(regPathKey, "")

            if regPathType != winreg.REG_SZ:
                raise TypeError
        except:
            raise Exception("There was an error reading the registry key for NSIS.\n"
                            "You may need to reinstall NSIS to fix this error.")

        self.executeNSIS(os.path.join(regPathValue, "makensis.exe"), self.nsis_file)

sys.path.append(os.path.join(os.path.split(__file__)[0], "src"))
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


packageData = {"src": ["../resources/*",
      "../names.txt.gz",
      "../dict_en.dat.gz",
      "../sample.trelby",
      "../fileformat.txt",
      "../manual.html",
      "../README",
]}
dataFiles = []

if sys.platform == "win32":
    import py2exe

    # Distutils' package_data argument doesn't work with py2exe.
    # On the other hand, we don't need the data_files argument
    # (which we're only using under Linux for stuff like our .desktop file and
    # man page that go to system directories), so we'll just use it instead
    # of package_data.
    for path, files in packageData.items():
        for file in files:
            dataFile = os.path.normpath(os.path.join(path, file))
            dataFiles.append((os.path.dirname(dataFile),glob.glob(dataFile)))
    packageData = {}

    platformOptions = dict(
        zipfile = "library.zip",

        windows = [{
                "script" : "bin/trelby",
                "icon_resources": [(1, "icon32.ico")],
           }]
        )
else:
    dataFiles = [
        ("applications", ["trelby.desktop"]),
        ("man/man1", ["doc/trelby.1.gz"]),
        ]
    platformOptions = {}

setup(
    name = "Trelby",
    cmdclass = {
        "build_scripts": build_scripts,
        "bdist_rpm": bdist_rpm,
        "install_data": install_data,
        "nsis": nsis,
    },
    version = misc.version,
    description = "Free, multiplatform, feature-rich screenwriting program",

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
      author = "Osku Salerma",
      author_email = "osku.salerma@gmail.com",
      url = "http://www.trelby.org/",
      license = "GPL",
      packages = ["src"],
      package_data = packageData,
      data_files = dataFiles,
      scripts = ["bin/trelby"],
      options = options,
      **platformOptions)
