import gutil
import misc
import pdf
import pml
import titles
import util

import copy

import wx

class TitlesDlg(wx.Dialog):
    def __init__(self, parent, titles, cfg, cfgGl):
        wx.Dialog.__init__(self, parent, -1, "Title pages",
                           style = wx.DEFAULT_DIALOG_STYLE)

        self.titles = titles
        self.cfg = cfg
        self.cfgGl = cfgGl

        # whether some events are blocked
        self.block = False

        self.setPage(0)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.pageLabel = wx.StaticText(self, -1, "")
        vsizer.Add(self.pageLabel, 0, wx.ADJUST_MINSIZE)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        tmp = wx.Button(self, -1, "Add")
        hsizer.Add(tmp)
        self.Bind(wx.EVT_BUTTON, self.OnAddPage, id=tmp.GetId())
        gutil.btnDblClick(tmp, self.OnAddPage)

        self.delPageBtn = wx.Button(self, -1, "Delete")
        hsizer.Add(self.delPageBtn, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_BUTTON, self.OnDeletePage, id=self.delPageBtn.GetId())
        gutil.btnDblClick(self.delPageBtn, self.OnDeletePage)

        self.moveBtn = wx.Button(self, -1, "Move")
        hsizer.Add(self.moveBtn, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_BUTTON, self.OnMovePage, id=self.moveBtn.GetId())
        gutil.btnDblClick(self.moveBtn, self.OnMovePage)

        self.nextBtn = wx.Button(self, -1, "Next")
        hsizer.Add(self.nextBtn, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_BUTTON, self.OnNextPage, id=self.nextBtn.GetId())
        gutil.btnDblClick(self.nextBtn, self.OnNextPage)

        vsizer.Add(hsizer, 0, wx.TOP, 5)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM,
                   10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        tmp = wx.StaticText(self, -1, "Strings:")
        vsizer2.Add(tmp)

        self.stringsLb = wx.ListBox(self, -1, size = (200, 150))
        vsizer2.Add(self.stringsLb)

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)

        self.addBtn = gutil.createStockButton(self, "Add")
        hsizer2.Add(self.addBtn)
        self.Bind(wx.EVT_BUTTON, self.OnAddString, id=self.addBtn.GetId())
        gutil.btnDblClick(self.addBtn, self.OnAddString)

        self.delBtn = gutil.createStockButton(self, "Delete")
        hsizer2.Add(self.delBtn, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteString, id=self.delBtn.GetId())
        gutil.btnDblClick(self.delBtn, self.OnDeleteString)

        vsizer2.Add(hsizer2, 0, wx.TOP, 5)

        hsizer.Add(vsizer2)

        self.previewCtrl = TitlesPreview(self, self, self.cfg)
        util.setWH(self.previewCtrl, 150, 150)
        hsizer.Add(self.previewCtrl, 1, wx.EXPAND | wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Text:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.textEntry = wx.TextCtrl(
            self, -1, style = wx.TE_MULTILINE | wx.TE_DONTWRAP, size = (200, 75))
        hsizer.Add(self.textEntry, 1, wx.LEFT, 10)
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.textEntry.GetId())

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        # TODO: should use FlexGridSizer, like headersdlg, to get neater
        # layout

        hsizerTop = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Alignment:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.alignCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for it in [ ("Left", util.ALIGN_LEFT), ("Center", util.ALIGN_CENTER),
                    ("Right", util.ALIGN_RIGHT) ]:
            self.alignCombo.Append(it[0], it[1])

        hsizer.Add(self.alignCombo, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_COMBOBOX, self.OnMisc, id=self.alignCombo.GetId())

        vsizer2.Add(hsizer, 0, wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "X / Y Pos (mm):"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.xEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.xEntry, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.xEntry.GetId())
        self.yEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.yEntry, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.yEntry.GetId())

        vsizer2.Add(hsizer, 0, wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Font / Size:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.fontCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for it in [ ("Courier", pml.COURIER), ("Helvetica", pml.HELVETICA),
                    ("Times-Roman", pml.TIMES_ROMAN) ]:
            self.fontCombo.Append(it[0], it[1])

        hsizer.Add(self.fontCombo, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_COMBOBOX, self.OnMisc, id=self.fontCombo.GetId())

        self.sizeEntry = wx.SpinCtrl(self, -1, size = (50, -1))
        self.sizeEntry.SetRange(4, 288)
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.sizeEntry.GetId())
        self.sizeEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        hsizer.Add(self.sizeEntry, 0, wx.LEFT, 10)

        vsizer2.Add(hsizer, 0, wx.TOP, 10)

        hsizerTop.Add(vsizer2)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Style"),
                                   wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.addCheckBox("Bold", self, vsizer2, pad)
        self.addCheckBox("Italic", self, vsizer2, pad)
        self.addCheckBox("Underlined", self, vsizer2, pad)

        bsizer.Add(vsizer2)

        hsizerTop.Add(bsizer, 0, wx.LEFT, 20)

        vsizer.Add(hsizerTop, 0, wx.TOP, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        self.previewBtn = gutil.createStockButton(self, "Preview")
        hsizer.Add(self.previewBtn)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        util.finishWindow(self, vsizer)

        self.Bind(wx.EVT_BUTTON, self.OnPreview, id=self.previewBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

        self.Bind(wx.EVT_LISTBOX, self.OnStringsLb, id=self.stringsLb.GetId())

        # list of widgets that are specific to editing the selected string
        self.widList = [ self.textEntry, self.xEntry, self.alignCombo,
                         self.yEntry, self.fontCombo, self.sizeEntry,
                         self.boldCb, self.italicCb, self.underlinedCb ]

        self.updateGui()

        self.textEntry.SetFocus()

    def addCheckBox(self, name, parent, sizer, pad):
        cb = wx.CheckBox(parent, -1, name)
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=cb.GetId())
        sizer.Add(cb, 0, wx.TOP, pad)
        setattr(self, name.lower() + "Cb", cb)

    def OnOK(self, event):
        self.titles.sort()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnPreview(self, event):
        doc = pml.Document(self.cfg.paperWidth, self.cfg.paperHeight)

        self.titles.generatePages(doc)
        tmp = pdf.generate(doc)
        gutil.showTempPDF(tmp, self.cfgGl, self)

    # set given page. 'page' can be an invalid value.
    def setPage(self, page):
        # selected page index or -1
        self.pageIndex = -1

        if self.titles.pages:
            self.pageIndex = 0

            if (page >= 0) and (len(self.titles.pages) > page):
                self.pageIndex = page

        # selected string index or -1
        self.tsIndex = -1

        if self.pageIndex == -1:
            return

        if len(self.titles.pages[self.pageIndex]) > 0:
            self.tsIndex = 0

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnStringsLb(self, event = None):
        self.tsIndex = self.stringsLb.GetSelection()
        self.updateStringGui()

    def OnAddPage(self, event):
        self.titles.pages.append([])
        self.setPage(len(self.titles.pages) - 1)

        self.updateGui()

    def OnDeletePage(self, event):
        del self.titles.pages[self.pageIndex]
        self.setPage(0)

        self.updateGui()

    def OnMovePage(self, event):
        newIndex = (self.pageIndex + 1) % len(self.titles.pages)

        self.titles.pages[self.pageIndex], self.titles.pages[newIndex] = (
            self.titles.pages[newIndex], self.titles.pages[self.pageIndex])

        self.setPage(newIndex)

        self.updateGui()

    def OnNextPage(self, event):
        self.setPage((self.pageIndex + 1) % len(self.titles.pages))

        self.updateGui()

    def OnAddString(self, event):
        if self.pageIndex == -1:
            return

        if self.tsIndex != -1:
            ts = copy.deepcopy(self.titles.pages[self.pageIndex][self.tsIndex])
            ts.y += util.getTextHeight(ts.size)
        else:
            ts = titles.TitleString(["new string"], 0.0, 100.0)

        self.titles.pages[self.pageIndex].append(ts)
        self.tsIndex = len(self.titles.pages[self.pageIndex]) - 1

        self.updateGui()

    def OnDeleteString(self, event):
        if (self.pageIndex == -1) or (self.tsIndex == -1):
            return

        del self.titles.pages[self.pageIndex][self.tsIndex]
        self.tsIndex = min(self.tsIndex,
                           len(self.titles.pages[self.pageIndex]) - 1)

        self.updateGui()

    # update page/string listboxes and selection
    def updateGui(self):
        self.stringsLb.Clear()

        pgCnt = len(self.titles.pages)

        self.delPageBtn.Enable(pgCnt > 0)
        self.moveBtn.Enable(pgCnt > 1)
        self.nextBtn.Enable(pgCnt > 1)
        self.previewBtn.Enable(pgCnt > 0)

        if self.pageIndex != -1:
            page = self.titles.pages[self.pageIndex]

            self.pageLabel.SetLabel("Page: %d / %d" % (self.pageIndex + 1,
                                                       pgCnt))
            self.addBtn.Enable(True)
            self.delBtn.Enable(len(page) > 0)

            for s in page:
                self.stringsLb.Append("--".join(s.items))

            if self.tsIndex != -1:
                self.stringsLb.SetSelection(self.tsIndex)
        else:
            self.pageLabel.SetLabel("No pages.")
            self.addBtn.Disable()
            self.delBtn.Disable()

        self.updateStringGui()

        self.previewCtrl.Refresh()

    # update selected string stuff
    def updateStringGui(self):
        if self.tsIndex == -1:
            for w in self.widList:
                w.Disable()

            self.textEntry.SetValue("")
            self.xEntry.SetValue("")
            self.yEntry.SetValue("")
            self.sizeEntry.SetValue(12)
            self.boldCb.SetValue(False)
            self.italicCb.SetValue(False)
            self.underlinedCb.SetValue(False)

            return

        self.block = True

        ts = self.titles.pages[self.pageIndex][self.tsIndex]

        for w in self.widList:
            w.Enable(True)

        if ts.isCentered:
            self.xEntry.Disable()

        self.textEntry.SetValue("\n".join(ts.items))

        self.xEntry.SetValue("%.2f" % ts.x)
        self.yEntry.SetValue("%.2f" % ts.y)

        util.reverseComboSelect(self.alignCombo, ts.getAlignment())

        util.reverseComboSelect(self.fontCombo, ts.font)
        self.sizeEntry.SetValue(ts.size)

        self.boldCb.SetValue(ts.isBold)
        self.italicCb.SetValue(ts.isItalic)
        self.underlinedCb.SetValue(ts.isUnderlined)

        self.block = False

        self.previewCtrl.Refresh()

    def OnMisc(self, event = None):
        if (self.tsIndex == -1) or self.block:
            return

        ts = self.titles.pages[self.pageIndex][self.tsIndex]

        ts.items = [util.toInputStr(s) for s in
                    misc.fromGUI(self.textEntry.GetValue()).split("\n")]

        self.stringsLb.SetString(self.tsIndex, "--".join(ts.items))

        ts.x = util.str2float(self.xEntry.GetValue(), 0.0)
        ts.y = util.str2float(self.yEntry.GetValue(), 0.0)

        ts.setAlignment(self.alignCombo.GetClientData(self.alignCombo.GetSelection()))
        self.xEntry.Enable(not ts.isCentered)

        ts.size = util.getSpinValue(self.sizeEntry)
        ts.font = self.fontCombo.GetClientData(self.fontCombo.GetSelection())

        ts.isBold = self.boldCb.GetValue()
        ts.isItalic = self.italicCb.GetValue()
        ts.isUnderlined = self.underlinedCb.GetValue()

        self.previewCtrl.Refresh()


class TitlesPreview(wx.Window):
    def __init__(self, parent, ctrl, cfg):
        wx.Window.__init__(self, parent, -1)

        self.cfg = cfg
        self.ctrl = ctrl

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wx.Bitmap(size.width, size.height)

    def OnEraseBackground(self, event):
        pass

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.screenBuf)

        # widget size
        ww, wh = self.GetClientSize()

        dc.SetBrush(wx.Brush(self.GetBackgroundColour()))
        dc.SetPen(wx.Pen(self.GetBackgroundColour()))
        dc.DrawRectangle(0, 0, ww, wh)

        # aspect ratio of paper
        aspect = self.cfg.paperWidth / self.cfg.paperHeight

        # calculate which way we can best fit the paper on screen
        h = wh
        w = int(aspect * wh)

        if w > ww:
            w = ww
            h = int(ww / aspect)

        # offset of paper
        ox = (ww - w) // 2
        oy = (wh - h) // 2

        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(ox, oy, w, h)

        if self.ctrl.pageIndex != -1:
            page = self.ctrl.titles.pages[self.ctrl.pageIndex]

            for i in range(len(page)):
                ts = page[i]

                # text height in mm
                textHinMM = util.getTextHeight(ts.size)

                textH = int((textHinMM / self.cfg.paperHeight) * h)
                textH = max(1, textH)
                y = ts.y

                for line in ts.items:
                    # people may have empty lines in between non-empty
                    # lines to achieve double spaced lines; don't draw a
                    # rectangle for lines consisting of nothing but
                    # whitespace

                    if line.strip():
                        textW = int((util.getTextWidth(line, ts.getStyle(),
                            ts.size) / self.cfg.paperWidth) * w)
                        textW = max(1, textW)

                        if ts.isCentered:
                            xp = w // 2 - textW // 2
                        else:
                            xp = int((ts.x / self.cfg.paperWidth) * w)

                        if ts.isRightJustified:
                            xp -= textW

                        if i == self.ctrl.tsIndex:
                            dc.SetPen(wx.RED_PEN)
                            dc.SetBrush(wx.RED_BRUSH)
                        else:
                            dc.SetPen(wx.BLACK_PEN)
                            dc.SetBrush(wx.BLACK_BRUSH)

                        yp = int((y / self.cfg.paperHeight) * h)

                        dc.DrawRectangle(ox + xp, oy + yp, textW, textH)

                    y += textHinMM

