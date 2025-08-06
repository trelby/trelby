import trelby.util as util
import wx


class PaperPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        self.blockEvents = 1

        self.paperSizes = {
            "A4": (210.0, 297.0),
            "Letter": (215.9, 279.4),
            "Custom": (1.0, 1.0),
        }

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(3, 2, 5, 5)

        gsizer.Add(
            wx.StaticText(self, -1, _("Type:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.paperCombo = wx.ComboBox(self, -1, style=wx.CB_READONLY)

        for k, v in list(self.paperSizes.items()):
            self.paperCombo.Append(k, v)

        gsizer.Add(self.paperCombo)

        gsizer.Add(wx.StaticText(self, -1, _("Width:")), 0, wx.ALIGN_CENTER_VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.widthEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.widthEntry)
        hsizer.Add(
            wx.StaticText(self, -1, "mm"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5
        )
        gsizer.Add(hsizer)

        gsizer.Add(wx.StaticText(self, -1, _("Height:")), 0, wx.ALIGN_CENTER_VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.heightEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.heightEntry)
        hsizer.Add(
            wx.StaticText(self, -1, "mm"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5
        )
        gsizer.Add(hsizer)

        vsizer.Add(gsizer, 0, wx.BOTTOM, 10)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, _("Margins")), wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(4, 5, 5, 5)

        self.addMarginCtrl(_("Top"), self, gsizer)
        self.addMarginCtrl(_("Bottom"), self, gsizer)
        self.addMarginCtrl(_("Left"), self, gsizer)
        self.addMarginCtrl(_("Right"), self, gsizer)

        bsizer.Add(gsizer, 0, wx.EXPAND | wx.ALL, 10)

        vsizer.Add(bsizer, 0, wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "(1 inch = 25.4 mm)"), 0, wx.LEFT, 25)

        self.linesLabel = wx.StaticText(self, -1, "")

        # wxwindows doesn't recalculate sizer size correctly at startup so
        # set initial text
        self.setLines()

        vsizer.Add(self.linesLabel, 0, wx.TOP, 20)

        util.finishWindow(self, vsizer, center=False)

        ptype = "Custom"
        for k, v in list(self.paperSizes.items()):
            if self.eqFloat(self.cfg.paperWidth, v[0]) and self.eqFloat(
                self.cfg.paperHeight, v[1]
            ):
                ptype = k

        idx = self.paperCombo.FindString(ptype)
        if idx != -1:
            self.paperCombo.SetSelection(idx)

        self.Bind(wx.EVT_COMBOBOX, self.OnPaperCombo, id=self.paperCombo.GetId())
        self.OnPaperCombo(None)

        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.widthEntry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.heightEntry.GetId())

        self.cfg2mm()
        self.cfg2inch()

        self.blockEvents -= 1

    def eqFloat(self, f1, f2):
        return round(f1, 2) == round(f2, 2)

    def addMarginCtrl(self, name, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, name + ":"), 0, wx.ALIGN_CENTER_VERTICAL)

        entry = wx.TextCtrl(parent, -1)
        sizer.Add(entry, 0)
        label = wx.StaticText(parent, -1, "mm")
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)

        entry2 = wx.TextCtrl(parent, -1)
        sizer.Add(entry2, 0, wx.LEFT, 20)
        label2 = wx.StaticText(parent, -1, "inch")
        sizer.Add(label2, 0, wx.ALIGN_CENTER_VERTICAL)

        setattr(self, name.lower() + "EntryMm", entry)
        setattr(self, name.lower() + "EntryInch", entry2)

        self.Bind(wx.EVT_TEXT, self.OnMarginMm, id=entry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMarginInch, id=entry2.GetId())

    def doForcedUpdate(self):
        self.setLines()

    def setLines(self):
        self.cfg.recalc(False)
        self.linesLabel.SetLabel(_("Lines per page: {}".format(self.cfg.linesOnPage)))

    def OnPaperCombo(self, event):
        w, h = self.paperCombo.GetClientData(self.paperCombo.GetSelection())

        ptype = self.paperCombo.GetStringSelection()

        if ptype == "Custom":
            self.widthEntry.Enable(True)
            self.heightEntry.Enable(True)
            w = self.cfg.paperWidth
            h = self.cfg.paperHeight
        else:
            self.widthEntry.Disable()
            self.heightEntry.Disable()

        self.widthEntry.SetValue(str(w))
        self.heightEntry.SetValue(str(h))

        self.setLines()

    def OnMisc(self, event):
        if self.blockEvents > 0:
            return

        self.entry2float(self.widthEntry, "paperWidth")
        self.entry2float(self.heightEntry, "paperHeight")

        self.setLines()

    def OnMarginMm(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1

        self.entry2float(self.topEntryMm, "marginTop")
        self.entry2float(self.bottomEntryMm, "marginBottom")
        self.entry2float(self.leftEntryMm, "marginLeft")
        self.entry2float(self.rightEntryMm, "marginRight")

        self.setLines()

        self.cfg2inch()

        self.blockEvents -= 1

    def OnMarginInch(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1

        self.entry2float(self.topEntryInch, "marginTop", 25.4)
        self.entry2float(self.bottomEntryInch, "marginBottom", 25.4)
        self.entry2float(self.leftEntryInch, "marginLeft", 25.4)
        self.entry2float(self.rightEntryInch, "marginRight", 25.4)

        self.setLines()

        self.cfg2mm()

        self.blockEvents -= 1

    def cfg2mm(self):
        self.topEntryMm.SetValue(str(self.cfg.marginTop))
        self.bottomEntryMm.SetValue(str(self.cfg.marginBottom))
        self.leftEntryMm.SetValue(str(self.cfg.marginLeft))
        self.rightEntryMm.SetValue(str(self.cfg.marginRight))

    def cfg2inch(self):
        self.topEntryInch.SetValue(str(self.cfg.marginTop / 25.4))
        self.bottomEntryInch.SetValue(str(self.cfg.marginBottom / 25.4))
        self.leftEntryInch.SetValue(str(self.cfg.marginLeft / 25.4))
        self.rightEntryInch.SetValue(str(self.cfg.marginRight / 25.4))

    def entry2float(self, entry, name, factor=1.0):
        val = util.str2float(entry.GetValue(), 0.0) * factor
        setattr(self.cfg, name, val)
