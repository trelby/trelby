import trelby.misc as misc
import trelby.util as util
import wx


class StringsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        # list of names. each name is both the name of a wx.TextCtrl in
        # this class and the name of a string configuration variable in
        # cfg.
        self.items = []

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(4, 2, 5, 0)

        self.addEntry("strContinuedPageEnd", "(CONTINUED)", self, gsizer)
        self.addEntry("strContinuedPageStart", "CONTINUED:", self, gsizer)
        self.addEntry("strMore", "(MORE)", self, gsizer)
        self.addEntry("strDialogueContinued", " (cont'd)", self, gsizer)

        gsizer.AddGrowableCol(1)
        vsizer.Add(gsizer, 0, wx.EXPAND)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center=False)

        for it in self.items:
            self.Bind(wx.EVT_TEXT, self.OnMisc, id=getattr(self, it).GetId())

    def addEntry(self, name, descr, parent, sizer):
        sizer.Add(
            wx.StaticText(parent, -1, descr), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )

        tmp = wx.TextCtrl(parent, -1)
        sizer.Add(tmp, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        setattr(self, name, tmp)
        self.items.append(name)

    def OnMisc(self, event=None):
        for it in self.items:
            setattr(self.cfg, it, misc.fromGUI(getattr(self, it).GetValue()))

    def cfg2gui(self):
        for it in self.items:
            getattr(self, it).SetValue(getattr(self.cfg, it))
