import sys
import os
import u

from unittest import mock

wxMock = mock.Mock()
wxMock.ID_OK = 1
wxMock.Dialog.ShowModal.return_value = wxMock.ID_OK

sys.modules['wx'] = wxMock

import myimport



def testImportTextFile()->None:
    u.init()
    location = os.path.dirname(__file__)
    pathToTestScriptTxt = os.path.join(location, "fixtures/test-script.txt")

    lines = myimport.importTextFile(pathToTestScriptTxt,mock.Mock())

    expectedScreenplay = u.load()
    for line, expectedLine in zip(lines, expectedScreenplay.lines):
        assert line == expectedLine
