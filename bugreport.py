import os
import sys

import misc
import util

from wxPython.wx import *

# main program should set this as soon as the main frame is created
mainFrame = None

class BugReportHandler:
    def __init__(self):

        # data printed to stdout/stderr so far and not reported in some
        # way back to oskusoft.
        self.data = util.String()

        # size of data last time it was copied to the clipboard
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
        
class BugReportDlg(wxDialog):
    def __init__(self, parent, brh):
        wxDialog.__init__(self, parent, -1, "Error")

        self.brh = brh

        vsizer = wxBoxSizer(wxVERTICAL)

        s = "An error has occurred in the program. To help us fix it," \
            " please send a report to bugreport@oskusoft.com explaining" \
            " what you were doing and what went wrong. If possible, include" \
            " data needed to reproduce the problem.\n\n" \
            "" \
            "Also, and this is very important, press the \"Copy\" button" \
            " below to copy additional information about the problem to the" \
            " clipboard, and then paste that information at the end of your" \
            " mail. Don't close this window until you've safely copied this" \
            " extra information to another program.\n\n" \
            "" \
            "If you have other windows besides the main window open in" \
            " this program, you need to close them before being able to" \
            " press \"Copy\".\n\n" \
            "" \
            "After doing all this, save your work (if possible), and" \
            " restart the program."

        vsizer.Add(wxTextCtrl(self, -1, s,
            size = wxSize(400, 300), style = wxTE_MULTILINE | wxTE_READONLY),
            1, wxEXPAND)
        
        btn = wxButton(self, -1, "Copy")
        EVT_BUTTON(self, btn.GetId(), self.OnCopyCb)
        vsizer.Add(btn, 0, wxALIGN_CENTER | wxTOP, 10)

        util.finishWindow(self, vsizer)

        EVT_CLOSE(self, self.OnCloseWindow)

    def OnCloseWindow(self, event):
        self.Destroy()

        self.brh.dlg = None
        self.brh.data = util.String(str(self.brh.data)[self.brh.copyPos:])
        self.brh.copyPos = 0
        
    # FIXME: make this write the information to a file instead of using
    # the clipboard
    def OnCopyCb(self, event):
        if wxTheClipboard.Open():
            wxTheClipboard.UsePrimarySelection(True)
            
            wxTheClipboard.Clear()

            self.brh.copyPos = len(self.brh.data)
            s1 = str(self.brh.data).encode("base64").encode("rot13")
            s2 = "---start info---\n1 "

            # FIXME: put whole license string here
            if misc.isEval:
                s2 += "0\n"
            else:
                s2 += "1\n%s" % misc.license

            s2 += "%s---end info---\n" % s1
            s2 = s2.replace("\n", os.linesep)

            wxTheClipboard.AddData(wxTextDataObject(s2))
            wxTheClipboard.Flush()
                
            wxTheClipboard.Close()
