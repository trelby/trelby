from wxPython.wx import *

# alignment values
ALIGN_LEFT    = 0
ALIGN_CENTER  = 1
ALIGN_RIGHT   = 2
VALIGN_TOP    = 1
VALIGN_CENTER = 2
VALIGN_BOTTOM = 3

# mappings from lowercase to uppercase letters for different charsets
_iso_8859_1_map = {
    97 : 65, 98 : 66, 99 : 67, 100 : 68, 101 : 69,
    102 : 70, 103 : 71, 104 : 72, 105 : 73, 106 : 74,
    107 : 75, 108 : 76, 109 : 77, 110 : 78, 111 : 79,
    112 : 80, 113 : 81, 114 : 82, 115 : 83, 116 : 84,
    117 : 85, 118 : 86, 119 : 87, 120 : 88, 121 : 89,
    122 : 90, 224 : 192, 225 : 193, 226 : 194, 227 : 195,
    228 : 196, 229 : 197, 230 : 198, 231 : 199, 232 : 200,
    233 : 201, 234 : 202, 235 : 203, 236 : 204, 237 : 205,
    238 : 206, 239 : 207, 240 : 208, 241 : 209, 242 : 210,
    243 : 211, 244 : 212, 245 : 213, 246 : 214, 248 : 216,
    249 : 217, 250 : 218, 251 : 219, 252 : 220, 253 : 221,
    254 : 222
    }

# current mappings, 256 chars long.
_to_upper = ""
_to_lower = ""

# we only support ISO-8859-1 for now, so this doesn't take any parameters
def setCharset():
    global _to_upper, _to_lower

    _to_upper = ""
    _to_lower = ""
    tmpUpper = []
    tmpLower = []

    for i in range(256):
        tmpUpper.append(i)
        tmpLower.append(i)

    for k, v in _iso_8859_1_map.iteritems():
        tmpUpper[k] = v
        tmpLower[v] = k

    for i in range(256):
        _to_upper += chr(tmpUpper[i])
        _to_lower += chr(tmpLower[i])

# like string.upper/lower, but we do our own charset-handling that doesn't
# need locales etc
def upper(s):
    return s.translate(_to_upper)

def lower(s):
    return s.translate(_to_lower)

# returns True if kc (key-code) is a valid character to add to the script.
def isValidInputChar(kc):
    # [0x80, 0x9F] = unspecified control characters in ISO-8859-1, added
    # characters like euro etc in windows-1252. 0x7F = backspace, 0xA0 =
    # non-breaking space, 0xAD = soft hyphen.
    return (kc >= 32) and (kc <= 255) and not\
           ((kc >= 0x7F) and (kc <= 0xA0)) and (kc != 0xAD)

# returns s with all possible different types of newlines converted to
# unix newlines, i.e. a single "\n"
def fixNL(s):
    return s.replace("\r\n", "\n").replace("\r", "\n")

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

# wxMSW doesn't respect the control's min/max values at all, so we have to
# implement this ourselves
def getSpinValue(spinCtrl):
    tmp = clamp(spinCtrl.GetValue(), spinCtrl.GetMin(), spinCtrl.GetMax())
    spinCtrl.SetValue(tmp)
    
    return tmp

# returns true if c, a single character, is either empty, not an
# alphanumeric character, or more than one character.
def isWordBoundary(c):
    if len(c) != 1:
        return True

    # FIXME: this is broken for ISO-8859-1 characters
    if not c.isalnum():
        return True

    return False

# DrawLine-wrapper that makes it easier when the end-point is just
# offsetted from the starting point
def drawLine(dc, x, y, xd, yd):
    dc.DrawLine(x, y, x + xd, y + yd)

# draws text aligned somehow
def drawText(dc, text, x, y, align = ALIGN_LEFT, valign = VALIGN_TOP):
    w, h = dc.GetTextExtent(text)

    if align == ALIGN_CENTER:
        x -= w / 2
    elif align == ALIGN_RIGHT:
        x -= w
        
    if valign == VALIGN_CENTER:
        y -= h / 2
    elif valign == VALIGN_BOTTOM:
        y -= h
        
    dc.DrawText(text, x, y)

# fake key event, supports same operations as the real one
class MyKeyEvent:
    def __init__(self, kc = 0):
        # keycode
        self.kc = kc

        self.controlDown = False
        self.altDown = False
        self.shiftDown = False

    def GetKeyCode(self):
        return self.kc
    
    def ControlDown(self):
        return self.controlDown

    def AltDown(self):
        return self.altDown

    def ShiftDown(self):
        return self.shiftDown

    def Skip(self):
        pass

# a string-like object that features reasonably fast repeated appends even
# for large strings, since it keeps each appended string as an item in a
# list.
class String:
    def __init__(self):

        # byte count of data appended
        self.pos = 0

        # list of strings
        self.data = []

    def getPos(self):
        return self.pos

    def __str__(self):
        return "".join(self.data)
    
    def __iadd__(self, s):
        s2 = str(s)
        
        self.data.append(s2)
        self.pos += len(s2)

        return self

# write 'data' to 'filename', popping up a messagebox using 'frame' as
# parent on errors. returns True on success.
def writeToFile(filename, data, frame):
    try:
        f = open(filename, "wb")

        try:
            f.write(data)
        finally:
            f.close()

        return True
    
    except IOError, (errno, strerror):
        wxMessageBox("Error writing file '%s': %s" % (filename, strerror),
                     "Error", wxOK, frame)

        return False
