import gutil
import opts
import util

import os
import os.path
import sys

from wxPython.wx import *

def init(doWX = True):
    global isWindows, isUnix, unicodeFS, wx26, wxIsUnicode, progPath, \
           confPath, tmpPrefix

    # prefix used for temp files
    tmpPrefix = "oskusoft-blyte-tmp-"

    isWindows = False
    isUnix = False

    if wxPlatform == "__WXMSW__":
        isWindows = True
    else:
        isUnix = True

    # are we using wxWidgets 2.6
    wx26 = (wxMAJOR_VERSION == 2) and (wxMINOR_VERSION == 6)

    # are we using a Unicode build of wxWidgets
    wxIsUnicode = wx26 and ("unicode" in wxPlatformInfo)

    # does this platform support using Python's unicode strings in various
    # filesystem calls; if not, we need to convert filenames to UTF-8
    # before using them.
    unicodeFS = isWindows

    # stupid hack to keep testcases working, since they don't initialize
    # opts (the doWX name is just for similary with util, and to confuse
    # people trying to disassemble the code)
    if not doWX or opts.isTest:
        progPath = "."
        confPath = ".blyte"
    else:
        if isUnix:
            progPath = "/usr/local/blyte"
            confPath = os.environ["HOME"] + "/.blyte"
        else:
            progPath = r"C:\Program Files\Oskusoft\Blyte"
            confPath = progPath + r"\conf"

    # convert the path settings to Unicode
    progPath = unicode(progPath, "UTF-8")
    confPath = unicode(confPath, "UTF-8")

# convert s, which is returned from the wxWidgets GUI and is either an
# Unicode string or a normal string, to a normal string.
def fromGUI(s):
    if not wxIsUnicode:
        return s
    else:
        return s.encode("ISO-8859-1", "ignore")

# convert s, which is returned from the wxWidgets GUI and is either an
# Unicode string or a normal string, to a Unicode string. since the only
# thing we use full Unicode for is file/directory names, and those are
# UTF-8 on UNIXes, we use that instead of ISO-8859-1 here.
def fromGUIUnicode(s):
    if wxIsUnicode:
        return s
    else:
        return unicode(s, "UTF-8", "ignore")

# convert s, which is an Unicode string, to a form suitable for passing to
# wxWidgets for display. since the only thing we use full Unicode for is
# file/directory names, and those are UTF-8 on UNIXes, we use that instead
# of ISO-8859-1 here.
def toGUIUnicode(s):
    if wxIsUnicode:
        return s
    else:
        return s.encode("UTF-8")

# convert s, which is an Unicode string, to an object suitable for passing
# to Python's file APIs. this is either the Unicode string itself, if the
# platform supports Unicode-based APIs (and Python has implemented support
# for it), or the Unicode string converted to UTF-8 on other platforms.
def toPath(s):
    if unicodeFS:
        return s
    else:
        return s.encode("UTF-8")

class MyColorSample(wxWindow):
    def __init__(self, parent, id, size):
        wxWindow.__init__(self, parent, id, size = size)

        EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, event):
        dc = wxPaintDC(self)

        w, h = self.GetClientSizeTuple()
        br = wxBrush(self.GetBackgroundColour())
        dc.SetBrush(br)
        dc.DrawRectangle(0, 0, w, h)

# our own version of a tab control, which exists for two reasons: it does
# not care where it is physically located, which allows us to combine it
# with other controls on a horizontal row, and it consumes less vertical
# space than wxNotebook. note that this control is divided into two parts,
# MyTabCtrl and MyTabCtrl2, and both must be created.
class MyTabCtrl(wxWindow):
    def __init__(self, parent, id):
        style = 0
        if wx26:
            style |= wxFULL_REPAINT_ON_RESIZE

        wxWindow.__init__(self, parent, id, style = style)

        # pages, i.e., [wxWindow, name] lists. note that 'name' must be an
        # Unicode string.
        self.pages = []

        # index of selected page
        self.selected = -1

        # index of first visible tab
        self.firstTab = 0

        # how much padding to leave horizontally at the ends of the
        # control, and within each tab
        self.paddingX = 5

        # starting Y-pos of text in labels
        self.textY = 5

        # width of a single tab
        self.tabWidth = 150

        # width, height, spacing, y-pos of arrows
        self.arrowWidth = 8
        self.arrowHeight = 13
        self.arrowSpacing = 3
        self.arrowY = 5

        # initialized in OnPaint since we don't know our height yet
        self.font = None

        if wx26:
            self.SetMinSize(wxSize(self.paddingX * 2 + self.arrowWidth * 2 + \
                                   self.arrowSpacing + self.tabWidth, 20))

        EVT_LEFT_DOWN(self, self.OnLeftDown)
        EVT_LEFT_DCLICK(self, self.OnLeftDown)
        EVT_SIZE(self, self.OnSize)
        EVT_PAINT(self, self.OnPaint)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)

    # get the ctrl that the tabbed windows should use as a parent
    def getTabParent(self):
        return self.ctrl2

    # get page count
    def getPageCount(self):
        return len(self.pages)

    # get selected page index
    def getSelectedPageIndex(self):
        return self.selected

    # get given page
    def getPage(self, i):
        return self.pages[i][0]
    
    # MyTabCtrl2 uses this to register itself with us
    def add2(self, ctrl2):
        self.ctrl2 = ctrl2

    # add page
    def addPage(self, page, name):
        self.pages.append([page, name])

        # the new page must be given the correct size and position
        self.setPageSizes()
        page.MoveXY(0, 0)

        self.selectPage(len(self.pages) - 1)

    # set all page's sizes
    def setPageSizes(self):
        size = self.ctrl2.GetClientSize()

        for p in self.pages:
            p[0].SetClientSizeWH(size.width, size.height)

    # select given page
    def selectPage(self, page):
        self.selected = page
        
        for i in range(len(self.pages)):
            w = self.pages[i][0]

            if i == self.selected:
                w.Show()
            else:
                w.Hide()

        self.pageChangeFunc(self.selected)
        self.makeSelectedTabVisible()
        self.Refresh(False)

    # delete currently selected page
    def deletePage(self):
        self.pages[self.selected][0].Destroy()
        del self.pages[self.selected]

        self.selectPage(util.clamp(self.selected, 0, len(self.pages) - 1))

    # try to change the first visible tag by the given amount.
    def scroll(self, delta):
        newFirstTab = self.firstTab + delta

        if (newFirstTab >= 0) and (newFirstTab < len(self.pages)):
            self.firstTab = newFirstTab
            self.Refresh(False)

    # calculate the maximum number of tabs that we could show with our
    # current size.
    def calcMaxVisibleTabs(self):
        w = self.GetClientSizeTuple()[0]

        w -= self.paddingX * 2
        w -= self.arrowWidth * 2 + self.arrowSpacing

        # leave at least 2 pixels between left arrow and last tab
        w -= 2

        w //= self.tabWidth

        # if by some freak accident we're so small that the above results
        # in w being negative or positive but too small, guard against us
        # ever returning < 1.
        return max(1, w)

    # get last visible tab
    def getLastVisibleTab(self):
        return util.clamp(self.firstTab + self.calcMaxVisibleTabs() - 1,
                          maxVal = len(self.pages) - 1)
        
    # make sure selected tab is visible
    def makeSelectedTabVisible(self):
        maxTab = self.getLastVisibleTab()

        # if already visible, no need to do anything
        if (self.selected >= self.firstTab) and (self.selected <= maxTab):
            return

        # otherwise, position the selected tab as far right as possible
        self.firstTab = util.clamp(
            self.selected - self.calcMaxVisibleTabs() + 1,
            0)
        
    # set text for tab 'i' to 's'
    def setTabText(self, i, s):
        self.pages[i][1] = s
        self.Refresh(False)

    # set function to call when page changes. the function gets a single
    # integer argument, the index of the new page.
    def setPageChangedFunc(self, func):
        self.pageChangeFunc = func

    def OnLeftDown(self, event):
        x = event.GetPosition().x

        if x < self.paddingX:
            return

        w = self.GetClientSizeTuple()[0]
        
        # start of left arrow
        lx = w - 1 - self.paddingX - self.arrowWidth - self.arrowSpacing \
             - self.arrowWidth + 1

        if x < lx:
            page = self.firstTab + (x - self.paddingX) // self.tabWidth

            if page < len(self.pages):
                self.selectPage(page)
        else:
            if x < (lx + self.arrowWidth):
                self.scroll(-1)

            # start of right arrow
            rx = lx + self.arrowWidth + self.arrowSpacing

            if (x >= rx) and (x < (rx + self.arrowWidth)) and \
                   (self.getLastVisibleTab() < (len(self.pages) - 1)):
                self.scroll(1)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)

    def OnEraseBackground(self, event):
        pass

    def OnPaint(self, event):
        dc = wxBufferedPaintDC(self, self.screenBuf)

        # a kludge, but it works for now
        cfgGui = self.pages[0][0].ctrl.getCfgGui()
        
        w, h = self.GetClientSizeTuple()

        dc.SetBrush(cfgGui.workspaceBrush)
        dc.SetPen(cfgGui.workspacePen)
        dc.DrawRectangle(0, 0, w, h)

        dc.SetBrush(cfgGui.tabSelectedBgBrush)
        dc.SetTextForeground(cfgGui.tabFgColor)

        xpos = self.paddingX

        tabW = self.tabWidth
        tabH = h - 2
        tabY = h - tabH

        if not self.font:
            textH = h - self.textY - 1
            self.font = util.createPixelFont(textH, wxFONTFAMILY_DEFAULT,
                                             wxNORMAL, wxNORMAL)

        dc.SetFont(self.font)

        maxTab = self.getLastVisibleTab()
        
        for i in range(self.firstTab, maxTab + 1):
            p = self.pages[i]

            dc.DestroyClippingRegion()
            dc.SetClippingRegion(xpos, tabY, tabW, tabH)

            if i == self.selected:
                dc.SetPen(cfgGui.tabSelectedBgPen)
                dc.DrawRectangle(xpos + 1, tabY + 1, tabW - 2, tabH - 1)

            dc.SetPen(cfgGui.tabHighlightPen)
            util.drawLine(dc, xpos, tabY + 2, 0, tabH - 2)
            util.drawLine(dc, xpos + 2, tabY, tabW - 4, 0)
            dc.DrawPoint(xpos + 1, tabY + 1)

            dc.SetPen(cfgGui.tabFgPen)
            util.drawLine(dc, xpos + tabW - 1, tabY + 2, 0, tabH - 2)
            dc.DrawPoint(xpos + tabW - 2, tabY + 1)

            dc.DrawText(toGUIUnicode(p[1]), xpos + self.paddingX, self.textY)

            xpos += tabW

        # start of right arrow
        rx = w - 1 - self.paddingX - self.arrowWidth + 1

        if self.firstTab != 0:
            dc.DestroyClippingRegion()
            dc.SetPen(cfgGui.tabFgPen)

            util.drawLine(dc, rx - self.arrowSpacing - 1, self.arrowY,
                          0, self.arrowHeight)
            util.drawLine(dc, rx - self.arrowSpacing - 2, self.arrowY,
                          -self.arrowWidth + 1, self.arrowHeight // 2 + 1)
            util.drawLine(dc, rx - self.arrowSpacing - self.arrowWidth,
                          self.arrowY + self.arrowHeight // 2,
                          self.arrowWidth - 1, self.arrowHeight // 2 + 1)

        if maxTab < (len(self.pages) - 1):
            dc.DestroyClippingRegion()
            dc.SetPen(cfgGui.tabFgPen)

            util.drawLine(dc, rx, self.arrowY, 0, self.arrowHeight)
            util.drawLine(dc, rx + 1, self.arrowY, self.arrowWidth - 1,
                          self.arrowHeight // 2 + 1)
            util.drawLine(dc, rx + 1, self.arrowY + self.arrowHeight - 1,
                          self.arrowWidth - 1, -(self.arrowHeight // 2 + 1))

# second part of MyTabCtrl
class MyTabCtrl2(wxWindow):
    def __init__(self, parent, id, tabCtrl):
        wxWindow.__init__(self, parent, id)

        # MyTabCtrl
        self.tabCtrl = tabCtrl

        self.tabCtrl.add2(self)

        EVT_PAINT(self, self.OnPaint)
        EVT_SIZE(self, self.OnSize)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event):
        self.tabCtrl.setPageSizes()

    # we have an OnPaint handler that does nothing in a feeble attempt in
    # trying to make sure that in the cases when this does get called, as
    # little (useless) work as possible is done.
    def OnPaint(self, event):
        dc = wxPaintDC(self)

# dialog that shows two lists of script names, allowing user to choose one
# from both. stores indexes of selections in members named 'sel1' and
# 'sel2' when OK is pressed. 'items' must have at least two items.
class ScriptChooserDlg(wxDialog):
    def __init__(self, parent, items):
        wxDialog.__init__(self, parent, -1, "Choose scripts",
                          style = wxDEFAULT_DIALOG_STYLE)

        vsizer = wxBoxSizer(wxVERTICAL)

        gsizer = wxFlexGridSizer(2, 2, 5, 0)

        self.addCombo("first", "Compare script", self, gsizer, items, 0)
        self.addCombo("second", "to", self, gsizer, items, 1)

        vsizer.Add(gsizer)

        self.forceCb = wxCheckBox(self, -1, "Use same configuration")
        self.forceCb.SetValue(True)
        vsizer.Add(self.forceCb, 0, wxTOP, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add((1, 1), 1)
        
        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)
        
        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 10)

        util.finishWindow(self, vsizer)

        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def addCombo(self, name, descr, parent, sizer, items, sel):
        al = wxALIGN_CENTER_VERTICAL | wxRIGHT
        if sel == 1:
            al |= wxALIGN_RIGHT
            
        sizer.Add(wxStaticText(parent, -1, descr), 0, al, 10)
        
        combo = wxComboBox(parent, -1, style = wxCB_READONLY)
        util.setWH(combo, w = 200)
        
        for s in items:
            combo.Append(s)

        combo.SetSelection(sel)
        
        sizer.Add(combo)

        setattr(self, name + "Combo", combo)

    def OnOK(self, event):
        self.sel1 = self.firstCombo.GetSelection()
        self.sel2 = self.secondCombo.GetSelection()
        self.forceSameCfg = bool(self.forceCb.GetValue())
        
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

# CheckBoxDlg below handles lists of these
class CheckBoxItem:
    def __init__(self, text, selected = True, cdata = None):
        self.text = text
        self.selected = selected
        self.cdata = cdata

    # return dict which has keys for all selected items' client data.
    # takes a list of CheckBoxItem's as its parameter. note: this is a
    # static function.
    def getClientData(cbil):
        tmp = {}
        
        for i in range(len(cbil)):
            cbi = cbil[i]
            
            if cbi.selected:
                tmp[cbi.cdata] = None

        return tmp
    
    getClientData = staticmethod(getClientData)

# shows one or two (one if cbil2 = None) checklistbox widgets with
# contents from cbil1 and possibly cbil2, which are lists of
# CheckBoxItems. btns[12] are bools for whether or not to include helper
# buttons. if OK is pressed, the incoming lists' items' selection status
# will be modified.
class CheckBoxDlg(wxDialog):
    def __init__(self, parent, title, cbil1, descr1, btns1,
                 cbil2 = None, descr2 = None, btns2 = None):
        wxDialog.__init__(self, parent, -1, title,
                          style = wxDEFAULT_DIALOG_STYLE)

        vsizer = wxBoxSizer(wxVERTICAL)

        self.cbil1 = cbil1
        self.list1 = self.addList(descr1, self, vsizer, cbil1, btns1, True)
        
        if cbil2 != None:
            self.cbil2 = cbil2
            self.list2 = self.addList(descr2, self, vsizer, cbil2, btns2,
                                      False, 20)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add((1, 1), 1)
        
        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)
        
        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 10)

        util.finishWindow(self, vsizer)

        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()
        
    def addList(self, descr, parent, sizer, items, doBtns, isFirst, pad = 0):
        sizer.Add(wxStaticText(parent, -1, descr), 0, wxTOP, pad)

        if doBtns:
            hsizer = wxBoxSizer(wxHORIZONTAL)

            if isFirst:
                funcs = [ self.OnSet1, self.OnClear1, self.OnToggle1 ]
            else:
                funcs = [ self.OnSet2, self.OnClear2, self.OnToggle2 ]

            tmp = wxButton(parent, -1, "Set")
            hsizer.Add(tmp)
            EVT_BUTTON(self, tmp.GetId(), funcs[0])

            tmp = wxButton(parent, -1, "Clear")
            hsizer.Add(tmp, 0, wxLEFT, 10)
            EVT_BUTTON(self, tmp.GetId(), funcs[1])

            tmp = wxButton(parent, -1, "Toggle")
            hsizer.Add(tmp, 0, wxLEFT, 10)
            EVT_BUTTON(self, tmp.GetId(), funcs[2])

            sizer.Add(hsizer, 0, wxTOP | wxBOTTOM, 5)
        
        tmp = wxCheckListBox(parent, -1)

        longest = -1
        for i in range(len(items)):
            it = items[i]

            tmp.Append(it.text)
            tmp.Check(i, it.selected)

            if isFirst:
                if longest != -1:
                    if len(it.text) > len(items[longest].text):
                        longest = i
                else:
                    longest = 0

        w = -1
        if isFirst:
            h = len(items)
            if longest != -1:
                w = util.getTextExtent(tmp.GetFont(),
                                       "[x] " + items[longest].text)[0] + 15
        else:
            h = min(10, len(items))

        # don't know of a way to get the vertical spacing of items in a
        # wxCheckListBox, so estimate it at font height + 5 pixels, which
        # is close enough on everything I've tested.
        h *= util.getFontHeight(tmp.GetFont()) + 5
        h += 5
        h = max(25, h)
        
        util.setWH(tmp, w, h)
        sizer.Add(tmp, 0, wxEXPAND)

        return tmp

    def storeResults(self, cbil, ctrl):
        for i in range(len(cbil)):
            cbil[i].selected = bool(ctrl.IsChecked(i))

    def setAll(self, ctrl, state):
        for i in range(ctrl.GetCount()):
            ctrl.Check(i, state)
        
    def toggle(self, ctrl):
        for i in range(ctrl.GetCount()):
            ctrl.Check(i, not ctrl.IsChecked(i))

    def OnSet1(self, event):
        self.setAll(self.list1, True)
        
    def OnClear1(self, event):
        self.setAll(self.list1, False)
        
    def OnToggle1(self, event):
        self.toggle(self.list1)
        
    def OnSet2(self, event):
        self.setAll(self.list2, True)
        
    def OnClear2(self, event):
        self.setAll(self.list2, False)
        
    def OnToggle2(self, event):
        self.toggle(self.list2)

    def OnOK(self, event):
        self.storeResults(self.cbil1, self.list1)

        if hasattr(self, "list2"):
            self.storeResults(self.cbil2, self.list2)
        
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

# shows a multi-line string to the user in a scrollable text control.
class TextDlg(wxDialog):
    def __init__(self, parent, text, title):
        wxDialog.__init__(self, parent, -1, title,
                          style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)

        vsizer = wxBoxSizer(wxVERTICAL)

        tc = wxTextCtrl(self, -1, size = wxSize(400, 200),
            style = wxTE_MULTILINE | wxTE_READONLY | wxTE_LINEWRAP)
        tc.SetValue(text)
        vsizer.Add(tc, 1, wxEXPAND);
        
        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 5)
        
        okBtn = gutil.createStockButton(self, "OK")
        vsizer.Add(okBtn, 0, wxALIGN_CENTER)

        util.finishWindow(self, vsizer)

        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def OnOK(self, event):
        self.EndModal(wxID_OK)

# helper function for using TextDlg
def showText(parent, text, title = "Message"):
    dlg = TextDlg(parent, text, title)
    dlg.ShowModal()
    dlg.Destroy()

# ask user for a single-line text input.
class TextInputDlg(wxDialog):
    def __init__(self, parent, text, title, validateFunc = None):
        wxDialog.__init__(self, parent, -1, title,
                          style = wxDEFAULT_DIALOG_STYLE | wxWANTS_CHARS)

        # function to call to validate the input string on OK. can be
        # None, in which case it is not called. if it returns "", the
        # input is valid, otherwise the string it returns is displayed in
        # a message box and the dialog is not closed.
        self.validateFunc = validateFunc

        vsizer = wxBoxSizer(wxVERTICAL)

        vsizer.Add(wxStaticText(self, -1, text), 1, wxEXPAND | wxBOTTOM, 5)
        
        self.tc = wxTextCtrl(self, -1, style = wxTE_PROCESS_ENTER)
        vsizer.Add(self.tc, 1, wxEXPAND);
        
        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 5)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)
        
        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 5)

        util.finishWindow(self, vsizer)

        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        EVT_TEXT_ENTER(self, self.tc.GetId(), self.OnOK)

        EVT_CHAR(self.tc, self.OnCharEntry)
        EVT_CHAR(cancelBtn, self.OnCharButton)
        EVT_CHAR(okBtn, self.OnCharButton)

        self.tc.SetFocus()

    def OnCharEntry(self, event):
        self.OnChar(event, True)

    def OnCharButton(self, event):
        self.OnChar(event, False)

    def OnChar(self, event, isEntry):
        kc = event.GetKeyCode()

        if kc == WXK_ESCAPE:
            self.OnCancel()
            
        elif (kc == WXK_RETURN) and isEntry:
                self.OnOK()

        else:
            event.Skip()

    def OnOK(self, event = None):
        self.input = fromGUI(self.tc.GetValue())

        if self.validateFunc:
            msg = self.validateFunc(self.input)

            if msg:
                wxMessageBox(msg, "Error", wxOK, self)

                return
        
        self.EndModal(wxID_OK)

    def OnCancel(self, event = None):
        self.EndModal(wxID_CANCEL)

# asks the user for a keypress and stores it.
class KeyDlg(wxDialog):
    def __init__(self, parent, cmdName):
        wxDialog.__init__(self, parent, -1, "Key capture",
                          style = wxDEFAULT_DIALOG_STYLE)

        vsizer = wxBoxSizer(wxVERTICAL)

        vsizer.Add(wxStaticText(self, -1, "Press the key combination you\n"
            "want to bind to the command\n'%s'." % cmdName))

        tmp = KeyDlgWidget(self, -1, (1, 1))
        vsizer.Add(tmp)

        util.finishWindow(self, vsizer)

        tmp.SetFocus()

# used by KeyDlg
class KeyDlgWidget(wxWindow):
    def __init__(self, parent, id, size):
        wxWindow.__init__(self, parent, id, size = size,
                          style = wxWANTS_CHARS)

        EVT_CHAR(self, self.OnKeyChar)

    def OnKeyChar(self, ev):
        p = self.GetParent()
        p.key = util.Key.fromKE(ev)
        p.EndModal(wxID_OK)

# handles the "Most recently used" list of files in a menu.
class MRUFiles:
    def __init__(self, maxCount):
        # max number of items
        self.maxCount = maxCount

        # items (Unicode strings)
        self.items = []

        for i in range(self.maxCount):
            id = wxNewId()

            if i == 0:
                # first menu id
                self.firstId = id
            elif i == (self.maxCount - 1):
                # last menu id
                self.lastId = id

    # use given menu. this must be called before any "add" calls.
    def useMenu(self, menu, menuPos):
        # menu to use
        self.menu = menu

        # position in menu to add first item at
        self.menuPos = menuPos

        # if we already have items, add them to the menu (in reverse order
        # to maintain the correct ordering)
        tmp = self.items
        tmp.reverse()
        self.items = []

        for it in tmp:
            self.add(it)

    # return (firstMenuId, lastMenuId).
    def getIds(self):
        return (self.firstId, self.lastId)

    # add item.
    def add(self, s):
        # remove old menu items
        for i in range(self.getCount()):
            self.menu.Delete(self.firstId + i)

        # if item already exists, remove it
        try:
            i = self.items.index(s)
            del self.items[i]
        except ValueError:
            pass

        # add item to top of list
        self.items.insert(0, s)

        # prune overlong list
        if self.getCount() > self.maxCount:
            self.items = self.items[:self.maxCount]

        # add new menu items
        for i in range(self.getCount()):
            self.menu.Insert(self.menuPos + i, self.firstId + i,
                             "&%d %s" % (
                i + 1, toGUIUnicode(os.path.basename(self.get(i)))))

    # return number of items.
    def getCount(self):
        return len(self.items)

    # get item number 'i'.
    def get(self, i):
        return self.items[i]
