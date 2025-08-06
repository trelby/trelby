import os.path

import trelby.misc as misc
import trelby.truetype as truetype
import trelby.util as util
import wx


class PDFFontsPanel(wx.Panel):
    def __init__(self, parent, id, cfg, cfgFrame):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg
        self.cfgFrame = cfgFrame

        self.blockEvents = True

        # last directory we chose a font from
        self.lastDir = ""

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(
            wx.StaticText(
                self,
                -1,
                _(
                    "Leave all the fields empty to use the default PDF Courier\nfonts. This is highly recommended.\n\nOtherwise, fill in the the font filename to use\nthe specified TrueType font. \nSee the manual for the full details.\n"
                ),
            )
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, _("Type:")),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.typeCombo = wx.ComboBox(self, -1, style=wx.CB_READONLY)

        for pfi in self.cfg.getPDFFontIds():
            pf = self.cfg.getPDFFont(pfi)
            self.typeCombo.Append(pf.name, pf)

        hsizer.Add(self.typeCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(2, 3, 5, 5)
        gsizer.AddGrowableCol(1)

        self.addEntry("nameEntry", _("Name:"), self, gsizer)
        self.nameEntry.SetEditable(False)
        gsizer.Add((1, 1), 0)

        self.addEntry("fileEntry", _("File:"), self, gsizer)
        btn = wx.Button(self, -1, _("Browse"))
        gsizer.Add(btn)

        self.Bind(wx.EVT_BUTTON, self.OnBrowse, id=btn.GetId())

        vsizer.Add(gsizer, 0, wx.EXPAND)

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_COMBOBOX, self.OnTypeCombo, id=self.typeCombo.GetId())

        self.typeCombo.SetSelection(0)
        self.OnTypeCombo()

        self.blockEvents = False

    # check that all embedded TrueType fonts are OK
    def checkForErrors(self):

        for pfi in self.cfg.getPDFFontIds():
            pf = self.cfg.getPDFFont(pfi)

            if pf.filename:
                self.getFontPostscriptName(pf.filename)

    def addEntry(self, name, descr, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, descr), 0, wx.ALIGN_CENTER_VERTICAL)

        entry = wx.TextCtrl(parent, -1)
        sizer.Add(entry, 1, wx.EXPAND)

        setattr(self, name, entry)

        self.Bind(wx.EVT_TEXT, self.OnMisc, id=entry.GetId())

    def OnMisc(self, event):
        if self.blockEvents:
            return

        self.pf.pdfName = misc.fromGUI(self.nameEntry.GetValue())
        self.pf.filename = self.fileEntry.GetValue()

    def OnBrowse(self, event):
        if self.pf.filename:
            dDir = os.path.dirname(self.pf.filename)
            dFile = os.path.basename(self.pf.filename)
        else:
            dDir = self.lastDir
            dFile = ""

        dlg = wx.FileDialog(
            self.cfgFrame,
            "Choose font file",
            defaultDir=dDir,
            defaultFile=dFile,
            wildcard="TrueType fonts (*.ttf;*.TTF)|*.ttf;*.TTF|All files|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.fileEntry.SetValue(dlg.GetPath())
            self.fileEntry.SetInsertionPointEnd()

            fname = dlg.GetPath()

            self.nameEntry.SetValue(self.getFontPostscriptName(fname))
            self.lastDir = os.path.dirname(fname)

        dlg.Destroy()

    def OnTypeCombo(self, event=None):
        self.blockEvents = True

        self.pf = self.typeCombo.GetClientData(self.typeCombo.GetSelection())
        self.cfg2gui()

        self.blockEvents = False

    def cfg2gui(self):
        self.nameEntry.SetValue(self.pf.pdfName)
        self.fileEntry.SetValue(self.pf.filename)
        self.fileEntry.SetInsertionPointEnd()

    # read TrueType font from given file and return its Postscript name,
    # or "" on errors.
    def getFontPostscriptName(self, filename):
        # we load at most 10 MB to avoid a denial-of-service attack by
        # passing around scripts containing references to fonts with
        # filenames like "/dev/zero" etc. no real font that I know of is
        # this big so it shouldn't hurt.
        fontProgram = util.loadFile(filename, self.cfgFrame, 10 * 1024 * 1024, True)

        if fontProgram is None:
            return ""

        f = truetype.Font(fontProgram)

        if not f.isOK():
            wx.MessageBox(
                _(
                    "File '{}'\ndoes not appear to be a valid TrueType font.".format(
                        filename
                    )
                ),
                _("Error"),
                wx.OK,
                self.cfgFrame,
            )

            return ""

        if not f.allowsEmbedding():
            wx.MessageBox(
                _(
                    "Font '{}'\ndoes not allow embedding in its license terms.\nYou may encounter problems using this font embedded.".format(
                        filename
                    )
                ),
                _("Error"),
                wx.OK,
                self.cfgFrame,
            )

        return f.getPostscriptName()
