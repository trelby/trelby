# see fileformat.txt for more detailed information about the various
# defines found here.

from error import *
import misc
import mypickle
import util

from wxPython.wx import *

# linebreak types
LB_SPACE = 1
LB_SPACE2 = 2
LB_NONE = 3
LB_FORCED = 4
LB_LAST = 5

# mapping from character to linebreak
_text2lb = {
    '>' : LB_SPACE,
    '+' : LB_SPACE2,
    '&' : LB_NONE,
    '|' : LB_FORCED,
    '.' : LB_LAST
    }

# reverse to above
_lb2text = {}

# what string each linebreak type should be mapped to.
_lb2str = {
    LB_SPACE : " ",
    LB_SPACE2 : "  ",
    LB_NONE : "",
    LB_FORCED : "\n",
    LB_LAST : "\n"
    }

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

# reverse to above
_lt2text = {}

# page break indicators. do not change these values as they're saved to
# the config file.
PBI_NONE = 0
PBI_REAL = 1
PBI_REAL_AND_UNADJ = 2

# for range checking above value
PBI_FIRST, PBI_LAST = PBI_NONE, PBI_REAL_AND_UNADJ

# current config.
currentCfg = None


# construct reverse lookup tables

for k, v in _text2lb.items():
    _lb2text[v] = k

for k, v in _text2lt.items():
    _lt2text[v] = k

del k, v

class TextType:
    cvars = None
    
    def __init__(self):
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addBool("isCaps", False, "AllCaps")
            v.addBool("isBold", False, "Bold")
            v.addBool("isItalic", False, "Italic")
            v.addBool("isUnderlined", False, "Underlined")

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        return self.cvars.save(prefix, self)

class Type:
    cvars = None

    def __init__(self, cfg):
        self.cfg = cfg
        
        # line type
        self.lt = None

        # textual description. this is saved into the config file, so
        # don't change these.
        self.name = None

        # text types, one for screen and one for export
        self.screen = TextType()
        self.export = TextType()
        
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addInt("emptyLinesBefore", 0, "EmptyLinesBefore", 0, 0)
            v.addInt("indent", 0, "Indent", 0, 0)
            v.addInt("width", 0, "Width", 0, 0)

            # what type of element to insert when user presses enter or tab.
            v.addElemName("newTypeEnter", None, "NewTypeEnter")
            v.addElemName("newTypeTab", None, "NewTypeTab")

            # what element to switch to when user hits tab / shift-tab.
            v.addElemName("nextTypeTab", None, "NextTypeTab")
            v.addElemName("prevTypeTab", None, "PrevTypeTab")
            
            # auto-completion stuff, only used for some element types
            v.addBool("doAutoComp", False, "AutoCompletion")
            v.addList("autoCompList", [], "AutoCompletionList",
                      mypickle.StrVar("", "", ""))

        self.__class__.cvars.setDefaults(self)
            
    def save(self, prefix):
        prefix += "%s/" % self.name

        s = self.cvars.save(prefix, self)
        s += self.screen.save(prefix + "Screen/")
        s += self.export.save(prefix + "Export/")

        return s

# type-specific stuff that are wxwindows objects, so can't be in normal
# Type (deepcopy dies)
class TypeGui:
    def __init__(self):
        self.font = None

class Config:
    cvars = None
    
    def __init__(self):

        # offsets from upper left corner of main widget, ie. this much empty
        # space is left on the top and left sides.
        self.offsetY = 10
        self.offsetX = 10

        if not self.__class__.cvars:
            self.setupVars()

        self.__class__.cvars.setDefaults(self)

        # type configs, key = line type, value = Type
        self.types = { }

        # element types
        t = Type(self)
        t.lt = SCENE
        t.name = "Scene"
        t.emptyLinesBefore = 1
        t.indent = 0 
        t.width = 60
        t.screen.isCaps = True
        t.screen.isBold = True
        t.export.isCaps = True
        t.newTypeEnter = ACTION
        t.newTypeTab = CHARACTER
        t.nextTypeTab = ACTION
        t.prevTypeTab = TRANSITION
        t.doAutoComp = True
        self.types[t.lt] = t

        t = Type(self)
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

        t = Type(self)
        t.lt = CHARACTER
        t.name = "Character"
        t.emptyLinesBefore = 1
        t.indent = 22
        t.width = 38
        t.screen.isCaps = True
        t.export.isCaps = True
        t.newTypeEnter = DIALOGUE
        t.newTypeTab = PAREN
        t.nextTypeTab = ACTION
        t.prevTypeTab = ACTION
        t.doAutoComp = True
        self.types[t.lt] = t

        t = Type(self)
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

        t = Type(self)
        t.lt = PAREN
        t.name = "Parenthetical"
        t.emptyLinesBefore = 0
        t.indent = 16
        t.width = 25
        t.newTypeEnter = DIALOGUE
        t.newTypeTab = ACTION
        t.nextTypeTab = CHARACTER
        t.prevTypeTab = DIALOGUE
        self.types[t.lt] = t

        t = Type(self)
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

        t = Type(self)
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
        
        t = Type(self)
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

        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()
        
        # confirm non-undoable delete operations that would delete at
        # least this many lines. (0 = disabled)
        v.addInt("confirmDeletes", 2, "ConfirmDeletes", 0, 500)

        # not used perse, but listed here so that we can easily query
        # min/max values for these in various places
        v.addInt("elementEmptyLinesBefore", 0, "", 0, 5)
        v.addInt("elementIndent", 0, "", 0, 80)
        v.addInt("elementWidth", 5, "", 5, 80)

        # vertical distance between rows, in pixels
        v.addInt("fontYdelta", 18, "FontYDelta", 4, 125)

        # font size used for PDF generation, in points
        v.addInt("fontSize", 12, "PDF/FontSize", 4, 72)

        # margins
        v.addFloat("marginBottom", 25.4, "Margin/Bottom", 0.0, 900.0)
        v.addFloat("marginLeft", 38.1, "Margin/Left", 0.0, 900.0)
        v.addFloat("marginRight", 25.4, "Margin/Right", 0.0, 900.0)
        v.addFloat("marginTop", 12.7, "Margin/Top", 0.0, 900.0)

        # how many lines to scroll per mouse wheel event
        v.addInt("mouseWheelLines", 4, "MouseWheelLines", 1, 50)

        # interval in seconds between automatic pagination (0 = disabled)
        # TODO: change this to 5 or something
        v.addInt("paginateInterval", 0, "PaginateInterval", 0, 60)

        # paper size
        v.addFloat("paperHeight", 297.0, "Paper/Height", 100.0, 1000.0)
        v.addFloat("paperWidth", 210.0, "Paper/Width", 50.0, 1000.0)

        # leave at least this many action lines on the end of a page
        v.addInt("pbActionLines", 2, "PageBreakActionLines", 1, 30)

        # leave at least this many dialogue lines on the end of a page
        v.addInt("pbDialogueLines", 2, "PageBreakDialogueLines", 1, 30)

        # whether to check script for errors before export / print
        v.addBool("checkOnExport", True, "CheckScriptForErrors")
        
        # whether to auto-capitalize start of sentences
        v.addBool("capitalize", True, "CapitalizeSentences")

        # page break indicators to show
        v.addInt("pbi", PBI_REAL, "PageBreakIndicators", PBI_FIRST,
                    PBI_LAST)
        
        # PDF viewer program and args
        if misc.isUnix:
            s1 = "/usr/local/Acrobat5/bin/acroread"
            s2 = "-tempFile"
        elif misc.isWindows:
            s1 = r"C:\Program Files\Adobe\Acrobat 6.0\Reader\AcroRd32.exe"
            s2 = ""
        else:
            s1 = "not set yet (unknown platform %s)"\
                                 % wxPlatform
            s2 = ""

        v.addStr("pdfViewerPath", s1, "PDF/ViewerPath")
        v.addStr("pdfViewerArgs", s2, "PDF/ViewerArguments")

        # font
        if misc.isUnix:
            s1 = "0;-adobe-courier-medium-r-normal-*-*-140-*-*-m-*-iso8859-1"
        elif misc.isWindows:
            s1 = "0;-16;0;0;0;400;0;0;0;0;3;2;1;49;Courier New"
        else:
            s1 = ""
            
        v.addStr("nativeFont", s1, "FontInfo")
        
        # default script directory
        v.addStr("scriptDir", misc.progPath, "DefaultScriptDirectory")
        
        # whether to draw rectangle showing margins
        v.addBool("pdfShowMargins", False, "PDF/ShowMargins")

        # whether to show line numbers next to each line
        v.addBool("pdfShowLineNumbers", False, "PDF/ShowLineNumbers")

        # colors
        v.addColor("text", 0, 0, 0, "TextFG", "Text foreground")
        v.addColor("bg", 204, 204, 204, "TextBG", "Text background")
        v.addColor("selected", 128, 192, 192, "Selected", "Selection")
        v.addColor("search", 255, 127, 0, "SearchResult", "Search result")
        v.addColor("cursor", 205, 0, 0, "Cursor", "Cursor")
        v.addColor("autoCompFg", 0, 0, 0, "AutoCompletionFG",
                   "Auto-completion foreground")
        v.addColor("autoCompBg", 249, 222, 99, "AutoCompletionBG",
                   "Auto-completion background")
        v.addColor("note", 255, 255, 0, "ScriptNote", "Script note")
        v.addColor("pagebreak", 128, 128, 128, "PageBreakLine",
                   "Page-break line")
        v.addColor("pagebreakNoAdjust", 128, 128, 128,
                   "PageBreakNoAdjustLine",
                   "Page-break (original, not adjusted) line")
        
        # make various dictionaries pointing to the config variables.
        self.allVars = v.getDict()
        self.colorVars = v.getDict(mypickle.ColorVar)
        self.numericVars = v.getDict(mypickle.NumericVar)

    # get default value of a setting
    def getDefault(self, name):
        return self.allVars[name].defVal
        
    # get minimum value of a numeric setting
    def getMin(self, name):
        return self.numericVars[name].minVal
        
    # get maximum value of a numeric setting
    def getMax(self, name):
        return self.numericVars[name].maxVal
        
    # get minimum and maximum value of a numeric setting as a (min,max)
    # tuple.
    def getMinMax(self, name):
        return (self.getMin(name), self.getMax(name))

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        pass

    # save config into a string and return that.
    def save(self):
        s = self.cvars.save("", self)

        for t in self.types.itervalues():
            s += t.save("Element/")
            
        return s
            
    # fix up all invalid config values and recalculate all variables
    # dependent on other variables.
    #
    # if doAll is False, enforces restrictions only on a per-variable
    # basis, e.g. doesn't modify variable v2 based on v1's value. this is
    # useful when user is interactively modifying v1, and it temporarily
    # strays out of bounds (e.g. when deleting the old text in an entry
    # box, thus getting the minimum value), which would then possibly
    # modify the value of other variables which is not what we want.
    def recalc(self, doAll = True):
        for it in self.numericVars.itervalues():
            util.clampObj(self, it.name, it.minVal, it.maxVal)

        # FIXME: check that required string vars are valid input text
        
        for el in self.types.itervalues():
            util.clampObj(el, "emptyLinesBefore",
                          *self.getMinMax("elementEmptyLinesBefore"))
            util.clampObj(el, "indent", *self.getMinMax("elementIndent"))
            util.clampObj(el, "width", *self.getMinMax("elementWidth"))
            
        # make sure usable space on the page isn't too small
        if doAll and (self.marginTop + self.marginBottom) >= \
               (self.paperHeight - 100.0):
            self.marginTop = 0.0
            self.marginBottom = 0.0
            
        h = self.paperHeight - self.marginTop - self.marginBottom

        # how many lines on a page
        self.linesOnPage = int(h / util.getTextHeight(self.fontSize))

    def getType(self, lt):
        return self.types[lt]

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

def lb2str(lb):
    return _conv(_lb2str, lb)

def text2lt(str, raiseException = True):
    return _conv(_text2lt, str, raiseException)

def lt2text(lt):
    return _conv(_lt2text, lt)
