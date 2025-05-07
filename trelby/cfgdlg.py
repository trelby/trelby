import os.path

import wx

import trelby.gutil as gutil
import trelby.misc as misc
import trelby.truetype as truetype
import trelby.util as util

from trelby.configpages.globalaboutpanel import GlobalAboutPanel
from trelby.configpages.scriptaboutpanel import ScriptAboutPanel
from trelby.configpages.elementspanel import ElementsPanel
from trelby.configpages.elementsglobalpanel import ElementsGlobalPanel
from trelby.configpages.colorspanel import ColorsPanel
from trelby.configpages.paperpanel import PaperPanel
from trelby.configpages.formattingpanel import FormattingPanel
from trelby.configpages.stringspanel import StringsPanel
from trelby.configpages.pdfpanel import PDFPanel

# stupid hack to get correct window modality stacking for dialogs
cfgFrame = None


# WX2.6-FIXME: we can delete this when/if we switch to using wxListBook in
# wxWidgets 2.6
class MyListBook(wx.ListBox):
    def __init__(self, parent):
        wx.ListBox.__init__(self, parent, -1)

        self.Bind(wx.EVT_LISTBOX, self.OnPageChange, id=self.GetId())

    # get a list of all the pages
    def GetPages(self):
        ret = []

        for i in range(self.GetCount()):
            ret.append(self.GetClientData(i))

        return ret

    def AddPage(self, page, name):
        self.Append(name, page)

    # get (w,h) tuple that's big enough to cover all contained pages
    def GetContainingSize(self):
        w, h = 0, 0

        for page in self.GetPages():
            size = page.GetClientSize()
            w = max(w, size.width)
            h = max(h, size.height)

        return (w, h)

    # set all page sizes
    def SetPageSizes(self, w, h):
        for page in self.GetPages():
            page.SetClientSize(w, h)

    def OnPageChange(self, event=None):
        for page in self.GetPages():
            page.Hide()

        panel = self.GetClientData(self.GetSelection())

        # newer wxWidgets versions sometimes return None from the above
        # for some reason when the dialog is closed.
        if panel is None:
            return

        if hasattr(panel, "doForcedUpdate"):
            panel.doForcedUpdate()

        panel.Show()


class CfgDlg(wx.Dialog):
    def __init__(self, parent, cfg, applyFunc, isGlobal):
        wx.Dialog.__init__(
            self, parent, -1, "", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.cfg = cfg
        self.applyFunc = applyFunc

        global cfgFrame
        cfgFrame = self

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.listbook = MyListBook(self)
        w = util.getTextExtent(self.listbook.GetFont(), "Formatting")[0]
        util.setWH(self.listbook, w + 20, 200)

        hsizer.Add(self.listbook, 0, wx.EXPAND)

        self.panel = wx.Panel(self, -1)

        hsizer.Add(self.panel, 1, wx.EXPAND)

        if isGlobal:
            self.SetTitle("Settings dialog")

            self.AddPage(GlobalAboutPanel, "About")
            self.AddPage(ColorsPanel, "Colors")
            self.AddPage(DisplayPanel, "Display")
            self.AddPage(ElementsGlobalPanel, "Elements")
            self.AddPage(KeyboardPanel, "Keyboard")
            self.AddPage(MiscPanel, "Misc")
        else:
            self.SetTitle("Script settings dialog")

            self.AddPage(ScriptAboutPanel, "About")
            self.AddPage(ElementsPanel, "Elements")
            self.AddPage(FormattingPanel, "Formatting")
            self.AddPage(PaperPanel, "Paper")
            self.AddPage(PDFPanel, "PDF")
            self.AddPage(PDFFontsPanel, "PDF/Fonts")
            self.AddPage(StringsPanel, "Strings")

        size = self.listbook.GetContainingSize()

        hsizer.SetItemMinSize(self.panel, *size)
        self.listbook.SetPageSizes(*size)

        self.listbook.SetSelection(0)

        # it's unclear whether SetSelection sends an event on all
        # platforms or not, so force correct action.
        self.listbook.OnPageChange()

        vsizer.Add(hsizer, 1, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        applyBtn = gutil.createStockButton(self, "Apply")
        hsizer.Add(applyBtn, 0, wx.ALL, 5)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.ALL, 5)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.ALL, 5)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        self.SetSizerAndFit(vsizer)
        self.Layout()
        # self.Center()

        self.Bind(wx.EVT_BUTTON, self.OnApply, id=applyBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

    def AddPage(self, classObj, name):
        p = classObj(self.panel, -1, self.cfg)
        self.listbook.AddPage(p, name)

    # check for errors in each panel
    def checkForErrors(self):
        for panel in self.listbook.GetPages():
            if hasattr(panel, "checkForErrors"):
                panel.checkForErrors()

    def OnOK(self, event):
        self.checkForErrors()
        self.EndModal(wx.ID_OK)

    def OnApply(self, event):
        self.checkForErrors()
        self.applyFunc(self.cfg)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)


class DisplayPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Screen fonts:"))

        self.fontsLb = wx.ListBox(self, -1, size=(300, 100))

        for it in ["fontNormal", "fontBold", "fontItalic", "fontBoldItalic"]:
            self.fontsLb.Append("", it)

        vsizer.Add(self.fontsLb, 0, wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        btn = wx.Button(self, -1, "Change")
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.OnChangeFont, id=self.fontsLb.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnChangeFont, id=btn.GetId())

        self.errText = wx.StaticText(self, -1, "")
        self.origColor = self.errText.GetForegroundColour()

        hsizer.Add(btn)
        hsizer.Add((20, -1))
        hsizer.Add(self.errText, 0, wx.ALIGN_CENTER_VERTICAL)
        vsizer.Add(hsizer, 0, wx.BOTTOM, 20)

        vsizer.Add(
            wx.StaticText(
                self, -1, "The settings below apply only" " to 'Draft' view mode."
            ),
            0,
            wx.BOTTOM,
            15,
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, "Row spacing:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            10,
        )

        self.spacingEntry = wx.SpinCtrl(self, -1)
        self.spacingEntry.SetRange(*self.cfg.cvars.getMinMax("fontYdelta"))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.spacingEntry.GetId())
        self.spacingEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        hsizer.Add(self.spacingEntry, 0)

        hsizer.Add(
            wx.StaticText(self, -1, "pixels"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10
        )

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 15)

        self.pbRb = wx.RadioBox(
            self,
            -1,
            "Page break lines to show",
            style=wx.RA_SPECIFY_COLS,
            majorDimension=1,
            choices=["None", "Normal", "Normal + unadjusted   "],
        )
        vsizer.Add(self.pbRb)

        self.fontsLb.SetSelection(0)
        self.updateFontLb()

        self.cfg2gui()

        util.finishWindow(self, vsizer, center=False)

        self.Bind(wx.EVT_RADIOBOX, self.OnMisc, id=self.pbRb.GetId())

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wx.GTK gets stuck in
        # some weird state
        event.Skip()

    def OnChangeFont(self, event):
        fname = self.fontsLb.GetClientData(self.fontsLb.GetSelection())
        nfont = getattr(self.cfg, fname)

        fd = wx.FontData()
        nfi = wx.NativeFontInfo()
        nfi.FromString(nfont)
        font = wx.Font(nfi)
        fd.SetInitialFont(font)

        dlg = wx.FontDialog(self, fd)
        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()
            if util.isFixedWidth(font):
                setattr(self.cfg, fname, font.GetNativeFontInfo().ToString())

                self.cfg.fontYdelta = util.getFontHeight(font)

                self.cfg2gui()
                self.updateFontLb()
            else:
                wx.MessageBox(
                    "The selected font is not fixed width and" " can not be used.",
                    "Error",
                    wx.OK,
                    cfgFrame,
                )

        dlg.Destroy()

    def OnMisc(self, event=None):
        self.cfg.fontYdelta = util.getSpinValue(self.spacingEntry)
        self.cfg.pbi = self.pbRb.GetSelection()

    def updateFontLb(self):
        names = ["Normal", "Bold", "Italic", "Bold-Italic"]

        # keep track if all fonts have the same width
        widths = set()

        for i in range(len(names)):
            nfi = wx.NativeFontInfo()
            nfi.FromString(getattr(self.cfg, self.fontsLb.GetClientData(i)))

            ps = nfi.GetPointSize()
            s = nfi.GetFaceName()

            row = "%s: %s, %d" % (names[i], s, ps)
            if misc.isMac:
                # Work around odd issue where wxOSX doesn't notice change in width
                self.fontsLb.Insert(row, i, self.fontsLb.GetClientData(i))
                self.fontsLb.Delete(i + 1)
            else:
                self.fontsLb.SetString(i, row)

            f = wx.Font(nfi)
            widths.add(util.getTextExtent(f, "iw")[0])

        if len(widths) > 1:
            self.errText.SetLabel("Fonts have different widths")
            self.errText.SetForegroundColour((255, 0, 0))
        else:
            self.errText.SetLabel("Fonts have matching widths")
            self.errText.SetForegroundColour(self.origColor)

    def cfg2gui(self):
        self.spacingEntry.SetValue(self.cfg.fontYdelta)
        self.pbRb.SetSelection(self.cfg.pbi)


class KeyboardPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, "Commands:"))

        self.commandsLb = wx.ListBox(self, -1, size=(175, 50))

        for cmd in self.cfg.commands:
            self.commandsLb.Append(cmd.name, cmd)

        vsizer2.Add(self.commandsLb, 1)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.RIGHT, 15)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, "Keys:"))

        self.keysLb = wx.ListBox(self, -1, size=(150, 60))
        vsizer2.Add(self.keysLb, 1, wx.BOTTOM, 10)

        btn = wx.Button(self, -1, "Add")
        self.Bind(wx.EVT_BUTTON, self.OnAdd, id=btn.GetId())
        vsizer2.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.addBtn = btn

        btn = wx.Button(self, -1, "Delete")
        self.Bind(wx.EVT_BUTTON, self.OnDelete, id=btn.GetId())
        vsizer2.Add(btn, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        self.deleteBtn = btn

        vsizer2.Add(wx.StaticText(self, -1, "Description:"))

        self.descEntry = wx.TextCtrl(
            self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(150, 75)
        )
        vsizer2.Add(self.descEntry, 1, wx.EXPAND)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.BOTTOM, 10)

        vsizer.Add(hsizer)

        vsizer.Add(wx.StaticText(self, -1, "Conflicting keys:"), 0, wx.TOP, 10)

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
        dlg = misc.KeyDlg(cfgFrame, self.cmd.name)

        key = None
        if dlg.ShowModal() == wx.ID_OK:
            key = dlg.key
        dlg.Destroy()

        if key:
            kint = key.toInt()
            if kint in self.cmd.keys:
                wx.MessageBox(
                    "The key is already bound to this command.",
                    "Error",
                    wx.OK,
                    cfgFrame,
                )

                return

            if key.isValidInputChar():
                wx.MessageBox(
                    "You can't bind input characters to commands.",
                    "Error",
                    wx.OK,
                    cfgFrame,
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


class MiscPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        bsizer = wx.StaticBoxSizer(
            wx.StaticBox(self, -1, "Default script directory"), wx.VERTICAL
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.scriptDirEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.scriptDirEntry, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        btn = wx.Button(self, -1, "Browse")
        self.Bind(wx.EVT_BUTTON, self.OnBrowse, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        bsizer.Add(hsizer, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        vsizer.Add(bsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        bsizer = wx.StaticBoxSizer(
            wx.StaticBox(self, -1, "PDF viewer application"), wx.VERTICAL
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, "Path:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
        )

        self.progEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.progEntry, 1, wx.ALIGN_CENTER_VERTICAL)

        btn = wx.Button(self, -1, "Browse")
        self.Bind(wx.EVT_BUTTON, self.OnBrowsePDF, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        btn = wx.Button(self, -1, "Guess")
        self.Bind(wx.EVT_BUTTON, self.OnGuessPDF, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        bsizer.Add(hsizer, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, "Arguments:"),
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
            ("capitalize", "Auto-capitalize sentences"),
            ("capitalizeI", "Auto-capitalize i -> I"),
            ("honorSavedPos", "When opening a script, start at last saved position"),
            ("recenterOnScroll", "Recenter screen on scrolling"),
            ("overwriteSelectionOnInsert", "Typing replaces selected text"),
            (
                "checkOnExport",
                "Check script for errors before print, export or compare",
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
            "Show splash screen for X seconds:\n" " (0 = disable)",
            self,
            vsizer,
            "splashTime",
        )

        self.addSpin(
            "paginate",
            "Auto-paginate interval in seconds:\n" " (0 = disable)",
            self,
            vsizer,
            "paginateInterval",
        )

        self.addSpin(
            "wheelScroll",
            "Lines to scroll per mouse wheel event:",
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

        setattr(self, name + "Entry", tmp)

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
            cfgFrame, defaultPath=self.cfg.scriptDir, style=wx.DD_NEW_DIR_BUTTON
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.scriptDirEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def OnBrowsePDF(self, event):
        dlg = wx.FileDialog(
            cfgFrame,
            "Choose program",
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
                "Unable to guess. Please set the path manually.",
                "PDF Viewer",
                wx.OK,
                cfgFrame,
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


class PDFFontsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        self.blockEvents = True

        # last directory we chose a font from
        self.lastDir = ""

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(
            wx.StaticText(
                self,
                -1,
                "Leave all the fields empty to use the default PDF Courier\n"
                "fonts. This is highly recommended.\n"
                "\n"
                "Otherwise, fill in the the font filename to use\n"
                "the specified TrueType font. \n"
                "See the manual for the full details.\n",
            )
        )

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, "Type:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10
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

        self.addEntry("nameEntry", "Name:", self, gsizer)
        self.nameEntry.SetEditable(False)
        gsizer.Add((1, 1), 0)

        self.addEntry("fileEntry", "File:", self, gsizer)
        btn = wx.Button(self, -1, "Browse")
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
            cfgFrame,
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
        fontProgram = util.loadFile(filename, cfgFrame, 10 * 1024 * 1024, True)

        if fontProgram is None:
            return ""

        f = truetype.Font(fontProgram)

        if not f.isOK():
            wx.MessageBox(
                "File '%s'\n" "does not appear to be a valid TrueType font." % filename,
                "Error",
                wx.OK,
                cfgFrame,
            )

            return ""

        if not f.allowsEmbedding():
            wx.MessageBox(
                "Font '%s'\n"
                "does not allow embedding in its license terms.\n"
                "You may encounter problems using this font"
                " embedded." % filename,
                "Error",
                wx.OK,
                cfgFrame,
            )

        return f.getPostscriptName()

