import screenplay as scr
import u

# tests element joining

# we used to have a bug where if the latter element contained a forced
# linebreak the result was invalid. this one tests the case where the
# forced linebreak is on the first line of the element, the second one
# where it is on the third line.
def testForcedLb():
    sp = u.new()

    sp.cmd("addChar", char = "a")
    sp.cmd("splitElement")
    sp.cmd("toDialogue")
    sp.cmd("addChar", char = "b")
    sp.cmd("insertForcedLineBreak")
    sp.cmd("addChar", char = "c")
    sp.cmd("moveLeft")
    sp.cmd("moveUp")
    sp.cmd("deleteBackward")

    assert len(sp.lines) == 2
    assert (sp.line == 0) and (sp.column == 1)
    assert sp.lines[0].text == "AB"
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].lb == scr.LB_FORCED
    assert sp.lines[1].text == "c"
    assert sp.lines[1].lt == scr.SCENE
    assert sp.lines[1].lb == scr.LB_LAST

def testForcedLb2():
    sp = u.new()

    sp.cmd("addChar", char = "a")
    sp.cmd("splitElement")
    sp.cmd("toTransition")
    sp.cmdChars("line 1///////////// ")
    sp.cmdChars("line 2///////////// ")
    sp.cmdChars("line 3")
    sp.cmd("insertForcedLineBreak")
    sp.cmdChars("line 4")
    sp.gotoPos(1, 0)
    sp.cmd("deleteBackward")

    assert len(sp.lines) == 2
    assert (sp.line == 0) and (sp.column == 1)
    assert sp.lines[0].text == "ALine 1///////////// line 2///////////// line 3"
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].lb == scr.LB_FORCED
    assert sp.lines[1].text == "line 4"
    assert sp.lines[1].lt == scr.SCENE
    assert sp.lines[1].lb == scr.LB_LAST
