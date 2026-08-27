# -*- coding: utf-8 -*-

"""Test importing script formats."""

from __future__ import annotations

from unittest import mock
from pathlib import Path

import wx

from trelby import translations
from trelby import screenplay
from trelby.line import Line
from trelby import myimport

from tests import u


_ = translations.trelby_translations_load()


def test_importing_celtx() -> None:
    """Test importing a Celtx script."""
    u.init()
    location = Path(__file__).parent
    path_to_test_script_celtx = Path(location, "fixtures/test.celtx")

    imported_lines = myimport.importCeltx(
        path_to_test_script_celtx, mock.Mock()
    )

    assert imported_lines is not None

    # in order to compare the screenplays,
    # we need to reformat it with the same configuration as the loaded one
    imported_screenplay = u.new()
    imported_screenplay.lines = imported_lines
    imported_screenplay.reformatAll()

    expected_screenplay = u.load()

    for (
            line, expected_line
    ) in zip(imported_screenplay.lines, expected_screenplay.lines):
        assert line == expected_line


def test_importing_text_file() -> None:
    """Test importing a text file as a script."""
    mocked_dialog = mock.MagicMock(spec=wx.Dialog)
    mocked_dialog.ShowModal.return_value = wx.ID_OK

    with mock.patch('trelby.myimport.ImportDlg', return_value=mocked_dialog):

        u.init()
        location = Path(__file__).parent
        path_to_test_script_txt = Path(location, "fixtures/test.txt")

        lines = myimport.importTextFile(
            path_to_test_script_txt, mock.Mock()
        )

        expected_screenplay = u.load()
        for line, expected_line in zip(lines, expected_screenplay.lines):
            assert TextImportMatcher(line) == TextImportMatcher(expected_line)


class TextImportMatcher:

    """Matcher for imported text."""

    def __init__(self, line: Line) -> None:
        """Create new instance.

        Args:
            line: line to compare.

        """
        self.line: Line = line

    def __eq__(self, other: TextImportMatcher) -> bool | NotImplemented:
        """Compare one line.

        Args:
            other: other instance containing a line to be compared.

        The text import has some known limitations:
        *   depending on the export config, some lines are all caps,
            so it can't reliably preserve case;
        *   it can't reliably detect linebreak types;
        *   sometimes, it can't distinguish ACTION from SCENE types.

        That's why this implementation is not so hard on it,
        and only compares the text case-insensitively,
        doesn't compare linebreak types at all and only compares the line type
        if it's not ACTION or SCENE.

        Returns:
            True if lines are equal. Otherwise, False.

        """
        if not isinstance(other, TextImportMatcher):
            return NotImplemented

        if self.line.text.lower() != other.line.text.lower():
            return False
        if (
            self.line.lt != screenplay.ACTION
            and self.line.lt != screenplay.SCENE
            and self.line.lt != other.line.lt
        ):
            return False
        return True

    def __repr__(self) -> str:
        """Get the representational string.

        Returns:
            Representational string.

        """
        return self.line.__str__()
