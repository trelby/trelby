import screenplay as scr
import u

# tests deleting selected areas of text

def testBasic():
    sp = u.load()

    sp.cmd("setMark")
    sp.getSelectedAsCD(True)

    assert sp.lines[0].lb == scr.LB_LAST
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].text == "xt. stonehenge - night"

def testLastDelete():
    sp = u.load()

    sp.cmd("moveEnd")
    sp.cmd("setMark")
    sp.cmd("moveUp", count = 4)
    sp.cmd("moveLineStart")

    # we used to have a bug where if we deleted e.g. the last two lines of
    # the script, and that element was longer, we didn't mark the
    # third-last line as LB_LAST, and then it crashed in rewrapPara.
    sp.getSelectedAsCD(True)

def testEndPrevPara():
    sp = u.load()

    sp.cmd("moveDown", count = 4)
    sp.cmd("moveLineEnd")
    sp.cmd("setMark")
    sp.cmd("moveLineStart")
    sp.cmd("moveUp")

    sp.getSelectedAsCD(True)

    # test that when deleting the last lines of an element we correctly
    # flag the preceding line as the new last line.

    assert sp.lines[2].lb == scr.LB_LAST
    assert sp.lines[3].lt == scr.CHARACTER

# we used to have a bug where joining two elements when the latter one
# contained a forced linebreak didn't convert it properly to the preceding
# element's type.
def testForcedLb():
    sp = u.load()

    sp.cmd("moveDown", count = 2)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp", count = 2)
    sp.cmd("moveLineEnd")
    sp.cmd("setMark")
    sp.cmd("moveRight")
    sp.getSelectedAsCD(True)
    sp._validate()

# we used to have a bug where if we deleted the first line of an element
# plus at least some of the later lines, the rest of the element was
# erroneously joined to the preceding element.
def testFirstDelete():
    sp = u.load()

    sp.cmd("moveDown")
    sp.cmd("setMark")
    sp.cmd("moveDown")
    sp.getSelectedAsCD(True)

    assert sp.lines[0].lb == scr.LB_LAST
    assert sp.lines[0].lt == scr.SCENE

    assert sp.lines[1].lb == scr.LB_SPACE
    assert sp.lines[1].lt == scr.ACTION
    assert sp.lines[1].lt == scr.ACTION
    assert sp.lines[1].text == "lmost zero. Only at brief moments do we catch sight of the"

    sp._validate()

# test that when joining two elements of different type, the latter of
# which contains forced linebreaks, that the whole of the latter element
# is rewrapped correctly.
def testTypeConvert():
    sp = u.load()

    sp.cmd("toTransition")
    sp.cmd("moveDown", count = 3)
    sp.cmd("insertForcedLineBreak")
    sp.cmd("moveUp")
    sp.cmd("setMark")
    sp.cmd("moveLeft")
    sp.getSelectedAsCD(True)

    sp._validate()
