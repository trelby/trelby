import config
import util
from wxPython.wx import *

class FindDlg(wxDialog):
    def __init__(self, parent):
        wxDialog.__init__(self, parent, -1, "Find & Replace",
                          pos = wxDefaultPosition,
                          size = (400, 135),
                          style = wxDEFAULT_DIALOG_STYLE | wxWANTS_CHARS)

        self.Center()

        panel = wxPanel(self, -1)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        panel.SetSizer(hsizer)

        vsizer = wxBoxSizer(wxVERTICAL)
        
        gsizer = wxFlexGridSizer(2, 2, 5, 20)
        gsizer.AddGrowableCol(1)
        
        gsizer.Add(wxStaticText(panel, -1, "Find what:"))
        self.findEntry = wxTextCtrl(panel, -1)
        gsizer.Add(self.findEntry, 0, wxEXPAND)

        gsizer.Add(wxStaticText(panel, -1, "Replace with:"))
        self.replaceEntry = wxTextCtrl(panel, -1)
        gsizer.Add(self.replaceEntry, 0, wxEXPAND)
        
        vsizer.Add(gsizer, 0, wxEXPAND | wxBOTTOM, 10)

        hsizer2 = wxBoxSizer(wxHORIZONTAL)

        vsizer2 = wxBoxSizer(wxVERTICAL)

        self.matchWhole = wxCheckBox(panel, -1, "Match whole word only")
        vsizer2.Add(self.matchWhole)

        self.matchCase = wxCheckBox(panel, -1, "Match case")
        vsizer2.Add(self.matchCase)

        hsizer2.Add(vsizer2, 0, wxEXPAND)

        self.direction = wxRadioBox(panel, -1, "Direction",
                                    choices = ["Up", "Down"])

        hsizer2.Add(self.direction, 1, 0)
        
        vsizer.Add(hsizer2, 1, wxEXPAND)

        hsizer.Add(vsizer, 1, wxEXPAND)
        
        vsizer = wxBoxSizer(wxVERTICAL)
        
        find = wxButton(panel, -1, "&Find next")
        vsizer.Add(find, 0, wxBOTTOM, 5)

        replace = wxButton(panel, -1, "&Replace")
        vsizer.Add(replace, 0, wxBOTTOM, 5)
        
        replaceAll = wxButton(panel, -1, "Replace &all")
        vsizer.Add(replaceAll, 0, wxBOTTOM, 5)

        hsizer.Add(vsizer, 0, wxEXPAND | wxLEFT, 30)

        EVT_BUTTON(self, find.GetId(), self.OnFind)
        EVT_BUTTON(self, replace.GetId(), self.OnReplace)
        EVT_BUTTON(self, replaceAll.GetId(), self.OnReplaceAll)

        EVT_CHAR(panel, self.OnCharMisc)
        EVT_CHAR(self.findEntry, self.OnCharEntry)
        EVT_CHAR(self.replaceEntry, self.OnCharEntry)
        EVT_CHAR(find, self.OnCharButton)
        EVT_CHAR(replace, self.OnCharButton)
        EVT_CHAR(replaceAll, self.OnCharButton)
        EVT_CHAR(self.matchWhole, self.OnCharButton)
        EVT_CHAR(self.matchCase, self.OnCharButton)
        EVT_CHAR(self.direction, self.OnCharButton)
        
        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)
        self.Layout()
        
        self.findEntry.SetFocus()

    def OnCharEntry(self, event):
        self.OnChar(event, True, False)

    def OnCharButton(self, event):
        self.OnChar(event, False, True)

    def OnCharMisc(self, event):
        self.OnChar(event, False, False)

    def OnChar(self, event, isEntry, isButton):
        kc = event.GetKeyCode()

        if kc == WXK_ESCAPE:
            self.EndModal(wxID_OK)
            return

        if kc == WXK_RETURN:
            if isButton:
                event.Skip()
                return
            else:
                self.OnFind()
                return
            
        if isEntry:
            event.Skip()
        else:
            if kc < 256:
                if chr(kc) == "f":
                    self.OnFind()
                elif chr(kc) == "r":
                    self.OnReplace()
                elif chr(kc) == "a":
                    self.OnReplaceAll()
                else:
                    event.Skip()
            else:
                event.Skip()
                    
        
    def OnFind(self, event = None):
        print "find"
            
    def OnReplace(self, event = None):
        print "replace"
            
    def OnReplaceAll(self, event = None):
        print "replace all"
