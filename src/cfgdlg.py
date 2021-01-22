import config
import gutil
import misc
import screenplay
import truetype
import util
import functools

import os.path

import wx

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

    def OnPageChange(self, event = None):
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
        wx.Dialog.__init__(self, parent, -1, "",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
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
        self.Center()

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

class AboutPanel(wx.Panel):
    def __init__(self, parent, id, cfg, text):
        wx.Panel.__init__(self, parent, id)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, text))

        util.finishWindow(self, vsizer, center = False)

class GlobalAboutPanel(AboutPanel):
    def __init__(self, parent, id, cfg):
        s = \
"""This is the config dialog for global settings, which means things
that affect the user interface of the program like interface colors,
keyboard shortcuts, display fonts, and so on.

The settings here are independent of any script being worked on,
and unique to this computer.

None of the settings here have any effect on the generated PDF
output for a script. See Script/Settings for those."""

        AboutPanel.__init__(self, parent, id, cfg, s)

class ScriptAboutPanel(AboutPanel):
    def __init__(self, parent, id, cfg):
        s = \
"""This is the config dialog for script format settings, which means
things that affect the generated PDF output of a script. Things like
paper size, indendation/line widths/font styles for the different
element types, and so on.

The settings here are saved within the screenplay itself.

If you're looking for the user interface settings (colors, keyboard
shortcuts, etc.), those are found in File/Settings."""

        AboutPanel.__init__(self, parent, id, cfg, s)

class DisplayPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Screen fonts:"))

        self.fontsLb = wx.ListBox(self, -1, size = (300, 100))

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

        vsizer.Add(wx.StaticText(self, -1, "The settings below apply only"
                                " to 'Draft' view mode."), 0, wx.BOTTOM, 15)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Row spacing:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.spacingEntry = wx.SpinCtrl(self, -1)
        self.spacingEntry.SetRange(*self.cfg.cvars.getMinMax("fontYdelta"))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.spacingEntry.GetId())
        self.spacingEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        hsizer.Add(self.spacingEntry, 0)

        hsizer.Add(wx.StaticText(self, -1, "pixels"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 15)

        self.pbRb = wx.RadioBox(self, -1, "Page break lines to show",
            style = wx.RA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "None", "Normal", "Normal + unadjusted   " ])
        vsizer.Add(self.pbRb)

        self.fontsLb.SetSelection(0)
        self.updateFontLb()

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

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
                wx.MessageBox("The selected font is not fixed width and"
                              " can not be used.", "Error", wx.OK, cfgFrame)

        dlg.Destroy()

    def OnMisc(self, event = None):
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

            self.fontsLb.SetString(i, "%s: %s, %d" % (names[i], s, ps))

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

class ElementsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Element:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.elementsCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for t in config.getTIs():
            self.elementsCombo.Append(t.name, t.lt)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(self.addTextStyles("Screen", "screen", self))
        hsizer.Add(self.addTextStyles("Print", "export", self), 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        gsizer.Add(wx.StaticText(self, -1, "Empty lines / 10 before:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        tmp = wx.SpinCtrl(self, -1)
        tmp.SetRange(*self.cfg.getType(screenplay.ACTION).cvars.getMinMax(
            "beforeSpacing"))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=tmp.GetId())
        tmp.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(tmp)
        self.beforeSpacingEntry = tmp

        gsizer.Add(wx.StaticText(self, -1, "Empty lines / 10 between:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        tmp = wx.SpinCtrl(self, -1)
        tmp.SetRange(*self.cfg.getType(screenplay.ACTION).cvars.getMinMax(
            "intraSpacing"))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=tmp.GetId())
        tmp.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(tmp)
        self.intraSpacingEntry = tmp

        vsizer.Add(gsizer, 0, wx.BOTTOM, 20)

        gsizer = wx.FlexGridSizer(2, 3, 5, 0)

        gsizer.Add(wx.StaticText(self, -1, "Indent:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.indentEntry = wx.SpinCtrl(self, -1)
        self.indentEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("indent"))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.indentEntry.GetId())
        self.indentEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(self.indentEntry, 0)

        gsizer.Add(wx.StaticText(self, -1, "characters (10 characters"
            " = 1 inch)"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        gsizer.Add(wx.StaticText(self, -1, "Width:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.widthEntry = wx.SpinCtrl(self, -1)
        self.widthEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("width"))
        self.Bind(wx.EVT_SPINCTRL, self.OnMisc, id=self.widthEntry.GetId())
        self.widthEntry.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        gsizer.Add(self.widthEntry, 0)

        gsizer.Add(wx.StaticText(self, -1, "characters (10 characters"
            " = 1 inch)"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        vsizer.Add(gsizer, 0, wx.BOTTOM, 20)

        util.finishWindow(self, vsizer, center = False)

        self.Bind(wx.EVT_COMBOBOX, self.OnElementCombo, id=self.elementsCombo.GetId())

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTextStyles(self, name, prefix, parent):
        hsizer = wx.StaticBoxSizer(wx.StaticBox(parent, -1, name),
                                   wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(2, 2, 0, 10)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5

        self.addCheckBox("Caps", prefix, parent, gsizer, pad)
        self.addCheckBox("Italic", prefix, parent, gsizer, pad)
        self.addCheckBox("Bold", prefix, parent, gsizer, pad)
        self.addCheckBox("Underlined", prefix, parent, gsizer, pad)

        hsizer.Add(gsizer, 0, wx.EXPAND)

        return hsizer

    def addCheckBox(self, name, prefix, parent, sizer, pad):
        cb = wx.CheckBox(parent, -1, name)
        self.Bind(wx.EVT_CHECKBOX, self.OnStyleCb, id=cb.GetId())
        sizer.Add(cb, 0, wx.TOP, pad)
        setattr(self, prefix + name + "Cb", cb)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnElementCombo(self, event = None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection())
        self.cfg2gui()

    def OnStyleCb(self, event):
        tcfg = self.cfg.types[self.lt]

        tcfg.screen.isCaps = self.screenCapsCb.GetValue()
        tcfg.screen.isItalic = self.screenItalicCb.GetValue()
        tcfg.screen.isBold = self.screenBoldCb.GetValue()
        tcfg.screen.isUnderlined = self.screenUnderlinedCb.GetValue()

        tcfg.export.isCaps = self.exportCapsCb.GetValue()
        tcfg.export.isItalic = self.exportItalicCb.GetValue()
        tcfg.export.isBold = self.exportBoldCb.GetValue()
        tcfg.export.isUnderlined = self.exportUnderlinedCb.GetValue()

    def OnMisc(self, event = None):
        tcfg = self.cfg.types[self.lt]

        tcfg.beforeSpacing = util.getSpinValue(self.beforeSpacingEntry)
        tcfg.intraSpacing = util.getSpinValue(self.intraSpacingEntry)
        tcfg.indent = util.getSpinValue(self.indentEntry)
        tcfg.width = util.getSpinValue(self.widthEntry)

    def cfg2gui(self):
        tcfg = self.cfg.types[self.lt]

        self.screenCapsCb.SetValue(tcfg.screen.isCaps)
        self.screenItalicCb.SetValue(tcfg.screen.isItalic)
        self.screenBoldCb.SetValue(tcfg.screen.isBold)
        self.screenUnderlinedCb.SetValue(tcfg.screen.isUnderlined)

        self.exportCapsCb.SetValue(tcfg.export.isCaps)
        self.exportItalicCb.SetValue(tcfg.export.isItalic)
        self.exportBoldCb.SetValue(tcfg.export.isBold)
        self.exportUnderlinedCb.SetValue(tcfg.export.isUnderlined)

        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.beforeSpacingEntry.SetValue(5)
        self.intraSpacingEntry.SetValue(5)
        self.indentEntry.SetValue(5)

        self.beforeSpacingEntry.SetValue(tcfg.beforeSpacing)
        self.intraSpacingEntry.SetValue(tcfg.intraSpacing)
        self.indentEntry.SetValue(tcfg.indent)
        self.widthEntry.SetValue(tcfg.width)

class ColorsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.colorsLb = wx.ListBox(self, -1, size = (300, 250))

        tmp = list(self.cfg.cvars.color.values())
        tmp = sorted(tmp, key=functools.cmp_to_key(lambda c1, c2: cmpfunc(c1.descr, c2.descr)))

        for it in tmp:
            self.colorsLb.Append(it.descr, it.name)

        hsizer.Add(self.colorsLb, 1)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        btn = wx.Button(self, -1, "Change")
        self.Bind(wx.EVT_BUTTON, self.OnChangeColor, id=btn.GetId())
        vsizer2.Add(btn, 0, wx.BOTTOM, 10)

        btn = wx.Button(self, -1, "Restore default")
        self.Bind(wx.EVT_BUTTON, self.OnDefaultColor, id=btn.GetId())
        vsizer2.Add(btn)

        hsizer.Add(vsizer2, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.colorSample = misc.MyColorSample(self, -1,
            size = wx.Size(200, 50))
        hsizer.Add(self.colorSample, 1, wx.EXPAND)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        self.useCustomElemColors = wx.CheckBox(
            self, -1, "Use per-element-type colors")
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.useCustomElemColors.GetId())
        vsizer.Add(self.useCustomElemColors)

        util.finishWindow(self, vsizer, center = False)

        self.Bind(wx.EVT_LISTBOX, self.OnColorLb, id=self.colorsLb.GetId())
        self.colorsLb.SetSelection(0)
        self.OnColorLb()

    def OnColorLb(self, event = None):
        self.color = self.colorsLb.GetClientData(self.colorsLb.
                                                    GetSelection())
        self.cfg2gui()

    def OnChangeColor(self, event):
        cd = wx.ColourData()
        cd.SetColour(getattr(self.cfg, self.color).toWx())
        dlg = wx.ColourDialog(self, cd)
        dlg.SetTitle(self.colorsLb.GetStringSelection())
        if dlg.ShowModal() == wx.ID_OK:
            setattr(self.cfg, self.color,
                    util.MyColor.fromWx(dlg.GetColourData().GetColour()))
        dlg.Destroy()

        self.cfg2gui()

    def OnDefaultColor(self, event):
        setattr(self.cfg, self.color, self.cfg.cvars.getDefault(self.color))
        self.cfg2gui()

    def OnMisc(self, event = None):
        self.cfg.useCustomElemColors = self.useCustomElemColors.GetValue()

    def cfg2gui(self):
        self.useCustomElemColors.SetValue(self.cfg.useCustomElemColors)

        self.colorSample.SetBackgroundColour(
            getattr(self.cfg, self.color).toWx())
        self.colorSample.Refresh()

class PaperPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        self.blockEvents = 1

        self.paperSizes = {
            "A4" : (210.0, 297.0),
            "Letter" : (215.9, 279.4),
            "Custom" : (1.0, 1.0)
            }

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(3, 2, 5, 5)

        gsizer.Add(wx.StaticText(self, -1, "Type:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.paperCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for k, v in list(self.paperSizes.items()):
            self.paperCombo.Append(k, v)

        gsizer.Add(self.paperCombo)

        gsizer.Add(wx.StaticText(self, -1, "Width:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.widthEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.widthEntry)
        hsizer.Add(wx.StaticText(self, -1, "mm"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        gsizer.Add(hsizer)

        gsizer.Add(wx.StaticText(self, -1, "Height:"), 0,
                   wx.ALIGN_CENTER_VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.heightEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.heightEntry)
        hsizer.Add(wx.StaticText(self, -1, "mm"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 5)
        gsizer.Add(hsizer)

        vsizer.Add(gsizer, 0, wx.BOTTOM, 10)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Margins"),
                                  wx.HORIZONTAL)

        gsizer = wx.FlexGridSizer(4, 5, 5, 5)

        self.addMarginCtrl("Top", self, gsizer)
        self.addMarginCtrl("Bottom", self, gsizer)
        self.addMarginCtrl("Left", self, gsizer)
        self.addMarginCtrl("Right", self, gsizer)

        bsizer.Add(gsizer, 0, wx.EXPAND | wx.ALL, 10)

        vsizer.Add(bsizer, 0, wx.BOTTOM, 10)

        vsizer.Add(wx.StaticText(self, -1, "(1 inch = 25.4 mm)"), 0,
                   wx.LEFT, 25)

        self.linesLabel = wx.StaticText(self, -1, "")

        # wxwindows doesn't recalculate sizer size correctly at startup so
        # set initial text
        self.setLines()

        vsizer.Add(self.linesLabel, 0, wx.TOP, 20)

        util.finishWindow(self, vsizer, center = False)

        ptype = "Custom"
        for k, v in list(self.paperSizes.items()):
            if self.eqFloat(self.cfg.paperWidth, v[0]) and \
               self.eqFloat(self.cfg.paperHeight, v[1]):
                ptype = k

        idx = self.paperCombo.FindString(ptype)
        if idx != -1:
            self.paperCombo.SetSelection(idx)

        self.Bind(wx.EVT_COMBOBOX, self.OnPaperCombo, id=self.paperCombo.GetId())
        self.OnPaperCombo(None)

        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.widthEntry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.heightEntry.GetId())

        self.cfg2mm()
        self.cfg2inch()

        self.blockEvents -= 1

    def eqFloat(self, f1, f2):
        return round(f1, 2) == round(f2, 2)

    def addMarginCtrl(self, name, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, name + ":"), 0,
                  wx.ALIGN_CENTER_VERTICAL)

        entry = wx.TextCtrl(parent, -1)
        sizer.Add(entry, 0)
        label = wx.StaticText(parent, -1, "mm")
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)

        entry2 = wx.TextCtrl(parent, -1)
        sizer.Add(entry2, 0, wx.LEFT, 20)
        label2 = wx.StaticText(parent, -1, "inch")
        sizer.Add(label2, 0, wx.ALIGN_CENTER_VERTICAL)

        setattr(self, name.lower() + "EntryMm", entry)
        setattr(self, name.lower() + "EntryInch", entry2)

        self.Bind(wx.EVT_TEXT, self.OnMarginMm, id=entry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMarginInch, id=entry2.GetId())

    def doForcedUpdate(self):
        self.setLines()

    def setLines(self):
        self.cfg.recalc(False)
        self.linesLabel.SetLabel("Lines per page: %d" % self.cfg.linesOnPage)

    def OnPaperCombo(self, event):
        w, h = self.paperCombo.GetClientData(self.paperCombo.GetSelection())

        ptype = self.paperCombo.GetStringSelection()

        if ptype == "Custom":
            self.widthEntry.Enable(True)
            self.heightEntry.Enable(True)
            w = self.cfg.paperWidth
            h = self.cfg.paperHeight
        else:
            self.widthEntry.Disable()
            self.heightEntry.Disable()

        self.widthEntry.SetValue(str(w))
        self.heightEntry.SetValue(str(h))

        self.setLines()

    def OnMisc(self, event):
        if self.blockEvents > 0:
            return

        self.entry2float(self.widthEntry, "paperWidth")
        self.entry2float(self.heightEntry, "paperHeight")

        self.setLines()

    def OnMarginMm(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1

        self.entry2float(self.topEntryMm, "marginTop")
        self.entry2float(self.bottomEntryMm, "marginBottom")
        self.entry2float(self.leftEntryMm, "marginLeft")
        self.entry2float(self.rightEntryMm, "marginRight")

        self.setLines()

        self.cfg2inch()

        self.blockEvents -= 1

    def OnMarginInch(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1

        self.entry2float(self.topEntryInch, "marginTop", 25.4)
        self.entry2float(self.bottomEntryInch, "marginBottom", 25.4)
        self.entry2float(self.leftEntryInch, "marginLeft", 25.4)
        self.entry2float(self.rightEntryInch, "marginRight", 25.4)

        self.setLines()

        self.cfg2mm()

        self.blockEvents -= 1

    def cfg2mm(self):
        self.topEntryMm.SetValue(str(self.cfg.marginTop))
        self.bottomEntryMm.SetValue(str(self.cfg.marginBottom))
        self.leftEntryMm.SetValue(str(self.cfg.marginLeft))
        self.rightEntryMm.SetValue(str(self.cfg.marginRight))

    def cfg2inch(self):
        self.topEntryInch.SetValue(str(self.cfg.marginTop / 25.4))
        self.bottomEntryInch.SetValue(str(self.cfg.marginBottom / 25.4))
        self.leftEntryInch.SetValue(str(self.cfg.marginLeft / 25.4))
        self.rightEntryInch.SetValue(str(self.cfg.marginRight / 25.4))

    def entry2float(self, entry, name, factor = 1.0):
        val = util.str2float(entry.GetValue(), 0.0) * factor
        setattr(self.cfg, name, val)

class FormattingPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1,
            "Leave at least this many lines at the end of a page when\n"
            "breaking in the middle of an element:"), 0, wx.BOTTOM, 5)

        gsizer = wx.FlexGridSizer(2, 2, 5, 0)

        self.addSpin("action", "Action:", self, gsizer, "pbActionLines")
        self.addSpin("dialogue", "Dialogue", self, gsizer, "pbDialogueLines")

        vsizer.Add(gsizer, 0, wx.LEFT, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.addSpin("fontSize", "Font size:", self, hsizer, "fontSize")
        vsizer.Add(hsizer, 0, wx.TOP, 20)

        vsizer.Add(wx.StaticText(self, -1, "Scene CONTINUEDs:"), 0,
                   wx.TOP, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sceneContinuedsCb = wx.CheckBox(self, -1, "Include,")
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.sceneContinuedsCb.GetId())
        hsizer.Add(self.sceneContinuedsCb, 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        self.addSpin("sceneContinuedIndent", "indent:", self, hsizer,
                     "sceneContinuedIndent")
        hsizer.Add(wx.StaticText(self, -1, "characters"), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        vsizer.Add(hsizer, 0, wx.LEFT, 5)

        self.scenesCb = wx.CheckBox(self, -1, "Include scene numbers")
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.scenesCb.GetId())
        vsizer.Add(self.scenesCb, 0, wx.TOP, 10)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.lineNumbersCb = wx.CheckBox(self, -1, "Show line numbers (debug)")
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=self.lineNumbersCb.GetId())
        vsizer.Add(self.lineNumbersCb, 0, wx.TOP, pad)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

    def addSpin(self, name, descr, parent, sizer, cfgName):
        sizer.Add(wx.StaticText(parent, -1, descr), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

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

    def OnMisc(self, event = None):
        self.cfg.pbActionLines = util.getSpinValue(self.actionEntry)
        self.cfg.pbDialogueLines = util.getSpinValue(self.dialogueEntry)
        self.cfg.sceneContinueds = self.sceneContinuedsCb.GetValue()
        self.cfg.sceneContinuedIndent = util.getSpinValue(
            self.sceneContinuedIndentEntry)
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

class KeyboardPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, "Commands:"))

        self.commandsLb = wx.ListBox(self, -1, size = (175, 50))

        for cmd in self.cfg.commands:
            self.commandsLb.Append(cmd.name, cmd)

        vsizer2.Add(self.commandsLb, 1)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.RIGHT, 15)

        vsizer2 = wx.BoxSizer(wx.VERTICAL)

        vsizer2.Add(wx.StaticText(self, -1, "Keys:"))

        self.keysLb = wx.ListBox(self, -1, size = (150, 60))
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

        self.descEntry = wx.TextCtrl(self, -1,
            style = wx.TE_MULTILINE | wx.TE_READONLY, size = (150, 75))
        vsizer2.Add(self.descEntry, 1, wx.EXPAND)

        hsizer.Add(vsizer2, 0, wx.EXPAND | wx.BOTTOM, 10)

        vsizer.Add(hsizer)

        vsizer.Add(wx.StaticText(self, -1, "Conflicting keys:"), 0, wx.TOP, 10)

        self.conflictsEntry = wx.TextCtrl(self, -1,
            style = wx.TE_MULTILINE | wx.TE_READONLY, size = (50, 75))
        vsizer.Add(self.conflictsEntry, 1, wx.EXPAND)

        util.finishWindow(self, vsizer, center = False)

        self.Bind(wx.EVT_LISTBOX, self.OnCommandLb, id=self.commandsLb.GetId())
        self.commandsLb.SetSelection(0)
        self.OnCommandLb()

    def OnCommandLb(self, event = None):
        self.cmd = self.commandsLb.GetClientData(self.commandsLb.
                                                 GetSelection())
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
                wx.MessageBox("The key is already bound to this command.",
                              "Error", wx.OK, cfgFrame)

                return

            if key.isValidInputChar():
                wx.MessageBox("You can't bind input characters to commands.",
                              "Error", wx.OK, cfgFrame)

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

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1,
            "Default script directory"), wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.scriptDirEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.scriptDirEntry, 1,
                   wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        btn = wx.Button(self, -1, "Browse")
        self.Bind(wx.EVT_BUTTON, self.OnBrowse, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        bsizer.Add(hsizer, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        vsizer.Add(bsizer, 0, wx.EXPAND | wx.BOTTOM, 10)

        bsizer = wx.StaticBoxSizer(wx.StaticBox(self, -1,
            "PDF viewer application"), wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Path:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

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

        hsizer.Add(wx.StaticText(self, -1, "Arguments:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

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
            ("checkOnExport", "Check script for errors before print, export or compare"),
            ]

        self.checkList = wx.CheckListBox(self, -1, size = (-1, 120))

        for it in self.checkListItems:
            self.checkList.Append(it[1])

        vsizer.Add(self.checkList, 0, wx.TOP | wx.BOTTOM, pad)

        self.Bind(wx.EVT_LISTBOX, self.OnMisc, id=self.checkList.GetId())
        self.Bind(wx.EVT_CHECKLISTBOX, self.OnMisc, id=self.checkList.GetId())

        self.addSpin("splashTime", "Show splash screen for X seconds:\n"
                     " (0 = disable)", self, vsizer, "splashTime")

        self.addSpin("paginate", "Auto-paginate interval in seconds:\n"
                     " (0 = disable)", self, vsizer, "paginateInterval")

        self.addSpin("wheelScroll", "Lines to scroll per mouse wheel event:",
                     self, vsizer, "mouseWheelLines")

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.scriptDirEntry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.progEntry.GetId())
        self.Bind(wx.EVT_TEXT, self.OnMisc, id=self.argsEntry.GetId())

    def addSpin(self, name, descr, parent, sizer, cfgName):
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(parent, -1, descr), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

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

    def OnMisc(self, event = None):
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
            cfgFrame, defaultPath = self.cfg.scriptDir,
            style = wx.DD_NEW_DIR_BUTTON)

        if dlg.ShowModal() == wx.ID_OK:
            self.scriptDirEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def OnBrowsePDF(self, event):
        dlg = wx.FileDialog(
            cfgFrame, "Choose program",
            os.path.dirname(self.cfg.pdfViewerPath),
            self.cfg.pdfViewerPath, style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            self.progEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def OnGuessPDF(self, event):
        # TODO: there must be a way to find out the default PDF viewer on
        # Linux; we should do that here.

        viewer = util.getWindowsPDFViewer()

        if viewer:
            self.progEntry.SetValue(viewer)
        else:
            wx.MessageBox("Unable to guess. Please set the path manually.",
                          "PDF Viewer", wx.OK, cfgFrame)

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

class ElementsGlobalPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Element:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.elementsCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for t in config.getTIs():
            self.elementsCombo.Append(t.name, t.lt)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(0, 2, 5, 0)

        self.addTypeCombo("newEnter", "Enter creates", self, gsizer)
        self.addTypeCombo("newTab", "Tab creates", self, gsizer)
        self.addTypeCombo("nextTab", "Tab switches to", self, gsizer)
        self.addTypeCombo("prevTab", "Shift+Tab switches to", self, gsizer)

        vsizer.Add(gsizer)

        util.finishWindow(self, vsizer, center = False)

        self.Bind(wx.EVT_COMBOBOX, self.OnElementCombo, id=self.elementsCombo.GetId())

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTypeCombo(self, name, descr, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, descr + ":"), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        combo = wx.ComboBox(parent, -1, style = wx.CB_READONLY)

        for t in config.getTIs():
            combo.Append(t.name, t.lt)

        sizer.Add(combo)

        self.Bind(wx.EVT_COMBOBOX, self.OnMisc, id=combo.GetId())

        setattr(self, name + "Combo", combo)

    def OnElementCombo(self, event = None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.
                                                   GetSelection())
        self.cfg2gui()

    def OnMisc(self, event = None):
        tcfg = self.cfg.types[self.lt]

        tcfg.newTypeEnter = self.newEnterCombo.GetClientData(
            self.newEnterCombo.GetSelection())
        tcfg.newTypeTab = self.newTabCombo.GetClientData(
            self.newTabCombo.GetSelection())
        tcfg.nextTypeTab = self.nextTabCombo.GetClientData(
            self.nextTabCombo.GetSelection())
        tcfg.prevTypeTab = self.prevTabCombo.GetClientData(
            self.prevTabCombo.GetSelection())

    def cfg2gui(self):
        tcfg = self.cfg.types[self.lt]

        util.reverseComboSelect(self.newEnterCombo, tcfg.newTypeEnter)
        util.reverseComboSelect(self.newTabCombo, tcfg.newTypeTab)
        util.reverseComboSelect(self.nextTabCombo, tcfg.nextTypeTab)
        util.reverseComboSelect(self.prevTabCombo, tcfg.prevTypeTab)

class StringsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        # list of names. each name is both the name of a wx.TextCtrl in
        # this class and the name of a string configuration variable in
        # cfg.
        self.items = []

        vsizer = wx.BoxSizer(wx.VERTICAL)

        gsizer = wx.FlexGridSizer(4, 2, 5, 0)

        self.addEntry("strContinuedPageEnd", "(CONTINUED)", self, gsizer)
        self.addEntry("strContinuedPageStart", "CONTINUED:", self, gsizer)
        self.addEntry("strMore", "(MORE)", self, gsizer)
        self.addEntry("strDialogueContinued", " (cont'd)", self, gsizer)

        gsizer.AddGrowableCol(1)
        vsizer.Add(gsizer, 0, wx.EXPAND)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

        for it in self.items:
            self.Bind(wx.EVT_TEXT, self.OnMisc, id=getattr(self, it).GetId())

    def addEntry(self, name, descr, parent, sizer):
        sizer.Add(wx.StaticText(parent, -1, descr), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        tmp = wx.TextCtrl(parent, -1)
        sizer.Add(tmp, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)

        setattr(self, name, tmp)
        self.items.append(name)

    def OnMisc(self, event = None):
        for it in self.items:
            setattr(self.cfg, it, misc.fromGUI(getattr(self, it).GetValue()))

    def cfg2gui(self):
        for it in self.items:
            getattr(self, it).SetValue(getattr(self.cfg, it))

class PDFPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.includeTOCCb = self.addCb("Add table of contents", vsizer, pad)

        self.showTOCCb = self.addCb("Show table of contents on PDF open",
                                    vsizer, pad)

        self.openOnCurrentPageCb = self.addCb("Open PDF on current page",
                                              vsizer, pad)

        self.removeNotesCb = self.addCb(
            "Omit Note elements", vsizer, pad)

        self.outlineNotesCb = self.addCb(
            "  Draw rectangles around Note elements", vsizer, pad)

        self.marginsCb = self.addCb("Show margins (debug)", vsizer, pad)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

    def addCb(self, descr, sizer, pad):
        ctrl = wx.CheckBox(self, -1, descr)
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=ctrl.GetId())
        sizer.Add(ctrl, 0, wx.TOP, pad)

        return ctrl

    def OnMisc(self, event = None):
        self.cfg.pdfIncludeTOC = self.includeTOCCb.GetValue()
        self.cfg.pdfShowTOC = self.showTOCCb.GetValue()
        self.cfg.pdfOpenOnCurrentPage = self.openOnCurrentPageCb.GetValue()
        self.cfg.pdfRemoveNotes = self.removeNotesCb.GetValue()
        self.cfg.pdfOutlineNotes = self.outlineNotesCb.GetValue()
        self.cfg.pdfShowMargins = self.marginsCb.GetValue()

        self.outlineNotesCb.Enable(not self.cfg.pdfRemoveNotes)

    def cfg2gui(self):
        self.includeTOCCb.SetValue(self.cfg.pdfIncludeTOC)
        self.showTOCCb.SetValue(self.cfg.pdfShowTOC)
        self.openOnCurrentPageCb.SetValue(self.cfg.pdfOpenOnCurrentPage)
        self.removeNotesCb.SetValue(self.cfg.pdfRemoveNotes)
        self.outlineNotesCb.SetValue(self.cfg.pdfOutlineNotes)
        self.marginsCb.SetValue(self.cfg.pdfShowMargins)

class PDFFontsPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        self.blockEvents = True

        # last directory we chose a font from
        self.lastDir = ""

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1,
            "Leave all the fields empty to use the default PDF Courier\n"
            "fonts. This is highly recommended.\n"
            "\n"
            "Otherwise, fill in the font name (e.g. AndaleMono) to use\n"
            "the specified TrueType font. If you want to embed the font\n"
            "in the generated PDF files, fill in the font filename as well.\n"
            "\n"
            "See the manual for the full details.\n"))

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Type:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)

        self.typeCombo = wx.ComboBox(self, -1, style = wx.CB_READONLY)

        for pfi in self.cfg.getPDFFontIds():
            pf = self.cfg.getPDFFont(pfi)
            self.typeCombo.Append(pf.name, pf)

        hsizer.Add(self.typeCombo, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        gsizer = wx.FlexGridSizer(2, 3, 5, 5)
        gsizer.AddGrowableCol(1)

        self.addEntry("nameEntry", "Name:", self, gsizer)
        gsizer.Add((1,1), 0)

        self.addEntry("fileEntry", "File:", self, gsizer)
        btn = wx.Button(self, -1, "Browse")
        gsizer.Add(btn)

        self.Bind(wx.EVT_BUTTON, self.OnBrowse, id=btn.GetId())

        vsizer.Add(gsizer, 0, wx.EXPAND)

        util.finishWindow(self, vsizer, center = False)

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
        sizer.Add(wx.StaticText(parent, -1, descr), 0,
                  wx.ALIGN_CENTER_VERTICAL)

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

        dlg = wx.FileDialog(cfgFrame, "Choose font file",
            defaultDir = dDir, defaultFile = dFile,
            wildcard = "TrueType fonts (*.ttf;*.TTF)|*.ttf;*.TTF|All files|*",
            style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            self.fileEntry.SetValue(dlg.GetPath())
            self.fileEntry.SetInsertionPointEnd()

            fname = dlg.GetPath()

            self.nameEntry.SetValue(self.getFontPostscriptName(fname))
            self.lastDir = os.path.dirname(fname)

        dlg.Destroy()

    def OnTypeCombo(self, event = None):
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
        fontProgram = util.loadFile(filename, cfgFrame, 10 * 1024 * 1024)

        if fontProgram is None:
            return ""

        f = truetype.Font(fontProgram)

        if not f.isOK():
            wx.MessageBox("File '%s'\n"
                          "does not appear to be a valid TrueType font."
                          % filename,
                          "Error", wx.OK, cfgFrame)

            return ""

        if not f.allowsEmbedding():
            wx.MessageBox("Font '%s'\n"
                          "does not allow embedding in its license terms.\n"
                          "You may encounter problems using this font"
                          " embedded." % filename,
                          "Error", wx.OK, cfgFrame)

        return f.getPostscriptName()

def cmpfunc(a, b):
    return (a > b) - (a < b)
