import sys
import os
from typing import Union

import screenplay
import u

from unittest import mock

wxMock = mock.Mock()
wxMock.ID_OK = 1
wxMock.Dialog.ShowModal.return_value = wxMock.ID_OK

sys.modules['wx'] = wxMock

import myimport

def testImportCeltx()->None:
    u.init()
    location = os.path.dirname(__file__)
    pathToTestScriptCeltx = os.path.join(location, "fixtures/test.celtx")

    importedLines = myimport.importCeltx(pathToTestScriptCeltx,mock.Mock())

    assert importedLines is not None

    # in order to compare the screenplays, we need to reformat it with the same configuration as the loaded one
    importedScreenplay = u.new()
    importedScreenplay.lines = importedLines
    importedScreenplay.reformatAll()

    expectedScreenplay = u.load()

    for line, expectedLine in zip(importedScreenplay.lines, expectedScreenplay.lines):
        assert line == expectedLine

def testImportTextFile()->None:
    u.init()
    location = os.path.dirname(__file__)
    pathToTestScriptTxt = os.path.join(location, "fixtures/test.txt")

    lines = myimport.importTextFile(pathToTestScriptTxt,mock.Mock())

    expectedScreenplay = u.load()
    for line, expectedLine in zip(lines, expectedScreenplay.lines):
        assert TextImportMatcher(line) == TextImportMatcher(expectedLine)

class TextImportMatcher:
    line: screenplay.Line
    def __init__(self, line: screenplay.Line):
        self.line = line

    def __eq__(self, other):
        """
        The text import has some known limitations:
            - depending on the export config, some lines are all caps, so it can't reliably preserve case
            - it can't reliably detect linebreak types
            - sometimes, it can't distinguish ACTION from SCENE types
        That's why this implementation is not so hard on it, and only compares the text case-insensitively, doesn't
        compare linebreak types at all and only compares the line type if it's not ACTION or SCENE
        """
        if not isinstance(other, TextImportMatcher):
            return NotImplemented
        if self.line.text.lower() != other.line.text.lower():
            return False
        if self.line.lt != screenplay.ACTION and self.line.lt != screenplay.SCENE and self.line.lt != other.line.lt:
            return False
        return True

    def __repr__(self)->str:
        return self.line.__str__()
