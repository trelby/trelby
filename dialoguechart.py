import math
import config
import misc
import util
from wxPython.wx import *

class DialogueChartDlg(wxDialog):
    def __init__(self, parent, ctrl):
        wxDialog.__init__(self, parent, -1, "Dialogue chart",
            pos = wxDefaultPosition, size = (1, 1),
            style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER | wxMAXIMIZE_BOX)

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        hsizer.Add(wxStaticText(self, -1, "Sort by: "), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        
        self.sortCb = wxComboBox(self, -1, style = wxCB_READONLY)
        self.sortCb.Append("First appearance", cmpFirst)
        self.sortCb.Append("Last appearance", cmpLast)
        self.sortCb.Append("Number of appearances", cmpCount)
        self.sortCb.Append("Name", cmpName)

        sz = self.sortCb.GetSize()
        sz.width = 175
        self.sortCb.SetSize(sz)

        hsizer.Add(self.sortCb, 1)

        vsizer.Add(hsizer, 0, wxALIGN_CENTRE | wxTOP | wxBOTTOM, 5)

        # record how much space non-chart things take
        self.topStuffHeight = sz.height + 10
        
        self.chart = MyDiagChart(self, ctrl)
        vsizer.Add(self.chart, 1, wxEXPAND)

        self.Layout()

        EVT_COMBOBOX(self, self.sortCb.GetId(), self.OnSortCombo)

        self.sortCb.SetSelection(0)
        self.OnSortCombo()

    def OnSortCombo(self, event = None):
        sel = self.sortCb.GetSelection()
        if sel != -1:
            self.chart.cinfo.sort(self.sortCb.GetClientData(sel))

        self.chart.Refresh(False)
        
class MyDiagChart(wxWindow):
    def __init__(self, parent, ctrl):
        wxWindow.__init__(self, parent, -1)

        self.ctrl = ctrl

        ls = self.ctrl.sp.lines

        # appearances by each character. index = page (0-indexed), value =
        # map of characters speaking on that page
        self.pages = []

        # map of characters
        self.characters = {}

        # dialogue density, 0.0 - 1.0, proportion of dialogue lines on
        # each page
        self.diagDens = []
        
        # selected item, or -1
        self.selectedItem = -1
        
        for i in xrange(len(self.ctrl.pages) - 1):
            self.pages.append({})

        curPage = 0
        diagLines = 0
        totalLines = 0
        name = "UNKNOWN"
        diagTypes = [config.CHARACTER, config.DIALOGUE, config.PAREN]
        
        for i in xrange(len(ls)):
            page = self.ctrl.line2page(i) - 1
            line = ls[i]

            if page != curPage:
                if totalLines == 0:
                    totalLines = 1
                self.diagDens.append((float(diagLines) / totalLines))
                curPage = page
                diagLines = 0
                totalLines = 0

            totalLines += 1
            if line.type in diagTypes:
                diagLines += 1
            
            if (line.type == config.CHARACTER) and\
                   (line.lb == config.LB_LAST):
                name = util.upper(line.text)
                self.characters[name] = None
                
            elif line.type in (config.DIALOGUE, config.PAREN):
                self.pages[page][name] = None

        self.diagDens.append((float(diagLines) / totalLines))

        tmpMap = {}
        for i in xrange(len(self.pages)):
            for c in self.pages[i]:
                item = tmpMap.get(c)
                if item:
                    item.addPage(i)
                else:
                    tmpMap[c] = CharInfo(c, i)

        # character info, list of CharInfo objects
        self.cinfo = []
        for v in tmpMap.values():
            self.cinfo.append(v)

        # windows and linux have very different ideas about font sizes
        if wxPlatform == "__WXGTK__":
            self.font = wxFont(12, wxMODERN, wxNORMAL, wxNORMAL)
            self.smallFont = wxFont(10, wxMODERN, wxNORMAL, wxNORMAL)
        else:
            self.font = wxFont(8, wxMODERN, wxNORMAL, wxNORMAL)
            self.smallFont = wxFont(8, wxMODERN, wxNORMAL, wxNORMAL)

        # how many pixels for character names
        self.charPix = 125

        # how many pixels for page indicators
        self.pagePix = 20

        # how many pixels in Y direction for each character
        self.yPix = 10

        # how tall dialogue density bars are
        self.barHeight = 50

        # where does the actual dialogue chart start in Y-dir
        self.startY = 85

        # how much to leave empty on each side
        self.margin = 5

        # total length of chart-portion
        self.chartHeight = len(self.characters) * self.yPix

        EVT_PAINT(self, self.OnPaint)
        EVT_LEFT_DOWN(self, self.OnLeftDown)
        EVT_SIZE(self, self.OnSize)

        p = self.GetParent()
        p.SetClientSize(wxSize(800, self.startY + self.chartHeight +
                               self.margin * 2 + p.topStuffHeight))

    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)

    def OnLeftDown(self, event):
        pos = event.GetPosition()
        self.selectedItem = (pos.y - self.startY) / self.yPix
        self.Refresh(False)

    def OnPaint(self, event):
        dc = wxBufferedPaintDC(self, self.screenBuf)

        black = wxColour(0, 0, 0)
        gray = wxColour(192, 192, 192)
        darkGray = wxColour(96, 96, 96)

        dc.SetFont(self.font)
        dc.SetTextForeground(black)

        w, h = self.GetClientSizeTuple()
        
        whiteBr = wxBrush(wxColour(255,255,255))
        dc.SetBrush(whiteBr)
        dc.DrawRectangle(0, 0, w, h)

        pageCnt = len(self.pages)
        pixelsPerPage = max(1.0, float(w - self.margin - self.charPix) /
                            pageCnt)
        pixelsPerPageInt = int(math.ceil(pixelsPerPage))

        chartWidth = int(pageCnt * pixelsPerPage)
        
        blackBr = wxBrush(black)
        grayBr = wxBrush(gray)
        darkGrayBr = wxBrush(darkGray)

        blackPen = wxPen(black)
        grayPen = wxPen(gray)
        darkGrayPen = wxPen(darkGray)
        
        dc.SetPen(wxPen(wxColour(128, 128, 128), style = wxDOT))

        util.drawText(dc, "Page:  ", self.charPix, self.margin,
                      util.ALIGN_RIGHT)

        # draw grid
        for i in xrange(pageCnt):
            if (i == 0) or ((i + 1) % 10) == 0:
                x = int(self.charPix + i * pixelsPerPage)
                util.drawText(dc, "%d" % (i + 1), x, self.margin,
                              util.ALIGN_CENTER)
                util.drawLine(dc, x, self.startY, 0,
                              self.chartHeight)

        util.drawLine(dc, self.charPix + chartWidth, self.startY, 0,
                      self.chartHeight)
        util.drawLine(dc, self.charPix, self.startY, chartWidth, 0)
        util.drawLine(dc, self.charPix, self.startY + self.chartHeight,
                      chartWidth, 0)

        # draw dialogue density bars
        dc.SetFont(self.smallFont)

        dc.DrawText("Dialogue density:", self.margin, 50)
        util.drawText(dc, "100% ", self.charPix - 2, 30, util.ALIGN_RIGHT)
        util.drawText(dc, "0% ", self.charPix - 2, 30 + self.barHeight,
                      util.ALIGN_RIGHT, util.VALIGN_BOTTOM)

        dc.SetFont(self.font)

        dc.SetPen(blackPen)
        dc.SetBrush(whiteBr)
        dc.DrawRectangle(self.charPix - 1, 30 - 1, chartWidth + 2,
                         self.barHeight + 2)
        
        dc.SetPen(darkGrayPen)
        dc.SetBrush(darkGrayBr)
        
        for i in xrange(pageCnt):
            x = int(self.charPix + i * pixelsPerPage)
            barH = int(self.barHeight * self.diagDens[i])
            dc.DrawRectangle(x, 30 + (self.barHeight - barH),
                             pixelsPerPageInt, barH)

        # draw character info
        dc.SetPen(blackPen)
        dc.SetBrush(blackBr)
                
        cnt = 0
        for ci in self.cinfo:
            y = self.startY + cnt * self.yPix
            
            if cnt == self.selectedItem:
                dc.SetPen(grayPen)
                dc.SetBrush(grayBr)
                
                dc.DrawRectangle(self.margin, y,
                                 self.charPix + chartWidth - self.margin,
                                 self.yPix)
                
                dc.SetPen(blackPen)
                dc.SetBrush(blackBr)

            if not misc.isEval:
                name = ci.name
            else:
                name = "BUY ME"

            util.drawText(dc, name, self.margin, y + self.yPix/2,
                          valign = util.VALIGN_CENTER)
            
            for i in xrange(pageCnt):
                m = self.pages[i]

                if ci.name in m:
                    dc.DrawRectangle(int(self.charPix + i * pixelsPerPage),
                        y, pixelsPerPageInt, self.yPix - 1)
                
            cnt += 1

# keeps track of each character's appearances
class CharInfo:
    def __init__(self, name, firstPage):
        self.name = name
        self.firstPage = firstPage
        self.lastPage = firstPage
        self.pageCnt = 1

    def addPage(self, page):
        self.lastPage = page
        self.pageCnt += 1

def cmpCount(c1, c2):
    ret = cmp(c2.pageCnt, c1.pageCnt)
    if ret != 0:
        return ret
    else:
        return cmpFirst(c1, c2)
    
def cmpFirst(c1, c2):
    ret = cmp(c1.firstPage, c2.firstPage)
    if ret != 0:
        return ret
    else:
        return cmpLastRev(c1, c2)
    
def cmpLast(c1, c2):
    ret = cmp(c1.lastPage, c2.lastPage)
    if ret != 0:
        return ret
    else:
        return cmpName(c1, c2)
    
def cmpLastRev(c1, c2):
    ret = cmp(c2.lastPage, c1.lastPage)
    if ret != 0:
        return ret
    else:
        return cmpName(c1, c2)
    
def cmpName(c1, c2):
    ret = cmp(c1.name, c2.name)

    return ret
