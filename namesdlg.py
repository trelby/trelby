import misc
import namearray
import util

import wx

class NamesDlg(wx.Dialog):
    def __init__(self, parent, ctrl, nameArr):
        wx.Dialog.__init__(self, parent, -1, "Character name database",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.ctrl = ctrl
        self.nameArr = nameArr
        
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Search in:"))

        self.typeList = wx.ListCtrl(self, -1,
            style = wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)
        
        self.typeList.InsertColumn(0, "Count")
        self.typeList.InsertColumn(1, "Type")

        for i in xrange(len(self.nameArr.typeNames)):
            self.typeList.InsertStringItem(i, str(self.nameArr.typeFreqs[i]))
            self.typeList.SetStringItem(i, 1, self.nameArr.typeNames[i])
            self.typeList.SetItemData(i, i)

        self.typeList.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.typeList.SetColumnWidth(1, wx.LIST_AUTOSIZE)

        w = 0
        w += self.typeList.GetColumnWidth(0)
        w += self.typeList.GetColumnWidth(1)

        util.setWH(self.typeList, w + 15, 425)
        
        self.typeList.SortItems(self.CmpFreq)
        self.selectAllTypes()
        vsizer.Add(self.typeList, 1, wx.EXPAND | wx.BOTTOM, 5)

        selectAllBtn = wx.Button(self, -1, "Select all")
        vsizer.Add(selectAllBtn)

        hsizer.Add(vsizer, 0, wx.EXPAND)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        
        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        
        vsizer2 = wx.BoxSizer(wx.VERTICAL)
        
        searchBtn = wx.Button(self, -1, "Search")
        wx.EVT_BUTTON(self, searchBtn.GetId(), self.OnSearch)
        vsizer2.Add(searchBtn, 0, wx.BOTTOM | wx.TOP, 10)

        self.searchEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        vsizer2.Add(self.searchEntry, 0, wx.EXPAND)

        tmp = wx.Button(self, -1, "Insert")
        wx.EVT_BUTTON(self, tmp.GetId(), self.OnInsertName)
        vsizer2.Add(tmp, 0, wx.BOTTOM | wx.TOP, 10)

        hsizer2.Add(vsizer2, 1, wx.RIGHT, 10)

        self.nameRb = wx.RadioBox(self, -1, "Name",
            style = wx.RA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "begins with", "contains", "ends in" ])
        hsizer2.Add(self.nameRb)

        self.sexRb = wx.RadioBox(self, -1, "Sex",
            style = wx.RA_SPECIFY_COLS, majorDimension = 1,
            choices = [ "Male", "Female", "Both" ])
        self.sexRb.SetSelection(2)
        hsizer2.Add(self.sexRb, 0, wx.LEFT, 5)
        
        vsizer.Add(hsizer2, 0, wx.EXPAND | wx.ALIGN_CENTER)

        vsizer.Add(wx.StaticText(self, -1, "Results:"))
        
        self.list = MyListCtrl(self, nameArr)
        vsizer.Add(self.list, 1, wx.EXPAND | wx.BOTTOM, 5)

        self.foundLabel = wx.StaticText(self, -1, "",
            style = wx.ALIGN_CENTRE | wx.ST_NO_AUTORESIZE)
        vsizer.Add(self.foundLabel, 0, wx.EXPAND)

        hsizer.Add(vsizer, 20, wx.EXPAND | wx.LEFT, 10)

        wx.EVT_TEXT_ENTER(self, self.searchEntry.GetId(), self.OnSearch)
        wx.EVT_BUTTON(self, selectAllBtn.GetId(), self.selectAllTypes)
        wx.EVT_LIST_COL_CLICK(self, self.typeList.GetId(), self.OnHeaderClick)

        util.finishWindow(self, hsizer)

        self.OnSearch()
        self.searchEntry.SetFocus()

    def selectAllTypes(self, event = None):
        for i in xrange(len(self.nameArr.typeNames)):
            self.typeList.SetItemState(i, wx.LIST_STATE_SELECTED,
                                       wx.LIST_STATE_SELECTED)
        
    def OnHeaderClick(self, event):
        if event.GetColumn() == 0:
            self.typeList.SortItems(self.CmpFreq)
        else:
            self.typeList.SortItems(self.CmpType)

    def CmpFreq(self, i1, i2):
        return self.nameArr.typeFreqs[i2] - self.nameArr.typeFreqs[i1]
    
    def CmpType(self, i1, i2):
        return cmp(self.nameArr.typeNames[i1], self.nameArr.typeNames[i2])

    def OnInsertName(self, event):
        item = self.list.GetNextItem(-1, wx.LIST_NEXT_ALL,
                                     wx.LIST_STATE_SELECTED)

        if item == -1:
            return

        # this seems to return column 0's text, which is lucky, because I
        # don't see a way of getting other columns' texts...
        name = self.list.GetItemText(item)

        for ch in name:
            self.ctrl.OnKeyChar(util.MyKeyEvent(ord(ch)))

    def OnSearch(self, event = None):
        l = []

        wx.BeginBusyCursor()
        
        s = util.lower(misc.fromGUI(self.searchEntry.GetValue()))
        sex = self.sexRb.GetSelection()
        nt = self.nameRb.GetSelection()

        selTypes = {}
        item = -1
        
        while 1:
            item = self.typeList.GetNextItem(item, wx.LIST_NEXT_ALL,
                wx.LIST_STATE_SELECTED)

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

            l.append(i)

        self.list.items = l
        self.list.SetItemCount(len(l))
        self.list.EnsureVisible(0)

        wx.EndBusyCursor()

        self.foundLabel.SetLabel("%d names found." % len(l))

class MyListCtrl(wx.ListCtrl):
    def __init__(self, parent, nameArr):
        wx.ListCtrl.__init__(self, parent, -1,
            style = wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL |
                    wx.LC_HRULES | wx.LC_VRULES)

        self.nameArr = nameArr

        self.sex = ["Female", "Male"]
        
        self.InsertColumn(0, "Name")
        self.InsertColumn(1, "Type")
        self.InsertColumn(2, "Sex")
        self.SetColumnWidth(0, 120)
        self.SetColumnWidth(1, 120)

        # we can't use wx.LIST_AUTOSIZE since this is a virtual control,
        # so calculate the size ourselves since we know the longest string
        # possible.
        w = util.getTextExtent(self.GetFont(), "Female")[0] + 15
        self.SetColumnWidth(2, w)

        util.setWH(self, w = 120*2 + w + 25)

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
