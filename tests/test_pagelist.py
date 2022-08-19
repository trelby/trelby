import screenplay as scr
import u

# test screenplay.PageList

# helper test function.
def ch(allPages, pages, res):
    pl = scr.PageList(allPages)

    for p in pages:
        pl.addPage(p)

    assert str(pl) == res

def testBasic():
    u.init()

    # "1" .. "119"
    allPages = [str(p) for p in range(120)[1:]]

    # test basic stuff
    ch([], [], "")
    ch(allPages, [], "")
    ch(allPages, [-42, 167], "")
    ch(allPages, [1], "1")
    ch(allPages, [1, 2], "1-2")
    ch(allPages, [6, 7, 8], "6-8")
    ch(allPages, [6, 7, 8, 118], "6-8, 118")
    ch(allPages, [6, 7, 8, 119], "6-8, 119")
    ch(allPages, [6, 7, 8, 118, 119], "6-8, 118-119")

    # test that int/str makes no difference
    ch(allPages, [1, 2, 3, 5, 7, 9, 42, 43, 44], "1-3, 5, 7, 9, 42-44")
    ch(allPages, ["1", "2", "3", "5", "7", "9", "42", "43", "44"],
       "1-3, 5, 7, 9, 42-44")
    ch(allPages, ["1", 2, "3", 5, "7", 9, "42", 43, "44"],
       "1-3, 5, 7, 9, 42-44")

def testFancy():
    u.init()

    allPages = ["1A", "3", "4B", "4C", "4D", "5", "6", "6A", "7", "7B"]

    ch(allPages, ["1A", "3", "4C", "6", "6A", "7", "7B"], "1A-3, 4C, 6-7B")
    ch(allPages, ["1A", "7B"], "1A, 7B")
    ch(allPages, ["1A", 7, "7B"], "1A, 7-7B")
