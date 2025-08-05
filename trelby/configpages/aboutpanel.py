import trelby.util as util
import wx


class AboutPanel(wx.Panel):
    def __init__(self, parent, id, cfg, text):
        wx.Panel.__init__(self, parent, id)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, text))

        util.finishWindow(self, vsizer, center=False)
