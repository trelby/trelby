import u
import util

# test util stuff

def testReplace():
    u.init()

    ur = util.replace
    
    assert ur("", "", 0, 0) == ""
    assert ur("", "jep", 0, 0) == "jep"
    assert ur("yo", "bar", 0, 0) == "baryo"
    assert ur("yo", "bar", 0, 1) == "baro"
    assert ur("yo", "bar", 1, 0) == "ybaro"
    assert ur("yo", "bar", 1, 1) == "ybar"
    assert ur("yo", "bar", 2, 0) == "yobar"
    assert ur("yo", "ba\tr", 2, 0) == "yoba|r"
