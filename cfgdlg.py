import config
import util
from wxPython.wx import *

class CfgDlg(wxDialog):
    def __init__(self, parent, cfg, applyFunc):
        wxDialog.__init__(self, parent, -1, "Config dialog",
                          pos = wxDefaultPosition,
                          size = (400, 400),
                          style = wxDEFAULT_DIALOG_STYLE)
        self.cfg = cfg
        self.applyFunc = applyFunc

        self.Center()
        
        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        self.notebook = wxNotebook(self, -1, style = wxCLIP_CHILDREN)
        vsizer.Add(self.notebook, 1, wxEXPAND)

        p = FontPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Font")

        p = ElementsPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Elements")

        p = PaperPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Paper")

        p = ColorsPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Colors")

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

        self.fontLabel = wxStaticText(panel, -1, "")
        hsizer.Add(self.fontLabel, 0, wxADJUST_MINSIZE |
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        btn = wxButton(panel, -1, "Change")
        EVT_BUTTON(self, btn.GetId(), self.OnChangeFont)
        hsizer.Add(btn, 0)

        vsizer.Add(hsizer, 0, wxEXPAND | wxBOTTOM, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(panel, -1, "Row spacing:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.spacingEntry = wxSpinCtrl(panel, -1)
        self.spacingEntry.SetRange(8, 100)
        EVT_SPINCTRL(self, self.spacingEntry.GetId(), self.OnSpacing)
        hsizer.Add(self.spacingEntry, 0)

        hsizer.Add(wxStaticText(panel, -1, "pixels"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND)
                
        panel.SetSizer(vsizer)

        self.cfg2gui()
        
        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

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
                             " can not be used.", "Error", wxOK, self)

        dlg.Destroy()

    def OnSpacing(self, event):
        self.cfg.fontYdelta = self.spacingEntry.GetValue()
        
    def cfg2gui(self):
        nfi = wxNativeFontInfo()
        nfi.FromString(self.cfg.nativeFont)
        self.fontLabel.SetLabel("Font: '%s', Size: %d" %
                                (nfi.GetFaceName(), nfi.GetPointSize() / 10))

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

        self.capsCb = wxCheckBox(panel, -1, "Caps")
        EVT_CHECKBOX(self, self.capsCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.capsCb, 0)
            
        self.italicCb = wxCheckBox(panel, -1, "Italic")
        EVT_CHECKBOX(self, self.italicCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.italicCb, 0)
            
        self.boldCb = wxCheckBox(panel, -1, "Bold")
        EVT_CHECKBOX(self, self.boldCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.boldCb, 0)
            
        self.underlinedCb = wxCheckBox(panel, -1, "Underlined")
        EVT_CHECKBOX(self, self.underlinedCb.GetId(), self.OnStyleCb)
        gsizer.Add(self.underlinedCb, 0)
            
        hsizer.Add(gsizer, 0, wxEXPAND)
        
        vsizer.Add(hsizer, 0, wxBOTTOM, 10)

        gsizer = wxFlexGridSizer(2, 3, 5, 0)

        gsizer.Add(wxStaticText(panel, -1, "Indent:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.indentEntry = wxSpinCtrl(panel, -1)
        self.indentEntry.SetRange(0, 80)
        EVT_SPINCTRL(self, self.indentEntry.GetId(), self.OnMisc)
        gsizer.Add(self.indentEntry, 0)

        gsizer.Add(wxStaticText(panel, -1, "characters"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        gsizer.Add(wxStaticText(panel, -1, "Width:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.widthEntry = wxSpinCtrl(panel, -1)
        self.widthEntry.SetRange(5, 80)
        EVT_SPINCTRL(self, self.widthEntry.GetId(), self.OnMisc)
        gsizer.Add(self.widthEntry, 0)

        gsizer.Add(wxStaticText(panel, -1, "characters"), 0,
                   wxALIGN_CENTER_VERTICAL | wxLEFT, 10)

        vsizer.Add(gsizer, 0, wxBOTTOM, 10)

        gsizer = wxFlexGridSizer(2, 2, 5, 0)

        gsizer.Add(wxStaticText(panel, -1, "Next in tab order:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.nextTabCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for t in self.cfg.types.values():
            self.nextTabCombo.Append(t.name, t.type)

        gsizer.Add(self.nextTabCombo, 0)

        gsizer.Add(wxStaticText(panel, -1, "Previous in tab order:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.prevTabCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for t in self.cfg.types.values():
            self.prevTabCombo.Append(t.name, t.type)

        gsizer.Add(self.prevTabCombo, 0)

        vsizer.Add(gsizer, 0, 0)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        EVT_COMBOBOX(self, self.nextTabCombo.GetId(), self.OnMisc)
        EVT_COMBOBOX(self, self.prevTabCombo.GetId(), self.OnMisc)
        
        EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)
        self.OnElementCombo(None)

    def OnElementCombo(self, event):
        self.type = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection())
        self.cfg2gui()
                         
    def OnStyleCb(self, event):
        tcfg = self.cfg.types[self.type]
        
        tcfg.isCaps = self.capsCb.GetValue()
        tcfg.isItalic = self.italicCb.GetValue()
        tcfg.isBold = self.boldCb.GetValue()
        tcfg.isUnderlined = self.underlinedCb.GetValue()

    def OnMisc(self, event):
        tcfg = self.cfg.types[self.type]

        tcfg.indent = self.indentEntry.GetValue()
        tcfg.width = self.widthEntry.GetValue()

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
        self.indentEntry.SetValue(5)
        
        self.indentEntry.SetValue(tcfg.indent)
        self.widthEntry.SetValue(tcfg.width)

        util.reverseComboSelect(self.nextTabCombo, tcfg.nextTypeTab)
        util.reverseComboSelect(self.prevTabCombo, tcfg.prevTypeTab)

class ColorsPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.colorsCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        keys = self.cfg.colors.keys()
        keys.sort()
        for k in keys:
            self.colorsCombo.Append(k, self.cfg.colors[k])

        hsizer.Add(self.colorsCombo, 1)

        vsizer.Add(hsizer, 0, wxEXPAND | wxBOTTOM, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        btn = wxButton(panel, -1, "Change")
        EVT_BUTTON(self, btn.GetId(), self.OnChangeColor)
        hsizer.Add(btn, 0, wxRIGHT, 10)
        
        self.sampleBtn = wxButton(panel, -1, "    ")
        self.sampleBtn.Disable()
        hsizer.Add(self.sampleBtn, 0)
        
        vsizer.Add(hsizer, 0, wxEXPAND)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        EVT_COMBOBOX(self, self.colorsCombo.GetId(), self.OnColorCombo)
        self.OnColorCombo(None)

    def OnColorCombo(self, event):
        self.color = self.colorsCombo.GetClientData(self.colorsCombo.
                                                    GetSelection())
        self.cfg2gui()
                         
    def OnChangeColor(self, event):
        cd = wxColourData()
        cd.SetColour(getattr(self.cfg, self.color))
        dlg = wxColourDialog(self, cd)
        if dlg.ShowModal() == wxID_OK:
            setattr(self.cfg, self.color,
                    dlg.GetColourData().GetColour().Get())
        dlg.Destroy()

        self.cfg2gui()
            
    def cfg2gui(self):
        self.sampleBtn.SetBackgroundColour(getattr(self.cfg, self.color))
        self.sampleBtn.Refresh()
        
class PaperPanel(wxPanel):
    def __init__(self, parent, id, cfg):
        wxPanel.__init__(self, parent, id)
        self.cfg = cfg

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

        gsizer = wxFlexGridSizer(4, 3, 5, 5)

        gsizer.Add(wxStaticText(panel, -1, "Top:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.topEntry = wxTextCtrl(panel, -1)
        gsizer.Add(self.topEntry, 0)
        gsizer.Add(wxStaticText(panel, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL)

        gsizer.Add(wxStaticText(panel, -1, "Bottom:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.bottomEntry = wxTextCtrl(panel, -1)
        gsizer.Add(self.bottomEntry, 0)
        gsizer.Add(wxStaticText(panel, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL)

        gsizer.Add(wxStaticText(panel, -1, "Left:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.leftEntry = wxTextCtrl(panel, -1)
        gsizer.Add(self.leftEntry, 0)
        gsizer.Add(wxStaticText(panel, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL)

        gsizer.Add(wxStaticText(panel, -1, "Right:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.rightEntry = wxTextCtrl(panel, -1)
        gsizer.Add(self.rightEntry, 0)
        gsizer.Add(wxStaticText(panel, -1, "mm"), 0,
                   wxALIGN_CENTER_VERTICAL)
            
        bsizer.Add(gsizer, 0, wxEXPAND | wxALL, 10)
        
        vsizer.Add(bsizer, 0, wxBOTTOM, 10)

        vsizer.Add(wxStaticText(panel, -1, "(1 inch = 25.4 mm)"), 0,
                   wxLEFT, 25)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        self.blockEvents = True
        
        idx = self.paperCombo.FindString(self.cfg.paperType)
        if idx != -1:
            self.paperCombo.SetSelection(idx)
        
        EVT_COMBOBOX(self, self.paperCombo.GetId(), self.OnPaperCombo)
        self.OnPaperCombo(None)

        EVT_TEXT(self, self.widthEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.heightEntry.GetId(), self.OnMisc)
        
        self.cfg2gui()
        
        EVT_TEXT(self, self.topEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.bottomEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.leftEntry.GetId(), self.OnMisc)
        EVT_TEXT(self, self.rightEntry.GetId(), self.OnMisc)

        self.blockEvents = False
        
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
        if self.blockEvents:
            return

        self.entry2float(self.topEntry, "marginTop", 0.0)
        self.entry2float(self.bottomEntry, "marginBottom", 0.0)
        self.entry2float(self.leftEntry, "marginLeft", 0.0)
        self.entry2float(self.rightEntry, "marginRight", 0.0)
        self.entry2float(self.widthEntry, "paperWidth", 100.0)
        self.entry2float(self.heightEntry, "paperHeight", 100.0)
    
    def cfg2gui(self):
        self.topEntry.SetValue(str(self.cfg.marginTop))
        self.bottomEntry.SetValue(str(self.cfg.marginBottom))
        self.leftEntry.SetValue(str(self.cfg.marginLeft))
        self.rightEntry.SetValue(str(self.cfg.marginRight))

    def entry2float(self, entry, name, minVal):
        try:
            val = max(minVal, float(entry.GetValue()))
        except ValueError:
            val = minVal

        setattr(self.cfg, name, val)
        
