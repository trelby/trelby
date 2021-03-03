import misc
import namearray
import util

import wx

# NameArray, or None if not loaded
nameArr = None

# if not already loaded, read the name database from disk and store it.
# returns False on errors.
def readNames(frame):
    global nameArr

    if nameArr:
        # already loaded
        return True

    try:
        data = util.loadMaybeCompressedFile("names.txt", frame)
        if not data:
            return False

        res = namearray.NameArray()
        nameType = None

        for line in data.splitlines():
            ch = line[0]
            if ch == "#":
                continue
            elif ch == "N":
                nameType = line[1:]
            elif ch in ("M", "F"):
                if not nameType:
                    raise Exception("No name type set before line: '%s'" % line)
                res.append(line[1:], nameType, ch)
            else:
                raise Exception("Unknown linetype for line: '%s'" % line)

        nameArr = res

        return True

    except Exception as e:
        wx.MessageBox("Error loading name database: %s" % str(e),
                      "Error", wx.OK, frame)


        return False

class NamesDlg(wx.Dialog):
    def __init__(self, parent, ctrl):
        wx.Dialog.__init__(self, parent, -1, "Character name database",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.ctrl = ctrl

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Search in:"))

        self.typeList = wx.ListCtrl(self, -1,
            style = wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)

        self.typeList.InsertColumn(0, "Count")
        self.typeList.InsertColumn(1, "Type")

        for i in range(len(nameArr.typeNamesById)):
            typeName = nameArr.typeNamesById[i]

            self.typeList.InsertItem(i, str(nameArr.typeNamesCnt[typeName]))
            self.typeList.SetItem(i, 1, typeName)
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
        self.Bind(wx.EVT_BUTTON, self.OnSearch, id=searchBtn.GetId())
        vsizer2.Add(searchBtn, 0, wx.BOTTOM | wx.TOP, 10)

        self.searchEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        vsizer2.Add(self.searchEntry, 0, wx.EXPAND)

        tmp = wx.Button(self, -1, "Insert")
        self.Bind(wx.EVT_BUTTON, self.OnInsertName, id=tmp.GetId())
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

        self.list = MyListCtrl(self)
        vsizer.Add(self.list, 1, wx.EXPAND | wx.BOTTOM, 5)

        self.foundLabel = wx.StaticText(self, -1, "",
            style = wx.ALIGN_CENTRE | wx.ST_NO_AUTORESIZE)
        vsizer.Add(self.foundLabel, 0, wx.EXPAND)

        hsizer.Add(vsizer, 20, wx.EXPAND | wx.LEFT, 10)

        self.Bind(wx.EVT_TEXT_ENTER, self.OnSearch, id=self.searchEntry.GetId())
        self.Bind(wx.EVT_BUTTON, self.selectAllTypes, id=selectAllBtn.GetId())
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnHeaderClick, id=self.typeList.GetId())

        util.finishWindow(self, hsizer)

        self.OnSearch()
        self.searchEntry.SetFocus()

    def selectAllTypes(self, event = None):
        for i in range(len(nameArr.typeNamesById)):
            self.typeList.SetItemState(i, wx.LIST_STATE_SELECTED,
                                       wx.LIST_STATE_SELECTED)

    def OnHeaderClick(self, event):
        if event.GetColumn() == 0:
            self.typeList.SortItems(self.CmpFreq)
        else:
            self.typeList.SortItems(self.CmpType)

    def CmpFreq(self, i1, i2):
        return nameArr.typeNamesCnt[nameArr.typeNamesById[i2]] - nameArr.typeNamesCnt[nameArr.typeNamesById[i1]]

    def cmpfunc(a, b):
        return (a > b) - (a < b)

    def CmpType(self, i1, i2):
        return util.cmpfunc(nameArr.typeNamesById[i1], nameArr.typeNamesById[i2])

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

        s = str(util.lower(misc.fromGUI(self.searchEntry.GetValue())))
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

        if len(selTypes) == len(nameArr.typeNamesCnt):
            doTypes = False
        else:
            doTypes = True

        for i in range(nameArr.count):
            if (sex != 2) and (sex == nameArr.sex[i]):
                continue

            if doTypes and nameArr.type[i] not in selTypes:
                continue

            if s:
                name = util.lower(nameArr.name[i])

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
        if self.list.GetItemCount() > 0:
            self.list.EnsureVisible(0)

        wx.EndBusyCursor()

        self.foundLabel.SetLabel("%d names found." % len(l))

class MyListCtrl(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, -1,
            style = wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_SINGLE_SEL |
                    wx.LC_HRULES | wx.LC_VRULES)

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
            return nameArr.name[n]
        elif col == 1:
            return nameArr.typeNamesById[nameArr.type[n]]
        elif col == 2:
            return self.sex[nameArr.sex[n]]

        # shouldn't happen
        return ""

    # for some reason this must be overridden as well, otherwise we get
    # assert failures under windows.
    def OnGetItemImage(self, item):
        return -1
