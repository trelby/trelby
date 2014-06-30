# -*- coding: iso-8859-1 -*-

import gutil
import opts
import util

import os
import os.path
import sys

if "TRELBY_TESTING" in os.environ:
    import mock
    wx = mock.Mock()
else:
    import wx

TAB_BAR_HEIGHT = 24

version = "2.3-dev"

def init(doWX = True):
    global isWindows, isUnix, unicodeFS, doDblBuf, progPath, confPath, tmpPrefix

    # prefix used for temp files
    tmpPrefix = "trelby-tmp-"

    isWindows = False
    isUnix = False

    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        isUnix = True
    else:
        isWindows = True

    # does this platform support using Python's unicode strings in various
    # filesystem calls; if not, we need to convert filenames to UTF-8
    # before using them.
    unicodeFS = isWindows

    # wxGTK2 does not need us to do double buffering ourselves, others do
    doDblBuf = not isUnix

    # stupid hack to keep testcases working, since they don't initialize
    # opts (the doWX name is just for similarity with util)
    if not doWX or opts.isTest:
        progPath = u"."
        confPath = u".trelby"
    else:
        if isUnix:
            progPath = unicode(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "UTF-8")

            confPath = unicode(os.environ["HOME"], "UTF-8") + u"/.trelby"
        else:
            progPath = getPathFromRegistry()

            confPath = util.getWindowsUnicodeEnvVar(u"USERPROFILE") + ur"\Trelby\conf"

            if not os.path.exists(confPath):
                os.makedirs(confPath)

def getPathFromRegistry():
    registryPath = r"Software\Microsoft\Windows\CurrentVersion\App Paths\trelby.exe"

    try:
        import _winreg

        regPathKey = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, registryPath)
        regPathValue, regPathType = _winreg.QueryValueEx(regPathKey, "Path")

        if regPathType == _winreg.REG_SZ:
            return regPathValue
        else:
            raise TypeError

    except:
        wx.MessageBox("There was an error reading the following registry key: %s.\n"
                      "You may need to reinstall the program to fix this error." %
                      registryPath, "Error", wx.OK)
        sys.exit()

# convert s, which is returned from the wxWidgets GUI and is an Unicode
# string, to a normal string.
def fromGUI(s):
    return s.encode("ISO-8859-1", "ignore")

# convert s, which is an Unicode string, to an object suitable for passing
# to Python's file APIs. this is either the Unicode string itself, if the
# platform supports Unicode-based APIs (and Python has implemented support
# for it), or the Unicode string converted to UTF-8 on other platforms.
def toPath(s):
    if unicodeFS:
        return s
    else:
        return s.encode("UTF-8")

# return bitmap created from the given file. argument is as for
# getFullPath.
def getBitmap(filename):
    return wx.Bitmap(getFullPath(filename))

# return the absolute path of a file under the install dir. so passing in
# "resources/blaa.png" might return "/opt/trelby/resources/blaa.png" for
# example.
def getFullPath(relative):
    return progPath + "/" + relative

# TODO: move all GUI stuff to gutil

class MyColorSample(wx.Window):
    def __init__(self, parent, id, size):
        wx.Window.__init__(self, parent, id, size = size)

        wx.EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        w, h = self.GetClientSizeTuple()
        br = wx.Brush(self.GetBackgroundColour())
        dc.SetBrush(br)
        dc.DrawRectangle(0, 0, w, h)

# Custom "exit fullscreen" button for our tab bar. Used so that we have
# full control over the button's size.
class MyFSButton(wx.Window):
    def __init__(self, parent, id, getCfgGui):
        wx.Window.__init__(self, parent, id, size = (TAB_BAR_HEIGHT, TAB_BAR_HEIGHT))

        self.getCfgGui = getCfgGui
        self.fsImage = getBitmap("resources/fullscreen.png")

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_LEFT_DOWN(self, self.OnMouseDown)

    def OnPaint(self, event):
        cfgGui = self.getCfgGui()
        dc = wx.PaintDC(self)

        w, h = self.GetClientSizeTuple()

        dc.SetBrush(cfgGui.tabNonActiveBgBrush)
        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawRectangle(0, 0, w, h)

        off = (h - self.fsImage.GetHeight()) // 2
        dc.DrawBitmap(self.fsImage, off, off)

    def OnMouseDown(self, event):
        clickEvent = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.GetId())
        clickEvent.SetEventObject(self)
        self.GetEventHandler().ProcessEvent(clickEvent)

# custom status control
class MyStatus(wx.Window):
    WIDTH = 280
    X_ELEDIVIDER = 100

    def __init__(self, parent, id, getCfgGui):
        wx.Window.__init__(self, parent, id, size = (MyStatus.WIDTH, TAB_BAR_HEIGHT),
                           style = wx.FULL_REPAINT_ON_RESIZE)

        self.getCfgGui = getCfgGui

        self.page = 0
        self.pageCnt = 0
        self.elemType = ""
        self.tabNext = ""
        self.enterNext = ""

        self.elementFont = util.createPixelFont(
            TAB_BAR_HEIGHT // 2 + 6, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)

        self.font = util.createPixelFont(
            TAB_BAR_HEIGHT // 2 + 2, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)

        wx.EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, event):
        cfgGui = self.getCfgGui()

        cy = (TAB_BAR_HEIGHT - 1) // 2
        xoff = 5

        dc = wx.PaintDC(self)
        w, h = self.GetClientSizeTuple()

        dc.SetBrush(cfgGui.tabBarBgBrush)
        dc.SetPen(cfgGui.tabBarBgPen)
        dc.DrawRectangle(0, 0, w, h)

        dc.SetPen(cfgGui.tabTextPen)
        dc.SetTextForeground(cfgGui.tabTextColor)

        pageText = "Page %d / %d" % (self.page, self.pageCnt)
        dc.SetFont(self.font)

        util.drawText(dc, pageText, MyStatus.WIDTH - xoff, cy,
            util.ALIGN_RIGHT, util.VALIGN_CENTER)

        s1 = "%s [Enter]" % self.enterNext
        s2 = "%s [Tab]" % self.tabNext

        x = MyStatus.X_ELEDIVIDER + xoff
        dc.DrawText(s1, x, 0)
        dc.DrawText(s2, x, cy)

        x = xoff
        s = "%s" % self.elemType
        dc.SetFont(self.elementFont)
        util.drawText(dc, s, x, cy, valign = util.VALIGN_CENTER)

        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawLine(0, h-1, w, h-1)

        for x in (MyStatus.X_ELEDIVIDER, 0):
            dc.DrawLine(x, 0, x, h-1)

    def SetValues(self, page, pageCnt, elemType, tabNext, enterNext):
        self.page = page
        self.pageCnt = pageCnt
        self.elemType = elemType
        self.tabNext = tabNext
        self.enterNext = enterNext

        self.Refresh(False)


# our own version of a tab control, which exists for two reasons: it does
# not care where it is physically located, which allows us to combine it
# with other controls on a horizontal row, and it consumes less vertical
# space than wx.Notebook. note that this control is divided into two parts,
# MyTabCtrl and MyTabCtrl2, and both must be created.
class MyTabCtrl(wx.Window):
    def __init__(self, parent, id, getCfgGui):
        style = wx.FULL_REPAINT_ON_RESIZE
        wx.Window.__init__(self, parent, id, style = style)

        self.getCfgGui = getCfgGui

        # pages, i.e., [wx.Window, name] lists. note that 'name' must be an
        # Unicode string.
        self.pages = []

        # index of selected page
        self.selected = -1

        # index of first visible tab
        self.firstTab = 0

        # how much padding to leave horizontally at the ends of the
        # control, and within each tab
        self.paddingX = 10

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
        self.boldFont = None

        self.SetMinSize(wx.Size(
                self.paddingX * 2 + self.arrowWidth * 2 + self.arrowSpacing +\
                    self.tabWidth + 5,
                TAB_BAR_HEIGHT))

        wx.EVT_LEFT_DOWN(self, self.OnLeftDown)
        wx.EVT_LEFT_DCLICK(self, self.OnLeftDown)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)

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

    # delete given page
    def deletePage(self, i):
        self.pages[i][0].Destroy()
        del self.pages[i]

        self.selectPage(util.clamp(i, 0, len(self.pages) - 1))

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
            page, pageOffset = divmod(x - self.paddingX, self.tabWidth)
            page += self.firstTab

            if page < len(self.pages):
                hitX = pageOffset >= (self.tabWidth - self.paddingX * 2)

                if hitX:
                    panel = self.pages[page][0]
                    if not panel.ctrl.canBeClosed():
                        return

                    if self.getPageCount() > 1:
                        self.deletePage(page)
                    else:
                        panel.ctrl.createEmptySp()
                        panel.ctrl.updateScreen()
                else:
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
        self.screenBuf = wx.EmptyBitmap(size.width, size.height)

    def OnEraseBackground(self, event):
        pass

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.screenBuf)

        cfgGui = self.getCfgGui()

        w, h = self.GetClientSizeTuple()

        dc.SetBrush(cfgGui.tabBarBgBrush)
        dc.SetPen(cfgGui.tabBarBgPen)
        dc.DrawRectangle(0, 0, w, h)

        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawLine(0,h-1,w,h-1)

        xpos = self.paddingX

        tabW = self.tabWidth
        tabH = h - 2
        tabY = h - tabH

        if not self.font:
            textH = h - self.textY - 1
            self.font = util.createPixelFont(
                textH, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)
            self.boldFont = util.createPixelFont(
                textH, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD)

        maxTab = self.getLastVisibleTab()

        for i in range(self.firstTab, maxTab + 1):
            dc.SetFont(self.font)
            p = self.pages[i]

            dc.DestroyClippingRegion()
            dc.SetClippingRegion(xpos, tabY, tabW, tabH)
            dc.SetPen(cfgGui.tabBorderPen)

            if i == self.selected:
                points=((6,1),(tabW-8,1),(tabW-6,2),(tabW-2,tabH),(0,tabH),(4,2))
                dc.SetBrush(cfgGui.workspaceBrush)
            else:
                points=((5,2),(tabW-8,2),(tabW-6,3),(tabW-2,tabH-1),(0,tabH-1),(3,3))
                dc.SetBrush(cfgGui.tabNonActiveBgBrush)

            dc.DrawPolygon(points,xpos,tabY)

            # clip the text to fit within the tabs
            dc.DestroyClippingRegion()
            dc.SetClippingRegion(xpos, tabY, tabW - self.paddingX * 3, tabH)

            dc.SetPen(cfgGui.tabTextPen)
            dc.SetTextForeground(cfgGui.tabTextColor)
            dc.DrawText(p[1], xpos + self.paddingX, self.textY)

            dc.DestroyClippingRegion()
            dc.SetFont(self.boldFont)
            dc.DrawText("×", xpos + tabW - self.paddingX * 2, self.textY)

            xpos += tabW

        # start of right arrow
        rx = w - 1 - self.paddingX - self.arrowWidth + 1

        if self.firstTab != 0:
            dc.DestroyClippingRegion()
            dc.SetPen(cfgGui.tabTextPen)

            util.drawLine(dc, rx - self.arrowSpacing - 1, self.arrowY,
                          0, self.arrowHeight)
            util.drawLine(dc, rx - self.arrowSpacing - 2, self.arrowY,
                          -self.arrowWidth + 1, self.arrowHeight // 2 + 1)
            util.drawLine(dc, rx - self.arrowSpacing - self.arrowWidth,
                          self.arrowY + self.arrowHeight // 2,
                          self.arrowWidth - 1, self.arrowHeight // 2 + 1)

        if maxTab < (len(self.pages) - 1):
            dc.DestroyClippingRegion()
            dc.SetPen(cfgGui.tabTextPen)

            util.drawLine(dc, rx, self.arrowY, 0, self.arrowHeight)
            util.drawLine(dc, rx + 1, self.arrowY, self.arrowWidth - 1,
                          self.arrowHeight // 2 + 1)
            util.drawLine(dc, rx + 1, self.arrowY + self.arrowHeight - 1,
                          self.arrowWidth - 1, -(self.arrowHeight // 2 + 1))

# second part of MyTabCtrl
class MyTabCtrl2(wx.Window):
    def __init__(self, parent, id, tabCtrl):
        wx.Window.__init__(self, parent, id)

        # MyTabCtrl
        self.tabCtrl = tabCtrl

        self.tabCtrl.add2(self)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event):
        self.tabCtrl.setPageSizes()

    # we have an OnPaint handler that does nothing in a feeble attempt in
    # trying to make sure that in the cases when this does get called, as
    # little (useless) work as possible is done.
    def OnPaint(self, event):
        dc = wx.PaintDC(self)

# dialog that shows two lists of script names, allowing user to choose one
# from both. stores indexes of selections in members named 'sel1' and
# 'sel2' when OK is pressed. 'items' must have at least two items.
class ScriptChooserDlg(wx.Dialog):
    def __init__(self, parent, items):
        wx.Dialog.__init__(self, parent, -1, "Choose scripts",
                           style = wx.DEFAULT_DIALOG_STYLE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        self.addCombo("first", "Compare script", self, gsizer, items, 0)
        self.addCombo("second", "to", self, gsizer, items, 1)

        vsizer.Add(gsizer)

        self.forceCb = wx.CheckBox(self, -1, "Use same configuration")
        self.forceCb.SetValue(True)
        vsizer.Add(self.forceCb, 0, wx.TOP, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def addCombo(self, name, descr, parent, sizer, items, sel):
        al = wx.ALIGN_CENTER_VERTICAL | wx.RIGHT
        if sel == 1:
            al |= wx.ALIGN_RIGHT

        sizer.Add(wx.StaticText(parent, -1, descr), 0, al, 10)

        combo = wx.ComboBox(parent, -1, style = wx.CB_READONLY)
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

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

# CheckBoxDlg below handles lists of these
class CheckBoxItem:
    def __init__(self, text, selected = True, cdata = None):
        self.text = text
        self.selected = selected
        self.cdata = cdata

    # return dict which has keys for all selected items' client data.
    # takes a list of CheckBoxItem's as its parameter. note: this is a
    # static function.
    @staticmethod
    def getClientData(cbil):
        tmp = {}

        for i in range(len(cbil)):
            cbi = cbil[i]

            if cbi.selected:
                tmp[cbi.cdata] = None

        return tmp

# shows one or two (one if cbil2 = None) checklistbox widgets with
# contents from cbil1 and possibly cbil2, which are lists of
# CheckBoxItems. btns[12] are bools for whether or not to include helper
# buttons. if OK is pressed, the incoming lists' items' selection status
# will be modified.
class CheckBoxDlg(wx.Dialog):
    def __init__(self, parent, title, cbil1, descr1, btns1,
                 cbil2 = None, descr2 = None, btns2 = None):
        wx.Dialog.__init__(self, parent, -1, title,
                           style = wx.DEFAULT_DIALOG_STYLE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.cbil1 = cbil1
        self.list1 = self.addList(descr1, self, vsizer, cbil1, btns1, True)

        if cbil2 != None:
            self.cbil2 = cbil2
            self.list2 = self.addList(descr2, self, vsizer, cbil2, btns2,
                                      False, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def addList(self, descr, parent, sizer, items, doBtns, isFirst, pad = 0):
        sizer.Add(wx.StaticText(parent, -1, descr), 0, wx.TOP, pad)

        if doBtns:
            hsizer = wx.BoxSizer(wx.HORIZONTAL)

            if isFirst:
                funcs = [ self.OnSet1, self.OnClear1, self.OnToggle1 ]
            else:
                funcs = [ self.OnSet2, self.OnClear2, self.OnToggle2 ]

            tmp = wx.Button(parent, -1, "Set")
            hsizer.Add(tmp)
            wx.EVT_BUTTON(self, tmp.GetId(), funcs[0])

            tmp = wx.Button(parent, -1, "Clear")
            hsizer.Add(tmp, 0, wx.LEFT, 10)
            wx.EVT_BUTTON(self, tmp.GetId(), funcs[1])

            tmp = wx.Button(parent, -1, "Toggle")
            hsizer.Add(tmp, 0, wx.LEFT, 10)
            wx.EVT_BUTTON(self, tmp.GetId(), funcs[2])

            sizer.Add(hsizer, 0, wx.TOP | wx.BOTTOM, 5)

        tmp = wx.CheckListBox(parent, -1)

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
        # wx.CheckListBox, so estimate it at font height + 5 pixels, which
        # is close enough on everything I've tested.
        h *= util.getFontHeight(tmp.GetFont()) + 5
        h += 5
        h = max(25, h)

        util.setWH(tmp, w, h)
        sizer.Add(tmp, 0, wx.EXPAND)

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

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

# shows a multi-line string to the user in a scrollable text control.
class TextDlg(wx.Dialog):
    def __init__(self, parent, text, title):
        wx.Dialog.__init__(self, parent, -1, title,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        tc = wx.TextCtrl(self, -1, size = wx.Size(400, 200),
                         style = wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_LINEWRAP)
        tc.SetValue(text)
        vsizer.Add(tc, 1, wx.EXPAND);

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        okBtn = gutil.createStockButton(self, "OK")
        vsizer.Add(okBtn, 0, wx.ALIGN_CENTER)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        okBtn.SetFocus()

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)

# helper function for using TextDlg
def showText(parent, text, title = "Message"):
    dlg = TextDlg(parent, text, title)
    dlg.ShowModal()
    dlg.Destroy()

# ask user for a single-line text input.
class TextInputDlg(wx.Dialog):
    def __init__(self, parent, text, title, validateFunc = None):
        wx.Dialog.__init__(self, parent, -1, title,
                           style = wx.DEFAULT_DIALOG_STYLE | wx.WANTS_CHARS)

        # function to call to validate the input string on OK. can be
        # None, in which case it is not called. if it returns "", the
        # input is valid, otherwise the string it returns is displayed in
        # a message box and the dialog is not closed.
        self.validateFunc = validateFunc

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, text), 1, wx.EXPAND | wx.BOTTOM, 5)

        self.tc = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        vsizer.Add(self.tc, 1, wx.EXPAND);

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 5)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        wx.EVT_TEXT_ENTER(self, self.tc.GetId(), self.OnOK)

        wx.EVT_CHAR(self.tc, self.OnCharEntry)
        wx.EVT_CHAR(cancelBtn, self.OnCharButton)
        wx.EVT_CHAR(okBtn, self.OnCharButton)

        self.tc.SetFocus()

    def OnCharEntry(self, event):
        self.OnChar(event, True)

    def OnCharButton(self, event):
        self.OnChar(event, False)

    def OnChar(self, event, isEntry):
        kc = event.GetKeyCode()

        if kc == wx.WXK_ESCAPE:
            self.OnCancel()

        elif (kc == wx.WXK_RETURN) and isEntry:
                self.OnOK()

        else:
            event.Skip()

    def OnOK(self, event = None):
        self.input = fromGUI(self.tc.GetValue())

        if self.validateFunc:
            msg = self.validateFunc(self.input)

            if msg:
                wx.MessageBox(msg, "Error", wx.OK, self)

                return

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event = None):
        self.EndModal(wx.ID_CANCEL)

# asks the user for a keypress and stores it.
class KeyDlg(wx.Dialog):
    def __init__(self, parent, cmdName):
        wx.Dialog.__init__(self, parent, -1, "Key capture",
                           style = wx.DEFAULT_DIALOG_STYLE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Press the key combination you\n"
            "want to bind to the command\n'%s'." % cmdName))

        tmp = KeyDlgWidget(self, -1, (1, 1))
        vsizer.Add(tmp)

        util.finishWindow(self, vsizer)

        tmp.SetFocus()

# used by KeyDlg
class KeyDlgWidget(wx.Window):
    def __init__(self, parent, id, size):
        wx.Window.__init__(self, parent, id, size = size,
                           style = wx.WANTS_CHARS)

        wx.EVT_CHAR(self, self.OnKeyChar)

    def OnKeyChar(self, ev):
        p = self.GetParent()
        p.key = util.Key.fromKE(ev)
        p.EndModal(wx.ID_OK)

# handles the "Most recently used" list of files in a menu.
class MRUFiles:
    def __init__(self, maxCount):
        # max number of items
        self.maxCount = maxCount

        # items (Unicode strings)
        self.items = []

        for i in range(self.maxCount):
            id = wx.NewId()

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
                i + 1, os.path.basename(self.get(i))))

    # return number of items.
    def getCount(self):
        return len(self.items)

    # get item number 'i'.
    def get(self, i):
        return self.items[i]
