from wxPython.wx import *

def clamp(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val

def isFixedWidth(font):
    dc = wxMemoryDC()
    dc.SetFont(font)
    w1, h1 = dc.GetTextExtent("iiiii")
    w2, h2 = dc.GetTextExtent("OOOOO")
    
    return w1 == w2

def reverseComboSelect(combo, clientData):
    for i in range(combo.GetCount()):
        if combo.GetClientData(i) == clientData:
            if combo.GetSelection() != i:
                combo.SetSelection(i)

            return True

    return False

# returns true if c, a single character, is either empty, not an
# alphanumeric character, or more than one character.
def isWordBoundary(c):
    if len(c) != 1:
        return True

    if not c.isalnum():
        return True
