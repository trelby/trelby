# -*- coding: ISO-8859-1 -*-

from error import *
import cfgdlg
import charmapdlg
import commandsdlg
import config
import decode
import dialoguechart
import finddlg
import headers
import headersdlg
import misc
import namesdlg
import pdf
import pml
import report
import splash
import titles
import titlesdlg
import util

import codecs
import copy
import difflib
import os.path
import re
import signal
import sys
import time
from wxPython.wx import *

#keycodes
KC_CTRL_A = 1
KC_CTRL_B = 2
KC_CTRL_D = 4
KC_CTRL_E = 5
KC_CTRL_F = 6
KC_CTRL_N = 14
KC_CTRL_P = 16
KC_CTRL_V = 22

ID_EDIT_COPY,\
ID_EDIT_CUT,\
ID_EDIT_FIND,\
ID_EDIT_PASTE,\
ID_EDIT_SELECT_SCENE,\
ID_EDIT_SHOW_FORMATTING,\
ID_FILE_CLOSE,\
ID_FILE_EXIT,\
ID_FILE_EXPORT,\
ID_FILE_NEW,\
ID_FILE_OPEN,\
ID_FILE_PRINT,\
ID_FILE_REVERT,\
ID_FILE_SAVE,\
ID_FILE_SAVE_AS,\
ID_FILE_SETTINGS,\
ID_HELP_ABOUT,\
ID_HELP_COMMANDS,\
ID_REPORTS_CHARACTER_REP,\
ID_REPORTS_DIALOGUE_CHART,\
ID_SCRIPT_FIND_ERROR,\
ID_SCRIPT_HEADERS,\
ID_SCRIPT_PAGINATE,\
ID_SCRIPT_REFORMAT,\
ID_SCRIPT_TITLES,\
ID_TOOLS_CHARMAP,\
ID_TOOLS_COMPARE_SCRIPTS,\
ID_TOOLS_NAME_DB = range(28)

def refreshGuiConfig():
    global cfgGui

    cfgGui = config.ConfigGui(cfg)

class Line:
    def __init__(self, lb = config.LB_LAST, lt = config.ACTION, text = ""):
        self.lb = lb
        self.lt = lt
        self.text = text

    def __eq__(self, other):
        return (self.lb == other.lb) and (self.lt == other.lt) and\
               (self.text == other.text)
    
    def __ne__(self, other):
        return not self == other
        
    def __str__(self):
        return config.lb2text(self.lb) + config.lt2text(self.lt)\
               + self.text

    # replace some words, rendering the script useless except for
    # evaluation purposes
    def replace(self):
        self.text = re.sub(r"\b(\w){3}\b", "BUY", self.text)
        self.text = re.sub(r"\b(\w){4}\b", "DEMO", self.text)
        self.text = re.sub(r"\b(\w){5}\b", "TRIAL", self.text)
        self.text = re.sub(r"\b(\w){6}\b", "*TEST*", self.text)
        self.text = re.sub(r"\b(\w){7}\b", "LIMITED", self.text)
        self.text = re.sub(r"\b(\w){10}\b", "EVALUATION", self.text)
        
class Screenplay:
    def __init__(self):
        self.titles = titles.Titles()
        self.headers = headers.Headers()
        self.lines = []
        
    def __eq__(self, other):
        if len(self.lines) != len(other.lines):
            return False

        if self.titles != other.titles:
            return False
        
        if self.headers != other.headers:
            return False
        
        for i in xrange(len(self.lines)):
            if self.lines[i] != other.lines[i]:
                return False

        return True
    
    def __ne__(self, other):
        return not self == other
    
    def getEmptyLinesBefore(self, i):
        if i == 0:
            return 0
        
        if self.lines[i - 1].lb == config.LB_LAST:
            return cfg.types[self.lines[i].lt].emptyLinesBefore
        else:
            return 0

    def replace(self):
        for i in xrange(len(self.lines)):
            self.lines[i].replace()

    # this is ~8x faster than the generic deepcopy, which makes a
    # noticeable difference at least on an Athlon 1.3GHz (0.06s versus
    # 0.445s)
    def __deepcopy__(self, memo):
        sp = Screenplay()
        l = sp.lines

        sp.titles = copy.deepcopy(self.titles)
        sp.headers = copy.deepcopy(self.headers)

        for i in xrange(len(self.lines)):
            ln = self.lines[i]
            l.append(Line(ln.lb, ln.lt, ln.text))

        return sp
            
class MyPanel(wxPanel):

    def __init__(self, parent, id):
        wxPanel.__init__(self, parent, id, style = wxWANTS_CHARS)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.scrollBar = wxScrollBar(self, -1, style = wxSB_VERTICAL)
        self.ctrl = MyCtrl(self, -1)

        hsizer.Add(self.ctrl, 1, wxEXPAND)
        hsizer.Add(self.scrollBar, 0, wxEXPAND)
        
        EVT_COMMAND_SCROLL(self, self.scrollBar.GetId(),
                           self.ctrl.OnScroll)

        EVT_SET_FOCUS(self.scrollBar, self.OnScrollbarFocus)
                           
        self.SetSizer(hsizer)

    # we never want the scrollbar to get the keyboard focus, pass it on to
    # the main widget
    def OnScrollbarFocus(self, event):
        self.ctrl.SetFocus()
    
class MyCtrl(wxControl):

    def __init__(self, parent, id):
        wxControl.__init__(self, parent, id, style=wxWANTS_CHARS)

        self.panel = parent
        
        EVT_SIZE(self, self.OnSize)
        EVT_PAINT(self, self.OnPaint)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        EVT_LEFT_DOWN(self, self.OnLeftDown)
        EVT_LEFT_DCLICK(self, self.OnLeftDown)
        EVT_RIGHT_DOWN(self, self.OnRightDown)
        EVT_MOTION(self, self.OnMotion)
        EVT_MOUSEWHEEL(self, self.OnMouseWheel)
        EVT_CHAR(self, self.OnKeyChar)

        self.createEmptySp()
        self.updateScreen(redraw = False)

    def clearVars(self):
        self.line = 0
        self.column = 0
        self.topLine = 0
        self.mark = -1
        self.autoComp = None
        self.autoCompSel = -1
        self.searchLine = -1
        self.searchColumn = -1
        self.searchWidth = -1
        self.pages = [-1, 0]
        self.pagesNoAdjust = [-1, 0]
        self.maxAutoCompItems = 10
        
    def createEmptySp(self):
        self.clearVars()
        self.sp = Screenplay()
        self.sp.titles.addDefaults()
        self.sp.headers.addDefaults()
        self.sp.lines.append(Line(config.LB_LAST, config.SCENE, ""))
        self.setFile(None)
        self.makeBackup()
        
    def loadFile(self, fileName):
        try:
            try:
                f = open(fileName, "rb")

                try:
                    bom = f.read(3)
                    if bom != codecs.BOM_UTF8:
                        raise MiscError(
                            "File does not start with Unicode BOM marker.")
                    
                    lines = f.readlines()
                finally:
                    f.close()

            except IOError, (errno, strerror):
                raise MiscError("IOError: %s" % strerror)
            
            sp = Screenplay()

            # used to keep track that element type only changes after a
            # LB_LAST line.
            prevType = None

            # did we encounter characters not in ISO-8859-1
            invalidChars = False

            # did we encounter characters in ISO-8859-1, but undesired
            unwantedChars = False

            # convert to ISO-8859-1, remove newlines
            for i in range(len(lines)):
                try:
                    s = unicode(lines[i], "UTF-8")
                except ValueError:
                    raise MiscError("Line %d contains invalid UTF-8 data."
                                    % (i + 1))

                try:
                    s = s.encode("ISO-8859-1")
                except ValueError:
                    invalidChars = True
                    s = s.encode("ISO-8859-1", "backslashreplace")

                s = util.fixNL(s.rstrip("\n"))
                
                newS = util.toInputStr(s)
                if s != newS:
                    unwantedChars = True
                    
                lines[i] = newS

            if len(lines) < 2:
                raise MiscError("File has too few lines to be a valid"
                                " screenplay file.")

            key, version = self.parseConfigLine(lines[0])
            if not key or (key != "Version"):
                raise MiscError("File doesn't seem to be a proper"
                                " screenplay file.")

            if version != "1":
                raise MiscError("File uses fileformat version '%s',\n"
                                "while this version of the program only"
                                " supports version '1'." % version)

            # did we encounter unknown element types
            unknownTypes = False

            # did we encounter unknown config lines
            unknownConfigs = False

            for i in range(1, len(lines)):
                s = lines[i]

                if len(s) < 2:
                    raise MiscError("Line %d is too short." % (i + 1))
                
                if s[0] == "#":
                    key, val = self.parseConfigLine(s)
                    if not key:
                        raise MiscError("Line %d has invalid syntax for"
                            " config line." % (i + 1))

                    if key == "Title-Page":
                        sp.titles.pages.append([])
                        
                    elif key == "Title-String":
                        if len(sp.titles.pages) == 0:
                            sp.titles.pages.append([])

                        tmp = titles.TitleString()
                        tmp.load(val)
                        sp.titles.pages[-1].append(tmp)

                    elif key == "Header-String":
                        tmp = headers.HeaderString()
                        tmp.load(val)
                        sp.headers.hdrs.append(tmp)

                    elif key == "Header-Empty-Lines":
                        sp.headers.emptyLinesAfter = util.str2int(val, 1, 0, 5)

                    else:
                        unknownConfigs = True
                        
                else:
                    lb = config.text2lb(s[0], False)
                    lt = config.text2lt(s[1], False)
                    text = s[2:]

                    if lb == None:
                        raise MiscError("Line %d has invalid linebreak type" %
                             (i + 1))

                    # convert unknown types into ACTION
                    if lt == None:
                        lt = config.ACTION
                        unknownTypes = True
                    
                    if prevType and (lt != prevType):
                        raise MiscError("Line %d has invalid element type." %
                             (i + 1))

                    line = Line(lb, lt, text)
                    sp.lines.append(line)

                    if lb != config.LB_LAST:
                        prevType = lt
                    else:
                        prevType = None

            if len(sp.lines) == 0:
                raise MiscError("Empty file.")

            if sp.lines[-1].lb != config.LB_LAST:
                raise MiscError("Last line doesn't end an element.")

            self.clearVars()
            self.sp = sp
            self.reformatAll(False)
            self.setFile(fileName)
            self.makeBackup()
            self.paginate()

            if unknownTypes:
                wxMessageBox("Screenplay contained unknown element types.\n"
                             "These have been converted to Action elements.",
                             "Warning",
                             wxOK, mainFrame)

            if unknownConfigs:
                wxMessageBox("Screenplay contained unknown information.\n"
                             "This probably means that the file was created\n"
                             "with a newer version of this program.\n\n"
                             "You'll lose that information if you save over\n"
                             "the existing file.\n",
                             "Warning", wxOK, mainFrame)

            if invalidChars:
                wxMessageBox("Screenplay contained characters not in the\n"
                             "ISO-8859-1 character set, which is all that\n"
                             "this version of the program supports.\n\n"
                             "These characters have been converted to their\n"
                             "Unicode escape sequences. Search for '\u' to\n"
                             "find them.", "Warning", wxOK, mainFrame)

            if unwantedChars:
                wxMessageBox("Screenplay contained invalid characters.\n"
                             "These characters have been converted to '|'.",
                             "Warning", wxOK, mainFrame)
                
            return True

        except BlyteError, e:
            wxMessageBox("Error loading file: %s" % e, "Error",
                         wxOK, mainFrame)

            return False

    def saveFile(self, fileName):
        ls = self.sp.lines

        output = util.String()

        output += codecs.BOM_UTF8
        output += "#Version 1\n"

        pgs = self.sp.titles.pages
        for pg in range(len(pgs)):
            if pg != 0:
                output += "#Title-Page \n"

            for i in xrange(len(pgs[pg])):
                output += "#Title-String %s\n" % util.toUTF8(str(pgs[pg][i]))

        for h in self.sp.headers.hdrs:
            output += "#Header-String %s\n" % util.toUTF8(str(h))

        output += "#Header-Empty-Lines %d\n" % self.sp.headers.emptyLinesAfter
        
        for i in range(len(ls)):
            output += util.toUTF8(str(ls[i]) + "\n")

        if util.writeToFile(fileName, str(output), mainFrame):
            self.setFile(fileName)
            self.makeBackup()

    # generate formatted text from given screenplay and return it as a
    # string. if 'dopages' is True, marks pagination in the output.
    def generateText(self, sp, doPages):
        ls = sp.lines
        
        output = util.String()

        for p in range(1, len(self.pages)):
            start = self.pages[p - 1] + 1
            end = self.pages[p]

            if doPages and (p != 1):
                s = "%s %d. " % ("-" * 30, p)
                s += "-" * (60 - len(s))
                output += "\n%s\n\n" % s

            for i in range(start, end + 1):
                line = ls[i]
                tcfg = cfg.getType(line.lt)

                if tcfg.export.isCaps:
                    text = util.upper(line.text)
                else:
                    text = line.text

                if (i != 0) and (not doPages or (i != start)):
                    output += sp.getEmptyLinesBefore(i) * "\n"

                output += " " * tcfg.indent + text + "\n"

        return str(output)

    # generate PDF file from given screenplay and return it as a string.
    def generatePDF(self, sp):
        ls = sp.lines
        fs = cfg.fontSize

        doc = pml.Document(cfg.paperWidth, cfg.paperHeight,
                           cfg.paperType)

        sp.titles.generatePages(doc)
        
        ch_x = util.points2x(fs)
        ch_y = util.points2y(fs)
        
        # used in several places, so keep around
        charIndent = cfg.getType(config.CHARACTER).indent

        for p in range(1, len(self.pages)):
            start = self.pages[p - 1] + 1
            end = self.pages[p]

            pg = pml.Page(doc)

            # what line we're on, counted from first line after top
            # margin
            y = 0

            if p != 1:
                sp.headers.generatePML(pg, str(p), cfg)
                y += sp.headers.getNrOfLines()

                if self.needsMore(start - 1):
                    pg.add(pml.TextOp(self.getPrevSpeaker(start) + " (cont'd)",
                        cfg.marginLeft + charIndent * ch_x,
                        cfg.marginTop + y * ch_y, fs))

                    y += 1

            for i in range(start, end + 1):
                line = ls[i]
                tcfg = cfg.getType(line.lt)

                if tcfg.export.isCaps:
                    text = util.upper(line.text)
                else:
                    text = line.text

                if i != start:
                    y += sp.getEmptyLinesBefore(i)

                typ = pml.NORMAL
                if tcfg.export.isBold:
                    typ |= pml.BOLD
                if tcfg.export.isItalic:
                    typ |= pml.ITALIC
                if tcfg.export.isUnderlined:
                    typ |= pml.UNDERLINED

                pg.add(pml.TextOp(text,
                    cfg.marginLeft + tcfg.indent * ch_x,
                    cfg.marginTop + y * ch_y, fs, typ))

                if cfg.pdfShowLineNumbers:
                    pg.add(pml.TextOp("%02d" % (y + 1),
                        cfg.marginLeft - 3 * ch_x,
                        cfg.marginTop + y * ch_y, fs))

                y += 1

            if self.needsMore(end):
                pg.add(pml.TextOp("(MORE)",
                        cfg.marginLeft + charIndent * ch_x,
                        cfg.marginTop + y * ch_y, fs))

            if misc.isEval:
                self.addDemoStamp(pg)

            if cfg.pdfShowMargins:
                lx = cfg.marginLeft
                rx = cfg.paperWidth - cfg.marginRight
                uy = cfg.marginTop
                dy = cfg.paperHeight - cfg.marginBottom

                pg.add(pml.LineOp([(lx, uy), (rx, uy), (rx, dy), (lx, dy)],
                                  0, True))

            doc.add(pg)

        return pdf.generate(doc)

    # add demo stamp to given pml.Page object. this modifies line join
    # parameters, so should only be called when the page is otherwise
    # ready.
    def addDemoStamp(self, pg):
        # list of lines which together draw a "DEMO" in a 45-degree angle
        # over the page. coordinates are percentages of page width/height.
        dl = [
            # D
            [ (0.056, 0.286), (0.208, 0.156), (0.23, 0.31), (0.056, 0.286) ],

            # E
            [ (0.356, 0.542), (0.238, 0.42), (0.38, 0.302), (0.502, 0.4) ],
            [ (0.328, 0.368), (0.426, 0.452) ],

            # M
            [ (0.432, 0.592), (0.574, 0.466), (0.522, 0.650),
              (0.722, 0.62), (0.604, 0.72) ],

            # O
            [ (0.67, 0.772), (0.794, 0.678), (0.896, 0.766),
              (0.772, 0.858), (0.67, 0.772) ]
            ]

        pg.add(pml.PDFOp("1 J 1 j"))

        for path in dl:
            p = []
            for point in path:
                p.append((point[0] * pg.doc.w, point[1] * pg.doc.h))

            pg.add(pml.LineOp(p, 10))

    def makeBackup(self):
        self.backup = copy.deepcopy(self.sp)

    def setFile(self, fileName):
        self.fileName = fileName
        if fileName:
            self.setDisplayName(os.path.basename(fileName))
        else:
            self.setDisplayName("untitled")

        self.setTabText()
        mainFrame.setTitle(self.fileNameDisplay)

    def setDisplayName(self, name):
        i = 1
        while 1:
            if i == 1:
                tmp = name
            else:
                tmp = name + "<%d>" % i

            matched = False
            
            for c in mainFrame.getCtrls():
                if c == self:
                    continue

                if c.fileNameDisplay == tmp:
                    matched = True

                    break

            if not matched:
                break

            i += 1
            
        self.fileNameDisplay = tmp

    def setTabText(self):
        mainFrame.setTabText(self.panel, self.fileNameDisplay)
        
    # parse a line containing a config-value in the format detailed in
    # fileformat.txt. line must have newline stripped from the end
    # already. returns a (key, value) tuple. if line doesn't match the
    # format, (None, None) is returned.
    def parseConfigLine(self, s):
        m = re.match("#([a-zA-Z0-9\-]+) (.*)", s)

        if m:
            return (m.group(1), m.group(2))
        else:
            return (None, None)
        
    def updateTypeCb(self):
        util.reverseComboSelect(mainFrame.typeCb,
                                self.sp.lines[self.line].lt)

    def reformatAll(self, makeVisible = True):
        line = 0
        while 1:
            line += self.rewrapPara(line)
            if line >= len(self.sp.lines):
                break

        if makeVisible:
            self.makeLineVisible(self.line)
        
    def fillAutoComp(self):
        ls = self.sp.lines

        tcfg = cfg.getType(ls[self.line].lt)
        if tcfg.doAutoComp:
            self.autoComp = self.getMatchingText(ls[self.line].text,
                                                 tcfg.lt)
            self.autoCompSel = 0

    # wraps a single line into however many lines are needed, according to
    # the type's width. doesn't modify the input line, returns a list of
    # new lines.
    def wrapLine(self, line):
        ret = []
        tcfg = cfg.getType(line.lt)

        # text remaining to be wrapped
        text = line.text
        
        while 1:
            if len(text) <= tcfg.width:
                ret.append(Line(line.lb, line.lt, text))
                break
            else:
                i = text.rfind(" ", 0, tcfg.width + 1)

                if i >= 0:
                    ret.append(Line(config.LB_AUTO_SPACE, line.lt,
                                    text[0:i]))
                    text = text[i + 1:]
                    
                else:
                    ret.append(Line(config.LB_AUTO_NONE, line.lt,
                                    text[0:tcfg.width]))
                    text = text[tcfg.width:]
                    
        return ret

    # rewrap paragraph starting at given line. returns the number of lines
    # in the wrapped paragraph. if startLine is -1, rewraps paragraph
    # containing self.line. maintains cursor position correctness.
    def rewrapPara(self, startLine = -1):
        ls = self.sp.lines

        if startLine == -1:
            line1 = self.getParaFirstIndexFromLine(self.line)
        else:
            line1 = startLine

        line2 = line1

        while ls[line2].lb not in (config.LB_LAST, config.LB_FORCED):
            line2 += 1

        if (self.line >= line1) and (self.line <= line2):
            # cursor is in this paragraph, save its offset from the
            # beginning of the paragraph
            cursorOffset = 0

            for i in range(line1, line2 + 1):
                if i == self.line:
                    cursorOffset += self.column

                    break
                else:
                    cursorOffset += len(ls[i].text)
                    if ls[i].lb == config.LB_AUTO_SPACE:
                        cursorOffset += 1
        else:
            cursorOffset = -1

        s = ls[line1].text
        for i in range(line1 + 1, line2 + 1):
            if ls[i - 1].lb == config.LB_AUTO_SPACE:
                s += " "
            s += ls[i].text

        ls[line1].text = s
        ls[line1].lb = ls[line2].lb
        del ls[line1 + 1:line2 + 1]

        wrappedLines = self.wrapLine(ls[line1])
        ls[line1:line1 + 1] = wrappedLines

        # adjust cursor position
        if cursorOffset != -1:
            for i in range(line1, line1 + len(wrappedLines)):
                if cursorOffset <= len(ls[i].text):
                    self.line = i
                    self.column = cursorOffset

                    break
                else:
                    cursorOffset -= len(ls[i].text)
                    if ls[i].lb == config.LB_AUTO_SPACE:
                        cursorOffset -= 1
        elif self.line >= line1:
            # cursor position is below current paragraph, modify its
            # linenumber appropriately
            self.line += len(wrappedLines) - (line2 - line1 + 1)
            
        return len(wrappedLines)

    # rewraps paragraph previous to current one.
    def rewrapPrevPara(self):
        line = self.getParaFirstIndexFromLine(self.line)

        if line == 0:
            return
        
        line = self.getParaFirstIndexFromLine(line - 1)
        self.rewrapPara(line)
        
    def convertCurrentTo(self, lt):
        ls = self.sp.lines
        first, last = self.getElemIndexes()

        # if changing away from PAREN containing only "()", remove it
        if (first == last) and (ls[first].lt == config.PAREN) and\
           (ls[first].text == "()"):
            ls[first].text = ""
            self.column = 0
            
        for i in range(first, last + 1):
            ls[i].lt = lt

        # if changing empty element to PAREN, add "()"
        if (first == last) and (ls[first].lt == config.PAREN) and\
               (len(ls[first].text) == 0):
            ls[first].text = "()"
            self.column = 1

        # rewrap whole element
        line = first
        while 1:
            line += self.rewrapPara(line)
            if ls[line - 1].lb == config.LB_LAST:
                break

    # join lines 'line' and 'line + 1' and position cursor at the join
    # position.
    def joinLines(self, line):
        ls = self.sp.lines
        pos = len(ls[line].text)
        ls[line].text += ls[line + 1].text
        ls[line].lb = ls[line + 1].lb
        del ls[line + 1]
        self.line = line
        self.column = pos

    # split current line at current column position.
    def splitLine(self):
        ln = self.sp.lines[self.line]
        s = ln.text
        preStr = s[:self.column]
        postStr = s[self.column:]
        newLine = Line(ln.lb, ln.lt, postStr)
        ln.text = preStr
        ln.lb = config.LB_FORCED
        self.sp.lines.insert(self.line + 1, newLine)
        self.line += 1
        self.column = 0

    # split element at current position. newType is type to give to the
    # new element.
    def splitElement(self, newType):
        ls = self.sp.lines
        
        if not self.autoComp:
            if self.isAtEndOfParen():
                self.column += 1
        else:
            ls[self.line].text = self.autoComp[self.autoCompSel]
            self.column = len(ls[self.line].text)

        self.splitLine()
        ls[self.line - 1].lb = config.LB_LAST

        self.convertCurrentTo(newType)
        
        self.rewrapPara()
        self.rewrapPrevPara()

    # delete character at given position and optionally position
    # cursor there.
    def deleteChar(self, line, column, posCursor = True):
        s = self.sp.lines[line].text
        self.sp.lines[line].text = s[:column] + s[column + 1:]
        
        if posCursor:
            self.column = column
            self.line = line

    # get first index of paragraph
    def getParaFirstIndexFromLine(self, line):
        ls = self.sp.lines
        
        while 1:
            tmp = line - 1
            if tmp < 0:
                break
            if ls[tmp].lb in (config.LB_LAST, config.LB_FORCED):
                break
            line -= 1

        return line

    # get last index of paragraph
    def getParaLastIndexFromLine(self, line):
        ls = self.sp.lines

        while 1:
            if ls[line].lb in (config.LB_LAST, config.LB_FORCED):
                break
            if (line + 1) >= len(ls):
                break
            line += 1

        return line

    def getElemFirstIndex(self):
        return self.getElemFirstIndexFromLine(self.line)

    def getElemFirstIndexFromLine(self, line):
        ls = self.sp.lines
        
        while 1:
            tmp = line - 1
            if tmp < 0:
                break
            if ls[tmp].lb == config.LB_LAST:
                break
            line -= 1

        return line
    
    def getElemLastIndex(self):
        return self.getElemLastIndexFromLine(self.line)
    
    def getElemLastIndexFromLine(self, line):
        ls = self.sp.lines

        while 1:
            if ls[line].lb == config.LB_LAST:
                break
            if (line + 1) >= len(ls):
                break
            line += 1

        return line

    def isFirstLineOfElem(self, line):
        return self.getElemFirstIndexFromLine(line) == line

    def isLastLineOfElem(self, line):
        return self.getElemLastIndexFromLine(line) == line

    def isOnlyLineOfElem(self, line):
        return self.isLastLineOfElem(line) and self.isFirstLineOfElem(line)
        
    def getElemIndexes(self):
        return self.getElemIndexesFromLine(self.line)

    def getElemIndexesFromLine(self, line):
        return (self.getElemFirstIndexFromLine(line),
                self.getElemLastIndexFromLine(line))

    def getSceneIndexes(self):
        return self.getSceneIndexesFromLine(self.line)

    def getTypeOfPrevElem(self, line):
        line = self.getElemFirstIndexFromLine(line)
        line -= 1
        if line < 0:
            return None

        return self.sp.lines[line].lt

    def getTypeOfNextElem(self, line):
        line = self.getElemLastIndexFromLine(line)
        line += 1
        if line >= len(self.sp.lines):
            return None

        return self.sp.lines[line].lt
    
    def getSceneIndexesFromLine(self, line):
        top, bottom = self.getElemIndexesFromLine(line)
        ls = self.sp.lines
        
        while 1:
            if ls[top].lt == config.SCENE:
                break
            
            tmp = top - 1
            if tmp < 0:
                break
            
            top, nothing = self.getElemIndexesFromLine(tmp)

        while 1:
            tmp = bottom + 1
            if tmp >= len(ls):
                break
            
            if ls[tmp].lt == config.SCENE:
                break
            
            nothing, bottom = self.getElemIndexesFromLine(tmp)

        return (top, bottom)
        
    def getLinesOnScreen(self):
        size = self.GetClientSize()
        length = len(self.sp.lines)

        lines = 0
        y = cfg.offsetY
        i = self.topLine
        while (y < size.height) and (i < length):
            y += self.sp.getEmptyLinesBefore(i) * cfg.fontYdelta

            if (y + cfg.fontYdelta) > size.height:
                break

            lines += 1
            y += cfg.fontYdelta
            i += 1

        return lines

    def pos2line(self, pos):
        size = self.GetClientSize()
        length = len(self.sp.lines)

        line = self.topLine
        y = cfg.offsetY
        while (y < size.height) and (line < (length -1)):
            y += self.sp.getEmptyLinesBefore(line) * cfg.fontYdelta

            if (y + cfg.fontYdelta) > size.height:
                break

            if (y + cfg.fontYdelta) > pos.y:
                break
            
            y += cfg.fontYdelta
            line += 1

        return line

    def line2page(self, line):
        return self.line2pageReal(line, self.pages)

    def line2pageNoAdjust(self, line):
        return self.line2pageReal(line, self.pagesNoAdjust)

    def line2pageReal(self, line, p):
        lo = 1
        hi = len(p) - 1

        while lo != hi:
            mid = (lo + hi) / 2

            if line <= p[mid]:
                hi = mid
            else:
                lo = mid + 1

        return lo

    # returns True if we're at second-to-last character of PAREN element,
    # and last character is ")"
    def isAtEndOfParen(self):
        ls = self.sp.lines
        
        return self.isLastLineOfElem(self.line) and\
           (ls[self.line].lt == config.PAREN) and\
           (ls[self.line].text[self.column:] == ")")

    # returns True if pressing TAB at current position would make a new
    # element, False if it would just change element's type.
    def tabMakesNew(self):
        l = self.sp.lines[self.line]

        if self.isAtEndOfParen():
            return True
        
        if (l.lb != config.LB_LAST) or (self.column != len(l.text)):
            return False

        if (len(l.text) == 0) and self.isOnlyLineOfElem(self.line):
            return False

        return True
        
    def isLineVisible(self, line):
        bottom = self.topLine + self.getLinesOnScreen() - 1
        if (line >= self.topLine) and (line <= bottom):
            return True
        else:
            return False
        
    def makeLineVisible(self, line, redraw = False):
        if self.isLineVisible(line):
            return
        
        self.topLine = max(0, int(line - (self.getLinesOnScreen() * 0.66)))
        if not self.isLineVisible(line):
            self.topLine = line
            
        if redraw:
            self.Refresh(False)
        
    def adjustScrollBar(self):
        pageSize = self.getLinesOnScreen()
        self.panel.scrollBar.SetScrollbar(self.topLine, pageSize,
                                          len(self.sp.lines), pageSize) 

    # get a list of strings (single-line text elements for now) that start
    # with 'text' (not case sensitive) and are of of type 'type'. also
    # mixes in the type's default items from config. ignores current line.
    def getMatchingText(self, text, lt):
        text = util.upper(text)
        tcfg = cfg.getType(lt)
        ls = self.sp.lines
        matches = {}
        last = None

        for i in range(len(ls)):
            if (ls[i].lt == lt) and (ls[i].lb == config.LB_LAST):
                upstr = util.upper(ls[i].text)
                
                if upstr.startswith(text) and i != self.line:
                    matches[upstr] = None
                    if i < self.line:
                        last = upstr

        for i in tcfg.autoCompList:
            upstr = util.upper(i)
            
            if upstr.startswith(text):
                matches[upstr] = None

        if last:
            del matches[last]
            
        mlist = matches.keys()
        mlist.sort()

        if last:
            mlist.insert(0, last)
        
        return mlist

    # returns pair (start, end) of marked lines, inclusive. if mark is
    # after the end of the script (text has been deleted since setting
    # it), returns a valid pair (by truncating selection to current
    # end). returns (-1, -1) if no lines marked.
    def getMarkedLines(self):
        if self.mark != -1:
            mark = min(len(self.sp.lines) - 1, self.mark)
            if self.line < mark:
                return (self.line, mark)
            else:
                return (mark, self.line)
        else:
            return (-1, -1)

    # checks if a line is marked. marked is the pair of the type
    # returned by the above function.
    def isLineMarked(self, line, marked):
        if (line >= marked[0]) and (line <= marked[1]):
            return True
        else:
            return False
        
    # returns true if there are no contents at all and we're not
    # attached to any file
    def isUntouched(self):
        if self.fileName or (len(self.sp.lines) > 1) or \
           (len(self.sp.lines[0].text) > 0):
            return False
        else:
            return True

    # returns True if the current contents differ from the version
    # supposedly on the disk (content at last load/save time), or if
    # this is totally new modified content and doesn't have disk
    # backing yet
    def isModified(self):
        return self.sp != self.backup

    # returns true if a character, inserted at current position, would
    # need to be capitalized as a start of a sentence.
    def capitalizeNeeded(self):
        if not cfg.capitalize:
            return False
        
        ls = self.sp.lines
        line = self.line
        column = self.column

        text = ls[line].text
        if (column < len(text)) and (text[column] != " "):
            return False
            
        # go backwards at most 4 characters, looking for "!?.", and
        # breaking on anything other than space or ".
        
        cnt = 1
        while 1:
            column -= 1

            char = None
            
            if column < 0:
                line -= 1

                if line < 0:
                    return True

                lb = ls[line].lb

                if lb == config.LB_LAST:
                    # start of an element
                    return True

                elif lb == config.LB_AUTO_SPACE:
                    char = " "
                    column = len(ls[line].text)

                else:
                    text = ls[line].text
                    column = len(text) - 1
                    if column < 0:
                        return True
            else:
                text = ls[line].text

            if not char:
                char = text[column]
            
            if cnt == 1:
                # must be preceded by a space
                if char != " ":
                    return False
            else:
                if char in (".", "?", "!"):
                    return True
                elif char not in (" ", "\""):
                    return False

            cnt += 1

            if cnt > 4:
                break
        
        return False
        
    # find next error in screenplay, starting at given line. returns
    # (line, msg) tuple, where line is -1 if no error was found and the
    # line number otherwise where the error is, and msg is a description
    # of the error
    def findError(self, line):
        ls = self.sp.lines

        msg = None
        while 1:
            if line >= len(ls):
                break

            l = ls[line]

            isFirst = self.isFirstLineOfElem(line)
            isLast = self.isLastLineOfElem(line)
            isOnly = isFirst and isLast

            prev = self.getTypeOfPrevElem(line)
            next = self.getTypeOfNextElem(line)
            
            if len(l.text) == 0:
                msg = "Empty line."
                break

            if len(l.text.strip()) == 0:
                msg = "Empty line (contains only whitespace)."
                break

            if (l.lt == config.PAREN) and isOnly and (l.text == "()"):
                msg = "Empty parenthetical."
                break

            if l.lt == config.CHARACTER:
                if isLast and next and next not in\
                       (config.PAREN, config.DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(next).name,
                           cfg.getType(l.lt).name)
                    break

            if l.lt == config.PAREN:
                if isFirst and prev and prev not in\
                       (config.CHARACTER, config.DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(l.lt).name, cfg.getType(prev).name)
                    break

            if l.lt == config.DIALOGUE:
                if isFirst and prev and prev not in\
                       (config.CHARACTER, config.PAREN):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(l.lt).name, cfg.getType(prev).name)
                    break

            line += 1
            
        if not msg:
            line = -1

        return (line, msg)

    # returns true if 'line', which must be the last line on a page, needs
    # (MORE) after it and the next page needs a "SOMEBODY (cont'd)"
    def needsMore(self, line):
        ls = self.sp.lines
        if ls[line].lt in (config.DIALOGUE, config.PAREN)\
           and (line != (len(ls) - 1)) and\
           ls[line + 1].lt in (config.DIALOGUE, config.PAREN):
            return True
        else:
            return False

    # starting at line, go backwards until a line with type of CHARACTER
    # and lb of LAST is found, and return that line's text, possibly
    # upper-cased if CHARACTER's config for export says so.
    def getPrevSpeaker(self, line):
        ls = self.sp.lines

        while 1:
            if line < 0:
                return "UNKNOWN"

            ln = ls[line]
            
            if (ln.lt == config.CHARACTER) and (ln.lb == config.LB_LAST):
                s = ln.text
                
                if cfg.getType(config.CHARACTER).export.isCaps:
                    s = util.upper(s)
                
                return s

            line -= 1

    def paginate(self):
        self.pages = [-1]
        self.pagesNoAdjust = [-1]

        ls = self.sp.lines
        length = len(ls)
        lastBreak = -1

        # fast aliases for stuff
        lbl = config.LB_LAST
        ct = cfg.types
        hdrLines = self.sp.headers.getNrOfLines()
        
        i = 0
        while 1:
            lp = cfg.linesOnPage

            if i != 0:
                lp -= hdrLines

                # decrease by 1 if we have to put a "WHOEVER (cont'd)" on
                # top of this page.
                if self.needsMore(i - 1):
                    lp -= 1

            # just a safeguard
            lp = max(5, lp)

            pageLines = 0
            if i < length:
                pageLines = 1
                
                # advance i until it points to the last line to put on
                # this page (before adjustments)
                
                while i < (length - 1):

                    pageLines += 1
                    if ls[i].lb == lbl:
                        pageLines += ct[ls[i + 1].lt].emptyLinesBefore

                    if pageLines > lp:
                        break

                    i += 1

            if i >= (length - 1):
                if pageLines != 0:
                    self.pages.append(length - 1)
                    self.pagesNoAdjust.append(length - 1)
                    
                break

            self.pagesNoAdjust.append(i)

            line = ls[i]

            if line.lt == config.SCENE:
                i = self.removeDanglingElement(i, config.SCENE, lastBreak)

            elif line.lt == config.ACTION:
                if line.lb != config.LB_LAST:
                    first = self.getElemFirstIndexFromLine(i)

                    if first > (lastBreak + 1):
                        linesOnThisPage = i - first + 1
                        if linesOnThisPage < cfg.pbActionLines:
                            i = first - 1

                        i = self.removeDanglingElement(i, config.SCENE,
                                                       lastBreak)

            elif line.lt == config.CHARACTER:
                i = self.removeDanglingElement(i, config.CHARACTER, lastBreak)
                i = self.removeDanglingElement(i, config.SCENE, lastBreak)

            elif line.lt in (config.DIALOGUE, config.PAREN):
                
                if line.lb != config.LB_LAST or\
                       self.getTypeOfNextElem(i) in\
                       (config.DIALOGUE, config.PAREN):

                    cutDialogue = False
                    cutParen = False
                    while 1:
                        oldI = i
                        line = ls[i]
                        
                        if line.lt == config.PAREN:
                            i = self.removeDanglingElement(i, config.PAREN,
                              lastBreak)
                            cutParen = True

                        elif line.lt == config.DIALOGUE:
                            if cutParen:
                                break
                            
                            first = self.getElemFirstIndexFromLine(i)

                            if first > (lastBreak + 1):
                                linesOnThisPage = i - first + 1

                                # do we need to reserve one line for (MORE)
                                reserveLine = not (cutDialogue or cutParen)

                                val = cfg.pbDialogueLines
                                if reserveLine:
                                    val += 1
                                
                                if linesOnThisPage < val:
                                    i = first - 1
                                    cutDialogue = True
                                else:
                                    if reserveLine:
                                        i -= 1
                                    break
                            else:
                                # leave space for (MORE)
                                i -= 1
                                break

                        elif line.lt == config.CHARACTER:
                            i = self.removeDanglingElement(i,
                              config.CHARACTER, lastBreak)
                            i = self.removeDanglingElement(i,
                              config.SCENE, lastBreak)

                            break

                        else:
                            break

                        if i == oldI:
                            break

            # make sure no matter how buggy the code above is, we always
            # advance at least one line per page
            i = max(i, lastBreak + 1)
            
            self.pages.append(i)
            lastBreak = i

            i += 1

    def removeDanglingElement(self, line, lt, lastBreak):
        while (self.sp.lines[line].lt == lt) and\
                  (line >= (lastBreak + 2)):
            line -= 1

        return line
        
    def updateScreen(self, redraw = True, setCommon = True):
        self.adjustScrollBar()
        
        if setCommon:
            self.updateCommon()
            
        if redraw:
            self.Refresh(False)

    # update GUI elements shared by all scripts, like statusbar etc
    def updateCommon(self):
        self.updateTypeCb()

        sb = mainFrame.statusBar
        
        sb.SetStatusText("Page: %3d / %3d" % (self.line2page(self.line),
            self.line2page(len(self.sp.lines) - 1)), 2)

        cur = cfg.getType(self.sp.lines[self.line].lt)
        
        sb.SetStatusText("Enter: %s" % cfg.getType(cur.newTypeEnter).name, 0)

        if self.tabMakesNew():
            s = "%s" % cfg.getType(cur.newTypeTab).name
        else:
            s = "%s [change]" % cfg.getType(cur.nextTypeTab).name

        sb.SetStatusText("Tab: %s" % s, 1)
        
    def applyCfg(self, newCfg):
        global cfg
        
        cfg = copy.deepcopy(newCfg)
        cfg.recalc()
        refreshGuiConfig()

        for c in mainFrame.getCtrls():
            c.reformatAll()
            c.paginate()
            c.adjustScrollBar()

        self.updateScreen()

    def checkEval(self):
        if misc.isEval:
            wxMessageBox("This feature is not supported in the\n"
                         "evaluation version.", "Notice",
                         wxOK, mainFrame)
            return True

        return False

    # return an exportable, paginated Screenplay object, or None if for
    # some reason that's not possible / wanted. 'action' is the name of
    # the action, e.g. "export" or "print", that'll be done to the script,
    # and is used in dialogue with the user if needed.
    def getExportable(self, action):
        if cfg.checkOnExport:
            line, msg = self.findError(0)

            if line != -1:
                if wxMessageBox("The script seems to contain errors.\n"
                    "Are you sure you want to %s it?" % action, "Confirm",
                     wxYES_NO | wxNO_DEFAULT, mainFrame) == wxNO:

                    return None

        self.paginate()

        sp = self.sp
        if misc.isEval:
            sp = copy.deepcopy(self.sp)
            sp.replace()

        return sp

    def OnEraseBackground(self, event):
        pass
        
    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)
    
    def OnLeftDown(self, event, mark = False):
        self.autoComp = None
        pos = event.GetPosition()
        self.line = self.pos2line(pos)
        tcfg = cfg.getType(self.sp.lines[self.line].lt)
        x = pos.x - tcfg.indent * cfgGui.fontX - cfg.offsetX
        self.column = util.clamp(x / cfgGui.fontX, 0,
                            len(self.sp.lines[self.line].text))

        if mark and (self.mark == -1):
            self.mark = self.line
            
        self.updateScreen()

    def OnRightDown(self, event):
        self.mark = -1
        self.updateScreen()
        
    def OnMotion(self, event):
        if event.LeftIsDown():
            self.OnLeftDown(event, mark = True)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            self.topLine -= cfg.mouseWheelLines
        else:
            self.topLine += cfg.mouseWheelLines
            
        self.topLine = util.clamp(self.topLine, 0, len(self.sp.lines) - 1)
        self.updateScreen()
        
    def OnTypeCombo(self, event):
        lt = mainFrame.typeCb.GetClientData(mainFrame.typeCb.GetSelection())
        self.convertCurrentTo(lt)
        self.SetFocus()
        self.updateScreen()

    def OnScroll(self, event):
        pos = self.panel.scrollBar.GetThumbPosition()
        self.topLine = pos
        self.autoComp = None
        self.updateScreen()

    def OnReformat(self):
        self.reformatAll()
        self.updateScreen()

    def OnPaginate(self):
        self.paginate()
        self.updateScreen()

    def OnTitles(self):
        dlg = titlesdlg.TitlesDlg(mainFrame, copy.deepcopy(self.sp.titles),
                                  cfg)

        if dlg.ShowModal() == wxID_OK:
            self.sp.titles = dlg.titles

        dlg.Destroy()

    def OnHeaders(self):
        dlg = headersdlg.HeadersDlg(mainFrame, copy.deepcopy(self.sp.headers),
                                    cfg)

        if dlg.ShowModal() == wxID_OK:
            self.sp.headers = dlg.headers

        dlg.Destroy()
        
    def OnDialogueChart(self):
        self.paginate()
        dialoguechart.show(mainFrame, self, cfg)

    def OnCharacterReport(self):
        self.paginate()
        report.genCharacterReport(mainFrame, self, cfg)

    def OnCharMap(self):
        dlg = charmapdlg.CharMapDlg(mainFrame, self)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCompareScripts(self):
        if mainFrame.notebook.GetPageCount() < 2:
            wxMessageBox("You need two at least two scripts open to"
                         " compare them.", "Error", wxOK, mainFrame)

            return

        items = []
        for c in mainFrame.getCtrls():
            items.append(c.fileNameDisplay)

        dlg = misc.ScriptChooserDlg(mainFrame, items)

        sel1 = -1
        sel2 = -1
        if dlg.ShowModal() == wxID_OK:
            sel1 = dlg.sel1
            sel2 = dlg.sel2
        
        dlg.Destroy()

        if sel1 == -1:
            return

        if sel1 == sel2:
            wxMessageBox("You can't compare a script to itself.", "Error",
                         wxOK, mainFrame)

            return
        
        c1 = mainFrame.notebook.GetPage(sel1).ctrl
        c2 = mainFrame.notebook.GetPage(sel2).ctrl
        
        sp1 = c1.getExportable("compare")
        sp2 = c2.getExportable("compare")

        if not sp1 or not sp2:
            return

        s1 = c1.generateText(sp1, False).split("\n")
        s2 = c2.generateText(sp2, False).split("\n")

        dltTmp = difflib.unified_diff(s1, s2, lineterm = "")

        # get rid of stupid delta generator object that doesn't allow
        # subscription or anything else really. also expands hunk
        # separators into three lines.
        dlt = []
        i = 0
        for s in dltTmp:
            if i >= 3:
                if s[0] == "@":
                    dlt.extend(["1", "2", "3"])
                else:
                    dlt.append(s)
                    
            i += 1

        if len(dlt) == 0:
            s = "The scripts are identical."
            if misc.isEval:
                s += "\n\nHowever, this is the evaluation version of the\n"\
                     "program, which replaces some words in the\n"\
                     "scripts before doing the comparison, which\n"\
                     "might have affected the result."
                
            wxMessageBox(s, "Results", wxOK, mainFrame)

            return
        
        dltTmp = dlt

        # now, generate changed-lines for single-line diffs
        dlt = []
        for i in range(len(dltTmp)):
            s = dltTmp[i]
            
            dlt.append(s)

            # this checks that we've just added a sequence of lines whose
            # first characters are " -+", where " " means '"not -" or
            # missing line', and that we're either at end of list or next
            # line does not start with "+".
            
            if (s[0] == "+") and \
               (i != 0) and (dltTmp[i - 1][0] == "-") and (
                (i == 1) or (dltTmp[i - 2][0] != "-")) and (
                (i == (len(dltTmp) - 1)) or (dltTmp[i + 1][0] != "+")):

                # generate line with "^" character at every position that
                # the lines differ
                
                s1 = dltTmp[i - 1]
                s2 = dltTmp[i]
                
                minCnt = min(len(s1), len(s2))
                maxCnt = max(len(s1), len(s2))

                res = "^"
                
                for i in range(1, minCnt):
                    if s1[i] != s2[i]:
                        res += "^"
                    else:
                        res += " "

                res += "^" * (maxCnt - minCnt)
                
                dlt.append(res)

        tmp = ["  Color information:", "1", "-  Deleted lines",
               "+  Added lines",
               "^  Positions of single-line changes (marked with ^)", "1",
               "2", "2", "3"]
        tmp.extend(dlt)
        dlt = tmp
        
        fs = cfg.fontSize
        ch_y = util.points2y(fs)
        
        doc = pml.Document(cfg.paperWidth, cfg.paperHeight,
                           cfg.paperType)

        # how many lines put on current page
        y = 0

        pg = pml.Page(doc)

        # we need to gather text ops for each page into a separate list
        # and add that list to the page only after all other ops are
        # added, otherwise the colored bars will be drawn partially over
        # some characters.
        textOps = []
        
        for s in dlt:

            if y >= cfg.linesOnPage:
                pg.ops.extend(textOps)
                doc.add(pg)

                pg = pml.Page(doc)
                textOps = []
                y = 0

            if s[0] == "1":
                pass

            elif s[0] == "3":
                pass

            elif s[0] == "2":
                pg.add(pml.PDFOp("0.75 g"))
                w = 50.0
                pg.add(pml.RectOp(doc.w / 2.0 - w /2.0, cfg.marginTop +
                    y * ch_y + ch_y / 4, w, ch_y / 2, -1, True))
                pg.add(pml.PDFOp("0.0 g"))

            else:
                color = ""

                if s[0] == "-":
                    color = "1.0 0.667 0.667"
                elif s[0] == "+":
                    color = "0.667 1.0 0.667"
                elif s[0] == "^":
                    color = "1.0 1.0 0.467"

                if color:
                    pg.add(pml.PDFOp("%s rg" % color))
                    pg.add(pml.RectOp(cfg.marginLeft, cfg.marginTop + y * ch_y,
                        doc.w - cfg.marginLeft - 5.0, ch_y, -1, True))
                    pg.add(pml.PDFOp("0.0 g"))

                textOps.append(pml.TextOp(s[1:], cfg.marginLeft,
                    cfg.marginTop + y * ch_y, fs))

            y += 1

        pg.ops.extend(textOps)
        doc.add(pg)

        if misc.isEval:
            for pg in doc.pages:
                self.addDemoStamp(pg)

        tmp = pdf.generate(doc)
        util.showTempPDF(tmp, cfg, mainFrame)

    def canBeClosed(self):
        if self.isModified():
            if wxMessageBox("The script has been modified. Are you sure\n"
                            "you want to discard the changes?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, mainFrame) == wxNO:
                return False

        return True

    def OnRevert(self):
        if self.fileName:
            if not self.canBeClosed():
                return
        
            self.loadFile(self.fileName)
            self.updateScreen()

    def OnCut(self, doUpdate = True, copyToClip = True):
        if self.mark != -1:
            marked = self.getMarkedLines()

            ls = self.sp.lines

            if copyToClip:
                mainFrame.clipboard = ls[marked[0] : marked[1] + 1]
            
            del ls[marked[0] : marked[1] + 1]
            
            if len(ls) == 0:
                ls.append(Line(config.LB_LAST, config.SCENE, ""))

            if (marked[0] != 0) and (marked[0] < len(ls)) and\
                   (ls[marked[0] - 1].lt != ls[marked[0]].lt):
                ls[marked[0] - 1].lb = config.LB_LAST

            if marked[0] < len(ls):
                self.line = marked[0]
                self.column = 0
            else:
                self.line = len(ls) - 1
                self.column = len(ls[self.line].text)
            
            self.mark = -1

            if doUpdate:
                self.makeLineVisible(self.line)
                self.updateScreen()
        
    def OnCopy(self):
        if self.mark != -1:
            marked = self.getMarkedLines()

            mainFrame.clipboard = copy.deepcopy(self.sp.lines[marked[0] :
                                                              marked[1] + 1])
        
    def OnPaste(self):
        if mainFrame.clipboard:
            ls = self.sp.lines
            
            if self.column == 0:
                insertPos = self.line
            else:
                insertPos = self.line + 1
                
            ls[insertPos : insertPos] = copy.deepcopy(mainFrame.clipboard)

            self.line = insertPos + len(mainFrame.clipboard) - 1
            self.column = len(ls[self.line].text)

            if insertPos != 0:
                if ls[insertPos - 1].lt != ls[insertPos].lt:
                    ls[insertPos - 1].lb = config.LB_LAST

            if (self.line + 1) < len(ls):
                if ls[self.line].lt != ls[self.line + 1].lt:
                    ls[self.line].lb = config.LB_LAST

            self.mark = -1
            self.makeLineVisible(self.line)
            self.updateScreen()

    def OnSelectScene(self):
        self.mark, self.line = self.getSceneIndexes()
        self.column = 0

        self.makeLineVisible(self.line)
        self.updateScreen()

    def OnFindError(self):
        line, msg = self.findError(self.line)

        if line != -1:
            self.line = line
            self.column = 0
            
            self.makeLineVisible(self.line)
            self.updateScreen()
            
        else:
            msg = "No errors found."
            
        wxMessageBox(msg, "Results", wxOK, mainFrame)
        
    def OnFind(self):
        dlg = finddlg.FindDlg(mainFrame, self, cfg)
        dlg.ShowModal()
        dlg.Destroy()

        self.searchLine = -1
        self.searchColStart = -1
        self.searchWidth = -1

        if hasattr(self, "findDlgDidReplaces"):
            del self.findDlgDidReplaces
            self.reformatAll()
            
        self.updateScreen()
        
    def OnSave(self):
        if self.checkEval():
            return
        
        if self.fileName:
            self.saveFile(self.fileName)
        else:
            self.OnSaveAs()

    def OnSaveAs(self):
        if self.checkEval():
            return
        
        dlg = wxFileDialog(mainFrame, "Filename to save as",
            wildcard = "Blyte files (*.blyte)|*.blyte|All files|*",
            style = wxSAVE | wxOVERWRITE_PROMPT)
        if dlg.ShowModal() == wxID_OK:
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnExport(self):
        sp = self.getExportable("export")
        if not sp:
            return
        
        dlg = wxFileDialog(mainFrame, "Filename to export as",
            wildcard = "PDF|*.pdf|Formatted text|*.txt",
            style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            if dlg.GetFilterIndex() == 0:
                data = self.generatePDF(sp)
            else:
                data = self.generateText(sp, True)

            util.writeToFile(dlg.GetPath(), data, mainFrame)

        dlg.Destroy()

    def OnPrint(self):
        sp = self.getExportable("print")
        if not sp:
            return
        
        s = self.generatePDF(sp)
        util.showTempPDF(s, cfg, mainFrame)

    def OnSettings(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(cfg), self.applyCfg)
        if dlg.ShowModal() == wxID_OK:
            self.applyCfg(dlg.cfg)

        dlg.Destroy()
        
    def OnKeyChar(self, ev):
        kc = ev.GetKeyCode()
        
        #print "kc: %d, ctrl/alt/shift: %d, %d, %d" %\
        #      (kc, ev.ControlDown(), ev.AltDown(), ev.ShiftDown())
        
        ls = self.sp.lines
        tcfg = cfg.getType(ls[self.line].lt)

        # FIXME: call ensureCorrectLine()

        # what to do about auto-completion
        AC_DEL = 0
        AC_REDO = 1
        AC_KEEP = 2

        doAutoComp = AC_DEL

        # 10 == CTRL+Enter under wxMSW
        if (kc == WXK_RETURN) or (kc == 10):
            if ev.ShiftDown() or ev.ControlDown():
                self.splitLine()
                
                self.rewrapPara()
                self.rewrapPrevPara()
            else:
                self.splitElement(tcfg.newTypeEnter)

        elif kc == WXK_BACK:
            if self.column == 0:
                if (self.line != 0):
                    if ls[self.line - 1].lb == config.LB_AUTO_NONE:
                        self.deleteChar(self.line - 1,
                            len(ls[self.line - 1].text) - 1, False)
                    self.joinLines(self.line - 1)
            else:
                self.deleteChar(self.line, self.column - 1)
                doAutoComp = AC_REDO

            self.rewrapPara()
            
        elif kc == WXK_DELETE:
            if self.mark == -1:
                if self.column == len(ls[self.line].text):
                    if self.line != (len(ls) - 1):
                        if ls[self.line].lb == config.LB_AUTO_NONE:
                            self.deleteChar(self.line + 1, 0, False)
                        self.joinLines(self.line)
                else:
                    self.deleteChar(self.line, self.column)
                    doAutoComp = AC_REDO

                self.rewrapPara()
            else:
                self.OnCut(False, False)

        elif ev.ControlDown():
            if kc == WXK_SPACE:
                self.mark = self.line
                
            elif kc == WXK_HOME:
                self.line = 0
                self.topLine = 0
                self.column = 0
                
            elif kc == WXK_END:
                self.line = len(ls) - 1
                self.column = len(ls[self.line].text)

            elif kc == WXK_UP:
                tmpUp, nothing = self.getSceneIndexes()

                if self.line != tmpUp:
                    self.line = tmpUp
                else:
                    tmpUp -= 1
                    if tmpUp >= 0:
                        self.line, nothing = self.getSceneIndexesFromLine(
                            tmpUp)
                    
                self.column = 0

            elif kc == WXK_DOWN:
                nothing, tmpBottom = self.getSceneIndexes()
                self.line = min(len(ls) - 1, tmpBottom + 1)
                self.column = 0
                
            else:
                ev.Skip()
                return
                
        elif kc == WXK_LEFT:
            self.column = max(self.column - 1, 0)
            
        elif kc == WXK_RIGHT:
            self.column = min(self.column + 1, len(ls[self.line].text))
            
        elif kc == WXK_DOWN:
            if not self.autoComp:
                if self.line < (len(ls) - 1):
                    self.line += 1
                    if self.line >= (self.topLine + self.getLinesOnScreen()):
                        while (self.topLine + self.getLinesOnScreen() - 1)\
                              < self.line:
                            self.topLine += 1
            else:
                self.autoCompSel = (self.autoCompSel + 1) % len(self.autoComp)
                doAutoComp = AC_KEEP
                        
        elif kc == WXK_UP:
            if not self.autoComp:
                if self.line > 0:
                    self.line -= 1
                    if self.line < self.topLine:
                        self.topLine -= 1
            else:
                self.autoCompSel = self.autoCompSel - 1
                if self.autoCompSel < 0:
                    self.autoCompSel = len(self.autoComp) - 1
                doAutoComp = AC_KEEP
                    
        elif kc == WXK_HOME:
            self.column = 0
            
        elif kc == WXK_END:
            if self.autoComp:
                ls[self.line].text = self.autoComp[self.autoCompSel]
                
            self.column = len(ls[self.line].text)
                
        elif kc == WXK_PRIOR:
            if not self.autoComp:
                self.topLine = max(self.topLine - self.getLinesOnScreen() - 2,
                    0)
                self.line = min(self.topLine + 5, len(ls) - 1)
            else:
                if len(self.autoComp) > self.maxAutoCompItems:
                    self.autoCompSel = self.autoCompSel - self.maxAutoCompItems
                    if self.autoCompSel < 0:
                        self.autoCompSel = len(self.autoComp) - 1
                
                doAutoComp = AC_KEEP
            
        elif kc == WXK_NEXT:
            if not self.autoComp:
                oldTop = self.topLine

                self.topLine += self.getLinesOnScreen() - 2
                if self.topLine >= len(ls):
                    self.topLine = len(ls) - self.getLinesOnScreen() / 2

                if self.topLine < 0:
                    self.topLine = 0

                self.line += self.topLine - oldTop
                self.line = util.clamp(self.line, 0, len(ls) - 1)
            else:
                if len(self.autoComp) > self.maxAutoCompItems:
                    self.autoCompSel = (self.autoCompSel +
                        self.maxAutoCompItems) % len(self.autoComp)
                
                doAutoComp = AC_KEEP
            
        elif ev.AltDown() and (kc < 256):
            ch = chr(kc).upper()
            lt = None
            if ch == "S":
                lt = config.SCENE
            elif ch == "A":
                lt = config.ACTION
            elif ch == "C":
                lt = config.CHARACTER
            elif ch == "D":
                lt = config.DIALOGUE
            elif ch == "P":
                lt = config.PAREN
            elif ch == "T":
                lt = config.TRANSITION
            elif ch == "N":
                lt = config.NOTE

            if lt != None:
                self.convertCurrentTo(lt)
            else:
                ev.Skip()
                return
            
        elif kc == WXK_TAB:
            if self.tabMakesNew():
                self.splitElement(tcfg.newTypeTab)
            else:
                if not ev.ShiftDown():
                    lt = tcfg.nextTypeTab
                else:
                    lt = tcfg.prevTypeTab

                self.convertCurrentTo(lt)

        elif kc == WXK_ESCAPE:
            self.mark = -1

        # FIXME: debug stuff
        elif (kc < 256) and (chr(kc) == "å"):
            self.loadFile("default.blyte")
        elif (kc < 256) and (chr(kc) == "Å"):
            self.OnSettings()
        elif (kc < 256) and (chr(kc) == "¤"):
            pass

        elif util.isValidInputChar(kc):
            char = chr(kc)

            if self.capitalizeNeeded():
                char = util.upper(char)
            
            s = ls[self.line].text
            s = s[:self.column] + char + s[self.column:]
            ls[self.line].text = s
            self.column += 1
                
            tmp = s.upper()
            if (tmp == "EXT.") or (tmp == "INT."):
                if self.isOnlyLineOfElem(self.line):
                    ls[self.line].lt = config.SCENE
            elif (tmp == "(") and\
                 ls[self.line].lt in (config.DIALOGUE, config.CHARACTER) and\
                 self.isOnlyLineOfElem(self.line):
                ls[self.line].lt = config.PAREN
                ls[self.line].text = "()"

            # no need to wrap if we're adding a character to the end of
            # the line and line length is <= tcfg.width
            if (self.column != len(ls[self.line].text)) or\
                   (self.column > tcfg.width):
                self.rewrapPara()

            doAutoComp = AC_REDO

        else:
            ev.Skip()
            return

        # FIXME: call ensureCorrectLine()
        self.column = min(self.column, len(ls[self.line].text))

        if doAutoComp == AC_DEL:
            self.autoComp = None
        elif doAutoComp == AC_REDO:
            self.fillAutoComp()
        elif doAutoComp == AC_KEEP:
            pass
        else:
            print "unknown value of doAutoComp: %s" % doAutoComp

        self.makeLineVisible(self.line)
        self.updateScreen()

    def OnPaint(self, event):
        ls = self.sp.lines
        dc = wxBufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        dc.SetBrush(cfgGui.bgBrush)
        dc.SetPen(cfgGui.bgPen)
        dc.DrawRectangle(0, 0, size.width, size.height)

        dc.SetTextForeground(cfg.textColor)
        
        y = cfg.offsetY
        length = len(ls)
        marked = self.getMarkedLines()

        cursorY = -1
        ccfg = None
        i = self.topLine
        while (y < size.height) and (i < length):
            y += self.sp.getEmptyLinesBefore(i) * cfg.fontYdelta

            if y >= size.height:
                break
            
            l = ls[i]
            tcfg = cfg.getType(l.lt)

            if l.lt == config.NOTE:
                dc.SetPen(cfgGui.notePen)
                dc.SetBrush(cfgGui.noteBrush)

                nx = cfg.offsetX + tcfg.indent * cfgGui.fontX - 5
                nw = tcfg.width * cfgGui.fontX + 10
                
                dc.DrawRectangle(nx, y, nw, cfg.fontYdelta)

                dc.SetPen(cfgGui.textPen)
                util.drawLine(dc, nx - 1, y, 0, cfg.fontYdelta)
                util.drawLine(dc, nx + nw, y, 0, cfg.fontYdelta)

                if self.isFirstLineOfElem(i):
                    util.drawLine(dc, nx - 1, y - 1, nw + 2, 0)

                if self.isLastLineOfElem(i):
                    util.drawLine(dc, nx - 1, y + cfg.fontYdelta, nw + 2, 0)

            if (self.mark != -1) and self.isLineMarked(i, marked):
                dc.SetPen(cfgGui.selectedPen)
                dc.SetBrush(cfgGui.selectedBrush)
                dc.DrawRectangle(0, y, size.width, cfg.fontYdelta)

            if mainFrame.showFormatting:
                dc.SetPen(cfgGui.bluePen)
                util.drawLine(dc, cfg.offsetX + tcfg.indent * cfgGui.fontX,
                    y, 0, cfg.fontYdelta)
                util.drawLine(dc, cfg.offsetX + (tcfg.indent + tcfg.width)
                    * cfgGui.fontX, y, 0, cfg.fontYdelta)

                if self.isFirstLineOfElem(i):
                    util.drawLine(dc, cfg.offsetX + tcfg.indent *
                        cfgGui.fontX, y, tcfg.width * cfgGui.fontX, 0)
                        
                if self.isLastLineOfElem(i):
                    util.drawLine(dc, cfg.offsetX + tcfg.indent *
                        cfgGui.fontX, y + cfg.fontYdelta,
                        tcfg.width * cfgGui.fontX, 0)
                        
                dc.SetTextForeground(cfgGui.redColor)
                dc.SetFont(cfgGui.getType(config.ACTION).font)
                dc.DrawText(config.lb2text(l.lb), 0, y)
                dc.SetTextForeground(cfg.textColor)

            if cfg.pbi == config.PBI_REAL_AND_UNADJ:
                if self.line2pageNoAdjust(i) != self.line2pageNoAdjust(i + 1):
                    dc.SetPen(cfgGui.pagebreakNoAdjustPen)
                    util.drawLine(dc, 0, y + cfg.fontYdelta - 1,
                        size.width, 0)

            if cfg.pbi in (config.PBI_REAL, config.PBI_REAL_AND_UNADJ):
                thisPage = self.line2page(i)
                if  thisPage != self.line2page(i + 1):
                    dc.SetPen(cfgGui.pagebreakPen)
                    util.drawLine(dc, 0, y + cfg.fontYdelta - 1,
                        size.width, 0)

            if i == self.line:
                cursorY = y
                ccfg = tcfg
                dc.SetPen(cfgGui.cursorPen)
                dc.SetBrush(cfgGui.cursorBrush)
                dc.DrawRectangle(cfg.offsetX + (self.column + tcfg.indent)
                    * cfgGui.fontX, y, cfgGui.fontX, cfgGui.fontY)

            if i == self.searchLine:
                dc.SetPen(cfgGui.searchPen)
                dc.SetBrush(cfgGui.searchBrush)
                dc.DrawRectangle(cfg.offsetX + (tcfg.indent +
                    self.searchColumn) * cfgGui.fontX, y,
                    self.searchWidth * cfgGui.fontX, cfgGui.fontY)

            if tcfg.screen.isCaps:
                text = util.upper(l.text)
            else:
                text = l.text

            if len(text) != 0:
                dc.SetFont(cfgGui.getType(l.lt).font)
                dc.DrawText(text, cfg.offsetX + tcfg.indent * cfgGui.fontX, y)

                if tcfg.screen.isUnderlined and misc.isUnix:
                    dc.SetPen(cfgGui.textPen)
                    util.drawLine(dc, cfg.offsetX + tcfg.indent *
                        cfgGui.fontX, y + cfg.fontYdelta - 1,
                        cfgGui.fontX * len(text) - 1, 0)

            y += cfg.fontYdelta
            i += 1

        if self.autoComp and (cursorY > 0):
            self.drawAutoComp(dc, cursorY, ccfg)

    def drawAutoComp(self, dc, cursorY, tcfg):
        offset = 5

        # scroll bar width
        sbw = 10
        
        selBleed = 2

        size = self.GetClientSize()
        
        dc.SetFont(cfgGui.getType(tcfg.lt).font)

        show = min(self.maxAutoCompItems, len(self.autoComp))
        doSbw = show < len(self.autoComp)
        
        startPos = (self.autoCompSel / show) * show
        endPos = min(startPos + show, len(self.autoComp))
        if endPos == len(self.autoComp):
            startPos = max(0, endPos - show)

        w = 0
        for i in range(len(self.autoComp)):
            tw, tmp = dc.GetTextExtent(self.autoComp[i])
            w = max(w, tw)

        w += offset * 2
        h = show * cfgGui.fontY + offset * 2

        itemW = w - offset * 2 + selBleed * 2
        if doSbw:
            w += sbw + offset * 2
            sbh = h - offset * 2 + selBleed * 2

        posX = cfg.offsetX + tcfg.indent * cfgGui.fontX
        posY = cursorY + cfg.fontYdelta

        # if the box doesn't fit on the screen in the normal position, put
        # it above the current line. if it doesn't fit there either,
        # that's just too bad, we don't support window sizes that small.
        if (posY + h) > size.height:
            posY = cursorY - h - 1
        
        dc.SetPen(cfgGui.autoCompPen)
        dc.SetBrush(cfgGui.autoCompBrush)
        dc.DrawRectangle(posX, posY, w, h)

        dc.SetTextForeground(cfg.autoCompFgColor)

        for i in range(startPos, endPos):
            if i == self.autoCompSel:
                dc.SetPen(cfgGui.autoCompRevPen)
                dc.SetBrush(cfgGui.autoCompRevBrush)
                dc.SetTextForeground(cfg.autoCompBgColor)
                dc.DrawRectangle(posX + offset - selBleed,
                    posY + offset + (i - startPos) * cfgGui.fontY - selBleed,
                    itemW,
                    cfgGui.fontY + selBleed * 2)
                dc.SetTextForeground(cfg.autoCompBgColor)
                dc.SetPen(cfgGui.autoCompPen)
                dc.SetBrush(cfgGui.autoCompBrush)
                
            dc.DrawText(self.autoComp[i], posX + offset, posY + offset +
                        (i - startPos) * cfgGui.fontY)

            if i == self.autoCompSel:
                dc.SetTextForeground(cfg.autoCompFgColor)

        if doSbw:
            dc.SetPen(cfgGui.autoCompPen)
            dc.SetBrush(cfgGui.autoCompRevBrush)
            util.drawLine(dc, posX + w - offset * 2 - sbw,
                posY, 0, h)
            dc.DrawRectangle(posX + w - offset - sbw,
                posY + offset - selBleed + int((float(startPos) /
                     len(self.autoComp)) * sbh),
                sbw,
                int((float(show) / len(self.autoComp)) * sbh))

class MyFrame(wxFrame):

    def __init__(self, parent, id, title):
        wxFrame.__init__(self, parent, id, title,
                         wxPoint(100, 100), wxSize(700, 830))

        if misc.isUnix:
            # automatically reaps zombies
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        
        self.clipboard = None
        self.showFormatting = False

        util.removeTempFiles(cfg.tmpPrefix)
        
        fileMenu = wxMenu()
        fileMenu.Append(ID_FILE_NEW, "&New")
        fileMenu.Append(ID_FILE_OPEN, "&Open...\tCTRL-O")
        fileMenu.Append(ID_FILE_SAVE, "&Save\tCTRL-S")
        fileMenu.Append(ID_FILE_SAVE_AS, "Save &As...")
        fileMenu.Append(ID_FILE_CLOSE, "&Close")
        fileMenu.Append(ID_FILE_REVERT, "&Revert")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_EXPORT, "&Export...")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_PRINT, "&Print\tCTRL-P")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_SETTINGS, "Se&ttings...")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_EXIT, "E&xit\tCTRL-Q")

        editMenu = wxMenu()
        editMenu.Append(ID_EDIT_CUT, "Cu&t\tCTRL-X")
        editMenu.Append(ID_EDIT_COPY, "&Copy\tCTRL-C")
        editMenu.Append(ID_EDIT_PASTE, "&Paste\tCTRL-V")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_SELECT_SCENE, "&Select scene\tCTRL-A")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_FIND, "&Find && Replace...\tCTRL-F")
        editMenu.AppendSeparator()
        editMenu.AppendCheckItem(ID_EDIT_SHOW_FORMATTING, "S&how formatting")
        
        scriptMenu = wxMenu()
        scriptMenu.Append(ID_SCRIPT_FIND_ERROR, "&Find next error\tCTRL-E")

        # TODO: remove permanently if this is not needed anymore
        #scriptMenu.Append(ID_SCRIPT_REFORMAT, "&Reformat all")
        
        scriptMenu.Append(ID_SCRIPT_PAGINATE, "&Paginate")
        scriptMenu.Append(ID_SCRIPT_TITLES, "&Title pages...")
        scriptMenu.Append(ID_SCRIPT_HEADERS, "&Headers...")

        reportsMenu = wxMenu()
        reportsMenu.Append(ID_REPORTS_DIALOGUE_CHART, "&Dialogue chart")
        reportsMenu.Append(ID_REPORTS_CHARACTER_REP, "&Character report...")
        
        toolsMenu = wxMenu()
        toolsMenu.Append(ID_TOOLS_NAME_DB, "&Name database...")
        toolsMenu.Append(ID_TOOLS_CHARMAP, "&Character map...")
        toolsMenu.Append(ID_TOOLS_COMPARE_SCRIPTS, "C&ompare scripts...")

        helpMenu = wxMenu()
        helpMenu.Append(ID_HELP_COMMANDS, "&Commands...")
        helpMenu.AppendSeparator()
        helpMenu.Append(ID_HELP_ABOUT, "&About...")
        
        self.menuBar = wxMenuBar()
        self.menuBar.Append(fileMenu, "&File")
        self.menuBar.Append(editMenu, "&Edit")
        self.menuBar.Append(scriptMenu, "Scr&ipt")
        self.menuBar.Append(reportsMenu, "&Reports")
        self.menuBar.Append(toolsMenu, "Too&ls")
        self.menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(self.menuBar)

        EVT_SIZE(self, self.OnSize)

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.typeCb = wxComboBox(self, -1, style = wxCB_READONLY)

        for t in cfg.types.values():
            self.typeCb.Append(t.name, t.lt)

        # these are hidden here because they're somewhat harder to find
        # here than in misc.pyo
        misc.isEval = False
        misc.licensedTo = "Evaluation copy."
        misc.version = "0.71"

        hsizer.Add(self.typeCb)

        vsizer.Add(hsizer, 0, wxALL, 5)
        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND)

        self.notebook = wxNotebook(self, -1, style = wxCLIP_CHILDREN)
        vsizer.Add(self.notebook, 1, wxEXPAND)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND)

        self.statusBar = wxStatusBar(self)
        self.statusBar.SetFieldsCount(3)
        self.statusBar.SetStatusWidths([-2, -2, -1])
        self.SetStatusBar(self.statusBar)

        EVT_MENU_HIGHLIGHT_ALL(self, self.OnMenuHighlight)
        
        EVT_NOTEBOOK_PAGE_CHANGED(self, self.notebook.GetId(),
                                  self.OnPageChange)
        
        EVT_COMBOBOX(self, self.typeCb.GetId(), self.OnTypeCombo)

        EVT_MENU(self, ID_FILE_NEW, self.OnNew)
        EVT_MENU(self, ID_FILE_OPEN, self.OnOpen)
        EVT_MENU(self, ID_FILE_SAVE, self.OnSave)
        EVT_MENU(self, ID_FILE_SAVE_AS, self.OnSaveAs)
        EVT_MENU(self, ID_FILE_EXPORT, self.OnExport)
        EVT_MENU(self, ID_FILE_CLOSE, self.OnClose)
        EVT_MENU(self, ID_FILE_REVERT, self.OnRevert)
        EVT_MENU(self, ID_FILE_PRINT, self.OnPrint)
        EVT_MENU(self, ID_FILE_SETTINGS, self.OnSettings)
        EVT_MENU(self, ID_FILE_EXIT, self.OnExit)
        EVT_MENU(self, ID_EDIT_CUT, self.OnCut)
        EVT_MENU(self, ID_EDIT_COPY, self.OnCopy)
        EVT_MENU(self, ID_EDIT_PASTE, self.OnPaste)
        EVT_MENU(self, ID_EDIT_SELECT_SCENE, self.OnSelectScene)
        EVT_MENU(self, ID_EDIT_FIND, self.OnFind)
        EVT_MENU(self, ID_EDIT_SHOW_FORMATTING, self.OnShowFormatting)
        EVT_MENU(self, ID_SCRIPT_FIND_ERROR, self.OnFindError)
        EVT_MENU(self, ID_SCRIPT_REFORMAT, self.OnReformat)
        EVT_MENU(self, ID_SCRIPT_PAGINATE, self.OnPaginate)
        EVT_MENU(self, ID_SCRIPT_TITLES, self.OnTitles)
        EVT_MENU(self, ID_SCRIPT_HEADERS, self.OnHeaders)
        EVT_MENU(self, ID_REPORTS_DIALOGUE_CHART, self.OnDialogueChart)
        EVT_MENU(self, ID_REPORTS_CHARACTER_REP, self.OnCharacterReport)
        EVT_MENU(self, ID_TOOLS_NAME_DB, self.OnNameDb)
        EVT_MENU(self, ID_TOOLS_CHARMAP, self.OnCharMap)
        EVT_MENU(self, ID_TOOLS_COMPARE_SCRIPTS, self.OnCompareScripts)
        EVT_MENU(self, ID_HELP_COMMANDS, self.OnHelpCommands)
        EVT_MENU(self, ID_HELP_ABOUT, self.OnAbout)

        EVT_CLOSE(self, self.OnCloseWindow)

        # FIXME: reset timer on settings change
        if cfg.paginateInterval != 0:
            self.timer = wxTimer(self)
            EVT_TIMER(self, -1, self.OnTimer)
            self.timer.Start(cfg.paginateInterval * 1000)

        self.Layout()
        
    def init(self):
        self.panel = self.createNewPanel()

    def createNewPanel(self):
        newPanel = MyPanel(self.notebook, -1)
        self.notebook.AddPage(newPanel, "", True)
        newPanel.ctrl.setTabText()
        newPanel.ctrl.SetFocus()

        return newPanel

    def setTitle(self, text):
        self.SetTitle("Blyte - %s" % text)

    def setTabText(self, panel, text):
        i = self.findPage(panel)
        if i != -1:
            self.notebook.SetPageText(i, text)
    
    # notebook.GetSelection() returns invalid values, eg. it can return 1
    # when there is only one tab in existence, so it can't be relied on.
    # this is currently worked around by never using that function,
    # instead this iterates over all tabs and finds out the correct page
    # number.
    def findPage(self, panel):
        for i in range(self.notebook.GetPageCount()):
            p = self.notebook.GetPage(i)
            if p == panel:
                return i

        return -1

    # get list of MyCtrl objects for all open scripts
    def getCtrls(self):
        l = []

        for i in range(self.notebook.GetPageCount()):
            l.append(self.notebook.GetPage(i).ctrl)

        return l

    # returns True if any open script has been modified
    def isModifications(self):
        for c in self.getCtrls():
            if c.isModified():
                return True

        return False

    def OnTimer(self, event):
        self.OnPaginate()

    def OnMenuHighlight(self, event):
        # default implementation modifies status bar, so we need to
        # override it and do nothing
        pass

    def OnPageChange(self, event):
        newPage = event.GetSelection()
        self.panel = self.notebook.GetPage(newPage)
        self.panel.ctrl.SetFocus()
        self.panel.ctrl.updateCommon()
        self.setTitle(self.panel.ctrl.fileNameDisplay)
        
    def OnNew(self, event = None):
        self.panel = self.createNewPanel()

    def OnOpen(self, event):
        dlg = wxFileDialog(self, "File to open",
            wildcard = "Blyte files (*.blyte)|*.blyte|All files|*",
            style = wxOPEN)
        if dlg.ShowModal() == wxID_OK:
            if not self.notebook.GetPage(self.findPage(self.panel))\
                   .ctrl.isUntouched():
                self.panel = self.createNewPanel()

            self.panel.ctrl.loadFile(dlg.GetPath())
            self.panel.ctrl.updateScreen()

        dlg.Destroy()

    def OnSave(self, event):
        self.panel.ctrl.OnSave()

    def OnSaveAs(self, event):
        self.panel.ctrl.OnSaveAs()

    def OnExport(self, event):
        self.panel.ctrl.OnExport()

    def OnClose(self, event = None):
        if not self.panel.ctrl.canBeClosed():
            return
        
        if self.notebook.GetPageCount() > 1:
            self.notebook.DeletePage(self.findPage(self.panel))
        else:
            self.panel.ctrl.createEmptySp()
            self.panel.ctrl.updateScreen()

    def OnRevert(self, event):
        self.panel.ctrl.OnRevert()

    def OnPrint(self, event):
        self.panel.ctrl.OnPrint()

    def OnSettings(self, event):
        self.panel.ctrl.OnSettings()

    def OnCut(self, event):
        self.panel.ctrl.OnCut()

    def OnCopy(self, event):
        self.panel.ctrl.OnCopy()

    def OnPaste(self, event):
        self.panel.ctrl.OnPaste()

    def OnSelectScene(self, event):
        self.panel.ctrl.OnSelectScene()

    def OnFindError(self, event):
        self.panel.ctrl.OnFindError()

    def OnFind(self, event):
        self.panel.ctrl.OnFind()

    def OnShowFormatting(self, event):
        self.showFormatting = self.menuBar.IsChecked(ID_EDIT_SHOW_FORMATTING)
        self.panel.ctrl.Refresh(False)

    def OnReformat(self, event):
        self.panel.ctrl.OnReformat()

    def OnPaginate(self, event = None):
        self.panel.ctrl.OnPaginate()

    def OnTitles(self, event):
        self.panel.ctrl.OnTitles()

    def OnHeaders(self, event):
        self.panel.ctrl.OnHeaders()

    def OnDialogueChart(self, event):
        self.panel.ctrl.OnDialogueChart()

    def OnCharacterReport(self, event):
        self.panel.ctrl.OnCharacterReport()

    def OnNameDb(self, event):
        if not hasattr(self, "names"):
            self.statusBar.SetStatusText("Opening name database...", 1)
            wxSafeYield()
            wxBeginBusyCursor()
            self.names = decode.readNames("names.dat")
            wxEndBusyCursor()
            self.panel.ctrl.updateCommon()

            if self.names.count == 0:
                wxMessageBox("Error opening name database", "Error",
                             wxOK, self)
                del self.names

                return

        dlg = namesdlg.NamesDlg(self, self.names)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCharMap(self, event):
        self.panel.ctrl.OnCharMap()

    def OnCompareScripts(self, event):
        self.panel.ctrl.OnCompareScripts()

    def OnHelpCommands(self, event):
        dlg = commandsdlg.CommandsDlg(self)
        dlg.Show()

    def OnAbout(self, event):
        win = splash.SplashWindow(self, -1)
        win.Show()
        
    def OnTypeCombo(self, event):
        self.panel.ctrl.OnTypeCombo(event)

    def OnCloseWindow(self, event):
        doExit = True
        if event.CanVeto() and self.isModifications():
            if wxMessageBox("You have unsaved changes. Are\n"
                            "you sure you want to exit?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxNO:
                doExit = False

        if doExit:
            util.removeTempFiles(cfg.tmpPrefix)
            self.Destroy()
            myApp.ExitMainLoop()
        else:
            event.Veto()

    def OnExit(self, event):
        self.Close(False)
        
    def OnSize(self, event):
        event.Skip()

class MyApp(wxApp):

    def OnInit(self):
        global cfg, mainFrame

        misc.init()
        util.init()
        
        cfg = config.Config()
        refreshGuiConfig()
                
        mainFrame = MyFrame(NULL, -1, "Blyte")
        mainFrame.init()
        mainFrame.Show(True)

        # windows needs this for some reason
        mainFrame.panel.ctrl.SetFocus()
        
        self.SetTopWindow(mainFrame)

        if "--no-splash" not in sys.argv:
            win = splash.SplashWindow(mainFrame, 5000)
            win.Show()
            win.Raise()
        
        return True

def main():
    global myApp
    
    myApp = MyApp(0)
    myApp.MainLoop()
