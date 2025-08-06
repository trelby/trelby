import trelby.config as config
import trelby.misc as misc
import trelby.screenplay as screenplay
import trelby.util as util
import wx


class ElementsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, _("Element:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.elementsCombo = wx.ComboBox(self, -1, style=wx.CB_READONLY)

        for t in config.getTIs():
            self.elementsCombo.Append(t.name, t.lt)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.addTextStyles("Screen", "screen", self))
        hsizer.Add(self.addTextStyles("Print", "export", self), 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        gsizer.Add(
            wx.StaticText(self, -1, _("Empty lines / 10 before:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        tmp = wx.SpinCtrl(self, -1)
        tmp.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("beforeSpacing")
        )
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=tmp.GetId())
        tmp.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(tmp)
        self.beforeSpacingEntry = tmp

        gsizer.Add(
            wx.StaticText(self, -1, _("Empty lines / 10 between:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        tmp = wx.SpinCtrl(self, -1)
        tmp.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("intraSpacing")
        )
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=tmp.GetId())
        tmp.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(tmp)
        self.intraSpacingEntry = tmp

        vsizer.Add(gsizer, 0, wx.BOTTOM, 20)

        gsizer = wx.FlexGridSizer(2, 3, 5, 0)

        gsizer.Add(
            wx.StaticText(self, -1, _("Indent:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.indentEntry = wx.SpinCtrl(self, -1)
        self.indentEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("indent")
        )
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.indentEntry.GetId())
        self.indentEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(self.indentEntry, 0)

        gsizer.Add(
            wx.StaticText(self, -1, _("characters (10 characters = 1 inch)")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            10,
        )

        gsizer.Add(
            wx.StaticText(self, -1, _("Width:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.widthEntry = wx.SpinCtrl(self, -1)
        self.widthEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("width")
        )
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.widthEntry.GetId())
        self.widthEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(self.widthEntry, 0)

        gsizer.Add(
            wx.StaticText(self, -1, _("characters (10 characters = 1 inch)")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            10,
        )

        vsizer.Add(gsizer, 0, wx.BOTTOM, 20)

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_COMBOBOX, self.OnElementCombo, id=self.elementsCombo.GetId())

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTextStyles(self, name, prefix, parent):
        hsizer = wx.StaticBoxSizer(wx.StaticBox(parent, -1, name), wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(2, 2, 0, 10)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.addCheckBox(_("Caps"), prefix, parent, gsizer, pad)
        self.addCheckBox(_("Italic"), prefix, parent, gsizer, pad)
        self.addCheckBox(_("Bold"), prefix, parent, gsizer, pad)
        self.addCheckBox(_("Underlined"), prefix, parent, gsizer, pad)

        hsizer.Add(gsizer, 0, wx.EXPAND)

        return hsizer

    def addCheckBox(self, name, prefix, parent, sizer, pad):
        cb = wx.CheckBox(parent, -1, name)
        self.Bind(wx.EVT_CHECKBOX, self.OnStyleCb, id=cb.GetId())
        sizer.Add(cb, 0, wx.TOP, pad)
        setattr(self, prefix + name + "Cb", cb)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnElementCombo(self, event=None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.GetSelection())
        self.cfg2gui()

    def OnStyleCb(self, event):
        tcfg = self.cfg.types[self.lt]

        tcfg.screen.isCaps = self.screenCapsCb.GetValue()
        tcfg.screen.isItalic = self.screenItalicCb.GetValue()
        tcfg.screen.isBold = self.screenBoldCb.GetValue()
        tcfg.screen.isUnderlined = self.screenUnderlinedCb.GetValue()

        tcfg.export.isCaps = self.exportCapsCb.GetValue()
        tcfg.export.isItalic = self.exportItalicCb.GetValue()
        tcfg.export.isBold = self.exportBoldCb.GetValue()
        tcfg.export.isUnderlined = self.exportUnderlinedCb.GetValue()

    def OnMisc(self, event=None):
        tcfg = self.cfg.types[self.lt]

        tcfg.beforeSpacing = util.getSpinValue(self.beforeSpacingEntry)
        tcfg.intraSpacing = util.getSpinValue(self.intraSpacingEntry)
        tcfg.indent = util.getSpinValue(self.indentEntry)
        tcfg.width = util.getSpinValue(self.widthEntry)

    def cfg2gui(self):
        tcfg = self.cfg.types[self.lt]

        self.screenCapsCb.SetValue(tcfg.screen.isCaps)
        self.screenItalicCb.SetValue(tcfg.screen.isItalic)
        self.screenBoldCb.SetValue(tcfg.screen.isBold)
        self.screenUnderlinedCb.SetValue(tcfg.screen.isUnderlined)

        self.exportCapsCb.SetValue(tcfg.export.isCaps)
        self.exportItalicCb.SetValue(tcfg.export.isItalic)
        self.exportBoldCb.SetValue(tcfg.export.isBold)
        self.exportUnderlinedCb.SetValue(tcfg.export.isUnderlined)

        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.beforeSpacingEntry.SetValue(5)
        self.intraSpacingEntry.SetValue(5)
        self.indentEntry.SetValue(5)

        self.beforeSpacingEntry.SetValue(tcfg.beforeSpacing)
        self.intraSpacingEntry.SetValue(tcfg.intraSpacing)
        self.indentEntry.SetValue(tcfg.indent)
        self.widthEntry.SetValue(tcfg.width)
