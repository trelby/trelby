import cfg
import string
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

ID_OPEN = 0
ID_SAVE = 1
ID_SAVE_AS = 2
ID_EXIT = 3
ID_REFORMAT = 4

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

    def __str__(self):
        return cfg.lb2text(self.lb) + cfg.linetype2text(self.type) + self.text

class Screenplay:
    def __init__(self):
        self.lines = []

    def getEmptyLinesBefore(self, i):
        if i == 0:
            return 0
        
        if self.lines[i - 1].lb == cfg.LB_LAST:
            return cfg.getTypeCfg(self.lines[i].type).emptyLinesBefore
        else:
            return 0
    
class MyCtrl(wxControl):

    def __init__(self, parent, id):
        wxControl.__init__(self, parent, id)#, style=wxWANTS_CHARS)

        self.line = 0
        self.column = 0

        self.topLine = 0
        
        EVT_SIZE(self, self.OnSize)
        EVT_PAINT(self, self.OnPaint)
        EVT_LEFT_DOWN(self, self.OnLeftDown)
        EVT_CHAR(self, self.OnKeyChar)

    def init(self):
        self.bluePen = wxPen(wxColour(0, 0, 255))
        self.redColor = wxColour(255, 0, 0)
        self.blackColor = wxColour(0, 0, 0)

        self.bgColor = wxColour(204, 204, 204)
        self.bgBrush = wxBrush(self.bgColor)
        self.bgPen = wxPen(self.bgColor)

        self.cursorColor = wxColour(205, 0, 0)
        self.cursorBrush = wxBrush(self.cursorColor)
        self.cursorPen = wxPen(self.cursorColor)
        
        self.pagebreakPen = wxPen(wxColour(128, 128, 128),
            style = wxSHORT_DASH)
        
        cfg.baseFont = wxFont(cfg.fontY, wxMODERN, wxNORMAL, wxNORMAL)

#         fd = wxFontData()
#         dlg = wxFontDialog(self, fd)
#         if dlg.ShowModal() == wxID_OK:
#             cfg.baseFont = dlg.GetFontData().GetChosenFont()
            
#         print "basefont facename: %s" % cfg.baseFont.GetFaceName()
#         print "basefont native: %s" % cfg.baseFont.GetNativeFontInfoDesc()
#         print "basefont isfixedwidth: %s" % cfg.baseFont.IsFixedWidth()
        
        self.loadFile("default.nasp")
        self.updateScreen(redraw = False)
        
    def loadFile(self, fileName):
        try:
            f = open(fileName, "rt")

            try:
                lines = f.readlines()
            finally:
                f.close()
        except IOError:
            print "got IOError"
            
            return

        sp = Screenplay()
        
        i = 0
        for i in range(len(lines)):
            str = lines[i].strip()
            
            if len(str) == 0:
                continue

            if len(str) < 2:
                raise Exception("line %d is invalid" % i)

            lb = cfg.text2lb(str[0])
            type = cfg.text2linetype(str[1])
            text = str[2:]

            line = Line(lb, type, text)
            sp.lines.append(line)

        self.sp = sp

    def saveFile(self, fileName):
        f = open(fileName, "wt")

        ls = self.sp.lines
        for i in range(0, len(ls)):
            f.write(str(ls[i]) + "\n")

        f.close()
        
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

    def line2page(self, n):
        return (n / 55) + 1
    
    def adjustScrollBar(self):
        sb = mainFrame.scrollBar

        pageSize = self.getLinesOnScreen()
        sb.SetScrollbar(self.topLine, pageSize, len(self.sp.lines), pageSize) 

    def updateScreen(self, redraw = True):
        mainFrame.statusBar.SetStatusText("Page: %3d / %3d" %
            (self.line / 55 + 1, len(self.sp.lines)/55 + 1), 0)
                                                           
        self.updateTypeCb()
        self.adjustScrollBar()
        if redraw:
            self.Refresh(False)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)
    
    def OnLeftDown(self, event):
        #pos = event.GetPosition()
        #print "pos: %s" % event.GetPosition()
        pass

    def OnTypeCombo(self, event):
        type = mainFrame.typeCb.GetClientData(mainFrame.typeCb.GetSelection())
        self.convertCurrentTo(type)
        self.updateScreen()

    def OnScroll(self, event):
        pos = mainFrame.scrollBar.GetThumbPosition()
        self.topLine = pos
        self.updateScreen()

    def OnReformat(self, event):
        self.reformatAll()
        self.updateScreen()

    def OnSave(self, event):
        self.saveFile("output.nasp")
        
    def OnKeyChar(self, event):
        kc = event.GetKeyCode()

        ls = self.sp.lines
        tcfg = cfg.getTypeCfg(ls[self.line].type)
        
        if kc == WXK_RETURN:
            if event.ShiftDown() or event.ControlDown():
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
            
        elif (kc == WXK_LEFT) or (kc == KC_CTRL_B):
            self.column = max(self.column - 1, 0)
            
        elif (kc == WXK_RIGHT) or (kc == KC_CTRL_F):
            self.column = min(self.column + 1, len(ls[self.line].text))
            
        elif (kc == WXK_DOWN) or (kc == KC_CTRL_N):
            if self.line < (len(ls) - 1):
                self.line += 1
                self.column = min(self.column, len(ls[self.line].text))
                if self.line >= (self.topLine + self.getLinesOnScreen()):
                    while (self.topLine + self.getLinesOnScreen() - 1)\
                          < self.line:
                        self.topLine += 1
                        
        elif (kc == WXK_UP) or (kc == KC_CTRL_P):
            if self.line > 0:
                self.line -= 1
                self.column = min(self.column, len(ls[self.line].text))
                if self.line < self.topLine:
                    self.topLine -= 1
                    
        elif (kc == WXK_HOME) or (kc == KC_CTRL_A):
            self.column = 0
            
        elif (kc == WXK_END) or (kc == KC_CTRL_E):
            self.column = len(ls[self.line].text)

        elif (kc == WXK_PRIOR) or (event.AltDown() and chr(kc) == "v"):
            self.topLine = max(self.topLine - self.getLinesOnScreen() - 2,
                0)
            self.line = self.topLine + 5
            
        elif (kc == WXK_NEXT) or (kc == KC_CTRL_V):
            oldTop = self.topLine
            
            self.topLine += self.getLinesOnScreen() - 2
            if self.topLine >= len(ls):
                self.topLine = len(ls) - self.getLinesOnScreen() / 2

            if self.topLine < 0:
                self.topLine = 0
                
            self.line += self.topLine - oldTop
            self.line = clamp(self.line, 0, len(ls) - 1)
            
        elif event.AltDown():
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
                event.Skip()
                return
            
        elif kc == WXK_TAB:
            type = ls[self.line].type

            if not event.ShiftDown():
                type = cfg.getNextTypeTab(type)
            else:
                type = cfg.getPrevTypeTab(type)
                
            self.convertCurrentTo(type)
            
        elif kc == WXK_ESCAPE:
            mainFrame.Close(True)
            return
        
        elif (kc == WXK_SPACE) or (kc > 32) and (kc < 256):
            str = ls[self.line].text
            str = str[:self.column] + chr(kc) + str[self.column:]
            ls[self.line].text = str
            self.column += 1

            tmp = str.upper()
            if (tmp == "EXT.") or (tmp == "INT."):
                if (ls[self.line].lb == cfg.LB_LAST) and \
                   (ls[self.line].type == cfg.ACTION) and\
                   self.isFirstLineOfElem(self.line):
                    ls[self.line].type = cfg.SCENE

            self.rewrap()
            
        else:
            print "something other than printable/handled character (%d)" % kc

        self.updateScreen()

    def OnPaint(self, event):
        ls = self.sp.lines

#        t = time.time()
        dc = wxBufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        dc.SetBrush(self.bgBrush)
        dc.SetPen(self.bgPen)
        dc.DrawRectangle(0, 0, size.width, size.height)
        dc.SetFont(cfg.baseFont)

        y = cfg.offsetY
        length = len(ls)

        i = self.topLine
        while (y < size.height) and (i < length):
            y += self.sp.getEmptyLinesBefore(i) * cfg.fontYdelta

            if y >= size.height:
                break
            
            l = ls[i]
            tcfg = cfg.getTypeCfg(l.type)

            # FIXME: debug code, make a hidden config-option
            if 0:
                dc.SetPen(self.bluePen)
                dc.DrawLine(cfg.offsetX + tcfg.indent * cfg.fontX, y,
                    cfg.offsetX + tcfg.indent * cfg.fontX, y + cfg.fontYdelta)
                dc.DrawLine(cfg.offsetX + (tcfg.indent + tcfg.width)
                    * cfg.fontX, y, cfg.offsetX + (tcfg.indent + tcfg.width)
                    * cfg.fontX, y + cfg.fontYdelta)
                dc.SetTextForeground(self.redColor)
                dc.DrawText(cfg.lb2text(l.lb), 0, y)
                dc.SetTextForeground(self.blackColor)

            if (i != 0) and (self.line2page(i - 1) != self.line2page(i)):
                dc.SetPen(self.pagebreakPen)
                dc.DrawLine(0, y, size.width, y)
                
            if i == self.line:
                dc.SetPen(self.cursorPen)
                dc.SetBrush(self.cursorBrush)
                dc.DrawRectangle(cfg.offsetX + (self.column + tcfg.indent)
                    * cfg.fontX, y, cfg.fontX, cfg.fontY)
                
            savedFont = None
            if l.type == cfg.SCENE:
                savedFont = dc.GetFont()
                dc.SetFont(wxFont(cfg.fontY, wxMODERN, wxNORMAL, wxBOLD))

            if tcfg.isCaps:
                text = l.text.upper()
            else:
                text = l.text

            dc.DrawText(text, cfg.offsetX + tcfg.indent * cfg.fontX, y)

            if savedFont:
                dc.SetFont(savedFont)
            
            y += cfg.fontYdelta
            i += 1

#        t = time.time() - t
#        print "paint took %.4f seconds" % t

class MyFrame(wxFrame):

    def __init__(self, parent, id, title):
        wxFrame.__init__(self, parent, id, title,
                         wxPoint(100, 100), wxSize(700, 830))

        fileMenu = wxMenu()
        fileMenu.Append(ID_OPEN, "&Open...")
        fileMenu.Append(ID_SAVE, "&Save")
        fileMenu.Append(ID_SAVE_AS, "Save &As")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_EXIT, "E&xit")

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
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.ctrl = MyCtrl(self, -1)
        size = self.GetSize()
        self.ctrl.SetSize(wxSize(size.width, size.height-30))
        self.ctrl.SetFocus()
        hsizer.Add(self.ctrl, 1, wxEXPAND)

        self.scrollBar = wxScrollBar(self, -1, style = wxSB_VERTICAL)
        hsizer.Add(self.scrollBar, 0, wxEXPAND)
        
        vsizer.Add(hsizer, 1, wxEXPAND)
        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND)

        self.statusBar = wxStatusBar(self)
        self.statusBar.SetFieldsCount(2)
        self.statusBar.SetStatusWidths([-1, -1])
        self.SetStatusBar(self.statusBar)
        
        EVT_COMBOBOX(self, self.typeCb.GetId(), self.ctrl.OnTypeCombo)

        EVT_COMMAND_SCROLL(self, self.scrollBar.GetId(), self.ctrl.OnScroll)
                           
        EVT_MENU(self, ID_SAVE, self.ctrl.OnSave)
        EVT_MENU(self, ID_EXIT, self.OnExit)
        EVT_MENU(self, ID_REFORMAT, self.ctrl.OnReformat)

        self.Layout()
        
    def init(self):
        self.ctrl.init()

    def OnCloseWindow(self, event):
        self.Destroy()

    def OnExit(self, event):
        self.Close(True)
        
    def OnSize(self, event):
        event.Skip()

class MyApp(wxApp):

    def OnInit(self):

        global mainFrame
        
        mainFrame = MyFrame(NULL, -1, "Nasp")
        mainFrame.init()
        mainFrame.Show(True)
        self.SetTopWindow(mainFrame)

        return True


app = MyApp(0)
app.MainLoop()
