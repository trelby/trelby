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
SHOT = 7
NOTE = 8

# mapping from character to line type
_text2linetype = {
    '\\' : SCENE,
    '.' : ACTION,
    '_' : CHARACTER,
    ':' : DIALOGUE,
    '(' : PAREN,
    '/' : TRANSITION,
    '=' : SHOT,
    '%' : NOTE
    }

# reverse to above, filled in init
_linetype2text = { }

# page break indicators
PBI_NONE = 0
PBI_REAL = 1
PBI_REAL_AND_UNADJ = 2

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

        # what type of element to insert when user presses enter or tab.
        self.newTypeEnter = None
        self.newTypeTab = None

        # what element to switch to when user hits tab / shift-tab.
        self.nextTypeTab = None
        self.prevTypeTab = None

        # auto-completion stuff, only used for some element types
        self.doAutoComp = False
        self.autoCompList = []

# type-specific stuff that are wxwindows objects, so can't be in normal
# Type (deepcopy dies)
class TypeGui:
    def __init__(self):
        self.font = None

class Config:
    def __init__(self):

        # type configs, key = line type, value = Type
        self.types = { }

        # color list, key = color description, value = attribute name
        self.colors = { }
        
        # vertical distance between rows, in pixels
        self.fontYdelta = 18

        # offsets from upper left corner of main widget, ie. this much empty
        # space is left on the top and left sides.
        self.offsetY = 10
        self.offsetX = 10

        # paper size
        self.paperType = "A4"
        self.paperWidth = 210.0
        self.paperHeight = 297.0

        # margins
        self.marginTop = 12.7
        self.marginBottom = 25.4
        self.marginLeft = 38.1
        self.marginRight = 25.4

        # whether to auto-capitalize start of sentences
        self.capitalize = True

        # how many lines to scroll per mouse wheel event
        self.mouseWheelLines = 4
        
        # page break indicators to show
        self.pbi = PBI_REAL
        
        # interval (seconds) between automatic pagination (0 = disabled)
        # TODO: change this to 5 or something
        self.paginateInterval = 0
        
        # leave at least this many action lines on the end of a page
        self.pbActionLines = 2

        # leave at least this many dialogue lines on the end of a page
        self.pbDialogueLines = 2

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
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = ACTION
        t.prevTypeTab = TRANSITION
        t.doAutoComp = True
        self.types[t.type] = t

        t = Type()
        t.type = ACTION
        t.name = "Action"
        t.emptyLinesBefore = 1
        t.indent = 0
        t.width = 60
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
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
        t.newTypeEnter = DIALOGUE
        t.newTypeTab = PAREN
        t.nextTypeTab = ACTION
        t.prevTypeTab = ACTION
        t.doAutoComp = True
        self.types[t.type] = t

        t = Type()
        t.type = DIALOGUE
        t.name = "Dialogue"
        t.emptyLinesBefore = 0
        t.indent = 10
        t.width = 35
        t.newTypeEnter = CHARACTER
        t.newTypeTab = ACTION
        t.nextTypeTab = PAREN
        t.prevTypeTab = ACTION
        self.types[t.type] = t

        t = Type()
        t.type = PAREN
        t.name = "Parenthetical"
        t.emptyLinesBefore = 0
        t.indent = 20
        t.width = 25
        t.newTypeEnter = DIALOGUE
        t.newTypeTab = ACTION
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
        t.newTypeEnter = SCENE
        t.newTypeTab = TRANSITION
        t.nextTypeTab = SCENE
        t.prevTypeTab = CHARACTER
        t.doAutoComp = True
        t.autoCompList = [
            "CUT TO:",
            "DISSOLVE TO:",
            "FADE IN:",
            "FADE OUT",
            "FADE TO BLACK",
            "MATCH CUT TO:"
            ]
        self.types[t.type] = t

        t = Type()
        t.type = SHOT
        t.name = "Shot"
        t.emptyLinesBefore = 1
        t.indent = 0
        t.width = 60
        t.isCaps = True
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = ACTION
        t.prevTypeTab = SCENE
        self.types[t.type] = t
        
        t = Type()
        t.type = NOTE
        t.name = "Note"
        t.emptyLinesBefore = 1
        t.indent = 5
        t.width = 55
        t.isItalic = True
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = ACTION
        t.prevTypeTab = CHARACTER
        self.types[t.type] = t

        if wxPlatform == "__WXGTK__":
            self.nativeFont = "0;-adobe-courier-medium-r-normal-*-*-140-*-*-m-*-iso8859-1"
        elif wxPlatform == "__WXMSW__":
            self.nativeFont = "0;-16;0;0;0;400;0;0;0;0;3;2;1;49;Courier New"
        else:
            self.nativeFont = ""

        self.addColor("textColor", "Text foreground", 0, 0, 0)
        self.addColor("bgColor", "Text background", 204, 204, 204)
        self.addColor("selectedColor", "Selection", 128, 192, 192)
        self.addColor("searchColor", "Search result", 255, 127, 0)
        self.addColor("cursorColor", "Cursor", 205, 0, 0)
        self.addColor("autoCompFgColor", "Auto-completion foreground",
                      0, 0, 0)
        self.addColor("autoCompBgColor", "Auto-completion background",
                      249, 222, 99)
        self.addColor("noteColor", "Script note", 255, 255, 0)
        self.addColor("pagebreakColor", "Page-break line", 128, 128, 128)
        self.addColor("pagebreakNoAdjustColor",
            "Page-break (original, not adjusted) line", 128, 128, 128)

        self.recalc()

    # recalculate all variables dependent on other variables
    def recalc(self):
        h = self.paperHeight - self.marginTop - self.marginBottom

        # how many lines on a page. 12-point font = 6 lines per inch, ie.
        # 1 line = 4.2333333 mm
        self.linesOnPage = int(h / 4.2333333)

    def getType(self, type):
        return self.types[type]

    def addColor(self, name, descr, r, g, b):
        setattr(self, name, wxColour(r, g, b))
        self.colors[descr] = name
        
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

        self.textPen = wxPen(cfg.textColor)
        
        self.bgBrush = wxBrush(cfg.bgColor)
        self.bgPen = wxPen(cfg.bgColor)

        self.selectedBrush = wxBrush(cfg.selectedColor)
        self.selectedPen = wxPen(cfg.selectedColor)

        self.searchBrush = wxBrush(cfg.searchColor)
        self.searchPen = wxPen(cfg.searchColor)

        self.cursorBrush = wxBrush(cfg.cursorColor)
        self.cursorPen = wxPen(cfg.cursorColor)

        self.noteBrush = wxBrush(cfg.noteColor)
        self.notePen = wxPen(cfg.noteColor)

        self.autoCompPen = wxPen(cfg.autoCompFgColor)
        self.autoCompBrush = wxBrush(cfg.autoCompBgColor)
        self.autoCompRevPen = wxPen(cfg.autoCompBgColor)
        self.autoCompRevBrush = wxBrush(cfg.autoCompFgColor)

        self.pagebreakPen = wxPen(cfg.pagebreakColor)
        self.pagebreakNoAdjustPen = wxPen(cfg.pagebreakNoAdjustColor,
                                          style = wxDOT)

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

def _conv(dict, key, raiseException = True):
    val = dict.get(key)
    if (val == None) and raiseException:
        raise ConfigError("key '%s' not found from '%s'" % (key, dict))
    
    return val

def text2lb(str, raiseException = True):
    return _conv(_text2lb, str, raiseException)

def lb2text(lb):
    return _conv(_lb2text, lb)

def text2linetype(str, raiseException = True):
    return _conv(_text2linetype, str, raiseException)

def linetype2text(type):
    return _conv(_linetype2text, type)
