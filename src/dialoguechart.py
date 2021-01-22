import gutil
import misc
import pdf
import pml
import screenplay
import util
import functools

import wx

def genDialogueChart(mainFrame, sp):
    # TODO: would be nice if this behaved like the other reports, i.e. the
    # junk below would be inside the class, not outside. this would allow
    # testcases to be written. only complication is the minLines thing
    # which would need some thinking.

    inf = []
    for it in [ ("Characters with < 10 lines", None),
                ("Sorted by: First appearance", cmpFirst),
                ("Sorted by: Last appearance", cmpLast),
                ("Sorted by: Number of lines spoken", cmpCount),
                ("Sorted by: Name", cmpName)
                ]:
        inf.append(misc.CheckBoxItem(it[0], cdata = it[1]))

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", inf,
                           "Information to include:", False)

    if dlg.ShowModal() != wx.ID_OK:
        dlg.Destroy()

        return

    dlg.Destroy()

    minLines = 1
    if not inf[0].selected:
        minLines = 10

    chart = DialogueChart(sp, minLines)

    if not chart.cinfo:
        wx.MessageBox("No characters speaking found.", "Error", wx.OK,
                      mainFrame)

        return

    del inf[0]

    if len(misc.CheckBoxItem.getClientData(inf)) == 0:
        wx.MessageBox("Can't disable all output.", "Error", wx.OK,
                      mainFrame)

        return

    data = chart.generate(inf)

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

class DialogueChart:
    def __init__(self, sp, minLines):

        self.sp = sp

        ls = sp.lines

        # PageInfo's for each page, 0-indexed.
        self.pages = []

        for i in range(len(sp.pages) - 1):
            self.pages.append(PageInfo())

        # map of CharInfo objects. key = name, value = CharInfo.
        tmpCinfo = {}

        name = "UNKNOWN"

        for i in range(len(ls)):
            pgNr = sp.line2page(i) -1
            pi = self.pages[pgNr]
            line = ls[i]

            pi.addLine(line.lt)

            if (line.lt == screenplay.CHARACTER) and\
                   (line.lb == screenplay.LB_LAST):
                name = util.upper(line.text)

            elif line.lt == screenplay.DIALOGUE:
                pi.addLineToSpeaker(name)

                ci = tmpCinfo.get(name)

                if ci:
                    ci.addLine(pgNr)
                else:
                    tmpCinfo[name] = CharInfo(name, pgNr)

            elif line.lt != screenplay.PAREN:
                name = "UNKNOWN"

        # CharInfo's.
        self.cinfo = []
        for v in list(tmpCinfo.values()):
            if v.lineCnt >= minLines:
                self.cinfo.append(v)

        # start Y of page markers
        self.pageY = 20.0

        # where dialogue density bars start and how tall they are
        self.barY = 30.0
        self.barHeight = 15.0

        # chart Y pos
        self.chartY = 50.0

        # how much to leave empty on each side (mm)
        self.margin = 10.0

        # try point sizes 10,9,8,7,6 until all characters fit on the page
        # (if 6 is still too big, too bad)
        size = 10
        while 1:
            # character font size in points
            self.charFs = size

            # how many mm in Y direction for each character
            self.charY = util.getTextHeight(self.charFs)

            # height of chart
            self.chartHeight = len(self.cinfo) * self.charY

            if size <= 6:
                break

            if (self.chartY + self.chartHeight) <= \
                   (sp.cfg.paperWidth - self.margin):
                break

            size -= 1

        # calculate maximum length of character name, and start position
        # of chart from that

        maxLen = 0
        for ci in self.cinfo:
            maxLen = max(maxLen, len(ci.name))
        maxLen = max(10, maxLen)

        charX = util.getTextWidth(" ", pml.COURIER, self.charFs)

        # chart X pos
        self.chartX = self.margin + maxLen * charX + 3

        # width of chart
        self.chartWidth = sp.cfg.paperHeight - self.chartX - self.margin

        # page contents bar legends' size and position
        self.legendWidth = 23.0
        self.legendHeight = 23.0
        self.legendX = self.margin + 2.0
        self.legendY = self.barY + self.barHeight - self.legendHeight

        # margin from legend border to first item
        self.legendMargin = 2.0

        # spacing from one legend item to next
        self.legendSpacing = 5.0

        # spacing from one legend item to next
        self.legendSize = 4.0

    def generate(self, cbil):
        doc = pml.Document(self.sp.cfg.paperHeight,
                           self.sp.cfg.paperWidth)

        for it in cbil:
            if it.selected:
                self.cinfo = sorted(self.cinfo, key=functools.cmp_to_key(it.cdata))
                doc.add(self.generatePage(it.text, doc))

        return pdf.generate(doc)

    def generatePage(self, title, doc):
        pg = pml.Page(doc)

        pg.add(pml.TextOp(title, doc.w / 2.0, self.margin, 18,
            pml.BOLD | pml.ITALIC | pml.UNDERLINED, util.ALIGN_CENTER))

        pageCnt = len(self.pages)
        mmPerPage = max(0.1, self.chartWidth / pageCnt)

        pg.add(pml.TextOp("Page:", self.chartX - 1.0, self.pageY - 5.0, 10))

        # draw backround for every other row. this needs to be done before
        # drawing the grid.
        for i in range(len(self.cinfo)):
            y = self.chartY + i * self.charY

            if (i % 2) == 1:
                pg.add(pml.PDFOp("0.93 g"))
                pg.add(pml.RectOp(self.chartX, y, self.chartWidth,
                                  self.charY))
                pg.add(pml.PDFOp("0.0 g"))

        # line width to use
        lw = 0.25

        pg.add(pml.PDFOp("0.5 G"))

        # dashed pattern
        pg.add(pml.PDFOp("[2 2] 0 d"))

        # draw grid and page markers
        for i in range(pageCnt):
            if (i == 0) or ((i + 1) % 10) == 0:
                x = self.chartX + i * mmPerPage
                pg.add(pml.TextOp("%d" % (i + 1), x, self.pageY,
                                  10, align = util.ALIGN_CENTER))
                if i != 0:
                    pg.add(pml.genLine(x, self.chartY, 0, self.chartHeight,
                                        lw))


        pg.add(pml.RectOp(self.chartX, self.chartY, self.chartWidth,
                          self.chartHeight, pml.NO_FILL, lw))

        pg.add(pml.PDFOp("0.0 G"))

        # restore normal line pattern
        pg.add(pml.PDFOp("[] 0 d"))

        # legend for page content bars
        pg.add(pml.RectOp(self.legendX, self.legendY,
            self.legendWidth, self.legendHeight, pml.NO_FILL, lw))

        self.drawLegend(pg, 0, 1.0, "Other", lw)
        self.drawLegend(pg, 1, 0.7, "Character", lw)
        self.drawLegend(pg, 2, 0.5, "Dialogue", lw)
        self.drawLegend(pg, 3, 0.3, "Action", lw)

        # page content bars
        for i in range(pageCnt):
            x = self.chartX + i * mmPerPage
            y = self.barY + self.barHeight
            pi = self.pages[i]
            tlc = pi.getTotalLineCount()

            pg.add(pml.PDFOp("0.3 g"))
            pct = util.safeDivInt(pi.getLineCount(screenplay.ACTION), tlc)
            barH = self.barHeight * pct
            pg.add(pml.RectOp(x, y - barH, mmPerPage, barH))
            y -= barH

            pg.add(pml.PDFOp("0.5 g"))
            pct = util.safeDivInt(pi.getLineCount(screenplay.DIALOGUE), tlc)
            barH = self.barHeight * pct
            pg.add(pml.RectOp(x, y - barH, mmPerPage, barH))
            y -= barH

            pg.add(pml.PDFOp("0.7 g"))
            pct = util.safeDivInt(pi.getLineCount(screenplay.CHARACTER), tlc)
            barH = self.barHeight * pct
            pg.add(pml.RectOp(x, y - barH, mmPerPage, barH))
            y -= barH


        pg.add(pml.PDFOp("0.0 g"))

        # rectangle around page content bars
        pg.add(pml.RectOp(self.chartX, self.barY, self.chartWidth,
                         self.barHeight, pml.NO_FILL, lw))

        for i in range(len(self.cinfo)):
            y = self.chartY + i * self.charY
            ci = self.cinfo[i]

            pg.add(pml.TextOp(ci.name, self.margin, y + self.charY / 2.0,
                self.charFs, valign = util.VALIGN_CENTER))

            for i in range(pageCnt):
                pi = self.pages[i]
                cnt = pi.getSpeakerLineCount(ci.name)

                if cnt > 0:
                    h = self.charY * (float(cnt) / self.sp.cfg.linesOnPage)

                    pg.add(pml.RectOp(self.chartX + i * mmPerPage,
                        y + (self.charY - h) / 2.0, mmPerPage, h))

        return pg

    # draw a single legend for page content bars
    def drawLegend(self, pg, pos, color, name, lw):
        x = self.legendX + self.legendMargin
        y = self.legendY + self.legendMargin + pos * self.legendSpacing

        pg.add(pml.PDFOp("%f g" % color))

        pg.add(pml.RectOp(x, y, self.legendSize, self.legendSize,
                          pml.STROKE_FILL, lw))

        pg.add(pml.PDFOp("0.0 g"))

        pg.add(pml.TextOp(name, x + self.legendSize + 2.0, y, 6))


# keeps track of information for one page
class PageInfo:
    def __init__(self):
        # how many lines of each type this page contains. key = line type,
        # value = int. note that if value would be 0, this doesn't have
        # the key at all, so use the helper functions below.
        self.lineCounts = {}

        # total line count
        self.totalLineCount = -1

        # how many lines each character speaks on this page. key =
        # character name, value = int. note that if someone doesn't speak
        # they have no entry.
        self.speakers = {}

    # add one line of given type.
    def addLine(self, lt):
        self.lineCounts[lt] = self.getLineCount(lt) + 1

    # get total number of lines.
    def getTotalLineCount(self):
        if self.totalLineCount == -1:
            self.totalLineCount = sum(iter(self.lineCounts.values()), 0)

        return self.totalLineCount

    # get number of lines of given type.
    def getLineCount(self, lt):
        return self.lineCounts.get(lt, 0)

    # add one dialogue line for given speaker.
    def addLineToSpeaker(self, name):
        self.speakers[name] = self.getSpeakerLineCount(name) + 1

    # get number of lines of dialogue for given character.
    def getSpeakerLineCount(self, name):
        return self.speakers.get(name, 0)

# keeps track of each character's dialogue lines.
class CharInfo:
    def __init__(self, name, firstPage):
        self.name = name
        self.firstPage = firstPage
        self.lastPage = firstPage
        self.lineCnt = 1

    # add a line at given page.
    def addLine(self, page):
        self.lastPage = page
        self.lineCnt += 1

def cmpfunc(a, b):
    return (a > b) - (a < b)

def cmpCount(c1, c2):
    ret = cmpfunc(c2.lineCnt, c1.lineCnt)

    if ret != 0:
        return ret
    else:
        return cmpFirst(c1, c2)

def cmpCountThenName(c1, c2):
    ret = cmpfunc(c2.lineCnt, c1.lineCnt)

    if ret != 0:
        return ret
    else:
        return cmpName(c1, c2)

def cmpFirst(c1, c2):
    ret = cmpfunc(c1.firstPage, c2.firstPage)

    if ret != 0:
        return ret
    else:
        return cmpLastRev(c1, c2)

def cmpLast(c1, c2):
    ret = cmpfunc(c1.lastPage, c2.lastPage)

    if ret != 0:
        return ret
    else:
        return cmpName(c1, c2)

def cmpLastRev(c1, c2):
    ret = cmpfunc(c2.lastPage, c1.lastPage)

    if ret != 0:
        return ret
    else:
        return cmpCountThenName(c1, c2)

def cmpName(c1, c2):
    return cmpfunc(c1.name, c2.name)
