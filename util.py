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
