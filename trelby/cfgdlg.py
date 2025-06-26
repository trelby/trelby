import wx

import trelby.gutil as gutil

# import config pages
from trelby.configpages.globalaboutpanel import GlobalAboutPanel
from trelby.configpages.scriptaboutpanel import ScriptAboutPanel
from trelby.configpages.elementspanel import ElementsPanel
from trelby.configpages.elementsglobalpanel import ElementsGlobalPanel
from trelby.configpages.colorspanel import ColorsPanel
from trelby.configpages.displaypanel import DisplayPanel
from trelby.configpages.keyboardpanel import KeyboardPanel
from trelby.configpages.formattingpanel import FormattingPanel
from trelby.configpages.paperpanel import PaperPanel
from trelby.configpages.pdfpanel import PDFPanel
from trelby.configpages.pdffontspanel import PDFFontsPanel
from trelby.configpages.stringspanel import StringsPanel
from trelby.configpages.miscpanel import MiscPanel

class CfgDlg(wx.Dialog):
    def __init__(self, parent, cfg, applyFunc, isGlobal):
        wx.Dialog.__init__(
            self, parent, -1, "", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.cfg = cfg
        self.applyFunc = applyFunc

        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.listbook = wx.Listbook(self, -1)

        if isGlobal:
            self.SetTitle("Settings dialog")

            self.AddPage(GlobalAboutPanel, "About")
            self.AddPage(ColorsPanel, "Colors")
            self.AddPage(DisplayPanel, "Display")
            self.AddPage(ElementsGlobalPanel, "Elements")
            self.AddPage(KeyboardPanel, "Keyboard")
            self.AddPage(MiscPanel, "Misc")
        else:
            self.SetTitle("Script settings dialog")

            self.AddPage(ScriptAboutPanel, "About")
            self.AddPage(ElementsPanel, "Elements")
            self.AddPage(FormattingPanel, "Formatting")
            self.AddPage(PaperPanel, "Paper")
            self.AddPage(PDFPanel, "PDF")
            self.AddPage(PDFFontsPanel, "PDF/Fonts")
            self.AddPage(StringsPanel, "Strings")

        vsizer.Add(self.listbook, 1, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add((1, 1), 1)

        applyBtn = gutil.createStockButton(self, "Apply")
        hsizer.Add(applyBtn, 0, wx.ALL, 5)

        cancelBtn = gutil.createStockButton(self, "Cancel")
        hsizer.Add(cancelBtn, 0, wx.ALL, 5)

        okBtn = gutil.createStockButton(self, "OK")
        hsizer.Add(okBtn, 0, wx.ALL, 5)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        self.SetSizerAndFit(vsizer)
        self.Layout()
        # self.Center()

        self.Bind(wx.EVT_BUTTON, self.OnApply, id=applyBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnCancel, id=cancelBtn.GetId())
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=okBtn.GetId())

    def AddPage(self, classObj, name):
        # stupid hack to get correct window modality stacking for dialogs
        needs_frame_ref = [DisplayPanel, KeyboardPanel, MiscPanel, PDFFontsPanel]
        if classObj in needs_frame_ref:
            p = classObj(self.listbook, -1, self.cfg, self)
        else:
            p = classObj(self.listbook, -1, self.cfg)

        self.listbook.AddPage(p, name)

    # check for errors in each panel
    def checkForErrors(self):
        for pageNum in range(self.listbook.GetPageCount()):
            panel = self.listbook.GetPage(pageNum)
            if hasattr(panel, "checkForErrors"):
                panel.checkForErrors()

    def OnOK(self, event):
        self.checkForErrors()
        self.EndModal(wx.ID_OK)

    def OnApply(self, event):
        self.checkForErrors()
        self.applyFunc(self.cfg)

    def OnCancel(self, event):
        self.EndModal(wx.ID_CANCEL)
