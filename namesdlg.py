import misc
import namearray
import util
import random
from wxPython.wx import *

class NamesDlg(wxDialog):
    def __init__(self, parent, nameArr):
        wxDialog.__init__(self, parent, -1, "Character name database",
                          pos = wxDefaultPosition,
                          size = (530, 500),
                          style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)

        self.nameArr = nameArr
        
        self.Center()

        panel = wxPanel(self, -1)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        panel.SetSizer(hsizer)

        vsizer = wxBoxSizer(wxVERTICAL)

        vsizer.Add(wxStaticText(panel, -1, "Search in:"))

        self.typeList = wxListCtrl(panel, -1,
            style = wxLC_REPORT | wxLC_HRULES | wxLC_VRULES)

        self.typeList.InsertColumn(0, "Count")
        self.typeList.InsertColumn(1, "Type")
        self.typeList.SetColumnWidth(0, 50)
        self.typeList.SetColumnWidth(1, 110)

        for i in xrange(len(self.nameArr.typeNames)):
            self.typeList.InsertStringItem(i, str(self.nameArr.typeFreqs[i]))
            self.typeList.SetStringItem(i, 1, self.nameArr.typeNames[i])
            self.typeList.SetItemData(i, i)

        self.typeList.SortItems(self.CmpFreq)
        self.selectAllTypes()
        vsizer.Add(self.typeList, 1, wxEXPAND | wxBOTTOM, 5)

        selectAllBtn = wxButton(panel, -1, "Select all")
        vsizer.Add(selectAllBtn)

        hsizer.Add(vsizer, 10, wxEXPAND)

        vsizer = wxBoxSizer(wxVERTICAL)
        
        hsizer2 = wxBoxSizer(wxHORIZONTAL)
        
        vsizer2 = wxBoxSizer(wxVERTICAL)
        
        searchBtn = wxButton(panel, -1, "Search")
        vsizer2.Add(searchBtn, 0, wxBOTTOM | wxTOP, 10)

        self.searchEntry = wxTextCtrl(panel, -1, style = wxTE_PROCESS_ENTER)
        vsizer2.Add(self.searchEntry)

        hsizer2.Add(vsizer2, 0, wxRIGHT, 10)

        self.nameRb = wxRadioBox(panel, -1, "Name",
            style = wxRA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "begins with", "contains", "ends in" ])
        hsizer2.Add(self.nameRb)

        self.sexRb = wxRadioBox(panel, -1, "Sex",
            style = wxRA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "Male", "Female", "Both" ])
        self.sexRb.SetSelection(2)
        hsizer2.Add(self.sexRb, 0, wxLEFT, 5)
        
        vsizer.Add(hsizer2, 0, wxALIGN_CENTER)

        vsizer.Add(wxStaticText(panel, -1, "Results:"))
        
        self.list = MyListCtrl(panel, nameArr)
        vsizer.Add(self.list, 1, wxEXPAND | wxBOTTOM, 5)

        self.foundLabel = wxStaticText(panel, -1, "",
            style = wxALIGN_CENTRE | wxST_NO_AUTORESIZE)
        vsizer.Add(self.foundLabel, 0, wxEXPAND)

        hsizer.Add(vsizer, 20, wxEXPAND | wxLEFT, 10)

        EVT_TEXT_ENTER(self, self.searchEntry.GetId(), self.OnSearch)
        EVT_BUTTON(self, searchBtn.GetId(), self.OnSearch)
        EVT_BUTTON(self, selectAllBtn.GetId(), self.selectAllTypes)
        EVT_LIST_COL_CLICK(self, self.typeList.GetId(), self.OnHeaderClick)
        
        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)

        self.SetSizer(vmsizer)
        self.Layout()

        self.OnSearch()
        self.searchEntry.SetFocus()

    def selectAllTypes(self, event = None):
        for i in xrange(len(self.nameArr.typeNames)):
            self.typeList.SetItemState(i, wxLIST_STATE_SELECTED,
                                       wxLIST_STATE_SELECTED)
        
    def OnHeaderClick(self, event):
        if event.GetColumn() == 0:
            self.typeList.SortItems(self.CmpFreq)
        else:
            self.typeList.SortItems(self.CmpType)

    def CmpFreq(self, i1, i2):
        return self.nameArr.typeFreqs[i2] - self.nameArr.typeFreqs[i1]
    
    def CmpType(self, i1, i2):
        return cmp(self.nameArr.typeNames[i1], self.nameArr.typeNames[i2])
    
    def OnSearch(self, event = None):
        l = []

        wxBeginBusyCursor()
        
        s = util.lower(self.searchEntry.GetValue())
        sex = self.sexRb.GetSelection()
        nt = self.nameRb.GetSelection()

        selTypes = {}
        skipped = 0
        item = -1
        isEval = misc.isEval
        
        while 1:
            item = self.typeList.GetNextItem(item, wxLIST_NEXT_ALL,
                wxLIST_STATE_SELECTED)

            if item == -1:
                break

            selTypes[self.typeList.GetItemData(item)] = True

        if len(selTypes) == len(self.nameArr.typeNames):
            doTypes = False
        else:
            doTypes = True

        for i in xrange(self.nameArr.count):
            if (sex != 2) and (sex == self.nameArr.sex[i]):
                continue

            if doTypes and self.nameArr.type[i] not in selTypes:
                continue
            
            if s:
                name = util.lower(self.nameArr.name[i])
                
                if nt == 0:
                    if not name.startswith(s):
                        continue
                elif nt == 1:
                    if name.find(s) == -1:
                        continue
                elif nt == 2:
                    if not name.endswith(s):
                        continue

            if isEval and (random.random() > 0.1):
                skipped += 1
                continue
            
            l.append(i)

        self.list.items = l
        self.list.SetItemCount(len(l))
        self.list.EnsureVisible(0)

        wxEndBusyCursor()

        self.foundLabel.SetLabel("%d names found." % len(l))
        
        if skipped > 0:
            wxMessageBox(
                "Found %d additional names that are not included\n"
                "in the results because this is an evaluation version."
                % skipped, "Evaluation notice", wxOK, self)

class MyListCtrl(wxListCtrl):
    def __init__(self, parent, nameArr):
        wxListCtrl.__init__(self, parent, -1,
            style = wxLC_REPORT | wxLC_VIRTUAL | wxLC_HRULES | wxLC_VRULES)

        self.nameArr = nameArr

        self.sex = ["Female", "Male"]
        
        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Type")
        self.InsertColumn(2, "Sex")
        self.SetColumnWidth(0, 120)
        self.SetColumnWidth(1, 120)
        self.SetColumnWidth(2, 50)

    def OnGetItemText(self, item, col):
        n = self.items[item]
        
        if col == 0:
            return self.nameArr.name[n]
        elif col == 1:
            return self.nameArr.typeNames[self.nameArr.type[n]]
        elif col == 2:
            return self.sex[self.nameArr.sex[n]]

        # shouldn't happen
        return ""
    
    # for some reason this must be overridden as well, otherwise we get
    # assert failures under windows.
    def OnGetItemImage(self, item):
        return -1
