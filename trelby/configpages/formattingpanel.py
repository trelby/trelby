import trelby.misc as misc
import trelby.util as util
import wx


class FormattingPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(
            wx.StaticText(
                self,
                -1,
                _(
                    "Leave at least this many lines at the end of a page when\nbreaking in the middle of an element:"
                ),
            ),
            0,
            wx.BOTTOM,
            5,
        )

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        self.addSpin("action", _("Action:"), self, gsizer, "pbActionLines")
        self.addSpin("dialogue", _("Dialogue"), self, gsizer, "pbDialogueLines")

        vsizer.Add(gsizer, 0, wx.LEFT, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.addSpin("fontSize", _("Font size:"), self, hsizer, "fontSize")
        vsizer.Add(hsizer, 0, wx.TOP, 20)

        vsizer.Add(wx.StaticText(self, -1, _("Scene CONTINUEDs:")), 0, wx.TOP, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sceneContinuedsCb = wx.CheckBox(self, -1, _("Include,"))
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.sceneContinuedsCb.GetId())
        hsizer.Add(self.sceneContinuedsCb, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        self.addSpin(
            "sceneContinuedIndent", _("indent:"), self, hsizer, "sceneContinuedIndent"
        )
        hsizer.Add(
            wx.StaticText(self, -1, _("characters")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
            10,
        )
        vsizer.Add(hsizer, 0, wx.LEFT, 5)

        self.scenesCb = wx.CheckBox(self, -1, _("Include scene numbers"))
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.scenesCb.GetId())
        vsizer.Add(self.scenesCb, 0, wx.TOP, 10)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.lineNumbersCb = wx.CheckBox(self, -1, _("Show line numbers (debug)"))
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.lineNumbersCb.GetId())
        vsizer.Add(self.lineNumbersCb, 0, wx.TOP, pad)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center=False)

    def addSpin(self, name, descr, parent, sizer, cfgName):
        sizer.Add(
            wx.StaticText(parent, -1, descr), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )

        entry = wx.SpinCtrl(parent, -1)
        entry.SetRange(*self.cfg.cvars.getMinMax(cfgName))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=entry.GetId())
        entry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        sizer.Add(entry, 0)

        setattr(self, name + "Entry", entry)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnMisc(self, event=None):
        self.cfg.pbActionLines = util.getSpinValue(self.actionEntry)
        self.cfg.pbDialogueLines = util.getSpinValue(self.dialogueEntry)
        self.cfg.sceneContinueds = self.sceneContinuedsCb.GetValue()
        self.cfg.sceneContinuedIndent = util.getSpinValue(
            self.sceneContinuedIndentEntry
        )
        self.cfg.fontSize = util.getSpinValue(self.fontSizeEntry)
        self.cfg.pdfShowSceneNumbers = self.scenesCb.GetValue()
        self.cfg.pdfShowLineNumbers = self.lineNumbersCb.GetValue()

    def cfg2gui(self):
        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.actionEntry.SetValue(5)
        self.dialogueEntry.SetValue(5)
        self.sceneContinuedIndentEntry.SetValue(5)

        self.actionEntry.SetValue(self.cfg.pbActionLines)
        self.dialogueEntry.SetValue(self.cfg.pbDialogueLines)
        self.sceneContinuedsCb.SetValue(self.cfg.sceneContinueds)
        self.sceneContinuedIndentEntry.SetValue(self.cfg.sceneContinuedIndent)
        self.fontSizeEntry.SetValue(self.cfg.fontSize)
        self.scenesCb.SetValue(self.cfg.pdfShowSceneNumbers)
        self.lineNumbersCb.SetValue(self.cfg.pdfShowLineNumbers)
