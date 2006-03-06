import gutil
import misc
import util

from wxPython.wx import *

class AutoCompletionDlg(wxDialog):
    def __init__(self, parent, autoCompletion):
        wxDialog.__init__(self, parent, -1, "Auto-completion",
                          style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)

        self.autoCompletion = autoCompletion

        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(self, -1, "Element:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.elementsCombo = wxComboBox(self, -1, style = wxCB_READONLY)

        for t in autoCompletion.types.itervalues():
            self.elementsCombo.Append(t.ti.name, t.ti.lt)

        EVT_COMBOBOX(self, self.elementsCombo.GetId(), self.OnElementCombo)

        hsizer.Add(self.elementsCombo, 0)

        vsizer.Add(hsizer, 0, wxEXPAND)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND | wxTOP | wxBOTTOM, 10)

        self.enabledCb = wxCheckBox(self, -1, "Auto-completion enabled")
        EVT_CHECKBOX(self, self.enabledCb.GetId(), self.OnMisc)
        vsizer.Add(self.enabledCb, 0, wxBOTTOM, 10)

        vsizer.Add(wxStaticText(self, -1, "Default items:"))

        self.itemsEntry = wxTextCtrl(self, -1, style = wxTE_MULTILINE |
                                     wxTE_DONTWRAP, size = (400, 200))
        EVT_TEXT(self, self.itemsEntry.GetId(), self.OnMisc)
        vsizer.Add(self.itemsEntry, 1, wxEXPAND)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add((1, 1), 1)
        
        cancelBtn = gutil.createStockButton(self, wxID_CANCEL, "Cancel")
        hsizer.Add(cancelBtn, 0, wxLEFT, 10)
        
        okBtn = gutil.createStockButton(self, wxID_OK, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 10)

        util.finishWindow(self, vsizer)

        self.elementsCombo.SetSelection(0)
        self.OnElementCombo()

        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def OnOK(self, event):
        self.autoCompletion.refresh()
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

    def OnElementCombo(self, event = None):
        self.lt = self.elementsCombo.GetClientData(self.elementsCombo.
                                                     GetSelection()) 
        t = self.autoCompletion.getType(self.lt)
       
        self.enabledCb.SetValue(t.enabled)

        self.itemsEntry.Enable(t.enabled)
        self.itemsEntry.SetValue("\n".join(t.items))
                         
    def OnMisc(self, event = None):
        t = self.autoCompletion.getType(self.lt)

        t.enabled = bool(self.enabledCb.IsChecked())
        self.itemsEntry.Enable(t.enabled)

        # this is cut&pasted from autocompletion.AutoCompletion.refresh,
        # but I don't want to call that since it does all types, this does
        # just the changed one.
        tmp = []
        for v in misc.fromGUI(self.itemsEntry.GetValue()).split("\n"):
            v = util.toInputStr(v).strip()

            if len(v) > 0:
                tmp.append(v)

        t.items = tmp
