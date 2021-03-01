import config
import gutil
import misc
import undo
import util

import wx

class FindDlg(wx.Dialog):
    def __init__(self, parent, ctrl):
        wx.Dialog.__init__(self, parent, -1, "Find & Replace",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.WANTS_CHARS)

        self.ctrl = ctrl

        self.searchLine = -1
        self.searchColumn = -1
        self.searchWidth = -1

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(2, 2, 5, 20)
        gsizer.AddGrowableCol(1)

        gsizer.Add(wx.StaticText(self, -1, "Find what:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.findEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        gsizer.Add(self.findEntry, 0, wx.EXPAND)

        gsizer.Add(wx.StaticText(self, -1, "Replace with:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.replaceEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        gsizer.Add(self.replaceEntry, 0, wx.EXPAND)

        vsizer.Add(gsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.matchWholeCb = wx.CheckBox(self, -1, "Match whole word only")
        vsizer2.Add(self.matchWholeCb, 0, wx.TOP, pad)

        self.matchCaseCb = wx.CheckBox(self, -1, "Match case")
        vsizer2.Add(self.matchCaseCb, 0, wx.TOP, pad)

        hsizer2.Add(vsizer2, 0, wx.EXPAND | wx.RIGHT, 10)

        self.direction = wx.RadioBox(self, -1, "Direction",
                                    choices = ["Up", "Down"])
        self.direction.SetSelection(1)

        hsizer2.Add(self.direction, 1, 0)

        vsizer.Add(hsizer2, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.extraLabel = wx.StaticText(self, -1, "Search in:")
        vsizer.Add(self.extraLabel)

        self.elements = wx.CheckListBox(self, -1)

        # sucky wxMSW doesn't support client data for checklistbox items,
        # so we have to store it ourselves
        self.elementTypes = []

        for t in config.getTIs():
            self.elements.Append(t.name)
            self.elementTypes.append(t.lt)

        vsizer.Add(self.elements, 1, wx.EXPAND)

        hsizer.Add(vsizer, 1, wx.EXPAND)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        find = wx.Button(self, -1, "&Find next")
        vsizer.Add(find, 0, wx.EXPAND | wx.BOTTOM, 5)

        replace = wx.Button(self, -1, "&Replace")
        vsizer.Add(replace, 0, wx.EXPAND | wx.BOTTOM, 5)

        replaceAll = wx.Button(self, -1, " Replace all ")
        vsizer.Add(replaceAll, 0, wx.EXPAND | wx.BOTTOM, 5)

        self.moreButton = wx.Button(self, -1, "")
        vsizer.Add(self.moreButton, 0, wx.EXPAND | wx.BOTTOM, 5)

        hsizer.Add(vsizer, 0, wx.EXPAND | wx.LEFT, 30)

        self.Bind(wx.EVT_BUTTON, self.OnFind, id=find.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnReplace, id=replace.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnReplaceAll, id=replaceAll.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnMore, id=self.moreButton.GetId())

        gutil.btnDblClick(find, self.OnFind)
        gutil.btnDblClick(replace, self.OnReplace)

        self.Bind(wx.EVT_TEXT, self.OnText, id=self.findEntry.GetId())

        self.Bind(wx.EVT_TEXT_ENTER, self.OnFind, id=self.findEntry.GetId())
        self.Bind(wx.EVT_TEXT_ENTER, self.OnFind, id=self.replaceEntry.GetId())

        self.Bind(wx.EVT_CHAR, self.OnCharMisc)
        self.findEntry.Bind(wx.EVT_CHAR, self.OnCharEntry)
        self.replaceEntry.Bind(wx.EVT_CHAR, self.OnCharEntry)
        find.Bind(wx.EVT_CHAR, self.OnCharButton)
        replace.Bind(wx.EVT_CHAR, self.OnCharButton)
        replaceAll.Bind(wx.EVT_CHAR, self.OnCharButton)
        self.moreButton.Bind(wx.EVT_CHAR, self.OnCharButton)
        self.matchWholeCb.Bind(wx.EVT_CHAR, self.OnCharMisc)
        self.matchCaseCb.Bind(wx.EVT_CHAR, self.OnCharMisc)
        self.direction.Bind(wx.EVT_CHAR, self.OnCharMisc)
        self.elements.Bind(wx.EVT_CHAR, self.OnCharMisc)

        util.finishWindow(self, hsizer, center = False)

        self.loadState()
        self.findEntry.SetFocus()

    def loadState(self):
        self.findEntry.SetValue(self.ctrl.findDlgFindText)
        self.findEntry.SetSelection(-1, -1)

        self.replaceEntry.SetValue(self.ctrl.findDlgReplaceText)

        self.matchWholeCb.SetValue(self.ctrl.findDlgMatchWholeWord)
        self.matchCaseCb.SetValue(self.ctrl.findDlgMatchCase)

        self.direction.SetSelection(int(not self.ctrl.findDlgDirUp))

        count = self.elements.GetCount()
        tmp = self.ctrl.findDlgElements

        if (tmp == None) or (len(tmp) != count):
            tmp = [True] * self.elements.GetCount()

        for i in range(count):
            self.elements.Check(i, tmp[i])

        self.showExtra(self.ctrl.findDlgUseExtra)
        self.Center()

    def saveState(self):
        self.getParams()

        self.ctrl.findDlgFindText = misc.fromGUI(self.findEntry.GetValue())
        self.ctrl.findDlgReplaceText = misc.fromGUI(
            self.replaceEntry.GetValue())
        self.ctrl.findDlgMatchWholeWord = self.matchWhole
        self.ctrl.findDlgMatchCase = self.matchCase
        self.ctrl.findDlgDirUp = self.dirUp
        self.ctrl.findDlgUseExtra = self.useExtra

        tmp = []
        for i in range(self.elements.GetCount()):
            tmp.append(bool(self.elements.IsChecked(i)))

        self.ctrl.findDlgElements = tmp

    def OnMore(self, event):
        self.showExtra(not self.useExtra)

    def OnText(self, event):
        if self.ctrl.sp.mark:
            self.ctrl.sp.clearMark()
            self.ctrl.updateScreen()

    def OnCharEntry(self, event):
        self.OnChar(event, True, False)

    def OnCharButton(self, event):
        self.OnChar(event, False, True)

    def OnCharMisc(self, event):
        self.OnChar(event, False, False)

    def OnChar(self, event, isEntry, isButton):
        kc = event.GetKeyCode()

        if kc == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_OK)
            return

        if kc == wx.WXK_RETURN:
            if isButton:
                event.Skip()
                return
            else:
                self.OnFind()
                return

        if isEntry:
            event.Skip()
        else:
            if kc < 256:
                if chr(kc) == "f":
                    self.OnFind()
                elif chr(kc) == "r":
                    self.OnReplace()
                else:
                    event.Skip()
            else:
                event.Skip()

    def showExtra(self, flag):
        self.extraLabel.Show(flag)
        self.elements.Show(flag)

        self.useExtra = flag

        if flag:
            self.moreButton.SetLabel("<<< Less")
            pos = self.elements.GetPosition()

            # don't know of a way to get the vertical spacing of items in
            # a wx.CheckListBox, so estimate it at font height + 5 pixels,
            # which is close enough on everything I've tested.
            h = pos.y + len(self.elementTypes) * \
                (util.getFontHeight(self.elements.GetFont()) + 5) + 15
        else:
            self.moreButton.SetLabel("More >>>")
            h = max(self.extraLabel.GetPosition().y,
                    self.moreButton.GetPosition().y +
                    self.moreButton.GetClientSize().height + 5)

        self.SetSizeHints(self.GetClientSize().width, h)
        util.setWH(self, h = h)

    def getParams(self):
        self.dirUp = self.direction.GetSelection() == 0
        self.matchWhole = self.matchWholeCb.IsChecked()
        self.matchCase = self.matchCaseCb.IsChecked()

        if self.useExtra:
            self.elementMap = {}
            for i in range(self.elements.GetCount()):
                self.elementMap[self.elementTypes[i]] = \
                    self.elements.IsChecked(i)

    def typeIncluded(self, lt):
        if not self.useExtra:
            return True

        return self.elementMap[lt]

    def OnFind(self, event = None, autoFind = False):
        if not autoFind:
            self.getParams()

        value = misc.fromGUI(self.findEntry.GetValue())
        if not self.matchCase:
            value = util.upper(value)

        if value == "":
            return

        self.searchWidth = len(value)

        if self.dirUp:
            inc = -1
        else:
            inc = 1

        line = self.ctrl.sp.line
        col = self.ctrl.sp.column
        ls = self.ctrl.sp.lines

        if (line == self.searchLine) and (col == self.searchColumn):
            text = ls[line].text

            col += inc
            if col >= len(text):
                line += 1
                col = 0
            elif col < 0:
                line -= 1
                if line >= 0:
                    col = max(len(ls[line].text) - 1, 0)

        fullSearch = False
        if inc > 0:
            if (line == 0) and (col == 0):
                fullSearch = True
        else:
            if (line == (len(ls) - 1)) and (col == (len(ls[line].text))):
                fullSearch = True

        self.searchLine = -1

        while True:
            found = False

            while True:
                if (line >= len(ls)) or (line < 0):
                    break

                if self.typeIncluded(ls[line].lt):
                    text = ls[line].text
                    value = str(value)
                    if not self.matchCase:
                        text = util.upper(text)

                    if inc > 0:
                        res = text.find(value, col)
                    else:
                        res = text.rfind(value, 0, col + 1)

                    if res != -1:
                        if not self.matchWhole or (
                            util.isWordBoundary(text[res - 1 : res]) and
                            util.isWordBoundary(text[res + len(value) :
                                                     res + len(value) + 1])):

                            found = True

                            break

                line += inc
                if inc > 0:
                    col = 0
                else:
                    if line >= 0:
                        col = max(len(ls[line].text) - 1, 0)

            if found:
                self.searchLine = line
                self.searchColumn = res
                self.ctrl.sp.gotoPos(line, res)
                self.ctrl.sp.setMark(line, res + self.searchWidth - 1)

                if not autoFind:
                    self.ctrl.makeLineVisible(line)
                    self.ctrl.updateScreen()

                break
            else:
                if autoFind:
                    break

                if fullSearch:
                    wx.MessageBox("Search finished without results.",
                                  "No matches", wx.OK, self)

                    break

                if inc > 0:
                    s1 = "end"
                    s2 = "start"
                    restart = 0
                else:
                    s1 = "start"
                    s2 = "end"
                    restart = len(ls) - 1

                if wx.MessageBox("Search finished at the %s of the script. Do\n"
                                 "you want to continue at the %s of the script?"
                                 % (s1, s2), "Continue?",
                                 wx.YES_NO | wx.YES_DEFAULT, self) == wx.YES:
                    line = restart
                    fullSearch = True
                else:
                    break

        if not autoFind:
            self.ctrl.updateScreen()

    def OnReplace(self, event = None, autoFind = False):
        if self.searchLine == -1:
            return False

        value = util.toInputStr(misc.fromGUI(self.replaceEntry.GetValue()))
        ls = self.ctrl.sp.lines

        sp = self.ctrl.sp
        u = undo.SinglePara(sp, undo.CMD_MISC, self.searchLine)

        ls[self.searchLine].text = util.replace(
            ls[self.searchLine].text, value,
            self.searchColumn, self.searchWidth)

        sp.rewrapPara(sp.getParaFirstIndexFromLine(self.searchLine))

        self.searchLine = -1

        diff = len(value) - self.searchWidth

        if not self.dirUp:
            sp.column += self.searchWidth + diff
        else:
            sp.column -= 1

            if sp.column < 0:
                sp.line -= 1

                if sp.line < 0:
                    sp.line = 0
                    sp.column = 0

                    self.searchLine = 0
                    self.searchColumn = 0
                    self.searchWidth = 0
                else:
                    sp.column = len(ls[sp.line].text)

        sp.clearMark()
        sp.markChanged()

        u.setAfter(sp)
        sp.addUndo(u)

        self.OnFind(autoFind = autoFind)

        return True

    def OnReplaceAll(self, event = None):
        self.getParams()

        if self.searchLine == -1:
            self.OnFind(autoFind = True)

        count = 0
        while self.OnReplace(autoFind = True):
            count += 1

        if count != 0:
            self.ctrl.makeLineVisible(self.ctrl.sp.line)
            self.ctrl.updateScreen()

        wx.MessageBox("Replaced %d matches" % count, "Results", wx.OK, self)
