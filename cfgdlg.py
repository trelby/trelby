import config
import util
from wxPython.wx import *

class CfgDlg(wxDialog):
    def __init__(self, parent, cfg):
        wxDialog.__init__(self, parent, -1, "Config dialog",
                          pos = wxDefaultPosition,
                          size = (400, 400),
                          style = wxDEFAULT_DIALOG_STYLE)
        self.cfg = cfg

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        self.notebook = wxNotebook(self, -1, style = wxCLIP_CHILDREN)
        vsizer.Add(self.notebook, 1, wxEXPAND)

        p = FontPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Font")

        p = ElementsPanel(self.notebook, -1, cfg)
        self.notebook.AddPage(p, "Elements")

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(1, 1, 1)
        
        cancel = wxButton(self, -1, "Cancel")
        hsizer.Add(cancel, 0, wxALL, 5)
        
        ok = wxButton(self, -1, "OK")
        hsizer.Add(ok, 0, wxALL, 5)

        vsizer.Add(hsizer, 0, wxEXPAND)

        EVT_BUTTON(self, cancel.GetId(), self.OnCancel)
        EVT_BUTTON(self, ok.GetId(), self.OnOK)
        
        self.Layout()
        
    def OnOK(self, event):
        self.EndModal(wxID_OK)

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

        for t in cfg.types.values():
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

        vsizer.Add(gsizer, 0, 0)
        
        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

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
