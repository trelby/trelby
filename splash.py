import misc
import util

import md5
import sys

from wxPython.wx import *

class SplashWindow(wxFrame):
    inited = False
    
    def __init__(self, parent, delay):
        wxFrame.__init__(self, parent, -1, "Splash",
            style = wxFRAME_FLOAT_ON_PARENT | wxSTAY_ON_TOP | wxSIMPLE_BORDER)

        if not SplashWindow.inited:
            SplashWindow.inited = True
            wxImage_AddHandler(wxJPEGHandler())

        fileName = "logo.jpg"
        fileData = util.loadFile(fileName, parent)

        if not fileData or (len(fileData) != 120900) or \
               (md5.new(fileData).digest() != \
          "\x79\xff\x05\x31\x2d\xa8\xdc\x09\x1e\x56\x43\xac\xda\xaf\x7c\xa3"):
            self.abort()
        
        self.pic = wxBitmap(fileName, wxBITMAP_TYPE_JPEG)
        if not self.pic.Ok():
            self.abort()

        w, h = (self.pic.GetWidth(), self.pic.GetHeight())

        if (w != 640) or (h != 440):
            self.abort()

        self.SetClientSizeWH(w, h)

        self.CenterOnScreen()

        self.textColor = wxColour(0, 0, 0)

        if misc.isUnix:
            self.font = wxFont(12, wxMODERN, wxNORMAL, wxNORMAL)
        else:
            self.font = wxFont(10, wxMODERN, wxNORMAL, wxNORMAL)

        if delay != -1:
            self.timer = wxTimer(self)
            EVT_TIMER(self, -1, self.OnTimer)
            self.timer.Start(delay, True)
        else:
            EVT_LEFT_DOWN(self, self.OnClick)

        EVT_PAINT(self, self.OnPaint)
        EVT_CLOSE(self, self.OnCloseWindow)

    def abort(self):
        wxMessageBox("Error opening splash screen.", "Error", wxOK,
                     self.GetParent())
        sys.exit()
        
    def OnClick(self, event):
        self.Close()

    def OnPaint(self, event):
        dc = wxPaintDC(self)

        dc.SetFont(self.font)
        dc.SetTextForeground(self.textColor)

        if self.pic:
            dc.DrawBitmap(self.pic, 0, 0, False)
        else:
            dc.DrawText("Splash screen image not found", 50, 50)

        x = 421
        dc.DrawText("Version %s" % misc.version, x, 346)
        dc.DrawText(misc.licensedTo, x, 360)
        
    def OnTimer(self, event):
        self.timer.Stop()
        self.Close()
        
    def OnCloseWindow(self, event):
        self.Destroy()
        self.Refresh()
        
