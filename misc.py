from wxPython.wx import *

class MyColorSample(wxWindow):
    def __init__(self, parent, id, size):
        wxWindow.__init__(self, parent, id, size = size)

        EVT_PAINT(self, self.OnPaint)

    def OnPaint(self, event):
        dc = wxPaintDC(self)

        w, h = self.GetClientSizeTuple()
        br = wxBrush(self.GetBackgroundColour())
        dc.SetBrush(br)
        dc.DrawRectangle(0, 0, w, h)
