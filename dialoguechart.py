import misc
import pdf
import pml
import screenplay
import util

from wxPython.wx import *

# show all all dialogue charts as a PDF document
def genDialogueChart(mainFrame, sp):

    # TODO: would be nice if this behaved like the other reports, i.e. the
    # junk below would be inside the class, not outside. this would allow
    # testcases to be written. only complication is the minPages thing
    # which would need some thinking.

    inf = []
    for it in [ ("Characters appearing on a single page", None),
                ("Sorted by: First appearance", cmpFirst),
                ("Sorted by: Last appearance", cmpLast),
                ("Sorted by: Number of appearances", cmpCount),
                ("Sorted by: Name", cmpName)
                ]:
        inf.append(misc.CheckBoxItem(it[0], cdata = it[1]))
    

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", inf,
                           "Information to include:", False)

    if dlg.ShowModal() != wxID_OK:
        dlg.Destroy()

        return

    dlg.Destroy()

    minPages = 1
    if not inf[0].selected:
        minPages = 2

    chart = DialogueChart(sp, minPages)

    if not chart.cinfo:
        wxMessageBox("No characters speaking found.", "Error", wxOK,
                     mainFrame)

        return

    del inf[0]
    
    if len(misc.CheckBoxItem.getClientData(inf)) == 0:
        wxMessageBox("Can't disable all output.", "Error", wxOK,
                     mainFrame)

        return
        
    data = chart.generate(inf)

    util.showTempPDF(data, sp.cfgGl, mainFrame)
    
class DialogueChart:
    def __init__(self, sp, minPages):

        self.sp = sp
        
        ls = sp.lines

        # appearances by each character. index = page (0-indexed), value =
        # map of characters speaking on that page
        self.pages = []

        # dialogue density, 0.0 - 1.0, proportion of dialogue lines on
        # each page
        self.diagDens = []
        
        for i in xrange(len(sp.pages) - 1):
            self.pages.append({})

        curPage = 0
        diagLines = 0
        totalLines = 0
        name = "UNKNOWN"
        diagTypes = [screenplay.CHARACTER, screenplay.DIALOGUE,
                     screenplay.PAREN]
        characters = {}
        
        for i in xrange(len(ls)):
            page = sp.line2page(i) - 1
            line = ls[i]

            if page != curPage:
                if totalLines == 0:
                    totalLines = 1
                self.diagDens.append((float(diagLines) / totalLines))
                curPage = page
                diagLines = 0
                totalLines = 0

            totalLines += 1
            if line.lt in diagTypes:
                diagLines += 1
            
            if (line.lt == screenplay.CHARACTER) and\
                   (line.lb == screenplay.LB_LAST):
                name = util.upper(line.text)
                characters[name] = None
                
            elif line.lt in (screenplay.DIALOGUE, screenplay.PAREN):
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
            if v.pageCnt >= minPages:
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

    def generate(self, cbil):
        doc = pml.Document(self.sp.cfg.paperHeight,
                           self.sp.cfg.paperWidth)

        for it in cbil:
            if it.selected:
                self.cinfo.sort(it.cdata)
                doc.add(self.generatePage(it.text, doc))
        
        return pdf.generate(doc)

    def generatePage(self, title, doc):
        pg = pml.Page(doc)

        pg.add(pml.TextOp(title, doc.w / 2.0, self.margin, 18,
            pml.BOLD | pml.ITALIC | pml.UNDERLINED, util.ALIGN_CENTER))

        pageCnt = len(self.pages)
        mmPerPage = max(0.1, self.chartWidth / pageCnt)

        pg.add(pml.TextOp("Page:  ", self.chartX, self.pageY, 10,
                          align = util.ALIGN_RIGHT))

        # draw backround for every other row. this needs to be done before
        # drawing the grid.
        for i in range(len(self.cinfo)):
            y = self.chartY + i * self.charY
            
            if (i % 2) == 1:
                pg.add(pml.PDFOp("0.93 g")) 
                pg.add(pml.RectOp(self.chartX, y, self.chartWidth,
                                  self.charY, -1, True))
                pg.add(pml.PDFOp("0.0 g"))

        # line width to use
        lw = 0.25

        pg.add(pml.PDFOp("0.5 G"))
        pg.add(pml.PDFOp("[2 2] 0 d"))
        
        # draw grid and page markers
        for i in xrange(pageCnt):
            if (i == 0) or ((i + 1) % 10) == 0:
                x = self.chartX + i * mmPerPage
                pg.add(pml.TextOp("%d" % (i + 1), x, self.pageY,
                                  10, align = util.ALIGN_CENTER))
                if i != 0:
                    pg.add(pml.genLine(x, self.chartY, 0, self.chartHeight,
                                        lw))


        pg.add(pml.RectOp(self.chartX, self.chartY, self.chartWidth,
                          self.chartHeight, lw))

        pg.add(pml.PDFOp("0.0 G"))
        pg.add(pml.PDFOp("[] 0 d"))

        pg.add(pml.TextOp("Dialogue density: ", self.chartX,
            self.barY + self.barHeight / 2.0, 6, align = util.ALIGN_RIGHT,
            valign = util.VALIGN_CENTER))
        pg.add(pml.TextOp("100% ", self.chartX, self.barY, 8,
                          align = util.ALIGN_RIGHT))
        pg.add(pml.TextOp("0% ", self.chartX, self.barY + self.barHeight, 8,
            align = util.ALIGN_RIGHT, valign = util.VALIGN_BOTTOM))

        # draw dialogue density bars

        pg.add(pml.PDFOp("0.5 g")) 
       
        for i in xrange(pageCnt):
            x = self.chartX + i * mmPerPage
            barH = self.barHeight * self.diagDens[i]
            pg.add(pml.RectOp(x, self.barY + (self.barHeight - barH),
                             mmPerPage, barH, -1, True))

        pg.add(pml.PDFOp("0.0 g"))

        pg.add(pml.RectOp(self.chartX, self.barY, self.chartWidth,
                         self.barHeight, lw))

        barH = self.charY - (self.charY / 5.0)
        
        for i in range(len(self.cinfo)):
            y = self.chartY + i * self.charY
            ci = self.cinfo[i]
            
            if misc.license:
                name = ci.name
            else:
                name = "EVALUATION"
                
            pg.add(pml.TextOp(name, self.margin, y + self.charY / 2.0,
                self.charFs, valign = util.VALIGN_CENTER))
            
            for i in xrange(pageCnt):
                m = self.pages[i]

                if ci.name in m:
                    pg.add(pml.RectOp(self.chartX + i * mmPerPage,
                        y + (self.charY - barH) / 2.0, mmPerPage, barH,
                        -1, True))
                
        return pg

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
    
def cmpCountThenName(c1, c2):
    ret = cmp(c2.pageCnt, c1.pageCnt)

    if ret != 0:
        return ret
    else:
        return cmpName(c1, c2)
    
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
        return cmpCountThenName(c1, c2)
    
def cmpName(c1, c2):
    return cmp(c1.name, c2.name)
