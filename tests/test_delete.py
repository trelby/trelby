import screenplay as scr
import u

# tests delete commands

def testBackStart():
    sp = u.load()
    sp.cmd("deleteBackward")
    assert (sp.line == 0) and (sp.column == 0)
    assert sp.lines[0].text == "ext. stonehenge - night"

def testBack():
    sp = u.load()
    sp.cmd("moveRight")
    sp.cmd("deleteBackward")
    assert (sp.line == 0) and (sp.column == 0)
    assert sp.lines[0].text == "xt. stonehenge - night"

def testBackJoinElements():
    sp = u.load()
    sp.cmd("moveDown")
    sp.cmd("deleteBackward")
    assert (sp.line == 0) and (sp.column == 23)
    assert sp.lines[0].text == "ext. stonehenge - nightA blizzard rages."\
           " Snow is everywhere"

def testBackLbSpace():
    sp = u.load()
    sp.gotoPos(16, 60)
    sp.cmd("addChar", char = " ")
    assert sp.lines[16].lb == scr.LB_SPACE
    sp.cmd("moveDown")
    sp.cmd("moveLineStart")
    sp.cmd("deleteBackward")
    assert (sp.line == 17) and (sp.column == 0)
    assert sp.lines[16].lb == scr.LB_SPACE
    assert sp.lines[16].text == "A calm night, with the ocean almost still."\
           " Two fishermen are"
    assert sp.lines[17].text == "smoking at the rear deck."

def testBackLbNone():
    sp = u.load()

    sp.gotoPos(20, 0)
    assert sp.lines[19].lb == scr.LB_NONE
    sp.cmd("deleteBackward")
    assert (sp.line == 19) and (sp.column == 34)
    assert sp.lines[19].text == "Aye,it'snightslikethisthatmakemeree"
    assert sp.lines[20].text == "mber why I love being a fisherman."
    assert sp.lines[19].lb == scr.LB_NONE
    sp.cmd("moveRight", count = 3)
    sp.cmd("addChar", char = " ")
    sp.cmd("moveLeft", count = 2)
    sp.cmd("deleteBackward")
    assert (sp.line == 19) and (sp.column == 34)
    assert sp.lines[19].text == "Aye,it'snightslikethisthatmakemerem"
    assert sp.lines[20].text == "ber why I love being a fisherman."
    assert sp.lines[19].lb == scr.LB_SPACE

def testBackLbForced():
    sp = u.load()

    sp.gotoPos(34, 0)
    assert sp.lines[33].lb == scr.LB_FORCED
    sp.cmd("deleteBackward")
    assert (sp.line == 33) and (sp.column == 6)
    assert sp.lines[33].text == "brightyellow package at their feet."
    assert sp.lines[33].lb == scr.LB_LAST

# test that when joining two elements of different type, the latter of
# which contains forced linebreaks, that the whole of the latter element
# is rewrapped correctly.
def testBackLbForcedTypeConvert():
    sp = u.load()

    sp.cmd("toTransition")
    sp.cmd("moveDown", count = 3)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp")
    sp.cmd("deleteBackward")

    sp._validate()

# FIXME: more tests for forward deletion

# test that when joining two elements of different type, the latter of
# which contains forced linebreaks, that the whole of the latter element
# is rewrapped correctly.
def testForwardLbForcedTypeConvert():
    sp = u.load()

    sp.cmd("toTransition")
    sp.cmd("moveDown", count = 3)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp", count = 2)
    sp.cmd("moveLineEnd")
    sp.cmd("deleteForward")

    sp._validate()
