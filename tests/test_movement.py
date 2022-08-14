import u

# tests movement commands

def testMoveRight():
    sp = u.load()
    sp.cmd("moveRight")
    assert sp.column == 1
    sp.cmd("moveLineEnd")
    sp.cmd("moveRight")
    assert (sp.line == 1) and (sp.column == 0)
    sp.cmd("moveEnd")
    sp.cmd("moveRight")
    assert (sp.line == 158) and (sp.column == 5)

def testMoveLeft():
    sp = u.load()
    sp.cmd("moveLeft")
    assert (sp.line == 0) and (sp.column == 0)
    sp.cmd("moveDown")
    sp.cmd("moveLeft")
    assert (sp.line == 0) and (sp.column == 23)
    sp.cmd("moveLineStart")
    assert sp.column == 0

def testMoveUp():
    sp = u.load()
    sp.cmd("moveUp")
    assert (sp.line == 0) and (sp.column == 0)
    sp.cmd("moveDown")
    sp.cmd("moveLineEnd")
    sp.cmd("moveUp")
    assert (sp.line == 0) and (sp.column == 23)

def testMoveDown():
    sp = u.load()
    sp.cmd("moveDown")
    assert sp.line == 1
    sp.cmd("moveDown")
    sp.cmd("moveDown")
    sp.cmd("moveLineEnd")
    sp.cmd("moveDown")
    assert (sp.line == 4) and (sp.column == 31)
    sp.cmd("moveEnd")
    sp.cmd("moveDown")
    assert sp.line == 158

def testMoveLineEnd():
    sp = u.load()
    sp.cmd("moveLineEnd")
    assert sp.column == 23

def testMoveLineStart():
    sp = u.load()
    sp.cmd("moveRight")
    sp.cmd("moveLineStart")
    assert sp.column == 0

def testMoveEnd():
    sp = u.load()
    sp.cmd("moveEnd")
    assert (sp.line == 158) and (sp.column == 5)

def testMoveStart():
    sp = u.load()
    sp.cmd("moveEnd")
    sp.cmd("moveStart")
    assert (sp.line == 0) and (sp.column == 0)

def testMoveSceneUp():
    sp = u.load()
    sp.cmd("moveSceneUp")
    assert (sp.line == 0) and (sp.column == 0)
    sp.gotoPos(18, 1)
    sp.cmd("moveSceneUp")
    assert (sp.line == 14) and (sp.column == 0)
    sp.cmd("moveSceneUp")
    assert (sp.line == 0) and (sp.column == 0)

    # make sure we don't go before the start trying to find scenes
    sp.cmd("toAction")
    sp.cmd("moveSceneUp")
    assert (sp.line == 0) and (sp.column == 0)

def testMoveSceneDown():
    sp = u.load()
    sp.cmd("moveSceneDown")
    assert (sp.line == 14) and (sp.column == 0)
    sp.cmd("moveDown")
    sp.cmd("moveSceneDown")
    assert (sp.line == 30) and (sp.column == 0)
    sp.cmd("moveEnd")
    sp.cmd("moveSceneDown")
    assert (sp.line == 158) and (sp.column == 0)
