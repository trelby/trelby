import misc
from wxPython.wx import *

class SplashWindow(wxFrame):
    inited = False
    
    def __init__(self, parent, delay):
        wxFrame.__init__(self, parent, -1, "Splash",
                         pos = wxDefaultPosition,
                         size = (100, 100),
                         style = wxFRAME_FLOAT_ON_PARENT | wxSTAY_ON_TOP |
                         wxSIMPLE_BORDER)

        if not SplashWindow.inited:
            SplashWindow.inited = True
            wxImage_AddHandler(wxJPEGHandler())
        
        self.pic = wxBitmap("logo.jpg", wxBITMAP_TYPE_JPEG)
        if self.pic.Ok():
            self.SetClientSizeWH(self.pic.GetWidth(), self.pic.GetHeight())
        else:
            self.pic = None
            self.SetClientSizeWH(512, 384)

        self.CenterOnScreen()

        self.textColor = wxColour(0, 0, 0)
        self.font = wxFont(12, wxMODERN, wxNORMAL, wxNORMAL)
            
        self.timer = wxTimer(self)
        EVT_TIMER(self, -1, self.OnTimer)
        self.timer.Start(delay, True)
        
        EVT_PAINT(self, self.OnPaint)
        EVT_CLOSE(self, self.OnCloseWindow)

    def OnPaint(self, event):
        dc = wxPaintDC(self)

        dc.SetFont(self.font)
        dc.SetTextForeground(self.textColor)

        if self.pic:
            dc.DrawBitmap(self.pic, 0, 0, False)
        else:
            dc.DrawText("Splash screen image not found", 50, 50)

        dc.DrawText("Version %s" % misc.version, 200, 135)
        dc.DrawText(misc.copyright, 125, 165)
        
        s = misc.licensedTo
        w, h = dc.GetTextExtent(s)
        w += 15
        h += 15
        size = self.GetClientSize()
        dc.DrawText(s, size.width - w, size.height - h)
        
    def OnTimer(self, event):
        self.timer.Stop()
        self.Close()
        
    def OnCloseWindow(self, event):
        self.Destroy()
        self.Refresh()
        
