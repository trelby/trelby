import config
import gutil
import misc
import util

from wxPython.wx import *

class FindDlg(wxDialog):
    def __init__(self, parent, ctrl):
        wxDialog.__init__(self, parent, -1, "Find & Replace",
                          style = wxDEFAULT_DIALOG_STYLE | wxWANTS_CHARS)

        self.ctrl = ctrl
        self.didReplaces = False
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        vsizer = wxBoxSizer(wxVERTICAL)
        
        gsizer = wxFlexGridSizer(2, 2, 5, 20)
        gsizer.AddGrowableCol(1)
        
        gsizer.Add(wxStaticText(self, -1, "Find what:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.findEntry = wxTextCtrl(self, -1, style = wxTE_PROCESS_ENTER)
        gsizer.Add(self.findEntry, 0, wxEXPAND)

        gsizer.Add(wxStaticText(self, -1, "Replace with:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.replaceEntry = wxTextCtrl(self, -1, style = wxTE_PROCESS_ENTER)
        gsizer.Add(self.replaceEntry, 0, wxEXPAND)
        
        vsizer.Add(gsizer, 0, wxEXPAND | wxBOTTOM, 10)

        hsizer2 = wxBoxSizer(wxHORIZONTAL)

        vsizer2 = wxBoxSizer(wxVERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.matchWholeCb = wxCheckBox(self, -1, "Match whole word only")
        vsizer2.Add(self.matchWholeCb, 0, wxTOP, pad)

        self.matchCaseCb = wxCheckBox(self, -1, "Match case")
        vsizer2.Add(self.matchCaseCb, 0, wxTOP, pad)

        hsizer2.Add(vsizer2, 0, wxEXPAND | wxRIGHT, 10)

        self.direction = wxRadioBox(self, -1, "Direction",
                                    choices = ["Up", "Down"])
        self.direction.SetSelection(1)
        
        hsizer2.Add(self.direction, 1, 0)
        
        vsizer.Add(hsizer2, 0, wxEXPAND | wxBOTTOM, 10)

        self.extraLabel = wxStaticText(self, -1, "Search in:")
        vsizer.Add(self.extraLabel)

        self.elements = wxCheckListBox(self, -1)

        # sucky wxMSW doesn't support client data for checklistbox items,
        # so we have to store it ourselves
        self.elementTypes = []
        
        for t in config.getTIs():
            self.elements.Append(t.name)
            self.elementTypes.append(t.lt)

        vsizer.Add(self.elements, 1, wxEXPAND)
        
        hsizer.Add(vsizer, 1, wxEXPAND)
        
        vsizer = wxBoxSizer(wxVERTICAL)
        
        find = wxButton(self, -1, "&Find next")
        vsizer.Add(find, 0, wxEXPAND | wxBOTTOM, 5)

        replace = wxButton(self, -1, "&Replace")
        vsizer.Add(replace, 0, wxEXPAND | wxBOTTOM, 5)
        
        replaceAll = wxButton(self, -1, " Replace all ")
        vsizer.Add(replaceAll, 0, wxEXPAND | wxBOTTOM, 5)

        self.moreButton = wxButton(self, -1, "")
        vsizer.Add(self.moreButton, 0, wxEXPAND | wxBOTTOM, 5)

        hsizer.Add(vsizer, 0, wxEXPAND | wxLEFT, 30)

        EVT_BUTTON(self, find.GetId(), self.OnFind)
        EVT_BUTTON(self, replace.GetId(), self.OnReplace)
        EVT_BUTTON(self, replaceAll.GetId(), self.OnReplaceAll)
        EVT_BUTTON(self, self.moreButton.GetId(), self.OnMore)

        gutil.btnDblClick(find, self.OnFind)
        gutil.btnDblClick(replace, self.OnReplace)

        EVT_TEXT(self, self.findEntry.GetId(), self.OnText)

        EVT_TEXT_ENTER(self, self.findEntry.GetId(), self.OnFind)
        EVT_TEXT_ENTER(self, self.replaceEntry.GetId(), self.OnFind)

        EVT_CHAR(self, self.OnCharMisc)
        EVT_CHAR(self.findEntry, self.OnCharEntry)
        EVT_CHAR(self.replaceEntry, self.OnCharEntry)
        EVT_CHAR(find, self.OnCharButton)
        EVT_CHAR(replace, self.OnCharButton)
        EVT_CHAR(replaceAll, self.OnCharButton)
        EVT_CHAR(self.moreButton, self.OnCharButton)
        EVT_CHAR(self.matchWholeCb, self.OnCharMisc)
        EVT_CHAR(self.matchCaseCb, self.OnCharMisc)
        EVT_CHAR(self.direction, self.OnCharMisc)
        EVT_CHAR(self.elements, self.OnCharMisc)
        
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
        if self.ctrl.searchLine != -1:
            self.ctrl.searchLine = -1
            self.ctrl.updateScreen()
        
    def OnCharEntry(self, event):
        self.OnChar(event, True, False)

    def OnCharButton(self, event):
        self.OnChar(event, False, True)

    def OnCharMisc(self, event):
        self.OnChar(event, False, False)

    def OnChar(self, event, isEntry, isButton):
        kc = event.GetKeyCode()

        if kc == WXK_ESCAPE:
            self.EndModal(wxID_OK)
            return

        if kc == WXK_RETURN:
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
            # a wxCheckListBox, so estimate it at font height + 5 pixels,
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
        
        self.ctrl.searchWidth = len(value)
        
        if self.dirUp:
            inc = -1
        else:
            inc = 1
            
        line = self.ctrl.sp.line
        col = self.ctrl.sp.column
        ls = self.ctrl.sp.lines

        if (line == self.ctrl.searchLine) and (col == self.ctrl.searchColumn):
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

        self.ctrl.searchLine = -1
        
        while True:
            found = False

            while True:
                if (line >= len(ls)) or (line < 0):
                    break

                if self.typeIncluded(ls[line].lt):
                    text = ls[line].text
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
                self.ctrl.sp.line = line
                self.ctrl.sp.column = res
                self.ctrl.searchLine = line
                self.ctrl.searchColumn = res

                if not autoFind:
                    self.ctrl.makeLineVisible(line)
                    self.ctrl.updateScreen()

                break
            else:
                if autoFind:
                    break
                
                if fullSearch:
                    wxMessageBox("Search finished without results.",
                                 "No matches", wxOK, self)

                    break
                
                if inc > 0: 
                    s1 = "end"
                    s2 = "start"
                    restart = 0
                else:
                    s1 = "start"
                    s2 = "end"
                    restart = len(ls) - 1

                if wxMessageBox("Search finished at the %s of the script. Do\n"
                                "you want to continue at the %s of the script?"
                                % (s1, s2), "Continue?",
                                wxYES_NO | wxYES_DEFAULT, self) == wxYES:
                    line = restart
                    fullSearch = True
                else:
                    break

        if not autoFind:
            self.ctrl.updateScreen()
            
    def OnReplace(self, event = None, autoFind = False):
        if self.ctrl.searchLine != -1:
            value = util.toInputStr(misc.fromGUI(self.replaceEntry.GetValue()))
            ls = self.ctrl.sp.lines

            ls[self.ctrl.searchLine].text = util.replace(
                ls[self.ctrl.searchLine].text, value,
                self.ctrl.searchColumn, self.ctrl.searchWidth)

            self.ctrl.searchLine = -1

            diff = len(value) - self.ctrl.searchWidth

            if not self.dirUp:
                self.ctrl.sp.column += self.ctrl.searchWidth + diff
            else:
                self.ctrl.sp.column -= 1

                if self.ctrl.sp.column < 0:
                    self.ctrl.sp.line -= 1

                    if self.ctrl.sp.line < 0:
                        self.ctrl.sp.line = 0
                        self.ctrl.sp.column = 0
                        
                        self.ctrl.searchLine = 0
                        self.ctrl.searchColumn = 0
                        self.ctrl.searchWidth = 0
                    else:
                        self.ctrl.sp.column = len(ls[self.ctrl.sp.line].text)

            if diff != 0:
                self.didReplaces = True
            
            self.ctrl.sp.markChanged()
            self.OnFind(autoFind = autoFind)

            return True
        else:
            return False
            
    def OnReplaceAll(self, event = None):
        self.getParams()

        if self.ctrl.searchLine == -1:
            self.OnFind(autoFind = True)

        count = 0
        while self.OnReplace(autoFind = True):
            count += 1

        if count != 0:
            self.ctrl.makeLineVisible(self.ctrl.sp.line)
            self.ctrl.updateScreen()
        
        wxMessageBox("Replaced %d matches" % count, "Results", wxOK, self)
