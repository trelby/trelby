import os.path

import trelby.misc as misc
import trelby.util as util
import wx


class MiscPanel(wx.Panel):
    def __init__(self, parent, id, cfg, cfgFrame):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg
        self.cfgFrame = cfgFrame

        vsizer = wx.BoxSizer(wx.VERTICAL)

        bsizer = wx.StaticBoxSizer(
            wx.StaticBox(self, -1, _("Default script directory")), wx.VERTICAL
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.scriptDirEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.scriptDirEntry, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        btn = wx.Button(self, -1, _("Browse"))
        self.Bind(wx.EVT_BUTTON, self.OnBrowse, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        bsizer.Add(hsizer, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        vsizer.Add(bsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        bsizer = wx.StaticBoxSizer(
            wx.StaticBox(self, -1, _("PDF viewer application")), wx.VERTICAL
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, _("Path:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.progEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.progEntry, 1, wx.ALIGN_CENTER_VERTICAL)

        btn = wx.Button(self, -1, _("Browse"))
        self.Bind(wx.EVT_BUTTON, self.OnBrowsePDF, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        btn = wx.Button(self, -1, _("Guess"))
        self.Bind(wx.EVT_BUTTON, self.OnGuessPDF, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        bsizer.Add(hsizer, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, _("Arguments:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.argsEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.argsEntry, 1, wx.ALIGN_CENTER_VERTICAL)

        bsizer.Add(hsizer, 1, wx.EXPAND)

        vsizer.Add(bsizer, 1, wx.EXPAND)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 5
        if misc.isWindows:
            pad = 10

        self.checkListItems = [
            ("capitalize", _("Auto-capitalize sentences")),
            ("capitalizeI", _("Auto-capitalize i -> I")),
            ("honorSavedPos", _("When opening a script, start at last saved position")),
            ("recenterOnScroll", _("Recenter screen on scrolling")),
            ("overwriteSelectionOnInsert", _("Typing replaces selected text")),
            (
                "checkOnExport",
                _("Check script for errors before print, export or compare"),
            ),
        ]

        self.checkList = wx.CheckListBox(self, -1, size=(-1, 120))

        for it in self.checkListItems:
            self.checkList.Append(it[1])

        vsizer.Add(self.checkList, 0, wx.TOP | wx.BOTTOM, pad)

        self.Bind(wx.EVT_LISTBOX, self.OnMisc, id=self.checkList.GetId())
        self.Bind(wx.EVT_CHECKLISTBOX, self.OnMisc, id=self.checkList.GetId())

        self.addSpin(
            "splashTime",
            _("Show splash screen for X seconds:\n (0 = disable)"),
            self,
            vsizer,
            "splashTime",
        )

        self.addSpin(
            "paginate",
            _("Auto-paginate interval in seconds:\n (0 = disable)"),
            self,
            vsizer,
            "paginateInterval",
        )

        self.addSpin(
            "wheelScroll",
            _("Lines to scroll per mouse wheel event:"),
            self,
            vsizer,
            "mouseWheelLines",
        )

        self.cfg2gui()

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.scriptDirEntry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.progEntry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.argsEntry.GetId())

    def addSpin(self, name, descr, parent, sizer, cfgName):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(parent, -1, descr), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )

        tmp = wx.SpinCtrl(parent, -1)
        tmp.SetRange(*self.cfg.cvars.getMinMax(cfgName))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=tmp.GetId())
        tmp.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        hsizer.Add(tmp)

        sizer.Add(hsizer, 0, wx.BOTTOM, 10)

        setattr(self, name + _("Entry"), tmp)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnMisc(self, event=None):
        self.cfg.scriptDir = self.scriptDirEntry.GetValue().rstrip("/\\")
        self.cfg.pdfViewerPath = self.progEntry.GetValue()
        self.cfg.pdfViewerArgs = misc.fromGUI(self.argsEntry.GetValue())

        for i, it in enumerate(self.checkListItems):
            setattr(self.cfg, it[0], bool(self.checkList.IsChecked(i)))

        self.cfg.paginateInterval = util.getSpinValue(self.paginateEntry)
        self.cfg.mouseWheelLines = util.getSpinValue(self.wheelScrollEntry)
        self.cfg.splashTime = util.getSpinValue(self.splashTimeEntry)

    def OnBrowse(self, event):
        dlg = wx.DirDialog(
            self.cfgFrame, defaultPath=self.cfg.scriptDir, style=wx.DD_NEW_DIR_BUTTON
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.scriptDirEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def OnBrowsePDF(self, event):
        dlg = wx.FileDialog(
            self.cfgFrame,
            _("Choose program"),
            os.path.dirname(self.cfg.pdfViewerPath),
            self.cfg.pdfViewerPath,
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.progEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def OnGuessPDF(self, event):
        viewer, _ = util.getPDFViewer()

        if viewer:
            self.progEntry.SetValue(viewer)
        else:
            wx.MessageBox(
                _("Unable to guess. Please set the path manually."),
                _("PDF Viewer"),
                wx.OK,
                self.cfgFrame,
            )

    def cfg2gui(self):
        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.paginateEntry.SetValue(5)

        self.scriptDirEntry.SetValue(self.cfg.scriptDir)
        self.progEntry.SetValue(self.cfg.pdfViewerPath)
        self.argsEntry.SetValue(self.cfg.pdfViewerArgs)

        for i, it in enumerate(self.checkListItems):
            self.checkList.Check(i, getattr(self.cfg, it[0]))

        self.paginateEntry.SetValue(self.cfg.paginateInterval)
        self.wheelScrollEntry.SetValue(self.cfg.mouseWheelLines)
        self.splashTimeEntry.SetValue(self.cfg.splashTime)
