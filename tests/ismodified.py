import screenplay as scr
import config
import u

# tests isModified updating

def testInitial():
    sp = u.load()
    assert not sp.isModified()

def testAddChar():
    sp = u.load()
    sp.cmd("addChar", char = "a")
    assert sp.isModified()

def testDeleteBackwardsStart():
    sp = u.load()
    sp.cmd("deleteBackward")
    assert not sp.isModified()

def testDeleteBackwards():
    sp = u.load()
    sp.cmd("moveRight")
    sp.cmd("deleteBackward")
    assert sp.isModified()

def testDelete():
    sp = u.load()
    sp.cmd("deleteForward")
    assert sp.isModified()

def testDeleteEnd():
    sp = u.load()
    sp.cmd("moveEnd")
    sp.cmd("deleteForward")
    assert not sp.isModified()

# waste of time to test all move commands, test just one
def testMoveRight():
    sp = u.load()
    sp.cmd("moveRight")
    assert not sp.isModified()

def testForcedLineBreak():
    sp = u.load()
    sp.cmd("insertForcedLineBreak")
    assert sp.isModified()

def testSplitElement():
    sp = u.load()
    sp.cmd("splitElement")
    assert sp.isModified()

def testTab():
    sp = u.load()
    sp.cmd("tab")
    assert sp.isModified()

def testToPrevTypeTab():
    sp = u.load()
    sp.cmd("toPrevTypeTab")
    assert sp.isModified()

def testConvert():
    sp = u.load()
    sp.cmd("toNote")
    assert sp.isModified()

def testPaste():
    sp = u.load()
    sp.paste([scr.Line(text = "yo")])
    assert sp.isModified()

def testRemoveElementTypes():
    sp = u.load()
    sp.removeElementTypes({ scr.ACTION : 0 }, False)
    assert sp.isModified()

def testApplyCfg():
    sp = u.load()
    sp.applyCfg(config.Config())
    assert sp.isModified()

def testCut():
    sp = u.load()
    sp.cmd("setMark")
    sp.cmd("moveRight")
    sp.getSelectedAsCD(True)
    assert sp.isModified()
