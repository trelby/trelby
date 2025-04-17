import wx

import trelby.config as config
import trelby.gutil as gutil
import trelby.util as util


class ImportDlg(wx.Dialog):
    def __init__(self, parent, indents, SCENE_ACTION, IGNORE):
        wx.Dialog.__init__(
            self, parent, -1, "Adjust styles", style=wx.DEFAULT_DIALOG_STYLE
        )

        indents.sort(key=lambda indent: indent.lines)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        tmp = wx.StaticText(self, -1, "Input:")
        vsizer.Add(tmp)

        self.inputLb = wx.ListBox(self, -1, size=(400, 200))
        for it in indents:
            self.inputLb.Append(
                "%d lines (indented %d characters)" % (len(it.lines), it.indent), it
            )

        vsizer.Add(self.inputLb, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Style:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.styleCombo = wx.ComboBox(self, -1, style=wx.CB_READONLY)

        self.styleCombo.Append("Scene / Action", SCENE_ACTION)
        for t in config.getTIs():
            self.styleCombo.Append(t.name, t.lt)

        self.styleCombo.Append("Ignore", IGNORE)

        util.setWH(self.styleCombo, w=150)

        hsizer.Add(self.styleCombo, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.TOP | wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "Lines:"))

        self.linesEntry = wx.TextCtrl(
            self, -1, size=(400, 200), style=wx.TE_MULTILINE | wx.TE_DONTWRAP
        )
        vsizer.Add(self.linesEntry, 0, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        self.Bind(wx.EVT_COMBOBOX, self.OnStyleCombo, id=self.styleCombo.GetId())
        self.Bind(wx.EVT_LISTBOX, self.OnInputLb, id=self.inputLb.GetId())

        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

        self.inputLb.SetSelection(0)
        self.OnInputLb()

    def OnOK(self, event):
        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnInputLb(self, event=None):
        self.selected = self.inputLb.GetClientData(self.inputLb.GetSelection())

        util.reverseComboSelect(self.styleCombo, self.selected.lt)
        self.linesEntry.SetValue("\n".join(self.selected.lines))

    def OnStyleCombo(self, event):
        self.selected.lt = self.styleCombo.GetClientData(self.styleCombo.GetSelection())
