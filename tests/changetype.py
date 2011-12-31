import u
import screenplay as scr

# test change of element type
def testTabChangeLineType():
    sp = u.load()
    sp.cmd("tab")
    assert(sp.lines[0].lt == scr.ACTION)
    sp.cmd("toPrevTypeTab")
    assert(sp.lines[0].lt == scr.CHARACTER)

    functionMap = { 
        "toScene" : scr.SCENE,
        "toCharacter" : scr.CHARACTER,
        "toAction" : scr.ACTION,
        "toDialogue" : scr.DIALOGUE,
        "toParen" : scr.PAREN,
        "toShot" : scr.SHOT,
        "toNote" : scr.NOTE,
        "toTransition" : scr.TRANSITION,
    }

    for (func, ele) in functionMap.items():
        sp.cmd(func)
        assert(sp.lines[0].lt == ele)

# test selecting text, and changing them all
def testSelectionChange():
    sp = u.load()
    # start selection
    sp.gotoPos(0, 0, False)
    sp.gotoPos(0, 0, True)
    # end it a little below
    sp.gotoPos(5, 4, True)
    # convert selected to Dialogue 
    sp.convertTypeTo(scr.DIALOGUE)
    # ensure the 8th line is "weather." in dialogue type, 
    # and ends with LB_LAST
    assert(sp.lines[7].text == "weather.")
    assert(sp.lines[7].lt == scr.DIALOGUE)
    assert(sp.lines[7].lb == scr.LB_LAST)

