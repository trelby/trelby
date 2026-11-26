import wx

import trelby.config as config
import trelby.gutil as gutil
import trelby.util as util

# what the line list shows
SHOW_ALL = 0
SHOW_REVIEW = 1
SHOW_CHANGED = 2


class _RowList(wx.ListCtrl):
    """Virtual list of the rows being imported."""

    def __init__(self, parent, dlg):
        wx.ListCtrl.__init__(
            self,
            parent,
            -1,
            size=(1000, 420),
            style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.LC_HRULES,
        )

        self.dlg = dlg

        self.InsertColumn(0, _("Line"), wx.LIST_FORMAT_RIGHT, 55)
        self.InsertColumn(1, _("Column"), wx.LIST_FORMAT_RIGHT, 65)
        self.InsertColumn(2, _("Type"), width=120)
        self.InsertColumn(3, _("Text"), width=360)
        self.InsertColumn(4, _("Note"), width=400)

        self.normalAttr = wx.ItemAttr()

        self.reviewAttr = wx.ItemAttr()
        self.reviewAttr.SetBackgroundColour(wx.Colour(255, 230, 140))
        self.reviewAttr.SetTextColour(wx.Colour(0, 0, 0))

        self.removeAttr = wx.ItemAttr()
        self.removeAttr.SetTextColour(wx.Colour(135, 135, 135))

    def OnGetItemText(self, item, col):
        return self.dlg.cellText(self.dlg.shown[item], col)

    def OnGetItemAttr(self, item):
        r = self.dlg.shown[item]

        if r.needsReview():
            return self.reviewAttr

        if r.lt == self.dlg.REMOVE:
            return self.removeAttr

        return self.normalAttr


class TextImportReviewDlg(wx.Dialog):
    """Shows how a text file will be imported, line by line, and lets the
    user correct it before anything is imported. rows is a list of
    myimport.ImportRow objects (and None for empty lines), which are
    modified in place."""

    def __init__(self, parent, rows, layout, REMOVE):
        wx.Dialog.__init__(
            self,
            parent,
            -1,
            _("Review import"),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.REMOVE = REMOVE
        self.rows = [r for r in rows if r is not None]

        self.types = [(ti.lt, ti.name) for ti in config.getTIs()]
        self.types.append((REMOVE, _("Don't import")))
        self.typeNames = dict(self.types)

        # paragraph index of each row, for "Select paragraph"
        self.para = {}
        n = 0
        for r in rows:
            if r is None:
                n += 1
            else:
                self.para[id(r)] = n

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.summary = wx.StaticText(self, -1, "")
        vsizer.Add(self.summary, 0, wx.EXPAND)

        vsizer.Add(wx.StaticText(self, -1, layout), 0, wx.EXPAND | wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(wx.StaticText(self, -1, _("Show:")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.showChoice = wx.Choice(self, -1)
        self.showChoice.Append(_("All lines"))
        self.showChoice.Append(_("Lines to review"))
        self.showChoice.Append(_("Lines not imported or changed"))
        self.showChoice.SetSelection(SHOW_ALL)
        hsizer.Add(self.showChoice, 0, wx.LEFT, 5)
        vsizer.Add(hsizer, 0, wx.TOP, 10)

        self.list = _RowList(self, self)
        vsizer.Add(self.list, 1, wx.EXPAND | wx.TOP, 5)

        # full details of the focused line
        self.details = wx.TextCtrl(
            self, -1, size=(-1, 70), style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        vsizer.Add(self.details, 0, wx.EXPAND | wx.TOP, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(
            wx.StaticText(self, -1, _("Type of selected lines:")),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self.typeChoice = wx.Choice(self, -1)
        for lt, name in self.types:
            self.typeChoice.Append(name, lt)
        hsizer.Add(self.typeChoice, 0, wx.LEFT, 5)

        self.checkedBtn = wx.Button(self, -1, _("Type is right"))
        hsizer.Add(self.checkedBtn, 0, wx.LEFT, 10)

        self.keepCb = wx.CheckBox(self, -1, _("Keep text as written"))
        hsizer.Add(self.keepCb, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 15)

        vsizer.Add(hsizer, 0, wx.TOP, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        nextBtn = wx.Button(self, -1, _("Next to review"))
        hsizer.Add(nextBtn)

        paraBtn = wx.Button(self, -1, _("Select paragraph"))
        hsizer.Add(paraBtn, 0, wx.LEFT, 10)

        indentBtn = wx.Button(self, -1, _("Select same column"))
        hsizer.Add(indentBtn, 0, wx.LEFT, 10)

        hsizer.Add((1, 1), 1)

        cancelBtn = gutil.createStockButton(self, _("Cancel"))
        hsizer.Add(cancelBtn)

        okBtn = wx.Button(self, wx.ID_OK, _("Import"))
        hsizer.Add(okBtn, 0, wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        self.Bind(wx.EVT_CHOICE, self.OnShowChoice, id=self.showChoice.GetId())
        self.Bind(wx.EVT_CHOICE, self.OnTypeChoice, id=self.typeChoice.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnChecked, id=self.checkedBtn.GetId())
        self.Bind(wx.EVT_CHECKBOX, self.OnKeepText, id=self.keepCb.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnNext, id=nextBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnSelectPara, id=paraBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnSelectIndent, id=indentBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelChanged)
        self.list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnSelChanged)
        self.list.Bind(wx.EVT_LIST_ITEM_FOCUSED, self.OnSelChanged)

        self.shown = []
        self.updateShown()
        self.OnNext()

    def cellText(self, r, col):
        if col == 0:
            return str(r.lineNo)

        if col == 1:
            return str(r.indent)

        if col == 2:
            return self.typeNames.get(r.lt, "")

        if col == 3:
            return r.text if r.lt == self.REMOVE else r.finalText()

        notes = []
        if r.flag:
            if r.checked:
                notes.append(_("Checked: {}").format(r.flag))
            else:
                notes.append(_("Check: {}").format(r.flag))

        if r.cleanText is not None and r.keepText:
            notes.append(_("Kept as written."))
        elif r.note and (r.lt == self.REMOVE or r.cleanText is not None):
            notes.append(r.note)

        return " ".join(notes)

    def isChanged(self, r):
        return r.lt == self.REMOVE or (r.cleanText is not None and not r.keepText)

    def updateShown(self):
        """Rebuild the list of shown rows, keeping the selection."""
        sel = self.selectedRows()

        show = self.showChoice.GetSelection()
        if show == SHOW_REVIEW:
            self.shown = [r for r in self.rows if r.flag]
        elif show == SHOW_CHANGED:
            self.shown = [r for r in self.rows if self.isChanged(r) or r.note]
        else:
            self.shown = list(self.rows)

        self.list.SetItemCount(len(self.shown))
        self.selectRows(sel, focus=False)
        self.refresh()

    def refresh(self):
        if self.shown:
            self.list.RefreshItems(0, len(self.shown) - 1)

        review = sum(1 for r in self.rows if r.needsReview())
        removed = sum(1 for r in self.rows if r.lt == self.REMOVE)
        changed = sum(
            1
            for r in self.rows
            if r.lt != self.REMOVE and r.cleanText is not None and not r.keepText
        )

        if review == 1:
            s = _("1 line needs review (highlighted).")
        elif review:
            s = _("{} lines need review (highlighted).").format(review)
        else:
            s = _("No lines need review.")

        s += " " + _("Lines not imported: {}. Lines shortened: {}.").format(
            removed, changed
        )

        self.summary.SetLabel(s)
        self.updateControls()

    def selectedRows(self):
        ret = []
        i = self.list.GetFirstSelected()

        while i != -1:
            ret.append(self.shown[i])
            i = self.list.GetNextSelected(i)

        return ret

    def selectRows(self, rows, focus=True):
        ids = set(id(r) for r in rows)
        first = None

        for i, r in enumerate(self.shown):
            on = id(r) in ids
            self.list.Select(i, on)

            if on and first is None:
                first = i

        if focus and first is not None:
            self.list.Focus(first)
            self.list.EnsureVisible(first)

    def updateDetails(self):
        i = self.list.GetFocusedItem()
        if i < 0 or i >= len(self.shown):
            self.details.SetValue("")
            return

        r = self.shown[i]
        s = _("Line {}, column {}: {}").format(
            r.lineNo, r.indent, self.typeNames.get(r.lt, "")
        )
        s += "\n" + _("As written: {}").format(r.text)

        if r.lt == self.REMOVE:
            s += "\n" + _("Not imported.")
        elif r.finalText() != r.text:
            s += "\n" + _("Imported as: {}").format(r.finalText())

        note = self.cellText(r, 4)
        if note:
            s += "\n" + note

        self.details.SetValue(s)

    def updateControls(self):
        self.updateDetails()

        sel = self.selectedRows()

        lts = set(r.lt for r in sel)
        if len(lts) == 1:
            util.reverseComboSelect(self.typeChoice, lts.pop())
        else:
            self.typeChoice.SetSelection(wx.NOT_FOUND)

        self.typeChoice.Enable(bool(sel))
        self.checkedBtn.Enable(any(r.needsReview() for r in sel))

        cleaned = [r for r in sel if r.cleanText is not None]
        self.keepCb.Enable(bool(cleaned))
        self.keepCb.SetValue(bool(cleaned) and all(r.keepText for r in cleaned))

    def OnSelChanged(self, event):
        event.Skip()

        # GTK sends these while the dialog is being torn down, too
        if not self.list or self.IsBeingDeleted():
            return

        self.updateControls()

    def OnShowChoice(self, event):
        self.updateShown()

    def OnTypeChoice(self, event):
        i = self.typeChoice.GetSelection()
        if i == wx.NOT_FOUND:
            return

        lt = self.typeChoice.GetClientData(i)
        for r in self.selectedRows():
            r.setType(lt)

        self.refresh()

    def OnChecked(self, event):
        for r in self.selectedRows():
            if r.flag:
                r.checked = True

        self.refresh()

    def OnKeepText(self, event):
        for r in self.selectedRows():
            if r.cleanText is not None:
                r.keepText = self.keepCb.GetValue()

        self.refresh()

    def OnNext(self, event=None):
        if not self.shown:
            return

        start = self.list.GetFocusedItem() + 1
        cnt = len(self.shown)

        for k in range(cnt):
            i = (start + k) % cnt
            if self.shown[i].needsReview():
                self.selectRows([self.shown[i]])
                self.updateControls()
                return

    def OnSelectPara(self, event):
        paras = set(self.para[id(r)] for r in self.selectedRows())
        self.selectRows([r for r in self.shown if self.para[id(r)] in paras])
        self.updateControls()

    def OnSelectIndent(self, event):
        indents = set(r.indent for r in self.selectedRows())
        self.selectRows([r for r in self.shown if r.indent in indents])
        self.updateControls()

    def OnOK(self, event):
        review = sum(1 for r in self.rows if r.needsReview())

        if review and (
            wx.MessageBox(
                _(
                    "{} lines still need review. They will be imported with "
                    "the type shown.\n\nImport anyway?"
                ).format(review),
                _("Confirm"),
                wx.YES_NO | wx.NO_DEFAULT,
                self,
            )
            == wx.NO
        ):
            return

        self.EndModal(wx.ID_OK)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
