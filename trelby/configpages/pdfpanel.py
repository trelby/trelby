import trelby.misc as misc
import trelby.util as util
import wx


class PDFPanel(wx.Panel):
    def __init__(self, parent, id, cfg):
        wx.Panel.__init__(self, parent, id)
        self.cfg = cfg

        vsizer = wx.BoxSizer(wx.VERTICAL)

        # wxGTK adds way more space by default than wxMSW between the
        # items, have to adjust for that
        pad = 0
        if misc.isWindows:
            pad = 10

        self.includeTOCCb = self.addCb(_("Add table of contents"), vsizer, pad)

        self.showTOCCb = self.addCb(
            _("Show table of contents on PDF open"), vsizer, pad
        )

        self.openOnCurrentPageCb = self.addCb(
            _("Open PDF on current page"), vsizer, pad
        )

        self.removeNotesCb = self.addCb(_("Omit Note elements"), vsizer, pad)

        self.outlineNotesCb = self.addCb(
            _("  Draw rectangles around Note elements"), vsizer, pad
        )

        self.marginsCb = self.addCb(_("Show margins (debug)"), vsizer, pad)

        self.cfg2gui()

        util.finishWindow(self, vsizer, center=False)

    def addCb(self, descr, sizer, pad):
        ctrl = wx.CheckBox(self, -1, descr)
        self.Bind(wx.EVT_CHECKBOX, self.OnMisc, id=ctrl.GetId())
        sizer.Add(ctrl, 0, wx.TOP, pad)

        return ctrl

    def OnMisc(self, event=None):
        self.cfg.pdfIncludeTOC = self.includeTOCCb.GetValue()
        self.cfg.pdfShowTOC = self.showTOCCb.GetValue()
        self.cfg.pdfOpenOnCurrentPage = self.openOnCurrentPageCb.GetValue()
        self.cfg.pdfRemoveNotes = self.removeNotesCb.GetValue()
        self.cfg.pdfOutlineNotes = self.outlineNotesCb.GetValue()
        self.cfg.pdfShowMargins = self.marginsCb.GetValue()

        self.outlineNotesCb.Enable(not self.cfg.pdfRemoveNotes)

    def cfg2gui(self):
        self.includeTOCCb.SetValue(self.cfg.pdfIncludeTOC)
        self.showTOCCb.SetValue(self.cfg.pdfShowTOC)
        self.openOnCurrentPageCb.SetValue(self.cfg.pdfOpenOnCurrentPage)
        self.removeNotesCb.SetValue(self.cfg.pdfRemoveNotes)
        self.outlineNotesCb.SetValue(self.cfg.pdfOutlineNotes)
        self.marginsCb.SetValue(self.cfg.pdfShowMargins)
