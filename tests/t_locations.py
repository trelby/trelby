import locations
import u

# test locations.Locations

# helper test function.
def ch(locsOld, scenes, locsNew):
    loc = locations.Locations()
    loc.locations = locsOld

    loc.refresh(scenes)

    assert loc.locations == locsNew

def test():
    u.init()

    scenes = {
        "INT. MOTEL ROOM - DAY" : None,
        "INT. MOTEL ROOM - NIGHT" : None,
        "EXT. PALACE - DAY" : None,
        "EXT. SHOPFRONT - DAY" : None
        }

    ch([], {}, [])
    ch([], scenes, [])
    ch([["nosuchthingie"]], {}, [])
    ch([["nosuchthingie"]], scenes, [])

    ch([["int. motel Room - day"]], scenes, [["INT. MOTEL ROOM - DAY"]])

    ch([["int. motel Room - day", "nosuchthingie"]], scenes,
       [["INT. MOTEL ROOM - DAY"]])

    ch([["int. motel Room - day", "int. motel Room - day"]], scenes,
       [["INT. MOTEL ROOM - DAY"]])

    ch([["INT. MOTEL ROOM - DAY", "EXT. SHOPFRONT - DAY"]], scenes,
       [["EXT. SHOPFRONT - DAY", "INT. MOTEL ROOM - DAY"]])

    ch([["INT. MOTEL ROOM - DAY"],
        ["INT. MOTEL ROOM - NIGHT", "EXT. PALACE - DAY"]], scenes,
       [["EXT. PALACE - DAY", "INT. MOTEL ROOM - NIGHT"],
        ["INT. MOTEL ROOM - DAY"]])
