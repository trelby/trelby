# see fileformat.txt for more detailed information about the various
# defines found here.

from error import *
import misc
import util

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
_text2lt = {
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
_lt2text = { }

# page break indicators
PBI_NONE = 0
PBI_REAL = 1
PBI_REAL_AND_UNADJ = 2

class TextType:
    def __init__(self):
        self.isCaps = False
        self.isBold = False
        self.isItalic = False
        self.isUnderlined = False

class Type:
    def __init__(self):
        # line type
        self.lt = None

        # textual description
        self.name = None

        self.emptyLinesBefore = 0

        self.indent = 0
        self.width = 0

        # text types, one for screen and one for export
        self.screen = TextType()
        self.export = TextType()
        
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
        
        # prefix used for temp files
        self.tmpPrefix = "oskusoft-blyte-tmp-"

        # offsets from upper left corner of main widget, ie. this much empty
        # space is left on the top and left sides.
        self.offsetY = 10
        self.offsetX = 10

        # integer/floating-point variables, with default, minimum and
        # maximum values
        self.numberVars = {

            # not used perse, but listed here so that we can easily query
            # min/max values for these in various places
            "elementEmptyLinesBefore" : (0, 0, 5),
            "elementIndent" : (0, 0, 80),
            "elementWidth" : (5, 5, 80),

            # vertical distance between rows, in pixels
            "fontYdelta" : (18, 4, 125),
            
            # font size used for PDF generation, in points
            "fontSize" : (12, 4, 72),

            # margins
            "marginBottom" : (25.4, 0.0, 900.0),
            "marginLeft" : (38.1, 0.0, 900.0),
            "marginRight" : (25.4, 0.0, 900.0),
            "marginTop" : (12.7, 0.0, 900.0),
            
            # how many lines to scroll per mouse wheel event
            "mouseWheelLines" : (4, 1, 50),
            
            # interval in seconds between automatic pagination (0 = disabled)
            # TODO: change this to 5 or something
            "paginateInterval" : (0, 0, 60),

            # paper size
            "paperHeight" : (297.0, 100.0, 1000.0),
            "paperWidth" : (210.0, 50.0, 1000.0),
            
            # leave at least this many action lines on the end of a page
            "pbActionLines" : (2, 1, 30),
            
            # leave at least this many dialogue lines on the end of a page
            "pbDialogueLines" : (2, 1, 30),
            }

        for k, v in self.numberVars.iteritems():
            setattr(self, k, v[0])
            
        # paper type
        self.paperType = "A4"

        # whether to check script for errors before export / print
        self.checkOnExport = True
        
        # whether to auto-capitalize start of sentences
        self.capitalize = True

        # page break indicators to show
        self.pbi = PBI_REAL
        
        # PDF viewer program and args
        if misc.isUnix:
            self.pdfViewerPath = "/usr/local/Acrobat5/bin/acroread"
            self.pdfViewerArgs = [ "-tempFile" ]
        elif misc.isWindows:
            self.pdfViewerPath = "C:\\Program Files\\Adobe\\Acrobat 6.0\\Reader\\AcroRd32.exe"
            self.pdfViewerArgs = [""]
        else:
            self.pdfViewerPath = "not set yet (unknown platform %s)"\
                                 % wxPlatform
            self.pdfViewerArgs = []

        # whether to draw rectangle showing margins
        self.pdfShowMargins = False

        # whether to show line numbers next to each line
        self.pdfShowLineNumbers = False
        
        # construct reverse lookup tables
        for k, v in _text2lb.items():
            _lb2text[v] = k

        for k, v in _text2lt.items():
            _lt2text[v] = k

        # element types
        t = Type()
        t.lt = SCENE
        t.name = "Scene"
        t.emptyLinesBefore = 1
        t.indent = 0 
        t.width = 60
        t.screen.isCaps = True
        t.screen.isBold = True
        t.export.isCaps = True
        t.export.isBold = True
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = ACTION
        t.prevTypeTab = TRANSITION
        t.doAutoComp = True
        self.types[t.lt] = t

        t = Type()
        t.lt = ACTION
        t.name = "Action"
        t.emptyLinesBefore = 1
        t.indent = 0
        t.width = 60
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = CHARACTER
        t.prevTypeTab = CHARACTER
        self.types[t.lt] = t

        t = Type()
        t.lt = CHARACTER
        t.name = "Character"
        t.emptyLinesBefore = 1
        t.indent = 25
        t.width = 20
        t.screen.isCaps = True
        t.export.isCaps = True
        t.newTypeEnter = DIALOGUE
        t.newTypeTab = PAREN
        t.nextTypeTab = ACTION
        t.prevTypeTab = ACTION
        t.doAutoComp = True
        self.types[t.lt] = t

        t = Type()
        t.lt = DIALOGUE
        t.name = "Dialogue"
        t.emptyLinesBefore = 0
        t.indent = 10
        t.width = 35
        t.newTypeEnter = CHARACTER
        t.newTypeTab = ACTION
        t.nextTypeTab = PAREN
        t.prevTypeTab = ACTION
        self.types[t.lt] = t

        t = Type()
        t.lt = PAREN
        t.name = "Parenthetical"
        t.emptyLinesBefore = 0
        t.indent = 20
        t.width = 25
        t.newTypeEnter = DIALOGUE
        t.newTypeTab = ACTION
        t.nextTypeTab = CHARACTER
        t.prevTypeTab = DIALOGUE
        self.types[t.lt] = t

        t = Type()
        t.lt = TRANSITION
        t.name = "Transition"
        t.emptyLinesBefore = 1
        t.indent = 45
        t.width = 20
        t.screen.isCaps = True
        t.export.isCaps = True
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
        self.types[t.lt] = t

        t = Type()
        t.lt = SHOT
        t.name = "Shot"
        t.emptyLinesBefore = 1
        t.indent = 0
        t.width = 60
        t.screen.isCaps = True
        t.export.isCaps = True
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = ACTION
        t.prevTypeTab = SCENE
        self.types[t.lt] = t
        
        t = Type()
        t.lt = NOTE
        t.name = "Note"
        t.emptyLinesBefore = 1
        t.indent = 5
        t.width = 55
        t.screen.isItalic = True
        t.export.isItalic = True
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = ACTION
        t.prevTypeTab = CHARACTER
        self.types[t.lt] = t

        if misc.isUnix:
            self.nativeFont = "0;-adobe-courier-medium-r-normal-*-*-140-*-*-m-*-iso8859-1"
        elif misc.isWindows:
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

    # get default value of a numeric setting
    def getDefault(self, name):
        return self.numberVars[name][0]
        
    # get minimum value of a numeric setting
    def getMin(self, name):
        return self.numberVars[name][1]
        
    # get maximum value of a numeric setting
    def getMax(self, name):
        return self.numberVars[name][2]
        
    # get minimum and maximum value of a numeric setting as a (min,max)
    # tuple.
    def getMinMax(self, name):
        return (self.getMin(name), self.getMax(name))
        
    # fix up all invalid config values and recalculate all variables
    # dependent on other variables.
    def recalc(self):
        for k, v in self.numberVars.iteritems():
            util.clampObj(self, k, v[1], v[2])

        for el in self.types.itervalues():
            util.clampObj(el, "emptyLinesBefore",
                          *self.getMinMax("elementEmptyLinesBefore"))
            util.clampObj(el, "indent", *self.getMinMax("elementIndent"))
            util.clampObj(el, "width", *self.getMinMax("elementWidth"))
            
        # make sure usable space on the page isn't too small
        if (self.marginTop + self.marginBottom) >= (self.paperHeight - 100.0):
            self.marginTop = 0.0
            self.marginBottom = 0.0
            
        h = self.paperHeight - self.marginTop - self.marginBottom

        # how many lines on a page
        self.linesOnPage = int(h / util.points2y(self.fontSize))

    def getType(self, lt):
        return self.types[lt]

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
            
            if t.screen.isBold:
                nfi.SetWeight(wxBOLD)
            else:
                nfi.SetWeight(wxNORMAL)

            if t.screen.isItalic:
                nfi.SetStyle(wxITALIC)
            else:
                nfi.SetStyle(wxNORMAL)

            nfi.SetUnderlined(t.screen.isUnderlined)
            
            tg.font = wxFontFromNativeInfo(nfi)
            self.types[t.lt] = tg

    def getType(self, lt):
        return self.types[lt]

def _conv(dict, key, raiseException = True):
    val = dict.get(key)
    if (val == None) and raiseException:
        raise ConfigError("key '%s' not found from '%s'" % (key, dict))
    
    return val

def text2lb(str, raiseException = True):
    return _conv(_text2lb, str, raiseException)

def lb2text(lb):
    return _conv(_lb2text, lb)

def text2lt(str, raiseException = True):
    return _conv(_text2lt, str, raiseException)

def lt2text(lt):
    return _conv(_lt2text, lt)
