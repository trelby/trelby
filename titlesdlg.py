import misc
import pdf
import pml
import titles
import util

import copy

from wxPython.wx import *

class TitlesDlg(wxDialog):
    def __init__(self, parent, titles, cfg):
        wxDialog.__init__(self, parent, -1, "Title pages",
                          style = wxDEFAULT_DIALOG_STYLE)

        self.titles = titles
        self.cfg = cfg

        # whether some events are blocked
        self.block = False
        
        self.setPage(0)

        h = 540
        if misc.isWindows:
            h = 530

        self.SetClientSizeWH(400, h);
        self.Center()
        
        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        self.pageLabel = wxStaticText(panel, -1, "")
        vsizer.Add(self.pageLabel, 0, wxADJUST_MINSIZE)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        tmp = wxButton(panel, -1, "Add")
        hsizer.Add(tmp)
        EVT_BUTTON(self, tmp.GetId(), self.OnAddPage)

        self.delPageBtn = wxButton(panel, -1, "Delete")
        hsizer.Add(self.delPageBtn, 0, wxLEFT, 10)
        EVT_BUTTON(self, self.delPageBtn.GetId(), self.OnDeletePage)

        self.moveBtn = wxButton(panel, -1, "Move")
        hsizer.Add(self.moveBtn, 0, wxLEFT, 10)
        EVT_BUTTON(self, self.moveBtn.GetId(), self.OnMovePage)

        self.nextBtn = wxButton(panel, -1, "Next")
        hsizer.Add(self.nextBtn, 0, wxLEFT, 10)
        EVT_BUTTON(self, self.nextBtn.GetId(), self.OnNextPage)

        vsizer.Add(hsizer, 0, wxTOP, 5)
        
        vsizer.Add(wxStaticLine(panel, -1), 0, wxEXPAND | wxTOP | wxBOTTOM,
                   10)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)

        vsizer2 = wxBoxSizer(wxVERTICAL)
        
        tmp = wxStaticText(panel, -1, "Strings:")
        vsizer2.Add(tmp)
        
        self.stringsLb = wxListBox(panel, -1, size = (200, 200))
        vsizer2.Add(self.stringsLb)

        hsizer2 = wxBoxSizer(wxHORIZONTAL)
        
        self.addBtn = wxButton(panel, -1, "Add")
        hsizer2.Add(self.addBtn)
        EVT_BUTTON(self, self.addBtn.GetId(), self.OnAddString)

        self.delBtn = wxButton(panel, -1, "Delete")
        hsizer2.Add(self.delBtn, 0, wxLEFT, 10)
        EVT_BUTTON(self, self.delBtn.GetId(), self.OnDeleteString)

        vsizer2.Add(hsizer2, 0, wxTOP, 5)

        hsizer.Add(vsizer2)
        
        self.previewCtrl = TitlesPreview(panel, self, self.cfg)
        hsizer.Add(self.previewCtrl, 1, wxEXPAND | wxLEFT, 10)
        
        vsizer.Add(hsizer, 0, wxEXPAND)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(panel, -1, "Text:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.textEntry = wxTextCtrl(panel, -1)
        hsizer.Add(self.textEntry, 1, wxLEFT, 10)
        EVT_TEXT(self, self.textEntry.GetId(), self.OnMisc)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 20)

        hsizerTop = wxBoxSizer(wxHORIZONTAL)

        vsizer2 = wxBoxSizer(wxVERTICAL)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(panel, -1, "X-Pos (mm):"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.xEntry = wxTextCtrl(panel, -1)
        hsizer.Add(self.xEntry, 0, wxLEFT, 10)
        EVT_TEXT(self, self.xEntry.GetId(), self.OnMisc)

        vsizer2.Add(hsizer, 0, wxTOP, 5)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(panel, -1, "Y-Pos (mm):"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.yEntry = wxTextCtrl(panel, -1)
        hsizer.Add(self.yEntry, 0, wxLEFT, 10)
        EVT_TEXT(self, self.yEntry.GetId(), self.OnMisc)

        vsizer2.Add(hsizer, 0, wxTOP, 5)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(panel, -1, "Font:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.fontCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for it in [ ("Courier", pml.COURIER), ("Helvetica", pml.HELVETICA),
                    ("Times-Roman", pml.TIMES_ROMAN) ]:
            self.fontCombo.Append(it[0], it[1])

        hsizer.Add(self.fontCombo, 0, wxLEFT, 10)
        EVT_COMBOBOX(self, self.fontCombo.GetId(), self.OnMisc)

        vsizer2.Add(hsizer, 0, wxTOP, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(panel, -1, "Size:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        
        self.sizeEntry = wxSpinCtrl(panel, -1)
        self.sizeEntry.SetRange(4, 288)
        EVT_SPINCTRL(self, self.sizeEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.sizeEntry, self.OnKillFocus)
        hsizer.Add(self.sizeEntry, 0, wxLEFT, 10)

        vsizer2.Add(hsizer, 0, wxTOP, 5)

        hsizerTop.Add(vsizer2)
        
        bsizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Style"),
                                  wxHORIZONTAL)

        vsizer2 = wxBoxSizer(wxVERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5
        
        self.addCheckBox("Centered", panel, vsizer2, pad)
        self.addCheckBox("Bold", panel, vsizer2, pad)
        self.addCheckBox("Italic", panel, vsizer2, pad)
        self.addCheckBox("Underlined", panel, vsizer2, pad)
            
        bsizer.Add(vsizer2)

        hsizerTop.Add(bsizer, 0, wxLEFT, 20)

        vsizer.Add(hsizerTop, 0, wxTOP, 10)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(1, 1, 1)
        
        self.previewBtn = wxButton(panel, -1, "Preview")
        hsizer.Add(self.previewBtn)

        cancelBtn = wxButton(panel, -1, "Cancel")
        hsizer.Add(cancelBtn, 0, wxLEFT, 10)
        
        okBtn = wxButton(panel, -1, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 20)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        EVT_BUTTON(self, self.previewBtn.GetId(), self.OnPreview)
        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        EVT_LISTBOX(self, self.stringsLb.GetId(), self.OnStringsLb)

        # list of widgets that are specific to editing the selected string
        self.widList = [ self.textEntry, self.xEntry, self.centeredCb,
                         self.yEntry, self.fontCombo, self.sizeEntry,
                         self.boldCb, self.italicCb, self.underlinedCb ]
        
        self.updateGui()

        self.textEntry.SetFocus()

    def addCheckBox(self, name, panel, sizer, pad):
        cb = wxCheckBox(panel, -1, name)
        EVT_CHECKBOX(self, cb.GetId(), self.OnMisc)
        sizer.Add(cb, 0, wxTOP, pad)
        setattr(self, name.lower() + "Cb", cb)
        
    def OnOK(self, event):
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

    def OnPreview(self, event):
        doc = pml.Document(self.cfg.paperWidth, self.cfg.paperHeight,
                           self.cfg.paperType)

        self.titles.generatePages(doc)
        tmp = pdf.generate(doc)
        util.showTempPDF(tmp, self.cfg, self)

    # set given page. 'page' can be an invalid value.
    def setPage(self, page):
        # selected page index or -1
        self.pageIndex = -1

        if self.titles.pages:
            self.pageIndex = 0

            if (page >= 0) and (len(self.titles.pages) > page):
                self.pageIndex = page

        # selected string index or -1
        self.tsIndex = -1

        if self.pageIndex == -1:
            return
        
        if len(self.titles.pages[self.pageIndex]) > 0:
            self.tsIndex = 0

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnStringsLb(self, event = None):
        self.tsIndex = self.stringsLb.GetSelection()
        self.updateStringGui()

    def OnAddPage(self, event):
        self.titles.pages.append([])
        self.setPage(len(self.titles.pages) - 1)

        self.updateGui()
    
    def OnDeletePage(self, event):
        del self.titles.pages[self.pageIndex]
        self.setPage(0)

        self.updateGui()
        
    def OnMovePage(self, event):
        newIndex = (self.pageIndex + 1) % len(self.titles.pages)

        self.titles.pages[self.pageIndex], self.titles.pages[newIndex] = (
            self.titles.pages[newIndex], self.titles.pages[self.pageIndex])
        
        self.setPage(newIndex)

        self.updateGui()
    
    def OnNextPage(self, event):
        self.setPage((self.pageIndex + 1) % len(self.titles.pages))

        self.updateGui()
    
    def OnAddString(self, event):
        if self.pageIndex == -1:
            return

        if self.tsIndex != -1:
            ts = copy.deepcopy(self.titles.pages[self.pageIndex][self.tsIndex])
            ts.y += util.points2y(ts.size)
        else:
            ts = titles.TitleString("new string", 0.0, 100.0)

        self.titles.pages[self.pageIndex].append(ts)
        self.tsIndex = len(self.titles.pages[self.pageIndex]) - 1

        self.updateGui()
            
    def OnDeleteString(self, event):
        if (self.pageIndex == -1) or (self.tsIndex == -1):
            return

        del self.titles.pages[self.pageIndex][self.tsIndex]
        self.tsIndex = min(self.tsIndex,
                           len(self.titles.pages[self.pageIndex]) - 1)

        self.updateGui()
        
    # update page/string listboxes and selection
    def updateGui(self):
        self.stringsLb.Clear()

        pgCnt = len(self.titles.pages)
        
        self.delPageBtn.Enable(pgCnt > 0)
        self.moveBtn.Enable(pgCnt > 1)
        self.nextBtn.Enable(pgCnt > 1)
        self.previewBtn.Enable(pgCnt > 0)
        
        if self.pageIndex != -1:
            page = self.titles.pages[self.pageIndex]
            
            self.pageLabel.SetLabel("Page: %d / %d" % (self.pageIndex + 1,
                                                       pgCnt))
            self.addBtn.Enable(True)
            self.delBtn.Enable(len(page) > 0)
            
            for s in page:
                self.stringsLb.Append(s.text)

            if self.tsIndex != -1:
                self.stringsLb.SetSelection(self.tsIndex)
        else:
            self.pageLabel.SetLabel("No pages.")
            self.addBtn.Disable()
            self.delBtn.Disable()
            
        self.updateStringGui()

        self.previewCtrl.Refresh()

    # update selected string stuff
    def updateStringGui(self):
        if self.tsIndex == -1:
            for w in self.widList:
                w.Disable()

            self.textEntry.SetValue("")
            self.xEntry.SetValue("")
            self.centeredCb.SetValue(False)
            self.yEntry.SetValue("")
            self.sizeEntry.SetValue(12)
            self.boldCb.SetValue(False)
            self.italicCb.SetValue(False)
            self.underlinedCb.SetValue(False)
            
            return

        self.block = True

        ts = self.titles.pages[self.pageIndex][self.tsIndex]
        
        for w in self.widList:
            w.Enable(True)

        if ts.isCentered:
            self.xEntry.Disable()

        self.textEntry.SetValue(ts.text)
        self.centeredCb.SetValue(ts.isCentered)
        self.xEntry.SetValue("%.2f" % ts.x)
        self.yEntry.SetValue("%.2f" % ts.y)

        util.reverseComboSelect(self.fontCombo, ts.font)
        self.sizeEntry.SetValue(ts.size)

        self.boldCb.SetValue(ts.isBold)
        self.italicCb.SetValue(ts.isItalic)
        self.underlinedCb.SetValue(ts.isUnderlined)

        self.block = False
        
        self.previewCtrl.Refresh()
        
    def OnMisc(self, event = None):
        if (self.tsIndex == -1) or self.block:
            return

        ts = self.titles.pages[self.pageIndex][self.tsIndex]
        
        ts.text = util.toInputStr(self.textEntry.GetValue())
        self.stringsLb.SetString(self.tsIndex, ts.text)
        
        ts.x = util.str2float(self.xEntry.GetValue(), 0.0)
        ts.y = util.str2float(self.yEntry.GetValue(), 0.0)

        ts.isCentered = self.centeredCb.GetValue()
        self.xEntry.Enable(not ts.isCentered)
        
        ts.size = util.getSpinValue(self.sizeEntry)
        ts.font = self.fontCombo.GetClientData(self.fontCombo.GetSelection())
        
        ts.isBold = self.boldCb.GetValue()
        ts.isItalic = self.italicCb.GetValue()
        ts.isUnderlined = self.underlinedCb.GetValue()
        
        self.previewCtrl.Refresh()


class TitlesPreview(wxWindow):
    def __init__(self, parent, ctrl, cfg):
        wxWindow.__init__(self, parent, -1)

        self.cfg = cfg
        self.ctrl = ctrl
        
        EVT_SIZE(self, self.OnSize)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        EVT_PAINT(self, self.OnPaint)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)
        
    def OnEraseBackground(self, event):
        pass
    
    def OnPaint(self, event):
        dc = wxBufferedPaintDC(self, self.screenBuf)

        # widget size
        ww, wh = self.GetClientSizeTuple()

        dc.SetBrush(wxBrush(self.GetBackgroundColour()))
        dc.SetPen(wxPen(self.GetBackgroundColour()))
        dc.DrawRectangle(0, 0, ww, wh)
        
        # aspect ratio of paper
        aspect = self.cfg.paperWidth / self.cfg.paperHeight

        # calculate which way we can best fit the paper on screen
        h = wh
        w = int(aspect * wh)

        if w > ww:
            w = ww
            h = int(ww / aspect)

        # offset of paper
        ox = (ww - w) / 2
        oy = (wh - h) / 2
        
        dc.SetPen(wxBLACK_PEN)
        dc.SetBrush(wxWHITE_BRUSH)
        dc.DrawRectangle(ox, oy, w, h)

        if self.ctrl.pageIndex != -1:
            page = self.ctrl.titles.pages[self.ctrl.pageIndex]
            
            for i in range(len(page)):
                ts = page[i]
                
                if len(ts.text) == 0:
                    continue

                ch_x = util.points2x(ts.size)
                ch_y = util.points2y(ts.size)

                textW = int(((len(ts.text) * ch_x) / self.cfg.paperWidth) * w)
                textW = max(1, textW)
                
                textH = int((ch_y / self.cfg.paperHeight) * h)
                textH = max(1, textH)
                
                if ts.isCentered:
                    xp = w / 2 - textW / 2
                else:
                    xp = int((ts.x / self.cfg.paperWidth) * w)
                    
                yp = int((ts.y / self.cfg.paperHeight) * h)
                
                if i == self.ctrl.tsIndex:
                    dc.SetPen(wxRED_PEN)
                    dc.SetBrush(wxRED_BRUSH)
                else:
                    dc.SetPen(wxBLACK_PEN)
                    dc.SetBrush(wxBLACK_BRUSH)
                    
                dc.DrawRectangle(ox + xp, oy + yp, textW, textH)
