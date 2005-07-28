# see fileformat.txt for more detailed information about the various
# defines found here.

from error import *
import misc
import mypickle
import screenplay
import util

import copy
from wxPython.wx import *

# mapping from character to linebreak
_char2lb = {
    '>' : screenplay.LB_SPACE,
    '+' : screenplay.LB_SPACE2,
    '&' : screenplay.LB_NONE,
    '|' : screenplay.LB_FORCED,
    '.' : screenplay.LB_LAST
    }

# reverse to above
_lb2char = {}

# what string each linebreak type should be mapped to.
_lb2str = {
    screenplay.LB_SPACE  : " ",
    screenplay.LB_SPACE2 : "  ",
    screenplay.LB_NONE   : "",
    screenplay.LB_FORCED : "\n",
    screenplay.LB_LAST   : "\n"
    }

# contains a TypeInfo for each element type
_ti = []

# mapping from character to TypeInfo
_char2ti = {}

# mapping from line type to TypeInfo
_lt2ti = {}

# mapping from element name to TypeInfo
_name2ti = {}

# page break indicators. do not change these values as they're saved to
# the config file.
PBI_NONE = 0
PBI_REAL = 1
PBI_REAL_AND_UNADJ = 2

# for range checking above value
PBI_FIRST, PBI_LAST = PBI_NONE, PBI_REAL_AND_UNADJ


# construct reverse lookup tables

for k, v in _char2lb.items():
    _lb2char[v] = k

del k, v

# non-changing information about an element type
class TypeInfo:
    def __init__(self, lt, char, name):

        # line type, e.g. screenplay.ACTION
        self.lt = lt

        # character used in saved scripts, e.g. "."
        self.char = char

        # textual name, e.g. "Action"
        self.name = name

# text type
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

    def load(self, vals, prefix):
        self.cvars.load(vals, prefix, self)

# script-specific information about an element type
class Type:
    cvars = None

    def __init__(self, lt):

        # line type
        self.lt = lt

        # pointer to TypeInfo
        self.ti = lt2ti(lt)

        # text types, one for screen and one for export
        self.screen = TextType()
        self.export = TextType()

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # these two are how much empty space to insert a) before the
            # element b) between the element's lines, in units of line /
            # 10.
            v.addInt("beforeSpacing", 0, "BeforeSpacing", 0, 50)
            v.addInt("intraSpacing", 0, "IntraSpacing", 0, 20)
            
            v.addInt("indent", 0, "Indent", 0, 80)
            v.addInt("width", 5, "Width", 5, 80)

            # auto-completion stuff, only used for some element types
            v.addBool("doAutoComp", False, "AutoCompletion")
            v.addList("autoCompList", [], "AutoCompletionList",
                      mypickle.StrVar("", "", ""))

            v.makeDicts()
            
        self.__class__.cvars.setDefaults(self)
            
    def save(self, prefix):
        prefix += "%s/" % self.ti.name

        s = self.cvars.save(prefix, self)
        s += self.screen.save(prefix + "Screen/")
        s += self.export.save(prefix + "Export/")

        return s

    def load(self, vals, prefix):
        prefix += "%s/" % self.ti.name
        
        self.cvars.load(vals, prefix, self)
        self.screen.load(vals, prefix + "Screen/")
        self.export.load(vals, prefix + "Export/")

# global information about an element type
class TypeGlobal:
    cvars = None

    def __init__(self, lt):
        
        # line type
        self.lt = lt

        # pointer to TypeInfo
        self.ti = lt2ti(lt)
        
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # what type of element to insert when user presses enter or tab.
            v.addElemName("newTypeEnter", screenplay.ACTION, "NewTypeEnter")
            v.addElemName("newTypeTab", screenplay.ACTION, "NewTypeTab")

            # what element to switch to when user hits tab / shift-tab.
            v.addElemName("nextTypeTab", screenplay.ACTION, "NextTypeTab")
            v.addElemName("prevTypeTab", screenplay.ACTION, "PrevTypeTab")
            
            v.makeDicts()
            
        self.__class__.cvars.setDefaults(self)
            
    def save(self, prefix):
        prefix += "%s/" % self.ti.name

        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        prefix += "%s/" % self.ti.name
        
        self.cvars.load(vals, prefix, self)

# command (an action in the main program)
class Command:
    cvars = None

    def __init__(self, name, desc, defKeys = [], isMovement = False,
                 isFixed = False, isMenu = False):
        # name, e.g. "MoveLeft"
        self.name = name

        # textual description
        self.desc = desc

        # default keys (list of serialized util.Key objects (ints))
        self.defKeys = defKeys

        # is this a movement command
        self.isMovement = isMovement

        # some commands & their keys (Tab, Enter, Quit, etc) are fixed and
        # can't be changed
        self.isFixed = isFixed
        
        # is this a menu item
        self.isMenu = isMenu
        
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addList("keys", [], "Keys",
                      mypickle.IntVar("", 0, "", 0, 9223372036854775808L))
            
            v.makeDicts()

        # this is not actually needed but let's keep it for consistency
        self.__class__.cvars.setDefaults(self)

        self.keys = copy.deepcopy(self.defKeys)

    def save(self, prefix):
        if self.isFixed:
            return ""
        
        prefix += "%s/" % self.name

        if len(self.keys) > 0:
            return self.cvars.save(prefix, self)
        else:
            self.keys.append(0)
            s = self.cvars.save(prefix, self)
            self.keys = []

            return s

    def load(self, vals, prefix):
        if self.isFixed:
            return

        prefix += "%s/" % self.name

        tmp = copy.deepcopy(self.keys)
        self.cvars.load(vals, prefix, self)

        if len(self.keys) == 0:
            # we have a new command in the program not found in the old
            # config file
            self.keys = tmp
        elif self.keys[0] == 0:
            self.keys = []

        # weed out invalid bindings
        tmp2 = self.keys
        self.keys = []
        
        for k in tmp2:
            k2 = util.Key.fromInt(k)
            if not k2.isValidInputChar():
                self.keys.append(k)

# information about one screen font
class FontInfo:
    def __init__(self):
        self.font = None

        # font width and height
        self.fx = 1
        self.fy = 1

# per-script config, each script has its own one of these.
class Config:
    cvars = None
    
    def __init__(self):

        if not self.__class__.cvars:
            self.setupVars()

        self.__class__.cvars.setDefaults(self)

        # type configs, key = line type, value = Type
        self.types = { }

        # element types
        t = Type(screenplay.SCENE)
        t.beforeSpacing = 10
        t.indent = 0 
        t.width = 60
        t.screen.isCaps = True
        t.screen.isBold = True
        t.export.isCaps = True
        t.doAutoComp = True
        self.types[t.lt] = t

        t = Type(screenplay.ACTION)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        self.types[t.lt] = t

        t = Type(screenplay.CHARACTER)
        t.beforeSpacing = 10
        t.indent = 22
        t.width = 38
        t.screen.isCaps = True
        t.export.isCaps = True
        t.doAutoComp = True
        self.types[t.lt] = t

        t = Type(screenplay.DIALOGUE)
        t.indent = 10
        t.width = 35
        self.types[t.lt] = t

        t = Type(screenplay.PAREN)
        t.indent = 16
        t.width = 25
        self.types[t.lt] = t

        t = Type(screenplay.TRANSITION)
        t.beforeSpacing = 10
        t.indent = 45
        t.width = 20
        t.screen.isCaps = True
        t.export.isCaps = True
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

        t = Type(screenplay.SHOT)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t
        
        t = Type(screenplay.NOTE)
        t.beforeSpacing = 10
        t.indent = 5
        t.width = 55
        t.screen.isItalic = True
        t.export.isItalic = True
        self.types[t.lt] = t

        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()
        
        # font size used for PDF generation, in points
        v.addInt("fontSize", 12, "FontSize", 4, 72)

        # margins
        v.addFloat("marginBottom", 25.4, "Margin/Bottom", 0.0, 900.0)
        v.addFloat("marginLeft", 38.1, "Margin/Left", 0.0, 900.0)
        v.addFloat("marginRight", 25.4, "Margin/Right", 0.0, 900.0)
        v.addFloat("marginTop", 12.7, "Margin/Top", 0.0, 900.0)

        # paper size
        v.addFloat("paperHeight", 297.0, "Paper/Height", 100.0, 1000.0)
        v.addFloat("paperWidth", 210.0, "Paper/Width", 50.0, 1000.0)

        # leave at least this many action lines on the end of a page
        v.addInt("pbActionLines", 2, "PageBreakActionLines", 1, 30)

        # leave at least this many dialogue lines on the end of a page
        v.addInt("pbDialogueLines", 2, "PageBreakDialogueLines", 1, 30)

        # whether scene continueds are enabled
        v.addBool("sceneContinueds", True, "SceneContinueds")
        
        # whether to include scene numbers
        v.addBool("pdfShowSceneNumbers", False, "ShowSceneNumbers")

        # whether to draw rectangle showing margins
        v.addBool("pdfShowMargins", False, "ShowMargins")

        # whether to show line numbers next to each line
        v.addBool("pdfShowLineNumbers", False, "ShowLineNumbers")

        v.makeDicts()
        
    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = self.cvars.makeVals(s)

        self.cvars.load(vals, "", self)

        for t in self.types.itervalues():
            t.load(vals, "Element/")

        self.recalc()
        
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
        for it in self.cvars.numeric.itervalues():
            util.clampObj(self, it.name, it.minVal, it.maxVal)

        for el in self.types.itervalues():
            for it in el.cvars.numeric.itervalues():
                util.clampObj(el, it.name, it.minVal, it.maxVal)

            tmp = []
            for v in el.autoCompList:
                v = util.toInputStr(v).strip()
                if len(v) > 0:
                    tmp.append(v)

            el.autoCompList = tmp
            
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

# global config. there is only ever one of these active.
class ConfigGlobal:
    cvars = None
    
    def __init__(self):

        if not self.__class__.cvars:
            self.setupVars()

        self.__class__.cvars.setDefaults(self)

        # type configs, key = line type, value = TypeGlobal
        self.types = { }

        # element types
        t = TypeGlobal(screenplay.SCENE)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.TRANSITION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.ACTION)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.CHARACTER
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.CHARACTER)
        t.newTypeEnter = screenplay.DIALOGUE
        t.newTypeTab = screenplay.PAREN
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.ACTION
        t.doAutoComp = True
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.DIALOGUE)
        t.newTypeEnter = screenplay.CHARACTER
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.PAREN
        t.prevTypeTab = screenplay.ACTION
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.PAREN)
        t.newTypeEnter = screenplay.DIALOGUE
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.CHARACTER
        t.prevTypeTab = screenplay.DIALOGUE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.TRANSITION)
        t.newTypeEnter = screenplay.SCENE
        t.newTypeTab = screenplay.TRANSITION
        t.nextTypeTab = screenplay.SCENE
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.SHOT)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.SCENE
        self.types[t.lt] = t
        
        t = TypeGlobal(screenplay.NOTE)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        # keyboard commands
        self.commands = [
            Command("Abort", "Abort something, e.g. selection,"
                    " auto-completion, etc.", [WXK_ESCAPE], isFixed = True),

            Command("About", "Show the about dialog.", isMenu = True),
            
            Command("ChangeToAction", "Change current element's style to"
                    " action.",
                    [util.Key(ord("A"), alt = True).toInt()]),

            Command("ChangeToCharacter", "Change current element's style to"
                    " character.",
                    [util.Key(ord("C"), alt = True).toInt()]),

            Command("ChangeToDialogue", "Change current element's style to"
                    " dialogue.",
                    [util.Key(ord("D"), alt = True).toInt()]),

            Command("ChangeToNote", "Change current element's style to note.",
                    [util.Key(ord("N"), alt = True).toInt()]),

            Command("ChangeToParenthetical", "Change current element's"
                    " style to parenthetical.",
                    [util.Key(ord("P"), alt = True).toInt()]),

            Command("ChangeToScene", "Change current element's style to"
                    " scene.",
                    [util.Key(ord("S"), alt = True).toInt()]),

            Command("ChangeToShot", "Change current element's style to"
                    " shot."),

            Command("ChangeToTransition", "Change current element's style to"
                    " transition.",
                    [util.Key(ord("T"), alt = True).toInt()]),

            Command("CharacterMap", "Open the character map.",
                    isMenu = True),

            Command("CloseScript", "Close the current script.",
                    isMenu = True),
            
            Command("CompareScripts", "Compare two scripts.", isMenu = True),

            Command("Copy", "Copy selected text to the internal clipboard.",
                    [util.Key(3, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("CopySystemCb", "Copy selected text to the system's"
                    " clipboard.", isMenu = True),
            
            Command("Cut", "Cut selected text to internal clipboard.",
                    [util.Key(24, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Delete", "Delete the character under the cursor,"
                    " or selected text.", [WXK_DELETE], isFixed = True),
            
            Command("DeleteBackward", "Delete the character behind the"
                    " cursor.", [WXK_BACK], isFixed = True),

            Command("DeleteElements", "Open the 'Delete elements' dialog.",
                    isMenu = True),
            
            Command("ExportScript", "Export the current script.",
                    isMenu = True),
            
            Command("FindAndReplaceDlg", "Open the 'Find & Replace' dialog.",
                    [util.Key(6, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("FindNextError", "Find next error in the current script.",
                    [util.Key(5, ctrl = True).toInt()], isMenu = True),
            
            Command("ForcedLineBreak", "Insert a forced line break.",
                    [util.Key(WXK_RETURN, ctrl = True).toInt(),
                     util.Key(WXK_RETURN, shift = True).toInt(),

                     # CTRL+Enter under wxMSW
                     util.Key(10, ctrl = True).toInt()],
                    isFixed = True),

            Command("HeadersDlg", "Open the headers dialog.", isMenu = True),
            
            Command("HelpCommands", "Show list of commands and their key"
                    " bindings.", isMenu = True),
            
            Command("HelpManual", "Open the manual.", isMenu = True),
            
            Command("ImportScript", "Import a script.", isMenu = True),
            
            Command("LicenseInfo", "Show information about your license.",
                    isMenu = True),
            
            Command("LoadSettings", "Load global settings.", isMenu = True),
            
            Command("LoadScriptSettings", "Load script-specific settings.",
                    isMenu = True),
            
            Command("LocationsDlg", "Open the locations dialog.",
                    isMenu = True),

            Command("MoveDown", "Move down.", [WXK_DOWN], isMovement = True),
            
            Command("MoveEndOfLine", "Move to the end of the line or"
                    " finish auto-completion.",
                    [WXK_END], isMovement = True),
            
            Command("MoveEndOfScript", "Move to the end of the script.",
                    [util.Key(WXK_END, ctrl = True).toInt()],
                    isMovement = True),
            
            Command("MoveLeft", "Move left.", [WXK_LEFT], isMovement = True),
            
            Command("MovePageDown", "Move one page down.",
                    [WXK_NEXT, WXK_PAGEDOWN], isMovement = True),
            
            Command("MovePageUp", "Move one page up.",
                    [WXK_PRIOR, WXK_PAGEUP], isMovement = True),
            
            Command("MoveRight", "Move right.", [WXK_RIGHT],
                    isMovement = True),
            
            Command("MoveSceneDown", "Move one scene down.",
                    [util.Key(WXK_DOWN, ctrl = True).toInt()],
                    isMovement = True),
            
            Command("MoveSceneUp", "Move one scene up.",
                    [util.Key(WXK_UP, ctrl = True).toInt()],
                    isMovement = True),
            
            Command("MoveStartOfLine", "Move to the start of the line.",
                    [WXK_HOME], isMovement = True),
            
            Command("MoveStartOfScript", "Move to the start of the"
                    " script.",
                    [util.Key(WXK_HOME, ctrl = True).toInt()],
                    isMovement = True),
            
            Command("MoveUp", "Move up.", [WXK_UP], isMovement = True),

            Command("NameDatabase", "Open the character name database.",
                    isMenu = True),
            
            Command("NewElement", "Create a new element.", [WXK_RETURN],
                    isFixed = True),

            Command("NewScript", "Create a new script.", isMenu = True),
            
            Command("OpenScript", "Open a script.",
                    [util.Key(15, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Paginate", "Paginate current script.", isMenu = True),
            
            Command("Paste", "Paste text from the internal clipboard.",
                    [util.Key(22, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("PasteSystemCb", "Paste text from the system's"
                    " clipboard.", isMenu = True),
            
            Command("PrintScript", "Print current script.",
                    [util.Key(16, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Quit", "Quit the program.",
                    [util.Key(17, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("ReleaseLicense", "Release your license.", isMenu = True),
            
            Command("ReportCharacter", "Generate character report.",
                    isMenu = True),
            
            Command("ReportDialogueChart", "Generate dialogue chart report.",
                    isMenu = True),

            Command("ReportLocation", "Generate location report.",
                    isMenu = True),
            
            Command("ReportScene", "Generate scene report.",
                    isMenu = True),
            
            Command("RevertScript", "Revert current script to the"
                    " version on disk.", isMenu = True),
            
            Command("SaveScriptSettingsAs", "Save script-specific settings"
                    " to a new file.", isMenu = True),
            
            Command("SaveSettingsAs", "Save global settings to a new file.",
                    isMenu = True),
            
            Command("SaveScript", "Save the current script.",
                    [util.Key(19, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("SaveScriptAs", "Save the current script to a new file.",
                    isMenu = True),
            
            Command("ScriptSettings", "Change script-specific settings.",
                    isMenu = True),
            
            Command("SelectScene", "Select the current scene.",
                    [util.Key(1, ctrl = True).toInt()], isMenu = True),
            
            Command("SetMark", "Set mark at current cursor position.",
                    [util.Key(WXK_SPACE, ctrl = True).toInt()]),
            
            Command("Settings", "Change global settings.", isMenu = True),
            
            Command("Tab", "Change current element to the next style or"
                    " create a new element.", [WXK_TAB], isFixed = True),

            Command("TabPrev", "Change current element to the previous"
                    " style.",
                    [util.Key(WXK_TAB, shift = True).toInt()],
                    isFixed = True),

            Command("TitlesDlg", "Open the titles dialog.", isMenu = True),
            
            Command("ToggleShowFormatting", "Toggle 'Show formatting'"
                    " display.", isMenu = True),

            Command("UpdateLicense", "Update your license.", isMenu = True),

            Command("ViewModeDraft", "Change view mode to draft.",
                    isMenu = True),

            Command("ViewModeLayout", "Change view mode to layout.",
                    isMenu = True),

            Command("ViewModeOverviewLarge", "Change view mode to large"
                    " overview.", isMenu = True),
            
            Command("ViewModeOverviewSmall", "Change view mode to small"
                    " overview.", isMenu = True),

            Command("ViewModeSideBySide", "Change view mode to side by"
                    " side.", isMenu = True)
            ]

        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()
        
        # confirm non-undoable delete operations that would delete at
        # least this many lines. (0 = disabled)
        v.addInt("confirmDeletes", 2, "ConfirmDeletes", 0, 500)

        # vertical distance between rows, in pixels
        v.addInt("fontYdelta", 18, "FontYDelta", 4, 125)

        # how many lines to scroll per mouse wheel event
        v.addInt("mouseWheelLines", 4, "MouseWheelLines", 1, 50)

        # interval in seconds between automatic pagination (0 = disabled)
        v.addInt("paginateInterval", 1, "PaginateInterval", 0, 10)

        # whether to check script for errors before export / print
        v.addBool("checkOnExport", True, "CheckScriptForErrors")
        
        # whether to auto-capitalize start of sentences
        v.addBool("capitalize", True, "CapitalizeSentences")

        # page break indicators to show
        v.addInt("pbi", PBI_REAL, "PageBreakIndicators", PBI_FIRST,
                    PBI_LAST)
        
        # PDF viewer program and args
        if misc.isUnix:
            s1 = "/usr/local/Adobe/Acrobat7.0/bin/acroread"
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

        # fonts
        if misc.isUnix:
            v.addStr("fontNormal", "0;-adobe-courier-medium-r-normal-*-*-140-*-*-m-*-iso8859-1", "FontNormal")
            v.addStr("fontBold", "0;-adobe-courier-bold-r-normal-*-*-140-*-*-m-*-iso8859-1", "FontBold")
            v.addStr("fontItalic", "0;-adobe-courier-medium-o-normal-*-*-140-*-*-m-*-iso8859-1", "FontItalic")
            v.addStr("fontBoldItalic", "0;-adobe-courier-bold-o-normal-*-*-140-*-*-m-*-iso8859-1", "FontBoldItalic")
            
        elif misc.isWindows:
            v.addStr("fontNormal", "0;-13;0;0;0;400;0;0;0;0;3;2;1;49;Courier New", "FontNormal")
            v.addStr("fontBold", "0;-13;0;0;0;700;0;0;0;0;3;2;1;49;Courier New", "FontBold")
            v.addStr("fontItalic", "0;-13;0;0;0;400;255;0;0;0;3;2;1;49;Courier New", "FontItalic")
            v.addStr("fontBoldItalic", "0;-13;0;0;0;700;255;0;0;0;3;2;1;49;Courier New", "FontBoldItalic")
        else:
            raise ConfigError("unknown platform")
        
        # default script directory
        v.addStr("scriptDir", misc.progPath, "DefaultScriptDirectory")
        
        # colors
        v.addColor("text", 0, 0, 0, "TextFG", "Text foreground")
        v.addColor("textHdr", 128, 128, 128, "TextHeadersFG",
                   "Text foreground (headers)")
        v.addColor("textBg", 255, 255, 255, "TextBG", "Text background")
        v.addColor("workspace", 204, 204, 204, "Workspace", "Workspace")
        v.addColor("pageBorder", 0, 0, 0, "PageBorder", "Page border")
        v.addColor("pageShadow", 128, 128, 128, "PageShadow", "Page shadow")
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

        v.makeDicts()
        
    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = self.cvars.makeVals(s)

        self.cvars.load(vals, "", self)

        for t in self.types.itervalues():
            t.load(vals, "Element/")

        for cmd in self.commands:
            cmd.load(vals, "Command/")

        self.recalc()
        
    # save config into a string and return that.
    def save(self):
        s = self.cvars.save("", self)

        for t in self.types.itervalues():
            s += t.save("Element/")
            
        for cmd in self.commands:
            s += cmd.save("Command/")

        return s
            
    # fix up all invalid config values.
    def recalc(self):
        for it in self.cvars.numeric.itervalues():
            util.clampObj(self, it.name, it.minVal, it.maxVal)

    def getType(self, lt):
        return self.types[lt]

    # add SHIFT+Key alias for all keys bound to movement commands, so
    # selection-movement works.
    def addShiftKeys(self):
        for cmd in self.commands:
            if cmd.isMovement:
                nk = []
                
                for key in cmd.keys:
                    k = util.Key.fromInt(key)
                    k.shift = True
                    ki = k.toInt()
                    
                    if ki not in cmd.keys:
                        nk.append(ki)

                cmd.keys.extend(nk)

    # remove key (int) from given cmd
    def removeKey(self, cmd, key):
        cmd.keys.remove(key)

        if cmd.isMovement:
            k = util.Key.fromInt(key)
            k.shift = True
            ki = k.toInt()

            if ki in cmd.keys:
                cmd.keys.remove(ki)

    # get textual description of conflicting keys, or None if no
    # conflicts.
    def getConflictingKeys(self):
        keys = {}
        
        for cmd in self.commands:
            for key in cmd.keys:
                if key in keys:
                    keys[key].append(cmd.name)
                else:
                    keys[key] = [cmd.name]

        s = ""
        for k, v in keys.iteritems():
            if len(v) > 1:
                s += "%s:" % util.Key.fromInt(k).toStr()

                for cmd in v:
                    s += " %s" % cmd

                s += "\n"

        if s == "":
            return None
        else:
            return s

# config stuff that are wxwindows objects, so can't be in normal
# ConfigGlobal (deepcopy dies)
class ConfigGui:

    # constants
    constantsInited = False
    bluePen = None
    redColor = None
    blackColor = None
    
    def __init__(self, cfgGl):

        if not ConfigGui.constantsInited:
            ConfigGui.bluePen = wxPen(wxColour(0, 0, 255))
            ConfigGui.redColor = wxColour(255, 0, 0)
            ConfigGui.blackColor = wxColour(0, 0, 0)

            ConfigGui.constantsInited = True

        # convert cfgGl.MyColor -> cfgGui.wxColour
        for it in cfgGl.cvars.color.itervalues():
            c = getattr(cfgGl, it.name)
            tmp = wxColour(c.r, c.g, c.b)
            setattr(self, it.name, tmp)

        self.textPen = wxPen(self.textColor)
        self.textHdrPen = wxPen(self.textHdrColor)
        
        self.workspaceBrush = wxBrush(self.workspaceColor)
        self.workspacePen = wxPen(self.workspaceColor)

        self.textBgBrush = wxBrush(self.textBgColor)
        self.textBgPen = wxPen(self.textBgColor)

        self.pageBorderPen = wxPen(self.pageBorderColor)
        self.pageShadowPen = wxPen(self.pageShadowColor)

        self.selectedBrush = wxBrush(self.selectedColor)
        self.selectedPen = wxPen(self.selectedColor)

        self.searchBrush = wxBrush(self.searchColor)
        self.searchPen = wxPen(self.searchColor)

        self.cursorBrush = wxBrush(self.cursorColor)
        self.cursorPen = wxPen(self.cursorColor)

        self.noteBrush = wxBrush(self.noteColor)
        self.notePen = wxPen(self.noteColor)

        self.autoCompPen = wxPen(self.autoCompFgColor)
        self.autoCompBrush = wxBrush(self.autoCompBgColor)
        self.autoCompRevPen = wxPen(self.autoCompBgColor)
        self.autoCompRevBrush = wxBrush(self.autoCompFgColor)

        self.pagebreakPen = wxPen(self.pagebreakColor)
        self.pagebreakNoAdjustPen = wxPen(self.pagebreakNoAdjustColor,
                                          style = wxDOT)

        # a 4-item list of FontInfo objects, indexed by the two lowest
        # bits of pml.TextOp.flags.
        self.fonts = []
        
        for fname in ["fontNormal", "fontBold", "fontItalic",
                      "fontBoldItalic"]:
            fi = FontInfo()
            
            nfi = wxNativeFontInfo()
            nfi.FromString(getattr(cfgGl, fname))
            nfi.SetEncoding(wxFONTENCODING_ISO8859_1)

            fi.font = wxFontFromNativeInfo(nfi)

            fx, fy = util.getTextExtent(fi.font, "O")

            fi.fx = max(1, fx)
            fi.fy = max(1, fy)

            self.fonts.append(fi)
            
    # TextType -> FontInfo
    def tt2fi(self, tt):
        return self.fonts[tt.isBold | (tt.isItalic << 1)]

def _conv(dict, key, raiseException = True):
    val = dict.get(key)
    if (val == None) and raiseException:
        raise ConfigError("key '%s' not found from '%s'" % (key, dict))
    
    return val

# get TypeInfos
def getTIs():
    return _ti

def char2lb(char, raiseException = True):
    return _conv(_char2lb, char, raiseException)

def lb2char(lb):
    return _conv(_lb2char, lb)

def lb2str(lb):
    return _conv(_lb2str, lb)

def char2lt(char, raiseException = True):
    ti = _conv(_char2ti, char, raiseException)

    if ti:
        return ti.lt
    else:
        return None

def lt2char(lt):
    return _conv(_lt2ti, lt).char

def name2ti(name, raiseException = True):
    return _conv(_name2ti, name, raiseException)

def lt2ti(lt):
    return _conv(_lt2ti, lt)

def _init():

    for lt, char, name in (
        (screenplay.SCENE,      "\\", "Scene"),
        (screenplay.ACTION,     ".",  "Action"),
        (screenplay.CHARACTER,  "_",  "Character"),
        (screenplay.DIALOGUE,   ":",  "Dialogue"),
        (screenplay.PAREN,      "(",  "Parenthetical"),
        (screenplay.TRANSITION, "/",  "Transition"),
        (screenplay.SHOT,       "=",  "Shot"),
        (screenplay.NOTE,       "%",  "Note")
        ):
        
        ti = TypeInfo(lt, char, name)

        _ti.append(ti)
        _lt2ti[lt] = ti
        _char2ti[char] = ti
        _name2ti[name] = ti

_init()
