import gutil
import headers
import misc
import pdf
import pml
import util

import wx

class HeadersDlg(wx.Dialog):
    def __init__(self, parent, headers, cfg, cfgGl, applyFunc):
        wx.Dialog.__init__(self, parent, -1, "Headers",
                           style = wx.DEFAULT_DIALOG_STYLE)

        self.headers = headers
        self.cfg = cfg
        self.cfgGl = cfgGl
        self.applyFunc = applyFunc

        # whether some events are blocked
        self.block = False

        self.hdrIndex = -1
        if len(self.headers.hdrs) > 0:
            self.hdrIndex = 0

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Empty lines after headers:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)

        self.elinesEntry = wx.SpinCtrl(self, -1)
        self.elinesEntry.SetRange(0, 5)
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.elinesEntry.GetId())
        self.elinesEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        hsizer.Add(self.elinesEntry, 0, wx.LEFT, 10)

        vsizer.Add(hsizer)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM,
                   10)

        tmp = wx.StaticText(self, -1, "Strings:")
        vsizer.Add(tmp)

        self.stringsLb = wx.ListBox(self, -1, size = (200, 100))
        vsizer.Add(self.stringsLb, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.addBtn = gutil.createStockButton(self, "Add")
        hsizer.Add(self.addBtn)
        self.Bind(wx.EVT_BUTTON, self.OnAddString, id=self.addBtn.GetId())
        gutil.btnDblClick(self.addBtn, self.OnAddString)

        self.delBtn = gutil.createStockButton(self, "Delete")
        hsizer.Add(self.delBtn, 0, wx.LEFT, 10)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteString, id=self.delBtn.GetId())
        gutil.btnDblClick(self.delBtn, self.OnDeleteString)

        vsizer.Add(hsizer, 0, wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Text:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)

        self.textEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.textEntry, 1, wx.LEFT, 10)
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.textEntry.GetId())

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        vsizer.Add(wx.StaticText(self, -1,
            "'${PAGE}' will be replaced by the page number."), 0,
            wx.ALIGN_CENTER | wx.TOP, 5)

        hsizerTop = wx.BoxSizer(wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(3, 2, 5, 0)

        gsizer.Add(wx.StaticText(self, -1, "Header line:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)

        self.lineEntry = wx.SpinCtrl(self, -1)
        self.lineEntry.SetRange(1, 5)
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.lineEntry.GetId())
        self.lineEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(self.lineEntry)

        gsizer.Add(wx.StaticText(self, -1, "X offset (characters):"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.xoffEntry = wx.SpinCtrl(self, -1)
        self.xoffEntry.SetRange(-100, 100)
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.xoffEntry.GetId())
        self.xoffEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(self.xoffEntry)

        gsizer.Add(wx.StaticText(self, -1, "Alignment:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        self.alignCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for it in [ ("Left", util.ALIGN_LEFT), ("Center", util.ALIGN_CENTER),
                    ("Right", util.ALIGN_RIGHT) ]:
            self.alignCombo.Append(it[0], it[1])

        gsizer.Add(self.alignCombo)
        self.Bind(wx.EVT_COMBOBOX, self.OnMisc, id=self.alignCombo.GetId())

        hsizerTop.Add(gsizer)

        bsizer = wx.StaticBoxSizer(
            wx.StaticBox(self, -1, "Style"), wx.HORIZONTAL)

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

        hsizerTop.Add(bsizer, 0, wx.LEFT, 40)

        vsizer.Add(hsizerTop, 0, wx.TOP, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        previewBtn = gutil.createStockButton(self, "Preview")
        hsizer.Add(previewBtn)

        applyBtn = gutil.createStockButton(self, "Apply")
        hsizer.Add(applyBtn, 0, wx.LEFT, 10)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 20)

        util.finishWindow(self, vsizer)

        self.Bind(wx.EVT_BUTTON, self.OnPreview, id=previewBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnApply, id=applyBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

        self.Bind(wx.EVT_LISTBOX, self.OnStringsLb, id=self.stringsLb.GetId())

        # list of widgets that are specific to editing the selected string
        self.widList = [ self.textEntry, self.xoffEntry, self.alignCombo,
                         self.lineEntry, self.boldCb, self.italicCb,
                         self.underlinedCb ]

        self.updateGui()

        self.textEntry.SetFocus()

    def addCheckBox(self, name, parent, sizer, pad):
        cb = wx.CheckBox(parent, -1, name)
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=cb.GetId())
        sizer.Add(cb, 0, wx.TOP, pad)
        setattr(self, name.lower() + "Cb", cb)

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnApply(self, event):
        self.applyFunc(self.headers)

    def OnPreview(self, event):
        doc = pml.Document(self.cfg.paperWidth, self.cfg.paperHeight)

        pg = pml.Page(doc)
        self.headers.generatePML(pg, "42", self.cfg)

        fs = self.cfg.fontSize
        chY = util.getTextHeight(fs)

        y = self.cfg.marginTop + self.headers.getNrOfLines() * chY

        pg.add(pml.TextOp("Mindy runs away from the dinosaur, but trips on"
            " the power", self.cfg.marginLeft, y, fs))

        pg.add(pml.TextOp("cord. The raptor approaches her slowly.",
            self.cfg.marginLeft, y + chY, fs))

        doc.add(pg)

        tmp = pdf.generate(doc)
        gutil.showTempPDF(tmp, self.cfgGl, self)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnStringsLb(self, event = None):
        self.hdrIndex = self.stringsLb.GetSelection()
        self.updateHeaderGui()

    def OnAddString(self, event):
        h = headers.HeaderString()
        h.text = "new string"

        self.headers.hdrs.append(h)
        self.hdrIndex = len(self.headers.hdrs) - 1

        self.updateGui()

    def OnDeleteString(self, event):
        if self.hdrIndex == -1:
            return

        del self.headers.hdrs[self.hdrIndex]
        self.hdrIndex = min(self.hdrIndex, len(self.headers.hdrs) - 1)

        self.updateGui()

    # update listbox
    def updateGui(self):
        self.stringsLb.Clear()

        self.elinesEntry.SetValue(self.headers.emptyLinesAfter)

        self.delBtn.Enable(self.hdrIndex != -1)

        for h in self.headers.hdrs:
            self.stringsLb.Append(h.text)

        if self.hdrIndex != -1:
            self.stringsLb.SetSelection(self.hdrIndex)

        self.updateHeaderGui()

    # update selected header stuff
    def updateHeaderGui(self):
        if self.hdrIndex == -1:
            for w in self.widList:
                w.Disable()

            self.textEntry.SetValue("")
            self.lineEntry.SetValue(1)
            self.xoffEntry.SetValue(0)
            self.boldCb.SetValue(False)
            self.italicCb.SetValue(False)
            self.underlinedCb.SetValue(False)

            return

        self.block = True

        h = self.headers.hdrs[self.hdrIndex]

        for w in self.widList:
            w.Enable(True)

        self.textEntry.SetValue(h.text)
        self.xoffEntry.SetValue(h.xoff)

        util.reverseComboSelect(self.alignCombo, h.align)
        self.lineEntry.SetValue(h.line)

        self.boldCb.SetValue(h.isBold)
        self.italicCb.SetValue(h.isItalic)
        self.underlinedCb.SetValue(h.isUnderlined)

        self.block = False

    def OnMisc(self, event = None):
        self.headers.emptyLinesAfter = util.getSpinValue(self.elinesEntry)

        if (self.hdrIndex == -1) or self.block:
            return

        h = self.headers.hdrs[self.hdrIndex]

        h.text = util.toInputStr(misc.fromGUI(self.textEntry.GetValue()))
        self.stringsLb.SetString(self.hdrIndex, h.text)

        h.xoff = util.getSpinValue(self.xoffEntry)
        h.line = util.getSpinValue(self.lineEntry)
        h.align = self.alignCombo.GetClientData(self.alignCombo.GetSelection())

        h.isBold = self.boldCb.GetValue()
        h.isItalic = self.italicCb.GetValue()
        h.isUnderlined = self.underlinedCb.GetValue()
