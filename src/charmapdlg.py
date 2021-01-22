import gutil
import util

import wx

class CharMapDlg(wx.Dialog):
    def __init__(self, parent, ctrl):
        wx.Dialog.__init__(self, parent, -1, "Character map")

        self.ctrl = ctrl

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.charMap = MyCharMap(self)
        hsizer.Add(self.charMap)

        self.insertButton = wx.Button(self, -1, " Insert character ")
        hsizer.Add(self.insertButton, 0, wx.ALL, 10)
        self.Bind(wx.EVT_BUTTON, self.OnInsert, id=self.insertButton.GetId())
        gutil.btnDblClick(self.insertButton, self.OnInsert)

        util.finishWindow(self, hsizer, 0)

    def OnInsert(self, event):
        if self.charMap.selected:
            self.ctrl.OnKeyChar(util.MyKeyEvent(ord(self.charMap.selected)))

class MyCharMap(wx.Window):
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1)

        self.selected = None

        # all valid characters
        self.chars = ""

        for i in range(256):
            if util.isValidInputChar(i):
                self.chars += chr(i)

        self.cols = 16
        self.rows = len(self.chars) // self.cols
        if len(self.chars) % 16:
            self.rows += 1

        # offset of grid
        self.offset = 5

        # size of a single character cell
        self.cellSize = 32

        # size of the zoomed-in character boxes
        self.boxSize = 60

        self.smallFont = util.createPixelFont(18,
            wx.FONTFAMILY_SWISS, wx.NORMAL, wx.NORMAL)
        self.normalFont = util.createPixelFont(self.cellSize - 2,
            wx.FONTFAMILY_MODERN, wx.NORMAL, wx.BOLD)
        self.bigFont = util.createPixelFont(self.boxSize - 2,
            wx.FONTFAMILY_MODERN, wx.NORMAL, wx.BOLD)

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        util.setWH(self, self.cols * self.cellSize + 2 * self.offset, 460)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wx.Bitmap(size.width, size.height)

    def OnLeftDown(self, event):
        pos = event.GetPosition()

        x = (pos.x - self.offset) // self.cellSize
        y = (pos.y - self.offset) // self.cellSize

        self.selected = None

        if (x >= 0) and (x < self.cols) and (y >= 0) and (y <= self.rows):
            i = y * self.cols + x
            if i < len(self.chars):
                self.selected = self.chars[i]

        self.Refresh(False)

    def OnMotion(self, event):
        if event.LeftIsDown():
            self.OnLeftDown(event)

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, size.width, size.height)

        dc.SetPen(wx.BLACK_PEN)
        dc.SetTextForeground(wx.BLACK)

        for y in range(self.rows + 1):
            util.drawLine(dc, self.offset, self.offset + y * self.cellSize,
                          self.cols * self.cellSize + 1, 0)

        for x in range(self.cols + 1):
            util.drawLine(dc, self.offset + x * self.cellSize,
                self.offset, 0, self.rows * self.cellSize)

        dc.SetFont(self.normalFont)

        for y in range(self.rows):
            for x in range(self.cols):
                i = y * self.cols + x
                if i < len(self.chars):
                    util.drawText(dc, self.chars[i],
                        x * self.cellSize + self.offset + self.cellSize // 2 + 1,
                        y * self.cellSize + self.offset + self.cellSize // 2 + 1,
                        util.ALIGN_CENTER, util.VALIGN_CENTER)

        y = self.offset + self.rows * self.cellSize
        pad = 5

        if self.selected:
            code = ord(self.selected)

            self.drawCharBox(dc, "Selected:", self.selected, self.offset,
                             y + pad, 75)

            c = util.upper(self.selected)
            if c == self.selected:
                c = util.lower(self.selected)
                if c == self.selected:
                    c = None

            if c:
                self.drawCharBox(dc, "Opposite case:", c, self.offset + 150,
                                 y + pad, 110)

            dc.SetFont(self.smallFont)
            dc.DrawText("Character code: %d" % code, 360, y + pad)

            if code == 32:
                dc.DrawText("Normal space", 360, y + pad + 30)
            elif code == 160:
                dc.DrawText("Non-breaking space", 360, y + pad + 30)

        else:
            dc.SetFont(self.smallFont)
            dc.DrawText("Click on a character to select it.", self.offset,
                        y + pad)

    def drawCharBox(self, dc, text, char, x, y, xinc):
        dc.SetFont(self.smallFont)
        dc.DrawText(text, x, y)

        boxX = x + xinc

        dc.DrawRectangle(boxX, y, self.boxSize, self.boxSize)

        dc.SetFont(self.bigFont)
        util.drawText(dc, char, boxX + self.boxSize // 2 + 1,
            y + self.boxSize // 2 + 1, util.ALIGN_CENTER, util.VALIGN_CENTER)
