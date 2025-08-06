import trelby.misc as misc
import trelby.util as util
import wx


class DisplayPanel(wx.Panel):
    def __init__(self, parent, id, cfg, cfgFrame=None):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg
        self.cfgFrame = cfgFrame

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, _("Screen fonts:")))

        self.fontsLb = wx.ListBox(self, -1, size=(300, 100))

        for it in ["fontNormal", "fontBold", "fontItalic", "fontBoldItalic"]:
            self.fontsLb.Append("", it)

        vsizer.Add(self.fontsLb, 0, wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        btn = wx.Button(self, -1, _("Change"))
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.OnChangeFont, id=self.fontsLb.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnChangeFont, id=btn.GetId())

        self.errText = wx.StaticText(self, -1, "")
        self.origColor = self.errText.GetForegroundColour()

        hsizer.Add(btn)
        hsizer.Add((20, -1))
        hsizer.Add(self.errText, 0, wx.ALIGN_CENTER_VERTICAL)
        vsizer.Add(hsizer, 0, wx.BOTTOM, 20)

        vsizer.Add(
            wx.StaticText(
                self, -1, _("The settings below apply only to 'Draft' view mode.")
            ),
            0,
            wx.BOTTOM,
            15,
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, _("Row spacing:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.spacingEntry = wx.SpinCtrl(self, -1)
        self.spacingEntry.SetRange(*self.cfg.cvars.getMinMax("fontYdelta"))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.spacingEntry.GetId())
        self.spacingEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        hsizer.Add(self.spacingEntry, 0)

        hsizer.Add(
            wx.StaticText(self, -1, _("pixels")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            10,
        )

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 15)

        self.pbRb = wx.RadioBox(
            self,
            -1,
            _("Page break lines to show"),
            style=wx.RA_SPECIFY_COLS,
            majorDimension=1,
            choices=[_("None"), _("Normal"), _("Normal + unadjusted   ")],
        )
        vsizer.Add(self.pbRb)

        self.fontsLb.SetSelection(0)
        self.updateFontLb()

        self.cfg2gui()

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_RADIOBOX, self.OnMisc, id=self.pbRb.GetId())

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wx.GTK gets stuck in
        # some weird state
        event.Skip()

    def OnChangeFont(self, event):
        fname = self.fontsLb.GetClientData(self.fontsLb.GetSelection())
        nfont = getattr(self.cfg, fname)

        fd = wx.FontData()
        nfi = wx.NativeFontInfo()
        nfi.FromString(nfont)
        font = wx.Font(nfi)
        fd.SetInitialFont(font)

        dlg = wx.FontDialog(self, fd)
        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()
            if util.isFixedWidth(font):
                setattr(self.cfg, fname, font.GetNativeFontInfo().ToString())

                self.cfg.fontYdelta = util.getFontHeight(font)

                self.cfg2gui()
                self.updateFontLb()
            else:
                wx.MessageBox(
                    _("The selected font is not fixed width and can not be used."),
                    _("Error"),
                    wx.OK,
                    self.cfgFrame,
                )

        dlg.Destroy()

    def OnMisc(self, event=None):
        self.cfg.fontYdelta = util.getSpinValue(self.spacingEntry)
        self.cfg.pbi = self.pbRb.GetSelection()

    def updateFontLb(self):
        names = ["Normal", "Bold", "Italic", "Bold-Italic"]

        # keep track if all fonts have the same width
        widths = set()

        for i in range(len(names)):
            nfi = wx.NativeFontInfo()
            nfi.FromString(getattr(self.cfg, self.fontsLb.GetClientData(i)))

            ps = nfi.GetPointSize()
            s = nfi.GetFaceName()

            row = "%s: %s, %d" % (names[i], s, ps)
            if misc.isMac:
                # Work around odd issue where wxOSX doesn't notice change in width
                self.fontsLb.Insert(row, i, self.fontsLb.GetClientData(i))
                self.fontsLb.Delete(i + 1)
            else:
                self.fontsLb.SetString(i, row)

            f = wx.Font(nfi)
            widths.add(util.getTextExtent(f, "iw")[0])

        if len(widths) > 1:
            self.errText.SetLabel(_("Fonts have different widths"))
            self.errText.SetForegroundColour((255, 0, 0))
        else:
            self.errText.SetLabel(_("Fonts have matching widths"))
            self.errText.SetForegroundColour(self.origColor)

    def cfg2gui(self):
        self.spacingEntry.SetValue(self.cfg.fontYdelta)
        self.pbRb.SetSelection(self.cfg.pbi)
