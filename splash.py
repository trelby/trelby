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

        if not fileData or (len(fileData) != 126849) or \
               (md5.new(fileData).digest() != \
          "\x12\x3b\xe5\x43\x75\xa9\xec\x08\x34\x03\x16\x48\x24\xb1\xae\x60"):
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
            fs = 12
        else:
            fs = 10
            
        self.font = wxFont(fs, wxMODERN, wxNORMAL, wxNORMAL,
                           encoding = wxFONTENCODING_ISO8859_1)

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

        dc.DrawBitmap(self.pic, 0, 0, False)

        util.drawText(dc, "Version %s, released %s." % (misc.version,
            misc.releaseDate), 630, 346, util.ALIGN_RIGHT)
        
    def OnTimer(self, event):
        self.timer.Stop()
        self.Close()
        
    def OnCloseWindow(self, event):
        self.Destroy()
        self.Refresh()
        
