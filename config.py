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
        self.linetype = None
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
        
class Config:
    def __init__(self):

        # type configs, key = line type, value = Type
        self.types = { }
        
        # various non-user configurable (for now anyway) settings

        # font size values in pixels
        self.fontY = 14
        self.fontX = 9

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
        t.linetype = SCENE
        t.emptyLinesBefore = 1
        t.indent = 0 
        t.width = 60
        t.isCaps = True
        t.isBold = True
        t.nextType = ACTION
        t.nextTypeTab = ACTION
        t.prevTypeTab = TRANSITION
        self.types[t.linetype] = t

        t = Type()
        t.linetype = ACTION
        t.emptyLinesBefore = 1
        t.indent = 0
        t.width = 60
        t.nextType = ACTION
        t.nextTypeTab = CHARACTER
        t.prevTypeTab = CHARACTER
        self.types[t.linetype] = t

        t = Type()
        t.linetype = CHARACTER
        t.emptyLinesBefore = 1
        t.indent = 25
        t.width = 20
        t.isCaps = True
        t.nextType = DIALOGUE
        t.nextTypeTab = ACTION
        t.prevTypeTab = ACTION
        self.types[t.linetype] = t

        t = Type()
        t.linetype = DIALOGUE
        t.emptyLinesBefore = 0
        t.indent = 10
        t.width = 35
        t.nextType = CHARACTER
        t.nextTypeTab = PAREN
        t.prevTypeTab = ACTION
        self.types[t.linetype] = t

        t = Type()
        t.linetype = PAREN
        t.emptyLinesBefore = 0
        t.indent = 20
        t.width = 25
        t.nextType = DIALOGUE
        t.nextTypeTab = CHARACTER
        t.prevTypeTab = DIALOGUE
        self.types[t.linetype] = t

        t = Type()
        t.linetype = TRANSITION
        t.emptyLinesBefore = 1
        t.indent = 55
        t.width = 15
        t.isCaps = True
        t.nextType = SCENE
        t.nextTypeTab = SCENE
        t.prevTypeTab = CHARACTER
        self.types[t.linetype] = t

        # wxWindows stuff
        self.baseFont = wxFont(self.fontY, wxMODERN, wxNORMAL, wxNORMAL)
        self.sceneFont = wxFont(self.fontY, wxMODERN, wxNORMAL, wxBOLD)

        self.bluePen = wxPen(wxColour(0, 0, 255))
        self.redColor = wxColour(255, 0, 0)
        self.blackColor = wxColour(0, 0, 0)

        self.bgColor = wxColour(204, 204, 204)
        self.bgBrush = wxBrush(self.bgColor)
        self.bgPen = wxPen(self.bgColor)

        self.selectedColor = wxColour(128, 192, 192)
        self.selectedBrush = wxBrush(self.selectedColor)
        self.selectedPen = wxPen(self.selectedColor)

        self.cursorColor = wxColour(205, 0, 0)
        self.cursorBrush = wxBrush(self.cursorColor)
        self.cursorPen = wxPen(self.cursorColor)

        self.autoCompFgColor = wxColour(0, 0, 0)
        self.autoCompBgColor = wxColor(249, 222, 99)
        self.autoCompPen = wxPen(self.autoCompFgColor)
        self.autoCompBrush = wxBrush(self.autoCompBgColor)
        self.autoCompRevPen = wxPen(self.autoCompBgColor)
        self.autoCompRevBrush = wxBrush(self.autoCompFgColor)

        self.pagebreakPen = wxPen(wxColour(128, 128, 128),
                                  style = wxSHORT_DASH)

    def getTypeCfg(self, type):
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
