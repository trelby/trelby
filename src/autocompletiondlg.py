import gutil
import misc
import util

import wx

class AutoCompletionDlg(wx.Dialog):
    def __init__(self, parent, autoCompletion):
        wx.Dialog.__init__(self, parent, -1, "Auto-completion",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.autoCompletion = autoCompletion

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Element:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.elementsCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for t in autoCompletion.types.values():
            self.elementsCombo.Append(t.ti.name, t.ti.lt)

        self.Bind(wx.EVT_COMBOBOX, self.OnElementCombo, id=self.elementsCombo.GetId())

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        self.enabledCb = wx.CheckBox(self, -1, "Auto-completion enabled")
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.enabledCb.GetId())
        vsizer.Add(self.enabledCb, 0, wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "Default items:"))

        self.itemsEntry = wx.TextCtrl(self, -1, style = wx.TE_MULTILINE |
                                      wx.TE_DONTWRAP, size = (400, 200))
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.itemsEntry.GetId())
        vsizer.Add(self.itemsEntry, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

    def OnOK(self, event):
        self.autoCompletion.refresh()
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnElementCombo(self, event = None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection())
        t = self.autoCompletion.getType(self.lt)

        self.enabledCb.SetValue(t.enabled)

        self.itemsEntry.Enable(t.enabled)
        self.itemsEntry.SetValue("\n".join(t.items))

    def OnMisc(self, event = None):
        t = self.autoCompletion.getType(self.lt)

        t.enabled = bool(self.enabledCb.IsChecked())
        self.itemsEntry.Enable(t.enabled)

        # this is cut&pasted from autocompletion.AutoCompletion.refresh,
        # but I don't want to call that since it does all types, this does
        # just the changed one.
        tmp = []
        for v in misc.fromGUI(self.itemsEntry.GetValue()).split("\n"):
            v = util.toInputStr(v).strip()

            if len(v) > 0:
                tmp.append(v)

        t.items = tmp
