import tests.u as u
import trelby.screenplay as scr
import trelby.viewmode as viewmode
from trelby.line import Line


def _mksp(lines):
    sp = u.new()
    sp.lines = lines
    return sp


def testContinuedAddedAfterInterveningAction():
    sp = _mksp(
        [
            Line(scr.LB_LAST, scr.SCENE, "INT. ROOM - DAY"),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "First line."),
            Line(scr.LB_LAST, scr.ACTION, "He sits."),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "Second line."),
        ]
    )

    assert not sp.shouldAddDialogueContinuedForCharacter(1)
    assert sp.shouldAddDialogueContinuedForCharacter(4)
    assert sp.getCharacterTextForDisplay(4) == "JOHN (cont'd)"


def testContinuedNotAddedWhenDifferentSpeakerInBetween():
    sp = _mksp(
        [
            Line(scr.LB_LAST, scr.SCENE, "INT. ROOM - DAY"),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "First."),
            Line(scr.LB_LAST, scr.CHARACTER, "MARY"),
            Line(scr.LB_LAST, scr.DIALOGUE, "Second."),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
        ]
    )

    assert not sp.shouldAddDialogueContinuedForCharacter(5)


def testContinuedNotAddedAcrossSceneBoundary():
    sp = _mksp(
        [
            Line(scr.LB_LAST, scr.SCENE, "INT. ROOM - DAY"),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "First."),
            Line(scr.LB_LAST, scr.SCENE, "EXT. STREET - NIGHT"),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
        ]
    )

    assert not sp.shouldAddDialogueContinuedForCharacter(4)


def testContinuedNotDuplicatedIfAlreadyPresent():
    sp = _mksp(
        [
            Line(scr.LB_LAST, scr.SCENE, "INT. ROOM - DAY"),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "First."),
            Line(scr.LB_LAST, scr.ACTION, "Pause."),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN (cont'd)"),
        ]
    )

    assert not sp.shouldAddDialogueContinuedForCharacter(4)
    assert sp.getCharacterTextForDisplay(4) == "JOHN (cont'd)"


def testStrictSpeakerMatchingWithVoiceModifier():
    sp = _mksp(
        [
            Line(scr.LB_LAST, scr.SCENE, "INT. ROOM - DAY"),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "First."),
            Line(scr.LB_LAST, scr.ACTION, "Pause."),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN (V.O.)"),
        ]
    )

    assert not sp.shouldAddDialogueContinuedForCharacter(4)


def testDisplayTextUsesExportCapsWithoutUppercasingContinuation():
    sp = _mksp(
        [
            Line(scr.LB_LAST, scr.SCENE, "INT. ROOM - DAY"),
            Line(scr.LB_LAST, scr.CHARACTER, "john"),
            Line(scr.LB_LAST, scr.DIALOGUE, "First."),
            Line(scr.LB_LAST, scr.ACTION, "Pause."),
            Line(scr.LB_LAST, scr.CHARACTER, "john"),
        ]
    )

    assert sp.getCharacterTextForDisplay(4, True) == "JOHN (cont'd)"


def testDraftViewUsesDisplayTextForRepeatedCharacterCue():
    sp = _mksp(
        [
            Line(scr.LB_LAST, scr.SCENE, "INT. ROOM - DAY"),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "First line."),
            Line(scr.LB_LAST, scr.ACTION, "He sits."),
            Line(scr.LB_LAST, scr.CHARACTER, "JOHN"),
            Line(scr.LB_LAST, scr.DIALOGUE, "Second line."),
        ]
    )

    class _DummyFi:
        fx = 1

    class _DummyCfgGui:
        def tt2fi(self, _tt):
            return _DummyFi()

    class _DummyCtrl:
        def __init__(self, screenplay):
            self.sp = screenplay
            self.mm2p = 1
            self.pageW = 100
            self._cfgGui = _DummyCfgGui()

        def GetClientSize(self):
            return (800, 600)

        def getCfgGui(self):
            return self._cfgGui

    texts, _ = viewmode.ViewModeDraft().getScreen(_DummyCtrl(sp), doExtra=True)
    line_texts = {t.line: t.text for t in texts}

    assert line_texts[1] == "JOHN"
    assert line_texts[4] == "JOHN (cont'd)"
    assert sp.lines[4].text == "JOHN"
