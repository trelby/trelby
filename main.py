#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

from error import *
import config
from cfgdlg import CfgDlg
from commandsdlg import CommandsDlg
import util

import copy
import string
import time
import os.path
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
ID_REFORMAT = 4
ID_FILE_NEW = 5
ID_FILE_SETTINGS = 6
ID_FILE_CLOSE = 7
ID_FILE_REVERT = 8
ID_EDIT_CUT = 9
ID_EDIT_COPY = 10
ID_EDIT_PASTE = 11
ID_HELP_COMMANDS = 12

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
            return cfg.getType(self.lines[i].type).emptyLinesBefore
        else:
            return 0

class MyPanel(wxPanel):

    def __init__(self, parent, id):
        wxPanel.__init__(self, parent, id)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.scrollBar = wxScrollBar(self, -1, style = wxSB_VERTICAL)
        self.ctrl = MyCtrl(self, -1)

        hsizer.Add(self.ctrl, 1, wxEXPAND)
        hsizer.Add(self.scrollBar, 0, wxEXPAND)
        
        EVT_COMMAND_SCROLL(self, self.scrollBar.GetId(),
                           self.ctrl.OnScroll)
                           
        self.SetSizer(hsizer)

    
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

            i = 0
            for i in range(len(lines)):
                str = lines[i].strip()

                if len(str) == 0:
                    continue

                if len(str) < 2:
                    raise MiscError("line %d is invalid" % (i + 1))

                lb = config.text2lb(str[0])
                type = config.text2linetype(str[1])
                text = str[2:]

                line = Line(lb, type, text)
                sp.lines.append(line)

            if len(sp.lines) == 0:
                raise MiscError("empty file")
            
            self.clearVars()
            self.sp = sp
            self.setFile(fileName)
            self.makeBackup()

            return True

        except NaspError, e:
            wxMessageBox("Error loading file: %s" % e, "Error",
                         wxOK, self)

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
                         wxOK, self)

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
            line += self.rewrap(startLine = line, toElemEnd = true)
            if line >= len(self.sp.lines):
                break

        self.line = 0
        self.topLine = 0
        self.column = 0
        
        #t = time.time() - t
        #print "reformatted %d lines in %.2f seconds" % (line, t)

    def fillAutoComp(self):
        ls = self.sp.lines
        
        if ls[self.line].type in (config.SCENE, config.CHARACTER,
                                  config.TRANSITION):
            self.autoComp = self.getMatchingText(ls[self.line].text,
                                                 ls[self.line].type)
            self.autoCompSel = 0
        
    def wrapLine(self, line):
        ret = []
        tcfg = cfg.getType(line.type)

        firstWrap = True
        while 1:
            if len(line.text) <= tcfg.width:
                ret.append(Line(line.lb, line.type, line.text))
                break
            else:
                i = tcfg.width
                while (i >= 0) and (line.text[i] != " "):
                    i -= 1

                if firstWrap:
                    if i != -1 and i < self.column:
                        self.column = self.column - i - 1
                        self.line += 1
                    elif i == -1 and self.column > tcfg.width:
                        self.column = 1
                        self.line += 1

                    firstWrap = False
                
                if i >= 0:
                    #print "text: '%s'\n"\
                    #      "       %si" % (line.text, " " * i)
                    
                    ret.append(Line(config.LB_AUTO_SPACE, line.type,
                                    line.text[0:i]))
                    line.text = line.text[i + 1:]
                    
                else:
                    ret.append(Line(config.LB_AUTO_NONE, line.type,
                                    line.text[0:tcfg.width]))
                    line.text = line.text[tcfg.width:]
                    
        return ret

    def rewrap(self, startLine = -1, toElemEnd = False):
        ls = self.sp.lines

        if startLine == -1:
            line1 = self.line
        else:
            line1 = startLine

        total = 0
        while 1:
            line2 = line1

            while ls[line2].lb not in (config.LB_FORCED, config.LB_LAST):
                line2 += 1

            #print "rewrapping lines %d - %d" % (line1, line2)
            
            str = ls[line1].text
            for i in range(line1 + 1, line2 + 1):
                if ls[i - 1].lb == config.LB_AUTO_SPACE:
                    str += " "
                str += ls[i].text

            ls[line1].text = str
            ls[line1].lb = ls[line2].lb
            del ls[line1 + 1:line2 + 1]

            #print "wrap line: '%s'" % ls[line1].text
            wrappedLines = self.wrapLine(ls[line1])
            ls[line1:line1 + 1] = wrappedLines
            total += len(wrappedLines)
            line1 += len(wrappedLines)

            if not toElemEnd:
                break
            else:
                if (line1 >= len(ls)) or (ls[line1].lb == config.LB_LAST):
                    break

        return total
        
    def convertCurrentTo(self, type):
        ls = self.sp.lines
        first, last = self.getElemIndexes()

        if (first == last) and (ls[first].type == config.PAREN) and\
           (ls[first].text == "()"):
            ls[first].text = ""
            self.column = 0
            
        for i in range(first, last + 1):
            ls[i].type = type

        if (first == last) and (ls[first].type == config.PAREN) and\
               (len(ls[first].text) == 0):
            ls[first].text = "()"
            self.column = 1
            
        self.rewrap(startLine = first, toElemEnd = True)

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

    def getElemFirstIndex(self):
        return self.getElemFirstIndexFromLine(self.line)

    def getElemFirstIndexFromLine(self, line):
        while 1:
            tmp = line - 1
            if tmp < 0:
                break
            if self.sp.lines[tmp].lb == config.LB_LAST:
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
        return self.getElemFirstIndexFromLine(line) == self.line

    def isLastLineOfElem(self, line):
        return self.getElemLastIndexFromLine(line) == self.line

    def isOnlyLineOfElem(self, line):
        return self.isLastLineOfElem(line) and self.isFirstLineOfElem(line)
        
    def getElemIndexes(self):
        return (self.getElemFirstIndex(), self.getElemLastIndex())
        
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

    def line2page(self, n):
        return (n / 55) + 1

    def isLineVisible(self, line):
        bottom = self.topLine + self.getLinesOnScreen() - 1
        if (self.line >= self.topLine) and (self.line <= bottom):
            return True
        else:
            return False
        
    def makeLineVisible(self, line, redraw = False):
        if self.isLineVisible(line):
            return
        
        self.topLine = max(0, int(self.line - (self.getLinesOnScreen()
                                               * 0.66)))
        if not self.isLineVisible(line):
            self.topLine = line
            
        if redraw:
            self.Refresh(False)
        
    def adjustScrollBar(self):
        pageSize = self.getLinesOnScreen()
        self.panel.scrollBar.SetScrollbar(self.topLine, pageSize,
                                          len(self.sp.lines), pageSize) 

    # get a list of strings (single-line text elements for now) that
    # start with 'text' (not case sensitive) and are of of type
    # 'type'. ignores current line.
    def getMatchingText(self, text, type):
        ls = self.sp.lines
        text = text.upper()
        matches = {}
        last = None
        
        for i in range(0, len(ls)):
            if (ls[i].type == type) and (ls[i].lb == config.LB_LAST):
                if i != self.line and ls[i].text.upper().\
                       startswith(text):
                    matches[ls[i].text.upper()] = None
                    if i < self.line:
                        last = ls[i].text.upper()

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
        
    def updateScreen(self, redraw = True, setCommon = True):
        self.adjustScrollBar()
        
        if setCommon:
            self.updateCommon()
            
        if redraw:
            self.Refresh(False)

    # update GUI elements shared by all scripts, like statusbar etc
    def updateCommon(self):
        self.updateTypeCb()
        mainFrame.statusBar.SetStatusText("Page: %3d / %3d" %
            (self.line / 55 + 1, len(self.sp.lines)/55 + 1), 0)

    def applyCfg(self, newCfg):
        global cfg
        
        cfg = copy.deepcopy(newCfg)
        refreshGuiConfig()
        self.reformatAll()
        self.updateScreen()

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

    def canBeClosed(self):
        if self.isModified():
            if wxMessageBox("The script has been modified. Are you sure\n"
                            "you want to discard the changes?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxNO:
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
        
    def OnSave(self):
        if self.fileName:
            self.saveFile(self.fileName)
        else:
            self.OnSaveAs()

    def OnSaveAs(self):
        dlg = wxFileDialog(self, "Filename to save as",
                           wildcard = "NASP files (*.nasp)|*.nasp|All files|*",
                           style = wxSAVE | wxOVERWRITE_PROMPT)
        if dlg.ShowModal() == wxID_OK:
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnSettings(self):
        dlg = CfgDlg(self, copy.deepcopy(cfg), self.applyCfg)
        if dlg.ShowModal() == wxID_OK:
            self.applyCfg(dlg.cfg)

        dlg.Destroy()
        
    def OnKeyChar(self, ev):
        kc = ev.GetKeyCode()
        
        #print "kc: %d, ctrldown: %d" % (kc, ev.ControlDown())
        
        ls = self.sp.lines
        tcfg = cfg.getType(ls[self.line].type)

        # FIXME: call ensureCorrectLine()

        # what to do about auto-completion
        AC_DEL = 0
        AC_REDO = 1
        AC_KEEP = 2

        doAutoComp = AC_DEL
        
        if kc == WXK_RETURN:
            if ev.ShiftDown() or ev.ControlDown():
                self.splitLine()
                
                self.rewrap()
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
                    
                self.rewrap()

        elif kc == WXK_BACK:
            if self.column == 0:
                if (self.line != 0):
                    self.joinLines(self.line - 1)
            else:
                self.deleteChar(self.line, self.column - 1)
                doAutoComp = AC_REDO

            self.rewrap()
            
        elif kc == WXK_DELETE:
            if self.column == len(ls[self.line].text):
                if self.line != (len(ls) - 1):
                    if ls[self.line].lb == config.LB_AUTO_NONE:
                        self.deleteChar(self.line + 1, 0, False)
                    self.joinLines(self.line)
            else:
                self.deleteChar(self.line, self.column)
                doAutoComp = AC_REDO

            self.rewrap()

        elif ev.ControlDown():
            if kc == WXK_SPACE:
                self.mark = self.line
                
            elif kc == WXK_HOME:
                self.line = 0
                self.topLine = 0
                self.column = 0
                
            elif kc == WXK_END:
                self.line = len(self.sp.lines) - 1
                self.column = len(ls[self.line].text)
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
            self.column = len(ls[self.line].text)

        elif kc == WXK_PRIOR:
            self.topLine = max(self.topLine - self.getLinesOnScreen() - 2,
                0)
            self.line = min(self.topLine + 5, len(self.sp.lines) - 1)
            
        elif kc == WXK_NEXT:
            oldTop = self.topLine
            
            self.topLine += self.getLinesOnScreen() - 2
            if self.topLine >= len(ls):
                self.topLine = len(ls) - self.getLinesOnScreen() / 2

            if self.topLine < 0:
                self.topLine = 0
                
            self.line += self.topLine - oldTop
            self.line = util.clamp(self.line, 0, len(ls) - 1)
            
        elif ev.AltDown():
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

        elif (kc == WXK_ESCAPE):
            self.mark = -1
            
        # FIXME: debug stuff
        elif (chr(kc) == "å"):
            self.loadFile("default.nasp")
        elif (chr(kc) == "Å"):
            self.OnSettings()
            
        elif (kc == WXK_SPACE) or (kc > 32) and (kc < 256):
            str = ls[self.line].text
            str = str[:self.column] + chr(kc) + str[self.column:]
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
                
            self.rewrap()
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

#        t = time.time()
        dc = wxBufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        dc.SetBrush(cfgGui.bgBrush)
        dc.SetPen(cfgGui.bgPen)
        dc.DrawRectangle(0, 0, size.width, size.height)

        dc.SetTextForeground(cfg.textColor)
        
        y = cfg.offsetY
        length = len(ls)
        prevType = -1
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
            
            # FIXME: debug code, make a hidden config-option
            if 0:
                dc.SetPen(cfgGui.bluePen)
                dc.DrawLine(cfg.offsetX + tcfg.indent * cfgGui.fontX, y,
                            cfg.offsetX + tcfg.indent * cfgGui.fontX,
                            y + cfg.fontYdelta)
                dc.DrawLine(cfg.offsetX + (tcfg.indent + tcfg.width)
                    * cfgGui.fontX, y, cfg.offsetX + (tcfg.indent + tcfg.width)
                    * cfgGui.fontX, y + cfg.fontYdelta)
                dc.SetTextForeground(cfgGui.redColor)
                dc.DrawText(config.lb2text(l.lb), 0, y)
                dc.SetTextForeground(cfg.textColor)

            if (i != 0) and (self.line2page(i - 1) != self.line2page(i)):
                dc.SetPen(cfgGui.pagebreakPen)
                dc.DrawLine(0, y, size.width, y)
                
            if i == self.line:
                cursorY = y
                ccfg = tcfg
                dc.SetPen(cfgGui.cursorPen)
                dc.SetBrush(cfgGui.cursorBrush)
                dc.DrawRectangle(cfg.offsetX + (self.column + tcfg.indent)
                    * cfgGui.fontX, y, cfgGui.fontX, cfgGui.fontY)

            if l.type != prevType:
                dc.SetFont(cfgGui.getType(l.type).font)

            if tcfg.isCaps:
                text = l.text.upper()
            else:
                text = l.text

            dc.DrawText(text, cfg.offsetX + tcfg.indent * cfgGui.fontX, y)

            y += cfg.fontYdelta
            i += 1
            prevType = l.type

        if self.autoComp and (cursorY > 0):
            self.drawAutoComp(dc, cursorY, ccfg)
            
#        t = time.time() - t
#        print "paint took %.4f seconds"

    def drawAutoComp(self, dc, cursorY, tcfg):
        offset = 5
        sbw = 10
        selBleed = 2

        dc.SetFont(cfgGui.getType(tcfg.type).font)

        show = min(10, len(self.autoComp))
        doSbw = show < len(self.autoComp)
        
        startPos = (self.autoCompSel / show) * show
        endPos = min(startPos + show, len(self.autoComp))
        if endPos == len(self.autoComp):
            startPos = max(0, endPos - show)

        w = 0
        for i in range(startPos, endPos):
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
            dc.DrawLine(posX + w - offset * 2 - sbw,
                posY,
                posX + w - offset * 2 - sbw,
                posY + h)
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
        
        fileMenu = wxMenu()
        fileMenu.Append(ID_FILE_NEW, "&New")
        fileMenu.Append(ID_FILE_OPEN, "&Open...\tCTRL-O")
        fileMenu.Append(ID_FILE_SAVE, "&Save\tCTRL-S")
        fileMenu.Append(ID_FILE_SAVE_AS, "Save &As...")
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
        
        formatMenu = wxMenu()
        formatMenu.Append(ID_REFORMAT, "&Reformat all")

        helpMenu = wxMenu()
        helpMenu.Append(ID_HELP_COMMANDS, "&Commands...")
        
        menuBar = wxMenuBar()
        menuBar.Append(fileMenu, "&File")
        menuBar.Append(editMenu, "&Edit")
        menuBar.Append(formatMenu, "F&ormat")
        menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(menuBar)

        EVT_SIZE(self, self.OnSize)

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.typeCb = wxComboBox(self, -1, style = wxCB_READONLY)

        for t in cfg.types.values():
            self.typeCb.Append(t.name, t.type)

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
        EVT_MENU(self, ID_FILE_CLOSE, self.OnClose)
        EVT_MENU(self, ID_FILE_REVERT, self.OnRevert)
        EVT_MENU(self, ID_FILE_SETTINGS, self.OnSettings)
        EVT_MENU(self, ID_FILE_EXIT, self.OnExit)
        EVT_MENU(self, ID_EDIT_CUT, self.OnCut)
        EVT_MENU(self, ID_EDIT_COPY, self.OnCopy)
        EVT_MENU(self, ID_EDIT_PASTE, self.OnPaste)
        EVT_MENU(self, ID_REFORMAT, self.OnReformat)
        EVT_MENU(self, ID_HELP_COMMANDS, self.OnHelpCommands)

        EVT_CLOSE(self, self.OnCloseWindow)
        
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

    def OnReformat(self, event):
        self.panel.ctrl.OnReformat()

    def OnHelpCommands(self, event):
        dlg = CommandsDlg(self)
        dlg.Show()
        
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
        else:
            event.Veto()

    def OnExit(self, event):
        self.Close(False)
        
    def OnSize(self, event):
        event.Skip()

class MyApp(wxApp):

    def OnInit(self):
        global cfg, mainFrame

        cfg = config.Config()
        refreshGuiConfig()
        
        mainFrame = MyFrame(NULL, -1, "Nasp")
        mainFrame.init()
        mainFrame.Show(True)
        self.SetTopWindow(mainFrame)

        return True


app = MyApp(0)
app.MainLoop()
