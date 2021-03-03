import pdf
import pml
import random
import util

import wx

# The watermark tool dialog.
class WatermarkDlg(wx.Dialog):
    # sp - screenplay object, from which to generate PDF
    # prefix - prefix name for the PDF files (unicode)
    def __init__(self, parent, sp, prefix):
        wx.Dialog.__init__(self, parent, -1, "Watermarked PDFs generator",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.frame = parent
        self.sp = sp

        vsizer = wx.BoxSizer(wx.VERTICAL)

        vsizer.Add(wx.StaticText(self, -1, "Directory to save in:"), 0)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.dirEntry = wx.TextCtrl(self, -1)
        hsizer.Add(self.dirEntry, 1, wx.EXPAND)

        btn = wx.Button(self, -1, "Browse")
        self.Bind(wx.EVT_BUTTON, self.OnBrowse, id=btn.GetId())
        hsizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        vsizer.Add(wx.StaticText(self, -1, "Filename prefix:"), 0)
        self.filenamePrefix = wx.TextCtrl(self, -1, prefix)
        vsizer.Add(self.filenamePrefix, 0, wx.EXPAND | wx.BOTTOM, 5)

        vsizer.Add(wx.StaticText(self, -1, "Watermark font size:"), 0)
        self.markSize = wx.SpinCtrl(self, -1, size=(60, -1))
        self.markSize.SetRange(20, 80)
        self.markSize.SetValue(40)
        vsizer.Add(self.markSize, 0, wx.BOTTOM, 5)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        vsizer.Add(wx.StaticText(self, -1, "Common mark:"), 0)
        self.commonMark = wx.TextCtrl(self, -1, "Confidential")
        vsizer.Add(self.commonMark, 0, wx.EXPAND| wx.BOTTOM, 5)

        vsizer.Add(wx.StaticText(self, -1, "Watermarks (one per line):"))
        self.itemsEntry = wx.TextCtrl(
            self, -1, style = wx.TE_MULTILINE | wx.TE_DONTWRAP,
            size = (300, 200))
        vsizer.Add(self.itemsEntry, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        closeBtn = wx.Button(self, -1, "Close")
        hsizer.Add(closeBtn, 0)
        hsizer.Add((1, 1), 1)
        generateBtn = wx.Button(self, -1, "Generate PDFs")
        hsizer.Add(generateBtn, 0)

        vsizer.Add(hsizer, 0, wx.EXPAND | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        self.Bind(wx.EVT_BUTTON, self.OnClose, id=closeBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnGenerate, id=generateBtn.GetId())

        self.dirEntry.SetFocus()

    @staticmethod
    def getUniqueId(usedIds):
        while True:
            uid = ""

            for i in range(8):
                uid += '%02x' % random.randint(0, 255)

            if uid in usedIds:
                continue

            usedIds.add(uid)

            return uid

    def OnGenerate(self, event):
        watermarks = self.itemsEntry.GetValue().split("\n")
        common = self.commonMark.GetValue()
        directory = self.dirEntry.GetValue()
        fontsize = self.markSize.GetValue()
        fnprefix = self.filenamePrefix.GetValue()

        watermarks = set(watermarks)

        # keep track of ids allocated so far, just on the off-chance we
        # randomly allocated the same id twice
        usedIds = set()

        if not directory:
            wx.MessageBox("Please set directory.", "Error", wx.OK, self)
            self.dirEntry.SetFocus()
            return

        count = 0

        for item in watermarks:
            s = item.strip()

            if not s:
                continue

            basename = item.replace(" ", "-")
            fn = directory + "/" + fnprefix + '-' + basename + ".pdf"
            pmldoc = self.sp.generatePML(True)

            ops = []

            # almost-not-there gray
            ops.append(pml.PDFOp("0.85 g"))

            if common:
                wm = pml.TextOp(
                    util.cleanInput(common),
                    self.sp.cfg.marginLeft + 20, self.sp.cfg.paperHeight * 0.45,
                    fontsize, pml.BOLD, angle = 45)
                ops.append(wm)

            wm = pml.TextOp(
                util.cleanInput(s),
                self.sp.cfg.marginLeft + 20, self.sp.cfg.paperHeight * 0.6,
                fontsize, pml.BOLD, angle = 45)
            ops.append(wm)

            # ...and back to black
            ops.append(pml.PDFOp("0.0 g"))

            for page in pmldoc.pages:
                page.addOpsToFront(ops)

            pmldoc.uniqueId = self.getUniqueId(usedIds)

            pdfdata = pdf.generate(pmldoc)

            if not util.writeToFile(fn, pdfdata, self):
                wx.MessageBox("PDF generation aborted.", "Error", wx.OK, self)
                return
            else:
                count += 1

        if count > 0:
            wx.MessageBox("Generated %d files in directory %s." %
                          (count, directory), "PDFs generated",
                          wx.OK, self)
        else:
            wx.MessageBox("No watermarks specified.", "Error", wx.OK, self)

    def OnClose(self, event):
        self.EndModal(wx.OK)

    def OnBrowse(self, event):
        dlg = wx.DirDialog(
            self.frame, style = wx.DD_NEW_DIR_BUTTON)

        if dlg.ShowModal() == wx.ID_OK:
            self.dirEntry.SetValue(dlg.GetPath())

        dlg.Destroy()
