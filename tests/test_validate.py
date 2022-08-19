import screenplay as scr
import u

# tests that Screenplay._validate() finds all errors it's supposed to

# helper function that asserts if sp._validate() does not assert
def v(sp):
    try:
        sp._validate()
    except AssertionError:
        return

    assert 0

def testEmpty():
    sp = u.new()
    sp._validate()
    sp.lines = []
    v(sp)

def testCursorPos():
    sp = u.new()

    sp._validate()

    sp.line = -1
    v(sp)

    sp.line = 5
    v(sp)

    sp.line = 0

    sp.column = -1
    v(sp)

    sp.column = 5
    v(sp)

    sp.column = 0

    sp._validate()

def testInvalidChars():
    sp = u.new()
    sp._validate()
    sp.lines[0].text = chr(9)
    v(sp)

def testTooLongLine():
    sp = u.new()
    sp._validate()
    sp.lines[0].text = "a" * 100
    v(sp)

def testElemChangesType():
    sp = u.load()
    sp._validate()
    sp.lines[1].lt = scr.SCENE
    v(sp)
