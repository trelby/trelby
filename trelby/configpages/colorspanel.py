import functools

import trelby.misc as misc
import trelby.util as util
import wx


class ColorsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.colorsLb = wx.ListBox(self, -1, size=(300, 250))

        tmp = list(self.cfg.cvars.color.values())
        tmp = sorted(
            tmp, key=functools.cmp_to_key(lambda c1, c2: cmpfunc(c1.descr, c2.descr))
        )

        for it in tmp:
            self.colorsLb.Append(it.descr, it.name)

        hsizer.Add(self.colorsLb, 1)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        btn = wx.Button(self, -1, _("Change"))
        self.Bind(wx.EVT_BUTTON, self.OnChangeColor, id=btn.GetId())
        vsizer2.Add(btn, 0, wx.BOTTOM, 10)

        btn = wx.Button(self, -1, _("Restore default"))
        self.Bind(wx.EVT_BUTTON, self.OnDefaultColor, id=btn.GetId())
        vsizer2.Add(btn)

        hsizer.Add(vsizer2, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.colorSample = misc.MyColorSample(self, -1, size=wx.Size(200, 50))
        hsizer.Add(self.colorSample, 1, wx.EXPAND)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.useCustomElemColors = wx.CheckBox(
            self, -1, _("Use per-element-type colors")
        )
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.useCustomElemColors.GetId())
        vsizer.Add(self.useCustomElemColors)

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_LISTBOX, self.OnColorLb, id=self.colorsLb.GetId())
        self.colorsLb.SetSelection(0)
        self.OnColorLb()

    def OnColorLb(self, event=None):
        self.color = self.colorsLb.GetClientData(self.colorsLb.GetSelection())
        self.cfg2gui()

    def OnChangeColor(self, event):
        cd = wx.ColourData()
        cd.SetColour(getattr(self.cfg, self.color).toWx())
        dlg = wx.ColourDialog(self, cd)
        dlg.SetTitle(self.colorsLb.GetStringSelection())
        if dlg.ShowModal() == wx.ID_OK:
            setattr(
                self.cfg,
                self.color,
                util.MyColor.fromWx(dlg.GetColourData().GetColour()),
            )
        dlg.Destroy()

        self.cfg2gui()

    def OnDefaultColor(self, event):
        setattr(self.cfg, self.color, self.cfg.cvars.getDefault(self.color))
        self.cfg2gui()

    def OnMisc(self, event=None):
        self.cfg.useCustomElemColors = self.useCustomElemColors.GetValue()

    def cfg2gui(self):
        self.useCustomElemColors.SetValue(self.cfg.useCustomElemColors)

        self.colorSample.SetBackgroundColour(getattr(self.cfg, self.color).toWx())
        self.colorSample.Refresh()


def cmpfunc(a, b):
    return (a > b) - (a < b)
