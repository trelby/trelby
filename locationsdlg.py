import gutil
import locations
import util

from wxPython.wx import *

class LocationsDlg(wxDialog):
    def __init__(self, parent, sp):
        wxDialog.__init__(self, parent, -1, "Locations",
                          style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)

        self.sp = sp

        vsizer = wxBoxSizer(wxVERTICAL)

        tmp = wxStaticText(self, -1, "Locations:")
        vsizer.Add(tmp)
        
        self.locationsLb = wxListBox(self, -1, size = (450, 200))
        vsizer.Add(self.locationsLb, 1, wxEXPAND)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.addBtn = wxButton(self, -1, "Add")
        hsizer.Add(self.addBtn)
        EVT_BUTTON(self, self.addBtn.GetId(), self.OnAdd)

        self.delBtn = wxButton(self, -1, "Delete")
        hsizer.Add(self.delBtn, 0, wxLEFT, 10)
        EVT_BUTTON(self, self.delBtn.GetId(), self.OnDelete)

        vsizer.Add(hsizer, 0, wxALIGN_CENTER | wxTOP, 10)

        tmp = wxStaticText(self, -1, "Scenes:")
        vsizer.Add(tmp)
        
        self.scenesLb = wxListBox(self, -1, size = (450, 200),
                                  style = wxLB_EXTENDED)
        vsizer.Add(self.scenesLb, 1, wxEXPAND)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(1, 1, 1)
        
        cancelBtn = wxButton(self, -1, "Cancel")
        hsizer.Add(cancelBtn, 0, wxLEFT, 10)
        
        okBtn = wxButton(self, -1, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 10)

        util.finishWindow(self, vsizer)

        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        self.fillGui()

    def OnOK(self, event):
        # master list
        ml = []

        # sub-list
        sl = []
        
        for i in range(self.locationsLb.GetCount()):
            scene = self.locationsLb.GetClientData(i)

            if scene:
                sl.append(scene)
            elif sl:
                ml.append(sl)
                sl = []

        self.sp.locations.locations = ml
        self.sp.locations.refresh(self.sp.getSceneNames())
        
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

    def OnAdd(self, event):
        selected = self.scenesLb.GetSelections()

        if not selected:
            wxMessageBox("No scenes selected in the lower list.", "Error",
                         wxOK, self)

            return

        locIdx = self.locationsLb.GetSelection()

        # if user has selected a separator line, treat it as no selection
        if (locIdx != -1) and\
               (self.locationsLb.GetClientData(locIdx) == None):
            locIdx = -1

        addSep = False
        
        for idx in selected:
            scene = self.scenesLb.GetClientData(idx)

            # insert at selected position, or at the bottom if a new group
            if locIdx != -1:
                self.locationsLb.InsertItems([scene], locIdx)
                self.locationsLb.SetClientData(locIdx, scene)
                gutil.listBoxSelect(self.locationsLb, locIdx)
            else:
                addSep = True
                self.locationsLb.Append(scene, scene)
                locIdx = self.locationsLb.GetCount() - 1
                gutil.listBoxSelect(self.locationsLb, locIdx)

        if addSep:
            self.locationsLb.Append("-" * 40, None)

        # we need these to be in sorted order, which they probably are,
        # but wxwidgets documentation doesn't say that, so to be safe we
        # sort it ourselves. and as tuples can't be sorted, we change it
        # to a list first.
        selected = [it for it in selected]
        selected.sort()

        for i in range(len(selected)):
            self.scenesLb.Delete(selected[i] - i)

    def OnDelete(self, event):
        scene = None
        idx = self.locationsLb.GetSelection()

        if idx != -1:
            scene = self.locationsLb.GetClientData(idx)

        if scene == None:
            wxMessageBox("No scene selected in the upper list.", "Error",
                         wxOK, self)

            return

        gutil.listBoxAdd(self.scenesLb, scene, scene)
        self.locationsLb.Delete(idx)

        # was the last item we looked at a separator
        lastWasSep = False

        # go through locations, remove first encountered double separator
        # (appears when a location group is deleted completely)
        for i in range(self.locationsLb.GetCount()):
            cdata = self.locationsLb.GetClientData(i)

            if lastWasSep and (cdata == None):
                self.locationsLb.Delete(i)

                break

            lastWasSep = cdata == None

        # if it goes completely empty, remove the single separator line
        if (self.locationsLb.GetCount() == 1) and\
           (self.locationsLb.GetClientData(0) == None):
            self.locationsLb.Delete(0)

    def fillGui(self):
        self.sp.locations.refresh(self.sp.getSceneNames())

        separator = "-" * 40
        added = {}
        
        for locList in self.sp.locations.locations:
            for scene in locList:
                self.locationsLb.Append(scene, scene)
                added[scene] = None

            self.locationsLb.Append(separator, None)

        # PY2.4: use sorted
        sceneNames = self.sp.getSceneNames().keys()
        sceneNames.sort()
        
        for scene in sceneNames:
            if scene not in added:
                self.scenesLb.Append(scene, scene)
