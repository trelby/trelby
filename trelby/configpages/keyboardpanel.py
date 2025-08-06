import trelby.misc as misc
import trelby.util as util
import wx


class KeyboardPanel(wx.Panel):
    def __init__(self, parent, id, cfg, cfgFrame=None):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg
        self.cfgFrame = cfgFrame

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, _("Commands:")))

        self.commandsLb = wx.ListBox(self, -1, size=(175, 50))

        for cmd in self.cfg.commands:
            self.commandsLb.Append(cmd.name, cmd)

        vsizer2.Add(self.commandsLb, 1)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.RIGHT, 15)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, _("Keys:")))

        self.keysLb = wx.ListBox(self, -1, size=(150, 60))
        vsizer2.Add(self.keysLb, 1, wx.BOTTOM, 10)

        btn = wx.Button(self, -1, _("Add"))
        self.Bind(wx.EVT_BUTTON, self.OnAdd, id=btn.GetId())
        vsizer2.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.addBtn = btn

        btn = wx.Button(self, -1, _("Delete"))
        self.Bind(wx.EVT_BUTTON, self.OnDelete, id=btn.GetId())
        vsizer2.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.deleteBtn = btn

        vsizer2.Add(wx.StaticText(self, -1, _("Description:")))

        self.descEntry = wx.TextCtrl(
            self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(150, 75)
        )
        vsizer2.Add(self.descEntry, 1, wx.EXPAND)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.BOTTOM, 10)

        vsizer.Add(hsizer)

        vsizer.Add(wx.StaticText(self, -1, _("Conflicting keys:")), 0, wx.TOP, 10)

        self.conflictsEntry = wx.TextCtrl(
            self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(50, 75)
        )
        vsizer.Add(self.conflictsEntry, 1, wx.EXPAND)

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_LISTBOX, self.OnCommandLb, id=self.commandsLb.GetId())
        self.commandsLb.SetSelection(0)
        self.OnCommandLb()

    def OnCommandLb(self, event=None):
        self.cmd = self.commandsLb.GetClientData(self.commandsLb.GetSelection())
        self.cfg2gui()

    def OnAdd(self, event):
        dlg = misc.KeyDlg(self.cfgFrame, self.cmd.name)

        key = None
        if dlg.ShowModal() == wx.ID_OK:
            key = dlg.key
        dlg.Destroy()

        if key:
            kint = key.toInt()
            if kint in self.cmd.keys:
                wx.MessageBox(
                    _("The key is already bound to this command."),
                    _("Error"),
                    wx.OK,
                    self.cfgFrame,
                )

                return

            if key.isValidInputChar():
                wx.MessageBox(
                    _("You can't bind input characters to commands."),
                    _("Error"),
                    wx.OK,
                    self.cfgFrame,
                )

                return

            self.cmd.keys.append(kint)
            self.cfg2gui()

    def OnDelete(self, event):
        sel = self.keysLb.GetSelection()
        if sel != -1:
            key = self.keysLb.GetClientData(sel)
            self.cfg.removeKey(self.cmd, key)
            self.cfg2gui()

    def cfg2gui(self):
        self.cfg.addShiftKeys()
        self.keysLb.Clear()

        for key in self.cmd.keys:
            k = util.Key.fromInt(key)
            self.keysLb.Append(k.toStr(), key)

        self.addBtn.Enable(not self.cmd.isFixed)
        self.deleteBtn.Enable(not self.cmd.isFixed)

        s = self.cmd.desc
        self.descEntry.SetValue(s)
        self.updateConflicts()

    def updateConflicts(self):
        s = self.cfg.getConflictingKeys()
        if s == None:
            s = "None"

        self.conflictsEntry.SetValue(s)
