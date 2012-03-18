import screenplay as scr
import u

# tests adding characters, i.e. normal typing

def testSpaceAtEOL():
    sp = u.load()
    sp.cmd("moveDown", count = 3)
    sp.cmd("moveLineEnd")
    sp.cmd("addChar", char = "z")
    sp.cmd("addChar", char = " ")
    assert sp.lines[3].text.endswith("z ")
    sp.cmd("addChar", char = "x")
    assert (sp.line == 4) and (sp.column == 1)
    assert sp.lines[3].lb == scr.LB_SPACE
    assert sp.lines[4].lb == scr.LB_LAST
    assert sp.lines[3].text.endswith("wouldz")
    assert sp.lines[4].text.startswith("x be")

def testNbspAtEOL():
    sp = u.load()
    sp.cmd("moveDown", count = 3)
    sp.cmd("moveLineEnd")
    sp.cmd("addChar", char = chr(160))
    sp.cmd("addChar", char = "a")
    assert sp.lines[3].text.endswith("mind")
    assert sp.lines[4].text.startswith("would%sa" % chr(160))
    assert (sp.line == 4) and (sp.column == 7)
    assert sp.lines[3].lb == scr.LB_SPACE
    assert sp.lines[4].lb == scr.LB_LAST

# FIXME: lot more tests
