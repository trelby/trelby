from error import *
import misc

import datetime
import glob
import os
import re
import sha
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

# this has to be below the ALIGN stuff, otherwise things break due to
# circular dependencies
import fontinfo

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

# permanent memory DC to get text extents etc
permDc = None

def init():
    global _to_upper, _to_lower, _input_tbl, permDc

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

    # dunno if the bitmap needs to be big enough to contain the text we're
    # measuring...
    permDc = wxMemoryDC()
    permDc.SelectObject(wxEmptyBitmap(512, 32))
    
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
# characters, except form feeds, which are just deleted.
def toInputStr(s):
    return s.translate(_input_tbl, "\f")

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
    except (ValueError, OverflowError):
        pass

    return clamp(val, minVal, maxVal)

# like str2float, but for ints.
def str2int(s, defVal, minVal = None, maxVal = None, radix = 10):
    val = defVal
    
    try:
        val = int(s, radix)
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

# return s encoded so that all characters outside the range [32,126] (and
# "\\") are escaped.
def encodeStr(s):
    ret = ""
    
    for ch in s:
        c = ord(ch)

        # ord("\\") == 92 == 0x5C
        if c == 92:
            ret += "\\5C"
        elif (c >= 32) and (c <= 126):
            ret += ch
        else:
            ret += "\\%02X" % c

    return ret

# reverse of encodeStr. if string contains invalid escapes, they're
# silently and arbitrarily replaced by something.
def decodeStr(s):
    return re.sub(r"\\..", _decodeRepl, s)

# converts "\A4" style matches to their character values.
def _decodeRepl(mo):
    val = str2int(mo.group(0)[1:], 256, 0, 256, 16)

    if val != 256:
        return chr(val)
    else:
        return ""

# return True if given font is a fixed-width one.
def isFixedWidth(font):
    return getTextExtent(font, "iiiii")[0] == getTextExtent(font, "OOOOO")[0]

# get extent of 's' as (w, h) (may or may not include descend values)
def getTextExtent(font, s):
    permDc.SetFont(font)

    return permDc.GetTextExtent(s)

# get real height of font, including descend
def getFontHeight(font):
    permDc.SetFont(font)
    ext = permDc.GetFullTextExtent("_\xC5")

    return ext[1] + ext[2]

# return how many mm tall given font size is.
def getTextHeight(size):
    return (size / 72.0) * 25.4

# return how many mm wide given text is at given style with given size.
def getTextWidth(text, style, size):
    return (fontinfo.getTextWidth(text, style, size) / 72.0) * 25.4

# create font that's height is <= 'height' pixels. other parameters are
# the same as in wxFont's constructor.
def createPixelFont(height, family, style, weight):
    fs = 6

    selected = fs
    closest = 1000
    over = 0
    
    while 1:
        fn = wxFont(fs, family, style, weight,
                    encoding = wxFONTENCODING_ISO8859_1)
        h = getFontHeight(fn)
        diff = height -h

        if diff >= 0:
            if diff < closest:
                closest = diff
                selected = fs
        else:
            over += 1

        if (over >= 3) or (fs > 144):
            break

        fs += 2

    return wxFont(selected, family, style, weight,
                  encoding = wxFONTENCODING_ISO8859_1)
    
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

# return count of how many 'ch' characters 's' begins with.
def countInitial(s, ch):
    cnt = 0

    for i in range(len(s)):
        if s[i] != ch:
            break

        cnt += 1

    return cnt

# searches string 's' for each item of list 'seq', returning True if any
# of them were found.
def multiFind(s, seq):
    for it in seq:
        if s.find(it) != -1:
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
        x -= w // 2
    elif align == ALIGN_RIGHT:
        x -= w
        
    if valign == VALIGN_CENTER:
        y -= h // 2
    elif valign == VALIGN_BOTTOM:
        y -= h
        
    dc.DrawText(text, x, y)

# create pad sizer for given window whose controls are in topSizer, with
# 'pad' pixels of padding on each side, resize window to correct size, and
# optionally center it.
def finishWindow(window, topSizer, pad = 10, center = True):
    padSizer = wxBoxSizer(wxVERTICAL)
    padSizer.Add(topSizer, 1, wxEXPAND | wxALL, pad)
    window.SetSizerAndFit(padSizer)
    window.Layout()
    
    if center:
        window.Center()

# wxColour replacement that can safely be copy.deepcopy'd
class MyColor:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def toWx(self):
        return wxColour(self.r, self.g, self.b)

    def fromWx(c):
        o = MyColor(0, 0, 0)

        o.r = c.Red()
        o.g = c.Green()
        o.b = c.Blue()

        return o
    
    fromWx = staticmethod(fromWx)

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
    def __init__(self, s = None):

        # byte count of data appended
        self.pos = 0

        # list of strings
        self.data = []

        if s:
            self += s
            
    def __len__(self):
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

# return True if given file exists.
def fileExists(path):
    try:
        os.stat(path)
    except OSError:
        return False

    return True

# handles license stuff. format of license string:
#
# byte 0: version. 1 for beta testing, 2 for 1.0.
#
# byte 1: type, one of the values from below.
#
# bytes 2-3: last valid upgrade date, coded as number of days from
# 2000-01-01 in MSB.
#
# bytes 4-63: user id (60 bytes), padded with spaces at the start, and of
# the form <spaces> + "John Doe <john.doe@foo.net>"
#
# bytes 64-???: RSA signature of the SHA-1 hash of bytes 0-63, using our
# keys
class License:

    # license types
    STANDARD = 1
    PRODUCTION = 2

    # public exponent
    pubExp = 65537

    # public modulus
    pubMod = 29254935334455182042965597757772817301388292845900130682433565746868784488942621381364364162876559936654774402100546511105176419382129217568575288944027703304619282120442896579432657991408527650397456570447078730409302439200998338391377014236607103211227770334291908435704256189487601062996199948526088132202037509875714366181479780973317439978377800228612195110775627486438461629432119946045079582937393673482668070579676014424061995584470961990760405006986126005760445352618843826128863015510277694523358487180922871886359268019390165724063513636205071546516271852479359572341580343117229752020268293334064287174153L

    def __init__(self, type, lastDate, userId):
        # license type
        self.type = type

        # datetime.date object for last date this license applies to
        self.lastDate = lastDate

        # user identification
        self.userId = userId

    # try to construct new License from given string, using frame as
    # parent for error message boxes. returns None on failure.
    def fromStr(s, frame):
        try:
            if len(s) < 65:
                raise BlyteError("too short")

            # the 32 is for safety as I'm not entirely sure whether the
            # signature can grow over 256 bytes or not. if we don't have
            # this check, the program tries to calculate rsa signature for
            # whatever multi-megabyte file the user is trying to open,
            # which would take $BIGNUM time.
            if len(s) > (64 + 256 + 32):
                raise BlyteError("too long")

            dig = sha.new(s[:64]).digest()
            d = decrypt(s[64:], License.pubExp, License.pubMod)

            if d != dig:
                raise BlyteError("corrupt data")
                          
            if ord(s[0]) != 2:
                raise BlyteError("incorrect version")

            t = ord(s[1])
            if t not in (License.STANDARD, License.PRODUCTION):
                raise BlyteError("incorrect type")

            ld = datetime.date(2000, 1, 1) + datetime.timedelta(days =
                (ord(s[2]) << 8) | ord(s[3]))

            uid = s[4:64]

            return License(t, ld, uid)
                
        except BlyteError, e:
            wxMessageBox("Invalid license: %s" % e, "Error", wxOK,
                         frame)

            return None

    fromStr = staticmethod(fromStr)

    def getTypeStr(self):
        if self.type == License.STANDARD:
            return "Standard"
        elif self.type == License.PRODUCTION:
            return "Production"
        else:
            return "Unknown"

# do RSA algorithm to s, which is a string, with modulo n and exponent e,
# and return the resulting string. s must not start with byte 0x00.
def crypt(s, e, n):
    m = 0
    for i in range(len(s)):
        m = (m << 8L) + ord(s[i])

    #assert m < n
    res = pow(m, e, n)

    s2 = ""
    while res != 0:
        s2 += chr(res & 0xFF)
        res >>= 8

    # reverses the string
    return s2[::-1]

# reverse of encrypt (see tools/make_license.py), takes out the extra byte
# from the result.
def decrypt(s, e, n):
    return crypt(s, e, n)[1:]
    
# simple timer class for use during development only
class TimerDev:

    # how many TimerDev instances are currently in existence
    nestingLevel = 0
    
    def __init__(self, msg = ""):
        self.msg = msg 
        self.__class__.nestingLevel += 1
        self.t = time.time()

    def __del__(self):
        self.t = time.time() - self.t
        self.__class__.nestingLevel -= 1
        print "%s%s took %.5f seconds" % (" " * self.__class__.nestingLevel,
                                          self.msg, self.t)

# show PDF document 'pdfData' in an external viewer program. writes out a
# temporary file, first deleting all old temporary files, then opens PDF
# viewer application. 'mainFrame' is used as a parent for message boxes in
# case there are any errors.
def showTempPDF(pdfData, cfg, mainFrame):

    try:
        try:
            removeTempFiles(misc.tmpPrefix)

            fd, filename = tempfile.mkstemp(prefix = misc.tmpPrefix,
                                            suffix = ".pdf")

            try:
                os.write(fd, pdfData)
            finally:
                os.close(fd)

            showPDF(filename, cfg, mainFrame)

        except IOError, (errno, strerror):
            raise MiscError("IOError: %s" % strerror)

    except BlyteError, e:
        wxMessageBox("Error writing temporary PDF file: %s" % e,
                     "Error", wxOK, mainFrame)

# show PDF file.
def showPDF(filename, cfg, frame):
    try:
        os.stat(cfg.pdfViewerPath)
    except OSError:
        wxMessageBox("PDF viewer application not found.\n\n"
                     "You can change your PDF settings\n"
                     "at File/Settings/PDF.", "Error", wxOK, frame)

        return
    
    # on Windows, Acrobat complains about "invalid path" if we
    # give the full path of the program as first arg, so give a
    # dummy arg.
    args = ["pdf"] + cfg.pdfViewerArgs.split() + [filename]
    
    os.spawnv(os.P_NOWAIT, cfg.pdfViewerPath, args)
