# see fileformat.txt for more detailed information about the various
# defines found here.

from error import *
import misc
import mypickle
import pml
import screenplay
import util

import copy
import os

if "TRELBY_TESTING" in os.environ:
    import mock
    wx = mock.Mock()
else:
    import wx

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

# constants for identifying PDFFontInfos
PDF_FONT_NORMAL = "Normal"
PDF_FONT_BOLD = "Bold"
PDF_FONT_ITALIC = "Italic"
PDF_FONT_BOLD_ITALIC = "Bold-Italic"

# scrolling  directions
SCROLL_UP = 0
SCROLL_DOWN = 1
SCROLL_CENTER = 2

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
                 isFixed = False, isMenu = False,
                 scrollDirection = SCROLL_CENTER):

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

        # which way the command wants to scroll the page
        self.scrollDirection = scrollDirection

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

# information about one PDF font
class PDFFontInfo:
    cvars = None

    # list of characters not allowed in pdfNames
    invalidChars = None

    def __init__(self, name, style):
        # our name for the font (one of the PDF_FONT_* constants)
        self.name = name

        # 2 lowest bits of pml.TextOp.flags
        self.style = style

        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            # name to use in generated PDF file (CourierNew, MyFontBold,
            # etc.). if empty, use the default PDF Courier font.
            v.addStrLatin1("pdfName", "", "Name")

            # filename for the font to embed, or empty meaning don't
            # embed.
            v.addStrUnicode("filename", u"", "Filename")

            v.makeDicts()

            tmp = ""

            for i in range(256):
                # the OpenType font specification 1.4, of all places,
                # contains the most detailed discussion of characters
                # allowed in Postscript font names, in the section on
                # 'name' tables, describing name ID 6 (=Postscript name).
                if (i <= 32) or (i >= 127) or chr(i) in (
                    "[", "]", "(", ")", "{", "}", "<", ">", "/", "%"):
                    tmp += chr(i)

            self.__class__.invalidChars = tmp

        self.__class__.cvars.setDefaults(self)

    def save(self, prefix):
        prefix += "%s/" % self.name

        return self.cvars.save(prefix, self)

    def load(self, vals, prefix):
        prefix += "%s/" % self.name

        self.cvars.load(vals, prefix, self)

    # fix up invalid values.
    def refresh(self):
        self.pdfName = util.deleteChars(self.pdfName, self.invalidChars)

        # to avoid confused users not understanding why their embedded
        # font isn't working, put in an arbitrary font name if needed
        if self.filename and not self.pdfName:
            self.pdfName = "SampleFontName"

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
        self.types[t.lt] = t

        t = Type(screenplay.SHOT)
        t.beforeSpacing = 10
        t.indent = 0
        t.width = 60
        t.screen.isCaps = True
        t.export.isCaps = True
        self.types[t.lt] = t

        t = Type(screenplay.ACTBREAK)
        t.beforeSpacing = 10
        t.indent = 25
        t.width = 10
        t.screen.isCaps = True
        t.screen.isBold = True
        t.screen.isUnderlined = True
        t.export.isCaps = True
        t.export.isUnderlined = True
        self.types[t.lt] = t

        t = Type(screenplay.NOTE)
        t.beforeSpacing = 10
        t.indent = 5
        t.width = 55
        t.screen.isItalic = True
        t.export.isItalic = True
        self.types[t.lt] = t

        # pdf font configs, key = PDF_FONT_*, value = PdfFontInfo
        self.pdfFonts = { }

        for name, style in (
            (PDF_FONT_NORMAL, pml.COURIER),
            (PDF_FONT_BOLD, pml.COURIER | pml.BOLD),
            (PDF_FONT_ITALIC, pml.COURIER | pml.ITALIC),
            (PDF_FONT_BOLD_ITALIC, pml.COURIER | pml.BOLD | pml.ITALIC)):
            self.pdfFonts[name] = PDFFontInfo(name, style)

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
        v.addBool("sceneContinueds", False, "SceneContinueds")

        # scene continued text indent width
        v.addInt("sceneContinuedIndent", 45, "SceneContinuedIndent", -20, 80)

        # whether to include scene numbers
        v.addBool("pdfShowSceneNumbers", False, "ShowSceneNumbers")

        # whether to include PDF TOC
        v.addBool("pdfIncludeTOC", True, "IncludeTOC")

        # whether to show PDF TOC by default
        v.addBool("pdfShowTOC", True, "ShowTOC")

        # whether to open PDF document on current page
        v.addBool("pdfOpenOnCurrentPage", True, "OpenOnCurrentPage")

        # whether to remove Note elements in PDF output
        v.addBool("pdfRemoveNotes", False, "RemoveNotes")

        # whether to draw rectangles around the outlines of Note elements
        v.addBool("pdfOutlineNotes", True, "OutlineNotes")

        # whether to draw rectangle showing margins
        v.addBool("pdfShowMargins", False, "ShowMargins")

        # whether to show line numbers next to each line
        v.addBool("pdfShowLineNumbers", False, "ShowLineNumbers")

        # cursor position, line
        v.addInt("cursorLine", 0, "Cursor/Line", 0, 1000000)

        # cursor position, column
        v.addInt("cursorColumn", 0, "Cursor/Column", 0, 1000000)

        # various strings we add to the script
        v.addStrLatin1("strMore", "(MORE)", "String/MoreDialogue")
        v.addStrLatin1("strContinuedPageEnd", "(CONTINUED)",
                       "String/ContinuedPageEnd")
        v.addStrLatin1("strContinuedPageStart", "CONTINUED:",
                       "String/ContinuedPageStart")
        v.addStrLatin1("strDialogueContinued", " (cont'd)",
                       "String/DialogueContinued")

        v.makeDicts()

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = self.cvars.makeVals(s)

        self.cvars.load(vals, "", self)

        for t in self.types.itervalues():
            t.load(vals, "Element/")

        for pf in self.pdfFonts.itervalues():
            pf.load(vals, "Font/")

        self.recalc()

    # save config into a string and return that.
    def save(self):
        s = self.cvars.save("", self)

        for t in self.types.itervalues():
            s += t.save("Element/")

        for pf in self.pdfFonts.itervalues():
            s += pf.save("Font/")

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

        for it in self.cvars.stringLatin1.itervalues():
            setattr(self, it.name, util.toInputStr(getattr(self, it.name)))

        for pf in self.pdfFonts.itervalues():
            pf.refresh()

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

    # get a PDFFontInfo object for the given font type (PDF_FONT_*)
    def getPDFFont(self, fontType):
        return self.pdfFonts[fontType]

    # return a tuple of all the PDF font types
    def getPDFFontIds(self):
        return (PDF_FONT_NORMAL, PDF_FONT_BOLD, PDF_FONT_ITALIC,
                PDF_FONT_BOLD_ITALIC)

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

        t = TypeGlobal(screenplay.ACTBREAK)
        t.newTypeEnter = screenplay.SCENE
        t.newTypeTab = screenplay.ACTION
        t.nextTypeTab = screenplay.SCENE
        t.prevTypeTab = screenplay.SCENE
        self.types[t.lt] = t

        t = TypeGlobal(screenplay.NOTE)
        t.newTypeEnter = screenplay.ACTION
        t.newTypeTab = screenplay.CHARACTER
        t.nextTypeTab = screenplay.ACTION
        t.prevTypeTab = screenplay.CHARACTER
        self.types[t.lt] = t

        # keyboard commands. these must be in alphabetical order.
        self.commands = [] if "TRELBY_TESTING" in os.environ else [
            Command("Abort", "Abort something, e.g. selection,"
                    " auto-completion, etc.", [wx.WXK_ESCAPE], isFixed = True),

            Command("About", "Show the about dialog.", isMenu = True),

            Command("AutoCompletionDlg", "Open the auto-completion dialog.",
                    isMenu = True),

            Command("ChangeToActBreak", "Change current element's style to"
                    " act break.",
                    [util.Key(ord("B"), alt = True).toInt()]),

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
                    [util.Key(23, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("CompareScripts", "Compare two scripts.", isMenu = True),

            Command("Copy", "Copy selected text to the internal clipboard.",
                    [util.Key(3, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("CopySystemCb", "Copy selected text to the system's"
                    " clipboard, unformatted.", isMenu = True),

            Command("CopySystemCbFormatted", "Copy selected text to the system's"
                    " clipboard, formatted.", isMenu = True),

            Command("Cut", "Cut selected text to internal clipboard.",
                    [util.Key(24, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("Delete", "Delete the character under the cursor,"
                    " or selected text.", [wx.WXK_DELETE], isFixed = True),

            Command("DeleteBackward", "Delete the character behind the"
                    " cursor.", [wx.WXK_BACK, util.Key(wx.WXK_BACK, shift = True).toInt()], isFixed = True),

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
                    [util.Key(wx.WXK_RETURN, ctrl = True).toInt(),
                     util.Key(wx.WXK_RETURN, shift = True).toInt(),

                     # CTRL+Enter under wxMSW
                     util.Key(10, ctrl = True).toInt()],
                    isFixed = True),

            Command("Fullscreen", "Toggle fullscreen.",
                    [util.Key(wx.WXK_F11).toInt()], isFixed = True,
                    isMenu = True),

            Command("GotoPage", "Goto to a given page.",
                    [util.Key(7, ctrl = True).toInt()], isFixed = True,
                    isMenu = True),

            Command("GotoScene", "Goto to a given scene.",
                    [util.Key(ord("G"), alt = True).toInt()], isFixed = True,
                    isMenu = True),

            Command("HeadersDlg", "Open the headers dialog.", isMenu = True),

            Command("HelpCommands", "Show list of commands and their key"
                    " bindings.", isMenu = True),

            Command("HelpManual", "Open the manual.", isMenu = True),

            Command("ImportScript", "Import a script.", isMenu = True),

            Command("InsertNbsp", "Insert non-breaking space.",
                    [util.Key(wx.WXK_SPACE, shift = True, ctrl = True).toInt()],
                    isMenu = True),

            Command("LoadScriptSettings", "Load script-specific settings.",
                    isMenu = True),

            Command("LoadSettings", "Load global settings.", isMenu = True),

            Command("LocationsDlg", "Open the locations dialog.",
                    isMenu = True),

            Command("MoveDown", "Move down.", [wx.WXK_DOWN], isMovement = True,
                    scrollDirection = SCROLL_DOWN),

            Command("MoveEndOfLine", "Move to the end of the line or"
                    " finish auto-completion.",
                    [wx.WXK_END], isMovement = True),

            Command("MoveEndOfScript", "Move to the end of the script.",
                    [util.Key(wx.WXK_END, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveLeft", "Move left.", [wx.WXK_LEFT], isMovement = True),

            Command("MovePageDown", "Move one page down.",
                    [wx.WXK_PAGEDOWN], isMovement = True),

            Command("MovePageUp", "Move one page up.",
                    [wx.WXK_PAGEUP], isMovement = True),

            Command("MoveRight", "Move right.", [wx.WXK_RIGHT],
                    isMovement = True),

            Command("MoveSceneDown", "Move one scene down.",
                    [util.Key(wx.WXK_DOWN, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveSceneUp", "Move one scene up.",
                    [util.Key(wx.WXK_UP, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveStartOfLine", "Move to the start of the line.",
                    [wx.WXK_HOME], isMovement = True),

            Command("MoveStartOfScript", "Move to the start of the"
                    " script.",
                    [util.Key(wx.WXK_HOME, ctrl = True).toInt()],
                    isMovement = True),

            Command("MoveUp", "Move up.", [wx.WXK_UP], isMovement = True,
                    scrollDirection = SCROLL_UP),

            Command("NameDatabase", "Open the character name database.",
                    isMenu = True),

            Command("NewElement", "Create a new element.", [wx.WXK_RETURN],
                    isFixed = True),

            Command("NewScript", "Create a new script.",
                    [util.Key(14, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

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

            Command("Redo", "Redo a change that was reverted through undo.",
                    [util.Key(25, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("ReportCharacter", "Generate character report.",
                    isMenu = True),

            Command("ReportDialogueChart", "Generate dialogue chart report.",
                    isMenu = True),

            Command("ReportLocation", "Generate location report.",
                    isMenu = True),

            Command("ReportScene", "Generate scene report.",
                    isMenu = True),

            Command("ReportScript", "Generate script report.",
                    isMenu = True),

            Command("RevertScript", "Revert current script to the"
                    " version on disk.", isMenu = True),

            Command("SaveScript", "Save the current script.",
                    [util.Key(19, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("SaveScriptAs", "Save the current script to a new file.",
                    isMenu = True),

            Command("SaveScriptSettingsAs", "Save script-specific settings"
                    " to a new file.", isMenu = True),

            Command("SaveSettingsAs", "Save global settings to a new file.",
                    isMenu = True),

            Command("ScriptNext", "Change to next open script.",
                    [util.Key(wx.WXK_TAB, ctrl = True).toInt(),
                     util.Key(wx.WXK_PAGEDOWN, ctrl = True).toInt()],
                    isMenu = True),

            Command("ScriptPrev", "Change to previous open script.",
                    [util.Key(wx.WXK_TAB, shift = True, ctrl = True).toInt(),
                     util.Key(wx.WXK_PAGEUP, ctrl = True).toInt()],
                    isMenu = True),

            Command("ScriptSettings", "Change script-specific settings.",
                    isMenu = True),

            Command("SelectAll", "Select the entire script.", isMenu = True),

            Command("SelectScene", "Select the current scene.",
                    [util.Key(1, ctrl = True).toInt()], isMenu = True),

            Command("SetMark", "Set mark at current cursor position.",
                    [util.Key(wx.WXK_SPACE, ctrl = True).toInt()]),

            Command("Settings", "Change global settings.", isMenu = True),

            Command("SpellCheckerDictionaryDlg",
                    "Open the global spell checker dictionary dialog.",
                    isMenu = True),

            Command("SpellCheckerDlg","Spell check the script.",
                    [util.Key(wx.WXK_F8).toInt()], isMenu = True),

            Command("SpellCheckerScriptDictionaryDlg",
                    "Open the script-specific spell checker dictionary"
                    " dialog.",
                    isMenu = True),

            Command("Tab", "Change current element to the next style or"
                    " create a new element.", [wx.WXK_TAB], isFixed = True),

            Command("TabPrev", "Change current element to the previous"
                    " style.",
                    [util.Key(wx.WXK_TAB, shift = True).toInt()],
                    isFixed = True),

            Command("TitlesDlg", "Open the titles dialog.", isMenu = True),

            Command("ToggleShowFormatting", "Toggle 'Show formatting'"
                    " display.", isMenu = True),

            Command("Undo", "Undo the last change.",
                    [util.Key(26, ctrl = True).toInt()],
                    isFixed = True, isMenu = True),

            Command("ViewModeDraft", "Change view mode to draft.",
                    isMenu = True),

            Command("ViewModeLayout", "Change view mode to layout.",
                    isMenu = True),

            Command("ViewModeSideBySide", "Change view mode to side by"
                    " side.", isMenu = True),

            Command("Watermark", "Generate watermarked PDFs.",
                    isMenu = True),
            ]

        self.recalc()

    def setupVars(self):
        v = self.__class__.cvars = mypickle.Vars()

        # how many seconds to show splash screen for on startup (0 = disabled)
        v.addInt("splashTime", 2, "SplashTime", 0, 10)

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

        # whether to auto-capitalize i -> I
        v.addBool("capitalizeI", True, "CapitalizeI")

        # whether to open scripts on their last saved position
        v.addBool("honorSavedPos", True, "OpenScriptOnSavedPos")

        # whether to recenter screen when cursor moves out of it
        v.addBool("recenterOnScroll", False, "RecenterOnScroll")

        # whether to overwrite selected text on typing
        v.addBool("overwriteSelectionOnInsert", True, "OverwriteSelectionOnInsert")

        # whether to use per-elem-type colors (textSceneColor etc.)
        # instead of using textColor for all elem types
        v.addBool("useCustomElemColors", False, "UseCustomElemColors")

        # page break indicators to show
        v.addInt("pbi", PBI_REAL, "PageBreakIndicators", PBI_FIRST,
                    PBI_LAST)

        # PDF viewer program and args. defaults are empty since generating
        # them is a complex process handled by findPDFViewer.
        v.addStrUnicode("pdfViewerPath", u"", "PDF/ViewerPath")
        v.addStrBinary("pdfViewerArgs", "", "PDF/ViewerArguments")

        # fonts. real defaults are set in setDefaultFonts.
        v.addStrBinary("fontNormal", "", "FontNormal")
        v.addStrBinary("fontBold", "", "FontBold")
        v.addStrBinary("fontItalic", "", "FontItalic")
        v.addStrBinary("fontBoldItalic", "", "FontBoldItalic")

        # default script directory
        v.addStrUnicode("scriptDir", misc.progPath, "DefaultScriptDirectory")

        # colors
        v.addColor("text", 0, 0, 0, "TextFG", "Text foreground")
        v.addColor("textHdr", 128, 128, 128, "TextHeadersFG",
                   "Text foreground (headers)")
        v.addColor("textBg", 255, 255, 255, "TextBG", "Text background")
        v.addColor("workspace", 237, 237, 237, "Workspace", "Workspace")
        v.addColor("pageBorder", 202, 202, 202, "PageBorder", "Page border")
        v.addColor("pageShadow", 153, 153, 153, "PageShadow", "Page shadow")
        v.addColor("selected", 200, 200, 200, "Selected", "Selection")
        v.addColor("cursor", 135, 135, 253, "Cursor", "Cursor")
        v.addColor("autoCompFg", 0, 0, 0, "AutoCompletionFG",
                   "Auto-completion foreground")
        v.addColor("autoCompBg", 255, 240, 168, "AutoCompletionBG",
                   "Auto-completion background")
        v.addColor("note", 255, 237, 223, "ScriptNote", "Script note")
        v.addColor("pagebreak", 221, 221, 221, "PageBreakLine",
                   "Page-break line")
        v.addColor("pagebreakNoAdjust", 221, 221, 221,
                   "PageBreakNoAdjustLine",
                   "Page-break (original, not adjusted) line")

        v.addColor("tabText", 50, 50, 50, "TabText", "Tab text")
        v.addColor("tabBorder", 202, 202, 202, "TabBorder",
                   "Tab border")
        v.addColor("tabBarBg", 221, 217, 215, "TabBarBG",
                   "Tab bar background")
        v.addColor("tabNonActiveBg", 180, 180, 180, "TabNonActiveBg", "Tab, non-active")

        for t in getTIs():
            v.addColor("text%s" % t.name, 0, 0, 0, "Text%sFG" % t.name,
                       "Text foreground for %s" % t.name)

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

    # set default values that vary depending on platform, wxWidgets
    # version, etc. this is not at the end of __init__ because
    # non-interactive uses have no needs for these.
    def setDefaults(self):
        # check keyboard commands are listed in correct order
        commands = [cmd.name for cmd in self.commands]
        commandsSorted = sorted(commands)

        if commands != commandsSorted:
            # for i in range(len(commands)):
            #     if commands[i] != commandsSorted[i]:
            #         print "Got: %s Expected: %s" % (commands[i], commandsSorted[i])

            # if you get this error, you've put a new command you've added
            # in an incorrect place in the command list. uncomment the
            # above lines to figure out where it should be.
            raise ConfigError("Commands not listed in correct order")

        self.setDefaultFonts()
        self.findPDFViewer()

    # set default fonts
    def setDefaultFonts(self):
        fn = ["", "", "", ""]

        if misc.isUnix:
            fn[0] = "Monospace 12"
            fn[1] = "Monospace Bold 12"
            fn[2] = "Monospace Italic 12"
            fn[3] = "Monospace Bold Italic 12"

        elif misc.isWindows:
                fn[0] = "0;-13;0;0;0;400;0;0;0;0;3;2;1;49;Courier New"
                fn[1] = "0;-13;0;0;0;700;0;0;0;0;3;2;1;49;Courier New"
                fn[2] = "0;-13;0;0;0;400;255;0;0;0;3;2;1;49;Courier New"
                fn[3] = "0;-13;0;0;0;700;255;0;0;0;3;2;1;49;Courier New"

        else:
            raise ConfigError("Unknown platform")

        self.fontNormal = fn[0]
        self.fontBold = fn[1]
        self.fontItalic = fn[2]
        self.fontBoldItalic = fn[3]

    # set PDF viewer program to the best one found on the machine.
    def findPDFViewer(self):
        # list of programs to look for. each item is of the form (name,
        # args). if name is an absolute path only that exact location is
        # looked at, otherwise PATH is searched for the program (on
        # Windows, all paths are interpreted as absolute). args is the
        # list of arguments for the program.
        progs = []

        if misc.isUnix:
            progs = [
                (u"/usr/local/Adobe/Acrobat7.0/bin/acroread", "-tempFile"),
                (u"acroread", "-tempFile"),
                (u"xpdf", ""),
                (u"evince", ""),
                (u"gpdf", ""),
                (u"kpdf", ""),
                (u"okular", ""),
                ]
        elif misc.isWindows:
            # get value via registry if possible, or fallback to old method.
            viewer = util.getWindowsPDFViewer()

            if viewer:
                self.pdfViewerPath = viewer
                self.pdfViewerArgs = ""

                return

            progs = [
                (ur"C:\Program Files\Adobe\Reader 11.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Reader 10.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Reader 9.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Reader 8.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 7.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 6.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 5.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Adobe\Acrobat 4.0\Reader\AcroRd32.exe",
                 ""),
                (ur"C:\Program Files\Foxit Software\Foxit Reader\Foxit Reader.exe",
                 ""),
                ]
        else:
            pass

        success = False

        for name, args in progs:
            if misc.isWindows or (name[0] == u"/"):
                if util.fileExists(name):
                    success = True

                    break
            else:
                name = util.findFileInPath(name)

                if name:
                    success = True

                    break

        if success:
            self.pdfViewerPath = name
            self.pdfViewerArgs = args

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
            ConfigGui.bluePen = wx.Pen(wx.Colour(0, 0, 255))
            ConfigGui.redColor = wx.Colour(255, 0, 0)
            ConfigGui.blackColor = wx.Colour(0, 0, 0)

            ConfigGui.constantsInited = True

        # convert cfgGl.MyColor -> cfgGui.wx.Colour
        for it in cfgGl.cvars.color.itervalues():
            c = getattr(cfgGl, it.name)
            tmp = wx.Colour(c.r, c.g, c.b)
            setattr(self, it.name, tmp)

        # key = line type, value = wx.Colour
        self._lt2textColor = {}

        for t in getTIs():
            self._lt2textColor[t.lt] = getattr(self, "text%sColor" % t.name)

        self.textPen = wx.Pen(self.textColor)
        self.textHdrPen = wx.Pen(self.textHdrColor)

        self.workspaceBrush = wx.Brush(self.workspaceColor)
        self.workspacePen = wx.Pen(self.workspaceColor)

        self.textBgBrush = wx.Brush(self.textBgColor)
        self.textBgPen = wx.Pen(self.textBgColor)

        self.pageBorderPen = wx.Pen(self.pageBorderColor)
        self.pageShadowPen = wx.Pen(self.pageShadowColor)

        self.selectedBrush = wx.Brush(self.selectedColor)
        self.selectedPen = wx.Pen(self.selectedColor)

        self.cursorBrush = wx.Brush(self.cursorColor)
        self.cursorPen = wx.Pen(self.cursorColor)

        self.noteBrush = wx.Brush(self.noteColor)
        self.notePen = wx.Pen(self.noteColor)

        self.autoCompPen = wx.Pen(self.autoCompFgColor)
        self.autoCompBrush = wx.Brush(self.autoCompBgColor)
        self.autoCompRevPen = wx.Pen(self.autoCompBgColor)
        self.autoCompRevBrush = wx.Brush(self.autoCompFgColor)

        self.pagebreakPen = wx.Pen(self.pagebreakColor)
        self.pagebreakNoAdjustPen = wx.Pen(self.pagebreakNoAdjustColor,
                                           style = wx.DOT)

        self.tabTextPen = wx.Pen(self.tabTextColor)
        self.tabBorderPen = wx.Pen(self.tabBorderColor)

        self.tabBarBgBrush = wx.Brush(self.tabBarBgColor)
        self.tabBarBgPen = wx.Pen(self.tabBarBgColor)

        self.tabNonActiveBgBrush = wx.Brush(self.tabNonActiveBgColor)
        self.tabNonActiveBgPen = wx.Pen(self.tabNonActiveBgColor)

        # a 4-item list of FontInfo objects, indexed by the two lowest
        # bits of pml.TextOp.flags.
        self.fonts = []

        for fname in ["fontNormal", "fontBold", "fontItalic",
                      "fontBoldItalic"]:
            fi = FontInfo()

            s = getattr(cfgGl, fname)

            # evil users can set the font name to empty by modifying the
            # config file, and some wxWidgets ports crash hard when trying
            # to create a font from an empty string, so we must guard
            # against that.
            if s:
                nfi = wx.NativeFontInfo()
                nfi.FromString(s)

                fi.font = wx.FontFromNativeInfo(nfi)

                # likewise, evil users can set the font name to "z" or
                # something equally silly, resulting in an
                # invalid/non-existent font. on wxGTK2 and wxMSW we can
                # detect this by checking the point size of the font.
                if fi.font.GetPointSize() == 0:
                    fi.font = None

            # if either of the above failures happened, create a dummy
            # font and use it. this sucks but is preferable to crashing or
            # displaying an empty screen.
            if not fi.font:
                fi.font = wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL,
                                  encoding = wx.FONTENCODING_ISO8859_1)
                setattr(cfgGl, fname, fi.font.GetNativeFontInfo().ToString())

            fx, fy = util.getTextExtent(fi.font, "O")

            fi.fx = max(1, fx)
            fi.fy = max(1, fy)

            self.fonts.append(fi)

    # TextType -> FontInfo
    def tt2fi(self, tt):
        return self.fonts[tt.isBold | (tt.isItalic << 1)]

    # line type -> wx.Colour
    def lt2textColor(self, lt):
        return self._lt2textColor[lt]

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
        (screenplay.ACTBREAK,   "@",  "Act break"),
        (screenplay.NOTE,       "%",  "Note")
        ):

        ti = TypeInfo(lt, char, name)

        _ti.append(ti)
        _lt2ti[lt] = ti
        _char2ti[char] = ti
        _name2ti[name] = ti

_init()
