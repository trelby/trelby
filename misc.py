from wxPython.wx import *

class MyColorSample(wxWindow):
    def __init__(self, parent, id, size):
        wxWindow.__init__(self, parent, id, size = size)

        EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, event):
        dc = wxPaintDC(self)

        w, h = self.GetClientSizeTuple()
        br = wxBrush(self.GetBackgroundColour())
        dc.SetBrush(br)
        dc.DrawRectangle(0, 0, w, h)

# dialog that shows two lists of script names, allowing user to choose one
# from both. stores indexes of selections in members named 'sel1' and
# 'sel2' when OK is pressed. 'items' must have at least two items.
class ScriptChooserDlg(wxDialog):
    def __init__(self, parent, items):
        wxDialog.__init__(self, parent, -1, "Choose scripts",
                          style = wxDEFAULT_DIALOG_STYLE)

        self.SetClientSizeWH(225, 115);
        self.Center()
        
        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        gsizer = wxFlexGridSizer(2, 2, 5, 0)

        self.addCombo("first", "Compare script", panel, gsizer, items, 0)
        self.addCombo("second", "to", panel, gsizer, items, 1)

        vsizer.Add(gsizer)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(1, 1, 1)
        
        cancelBtn = wxButton(panel, -1, "Cancel")
        hsizer.Add(cancelBtn)
        
        okBtn = wxButton(panel, -1, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 20)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def addCombo(self, name, descr, panel, sizer, items, sel):
        al = wxALIGN_CENTER_VERTICAL | wxRIGHT
        if sel == 1:
            al |= wxALIGN_RIGHT
            
        sizer.Add(wxStaticText(panel, -1, descr), 0, al, 10)
        
        combo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for s in items:
            combo.Append(s)

        combo.SetSelection(sel)
        
        sizer.Add(combo)

        setattr(self, name + "Combo", combo)

    def OnOK(self, event):
        self.sel1 = self.firstCombo.GetSelection()
        self.sel2 = self.secondCombo.GetSelection()
        
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)
