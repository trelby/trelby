import gutil
import misc
import util

import wx

class SCDictDlg(wx.Dialog):
    def __init__(self, parent, scDict, isGlobal):
        wx.Dialog.__init__(self, parent, -1, "Spell checker dictionary",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.scDict = scDict

        vsizer = wx.BoxSizer(wx.VERTICAL)

        if isGlobal:
            s = "Global words:"
        else:
            s = "Script-specific words:"

        vsizer.Add(wx.StaticText(self, -1, s))

        self.itemsEntry = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE |
                                     wx.TE_DONTWRAP, size = (300, 300))
        vsizer.Add(self.itemsEntry, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        self.cfg2gui()

        util.finishWindow(self, vsizer)

        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.itemsEntry.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

    def OnOK(self, event):
        self.scDict.refresh()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnMisc(self, event):
        self.scDict.set(misc.fromGUI(self.itemsEntry.GetValue()).split("\n"))

    def cfg2gui(self):
        self.itemsEntry.SetValue("\n".join(self.scDict.get()))
