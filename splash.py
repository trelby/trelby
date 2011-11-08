import misc
import util

import sys

import wx

class SplashWindow(wx.Frame):
    inited = False
    
    def __init__(self, parent, delay):
        wx.Frame.__init__(
            self, parent, -1, "Splash",
            style = wx.FRAME_FLOAT_ON_PARENT | wx.NO_BORDER)

        if not SplashWindow.inited:
            SplashWindow.inited = True
            wx.Image_AddHandler(wx.JPEGHandler())
        
        self.pic = misc.getBitmap("resources/logo.jpg")

        if self.pic.Ok():
            w, h = (self.pic.GetWidth(), self.pic.GetHeight())
        else:
            w, h = (375, 300)

        util.setWH(self, w, h)
        self.CenterOnScreen()

        self.textColor = wx.Colour(0, 0, 0)

        self.font = util.createPixelFont(
            14, wx.FONTFAMILY_MODERN, wx.NORMAL, wx.NORMAL)

        if delay != -1:
            self.timer = wx.Timer(self)
            wx.EVT_TIMER(self, -1, self.OnTimer)
            self.timer.Start(delay, True)

        wx.EVT_LEFT_DOWN(self, self.OnClick)

        wx.EVT_PAINT(self, self.OnPaint)
        wx.EVT_CLOSE(self, self.OnCloseWindow)
        
    def OnClick(self, event):
        self.Close()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        dc.SetFont(self.font)
        dc.SetTextForeground(self.textColor)

        if self.pic.Ok():
            dc.DrawBitmap(self.pic, 0, 0, False)

        util.drawText(dc, "Version %s" % (misc.version),
                      200, 170, util.ALIGN_RIGHT)
        
    def OnTimer(self, event):
        self.timer.Stop()
        self.Close()
        
    def OnCloseWindow(self, event):
        self.Destroy()
        self.Refresh()
