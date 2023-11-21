import u
import screenplay as scr

# test changing type of one element
def testChangeOneElem():
    sp = u.load()
    ls = sp.lines

    sp.cmd("moveDown")

    sp.cmd("tab")
    assert ls[1].lt == scr.CHARACTER

    sp.cmd("toPrevTypeTab")
    assert ls[1].lt == scr.ACTION

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

    for (func, ele) in list(functionMap.items()):
        sp.cmd(func)

        assert ls[0].lt == scr.SCENE

        i = 1
        while 1:
            assert ls[i].lt == ele

            if ls[i].lb == scr.LB_LAST:
                break

            i += 1

        assert ls[i + 1].lt == scr.CHARACTER

# test that when text belonging to multiple elements is selected, changing
# type changes all of those elements
def testChangeManyElemes():
    sp = u.load()
    ls = sp.lines

    # select second and third elements
    sp.cmd("moveDown")
    sp.cmd("setMark")
    sp.cmd("moveDown", count = 4)

    sp.cmd("toTransition")

    assert ls[0].lt == scr.SCENE

    for i in range(1, 13):
        assert ls[i].lt == scr.TRANSITION

    assert ls[11].lb == scr.LB_LAST
    assert ls[12].lb == scr.LB_LAST

    assert ls[13].lt == scr.DIALOGUE

