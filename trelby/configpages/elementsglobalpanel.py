import trelby.config as config
import trelby.util as util
import wx


class ElementsGlobalPanel(wx.Panel):
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

        gsizer = wx.FlexGridSizer(0, 2, 5, 0)

        self.addTypeCombo("newEnter", _("Enter creates"), self, gsizer)
        self.addTypeCombo("newTab", _("Tab creates"), self, gsizer)
        self.addTypeCombo("nextTab", _("Tab switches to"), self, gsizer)
        self.addTypeCombo("prevTab", _("Shift+Tab switches to"), self, gsizer)

        vsizer.Add(gsizer)

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_COMBOBOX, self.OnElementCombo, id=self.elementsCombo.GetId())

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTypeCombo(self, name, descr, parent, sizer):
        sizer.Add(
            wx.StaticText(parent, -1, descr + ":"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        combo = wx.ComboBox(parent, -1, style=wx.CB_READONLY)

        for t in config.getTIs():
            combo.Append(t.name, t.lt)

        sizer.Add(combo)

        self.Bind(wx.EVT_COMBOBOX, self.OnMisc, id=combo.GetId())

        setattr(self, name + _("Combo"), combo)

    def OnElementCombo(self, event=None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.GetSelection())
        self.cfg2gui()

    def OnMisc(self, event=None):
        tcfg = self.cfg.types[self.lt]

        tcfg.newTypeEnter = self.newEnterCombo.GetClientData(
            self.newEnterCombo.GetSelection()
        )
        tcfg.newTypeTab = self.newTabCombo.GetClientData(
            self.newTabCombo.GetSelection()
        )
        tcfg.nextTypeTab = self.nextTabCombo.GetClientData(
            self.nextTabCombo.GetSelection()
        )
        tcfg.prevTypeTab = self.prevTabCombo.GetClientData(
            self.prevTabCombo.GetSelection()
        )

    def cfg2gui(self):
        tcfg = self.cfg.types[self.lt]

        util.reverseComboSelect(self.newEnterCombo, tcfg.newTypeEnter)
        util.reverseComboSelect(self.newTabCombo, tcfg.newTypeTab)
        util.reverseComboSelect(self.nextTabCombo, tcfg.nextTypeTab)
        util.reverseComboSelect(self.prevTabCombo, tcfg.prevTypeTab)
