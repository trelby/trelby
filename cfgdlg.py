from wxPython.wx import *

class CfgDlg(wxDialog):
    def __init__(self, parent, cfg):
        wxDialog.__init__(self, parent, -1, "Config dialog",
                          pos = wxDefaultPosition,
                          size = wxDefaultSize,
                          style = wxDEFAULT_DIALOG_STYLE)
        self.cfg = cfg
