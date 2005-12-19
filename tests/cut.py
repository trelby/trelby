import screenplay as scr
import config
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
    

