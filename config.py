# see fileformat.txt for more detailed information about the various
# defines found here.

from error import *
from wxPython.wx import *

# linebreak types
LB_AUTO_SPACE = 1
LB_AUTO_NONE = 2
LB_FORCED = 3
LB_LAST = 4

# mapping from character to linebreak
_text2lb = {
    '>' : LB_AUTO_SPACE,
    '&' : LB_AUTO_NONE,
    '|' : LB_FORCED,
    '.' : LB_LAST
    }

# reverse to above, filled in _init
_lb2text = { }

# line types
SCENE = 1
ACTION = 2
CHARACTER = 3
DIALOGUE = 4
PAREN = 5
TRANSITION = 6

# mapping from character to line type
_text2linetype = {
    '\\' : SCENE,
    '.' : ACTION,
    '_' : CHARACTER,
    ':' : DIALOGUE,
    '(' : PAREN,
    '/' : TRANSITION
    }

# reverse to above, filled in init
_linetype2text = { }

class Type:
    def __init__(self):
        self.type = None
        self.name = None
        self.emptyLinesBefore = 0

        self.indent = 0
        self.width = 0

        self.isCaps = False
        self.isBold = False
        self.isItalic = False
        self.isUnderlined = False

        # what's the next type from this type. used in figuring out what
        # type of element to insert when user presses enter.
        self.nextType = None

        # what element to switch to when user hits tab / shift-tab.
        self.nextTypeTab = None
        self.prevTypeTab = None

# type-specific stuff that are wxwindows objects, so can't be in normal
# Type (deepcopy dies)
class TypeGui:
    def __init__(self):
        self.font = None

class Config:
    def __init__(self):

        # type configs, key = line type, value = Type
        self.types = { }
        
        # vertical distance between rows, in pixels
        self.fontYdelta = 18

        # offsets from upper left corner of main widget, ie. this much empty
        # space is left on the top and left sides.
        self.offsetY = 10
        self.offsetX = 10

        
        # construct reverse lookup tables
        for k, v in _text2lb.items():
            _lb2text[v] = k

        for k, v in _text2linetype.items():
            _linetype2text[v] = k

        # element types
        t = Type()
        t.type = SCENE
        t.name = "Scene"
        t.emptyLinesBefore = 1
        t.indent = 0 
        t.width = 60
        t.isCaps = True
        t.isBold = True
        t.nextType = ACTION
        t.nextTypeTab = ACTION
        t.prevTypeTab = TRANSITION
        self.types[t.type] = t

        t = Type()
        t.type = ACTION
        t.name = "Action"
        t.emptyLinesBefore = 1
        t.indent = 0
        t.width = 60
        t.nextType = ACTION
        t.nextTypeTab = CHARACTER
        t.prevTypeTab = CHARACTER
        self.types[t.type] = t

        t = Type()
        t.type = CHARACTER
        t.name = "Character"
        t.emptyLinesBefore = 1
        t.indent = 25
        t.width = 20
        t.isCaps = True
        t.nextType = DIALOGUE
        t.nextTypeTab = ACTION
        t.prevTypeTab = ACTION
        self.types[t.type] = t

        t = Type()
        t.type = DIALOGUE
        t.name = "Dialogue"
        t.emptyLinesBefore = 0
        t.indent = 10
        t.width = 35
        t.nextType = CHARACTER
        t.nextTypeTab = PAREN
        t.prevTypeTab = ACTION
        self.types[t.type] = t

        t = Type()
        t.type = PAREN
        t.name = "Parenthetical"
        t.emptyLinesBefore = 0
        t.indent = 20
        t.width = 25
        t.nextType = DIALOGUE
        t.nextTypeTab = CHARACTER
        t.prevTypeTab = DIALOGUE
        self.types[t.type] = t

        t = Type()
        t.type = TRANSITION
        t.name = "Transition"
        t.emptyLinesBefore = 1
        t.indent = 55
        t.width = 15
        t.isCaps = True
        t.nextType = SCENE
        t.nextTypeTab = SCENE
        t.prevTypeTab = CHARACTER
        self.types[t.type] = t

        # FIXME: use a different one in Windows
        self.nativeFont = "0;-adobe-courier-medium-r-normal-*-*-140-*-*-m-*-iso8859-1"

        self.bgColor = wxColour(204, 204, 204)
        self.selectedColor = wxColour(128, 192, 192)
        self.cursorColor = wxColour(205, 0, 0)
        self.autoCompFgColor = wxColour(0, 0, 0)
        self.autoCompBgColor = wxColor(249, 222, 99)
        self.pagebreakColor = wxColour(128, 128, 128)

    def getType(self, type):
        return self.types[type]

# config stuff that are wxwindows objects, so can't be in normal
# Config (deepcopy dies)
class ConfigGui:

    # constants
    constantsInited = False
    bluePen = None
    redColor = None
    blackColor = None
    
    def __init__(self, cfg):

        if not ConfigGui.constantsInited:
            ConfigGui.bluePen = wxPen(wxColour(0, 0, 255))
            ConfigGui.redColor = wxColour(255, 0, 0)
            ConfigGui.blackColor = wxColour(0, 0, 0)

            ConfigGui.constantsInited = True
            
        # type-gui configs, key = line type, value = TypeGui
        self.types = { }

        nfi = wxNativeFontInfo()
        nfi.FromString(cfg.nativeFont)
        font = wxFontFromNativeInfo(nfi)

        dc = wxMemoryDC()
        dc.SetFont(font)
        self.fontX, self.fontY = dc.GetTextExtent("O")

        self.bgBrush = wxBrush(cfg.bgColor)
        self.bgPen = wxPen(cfg.bgColor)

        self.selectedBrush = wxBrush(cfg.selectedColor)
        self.selectedPen = wxPen(cfg.selectedColor)

        self.cursorBrush = wxBrush(cfg.cursorColor)
        self.cursorPen = wxPen(cfg.cursorColor)

        self.autoCompPen = wxPen(cfg.autoCompFgColor)
        self.autoCompBrush = wxBrush(cfg.autoCompBgColor)
        self.autoCompRevPen = wxPen(cfg.autoCompBgColor)
        self.autoCompRevBrush = wxBrush(cfg.autoCompFgColor)

        self.pagebreakPen = wxPen(cfg.pagebreakColor, style = wxSHORT_DASH)

        for t in cfg.types.values():
            tg = TypeGui()
            
            nfi = wxNativeFontInfo()
            nfi.FromString(cfg.nativeFont)
            
            if t.isBold:
                nfi.SetWeight(wxBOLD)
            else:
                nfi.SetWeight(wxNORMAL)

            if t.isItalic:
                nfi.SetStyle(wxITALIC)
            else:
                nfi.SetStyle(wxNORMAL)

            nfi.SetUnderlined(t.isUnderlined)
            
            tg.font = wxFontFromNativeInfo(nfi)
            self.types[t.type] = tg

    def getType(self, type):
        return self.types[type]

def _conv(dict, key):
    val = dict.get(key)
    if val == None:
        raise ConfigError("key '%s' not found from '%s'" % (key, dict))
    
    return val

def text2lb(str):
    return _conv(_text2lb, str)

def lb2text(lb):
    return _conv(_lb2text, lb)

def text2linetype(str):
    return _conv(_text2linetype, str)

def linetype2text(type):
    return _conv(_linetype2text, type)
