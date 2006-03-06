import gutil
import misc
import util

from wxPython.wx import *

class SCDictDlg(wxDialog):
    def __init__(self, parent, scDict, isGlobal):
        wxDialog.__init__(self, parent, -1, "Spell checker dictionary",
                          style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)

        self.scDict = scDict

        vsizer = wxBoxSizer(wxVERTICAL)
        
        if isGlobal:
            s = "Global words:"
        else:
            s = "Script-specific words:"
            
        vsizer.Add(wxStaticText(self, -1, s))

        self.itemsEntry = wxTextCtrl(self, -1, style = wxTE_MULTILINE |
                                     wxTE_DONTWRAP, size = (300, 300))
        vsizer.Add(self.itemsEntry, 1, wxEXPAND)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add((1, 1), 1)
        
        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wxLEFT, 10)
        
        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 10)

        self.cfg2gui()

        util.finishWindow(self, vsizer)

        EVT_TEXT(self, self.itemsEntry.GetId(), self.OnMisc)
        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

    def OnOK(self, event):
        self.scDict.refresh()
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

    def OnMisc(self, event):
        self.scDict.set(misc.fromGUI(self.itemsEntry.GetValue()).split("\n"))

    def cfg2gui(self):
        self.itemsEntry.SetValue("\n".join(self.scDict.get()))
