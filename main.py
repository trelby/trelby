#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

from error import *
import cfg
from cfgdlg import CfgDlg

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

def clamp(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    else:
        return val

class Line:
    def __init__(self, lb = cfg.LB_LAST, type = cfg.ACTION, text = ""):
        self.lb = lb
        self.type = type
        self.text = text

    def __eq__(self, other):
        return (self.lb == other.lb) and (self.type == other.type) and \
               (self.text == other.text)
    
    def __ne__(self, other):
        return not self == other
        
    def __str__(self):
        return cfg.lb2text(self.lb) + cfg.linetype2text(self.type) + self.text

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
        
        if self.lines[i - 1].lb == cfg.LB_LAST:
            return cfg.getTypeCfg(self.lines[i].type).emptyLinesBefore
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

                lb = cfg.text2lb(str[0])
                type = cfg.text2linetype(str[1])
                text = str[2:]

                line = Line(lb, type, text)
                sp.lines.append(line)

            if len(sp.lines) == 0:
                raise MiscError("empty file")
            
            self.sp = sp
            self.line = 0
            self.column = 0
            self.topLine = 0
            self.mark = -1
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
        if "typeCbRevMap" not in self.__dict__:
            self.typeCbRevMap = {}
            for i in range(mainFrame.typeCb.GetCount()):
                self.typeCbRevMap[mainFrame.typeCb.GetClientData(i)] = i
                
        type = self.sp.lines[self.line].type
        revType = self.typeCbRevMap[type]

        if mainFrame.typeCb.GetSelection() != revType:
            mainFrame.typeCb.SetSelection(revType)

    def reformatAll(self):
        t = time.time()
        line = 0
        while 1:
            line += self.rewrap(startLine = line, toElemEnd = true)
            if line >= len(self.sp.lines):
                break
        t = time.time() - t
        print "reformatted %d lines in %.2f seconds" % (line, t)
        
    def wrapLine(self, line):
        ret = []
        tcfg = cfg.getTypeCfg(line.type)

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
                    
                    ret.append(Line(cfg.LB_AUTO_SPACE, line.type,
                                    line.text[0:i]))
                    line.text = line.text[i + 1:]
                    
                else:
                    ret.append(Line(cfg.LB_AUTO_NONE, line.type,
                                    line.text[0:tcfg.width]))
                    line.text = line.text[tcfg.width:]
                    
        return ret

    def rewrap(self, startLine = -1, toElemEnd = False):
        ls = self.sp.lines
        tcfg = cfg.getTypeCfg(ls[self.line].type)

        if startLine == -1:
            line1 = self.line
        else:
            line1 = startLine

        total = 0
        while 1:
            line2 = line1

            while ls[line2].lb not in (cfg.LB_FORCED, cfg.LB_LAST):
                line2 += 1

            #print "rewrapping lines %d - %d" % (line1, line2)
            
            str = ls[line1].text
            for i in range(line1 + 1, line2 + 1):
                if ls[i - 1].lb == cfg.LB_AUTO_SPACE:
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
                if (line1 >= len(ls)) or (ls[line1].lb == cfg.LB_LAST):
                    break

        return total
        
    def convertCurrentTo(self, type):
        ls = self.sp.lines
        first, last = self.getElemIndexes()

        #print "first - last: %d - %d" % (first, last)
        for i in range(first, last + 1):
            ls[i].type = type

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
        ln.lb = cfg.LB_FORCED
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
            if self.sp.lines[tmp].lb == cfg.LB_LAST:
                break
            line -= 1

        return line
    
    def getElemLastIndex(self):
        ls = self.sp.lines

        last = self.line
        while 1:
            if ls[last].lb == cfg.LB_LAST:
                break
            if (last + 1) >= len(ls):
                break
            last += 1

        return last

    def isFirstLineOfElem(self, line):
        return self.getElemFirstIndexFromLine(line) == self.line
        
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
        
    def isFixedWidth(self, font):
        dc = wxMemoryDC()
        dc.SetFont(font)
        w1, h1 = dc.GetTextExtent("iiiii")
        w2, h2 = dc.GetTextExtent("OOOOO")

        return w1 == w2

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
                                                           
    def OnEraseBackground(self, event):
        pass
        
    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)
    
    def OnLeftDown(self, event, mark = False):
        pos = event.GetPosition()
        self.line = self.pos2line(pos)
        tcfg = cfg.getTypeCfg(self.sp.lines[self.line].type)
        x = pos.x - tcfg.indent * cfg.fontX - cfg.offsetX
        self.column = clamp(x / cfg.fontX, 0,
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
        self.updateScreen()

    def OnReformat(self, event):
        self.reformatAll()
        self.updateScreen()

    def createEmptySp(self):
        self.sp = Screenplay()
        self.sp.lines.append(Line(cfg.LB_LAST, cfg.SCENE, ""))
        self.line = 0
        self.column = 0
        self.topLine = 0
        self.mark = -1
        self.setFile(None)
        self.makeBackup()

    def canBeClosed(self):
        if self.isModified():
            if wxMessageBox("The script has been modified. Are you sure\n"
                            "you want to discard the changes?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxNO:
                return False

        return True

    def OnRevert(self, event):
        if self.fileName:
            if not self.canBeClosed():
                return
        
            self.loadFile(self.fileName)
            self.updateScreen()
            
    def OnSave(self, event):
        if self.fileName:
            self.saveFile(self.fileName)
        else:
            self.OnSaveAs()

    def OnSaveAs(self, event = None):
        dlg = wxFileDialog(self, "Filename to save as",
                           wildcard = "NASP files (*.nasp)|*.nasp|All files|*",
                           style = wxSAVE | wxOVERWRITE_PROMPT)
        if dlg.ShowModal() == wxID_OK:
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnSettings(self, event = None):
        dlg = CfgDlg(self, copy.deepcopy(cfg._types))
        dlg.ShowModal()
        dlg.Destroy()
        
        fd = wxFontData()
        fd.SetInitialFont(cfg.baseFont)
        dlg = wxFontDialog(self, fd)
        if dlg.ShowModal() == wxID_OK:
            cfg.baseFont = dlg.GetFontData().GetChosenFont()

            # FIXME: test fixed widthness and refuse to use if not
            #self.isFixedWidth(cfg.baseFont)

            cfg.sceneFont = wxFontFromNativeInfo(
                cfg.baseFont.GetNativeFontInfo())
            cfg.sceneFont.SetWeight(wxBOLD)
            
            self.updateScreen()

        dlg.Destroy()
        
    def OnKeyChar(self, ev):
        kc = ev.GetKeyCode()
        
        #print "kc: %d, ctrldown: %d" % (kc, ev.ControlDown())
        
        ls = self.sp.lines
        tcfg = cfg.getTypeCfg(ls[self.line].type)

        # FIXME: call ensureCorrectLine()
        
        if kc == WXK_RETURN:
            if ev.ShiftDown() or ev.ControlDown():
                self.splitLine()
                
                self.rewrap()
            else:
                self.splitLine()
                ls[self.line - 1].lb = cfg.LB_LAST
                
                newType = cfg.getNextType(ls[self.line].type)
                i = self.line
                while 1:
                    ls[i].type = newType
                    if ls[i].lb == cfg.LB_LAST:
                        break
                    i += 1
                
                self.rewrap()

        elif kc == WXK_BACK:
            if self.column == 0:
                if (self.line != 0):
                    self.joinLines(self.line - 1)
            else:
                self.deleteChar(self.line, self.column - 1)

            self.rewrap()
            
        elif (kc == WXK_DELETE) or (kc == KC_CTRL_D):
            if self.column == len(ls[self.line].text):
                if self.line != (len(ls) - 1):
                    if ls[self.line].lb == cfg.LB_AUTO_NONE:
                        self.deleteChar(self.line + 1, 0, False)
                    self.joinLines(self.line)
            else:
                self.deleteChar(self.line, self.column)

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
                
        elif (kc == WXK_LEFT) or (kc == KC_CTRL_B):
            self.column = max(self.column - 1, 0)
            
        elif (kc == WXK_RIGHT) or (kc == KC_CTRL_F):
            self.column = min(self.column + 1, len(ls[self.line].text))
            
        elif (kc == WXK_DOWN) or (kc == KC_CTRL_N):
            if self.line < (len(ls) - 1):
                self.line += 1
                if self.line >= (self.topLine + self.getLinesOnScreen()):
                    while (self.topLine + self.getLinesOnScreen() - 1)\
                          < self.line:
                        self.topLine += 1
                        
        elif (kc == WXK_UP) or (kc == KC_CTRL_P):
            if self.line > 0:
                self.line -= 1
                if self.line < self.topLine:
                    self.topLine -= 1
                    
        elif (kc == WXK_HOME) or (kc == KC_CTRL_A):
            self.column = 0
            
        elif (kc == WXK_END) or (kc == KC_CTRL_E):
            self.column = len(ls[self.line].text)

        elif (kc == WXK_PRIOR) or (ev.AltDown() and chr(kc) == "v"):
            self.topLine = max(self.topLine - self.getLinesOnScreen() - 2,
                0)
            self.line = min(self.topLine + 5, len(self.sp.lines) - 1)
            
        elif (kc == WXK_NEXT) or (kc == KC_CTRL_V):
            oldTop = self.topLine
            
            self.topLine += self.getLinesOnScreen() - 2
            if self.topLine >= len(ls):
                self.topLine = len(ls) - self.getLinesOnScreen() / 2

            if self.topLine < 0:
                self.topLine = 0
                
            self.line += self.topLine - oldTop
            self.line = clamp(self.line, 0, len(ls) - 1)
            
        elif ev.AltDown():
            ch = string.upper(chr(kc))
            type = None
            if ch == "S":
                type = cfg.SCENE
            elif ch == "A":
                type = cfg.ACTION
            elif ch == "C":
                type = cfg.CHARACTER
            elif ch == "D":
                type = cfg.DIALOGUE
            elif ch == "P":
                type = cfg.PAREN
            elif ch == "T":
                type = cfg.TRANSITION

            if type != None:
                self.convertCurrentTo(type)
            else:
                ev.Skip()
                return
            
        elif kc == WXK_TAB:
            type = ls[self.line].type

            if not ev.ShiftDown():
                type = cfg.getNextTypeTab(type)
            else:
                type = cfg.getPrevTypeTab(type)
                
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
                if (ls[self.line].lb == cfg.LB_LAST) and\
                       self.isFirstLineOfElem(self.line):
                    ls[self.line].type = cfg.SCENE

            self.rewrap()

        else:
            ev.Skip()
            return

        # FIXME: call ensureCorrectLine()
        self.column = min(self.column, len(ls[self.line].text))

        self.makeLineVisible(self.line)
        self.updateScreen()

    def OnPaint(self, event):
        ls = self.sp.lines

#        t = time.time()
        dc = wxBufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        dc.SetBrush(cfg.bgBrush)
        dc.SetPen(cfg.bgPen)
        dc.DrawRectangle(0, 0, size.width, size.height)
        dc.SetFont(cfg.baseFont)

        y = cfg.offsetY
        length = len(ls)

        marked = self.getMarkedLines()
        
        i = self.topLine
        while (y < size.height) and (i < length):
            y += self.sp.getEmptyLinesBefore(i) * cfg.fontYdelta

            if y >= size.height:
                break
            
            l = ls[i]
            tcfg = cfg.getTypeCfg(l.type)

            # FIXME: debug code, make a hidden config-option
            if 0:
                dc.SetPen(cfg.bluePen)
                dc.DrawLine(cfg.offsetX + tcfg.indent * cfg.fontX, y,
                    cfg.offsetX + tcfg.indent * cfg.fontX, y + cfg.fontYdelta)
                dc.DrawLine(cfg.offsetX + (tcfg.indent + tcfg.width)
                    * cfg.fontX, y, cfg.offsetX + (tcfg.indent + tcfg.width)
                    * cfg.fontX, y + cfg.fontYdelta)
                dc.SetTextForeground(cfg.redColor)
                dc.DrawText(cfg.lb2text(l.lb), 0, y)
                dc.SetTextForeground(cfg.blackColor)

            if (self.mark != -1) and self.isLineMarked(i, marked):
                dc.SetPen(cfg.selectedPen)
                dc.SetBrush(cfg.selectedBrush)
                dc.DrawRectangle(0, y, size.width, cfg.fontYdelta)
            
            if (i != 0) and (self.line2page(i - 1) != self.line2page(i)):
                dc.SetPen(cfg.pagebreakPen)
                dc.DrawLine(0, y, size.width, y)
                
            if i == self.line:
                dc.SetPen(cfg.cursorPen)
                dc.SetBrush(cfg.cursorBrush)
                dc.DrawRectangle(cfg.offsetX + (self.column + tcfg.indent)
                    * cfg.fontX, y, cfg.fontX, cfg.fontY)
                
            savedFont = False
            if l.type == cfg.SCENE:
                savedFont = True
                dc.SetFont(cfg.sceneFont)

            if tcfg.isCaps:
                text = l.text.upper()
            else:
                text = l.text

            dc.DrawText(text, cfg.offsetX + tcfg.indent * cfg.fontX, y)

            if savedFont:
                dc.SetFont(cfg.baseFont)
            
            y += cfg.fontYdelta
            i += 1

#        t = time.time() - t
#        print "paint took %.4f seconds" % t

class MyFrame(wxFrame):

    def __init__(self, parent, id, title):
        wxFrame.__init__(self, parent, id, title,
                         wxPoint(100, 100), wxSize(700, 830))

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

        formatMenu = wxMenu()
        formatMenu.Append(ID_REFORMAT, "&Reformat all")
        
        menuBar = wxMenuBar()
        menuBar.Append(fileMenu, "&File")
        menuBar.Append(formatMenu, "F&ormat")
        self.SetMenuBar(menuBar)

        EVT_SIZE(self, self.OnSize)

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.typeCb = wxComboBox(self, -1, style = wxCB_READONLY)
        self.typeCb.Append("Action", cfg.ACTION)
        self.typeCb.Append("Character", cfg.CHARACTER)
        self.typeCb.Append("Dialogue", cfg.DIALOGUE)
        self.typeCb.Append("Paren", cfg.PAREN)
        self.typeCb.Append("Scene", cfg.SCENE)
        self.typeCb.Append("Transition", cfg.TRANSITION)

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
        EVT_MENU(self, ID_REFORMAT, self.OnReformat)

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
        self.panel.ctrl.OnSave(event)

    def OnSaveAs(self, event):
        self.panel.ctrl.OnSaveAs(event)

    def OnClose(self, event = None):
        if not self.panel.ctrl.canBeClosed():
            return
        
        if self.notebook.GetPageCount() > 1:
            self.notebook.DeletePage(self.findPage(self.panel))
        else:
            self.panel.ctrl.createEmptySp()
            self.panel.ctrl.updateScreen()

    def OnRevert(self, event):
        self.panel.ctrl.OnRevert(event)

    def OnSettings(self, event):
        self.panel.ctrl.OnSettings(event)

    def OnTypeCombo(self, event):
        self.panel.ctrl.OnTypeCombo(event)

    def OnReformat(self, event):
        self.panel.ctrl.OnReformat(event)

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

        global mainFrame

        cfg.init()
        mainFrame = MyFrame(NULL, -1, "Nasp")
        mainFrame.init()
        mainFrame.Show(True)
        self.SetTopWindow(mainFrame)

        return True


app = MyApp(0)
app.MainLoop()
