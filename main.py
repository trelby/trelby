# -*- coding: ISO-8859-1 -*-

from error import *
import cfgdlg
import commandsdlg
import config
import decode
import dialoguechart
import finddlg
import misc
import namesdlg
import splash
import util

import copy
import os.path
import re
import string
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

ID_FILE_OPEN = 0
ID_FILE_SAVE = 1
ID_FILE_SAVE_AS = 2
ID_FILE_EXIT = 3
ID_FORMAT_REFORMAT = 4
ID_FILE_NEW = 5
ID_FILE_SETTINGS = 6
ID_FILE_CLOSE = 7
ID_FILE_REVERT = 8
ID_EDIT_CUT = 9
ID_EDIT_COPY = 10
ID_EDIT_PASTE = 11
ID_HELP_COMMANDS = 12
ID_HELP_ABOUT = 13
ID_FILE_EXPORT = 14
ID_EDIT_FIND = 15
ID_EDIT_SELECT_SCENE = 16
ID_EDIT_FIND_ERROR = 17
ID_EDIT_SHOW_FORMATTING = 18
ID_FORMAT_PAGINATE = 19
ID_TOOLS_NAME_DB = 20
ID_REPORTS_DIALOGUE_CHART = 21

def refreshGuiConfig():
    global cfgGui

    cfgGui = config.ConfigGui(cfg)

class Line:
    def __init__(self, lb = config.LB_LAST, type = config.ACTION, text = ""):
        self.lb = lb
        self.type = type
        self.text = text

    def __eq__(self, other):
        return (self.lb == other.lb) and (self.type == other.type) and\
               (self.text == other.text)
    
    def __ne__(self, other):
        return not self == other
        
    def __str__(self):
        return config.lb2text(self.lb) + config.linetype2text(self.type)\
               + self.text

    # replace some words, rendering the script useless except for
    # evaluation purposes
    def replace(self):
        self.text = re.sub(r"\b(\w){3}\b", "BUY", self.text)
        self.text = re.sub(r"\b(\w){4}\b", "DEMO", self.text)
        self.text = re.sub(r"\b(\w){5}\b", "TRIAL", self.text)
        self.text = re.sub(r"\b(\w){10}\b", "EVALUATION", self.text)
        
class Screenplay:
    def __init__(self):
        self.lines = []

    def __eq__(self, other):
        if len(self.lines) != len(other.lines):
            return False

        for i in range(len(self.lines)):
            if self.lines[i] != other.lines[i]:
                return False

        return True
    
    def __ne__(self, other):
        return not self == other
    
    def getEmptyLinesBefore(self, i):
        if i == 0:
            return 0
        
        if self.lines[i - 1].lb == config.LB_LAST:
            return cfg.types[self.lines[i].type].emptyLinesBefore
        else:
            return 0

    def replace(self):
        for i in range(len(self.lines)):
            self.lines[i].replace()
            
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
        self.sp.lines.append(Line(config.LB_LAST, config.SCENE, ""))
        self.setFile(None)
        self.makeBackup()
        
    def loadFile(self, fileName):
        try:
            try:
                f = open(fileName, "rt")

                try:
                    lines = f.readlines()
                finally:
                    f.close()

            except IOError, (errno, strerror):
                raise MiscError("IOError: %s" % strerror)
                
            sp = Screenplay()

            # used to keep track that element type only changes after a
            # LB_LAST line.
            prevType = None
            
            i = 0
            for i in range(len(lines)):
                str = util.fixNL(lines[i]).rstrip("\n")

                if len(str) == 0:
                    continue

                if len(str) < 2:
                    raise MiscError("Line %d has invalid syntax" % (i + 1))

                lb = config.text2lb(str[0])
                type = config.text2linetype(str[1])
                text = str[2:]

                if prevType and (type != prevType):
                    raise MiscError("Line %d has invalid element type" %
                                    (i + 1))
                
                line = Line(lb, type, text)
                sp.lines.append(line)

                if lb != config.LB_LAST:
                    prevType = type
                else:
                    prevType = None

            if len(sp.lines) == 0:
                raise MiscError("Empty file.")

            if sp.lines[-1].lb != config.LB_LAST:
                raise MiscError("Last line doesn't end an element")
            
            self.clearVars()
            self.sp = sp
            self.setFile(fileName)
            self.makeBackup()
            self.paginate()

            return True

        except NaspError, e:
            wxMessageBox("Error loading file: %s" % e, "Error",
                         wxOK, mainFrame)

            return False

    def saveFile(self, fileName):
        try:
            output = []
            ls = self.sp.lines
            for i in range(0, len(ls)):
                output.append(str(ls[i]) + "\n")
        
            try:
                f = open(fileName, "wt")

                try:
                    f.writelines(output)
                finally:
                    f.close()
                    
                self.setFile(fileName)
                self.makeBackup()
                
            except IOError, (errno, strerror):
                raise MiscError("IOError: %s" % strerror)
                
        except NaspError, e:
            wxMessageBox("Error saving file: %s" % e, "Error",
                         wxOK, mainFrame)

    # script must be correctly paginated before this is called
    def export(self, sp, fileName, doPages):
        try:
            output = []
            ls = sp.lines
            
            for p in range(1, len(self.pages)):
                start = self.pages[p - 1] + 1
                end = self.pages[p]

                if doPages and (p != 1):
                    output.append("\n%70s%d.\n\n" % (" ", p))

                    if self.needsMore(start - 1):
                        output.append(" " * cfg.getType(config.CHARACTER).
                                      indent + "OSKU (cont'd)\n")
                
                for i in range(start, end + 1):
                    line = ls[i]
                    tcfg = cfg.getType(line.type)
                    
                    if tcfg.isCaps:
                        text = util.upper(line.text)
                    else:
                        text = line.text

                    if i != start:
                        output.append(sp.getEmptyLinesBefore(i) * "\n")
                        
                    output.append(" " * tcfg.indent + text + "\n")

                if doPages and self.needsMore(i):
                    output.append(" " * cfg.getType(config.CHARACTER).
                        indent + "(MORE)\n")
        
            try:
                f = open(fileName, "wt")

                try:
                    f.writelines(output)
                finally:
                    f.close()
                    
            except IOError, (errno, strerror):
                raise MiscError("IOError: %s" % strerror)
                
        except NaspError, e:
            wxMessageBox("Error saving file: %s" % e, "Error",
                         wxOK, mainFrame)

    def makeBackup(self):
        self.backup = copy.deepcopy(self.sp)
        
    def setFile(self, fileName):
        self.fileName = fileName
        if fileName:
            self.fileNameDisplay = os.path.basename(fileName)
        else:
            self.fileNameDisplay = "<new>"
            
        mainFrame.setTabText(self.panel, self.fileNameDisplay)
        mainFrame.setTitle(self.fileNameDisplay)
            
    def updateTypeCb(self):
        util.reverseComboSelect(mainFrame.typeCb,
                                self.sp.lines[self.line].type)

    def reformatAll(self):
        #t = time.time()
        line = 0
        while 1:
            line += self.rewrapPara(line)
            if line >= len(self.sp.lines):
                break

        self.makeLineVisible(self.line)

        #t = time.time() - t
        #print "took %.3f seconds" % t

    def fillAutoComp(self):
        ls = self.sp.lines

        tcfg = cfg.getType(ls[self.line].type)
        if tcfg.doAutoComp:
            self.autoComp = self.getMatchingText(ls[self.line].text,
                                                 tcfg.type)
            self.autoCompSel = 0

    # wraps a single line into however many lines are needed, according to
    # the type's width. doesn't modify the input line, returns a list of
    # new lines.
    def wrapLine(self, line):
        ret = []
        tcfg = cfg.getType(line.type)

        # text remaining to be wrapped
        text = line.text
        
        while 1:
            if len(text) <= tcfg.width:
                ret.append(Line(line.lb, line.type, text))
                break
            else:
                i = text.rfind(" ", 0, tcfg.width + 1)

                if i >= 0:
                    ret.append(Line(config.LB_AUTO_SPACE, line.type,
                                    text[0:i]))
                    text = text[i + 1:]
                    
                else:
                    ret.append(Line(config.LB_AUTO_NONE, line.type,
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

        while ls[line2].lb not in(config.LB_LAST, config.LB_FORCED):
            line2 += 1

        # if cursor is in this paragraph, save its offset from the
        # beginning of the paragraph
        if (self.line >= line1) and (self.line <= line2):
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
            
        str = ls[line1].text
        for i in range(line1 + 1, line2 + 1):
            if ls[i - 1].lb == config.LB_AUTO_SPACE:
                str += " "
            str += ls[i].text

        ls[line1].text = str
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
        
    def convertCurrentTo(self, type):
        ls = self.sp.lines
        first, last = self.getElemIndexes()

        # if changing away from PAREN containing only "()", remove it
        if (first == last) and (ls[first].type == config.PAREN) and\
           (ls[first].text == "()"):
            ls[first].text = ""
            self.column = 0
            
        for i in range(first, last + 1):
            ls[i].type = type

        # if changing empty element to PAREN, add "()"
        if (first == last) and (ls[first].type == config.PAREN) and\
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
        str = ln.text
        preStr = str[:self.column]
        postStr = str[self.column:]
        newLine = Line(ln.lb, ln.type, postStr)
        ln.text = preStr
        ln.lb = config.LB_FORCED
        self.sp.lines.insert(self.line + 1, newLine)
        self.line += 1
        self.column = 0
    
    # delete character at given position and optionally position
    # cursor there.
    def deleteChar(self, line, column, posCursor = True):
        str = self.sp.lines[line].text
        str = str[:column] + str[column + 1:]
        self.sp.lines[line].text = str
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

        return self.sp.lines[line].type

    def getTypeOfNextElem(self, line):
        line = self.getElemLastIndexFromLine(line)
        line += 1
        if line >= len(self.sp.lines):
            return None

        return self.sp.lines[line].type
    
    def getSceneIndexesFromLine(self, line):
        top, bottom = self.getElemIndexesFromLine(line)
        ls = self.sp.lines
        
        while 1:
            if ls[top].type == config.SCENE:
                break
            
            tmp = top - 1
            if tmp < 0:
                break
            
            top, nothing = self.getElemIndexesFromLine(tmp)

        while 1:
            tmp = bottom + 1
            if tmp >= len(ls):
                break
            
            if ls[tmp].type == config.SCENE:
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
    def getMatchingText(self, text, type):
        text = util.upper(text)
        tcfg = cfg.getType(type)
        ls = self.sp.lines
        matches = {}
        last = None

        for i in range(0, len(ls)):
            if (ls[i].type == type) and (ls[i].lb == config.LB_LAST):
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

            if (l.type == config.PAREN) and isOnly and (l.text == "()"):
                msg = "Empty parenthetical."
                break

            if l.type == config.CHARACTER:
                if isLast and next and next not in\
                       (config.PAREN, config.DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(next).name,
                           cfg.getType(l.type).name)
                    break

            if l.type == config.PAREN:
                if isFirst and prev and prev not in\
                       (config.CHARACTER, config.DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(l.type).name, cfg.getType(prev).name)
                    break

            if l.type == config.DIALOGUE:
                if isFirst and prev and prev not in\
                       (config.CHARACTER, config.PAREN):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(l.type).name, cfg.getType(prev).name)
                    break

            line += 1
            
        if not msg:
            line = -1

        return (line, msg)

    # returns true if 'line', which must be the last line on a page, needs
    # (MORE) after it and the next page needs a "SOMEBODY (cont'd)"
    def needsMore(self, line):
        ls = self.sp.lines
        if ls[line].type in (config.DIALOGUE, config.PAREN)\
           and (line != (len(ls) - 1)) and\
           ls[line + 1].type in (config.DIALOGUE, config.PAREN):
            return True
        else:
            return False

    # returns total number of lines, not counting empty ones at the end,
    # on the given page. assumes that pagination is up-to-date.
    def linesOnPage(self, page):

        # not supposed to be called with invalid page argument, but you
        # never know...
        if (page < 1) or (page >= (len(self.pages) - 1)):
            return 1
        
        start = self.pages[page - 1] + 1
        end = self.pages[page]

        lines = 1
        for i in range(start + 1, end + 1):
            lines += self.sp.getEmptyLinesBefore(i) + 1

        if self.needsMore(start - 1):
            lines += 1

        if self.needsMore(end):
            lines += 1

        return lines
        
    def paginate(self):
        #t = time.time()
        
        self.pages = [-1]
        self.pagesNoAdjust = [-1]

        ls = self.sp.lines
        length = len(ls)
        lastBreak = -1

        # fast aliases for stuff
        lp = cfg.linesOnPage
        lbl = config.LB_LAST
        ct = cfg.types
        
        i = 0
        while 1:
            pageLines = 0

            # FIXME: need to adjust lp here if we have to put a (cont'd)
            # on top of the page. problem is it can take n lines if the
            # character's name is long, and the (cont'd) itself can change
            # the number of lines needed...

            # FIXME: decrease lp by 2 for every page but the first to
            # account for the page number
            
            #print "starting page %d at %d" % (len(self.pages), i)
            if i < length:
                pageLines = 1
                
                while i < (length - 1):

                    pageLines += 1
                    if ls[i].lb == lbl:
                        pageLines += ct[ls[i + 1].type].emptyLinesBefore

                    if pageLines > lp:
                        break

                    i += 1

            if i == length:
                if pageLines != 0:
                    self.pages.append(length - 1)
                    self.pagesNoAdjust.append(length - 1)
                    
                break

            self.pagesNoAdjust.append(i)

            line = ls[i]

            if line.type == config.SCENE:
                i = self.removeDanglingElement(i, config.SCENE, lastBreak)

            elif line.type == config.ACTION:
                if line.lb != config.LB_LAST:
                    first = self.getElemFirstIndexFromLine(i)

                    if first > (lastBreak + 1):
                        linesOnThisPage = i - first + 1
                        if linesOnThisPage < cfg.pbActionLines:
                            i = first - 1

                        i = self.removeDanglingElement(i, config.SCENE,
                                                       lastBreak)

            elif line.type == config.CHARACTER:
                i = self.removeDanglingElement(i, config.CHARACTER, lastBreak)
                i = self.removeDanglingElement(i, config.SCENE, lastBreak)

            elif line.type in (config.DIALOGUE, config.PAREN):
                if line.lb != config.LB_LAST or\
                       self.getTypeOfNextElem(i) in\
                       (config.DIALOGUE, config.PAREN):

                    cutDialogue = False
                    cutParen = False
                    while 1:
                        oldI = i
                        line = ls[i]
                        
                        if line.type == config.PAREN:
                            i = self.removeDanglingElement(i, config.PAREN,
                              lastBreak)
                            cutParen = True

                        elif line.type == config.DIALOGUE:
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

                        elif line.type == config.CHARACTER:
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

        #t = time.time() - t
        #print "paginate took %.4f seconds" % t

    def removeDanglingElement(self, line, type, lastBreak):
        while (self.sp.lines[line].type == type) and\
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
        mainFrame.statusBar.SetStatusText("Page: %3d / %3d (line %d)" %
            (self.line2page(self.line),
             self.line2page(len(self.sp.lines) - 1), self.line + 1), 0)

    def applyCfg(self, newCfg):
        global cfg
        
        cfg = copy.deepcopy(newCfg)
        cfg.recalc()
        refreshGuiConfig()
        self.reformatAll()
        self.updateScreen()

    def checkEval(self):
        if misc.isEval:
            wxMessageBox("This feature is not supported in the\n"
                         "evaluation version.", "Notice",
                         wxOK, mainFrame)
            return True

        return False
                
    def OnEraseBackground(self, event):
        pass
        
    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)
    
    def OnLeftDown(self, event, mark = False):
        self.autoComp = None
        pos = event.GetPosition()
        self.line = self.pos2line(pos)
        tcfg = cfg.getType(self.sp.lines[self.line].type)
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
        type = mainFrame.typeCb.GetClientData(mainFrame.typeCb.GetSelection())
        self.convertCurrentTo(type)
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

    def OnDialogueChart(self):
        self.paginate()

        dlg = dialoguechart.DialogueChartDlg(mainFrame, self)
        dlg.ShowModal()
        dlg.Destroy()

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

    def OnCut(self):
        if self.mark != -1:
            marked = self.getMarkedLines()

            ls = self.sp.lines
            
            mainFrame.clipboard = ls[marked[0] : marked[1] + 1]
            del ls[marked[0] : marked[1] + 1]
            
            if len(ls) == 0:
                ls.append(Line(config.LB_LAST, config.SCENE, ""))

            if (marked[0] != 0) and (marked[0] < len(ls)) and\
                   (ls[marked[0] - 1].type != ls[marked[0]].type):
                ls[marked[0] - 1].lb = config.LB_LAST

            if marked[0] < len(ls):
                self.line = marked[0]
                self.column = 0
            else:
                self.line = len(ls) - 1
                self.column = len(ls[self.line].text)
            
            self.mark = -1
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
                if ls[insertPos - 1].type != ls[insertPos].type:
                    ls[insertPos - 1].lb = config.LB_LAST

            if (self.line + 1) < len(ls):
                if ls[self.line].type != ls[self.line + 1].type:
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
                           wildcard = "NASP files (*.nasp)|*.nasp|All files|*",
                           style = wxSAVE | wxOVERWRITE_PROMPT)
        if dlg.ShowModal() == wxID_OK:
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnExport(self):
        line, msg = self.findError(0)

        if line != -1:
            if wxMessageBox("The script seems to contain errors.\n"
                            "Are you sure you want to export it?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, mainFrame) == wxNO:
                return
        
        dlg = wxFileDialog(mainFrame, "Filename to export as",
                           wildcard = "Text files (*.txt)|*.txt|All files|*",
                           style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            sp = copy.deepcopy(self.sp)
            if misc.isEval:
                sp.replace()
            self.export(sp, dlg.GetPath(), True)

        dlg.Destroy()

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
        tcfg = cfg.getType(ls[self.line].type)

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
            else:
                if not self.autoComp:
                    if self.isLastLineOfElem(self.line) and\
                       (ls[self.line].type == config.PAREN) and\
                       (ls[self.line].text[self.column:] == ")"):
                        self.column += 1

                    self.splitLine()
                    ls[self.line - 1].lb = config.LB_LAST

                    newType = tcfg.nextType
                    i = self.line
                    while 1:
                        ls[i].type = newType
                        if ls[i].lb == config.LB_LAST:
                            break
                        i += 1
                else:
                    ls[self.line].text = self.autoComp[self.autoCompSel]
                    self.column = len(ls[self.line].text)

                    self.splitLine()
                    ls[self.line - 1].lb = config.LB_LAST
                    ls[self.line].type = tcfg.nextType
                    
                self.rewrapPara()

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
            if self.column == len(ls[self.line].text):
                if self.line != (len(ls) - 1):
                    if ls[self.line].lb == config.LB_AUTO_NONE:
                        self.deleteChar(self.line + 1, 0, False)
                    self.joinLines(self.line)
            else:
                self.deleteChar(self.line, self.column)
                doAutoComp = AC_REDO

            self.rewrapPara()

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
            ch = string.upper(chr(kc))
            type = None
            if ch == "S":
                type = config.SCENE
            elif ch == "A":
                type = config.ACTION
            elif ch == "C":
                type = config.CHARACTER
            elif ch == "D":
                type = config.DIALOGUE
            elif ch == "P":
                type = config.PAREN
            elif ch == "T":
                type = config.TRANSITION

            if type != None:
                self.convertCurrentTo(type)
            else:
                ev.Skip()
                return
            
        elif kc == WXK_TAB:
            if not ev.ShiftDown():
                type = tcfg.nextTypeTab
            else:
                type = tcfg.prevTypeTab
                
            self.convertCurrentTo(type)

        elif kc == WXK_ESCAPE:
            self.mark = -1

        # FIXME: debug stuff
        elif (kc < 256) and (chr(kc) == "å"):
            self.loadFile("default.nasp")
        elif (kc < 256) and (chr(kc) == "Å"):
            self.OnSettings()
        
        elif (kc == WXK_SPACE) or (kc > 32) and (kc < 256):
            char = chr(kc)

            if self.capitalizeNeeded():
                char = util.upper(char)
            
            str = ls[self.line].text
            str = str[:self.column] + char + str[self.column:]
            ls[self.line].text = str
            self.column += 1
                
            tmp = str.upper()
            if (tmp == "EXT.") or (tmp == "INT."):
                if self.isOnlyLineOfElem(self.line):
                    ls[self.line].type = config.SCENE
            elif (tmp == "(") and\
                 ls[self.line].type in (config.DIALOGUE, config.CHARACTER) and\
                 self.isOnlyLineOfElem(self.line):
                ls[self.line].type = config.PAREN
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

        #t = time.time()
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
            tcfg = cfg.getType(l.type)

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

                    # FIXME: take these out once done debugging
                    dc.DrawText("%d" % self.linesOnPage(thisPage),
                                size.width - 100, y + cfg.fontYdelta / 2)
                    if self.needsMore(i):
                        dc.DrawText("(MORE)", size.width - 50,
                                    y + cfg.fontYdelta / 2)

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

            if tcfg.isCaps:
                text = util.upper(l.text)
            else:
                text = l.text

            if len(text) != 0:
                dc.SetFont(cfgGui.getType(l.type).font)
                dc.DrawText(text, cfg.offsetX + tcfg.indent * cfgGui.fontX, y)

                if tcfg.isUnderlined and (wxPlatform == "__WXGTK__"):
                    dc.SetPen(cfgGui.textPen)
                    util.drawLine(dc, cfg.offsetX + tcfg.indent *
                        cfgGui.fontX, y + cfg.fontYdelta - 1,
                        cfgGui.fontX * len(text) - 1, 0)

            y += cfg.fontYdelta
            i += 1

        if self.autoComp and (cursorY > 0):
            self.drawAutoComp(dc, cursorY, ccfg)
            
        #t = time.time() - t
        #print "paint took %.4f seconds" % t

    def drawAutoComp(self, dc, cursorY, tcfg):
        offset = 5

        # scroll bar width
        sbw = 10
        
        selBleed = 2

        size = self.GetClientSize()
        
        dc.SetFont(cfgGui.getType(tcfg.type).font)

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

        self.clipboard = None
        self.showFormatting = False
        
        fileMenu = wxMenu()
        fileMenu.Append(ID_FILE_NEW, "&New")
        fileMenu.Append(ID_FILE_OPEN, "&Open...\tCTRL-O")
        fileMenu.Append(ID_FILE_SAVE, "&Save\tCTRL-S")
        fileMenu.Append(ID_FILE_SAVE_AS, "Save &As...")
        fileMenu.Append(ID_FILE_EXPORT, "&Export...")
        fileMenu.Append(ID_FILE_CLOSE, "&Close")
        fileMenu.Append(ID_FILE_REVERT, "&Revert")
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
        editMenu.Append(ID_EDIT_FIND, "&Find && Replace\tCTRL-F")
        editMenu.Append(ID_EDIT_FIND_ERROR, "Find next &error\tCTRL-E")
        editMenu.AppendSeparator()
        editMenu.AppendCheckItem(ID_EDIT_SHOW_FORMATTING, "S&how formatting")
        
        formatMenu = wxMenu()
        formatMenu.Append(ID_FORMAT_REFORMAT, "&Reformat all")
        formatMenu.Append(ID_FORMAT_PAGINATE, "&Paginate")

        reportsMenu = wxMenu()
        reportsMenu.Append(ID_REPORTS_DIALOGUE_CHART, "&Dialogue chart")
        
        toolsMenu = wxMenu()
        toolsMenu.Append(ID_TOOLS_NAME_DB, "&Name database...")

        helpMenu = wxMenu()
        helpMenu.Append(ID_HELP_COMMANDS, "&Commands...")
        helpMenu.AppendSeparator()
        helpMenu.Append(ID_HELP_ABOUT, "&About")
        
        self.menuBar = wxMenuBar()
        self.menuBar.Append(fileMenu, "&File")
        self.menuBar.Append(editMenu, "&Edit")
        self.menuBar.Append(formatMenu, "F&ormat")
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
            self.typeCb.Append(t.name, t.type)

        # these are hidden here because they're much harder to find here
        # than in misc.pyo
        misc.isEval = False
        misc.licensedTo = "Evaluation version."
        misc.version = "0.43"
        misc.copyright = "© Oskusoft 2004. All rights reserved."

        hsizer.Add(self.typeCb)

        vsizer.Add(hsizer, 0, wxALL, 5)
        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND)

        self.notebook = wxNotebook(self, -1, style = wxCLIP_CHILDREN)
        vsizer.Add(self.notebook, 1, wxEXPAND)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND)

        self.statusBar = wxStatusBar(self)
        self.statusBar.SetFieldsCount(2)
        self.statusBar.SetStatusWidths([-1, -1])
        self.SetStatusBar(self.statusBar)

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
        EVT_MENU(self, ID_FILE_SETTINGS, self.OnSettings)
        EVT_MENU(self, ID_FILE_EXIT, self.OnExit)
        EVT_MENU(self, ID_EDIT_CUT, self.OnCut)
        EVT_MENU(self, ID_EDIT_COPY, self.OnCopy)
        EVT_MENU(self, ID_EDIT_PASTE, self.OnPaste)
        EVT_MENU(self, ID_EDIT_SELECT_SCENE, self.OnSelectScene)
        EVT_MENU(self, ID_EDIT_FIND_ERROR, self.OnFindError)
        EVT_MENU(self, ID_EDIT_FIND, self.OnFind)
        EVT_MENU(self, ID_EDIT_SHOW_FORMATTING, self.OnShowFormatting)
        EVT_MENU(self, ID_FORMAT_REFORMAT, self.OnReformat)
        EVT_MENU(self, ID_FORMAT_PAGINATE, self.OnPaginate)
        EVT_MENU(self, ID_REPORTS_DIALOGUE_CHART, self.OnDialogueChart)
        EVT_MENU(self, ID_TOOLS_NAME_DB, self.OnNameDb)
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
        self.notebook.AddPage(newPanel, "<new>", True)
        newPanel.ctrl.SetFocus()

        return newPanel

    def setTitle(self, text):
        self.SetTitle("Nasp - %s" % text)

    def setTabText(self, panel, text):
        i = self.findPage(panel)
        if i != -1:
            self.notebook.SetPageText(i, text)
    
    def findPage(self, panel):
        for i in range(self.notebook.GetPageCount()):
            p = self.notebook.GetPage(i)
            if p == panel:
                return i

        return -1

    def isModifications(self):
        for i in range(self.notebook.GetPageCount()):
            p = self.notebook.GetPage(i)
            if p.ctrl.isModified():
                return True

        return False

    def OnTimer(self, event):
        self.OnPaginate()

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
                           wildcard = "NASP files (*.nasp)|*.nasp|All files|*",
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

    def OnDialogueChart(self, event):
        self.panel.ctrl.OnDialogueChart()

    def OnNameDb(self, event):
        if not hasattr(self, "names"):
            self.statusBar.SetStatusText("Opening name database...", 1)
            wxSafeYield()
            wxBeginBusyCursor()
            self.names = decode.readNames("names.dat")
            wxEndBusyCursor()
            self.statusBar.SetStatusText("", 1)

            if self.names.count == 0:
                wxMessageBox("Error opening name database", "Error",
                             wxOK, self)
                del self.names

                return

        dlg = namesdlg.NamesDlg(self, self.names)
        dlg.ShowModal()
        dlg.Destroy()

    def OnHelpCommands(self, event):
        dlg = commandsdlg.CommandsDlg(self)
        dlg.Show()

    def OnAbout(self, event):
        win = splash.SplashWindow(self, 10000)
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

        util.setCharset()
        
        cfg = config.Config()
        refreshGuiConfig()
                
        mainFrame = MyFrame(NULL, -1, "Nasp")
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
