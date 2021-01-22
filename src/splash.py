# -*- coding: utf-8 -*-

import misc
import util

import random

import wx

class Quote:
    def __init__(self, source, lines):
        # unicode string
        self.source = source

        # list of unicode strings
        self.lines = lines

class SplashWindow(wx.Frame):
    inited = False

    # Quote objects
    quotes = []

    def __init__(self, parent, delay):
        wx.Frame.__init__(
            self, parent, -1, "Splash",
            style = wx.FRAME_FLOAT_ON_PARENT | wx.NO_BORDER)

        if not SplashWindow.inited:
            SplashWindow.inited = True
            wx.Image.AddHandler(wx.JPEGHandler())

            self.loadQuotes(parent)

        self.pickRandomQuote()

        self.pic = misc.getBitmap("resources/logo.jpg")

        if self.pic.IsOk():
            w, h = (self.pic.GetWidth(), self.pic.GetHeight())
        else:
            w, h = (375, 300)

        util.setWH(self, w, h)
        self.CenterOnScreen()

        self.textColor = wx.Colour(0, 0, 0)

        self.font = util.createPixelFont(
            14, wx.FONTFAMILY_MODERN, wx.NORMAL, wx.NORMAL)

        self.quoteFont = util.createPixelFont(
            16, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)

        self.sourceFont = util.createPixelFont(
            15, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.NORMAL)

        if delay != -1:
            self.timer = wx.Timer(self)
            wx.Timer()
            self.timer.Start(delay, True)

        self.Bind(wx.EVT_LEFT_DOWN, self.OnClick)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

    def OnClick(self, event):
        self.Close()

    def OnPaint(self, event):
        dc = wx.PaintDC(self)

        dc.SetFont(self.font)
        dc.SetTextForeground(self.textColor)

        if self.pic.IsOk():
            dc.DrawBitmap(self.pic, 0, 0, False)

        util.drawText(dc, "Version %s" % (misc.version),
                      200, 170, util.ALIGN_RIGHT)

        util.drawText(dc, "http://www.trelby.org/", 200, 185, util.ALIGN_RIGHT)

        if self.quote:
            dc.SetFont(self.sourceFont)
            dc.DrawText(self.quote.source, 50, 280)

            dc.SetFont(self.quoteFont)

            for i,line in enumerate(self.quote.lines):
                x = 10
                y = 260 - (len(self.quote.lines) - i - 1) * 17

                if i == 0:
                    dc.DrawText("“", x - 5, y)

                if i == (len(self.quote.lines) - 1):
                    line = line + "”"

                dc.DrawText(line, x, y)


    def OnTimer(self, event):
        self.timer.Stop()
        self.Close()

    def OnCloseWindow(self, event):
        self.Destroy()
        self.Refresh()

    def pickRandomQuote(self):
        if not SplashWindow.quotes:
            self.quote = None
        else:
            self.quote = random.choice(SplashWindow.quotes)

    @staticmethod
    def loadQuotes(parent):
        try:
            data = util.loadFile(misc.getFullPath("resources/quotes.txt"), parent)
            if data is None:
                return

            #data = data.decode("utf-8")
            lines = data.splitlines()

            quotes = []

            # lines saved for current quote being processed
            tmp = []

            for i,line in enumerate(lines):
                if line.startswith("#") or not line.strip():
                    continue

                if line.startswith("  "):
                    if not tmp:
                        raise Exception("No lines defined for quote at line %d" % (i + 1))

                    if len(tmp) > 3:
                        raise Exception("Too many lines defined for quote at line %d" % (i + 1))

                    quotes.append(Quote(line.strip(), tmp))
                    tmp = []
                else:
                    tmp.append(line.strip())

            if tmp:
                raise Exception("Last quote does not have source")

            SplashWindow.quotes = quotes

        except Exception as e:
            wx.MessageBox("Error loading quotes: %s" % str(e),
                          "Error", wx.OK, parent)
