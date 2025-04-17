import wx

import trelby.util as util


class TitlesPreview(wx.Window):
    def __init__(self, parent, ctrl, cfg):
        wx.Window.__init__(self, parent, -1)

        self.cfg = cfg
        self.ctrl = ctrl

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_PAINT, self.OnPaint)

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wx.Bitmap(size.width, size.height)

    def OnEraseBackground(self, event):
        pass

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.screenBuf)

        # widget size
        ww, wh = self.GetClientSize()

        dc.SetBrush(wx.Brush(self.GetBackgroundColour()))
        dc.SetPen(wx.Pen(self.GetBackgroundColour()))
        dc.DrawRectangle(0, 0, ww, wh)

        # aspect ratio of paper
        aspect = self.cfg.paperWidth / self.cfg.paperHeight

        # calculate which way we can best fit the paper on screen
        h = wh
        w = int(aspect * wh)

        if w > ww:
            w = ww
            h = int(ww / aspect)

        # offset of paper
        ox = (ww - w) // 2
        oy = (wh - h) // 2

        dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(ox, oy, w, h)

        if self.ctrl.pageIndex != -1:
            page = self.ctrl.titles.pages[self.ctrl.pageIndex]

            for i in range(len(page)):
                ts = page[i]

                # text height in mm
                textHinMM = util.getTextHeight(ts.size)

                textH = int((textHinMM / self.cfg.paperHeight) * h)
                textH = max(1, textH)
                y = ts.y

                for line in ts.items:
                    # people may have empty lines in between non-empty
                    # lines to achieve double spaced lines; don't draw a
                    # rectangle for lines consisting of nothing but
                    # whitespace

                    if line.strip():
                        textW = int(
                            (
                                util.getTextWidth(line, ts.getStyle(), ts.size)
                                / self.cfg.paperWidth
                            )
                            * w
                        )
                        textW = max(1, textW)

                        if ts.isCentered:
                            xp = w // 2 - textW // 2
                        else:
                            xp = int((ts.x / self.cfg.paperWidth) * w)

                        if ts.isRightJustified:
                            xp -= textW

                        if i == self.ctrl.tsIndex:
                            dc.SetPen(wx.RED_PEN)
                            dc.SetBrush(wx.RED_BRUSH)
                        else:
                            dc.SetPen(wx.BLACK_PEN)
                            dc.SetBrush(wx.BLACK_BRUSH)

                        yp = int((y / self.cfg.paperHeight) * h)

                        dc.DrawRectangle(ox + xp, oy + yp, textW, textH)

                    y += textHinMM
