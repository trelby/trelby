from error import *
import glob
import os
import tempfile
import time

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

# translate table for converting strings to only contain valid input
# characters
_input_tbl = ""

def init():
    global _to_upper, _to_lower, _input_tbl

    # setup ISO-8859-1 case-conversion stuff
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

    # valid input string stuff
    for i in range(256):
        if isValidInputChar(i):
            _input_tbl += chr(i)
        else:
            _input_tbl += "|"

# like string.upper/lower, but we do our own charset-handling that doesn't
# need locales etc
def upper(s):
    return s.translate(_to_upper)

def lower(s):
    return s.translate(_to_lower)

# return 's', which must be a string of ISO-8859-1 characters, converted
# to UTF-8.
def toUTF8(s):
    return unicode(s, "ISO-8859-1").encode("UTF-8")

# returns True if kc (key-code) is a valid character to add to the script.
def isValidInputChar(kc):
    # [0x80, 0x9F] = unspecified control characters in ISO-8859-1, added
    # characters like euro etc in windows-1252. 0x7F = backspace, 0xA0 =
    # non-breaking space, 0xAD = soft hyphen.
    return (kc >= 32) and (kc <= 255) and not\
           ((kc >= 0x7F) and (kc <= 0xA0)) and (kc != 0xAD)

# return s with all non-valid input characters converted to valid input
# characters.
def toInputStr(s):
    return s.translate(_input_tbl)

# returns s with all possible different types of newlines converted to
# unix newlines, i.e. a single "\n"
def fixNL(s):
    return s.replace("\r\n", "\n").replace("\r", "\n")

# clamps the given value to a specific range. both limits are optional.
def clamp(val, minVal = None, maxVal = None):
    ret = val
    
    if minVal != None:
        ret = max(ret, minVal)

    if maxVal != None:
        ret = min(ret, maxVal)

    return ret

# like clamp, but gets/sets value directly from given object
def clampObj(obj, name, minVal = None, maxVal = None):
    setattr(obj, name, clamp(getattr(obj, name), minVal, maxVal))

# convert given string to float, clamping it to the given range
# (optional). never throws any exceptions, return defVal (possibly clamped
# as well) on any errors.
def str2float(s, defVal, minVal = None, maxVal = None):
    val = defVal
    
    try:
        val = float(s)
    except ValueError:
        pass
    except OverflowError:
        pass

    return clamp(val, minVal, maxVal)

# like str2float, but for ints.
def str2int(s, defVal, minVal = None, maxVal = None):
    val = defVal
    
    try:
        val = int(s)
    except ValueError:
        pass

    return clamp(val, minVal, maxVal)

# extract 'name' field from each item in 'seq', put it in a list, and
# return that list.
def listify(seq, name):
    l = []
    for it in seq:
        l.append(getattr(it, name))

    return l

# for each character in 'flags', starting at beginning, checks if that
# character is found in 's'. if so, appends True to a tuple, False
# otherwise. returns that tuple, whose length is of course is len(flags).
def flags2bools(s, flags):
    b = ()

    for f in flags:
        if s.find(f) != -1:
            b += (True,)
        else:
            b += (False,)

    return b

# reverse of flags2bools. is given a number of objects, if each object
# evaluates to true, chars[i] is appended to the return string. len(chars)
# == len(bools) must be true.
def bools2flags(chars, *bools):
    s = ""

    if len(chars) != len(bools):
        raise TypeError("bools2flags: chars and bools are not equal length")

    for i in range(len(chars)):
        if bools[i]:
            s += chars[i]

    return s
    
def isFixedWidth(font):
    dc = wxMemoryDC()
    dc.SetFont(font)
    w1, h1 = dc.GetTextExtent("iiiii")
    w2, h2 = dc.GetTextExtent("OOOOO")
    
    return w1 == w2

# return how many mm tall 'points' size font is
def points2y(points):
    return (points / 72.0) * 25.4

# return how many mm wide 'points' size font is. this assumes standard PDF
# Courier font, which has a width of 0.6 units for each character.
def points2x(points):
    return ((points * 0.6) / 72.0) * 25.4
    
def reverseComboSelect(combo, clientData):
    for i in range(combo.GetCount()):
        if combo.GetClientData(i) == clientData:
            if combo.GetSelection() != i:
                combo.SetSelection(i)

            return True

    return False

# set widget's client size. if w or h is -1, that dimension is not changed.
def setWH(ctrl, w = -1, h = -1):
    size = ctrl.GetClientSize()

    if w != -1:
        size.width = w

    if h != -1:
        size.height = h
        
    ctrl.SetClientSizeWH(size.width, size.height)

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

    c = unicode(c, "ISO-8859-1")
    if not c.isalnum():
        return True

    return False

# split string 's' into words. word = alphanumeric characters or "-'".
def splitToWords(s):
    tmp = ""
    
    s = unicode(s, "ISO-8859-1")
    for c in s:
        if c.isalnum() or (c == "-") or (c == "'"):
            tmp += c
        else:
            tmp += " "

    return tmp.encode("ISO-8859-1").split()

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

        # if True, means processing this key event shouldn't do expensive
        # screen updating stuff as there will be more key events coming
        # in.
        self.noUpdate = False

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

# load at most maxSize (all if -1) bytes from 'filename', returning the
# data as a string or None on errors. pops up message boxes with 'frame'
# as parent on errors.
def loadFile(filename, frame, maxSize = -1):
    ret = None
    
    try:
        f = open(filename, "rb")

        try:
            ret = f.read(maxSize)
        finally:
            f.close()

    except IOError, (errno, strerror):
        wxMessageBox("Error loading file '%s': %s" % (filename, strerror),
                     "Error", wxOK, frame)
        ret = None

    return ret

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

def removeTempFiles(prefix):
    files = glob.glob(tempfile.gettempdir() + "/%s*" % prefix)

    for fn in files:
        try:
            os.remove(fn)
        except OSError:
            continue

# simple timer class for use during development only
class TimerDev:
    def __init__(self, msg = ""):
        self.msg = msg
        self.t = time.time()

    def __del__(self):
        self.t = time.time() - self.t
        print "%s took %.4f seconds" % (self.msg, self.t)

# show PDF document 'pdfData' in an external viewer program. writes out a
# temporary file, first deleting all old temporary files, then opens PDF
# viewer application. 'mainFrame' is used as a parent for message boxes in
# case there are any errors.
def showTempPDF(pdfData, cfg, mainFrame):

    try:
        os.stat(cfg.pdfViewerPath)
    except OSError:
        wxMessageBox("PDF viewer application not found.", "Error", wxOK,
                     mainFrame)

        return
    
    try:
        try:
            removeTempFiles(cfg.tmpPrefix)

            fd, filename = tempfile.mkstemp(prefix = cfg.tmpPrefix,
                                            suffix = ".pdf")

            try:
                os.write(fd, pdfData)
            finally:
                os.close(fd)

            # on Windows, Acrobat complains about "invalid path" if we
            # give the full path of the program as first arg, so give a
            # dummy arg.
            args = ["pdf"] + cfg.pdfViewerArgs + [filename]

            os.spawnv(os.P_NOWAIT, cfg.pdfViewerPath, args)

        except IOError, (errno, strerror):
            raise MiscError("IOError: %s" % strerror)

    except BlyteError, e:
        wxMessageBox("Error writing temporary PDF file: %s" % e,
                     "Error", wxOK, mainFrame)
