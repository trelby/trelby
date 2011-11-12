import sys

import misc
import util

import wx

# main program should set this as soon as the main frame is created
mainFrame = None

class BugReportHandler:
    def __init__(self):

        # data printed to stdout/stderr so far and not reported in some
        # way back to oskusoft.
        self.data = util.String()

        # size of data last time it was written to a file
        self.copyPos = 0

        # possible open BugReportDlg
        self.dlg = None
        
    def write(self, s):
        if not mainFrame:
            sys.__stderr__.write(s)

            return
        
        self.data += s

        if not self.dlg:
            self.dlg = BugReportDlg(mainFrame, self)
            self.dlg.Show()
        
class BugReportDlg(wx.Dialog):
    def __init__(self, parent, brh):
        wx.Dialog.__init__(self, parent, -1, "Error")

        self.brh = brh

        vsizer = wx.BoxSizer(wx.VERTICAL)

        s = "An error has occurred in the program. To help us fix it," \
            " please send a report to bugreport@oskusoft.com explaining" \
            " what you were doing and what went wrong. If possible, include" \
            " data needed to reproduce the problem.\n\n" \
            "" \
            "Also, and this is very important, press the \"Save\" button" \
            " below to save additional information about the problem to a" \
            " file, and then attach that file to your mail.\n\n" \
            "" \
            "If you have other windows besides the main window open in" \
            " this program, you may need to close them before being able to" \
            " press \"Save\".\n\n" \
            "" \
            "After doing all this, save your work (if possible), and" \
            " restart the program."

        vsizer.Add(wx.TextCtrl(self, -1, s,
            size = wx.Size(400, 300), style = wx.TE_MULTILINE | wx.TE_READONLY),
            1, wx.EXPAND)
        
        btn = wx.Button(self, -1, "Save")
        wx.EVT_BUTTON(self, btn.GetId(), self.OnSave)
        vsizer.Add(btn, 0, wx.ALIGN_CENTER | wx.TOP, 10)

        util.finishWindow(self, vsizer)

        wx.EVT_CLOSE(self, self.OnCloseWindow)

    def OnCloseWindow(self, event):
        self.Destroy()

        self.brh.dlg = None
        self.brh.data = util.String(str(self.brh.data)[self.brh.copyPos:])
        self.brh.copyPos = 0
        
    def OnSave(self, event):
        dlg = wx.FileDialog(self, "Filename to save as",
            defaultFile = "error_report.txt",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            self.brh.copyPos = len(self.brh.data)
            s = str(self.brh.data)

            util.writeToFile(dlg.GetPath(), s, self)
