# setup.py
from distutils.core import setup
import py2exe

includes = [
    "encodings",
    "encodings.*"
    ]

manifest_template = '''
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="5.0.0.0"
    processorArchitecture="x86"
    name="%(prog)s"
    type="win32"
/>
<description>%(prog)s Program</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
'''

RT_MANIFEST = 24

options = {
    "py2exe":
    {
    "compressed": 1,
    "optimize": 2,
    "includes": includes,
    }
    }

target = { "script" : "blyte.py",
           "icon_resources": [(1, "icon32.ico")],
           "other_resources" : [(RT_MANIFEST, 1,
                                 manifest_template % dict(prog="blyte"))]
           }

setup(options = options, zipfile="wxc2.pyd", windows=[target])
