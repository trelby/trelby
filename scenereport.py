import pdf
import pml
import screenplay
import util

def genSceneReport(mainFrame, sp, cfgGl):
    report = SceneReport(sp)
    data = report.generate()

    util.showTempPDF(data, cfgGl, mainFrame)

class SceneReport:
    def __init__(self, sp):
        self.sp = sp
        
        # list of SceneInfos
        self.scenes = []
        
        line = 0
        while 1:
            if line >= len(sp.lines):
                break
            
            startLine, endLine = sp.getSceneIndexesFromLine(line)

            si = SceneInfo()
            si.read(sp, startLine, endLine)
            self.scenes.append(si)

            line = endLine + 1

        lineSeq = [si.lines for si in self.scenes]
        self.shortestScene = min(lineSeq)
        self.longestScene = max(lineSeq)
        self.avgScene = sum(lineSeq) / float(len(self.scenes))

    def generate(self):
        self.doc = pml.Document(self.sp.cfg.paperWidth,
                                self.sp.cfg.paperHeight)

        # how much to leave empty on each side (mm)
        self.margin = 15.0

        # normal font
        self.fontSize = 12

        # scene name font
        nameFs = 14

        self.pg = pml.Page(self.doc)
        self.y = self.margin

        self.addText("Minimum / maximum / average scene length in lines:"
                     " %d / %d / %.2f" % (self.shortestScene,
                                          self.longestScene, self.avgScene))
        for si in self.scenes:
            self.y += 5.0
            
            self.addText("%-4s %s" % (si.number, si.name),
                         style = pml.BOLD)

            self.y += 1.0
            
            if si.lines != 0:
                tmp = "%d" % ((100 * si.actionLines) / si.lines)
            else:
                tmp = "0"
                
            self.addText("     Lines: %d (%s%% action), Pages: %d (%s)" % (
                si.lines, tmp, len(si.pages),
                si.getPageList()))

            self.y += 2.5
            
            for it in util.sortDict(si.chars):
                self.addText("     %3d  %s" % (it[1], it[0]))
            
        self.doc.add(self.pg)

        return pdf.generate(self.doc)
    
    def addText(self, text, x = None, fs = None, style = pml.NORMAL):
        if x == None:
            x = self.margin

        if fs == None:
            fs = self.fontSize

        yd = util.getTextHeight(fs)

        if (self.y + yd) > (self.sp.cfg.paperHeight - self.margin):
            self.doc.add(self.pg)
            self.pg = pml.Page(self.doc)
            self.y = self.margin
            
        self.pg.add(pml.TextOp(text, x, self.y, fs, style))

        self.y += yd

# information about one scene
class SceneInfo:
    def __init__(self):
        # scene number, e.g. "42A"
        self.number = None
        
        # scene name, e.g. "INT. MOTEL ROOM - NIGHT"
        self.name = None

        # total lines, excluding scene lines
        self.lines = 0

        # action lines
        self.actionLines = 0

        # list of page numbers (strings)
        self.pages = []

        # key = character name (upper cased), value = number of dialogue
        # lines
        self.chars = {}

    # read information for scene within given lines.
    def read(self, sp, startLine, endLine):
        self.number = sp.getSceneNumber(startLine)

        ls = sp.lines
        
        # TODO: handle multi-line scene names
        if ls[startLine].lt == screenplay.SCENE:
            s = util.upper(ls[startLine].text)

            if len(s.strip()) == 0:
                self.name = "(EMPTY SCENE NAME)"
            else:
                self.name = s
        else:
            self.name = "(NO SCENE NAME)"

        self.addPage(str(sp.line2page(startLine)))

        line = startLine

        # skip over scene headers
        while (line <= endLine) and (ls[line].lt == screenplay.SCENE):
            line = sp.getElemLastIndexFromLine(line) + 1

        if line > endLine:
            # empty scene
            return

        # re-define startLine to be first line after scene header
        startLine = line

        self.lines = endLine - startLine + 1

        # get number of action lines and store page information
        for i in range(startLine, endLine + 1):
            self.addPage(str(sp.line2page(i)))
            
            if ls[i].lt == screenplay.ACTION:
                self.actionLines += 1

        line = startLine
        while 1:
            line = self.readSpeech(sp, line, endLine)
            if line >= endLine:
                break

    # read information for one (or zero) speech, beginning at given line.
    # return line number of the last line of the speech + 1, or endLine +
    # 1 if no speech found.
    def readSpeech(self, sp, line, endLine):
        ls = sp.lines

        # find start of speech
        while (line < endLine) and (ls[line].lt != screenplay.CHARACTER):
            line += 1
        
        if line >= endLine:
            # no speech found, or CHARACTER was on last line, leaving no
            # space for dialogue.
            return endLine

        # TODO: handle multi-line character names
        s = util.upper(ls[line].text)
        if len(s.strip()) == 0:
            name = "(EMPTY CHARACTER NAME)"
        else:
            name = s

        # skip over character name
        line = sp.getElemLastIndexFromLine(line) + 1

        # dialogue lines
        dlines = 0
        
        while 1:
            if line > endLine:
                break

            lt = ls[line].lt

            if lt == screenplay.DIALOGUE:
                dlines += 1
            elif lt != screenplay.PAREN:
                break

            line += 1

        if dlines > 0:
            self.chars[name] = self.chars.get(name, 0) + dlines
            
        return line

    # add page to page list if it's not already there
    def addPage(self, page):
        if self.pages and (self.pages[-1] == page):
            return
            
        self.pages.append(page)

    # get page list as a string
    def getPageList(self):
        p1 = self.pages[0]
        p2 = self.pages[-1]

        if p1 == p2:
            return p1
        else:
            return "%s-%s" % (p1, p2)
