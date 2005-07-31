import config
import misc
import screenplay
import util

import os.path

from wxPython.wx import *

# stupid hack to get correct window modality stacking for dialogs
cfgFrame = None

# we can delete this when/if we switch to using wxListBook in wxwidgets
# 2.5
class MyListBook(wxListBox):
    def __init__(self, parent):
        wxListBox.__init__(self, parent, -1)

        EVT_LISTBOX(self, self.GetId(), self.OnPageChange)

    def AddPage(self, page, name):
        self.Append(name, page)

    # get (w,h) tuple that's big enough to cover all contained pages
    def GetContainingSize(self):
        w, h = 0, 0

        for i in range(self.GetCount()):
            page = self.GetClientData(i)
            size = page.GetClientSize()
            w = max(w, size.width)
            h = max(h, size.height)

        return (w, h)

    # set all page sizes
    def SetPageSizes(self, w, h):
        for i in range(self.GetCount()):
            self.GetClientData(i).SetClientSizeWH(w, h)
        
    def OnPageChange(self, event = None):
        for i in range(self.GetCount()):
            self.GetClientData(i).Hide()

        panel = self.GetClientData(self.GetSelection())

        if hasattr(panel, "doForcedUpdate"):
            panel.doForcedUpdate()

        panel.Show()
    
class CfgDlg(wxDialog):
    def __init__(self, parent, cfg, applyFunc, isGlobal):
        wxDialog.__init__(self, parent, -1, "",
                          style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)
        self.cfg = cfg
        self.applyFunc = applyFunc

        global cfgFrame
        cfgFrame = self
        
        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.listbook = MyListBook(self)
        w = util.getTextExtent(self.listbook.GetFont(), "Formatting")[0]
        self.listbook.SetClientSizeWH(w + 20, 200)

        hsizer.Add(self.listbook, 0, wxEXPAND)

        self.panel = wxPanel(self, -1)
        
        hsizer.Add(self.panel, 1, wxEXPAND)

        if isGlobal:
            self.SetTitle("Settings dialog")
            
            self.AddPage(ColorsPanel, "Colors")
            self.AddPage(DisplayPanel, "Display")
            self.AddPage(ElementsGlobalPanel, "Elements")
            self.AddPage(KeyboardPanel, "Keyboard")
            self.AddPage(MiscPanel, "Misc")
        else:
            self.SetTitle("Script settings dialog")
            
            self.AddPage(ElementsPanel, "Elements")
            self.AddPage(FormattingPanel, "Formatting")
            self.AddPage(PaperPanel, "Paper")

        size = self.listbook.GetContainingSize()

        hsizer.SetItemMinSize(self.panel, *size)
        self.listbook.SetPageSizes(*size)

        self.listbook.SetSelection(0)

        # it's unclear whether SetSelection sends an event on all
        # platforms or not, so force correct action.
        self.listbook.OnPageChange()
        
        vsizer.Add(hsizer, 1, wxEXPAND)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 5)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(1, 1, 1)
        
        applyBtn = wxButton(self, -1, "Apply")
        hsizer.Add(applyBtn, 0, wxALL, 5)

        cancelBtn = wxButton(self, -1, "Cancel")
        hsizer.Add(cancelBtn, 0, wxALL, 5)
        
        okBtn = wxButton(self, -1, "OK")
        hsizer.Add(okBtn, 0, wxALL, 5)

        vsizer.Add(hsizer, 0, wxEXPAND)
        
        self.SetSizerAndFit(vsizer)
        self.Layout()
        self.Center()

        EVT_BUTTON(self, applyBtn.GetId(), self.OnApply)
        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def AddPage(self, classObj, name):
        p = classObj(self.panel, -1, self.cfg)
        self.listbook.AddPage(p, name)
        
    def OnOK(self, event):
        self.EndModal(wxID_OK)

    def OnApply(self, event):
        self.applyFunc(self.cfg)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

class DisplayPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)

        vsizer.Add(wxStaticText(self, -1, "Screen fonts:"))
        
        self.fontsLb = wxListBox(self, -1, size = (300, 100))

        for it in ["fontNormal", "fontBold", "fontItalic", "fontBoldItalic"]:
            self.fontsLb.Append("", it)
        self.fontsLb.SetSelection(0)
        self.updateFontLb()
        
        vsizer.Add(self.fontsLb, 0, wxBOTTOM, 10)
        
        btn = wxButton(self, -1, "Change")
        EVT_BUTTON(self, btn.GetId(), self.OnChangeFont)
        vsizer.Add(btn, 0, wxBOTTOM, 20)

        vsizer.Add(wxStaticText(self, -1, "The settings below apply only"
                                " to 'Draft' view mode."), 0, wxBOTTOM, 15)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(self, -1, "Row spacing:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.spacingEntry = wxSpinCtrl(self, -1)
        self.spacingEntry.SetRange(*self.cfg.cvars.getMinMax("fontYdelta"))
        EVT_SPINCTRL(self, self.spacingEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.spacingEntry, self.OnKillFocus)
        hsizer.Add(self.spacingEntry, 0)

        hsizer.Add(wxStaticText(self, -1, "pixels"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxBOTTOM, 15)

        self.pbRb = wxRadioBox(self, -1, "Page break lines to show",
            style = wxRA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "None", "Normal", "Normal + unadjusted   " ])
        vsizer.Add(self.pbRb)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)
        
        EVT_RADIOBOX(self, self.pbRb.GetId(), self.OnMisc)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnChangeFont(self, event):
        fname = self.fontsLb.GetClientData(self.fontsLb.GetSelection())
        nfont = getattr(self.cfg, fname)
        
        fd = wxFontData()
        nfi = wxNativeFontInfo()
        nfi.FromString(nfont)
        font = wxFontFromNativeInfo(nfi)
        fd.SetInitialFont(font)

        dlg = wxFontDialog(self, fd)
        if dlg.ShowModal() == wxID_OK:
            font = dlg.GetFontData().GetChosenFont()
            if util.isFixedWidth(font):
                setattr(self.cfg, fname, font.GetNativeFontInfo().ToString())

                self.cfg.fontYdelta = util.getFontHeight(font)
                
                self.cfg2gui()
                self.updateFontLb()
            else:
                wxMessageBox("The selected font is not fixed width and"
                             " can not be used.", "Error", wxOK, cfgFrame)

        dlg.Destroy()

    def OnMisc(self, event = None):
        self.cfg.fontYdelta = util.getSpinValue(self.spacingEntry)
        self.cfg.pbi = self.pbRb.GetSelection()

    def updateFontLb(self):
        names = ["Normal", "Bold", "Italic", "Bold + Italic"]

        for i in range(len(names)):
            nfi = wxNativeFontInfo()
            nfi.FromString(getattr(self.cfg, self.fontsLb.GetClientData(i)))

            ps = nfi.GetPointSize()
            if misc.isUnix:
                ps //= 10

            s = nfi.GetFaceName()

            self.fontsLb.SetString(i, "%s: %s, %d" % (names[i], s, ps))
        
    def cfg2gui(self):
        self.spacingEntry.SetValue(self.cfg.fontYdelta)
        self.pbRb.SetSelection(self.cfg.pbi)
        
class ElementsPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(self, -1, "Element:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.elementsCombo = wxComboBox(self, -1, style = wxCB_READONLY)

        for t in config.getTIs():
            self.elementsCombo.Append(t.name, t.lt)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wxEXPAND)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(self.addTextStyles("Screen", "screen", self))
        hsizer.Add(self.addTextStyles("Print", "export", self), 0, wxLEFT, 10)
        
        vsizer.Add(hsizer, 0, wxBOTTOM, 10)

        gsizer = wxFlexGridSizer(2, 2, 5, 0)
        
        gsizer.Add(wxStaticText(self, -1, "Empty lines / 10 before:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        tmp = wxSpinCtrl(self, -1)
        tmp.SetRange(*self.cfg.getType(screenplay.ACTION).cvars.getMinMax(
            "beforeSpacing"))
        EVT_SPINCTRL(self, tmp.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(tmp, self.OnKillFocus)
        gsizer.Add(tmp)
        self.beforeSpacingEntry = tmp
        
        gsizer.Add(wxStaticText(self, -1, "Empty lines / 10 between:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        tmp = wxSpinCtrl(self, -1)
        tmp.SetRange(*self.cfg.getType(screenplay.ACTION).cvars.getMinMax(
            "intraSpacing"))
        EVT_SPINCTRL(self, tmp.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(tmp, self.OnKillFocus)
        gsizer.Add(tmp)
        self.intraSpacingEntry = tmp
        
        vsizer.Add(gsizer, 0, wxBOTTOM, 20)
        
        gsizer = wxFlexGridSizer(2, 3, 5, 0)

        gsizer.Add(wxStaticText(self, -1, "Indent:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.indentEntry = wxSpinCtrl(self, -1)
        self.indentEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("indent"))
        EVT_SPINCTRL(self, self.indentEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.indentEntry, self.OnKillFocus)
        gsizer.Add(self.indentEntry, 0)

        gsizer.Add(wxStaticText(self, -1, "characters (10 characters"
            " = 1 inch)"), 0, wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        gsizer.Add(wxStaticText(self, -1, "Width:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.widthEntry = wxSpinCtrl(self, -1)
        self.widthEntry.SetRange(
            *self.cfg.getType(screenplay.ACTION).cvars.getMinMax("width"))
        EVT_SPINCTRL(self, self.widthEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.widthEntry, self.OnKillFocus)
        gsizer.Add(self.widthEntry, 0)

        gsizer.Add(wxStaticText(self, -1, "characters (10 characters"
            " = 1 inch)"), 0, wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        vsizer.Add(gsizer, 0, wxBOTTOM, 20)

        util.finishWindow(self, vsizer, center = False)

        EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTextStyles(self, name, prefix, parent):
        hsizer = wxStaticBoxSizer(wxStaticBox(parent, -1, name),
                                  wxHORIZONTAL)

        gsizer = wxFlexGridSizer(2, 2, 0, 10)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5
        
        self.addCheckBox("Caps", prefix, parent, gsizer, pad)
        self.addCheckBox("Italic", prefix, parent, gsizer, pad)
        self.addCheckBox("Bold", prefix, parent, gsizer, pad)
        self.addCheckBox("Underlined", prefix, parent, gsizer, pad)
            
        hsizer.Add(gsizer, 0, wxEXPAND)

        return hsizer

    def addCheckBox(self, name, prefix, parent, sizer, pad):
        cb = wxCheckBox(parent, -1, name)
        EVT_CHECKBOX(self, cb.GetId(), self.OnStyleCb)
        sizer.Add(cb, 0, wxTOP, pad)
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

class ColorsPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.colorsLb = wxListBox(self, -1, size = (300, 250))

        tmp = self.cfg.cvars.color.values()
        tmp.sort(lambda c1, c2: cmp(c1.descr, c2.descr))
        
        for it in tmp:
            self.colorsLb.Append(it.descr, it.name)

        hsizer.Add(self.colorsLb, 1)

        vsizer.Add(hsizer, 0, wxEXPAND | wxBOTTOM, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        btn = wxButton(self, -1, "Change")
        EVT_BUTTON(self, btn.GetId(), self.OnChangeColor)
        hsizer.Add(btn, 0, wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.colorSample = misc.MyColorSample(self, -1,
            size = wxSize(200, 50))
        hsizer.Add(self.colorSample)
        
        vsizer.Add(hsizer, 0, wxEXPAND)

        util.finishWindow(self, vsizer, center = False)

        EVT_LISTBOX(self, self.colorsLb.GetId(), self.OnColorLb)
        self.colorsLb.SetSelection(0)
        self.OnColorLb()

    def OnColorLb(self, event = None):
        self.color = self.colorsLb.GetClientData(self.colorsLb.
                                                    GetSelection())
        self.cfg2gui()
                         
    def OnChangeColor(self, event):
        cd = wxColourData()
        cd.SetColour(getattr(self.cfg, self.color).toWx())
        dlg = wxColourDialog(self, cd)
        dlg.SetTitle(self.colorsLb.GetStringSelection())
        if dlg.ShowModal() == wxID_OK:
            setattr(self.cfg, self.color,
                    util.MyColor.fromWx(dlg.GetColourData().GetColour()))
        dlg.Destroy()

        self.cfg2gui()
            
    def cfg2gui(self):
        self.colorSample.SetBackgroundColour(
            getattr(self.cfg, self.color).toWx())
        self.colorSample.Refresh()
        
class PaperPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        self.blockEvents = 1
        
        self.paperSizes = {
            "A4" : (210.0, 297.0),
            "Letter" : (215.9, 279.4),
            "Custom" : (1.0, 1.0)
            }
        
        vsizer = wxBoxSizer(wxVERTICAL)

        gsizer = wxFlexGridSizer(3, 2, 5, 5)

        gsizer.Add(wxStaticText(self, -1, "Type:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.paperCombo = wxComboBox(self, -1, style = wxCB_READONLY)

        for k, v in self.paperSizes.items():
            self.paperCombo.Append(k, v)

        gsizer.Add(self.paperCombo)

        gsizer.Add(wxStaticText(self, -1, "Width:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        hsizer = wxBoxSizer(wxHORIZONTAL)
        self.widthEntry = wxTextCtrl(self, -1)
        hsizer.Add(self.widthEntry)
        hsizer.Add(wxStaticText(self, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 5)
        gsizer.Add(hsizer)

        gsizer.Add(wxStaticText(self, -1, "Height:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        hsizer = wxBoxSizer(wxHORIZONTAL)
        self.heightEntry = wxTextCtrl(self, -1)
        hsizer.Add(self.heightEntry)
        hsizer.Add(wxStaticText(self, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 5)
        gsizer.Add(hsizer)

        vsizer.Add(gsizer, 0, wxBOTTOM, 10)
        
        bsizer = wxStaticBoxSizer(wxStaticBox(self, -1, "Margins"),
                                  wxHORIZONTAL)

        gsizer = wxFlexGridSizer(4, 5, 5, 5)

        self.addMarginCtrl("Top", self, gsizer)
        self.addMarginCtrl("Bottom", self, gsizer)
        self.addMarginCtrl("Left", self, gsizer)
        self.addMarginCtrl("Right", self, gsizer)
            
        bsizer.Add(gsizer, 0, wxEXPAND | wxALL, 10)
        
        vsizer.Add(bsizer, 0, wxBOTTOM, 10)

        vsizer.Add(wxStaticText(self, -1, "(1 inch = 25.4 mm)"), 0,
                   wxLEFT, 25)

        self.linesLabel = wxStaticText(self, -1, "")

        # wxwindows doesn't recalculate sizer size correctly at startup so
        # set initial text
        self.setLines()
        
        vsizer.Add(self.linesLabel, 0, wxTOP, 20)
        
        util.finishWindow(self, vsizer, center = False)

        ptype = "Custom"
        for k, v in self.paperSizes.items():
            if self.eqFloat(self.cfg.paperWidth, v[0]) and \
               self.eqFloat(self.cfg.paperHeight, v[1]):
                ptype = k
            
        idx = self.paperCombo.FindString(ptype)
        if idx != -1:
            self.paperCombo.SetSelection(idx)
        
        EVT_COMBOBOX(self, self.paperCombo.GetId(), self.OnPaperCombo)
        self.OnPaperCombo(None)

        EVT_TEXT(self, self.widthEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.heightEntry.GetId(), self.OnMisc)
        
        self.cfg2mm()
        self.cfg2inch()
        
        self.blockEvents -= 1

    def eqFloat(self, f1, f2):
        return round(f1, 2) == round(f2, 2)
        
    def addMarginCtrl(self, name, parent, sizer):
        sizer.Add(wxStaticText(parent, -1, name + ":"), 0,
                  wxALIGN_CENTER_VERTICAL)
        
        entry = wxTextCtrl(parent, -1)
        sizer.Add(entry, 0)
        label = wxStaticText(parent, -1, "mm")
        sizer.Add(label, 0, wxALIGN_CENTER_VERTICAL)

        entry2 = wxTextCtrl(parent, -1)
        sizer.Add(entry2, 0, wxLEFT, 20)
        label2 = wxStaticText(parent, -1, "inch")
        sizer.Add(label2, 0, wxALIGN_CENTER_VERTICAL)

        setattr(self, name.lower() + "EntryMm", entry)
        setattr(self, name.lower() + "LabelMm", label)
        
        setattr(self, name.lower() + "EntryInch", entry2)
        setattr(self, name.lower() + "LabelInch", label2)

        EVT_TEXT(self, entry.GetId(), self.OnMarginMm)
        EVT_TEXT(self, entry2.GetId(), self.OnMarginInch)

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

class FormattingPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)

        vsizer.Add(wxStaticText(self, -1,
            "Leave at least this many lines at the end of a page when\n"
            "breaking in the middle of an element:"), 0, wxBOTTOM, 5)
        
        gsizer = wxFlexGridSizer(2, 2, 5, 0)

        self.addSpin("action", "Action:", self, gsizer, "pbActionLines")
        self.addSpin("dialogue", "Dialogue", self, gsizer, "pbDialogueLines")

        vsizer.Add(gsizer, 0, wxLEFT, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(self, -1, "Font size:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.fontSizeEntry = wxSpinCtrl(self, -1)
        self.fontSizeEntry.SetRange(*self.cfg.cvars.getMinMax("fontSize"))
        EVT_SPINCTRL(self, self.fontSizeEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.fontSizeEntry, self.OnKillFocus)
        hsizer.Add(self.fontSizeEntry, 0)

        vsizer.Add(hsizer, 0, wxTOP, 20)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.sceneContinuedsCb = wxCheckBox(self, -1,
            "Include scene CONTINUEDs")
        EVT_CHECKBOX(self, self.sceneContinuedsCb.GetId(), self.OnMisc)
        vsizer.Add(self.sceneContinuedsCb, 0, wxTOP, 20)
        
        self.scenesCb = wxCheckBox(self, -1, "Include scene numbers")
        EVT_CHECKBOX(self, self.scenesCb.GetId(), self.OnMisc)
        vsizer.Add(self.scenesCb, 0, wxTOP, pad)

        self.marginsCb = wxCheckBox(self, -1, "Show margins (debug)")
        EVT_CHECKBOX(self, self.marginsCb.GetId(), self.OnMisc)
        vsizer.Add(self.marginsCb, 0, wxTOP, 10 + pad)

        self.lineNumbersCb = wxCheckBox(self, -1, "Show line numbers (debug)")
        EVT_CHECKBOX(self, self.lineNumbersCb.GetId(), self.OnMisc)
        vsizer.Add(self.lineNumbersCb, 0, wxTOP, pad)

        self.cfg2gui()
        
        util.finishWindow(self, vsizer, center = False)

    def addSpin(self, name, descr, parent, sizer, cfgName):
        sizer.Add(wxStaticText(parent, -1, descr), 0,
                  wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        entry = wxSpinCtrl(parent, -1)
        entry.SetRange(*self.cfg.cvars.getMinMax(cfgName))
        EVT_SPINCTRL(self, entry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(entry, self.OnKillFocus)
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
        self.cfg.fontSize = util.getSpinValue(self.fontSizeEntry)
        self.cfg.pdfShowSceneNumbers = self.scenesCb.GetValue()
        self.cfg.pdfShowMargins = self.marginsCb.GetValue()
        self.cfg.pdfShowLineNumbers = self.lineNumbersCb.GetValue()
        
    def cfg2gui(self):
        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.actionEntry.SetValue(5)
        self.dialogueEntry.SetValue(5)
        
        self.actionEntry.SetValue(self.cfg.pbActionLines)
        self.dialogueEntry.SetValue(self.cfg.pbDialogueLines)
        self.sceneContinuedsCb.SetValue(self.cfg.sceneContinueds)
        self.fontSizeEntry.SetValue(self.cfg.fontSize)
        self.scenesCb.SetValue(self.cfg.pdfShowSceneNumbers)
        self.marginsCb.SetValue(self.cfg.pdfShowMargins)
        self.lineNumbersCb.SetValue(self.cfg.pdfShowLineNumbers)

class KeyboardPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)

        vsizer2 = wxBoxSizer(wxVERTICAL)

        vsizer2.Add(wxStaticText(self, -1, "Commands:"))

        self.commandsLb = wxListBox(self, -1, size = (175, 50))

        for cmd in self.cfg.commands:
            self.commandsLb.Append(cmd.name, cmd)

        vsizer2.Add(self.commandsLb, 1)

        hsizer.Add(vsizer2, 0, wxEXPAND | wxRIGHT, 15)

        vsizer2 = wxBoxSizer(wxVERTICAL)

        vsizer2.Add(wxStaticText(self, -1, "Keys:"))

        self.keysLb = wxListBox(self, -1, size = (150, 60))
        vsizer2.Add(self.keysLb, 1, wxBOTTOM, 10)
        
        btn = wxButton(self, -1, "Add")
        EVT_BUTTON(self, btn.GetId(), self.OnAdd)
        vsizer2.Add(btn, 0, wxALIGN_CENTER | wxBOTTOM, 10)
        self.addBtn = btn
        
        btn = wxButton(self, -1, "Delete")
        EVT_BUTTON(self, btn.GetId(), self.OnDelete)
        vsizer2.Add(btn, 0, wxALIGN_CENTER | wxBOTTOM, 10)
        self.deleteBtn = btn

        vsizer2.Add(wxStaticText(self, -1, "Description:"))

        self.descEntry = wxTextCtrl(self, -1,
            style = wxTE_MULTILINE | wxTE_READONLY, size = (150, 75))
        vsizer2.Add(self.descEntry, 1, wxEXPAND)
        
        hsizer.Add(vsizer2, 0, wxEXPAND | wxBOTTOM, 10)

        vsizer.Add(hsizer)

        vsizer.Add(wxStaticText(self, -1, "Conflicting keys:"), 0, wxTOP, 10)

        self.conflictsEntry = wxTextCtrl(self, -1,
            style = wxTE_MULTILINE | wxTE_READONLY, size = (50, 75))
        vsizer.Add(self.conflictsEntry, 1, wxEXPAND)
        
        util.finishWindow(self, vsizer, center = False)

        EVT_LISTBOX(self, self.commandsLb.GetId(), self.OnCommandLb)
        self.commandsLb.SetSelection(0)
        self.OnCommandLb()

    def OnCommandLb(self, event = None):
        self.cmd = self.commandsLb.GetClientData(self.commandsLb.
                                                 GetSelection())
        self.cfg2gui()

    def OnAdd(self, event):
        dlg = misc.KeyDlg(cfgFrame, self.cmd.name)

        key = None
        if dlg.ShowModal() == wxID_OK:
            key = dlg.key
        dlg.Destroy()

        if key:
            kint = key.toInt()
            if kint in self.cmd.keys:
                wxMessageBox("The key is already bound to this command.",
                             "Error", wxOK, cfgFrame)

                return

            if key.isValidInputChar():
                wxMessageBox("You can't bind input characters to commands.",
                             "Error", wxOK, cfgFrame)

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
        
class MiscPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)

        bsizer = wxStaticBoxSizer(wxStaticBox(self, -1,
            "Default script directory"), wxVERTICAL)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.scriptDirEntry = wxTextCtrl(self, -1)
        hsizer.Add(self.scriptDirEntry, 1,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        btn = wxButton(self, -1, "Browse")
        EVT_BUTTON(self, btn.GetId(), self.OnBrowse)
        hsizer.Add(btn, 0, wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        bsizer.Add(hsizer, 1, wxEXPAND | wxTOP | wxBOTTOM, 5)

        vsizer.Add(bsizer, 0, wxEXPAND | wxBOTTOM, 10)

        bsizer = wxStaticBoxSizer(wxStaticBox(self, -1,
            "PDF viewer application"), wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(self, -1, "Path:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.progEntry = wxTextCtrl(self, -1)
        hsizer.Add(self.progEntry, 1, wxALIGN_CENTER_VERTICAL)

        btn = wxButton(self, -1, "Browse")
        EVT_BUTTON(self, btn.GetId(), self.OnBrowsePDF)
        hsizer.Add(btn, 0, wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        bsizer.Add(hsizer, 1, wxEXPAND)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(self, -1, "Arguments:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.argsEntry = wxTextCtrl(self, -1)
        hsizer.Add(self.argsEntry, 1, wxALIGN_CENTER_VERTICAL)

        bsizer.Add(hsizer, 1, wxEXPAND)

        vsizer.Add(bsizer, 1, wxEXPAND)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.autoCapSentences = wxCheckBox(self, -1,
                                           "Auto-capitalize sentences")
        EVT_CHECKBOX(self, self.autoCapSentences.GetId(), self.OnMisc)
        vsizer.Add(self.autoCapSentences, 0, wxTOP | wxBOTTOM, pad)

        self.checkErrorsCb = wxCheckBox(self, -1,
            "Check script for errors before print, export or compare")
        EVT_CHECKBOX(self, self.checkErrorsCb.GetId(), self.OnMisc)
        vsizer.Add(self.checkErrorsCb, 0, wxBOTTOM, 10)

        self.addSpin("paginate", "Auto-paginate interval in seconds:\n"
                     " (0 = disable)", self, vsizer, "paginateInterval")

        self.addSpin("confDel", "Confirm deletes >= this many lines\n"
                     " (0 = disable):", self, vsizer, "confirmDeletes")
        
        self.addSpin("wheelScroll", "Lines to scroll per mouse wheel event:",
                     self, vsizer, "mouseWheelLines")
            
        self.cfg2gui()

        util.finishWindow(self, vsizer, center = False)

        EVT_TEXT(self, self.scriptDirEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.progEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.argsEntry.GetId(), self.OnMisc)

    def addSpin(self, name, descr, parent, sizer, cfgName):
        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(parent, -1, descr), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        tmp = wxSpinCtrl(parent, -1)
        tmp.SetRange(*self.cfg.cvars.getMinMax(cfgName))
        EVT_SPINCTRL(self, tmp.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(tmp, self.OnKillFocus)
        hsizer.Add(tmp)
        
        sizer.Add(hsizer, 0, wxBOTTOM, 10)
        
        setattr(self, name + "Entry", tmp)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnMisc(self, event = None):
        self.cfg.scriptDir = self.scriptDirEntry.GetValue().rstrip("/\\")
        self.cfg.pdfViewerPath = self.progEntry.GetValue()
        self.cfg.pdfViewerArgs = self.argsEntry.GetValue()
        self.cfg.capitalize = self.autoCapSentences.GetValue()
        self.cfg.checkOnExport = self.checkErrorsCb.GetValue()
        self.cfg.paginateInterval = util.getSpinValue(self.paginateEntry)
        self.cfg.confirmDeletes = util.getSpinValue(self.confDelEntry)
        self.cfg.mouseWheelLines = util.getSpinValue(self.wheelScrollEntry)

    def OnBrowse(self, event):
        dlg = wxDirDialog(cfgFrame, defaultPath = self.cfg.scriptDir,
                          style = wxDD_NEW_DIR_BUTTON)

        if dlg.ShowModal() == wxID_OK:
            self.scriptDirEntry.SetValue(dlg.GetPath())

        dlg.Destroy()
            
    def OnBrowsePDF(self, event):
        dlg = wxFileDialog(cfgFrame, "Choose program",
            os.path.dirname(self.cfg.pdfViewerPath), self.cfg.pdfViewerPath,
            style = wxOPEN)

        if dlg.ShowModal() == wxID_OK:
            self.progEntry.SetValue(dlg.GetPath())

        dlg.Destroy()

    def cfg2gui(self):
        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.paginateEntry.SetValue(5)
        self.confDelEntry.SetValue(5)

        self.scriptDirEntry.SetValue(self.cfg.scriptDir)
        self.progEntry.SetValue(self.cfg.pdfViewerPath)
        self.argsEntry.SetValue(self.cfg.pdfViewerArgs)
        self.autoCapSentences.SetValue(self.cfg.capitalize)
        self.checkErrorsCb.SetValue(self.cfg.checkOnExport)
        self.paginateEntry.SetValue(self.cfg.paginateInterval)
        self.confDelEntry.SetValue(self.cfg.confirmDeletes)
        self.wheelScrollEntry.SetValue(self.cfg.mouseWheelLines)

class ElementsGlobalPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(self, -1, "Element:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.elementsCombo = wxComboBox(self, -1, style = wxCB_READONLY)

        for t in config.getTIs():
            self.elementsCombo.Append(t.name, t.lt)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wxEXPAND)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 10)

        gsizer = wxFlexGridSizer(2, 2, 5, 0)

        self.addTypeCombo("newEnter", "Enter creates", self, gsizer)
        self.addTypeCombo("newTab", "Tab creates", self, gsizer)
        self.addTypeCombo("nextTab", "Tab switches to", self, gsizer)
        self.addTypeCombo("prevTab", "Shift+Tab switches to", self, gsizer)

        vsizer.Add(gsizer)

        util.finishWindow(self, vsizer, center = False)

        EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTypeCombo(self, name, descr, parent, sizer):
        sizer.Add(wxStaticText(parent, -1, descr + ":"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        combo = wxComboBox(parent, -1, style = wxCB_READONLY)

        for t in config.getTIs():
            combo.Append(t.name, t.lt)

        sizer.Add(combo)

        EVT_COMBOBOX(self, combo.GetId(), self.OnMisc)
        
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
