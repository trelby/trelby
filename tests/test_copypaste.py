import screenplay as scr
import u

# tests delete commands

# we had a bug where pasting on an empty line right after a forced
# linebreak would think "oh, I'm in an empty element, I'll just change the
# linetype of this line and be done with it", which is wrong, because the
# linetypes of the lines above were not changed, and now you had an
# element with multiple different linetypes. the right thing to do is not
# change the linetypes at all unless the entire element is empty.
def testPasteAfterForcedLineBreak():
    sp = u.new()

    sp.cmd("addChar", char = "E")
    assert sp.lines[0].lt != scr.CHARACTER

    sp.cmd("insertForcedLineBreak")
    sp.paste([scr.Line(text = "Tsashkataar", lt = scr.CHARACTER)])

    assert len(sp.lines) == 2
    assert (sp.line == 1) and (sp.column == 11)
    assert sp.lines[0].text == "E"
    assert sp.lines[0].lt == scr.SCENE
    assert sp.lines[0].lb == scr.LB_FORCED
    assert sp.lines[1].text == "Tsashkataar"
    assert sp.lines[1].lt == scr.SCENE
    assert sp.lines[1].lb == scr.LB_LAST

    sp._validate()

# FIXME: lot more tests
