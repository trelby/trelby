import config
import misc
import string
import util
from wxPython.wx import *

# stupid hack to get correct window modality stacking for message box
# windows
cfgFrame = None

class CfgDlg(wxDialog):
    def __init__(self, parent, cfg, applyFunc):
        wxDialog.__init__(self, parent, -1, "Config dialog",
                          pos = wxDefaultPosition,
                          size = (400, 450),
                          style = wxDEFAULT_DIALOG_STYLE)
        self.cfg = cfg
        self.applyFunc = applyFunc

        global cfgFrame
        cfgFrame = self
        
        self.Center()
        
        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        self.notebook = wxNotebook(self, -1, style = wxCLIP_CHILDREN)
        vsizer.Add(self.notebook, 1, wxEXPAND)

        p = AutoCompPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Auto-completion")

        p = ColorsPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Colors")

        p = ElementsPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Elements")

        p = FontPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Font")

        p = PaperPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Paper")

        self.notebook.SetSelection(2)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(1, 1, 1)
        
        apply = wxButton(self, -1, "Apply")
        hsizer.Add(apply, 0, wxALL, 5)

        cancel = wxButton(self, -1, "Cancel")
        hsizer.Add(cancel, 0, wxALL, 5)
        
        ok = wxButton(self, -1, "OK")
        hsizer.Add(ok, 0, wxALL, 5)

        vsizer.Add(hsizer, 0, wxEXPAND)

        EVT_BUTTON(self, apply.GetId(), self.OnApply)
        EVT_BUTTON(self, cancel.GetId(), self.OnCancel)
        EVT_BUTTON(self, ok.GetId(), self.OnOK)
        
        self.Layout()

    def OnOK(self, event):
        self.EndModal(wxID_OK)

    def OnApply(self, event):
        self.applyFunc(self.cfg)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

class FontPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        btn = wxButton(panel, -1, "Change")
        EVT_BUTTON(self, btn.GetId(), self.OnChangeFont)
        hsizer.Add(btn, 0)

        self.fontLabel = wxStaticText(panel, -1, "")
        hsizer.Add(self.fontLabel, 0, wxADJUST_MINSIZE |
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxBOTTOM, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(panel, -1, "Row spacing:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.spacingEntry = wxSpinCtrl(panel, -1)
        self.spacingEntry.SetRange(4, 125)
        EVT_SPINCTRL(self, self.spacingEntry.GetId(), self.OnSpacing)
        EVT_KILL_FOCUS(self.spacingEntry, self.OnKillFocus)
        hsizer.Add(self.spacingEntry, 0)

        hsizer.Add(wxStaticText(panel, -1, "pixels"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxBOTTOM, 20)

        vsizer.Add(wxStaticText(panel, -1, "This font is only used for"
            " display on screen, printing always"))
        vsizer.Add(wxStaticText(panel, -1, "uses 12-point Courier."))
                
        panel.SetSizer(vsizer)

        self.cfg2gui()
        
        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

    def OnKillFocus(self, event):
        self.OnSpacing()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()
        
    def OnChangeFont(self, event):
        fd = wxFontData()
        nfi = wxNativeFontInfo()
        nfi.FromString(self.cfg.nativeFont)
        font = wxFontFromNativeInfo(nfi)
        fd.SetInitialFont(font)

        dlg = wxFontDialog(self, fd)
        if dlg.ShowModal() == wxID_OK:
            font = dlg.GetFontData().GetChosenFont()
            if util.isFixedWidth(font):
                self.cfg.nativeFont = font.GetNativeFontInfo().ToString()

                dc = wxMemoryDC()
                dc.SetFont(font)
                w1, h1, descent, nada = dc.GetFullTextExtent("O")
                self.cfg.fontYdelta = h1 + descent
                
                self.cfg2gui()
                self.Layout()
            else:
                wxMessageBox("The selected font is not fixed width and"
                             " can not be used.", "Error", wxOK, cfgFrame)

        dlg.Destroy()

    def OnSpacing(self, event = None):
        self.cfg.fontYdelta = util.getSpinValue(self.spacingEntry)
        
    def cfg2gui(self):
        nfi = wxNativeFontInfo()
        nfi.FromString(self.cfg.nativeFont)

        ps = nfi.GetPointSize()
        if wxPlatform == "__WXGTK__":
            ps /= 10
            
        self.fontLabel.SetLabel("Font: '%s', Size: %d" %
                                (nfi.GetFaceName(), ps))

        self.spacingEntry.SetValue(self.cfg.fontYdelta)
        
class ElementsPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(panel, -1, "Element:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.elementsCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for t in self.cfg.types.values():
            self.elementsCombo.Append(t.name, t.type)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wxEXPAND)

        vsizer.Add(wxStaticLine(panel, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 10)

        hsizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Style"),
                                  wxHORIZONTAL)

        gsizer = wxFlexGridSizer(2, 2, 0, 10)

        # wxGTK adds way more space by default than wxMSG between the
        # items, have to adjust for that
        pad = 0
        if wxPlatform == "__WXMSW__":
            pad = 5
        
        self.capsCb = wxCheckBox(panel, -1, "Caps")
        EVT_CHECKBOX(self, self.capsCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.capsCb, 0, wxTOP, pad)
            
        self.italicCb = wxCheckBox(panel, -1, "Italic")
        EVT_CHECKBOX(self, self.italicCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.italicCb, 0, wxTOP, pad)
            
        self.boldCb = wxCheckBox(panel, -1, "Bold")
        EVT_CHECKBOX(self, self.boldCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.boldCb, 0, wxTOP, pad)
            
        self.underlinedCb = wxCheckBox(panel, -1, "Underlined")
        EVT_CHECKBOX(self, self.underlinedCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.underlinedCb, 0, wxTOP, pad)
            
        hsizer.Add(gsizer, 0, wxEXPAND)
        
        vsizer.Add(hsizer, 0, wxBOTTOM, 10)

        hsizer2 = wxBoxSizer(wxHORIZONTAL)
        
        hsizer2.Add(wxStaticText(panel, -1, "Empty lines before:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.emptyLinesEntry = wxSpinCtrl(panel, -1)
        self.emptyLinesEntry.SetRange(0, 5)
        EVT_SPINCTRL(self, self.emptyLinesEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.emptyLinesEntry, self.OnKillFocus)
        hsizer2.Add(self.emptyLinesEntry, 0)
        
        vsizer.Add(hsizer2, 0, wxBOTTOM, 20)
        
        gsizer = wxFlexGridSizer(2, 3, 5, 0)

        gsizer.Add(wxStaticText(panel, -1, "Indent:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.indentEntry = wxSpinCtrl(panel, -1)
        self.indentEntry.SetRange(0, 80)
        EVT_SPINCTRL(self, self.indentEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.indentEntry, self.OnKillFocus)
        gsizer.Add(self.indentEntry, 0)

        gsizer.Add(wxStaticText(panel, -1, "characters (10 characters"
            " = 1 inch)"), 0, wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        gsizer.Add(wxStaticText(panel, -1, "Width:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.widthEntry = wxSpinCtrl(panel, -1)
        self.widthEntry.SetRange(5, 80)
        EVT_SPINCTRL(self, self.widthEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.widthEntry, self.OnKillFocus)
        gsizer.Add(self.widthEntry, 0)

        gsizer.Add(wxStaticText(panel, -1, "characters (10 characters"
            " = 1 inch)"), 0, wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        vsizer.Add(gsizer, 0, wxBOTTOM, 20)

        gsizer = wxFlexGridSizer(2, 2, 5, 0)

        self.addTypeCombo("newEnter", "Enter creates", panel, gsizer)
        self.addTypeCombo("newTab", "Tab creates", panel, gsizer)
        self.addTypeCombo("nextTab", "Tab switches to", panel, gsizer)
        self.addTypeCombo("prevTab", "Shift+Tab switches to", panel, gsizer)

        vsizer.Add(gsizer, 0, 0)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def addTypeCombo(self, name, descr, panel, sizer):
        sizer.Add(wxStaticText(panel, -1, descr + ":"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        combo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for t in self.cfg.types.values():
            combo.Append(t.name, t.type)

        sizer.Add(combo)

        EVT_COMBOBOX(self, combo.GetId(), self.OnMisc)
        
        setattr(self, name + "Combo", combo)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnElementCombo(self, event = None):
        self.type = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection())
        self.cfg2gui()
                         
    def OnStyleCb(self, event):
        tcfg = self.cfg.types[self.type]
        
        tcfg.isCaps = self.capsCb.GetValue()
        tcfg.isItalic = self.italicCb.GetValue()
        tcfg.isBold = self.boldCb.GetValue()
        tcfg.isUnderlined = self.underlinedCb.GetValue()

    def OnMisc(self, event = None):
        tcfg = self.cfg.types[self.type]

        tcfg.emptyLinesBefore = util.getSpinValue(self.emptyLinesEntry)
        tcfg.indent = util.getSpinValue(self.indentEntry)
        tcfg.width = util.getSpinValue(self.widthEntry)

        tcfg.newTypeEnter = self.newEnterCombo.GetClientData(
            self.newEnterCombo.GetSelection())
        tcfg.newTypeTab = self.newTabCombo.GetClientData(
            self.newTabCombo.GetSelection())
        tcfg.nextTypeTab = self.nextTabCombo.GetClientData(
            self.nextTabCombo.GetSelection())
        tcfg.prevTypeTab = self.prevTabCombo.GetClientData(
            self.prevTabCombo.GetSelection())
            
    def cfg2gui(self):
        tcfg = self.cfg.types[self.type]
        
        self.capsCb.SetValue(tcfg.isCaps)
        self.italicCb.SetValue(tcfg.isItalic)
        self.boldCb.SetValue(tcfg.isBold)
        self.underlinedCb.SetValue(tcfg.isUnderlined)

        # stupid wxwindows/wxpython displays empty box if the initial
        # value is zero if we don't do this...
        self.emptyLinesEntry.SetValue(5)
        self.indentEntry.SetValue(5)
        
        self.emptyLinesEntry.SetValue(tcfg.emptyLinesBefore)
        self.indentEntry.SetValue(tcfg.indent)
        self.widthEntry.SetValue(tcfg.width)

        util.reverseComboSelect(self.newEnterCombo, tcfg.newTypeEnter)
        util.reverseComboSelect(self.newTabCombo, tcfg.newTypeTab)
        util.reverseComboSelect(self.nextTabCombo, tcfg.nextTypeTab)
        util.reverseComboSelect(self.prevTabCombo, tcfg.prevTypeTab)

class ColorsPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.colorsLb = wxListBox(panel, -1, size = (300, 150))

        keys = self.cfg.colors.keys()
        keys.sort()
        for k in keys:
            self.colorsLb.Append(k, self.cfg.colors[k])

        hsizer.Add(self.colorsLb, 1)

        vsizer.Add(hsizer, 0, wxEXPAND | wxBOTTOM, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        btn = wxButton(panel, -1, "Change")
        EVT_BUTTON(self, btn.GetId(), self.OnChangeColor)
        hsizer.Add(btn, 0, wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.colorSample = misc.MyColorSample(panel, -1,
            size = wxSize(200, 50))
        hsizer.Add(self.colorSample)
        
        vsizer.Add(hsizer, 0, wxEXPAND)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        EVT_LISTBOX(self, self.colorsLb.GetId(), self.OnColorLb)
        self.colorsLb.SetSelection(0)
        self.OnColorLb()

    def OnColorLb(self, event = None):
        self.color = self.colorsLb.GetClientData(self.colorsLb.
                                                    GetSelection())
        self.cfg2gui()
                         
    def OnChangeColor(self, event):
        cd = wxColourData()
        cd.SetColour(getattr(self.cfg, self.color))
        dlg = wxColourDialog(self, cd)
        dlg.SetTitle(self.colorsLb.GetStringSelection())
        if dlg.ShowModal() == wxID_OK:
            setattr(self.cfg, self.color,
                    dlg.GetColourData().GetColour().Get())
        dlg.Destroy()

        self.cfg2gui()
            
    def cfg2gui(self):
        self.colorSample.SetBackgroundColour(getattr(self.cfg, self.color))
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
        
        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        gsizer = wxFlexGridSizer(3, 2, 5, 5)

        gsizer.Add(wxStaticText(panel, -1, "Type:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.paperCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for k, v in self.paperSizes.items():
            self.paperCombo.Append(k, v)

        gsizer.Add(self.paperCombo)

        gsizer.Add(wxStaticText(panel, -1, "Width:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        hsizer = wxBoxSizer(wxHORIZONTAL)
        self.widthEntry = wxTextCtrl(panel, -1)
        hsizer.Add(self.widthEntry)
        hsizer.Add(wxStaticText(panel, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 5)
        gsizer.Add(hsizer)

        gsizer.Add(wxStaticText(panel, -1, "Height:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        hsizer = wxBoxSizer(wxHORIZONTAL)
        self.heightEntry = wxTextCtrl(panel, -1)
        hsizer.Add(self.heightEntry)
        hsizer.Add(wxStaticText(panel, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 5)
        gsizer.Add(hsizer)

        vsizer.Add(gsizer, 0, wxBOTTOM, 10)
        
        bsizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Margins"),
                                  wxHORIZONTAL)

        gsizer = wxFlexGridSizer(4, 5, 5, 5)

        self.addMarginCtrl("Top", panel, gsizer)
        self.addMarginCtrl("Bottom", panel, gsizer)
        self.addMarginCtrl("Left", panel, gsizer)
        self.addMarginCtrl("Right", panel, gsizer)
            
        bsizer.Add(gsizer, 0, wxEXPAND | wxALL, 10)
        
        vsizer.Add(bsizer, 0, wxBOTTOM, 10)

        vsizer.Add(wxStaticText(panel, -1, "(1 inch = 25.4 mm)"), 0,
                   wxLEFT, 25)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        idx = self.paperCombo.FindString(self.cfg.paperType)
        if idx != -1:
            self.paperCombo.SetSelection(idx)
        
        EVT_COMBOBOX(self, self.paperCombo.GetId(), self.OnPaperCombo)
        self.OnPaperCombo(None)

        EVT_TEXT(self, self.widthEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.heightEntry.GetId(), self.OnMisc)
        
        self.cfg2mm()
        self.cfg2inch()
        
        self.blockEvents -= 1

    def addMarginCtrl(self, name, panel, sizer):
        sizer.Add(wxStaticText(panel, -1, name + ":"), 0,
                  wxALIGN_CENTER_VERTICAL)
        
        entry = wxTextCtrl(panel, -1)
        sizer.Add(entry, 0)
        label = wxStaticText(panel, -1, "mm")
        sizer.Add(label, 0, wxALIGN_CENTER_VERTICAL)

        entry2 = wxTextCtrl(panel, -1)
        sizer.Add(entry2, 0, wxLEFT, 20)
        label2 = wxStaticText(panel, -1, "inch")
        sizer.Add(label2, 0, wxALIGN_CENTER_VERTICAL)

        setattr(self, name.lower() + "EntryMm", entry)
        setattr(self, name.lower() + "LabelMm", label)
        
        setattr(self, name.lower() + "EntryInch", entry2)
        setattr(self, name.lower() + "LabelInch", label2)

        EVT_TEXT(self, entry.GetId(), self.OnMarginMm)
        EVT_TEXT(self, entry2.GetId(), self.OnMarginInch)
        
    def OnPaperCombo(self, event):
        w, h = self.paperCombo.GetClientData(self.paperCombo.GetSelection())

        type = self.paperCombo.GetStringSelection()
        self.cfg.paperType = type
        
        if type == "Custom":
            self.widthEntry.Enable(True)
            self.heightEntry.Enable(True)
            w = self.cfg.paperWidth
            h = self.cfg.paperHeight
        else:
            self.widthEntry.Disable()
            self.heightEntry.Disable()
        
        self.widthEntry.SetValue(str(w))
        self.heightEntry.SetValue(str(h))
                         
    def OnMisc(self, event):
        if self.blockEvents > 0:
            return

        self.entry2float(self.widthEntry, "paperWidth", 100.0)
        self.entry2float(self.heightEntry, "paperHeight", 100.0)
    
    def OnMarginMm(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1
        
        self.entry2float(self.topEntryMm, "marginTop", 0.0)
        self.entry2float(self.bottomEntryMm, "marginBottom", 0.0)
        self.entry2float(self.leftEntryMm, "marginLeft", 0.0)
        self.entry2float(self.rightEntryMm, "marginRight", 0.0)

        self.cfg2inch()

        self.blockEvents -= 1
        
    def OnMarginInch(self, event):
        if self.blockEvents > 0:
            return

        self.blockEvents += 1

        self.entry2float(self.topEntryInch, "marginTop", 0.0, 25.4)
        self.entry2float(self.bottomEntryInch, "marginBottom", 0.0, 25.4)
        self.entry2float(self.leftEntryInch, "marginLeft", 0.0, 25.4)
        self.entry2float(self.rightEntryInch, "marginRight", 0.0, 25.4)

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

    def entry2float(self, entry, name, minVal, factor = 1.0):
        try:
            val = max(minVal, float(entry.GetValue()) * factor)
        except ValueError:
            val = minVal

        setattr(self.cfg, name, val)
        
class AutoCompPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(panel, -1, "Element:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.elementsCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for t in (config.SCENE, config.CHARACTER, config.TRANSITION):
            self.elementsCombo.Append(cfg.getType(t).name, t)

        EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wxEXPAND)

        vsizer.Add(wxStaticLine(panel, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 10)

        self.enabledCb = wxCheckBox(panel, -1, "Auto-completion enabled")
        EVT_CHECKBOX(self, self.enabledCb.GetId(), self.OnMisc)
        vsizer.Add(self.enabledCb, 0, wxBOTTOM, 10)

        vsizer.Add(wxStaticText(panel, -1, "Default items:"))

        self.itemsEntry = wxTextCtrl(panel, -1, style = wxTE_MULTILINE |
                                     wxTE_DONTWRAP )
        EVT_TEXT(self, self.itemsEntry.GetId(), self.OnMisc)
        vsizer.Add(self.itemsEntry, 1, wxEXPAND)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

    def OnElementCombo(self, event = None):
        self.type = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection())
        self.cfg2gui()
                         
    def OnMisc(self, event = None):
        tcfg = self.cfg.types[self.type]

        tcfg.doAutoComp = self.enabledCb.IsChecked()
        self.itemsEntry.Enable(tcfg.doAutoComp)
        
        l = self.itemsEntry.GetValue().split("\n")
        l2 = []
        
        for i in l:
            s = i.strip()
            if len(s) > 0:
                l2.append(s)

        tcfg.autoCompList = l2
        
    def cfg2gui(self):
        tcfg = self.cfg.types[self.type]
        
        self.enabledCb.SetValue(tcfg.doAutoComp)

        self.itemsEntry.Enable(tcfg.doAutoComp)
        self.itemsEntry.SetValue(string.join(tcfg.autoCompList, "\n"))
