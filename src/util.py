# -*- coding: utf-8 -*-

import glob
import gzip
import misc
import os
import re
import tempfile
import time
import functools

if "TRELBY_TESTING" in os.environ:
    import unittest.mock as mock
    wx = mock.Mock()
else:
    import wx

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

# translate table that converts A-Z -> a-z, keeps a-z as they are, and
# converts everything else to z.
_normalize_tbl = ""

# identity table that maps each character to itself. used by deleteChars.
_identity_tbl = ""

# map some fancy unicode characters to their nearest ASCII/Latin-1
# equivalents so when people import text it's not mangled to uselessness
_fancy_unicode_map = {
#    ord('‘') : "'",
#    ord('’') : "'",
#    ord('“') : '"',
#    ord('”') : '"',
#    ord('—') : "--",
#    ord('–') : "-",
    }

# permanent memory DC to get text extents etc
permDc = None

def init(doWX = True):
    global _to_upper, _to_lower, _input_tbl, _normalize_tbl, _identity_tbl, \
           permDc

    # setup ISO-8859-1 case-conversion stuff
    tmpUpper = []
    tmpLower = []

    for i in range(256):
        tmpUpper.append(i)
        tmpLower.append(i)

    for k, v in _iso_8859_1_map.items():
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

    for i in range(256):
        # "a" - "z"
        if (i >= 97) and (i <= 122):
            ch = chr(i)
        # "A" - "Z"
        elif (i >= 65) and (i <= 90):
            # + 32 ("A" - "a") lowercases it
            ch = chr(i + 32)
        else:
            ch = "z"

        _normalize_tbl += ch

    _identity_tbl = "".join([chr(i) for i in range(256)])

    if doWX:
        # dunno if the bitmap needs to be big enough to contain the text
        # we're measuring...
        permDc = wx.MemoryDC()
        permDc.SelectObject(wx.Bitmap(512, 32))

# like string.upper/lower/capitalize, but we do our own charset-handling
# that doesn't need locales etc
def upper(s):
    return s.upper()

def lower(s):
    return s.lower()

def capitalize(s):
    return upper(s[:1]) + s[1:]

# return 's', which must be a unicode string, converted to a ISO-8859-1
# 8-bit string. characters not representable in ISO-8859-1 are discarded.
def toLatin1(s):
    return s.encode("ISO-8859-1", "ignore")

# return 's', which must be a string of ISO-8859-1 characters, converted
# to UTF-8.
def toUTF8(s):
    return s

# return 's', which must be a string of UTF-8 characters, converted to
# ISO-8859-1, with characters not representable in ISO-8859-1 discarded
# and any invalid UTF-8 sequences ignored.
def fromUTF8(s):
    return s

# returns True if kc (key-code) is a valid character to add to the script.
def isValidInputChar(kc):
    # [0x80, 0x9F] = unspecified control characters in ISO-8859-1, added
    # characters like euro etc in windows-1252. 0x7F = backspace, 0xA0 =
    # non-breaking space, 0xAD = soft hyphen.
    return (kc >= 32) and (kc <= 255) and not\
           ((kc >= 0x7F) and (kc < 0xA0)) and (kc != 0xAD)

# return s with all non-valid input characters converted to valid input
# characters, except form feeds, which are just deleted.
def toInputStr(s):
    return str(s).replace("\f", "").replace("\t", "|")

# replace fancy unicode characters with their ASCII/Latin1 equivalents.
def removeFancyUnicode(s):
    return s.translate(_fancy_unicode_map)

# transform external input (unicode) into a form suitable for having in a
# script
def cleanInput(s):
    return s

# replace s[start:start + width] with toInputStr(new) and return s
def replace(s, new, start, width):
    return s[0 : start] + toInputStr(new) + s[start + width:]

# delete all characters in 'chars' (a string) from s and return that.
def deleteChars(s, chars):
    for char in chars:
        s = s.replace(char, '')
    return s

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

# return percentage of 'val1' of 'val2' (both ints) as an int (50% -> 50
# etc.), or 0 if val2 is 0.
def pct(val1, val2):
    if val2 != 0:
        return (100 * val1) // val2
    else:
        return 0

# return percentage of 'val1' of 'val2' (both ints/floats) as a float (50%
# -> 50.0 etc.), or 0.0 if val2 is 0.0
def pctf(val1, val2):
    if val2 != 0.0:
        return (100.0 * val1) / val2
    else:
        return 0.0

# return float(val1) / val2, or 0.0 if val2 is 0.0
def safeDiv(val1, val2):
    if val2 != 0.0:
        return float(val1) / val2
    else:
        return 0.0

# return float(val1) / val2, or 0.0 if val2 is 0
def safeDivInt(val1, val2):
    if val2 != 0:
        return float(val1) / val2
    else:
        return 0.0

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

# return items, which is a list of ISO-8859-1 strings, as a single string
# with \n between each string. any \ characters in the individual strings
# are escaped as \\.
def escapeStrings(items):
    return "\\n".join([s.replace("\\", "\\\\") for s in items])

# opposite of escapeStrings. takes in a string, returns a list of strings.
def unescapeStrings(s):
    if not s:
        return []

    items = []

    tmp = ""
    i = 0
    while i < (len(s) - 1):
        ch = s[i]

        if ch != "\\":
            tmp += ch
            i += 1
        else:
            ch = s[i + 1]

            if ch == "n":
                items.append(tmp)
                tmp = ""
            else:
                tmp += ch

            i += 2

    if i < len(s):
        tmp += s[i]
        items.append(tmp)

    return items

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

# return string s escaped for use in RTF.
def escapeRTF(s):
    return s.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")

# convert mm to twips (1/1440 inch = 1/20 point).
def mm2twips(mm):
    # 56.69291 = 1440 / 25.4
    return mm * 56.69291

# TODO: move all GUI stuff to gutil

# return True if given font is a fixed-width one.
def isFixedWidth(font):
    return getTextExtent(font, "iiiii")[0] == getTextExtent(font, "OOOOO")[0]

# get extent of 's' as (w, h)
def getTextExtent(font, s):
    permDc.SetFont(font)

    # if we simply return permDc.GetTextExtent(s) from here, on some
    # versions of Windows we will incorrectly reject as non-fixed width
    # fonts (through isFixedWidth) some fonts that actually are fixed
    # width. it's especially bad because one of them is our default font,
    # "Courier New".
    #
    # these are the widths we get for the strings below for Courier New, italic:
    #
    # iiiii 40
    # iiiiiiiiii 80
    # OOOOO 41
    # OOOOOOOOOO 81
    #
    # we can see i and O are both 8 pixels wide, so the font is
    # fixed-width, but for whatever reason, on the O variants there is one
    # additional pixel returned in the width, no matter what the length of
    # the string is.
    #
    # to get around this, we actually call GetTextExtent twice, once with
    # the actual string we want to measure, and once with the string
    # duplicated, and take the difference between those two as the actual
    # width. this handily negates the one-extra-pixel returned and gives
    # us an accurate way of checking if a font is fixed width or not.
    #
    # it's a bit slower but this is not called from anywhere that's
    # performance critical.

    w1, h = permDc.GetTextExtent(s)
    w2 = permDc.GetTextExtent(s + s)[0]

    return (w2 - w1, h)

# get height of font in pixels
def getFontHeight(font):
    permDc.SetFont(font)
    return permDc.GetTextExtent("_\xC5")[1]

# return how many mm tall given font size is.
def getTextHeight(size):
    return (size / 72.0) * 25.4

# return how many mm wide given text is at given style with given size.
def getTextWidth(text, style, size):
    return (fontinfo.getMetrics(style).getTextWidth(text, size) / 72.0) * 25.4

# create a font that's height is at most 'height' pixels. other parameters
# are the same as in wx.Font's constructor.
def createPixelFont(height, family, style, weight):
    fs = 6

    selected = fs
    closest = 1000
    over = 0

    # FIXME: what's this "keep trying even once we go over the max height"
    # stuff? get rid of it.
    while 1:
        fn = wx.Font(fs, family, style, weight,
                     encoding = wx.FONTENCODING_ISO8859_1)
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

    return wx.Font(selected, family, style, weight,
                   encoding = wx.FONTENCODING_ISO8859_1)

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

    ctrl.SetMinSize(wx.Size(size.width, size.height))
    ctrl.SetClientSize(size.width, size.height)

# wxMSW doesn't respect the control's min/max values at all, so we have to
# implement this ourselves
def getSpinValue(spinCtrl):
    tmp = clamp(spinCtrl.GetValue(), spinCtrl.GetMin(), spinCtrl.GetMax())
    spinCtrl.SetValue(tmp)

    return tmp

# return True if c is not a word character, i.e. is either empty, not an
# alphanumeric character or a "'", or is more than one character.
def isWordBoundary(c):
    if len(c) != 1:
        return True

    if c == "'":
        return False

    return not isAlnum(c)

# return True if c is an alphanumeric character
def isAlnum(c):
    return str(c).isalnum()

# make sure s (unicode) ends in suffix (case-insensitively) and return
# that. suffix must already be lower-case.
def ensureEndsIn(s, suffix):
    if s.lower().endswith(suffix):
        return s
    else:
        return s + suffix

# return string 's' split into words (as a list), using isWordBoundary.
def splitToWords(s):
    tmp = ""

    for c in s:
        if isWordBoundary(c):
            tmp += " "
        else:
            tmp += c

    return tmp.split()

# return two-character prefix of s, using characters a-z only. len(s) must
# be at least 2.
def getWordPrefix(s):
    return s[:2].translate(_normalize_tbl)

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

def cmpfunc(a, b):
    return (a > b) - (a < b)

# put everything from dictionary d into a list as (key, value) tuples,
# then sort the list and return that. by default sorts by "desc(value)
# asc(key)", but a custom sort function can be given
def sortDict(d, sortFunc = None):
    def tmpSortFunc(o1, o2):
        ret = cmpfunc(o2[1], o1[1])

        if ret != 0:
            return ret
        else:
            return cmpfunc(o1[0], o2[0])

    if sortFunc == None:
        sortFunc = tmpSortFunc

    tmp = []
    for k, v in d.items():
        tmp.append((k, v))

    tmp = sorted(tmp, key=functools.cmp_to_key(sortFunc))

    return tmp

# an efficient FIFO container of fixed size. can't contain None objects.
class FIFO:
    def __init__(self, size):
        self.arr = [None] * size

        # index of next slot to fill
        self.next = 0

    # add item
    def add(self, obj):
        self.arr[self.next] = obj
        self.next += 1

        if self.next >= len(self.arr):
            self.next = 0

    # get contents as a list, in LIFO order.
    def get(self):
        tmp = []

        j = self.next - 1

        for i in range(len(self.arr)):
            if j < 0:
                j = len(self.arr) - 1

            obj = self.arr[j]

            if  obj != None:
                tmp.append(obj)

            j -= 1

        return tmp

# DrawLine-wrapper that makes it easier when the end-point is just
# offsetted from the starting point
def drawLine(dc, x, y, xd, yd):
    dc.DrawLine(x, y, x + xd, y + yd)

# draws text aligned somehow. returns a (w, h) tuple of the text extent.
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

    return (w, h)

# create pad sizer for given window whose controls are in topSizer, with
# 'pad' pixels of padding on each side, resize window to correct size, and
# optionally center it.
def finishWindow(window, topSizer, pad = 10, center = True):
    padSizer = wx.BoxSizer(wx.VERTICAL)
    padSizer.Add(topSizer, 1, wx.EXPAND | wx.ALL, pad)
    window.SetSizerAndFit(padSizer)
    window.Layout()

    if center:
        window.Center()

# wx.Colour replacement that can safely be copy.deepcopy'd
class MyColor:
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def toWx(self):
        return wx.Colour(self.r, self.g, self.b)

    @staticmethod
    def fromWx(c):
        o = MyColor(0, 0, 0)

        o.r = c.Red()
        o.g = c.Green()
        o.b = c.Blue()

        return o

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

# one key press
class Key:
    keyMap = {
        1 : "A",
        2 : "B",
        3 : "C",
        4 : "D",
        5 : "E",
        6 : "F",
        7 : "G",

        # CTRL+Enter = 10 in Windows
        10 : "Enter (Windows)",

        11 : "K",
        12 : "L",
        14 : "N",
        15 : "O",
        16 : "P",
        17 : "Q",
        18 : "R",
        19 : "S",
        20 : "T",
        21 : "U",
        22 : "V",
        23 : "W",
        24 : "X",
        25 : "Y",
        26 : "Z",
        wx.WXK_BACK : "Backspace",
        wx.WXK_TAB : "Tab",
        wx.WXK_RETURN : "Enter",
        wx.WXK_ESCAPE : "Escape",
        wx.WXK_DELETE : "Delete",
        wx.WXK_END : "End",
        wx.WXK_HOME : "Home",
        wx.WXK_LEFT : "Left",
        wx.WXK_UP : "Up",
        wx.WXK_RIGHT : "Right",
        wx.WXK_DOWN : "Down",
        wx.WXK_PAGEUP : "Page up",
        wx.WXK_PAGEDOWN : "Page down",
        wx.WXK_INSERT : "Insert",
        wx.WXK_F1 : "F1",
        wx.WXK_F2 : "F2",
        wx.WXK_F3 : "F3",
        wx.WXK_F4 : "F4",
        wx.WXK_F5 : "F5",
        wx.WXK_F6 : "F6",
        wx.WXK_F7 : "F7",
        wx.WXK_F8 : "F8",
        wx.WXK_F9 : "F9",
        wx.WXK_F10 : "F10",
        wx.WXK_F11 : "F11",
        wx.WXK_F12 : "F12",
        wx.WXK_F13 : "F13",
        wx.WXK_F14 : "F14",
        wx.WXK_F15 : "F15",
        wx.WXK_F16 : "F16",
        wx.WXK_F17 : "F17",
        wx.WXK_F18 : "F18",
        wx.WXK_F19 : "F19",
        wx.WXK_F20 : "F20",
        wx.WXK_F21 : "F21",
        wx.WXK_F22 : "F22",
        wx.WXK_F23 : "F23",
        wx.WXK_F24 : "F24",
        }

    def __init__(self, kc, ctrl = False, alt = False, shift = False):

        # we don't want to handle ALT+a/ALT+A etc separately, so uppercase
        # input char combinations
        if (kc < 256) and (ctrl or alt):
            kc = ord(upper(chr(kc)))

        # even though the wxWidgets documentation clearly states that
        # CTRL+[A-Z] should be returned as keycodes 1-26, wxGTK2 2.6 does
        # not do this (wxGTK1 and wxMSG do follow the documentation).
        #
        # so, we normalize to the wxWidgets official form here if necessary.

        # "A" - "Z"
        if ctrl and (kc >= 65) and (kc <= 90):
            kc -= 64

        # ASCII/Latin-1 keycode (0-255) or one of the wx.WXK_ constants (>255)
        self.kc = kc

        self.ctrl = ctrl
        self.alt = alt
        self.shift = shift

    # returns True if key is a valid input character
    def isValidInputChar(self):
        return not self.ctrl and not self.alt and isValidInputChar(self.kc)

    # toInt/fromInt serialize/deserialize to/from a 35-bit integer, laid
    # out like this:
    # bits 0-31:  keycode
    #        32:  Control
    #        33:  Alt
    #        34:  Shift

    def toInt(self):
        return (self.kc & 0xFFFFFFFF) | (self.ctrl << 32) | \
               (self.alt << 33) | (self.shift << 34)

    @staticmethod
    def fromInt(val):
        return Key(val & 0xFFFFFFFF, (val >> 32) & 1, (val >> 33) & 1,
                   (val >> 34) & 1)

    # construct from wx.KeyEvent
    @staticmethod
    def fromKE(ev):
        return Key(ev.GetKeyCode(), ev.ControlDown(), ev.AltDown(),
                   ev.ShiftDown())

    def toStr(self):
        s = ""

        if self.ctrl:
            s += "CTRL+"

        if self.alt:
            s += "ALT+"

        if self.shift:
            s += "SHIFT+"

        if isValidInputChar(self.kc):
            if self.kc == wx.WXK_SPACE:
                s += "Space"
            else:
                s += chr(self.kc)
        else:
            kname = self.__class__.keyMap.get(self.kc)

            if kname:
                s += kname
            else:
                s += "UNKNOWN(%d)" % self.kc

        return s

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
        f = open(misc.toPath(filename), "r", encoding='UTF-8')

        try:
            ret = f.read(maxSize)
        finally:
            f.close()

    except IOError as xxx_todo_changeme:
        (errno, strerror) = xxx_todo_changeme.args
        wx.MessageBox("Error loading file '%s': %s" % (
                filename, strerror), "Error", wx.OK, frame)
        ret = None

    return ret

# like loadFile, but if file doesn't exist, tries to load a .gz compressed
# version of it.
def loadMaybeCompressedFile(filename, frame):
    doGz = False

    if not fileExists(filename):
        filename += ".gz"
        doGz = True

    if not doGz:
        s = loadFile(filename, frame)
        return s

    try:
        f = gzip.open(filename, 'r')
        return f.read().decode('utf-8')
    except:
        wx.MessageBox("Error loading file '%s': Decompression failed" % \
                          filename, "Error", wx.OK, frame)
        return None

# write 'data' to 'filename', popping up a messagebox using 'frame' as
# parent on errors. returns True on success.
def writeToFile(filename, data, frame):
    try:
        f = open(misc.toPath(filename), "wb")

        try:
            if isinstance(data, str):
                f.write(data.encode("UTF-8"))
            else:
                f.write(data)
        finally:
            f.close()

        return True

    except IOError as xxx_todo_changeme1:
        (errno, strerror) = xxx_todo_changeme1.args
        wx.MessageBox("Error writing file '%s': %s" % (
                filename, strerror), "Error", wx.OK, frame)

        return False

def removeTempFiles(prefix):
    files = glob.glob(tempfile.gettempdir() + "/%s*" % prefix)

    for fn in files:
        try:
            os.remove(fn)
        except OSError:
            continue

# return True if given file exists.
def fileExists(filename):
    try:
        os.stat(misc.toPath(filename))
    except OSError:
        return False

    return True

# look for file 'filename' in all the directories listed in 'dirs', which
# is a list of absolute directory paths. if found, return the absolute
# filename, otherwise None.
def findFile(filename, dirs):
    for d in dirs:
        if d[-1] != "/":
            d += "/"

        path = d + filename

        if fileExists(path):
            return path

    return None

# look for file 'filename' in all the directories listed in $PATH. if
# found, return the absolute filename, otherwise None.
def findFileInPath(filename):
    dirs = os.getenv("PATH")
    if not dirs:
        return None

    # I have no idea how one should try to cope if PATH contains entries
    # with non-UTF8 characters, so just ignore any errors
    dirs = str(dirs).split(":")

    # only accept absolute paths. this strips out things like "~/bin/"
    # etc.
    dirs = [d for d in dirs if d and d[0] == "/"]

    return findFile(filename, dirs)

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
        print("%s%s took %.5f seconds" % (" " * self.__class__.nestingLevel,
                                          self.msg, self.t))

# Get the Windows default PDF viewer path from registry and return that,
# or None on errors.
def getWindowsPDFViewer():
    try:
        import winreg

        # HKCR/.pdf: gives the class of the PDF program.
        # Example : AcroRead.Document or FoxitReader.Document

        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".pdf")
        pdfClass = winreg.QueryValue(key, "")

        # HKCR/<class>/shell/open/command: the path to the PDF viewer program
        # Example: "C:\Program Files\Acrobat 8.0\acroread.exe" "%1"

        key2 = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT, pdfClass + r"\shell\open\command")

        # Almost every PDF program out there accepts passing the PDF path
        # as the argument, so we don't parse the arguments from the
        # registry, just get the program path.

        path = winreg.QueryValue(key2, "").split('"')[1]

        if fileExists(path):
            return path
    except:
        pass

    return None

# get a windows environment variable in its native unicode format, or None
# if not found
def getWindowsUnicodeEnvVar(name):
    import ctypes

    n = ctypes.windll.kernel32.GetEnvironmentVariableW(name, None, 0)

    if n == 0:
        return None

    buf = ctypes.create_unicode_buffer("\0" * n)
    ctypes.windll.kernel32.GetEnvironmentVariableW(name, buf, n)

    return buf.value

# show PDF file.
def showPDF(filename, cfgGl, frame):
    def complain():
        wx.MessageBox("PDF viewer application not found.\n\n"
                      "You can change your PDF viewer\n"
                      "settings at File/Settings/Change/Misc.",
                      "Error", wx.OK, frame)

    pdfProgram = cfgGl.pdfViewerPath
    pdfArgs = cfgGl.pdfViewerArgs

    # If configured pdf viewer does not exist, try finding one
    # automatically
    if not fileExists(pdfProgram):
        found = False

        if misc.isWindows:
            regPDF = getWindowsPDFViewer()

            if regPDF:
                wx.MessageBox(
                    "Currently set PDF viewer (%s) was not found.\n"
                    "Change this in File/Settings/Change/Misc.\n\n"
                    "Using the default PDF viewer for Windows instead:\n"
                    "%s" % (pdfProgram, regPDF),
                    "Warning", wx.OK, frame)

                pdfProgram = regPDF
                pdfArgs = ""

                found = True

        if not found:
            complain()

            return

    # on Windows, Acrobat complains about "invalid path" if we
    # give the full path of the program as first arg, so give a
    # dummy arg.
    args = ["pdf"] + pdfArgs.split() + [filename]

    # there's a race condition in checking if the path exists, above, and
    # using it, below. if the file disappears between those two we get an
    # OSError exception from spawnv, so we need to catch it and handle it.

    # TODO: spawnv does not support Unicode paths as of this moment
    # (Python 2.4). for now, convert it to UTF-8 and hope for the best.
    try:
        os.spawnv(os.P_NOWAIT, pdfProgram.encode("UTF-8"), args)
    except OSError:
        complain()
