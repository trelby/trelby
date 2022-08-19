# -*- coding: iso-8859-1 -*-

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

def testSplitToWords():
    u.init()

    us = util.splitToWords

    assert us("") == []
    assert us("yo") == ["yo"]
    assert us("yo foo") == ["yo", "foo"]
    assert us("äksy yö") == ["äksy", "yö"]
    assert us("Mixed CASE") == ["Mixed", "CASE"]
    assert us("out-of-nowhere, a monkey appears, bearing fruit!") == [
        "out", "of", "nowhere", "a", "monkey", "appears", "bearing", "fruit"]
    assert us("don't assume -- it blaa") == ["don't", "assume", "it", "blaa"]
    assert us("a''b--c|d®e") == ["a''b", "c", "d", "e"]

#def testToUTF8():
#    u.init()
#
#    t = util.toUTF8
#
#    assert t("") == ""
#    assert t("yo") == "yo"
#    assert t("yö") == "yÃ¶"

#def testFromUTF8():
#    u.init()
#
#    f = util.fromUTF8
#
#    assert f("") == ""
#    assert f("yo") == "yo"
#    assert f("yÃ¶") == "yö"
#    assert f("yö12345") == "y12345"
#    assert f("a\xE2\x82\xACb") == "ab"

def testEscapeStrings():
    u.init()

    data = [
        ([], ""),
        (["a"], "a"),
        (["a", "b"], "a\\nb"),
        (["a", "b", "cc"], "a\\nb\\ncc"),
        (["foo\\bar", "blaa"], "foo\\\\bar\\nblaa"),
        (["a\\n", "c"], "a\\\\n\\nc"),
        (["a\\", "b"], "a\\\\\\nb"),
        ]

    for items,s in data:
        assert util.escapeStrings(items) == s
        assert util.unescapeStrings(s) == items
