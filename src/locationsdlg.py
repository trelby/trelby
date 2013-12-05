import gutil
import locations
import util

import wx

class LocationsDlg(wx.Dialog):
    def __init__(self, parent, sp):
        wx.Dialog.__init__(self, parent, -1, "Locations",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.sp = sp

        vsizer = wx.BoxSizer(wx.VERTICAL)

        tmp = wx.StaticText(self, -1, "Locations:")
        vsizer.Add(tmp)

        self.locationsLb = wx.ListBox(self, -1, size = (450, 200))
        vsizer.Add(self.locationsLb, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.addBtn = gutil.createStockButton(self, "Add")
        hsizer.Add(self.addBtn)
        wx.EVT_BUTTON(self, self.addBtn.GetId(), self.OnAdd)

        self.delBtn = gutil.createStockButton(self, "Delete")
        hsizer.Add(self.delBtn, 0, wx.LEFT, 10)
        wx.EVT_BUTTON(self, self.delBtn.GetId(), self.OnDelete)

        vsizer.Add(hsizer, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        tmp = wx.StaticText(self, -1, "Scenes:")
        vsizer.Add(tmp)

        self.scenesLb = wx.ListBox(self, -1, size = (450, 200),
                                   style = wx.LB_EXTENDED)
        vsizer.Add(self.scenesLb, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.LEFT, 10)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        wx.EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

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

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def OnAdd(self, event):
        selected = self.scenesLb.GetSelections()

        if not selected:
            wx.MessageBox("No scenes selected in the lower list.", "Error",
                          wx.OK, self)

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
            wx.MessageBox("No scene selected in the upper list.", "Error",
                          wx.OK, self)

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

        sceneNames = sorted(self.sp.getSceneNames().keys())

        for scene in sceneNames:
            if scene not in added:
                self.scenesLb.Append(scene, scene)
