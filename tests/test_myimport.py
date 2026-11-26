import os
import sys
from typing import Union
from unittest import mock

import pytest

import tests.u as u
import trelby.screenplay as screenplay
from trelby.line import Line

wxMock = mock.Mock()
wxMock.ID_OK = 1
wxMock.Dialog.ShowModal.return_value = wxMock.ID_OK

sys.modules["wx"] = wxMock

import trelby.myimport as myimport


def testImportCeltx() -> None:
    u.init()
    location = os.path.dirname(__file__)
    pathToTestScriptCeltx = os.path.join(location, "fixtures/test.celtx")

    importedLines = myimport.importCeltx(pathToTestScriptCeltx, mock.Mock())

    assert importedLines is not None

    # in order to compare the screenplays, we need to reformat it with the same configuration as the loaded one
    importedScreenplay = u.new()
    importedScreenplay.lines = importedLines
    importedScreenplay.reformatAll()

    expectedScreenplay = u.load()

    for line, expectedLine in zip(importedScreenplay.lines, expectedScreenplay.lines):
        assert line == expectedLine


def testImportTextFile() -> None:
    u.init()
    location = os.path.dirname(__file__)
    pathToTestScriptTxt = os.path.join(location, "fixtures/test.txt")

    lines = myimport.importTextFile(pathToTestScriptTxt, mock.Mock())

    expectedScreenplay = u.load()
    for line, expectedLine in zip(lines, expectedScreenplay.lines):
        assert TextImportMatcher(line) == TextImportMatcher(expectedLine)


class TextImportMatcher:
    line: Line

    def __init__(self, line: Line):
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
        if (
            self.line.lt != screenplay.ACTION
            and self.line.lt != screenplay.SCENE
            and self.line.lt != other.line.lt
        ):
            return False
        return True

    def __repr__(self) -> str:
        return self.line.__str__()


@pytest.fixture(autouse=True)
def gettext():
    """Messages from the importers go through _(), which the app installs."""
    with mock.patch("builtins._", lambda s: s, create=True):
        yield


def analyzeFixture(name: str) -> list:
    with open(u.fixtureFilePath(name), encoding="UTF-8") as f:
        rows, layout = myimport.analyzeText(f.read())
    return rows


def importTextFixture(name: str) -> list:
    """Import a fixture, accepting everything the review dialog shows."""
    u.init()
    with mock.patch.object(myimport, "TextImportReviewDlg") as dlg:
        dlg.return_value.ShowModal.return_value = wxMock.ID_OK
        lines = myimport.importTextFile(u.fixtureFilePath(name), mock.Mock())

    return [(line.lt, line.text) for line in mergeElements(lines)]


def mergeElements(lines: list) -> list:
    """Join lines into whole elements, so tests don't depend on wrapping.
    Forced line breaks are kept as newlines."""
    ret = []
    sep = None
    for line in lines:
        if sep is not None:
            ret[-1] = Line(line.lb, line.lt, ret[-1].text + sep + line.text)
        else:
            ret.append(Line(line.lb, line.lt, line.text))
        sep = {screenplay.LB_SPACE: " ", screenplay.LB_FORCED: "\n"}.get(line.lb)
    return ret


def flagged(rows: list) -> list:
    return [r.text for r in rows if r is not None and r.flag]


def removed(rows: list) -> list:
    return [r.text for r in rows if r is not None and r.lt == myimport.REMOVE]


def testImportTextFromPdfWithSceneNumbers() -> None:
    """Scene numbers in the margin must not make action lines look like
    character names, and page break clutter is proposed for removal."""
    sc = screenplay
    assert importTextFixture("import-pdf-layout.txt") == [
        (sc.ACTION, "FADE IN:"),
        (sc.SCENE, "EXT. LIGHTHOUSE - NIGHT"),
        (
            sc.ACTION,
            "Waves hammer the rocks below. A single lamp turns slowly at the top of the tower.",
        ),
        (
            sc.ACTION,
            "MARGARET (60s, weathered) climbs the spiral stairs, lantern in hand. She stops at a window and stares out to sea.",
        ),
        (sc.CHARACTER, "MARGARET"),
        (sc.DIALOGUE, "Not tonight. Please, not tonight."),
        (sc.ACTION, "A distant HORN sounds. She freezes."),
        (sc.CHARACTER, "THOMAS (O.S.)"),
        (sc.DIALOGUE, "Mother? Is that the ship?"),
        (sc.CHARACTER, "MARGARET"),
        (sc.PAREN, "(without turning)"),
        (sc.DIALOGUE, "Go back to bed, Thomas."),
        (sc.SCENE, "INT. LIGHTHOUSE - KEEPER'S ROOM - CONTINUOUS"),
        (
            sc.ACTION,
            "Thomas, 12, sits up in a narrow cot. He pulls on his boots anyway.",
        ),
        (sc.CHARACTER, "THOMAS"),
        (
            sc.DIALOGUE,
            "I can see the lights from here. There are three of them, and they're coming closer every minute. You told me the ships never come this far north.",
        ),
        (sc.ACTION, "He runs to the door."),
        (sc.TRANSITION, "CUT TO:"),
        (sc.SCENE, "EXT. ROCKS - NIGHT"),
        (sc.ACTION, "The ship's hull splits open on the reef. Men scream."),
        (sc.TRANSITION, "FADE OUT."),
    ]


def testPdfLayoutFlagsAndRemovals() -> None:
    rows = analyzeFixture("import-pdf-layout.txt")

    # FADE IN: is at a column no element type uses
    assert flagged(rows) == ["FADE IN:"]

    assert removed(rows) == [
        "1.",
        "(MORE)",
        "2.",
        "CONTINUED:                                  2",
        "THOMAS (CONT'D)",
    ]
    assert [r.text for r in rows if r is not None and r.cleanText is not None] == [
        "1    EXT. LIGHTHOUSE - NIGHT                                          1",
        "2    INT. LIGHTHOUSE - KEEPER'S ROOM - CONTINUOUS                     2",
        "3    EXT. ROCKS - NIGHT                                               3",
    ]


def testReviewChangesAreApplied() -> None:
    """What the user changes in the review is what gets imported."""
    rows = analyzeFixture("import-pdf-layout.txt")
    byText = {r.text: r for r in rows if r is not None}

    byText[
        "1    EXT. LIGHTHOUSE - NIGHT                                          1"
    ].keepText = True
    byText["FADE IN:"].setType(screenplay.TRANSITION)
    # keep the repeated name: the speech is then not joined across the page
    byText["THOMAS (CONT'D)"].setType(screenplay.CHARACTER)

    assert byText["FADE IN:"].checked
    assert not byText["FADE IN:"].needsReview()

    lines = [(ln.lt, ln.text) for ln in mergeElements(myimport.rowsToLines(rows))]

    assert lines[0] == (screenplay.TRANSITION, "FADE IN:")
    assert lines[1] == (
        screenplay.SCENE,
        "1    EXT. LIGHTHOUSE - NIGHT                                          1",
    )
    i = lines.index((screenplay.CHARACTER, "THOMAS (CONT'D)"))
    assert lines[i - 1][0] == screenplay.DIALOGUE
    assert lines[i + 1] == (screenplay.DIALOGUE, "ships never come this far north.")


def testIndentedTextFlagsWhatRulesCantSettle() -> None:
    rows, layout = myimport.analyzeText(
        "INT. KITCHEN - DAY\n"
        "\n"
        "Pots boil over.\n"
        "\n"
        "                              AL\n"
        "               Who left the stove on?\n"
        "\n"
        "                            BEATRICE\n"
        "               Not me.\n"
        "\n"
        "                              AL\n"
        "               Somebody did.\n"
    )

    assert "character names at column 30" in layout
    types = [(r.lt, r.text, bool(r.flag)) for r in rows if r is not None]
    assert types == [
        (screenplay.SCENE, "INT. KITCHEN - DAY", False),
        (screenplay.ACTION, "Pots boil over.", False),
        (screenplay.CHARACTER, "AL", False),
        (screenplay.DIALOGUE, "Who left the stove on?", False),
        # name off the character column: proposed as speech, but flagged
        (screenplay.CHARACTER, "BEATRICE", True),
        (screenplay.DIALOGUE, "Not me.", True),
        (screenplay.CHARACTER, "AL", False),
        (screenplay.DIALOGUE, "Somebody did.", False),
    ]


def testImportTextWithoutIndentation() -> None:
    """Text copied out of a PDF often loses all indentation."""
    sc = screenplay
    assert importTextFixture("import-no-indent.txt") == [
        (sc.SCENE, "EXT. DESERT HIGHWAY - DAY"),
        (sc.ACTION, "Heat shimmer. A lone car approaches."),
        (sc.SCENE, "INT. CAR - CONTINUOUS"),
        (sc.ACTION, "MIKE (40s) drives. LUCY (30s) reads a map upside down."),
        (sc.CHARACTER, "MIKE"),
        (sc.DIALOGUE, "Are we lost?"),
        (sc.CHARACTER, "LUCY"),
        (sc.PAREN, "(turning the map)"),
        (sc.DIALOGUE, "We're not lost. We're exploring."),
        (sc.CHARACTER, "MIKE"),
        (sc.DIALOGUE, "That's what you said in Ohio."),
        (sc.ACTION, "BANG! A tire blows."),
        (sc.ACTION, "The car skids to the shoulder."),
        (sc.TRANSITION, "CUT TO:"),
        (sc.SCENE, "EXT. DESERT HIGHWAY - LATER"),
        (sc.ACTION, "Mike kicks the flat tire."),
        (sc.CHARACTER, "MIKE"),
        (sc.DIALOGUE, "Exploring."),
    ]
    assert flagged(analyzeFixture("import-no-indent.txt")) == []


def testUnindentedUncertainSpeechIsFlagged() -> None:
    rows, layout = myimport.analyzeText(
        "INT. HALL - DAY\n"
        "\n"
        "THE LIGHTS GO OUT\n"
        "Everyone screams.\n"
        "\n"
        "SILENCE FALLS.\n"
        "Then a match is struck.\n"
    )

    assert "read from the text alone" in layout
    assert [(r.lt, r.text, bool(r.flag)) for r in rows if r is not None] == [
        (screenplay.SCENE, "INT. HALL - DAY", False),
        # one-off upper case line followed by text: speech or action?
        (screenplay.CHARACTER, "THE LIGHTS GO OUT", True),
        (screenplay.DIALOGUE, "Everyone screams.", True),
        (screenplay.ACTION, "SILENCE FALLS.", True),
        (screenplay.ACTION, "Then a match is struck.", True),
    ]


def testImportTextWindowsEncoding(tmp_path) -> None:
    path = tmp_path / "script.txt"
    path.write_bytes(
        "INT. CAF\u00c9 - NIGHT\n\n          REN\u00c9E\n     Bonjour.\n".encode(
            "cp1252"
        )
    )
    u.init()
    with mock.patch.object(myimport, "TextImportReviewDlg") as dlg:
        dlg.return_value.ShowModal.return_value = wxMock.ID_OK
        lines = myimport.importTextFile(str(path), mock.Mock())

    assert [(line.lt, line.text) for line in lines] == [
        (screenplay.SCENE, "INT. CAF\u00c9 - NIGHT"),
        (screenplay.CHARACTER, "REN\u00c9E"),
        (screenplay.DIALOGUE, "Bonjour."),
    ]


def testImportTextCancelled() -> None:
    u.init()
    with mock.patch.object(myimport, "TextImportReviewDlg") as dlg:
        dlg.return_value.ShowModal.return_value = wxMock.ID_CANCEL
        lines = myimport.importTextFile(
            u.fixtureFilePath("import-pdf-layout.txt"), mock.Mock()
        )

    assert lines is None


class FakeReviewDlg:
    """Stands in for TextImportReviewDlg. review(rows) plays the user's
    part; returning False cancels."""

    def __init__(self, review=None):
        self.review = review
        self.rows = None

    def __call__(self, parent, rows, layout, remove):
        self.rows = rows
        return self

    def ShowModal(self):
        if self.review and self.review(self.rows) is False:
            return wxMock.ID_CANCEL
        return wxMock.ID_OK

    def Destroy(self):
        pass


def importFountainFixture(
    name: str, removeMarkup: bool = True, review: FakeReviewDlg = None
) -> tuple:
    sp = u.new()
    sp.titles.addDefaults()
    frame = mock.Mock()
    frame.panel.ctrl.sp.cfg.getType.return_value.width = 60

    def dialog(parent, title, items, label, other):
        items[2].selected = removeMarkup
        ret = mock.Mock()
        ret.ShowModal.return_value = wxMock.ID_OK
        return ret

    with mock.patch.object(myimport.misc, "CheckBoxDlg", dialog), mock.patch.object(
        myimport, "TextImportReviewDlg", review or FakeReviewDlg()
    ):
        lines, titlePages = myimport.importFountain(
            u.fixtureFilePath(name), frame, sp.titles.pages
        )

    if lines is None:
        return None, titlePages

    return [(line.lt, line.text) for line in mergeElements(lines)], titlePages


def testImportFountain() -> None:
    lines, titlePages = importFountainFixture("import.fountain")

    sc = screenplay
    assert lines == [
        (sc.SCENE, "EXT. BEACH - DAY"),
        (sc.ACTION, "BOOM!"),
        (sc.ACTION, "The sky splits open."),
        (sc.CHARACTER, "MARY (cont'd)"),
        (sc.DIALOGUE, "Did you hear that?"),
        (sc.CHARACTER, "McCLANE"),
        (sc.PAREN, "(smiling)"),
        (sc.DIALOGUE, "Yippee ki-yay."),
        (sc.ACTION, "THE CROWD CHEERS\nThey throw hats."),
        (sc.CHARACTER, "BOB"),
        (sc.DIALOGUE, "I'm here too."),
        (sc.ACTION, "Int. house at night\nis where it happens."),
        (sc.ACTION, "...and then"),
        (sc.SCENE, "FLASHBACK"),
        (sc.ACTION, "THE END"),
    ]
    assert titlePages[0][0].items == ["Lights: A Story"]
    assert titlePages[0][1].items == ["by", "", "Somebody"]


def testImportFountainKeepsMarkupWhenAsked() -> None:
    lines, titlePages = importFountainFixture("import.fountain", removeMarkup=False)

    assert (screenplay.SCENE, "EXT. BEACH - DAY #1#") in lines
    assert (screenplay.CHARACTER, "BOB ^") in lines


def testFountainSlipsAreFlagged() -> None:
    review = FakeReviewDlg()
    lines, titlePages = importFountainFixture("import-slips.fountain", review=review)

    flags = [(r.lineNo, r.text) for r in review.rows if r is not None and r.flag]
    # line numbers are the file's, even with a multi-line /* */ before them
    assert flags == [
        (6, "EXT. BEACH - DAY"),
        (7, "Waves crash."),
        (13, "BOOM!"),
        (14, "The window shatters."),
        (17, "(rubbing her eyes and"),
        (18, "yawning)"),
        (20, "CUT TO:"),
    ]

    # accepted as is, the Fountain rules stand
    sc = screenplay
    assert lines[:2] == [
        (sc.CHARACTER, "EXT. BEACH - DAY"),
        (sc.DIALOGUE, "Waves crash."),
    ]


def testFountainReviewChangesAreApplied() -> None:
    def review(rows):
        byText = {r.text: r for r in rows if r is not None}
        byText["EXT. BEACH - DAY"].setType(screenplay.SCENE)
        byText["Waves crash."].setType(screenplay.ACTION)
        byText["CUT TO:"].setType(myimport.REMOVE)

    lines, titlePages = importFountainFixture(
        "import-slips.fountain", review=FakeReviewDlg(review)
    )

    sc = screenplay
    assert lines[:2] == [
        (sc.SCENE, "EXT. BEACH - DAY"),
        (sc.ACTION, "Waves crash."),
    ]
    assert not any(text == "CUT TO:" for lt, text in lines)


def testFountainReviewCancelLeavesTitlesAlone() -> None:
    sp = u.new()
    sp.titles.addDefaults()
    before = [t.items for t in sp.titles.pages[0]]

    def dialog(parent, title, items, label, other):
        ret = mock.Mock()
        ret.ShowModal.return_value = wxMock.ID_OK
        return ret

    with mock.patch.object(myimport.misc, "CheckBoxDlg", dialog), mock.patch.object(
        myimport, "TextImportReviewDlg", FakeReviewDlg(lambda rows: False)
    ):
        lines, titlePages = myimport.importFountain(
            u.fixtureFilePath("import-slips.fountain"), mock.Mock(), sp.titles.pages
        )

    assert lines is None
    assert [t.items for t in sp.titles.pages[0]] == before


def testFountainWithoutSlipsSkipsReview(tmp_path) -> None:
    path = tmp_path / "clean.fountain"
    path.write_text("INT. HOUSE - DAY\n\nJOE\n(quietly)\nHello.\n\nCUT TO:\n\n")
    review = FakeReviewDlg()

    with mock.patch.object(u, "fixtureFilePath", lambda name: str(path)):
        lines, titlePages = importFountainFixture("clean.fountain", review=review)

    assert review.rows is None
    assert lines == [
        (screenplay.SCENE, "INT. HOUSE - DAY"),
        (screenplay.CHARACTER, "JOE"),
        (screenplay.PAREN, "(quietly)"),
        (screenplay.DIALOGUE, "Hello."),
        (screenplay.TRANSITION, "CUT TO:"),
    ]
