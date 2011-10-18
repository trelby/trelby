import misc
import util

import sys

import wx

class SplashWindow(wx.Frame):
    inited = False
    
    def __init__(self, parent, delay):
        wx.Frame.__init__(
            self, parent, -1, "Splash",
            style = wx.FRAME_FLOAT_ON_PARENT | wx.STAY_ON_TOP | wx.NO_BORDER)

        if not SplashWindow.inited:
            SplashWindow.inited = True
            wx.Image_AddHandler(wx.JPEGHandler())

        fileName = u"logo.jpg"
        fileData = util.loadFile(fileName, parent)

        if not fileData:
            self.abort()
        
        self.pic = wx.Bitmap(fileName, wx.BITMAP_TYPE_JPEG)
        if not self.pic.Ok():
            self.abort()

        w, h = (self.pic.GetWidth(), self.pic.GetHeight())

        if (w != 640) or (h != 440):
            self.abort()

        util.setWH(self, w, h)
        self.CenterOnScreen()

        self.textColor = wx.Colour(0, 0, 0)

        self.font = util.createPixelFont(
            17, wx.FONTFAMILY_MODERN, wx.NORMAL, wx.NORMAL)

        if delay != -1:
            self.timer = wx.Timer(self)
            wx.EVT_TIMER(self, -1, self.OnTimer)
            self.timer.Start(delay, True)
        else:
            wx.EVT_LEFT_DOWN(self, self.OnClick)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_CLOSE(self, self.OnCloseWindow)

    def abort(self):
        wx.MessageBox("Error opening splash screen.", "Error", wx.OK,
                      self.GetParent())
        sys.exit()
        
    def OnClick(self, event):
        self.Close()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

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
        
