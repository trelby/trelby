import headers
import misc
import pdf
import pml
import util

from wxPython.wx import *

class HeadersDlg(wxDialog):
    def __init__(self, parent, headers, cfg):
        wxDialog.__init__(self, parent, -1, "Headers",
                          style = wxDEFAULT_DIALOG_STYLE)

        self.headers = headers
        self.cfg = cfg

        # whether some events are blocked
        self.block = False

        self.hdrIndex = -1
        if len(self.headers.hdrs) > 0:
            self.hdrIndex = 0

        h = 425
        if misc.isWindows:
            h = 400

        self.SetClientSizeWH(400, h);
        self.Center()
        
        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(panel, -1, "Empty lines after headers:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        
        self.elinesEntry = wxSpinCtrl(panel, -1)
        self.elinesEntry.SetRange(0, 5)
        EVT_SPINCTRL(self, self.elinesEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.elinesEntry, self.OnKillFocus)
        hsizer.Add(self.elinesEntry, 0, wxLEFT, 10)

        vsizer.Add(hsizer)
        
        vsizer.Add(wxStaticLine(panel, -1), 0, wxEXPAND | wxTOP | wxBOTTOM,
                   10)
        
        tmp = wxStaticText(panel, -1, "Strings:")
        vsizer.Add(tmp)
        
        self.stringsLb = wxListBox(panel, -1, size = (200, 100))
        vsizer.Add(self.stringsLb, 0, wxEXPAND)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.addBtn = wxButton(panel, -1, "Add")
        hsizer.Add(self.addBtn)
        EVT_BUTTON(self, self.addBtn.GetId(), self.OnAddString)

        self.delBtn = wxButton(panel, -1, "Delete")
        hsizer.Add(self.delBtn, 0, wxLEFT, 10)
        EVT_BUTTON(self, self.delBtn.GetId(), self.OnDeleteString)

        vsizer.Add(hsizer, 0, wxTOP, 5)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(wxStaticText(panel, -1, "Text:"), 0,
                   wxALIGN_CENTER_VERTICAL)

        self.textEntry = wxTextCtrl(panel, -1)
        hsizer.Add(self.textEntry, 1, wxLEFT, 10)
        EVT_TEXT(self, self.textEntry.GetId(), self.OnMisc)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 20)

        vsizer.Add(wxStaticText(panel, -1,
            "'${PAGE}' will be replaced by the page number."), 0,
            wxALIGN_CENTER | wxTOP, 5)

        hsizerTop = wxBoxSizer(wxHORIZONTAL)

        gsizer = wxFlexGridSizer(3, 2, 5, 0)

        gsizer.Add(wxStaticText(panel, -1, "Header line:"), 0,
                   wxALIGN_CENTER_VERTICAL)

        self.lineEntry = wxSpinCtrl(panel, -1)
        self.lineEntry.SetRange(1, 5)
        EVT_SPINCTRL(self, self.lineEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.lineEntry, self.OnKillFocus)
        gsizer.Add(self.lineEntry)

        gsizer.Add(wxStaticText(panel, -1, "X offset (characters):"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)

        self.xoffEntry = wxSpinCtrl(panel, -1)
        self.xoffEntry.SetRange(-100, 100)
        EVT_SPINCTRL(self, self.xoffEntry.GetId(), self.OnMisc)
        EVT_KILL_FOCUS(self.xoffEntry, self.OnKillFocus)
        gsizer.Add(self.xoffEntry)

        gsizer.Add(wxStaticText(panel, -1, "Alignment:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.alignCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        for it in [ ("Left", util.ALIGN_LEFT), ("Center", util.ALIGN_CENTER),
                    ("Right", util.ALIGN_RIGHT) ]:
            self.alignCombo.Append(it[0], it[1])

        gsizer.Add(self.alignCombo)
        EVT_COMBOBOX(self, self.alignCombo.GetId(), self.OnMisc)

        hsizerTop.Add(gsizer)
        
        bsizer = wxStaticBoxSizer(wxStaticBox(panel, -1, "Style"),
                                  wxHORIZONTAL)

        vsizer2 = wxBoxSizer(wxVERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 5
        
        self.addCheckBox("Bold", panel, vsizer2, pad)
        self.addCheckBox("Italic", panel, vsizer2, pad)
        self.addCheckBox("Underlined", panel, vsizer2, pad)
            
        bsizer.Add(vsizer2)

        hsizerTop.Add(bsizer, 0, wxLEFT, 40)

        vsizer.Add(hsizerTop, 0, wxTOP, 20)

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
        self.widList = [ self.textEntry, self.xoffEntry, self.alignCombo,
                         self.lineEntry, self.boldCb, self.italicCb,
                         self.underlinedCb ]
        
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

        pg = pml.Page(doc)
        self.headers.generatePML(pg, "42", self.cfg)

        fs = self.cfg.fontSize
        ch_y = util.getTextHeight(fs)
        
        y = self.cfg.marginTop + self.headers.getNrOfLines() * ch_y
        
        pg.add(pml.TextOp("Mindy runs away from the dinosaur, but trips on"
            " the power", self.cfg.marginLeft, y, fs))

        pg.add(pml.TextOp("cord. The raptor approaches her slowly.",
            self.cfg.marginLeft, y + ch_y, fs))

        doc.add(pg)
        
        tmp = pdf.generate(doc)
        util.showTempPDF(tmp, self.cfg, self)

    def OnKillFocus(self, event):
        self.OnMisc()

        # if we don't call this, the spin entry on wxGTK gets stuck in
        # some weird state
        event.Skip()

    def OnStringsLb(self, event = None):
        self.hdrIndex = self.stringsLb.GetSelection()
        self.updateHeaderGui()

    def OnAddString(self, event):
        h = headers.HeaderString()
        h.text = "new string"
        
        self.headers.hdrs.append(h)
        self.hdrIndex = len(self.headers.hdrs) - 1

        self.updateGui()
        
    def OnDeleteString(self, event):
        if self.hdrIndex == -1:
            return

        del self.headers.hdrs[self.hdrIndex]
        self.hdrIndex = min(self.hdrIndex, len(self.headers.hdrs) - 1)

        self.updateGui()
        
    # update listbox
    def updateGui(self):
        self.stringsLb.Clear()

        self.elinesEntry.SetValue(self.headers.emptyLinesAfter)
        
        self.delBtn.Enable(self.hdrIndex != -1)

        for h in self.headers.hdrs:
            self.stringsLb.Append(h.text)

        if self.hdrIndex != -1:
            self.stringsLb.SetSelection(self.hdrIndex)
            
        self.updateHeaderGui()

    # update selected header stuff
    def updateHeaderGui(self):
        if self.hdrIndex == -1:
            for w in self.widList:
                w.Disable()

            self.textEntry.SetValue("")
            self.lineEntry.SetValue(1)
            self.xoffEntry.SetValue(0)
            self.boldCb.SetValue(False)
            self.italicCb.SetValue(False)
            self.underlinedCb.SetValue(False)
            
            return

        self.block = True

        h = self.headers.hdrs[self.hdrIndex]
        
        for w in self.widList:
            w.Enable(True)

        self.textEntry.SetValue(h.text)
        self.xoffEntry.SetValue(h.xoff)

        util.reverseComboSelect(self.alignCombo, h.align)
        self.lineEntry.SetValue(h.line)

        self.boldCb.SetValue(h.isBold)
        self.italicCb.SetValue(h.isItalic)
        self.underlinedCb.SetValue(h.isUnderlined)

        self.block = False
        
    def OnMisc(self, event = None):
        self.headers.emptyLinesAfter = util.getSpinValue(self.elinesEntry)
        
        if (self.hdrIndex == -1) or self.block:
            return

        h = self.headers.hdrs[self.hdrIndex]
        
        h.text = util.toInputStr(self.textEntry.GetValue())
        self.stringsLb.SetString(self.hdrIndex, h.text)
        
        h.xoff = util.getSpinValue(self.xoffEntry)
        h.line = util.getSpinValue(self.lineEntry)
        h.align = self.alignCombo.GetClientData(self.alignCombo.GetSelection())
        
        h.isBold = self.boldCb.GetValue()
        h.isItalic = self.italicCb.GetValue()
        h.isUnderlined = self.underlinedCb.GetValue()
