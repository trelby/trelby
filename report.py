import config
import misc
import pdf
import pml
import util

import textwrap

from wxPython.wx import *

def genCharacterReport(mainFrame, ctrl, cfg):
    tmp = CharacterReport(ctrl, cfg)

    if not tmp.cinfo:
        wxMessageBox("No characters speaking found.",
                     "Error", wxOK, mainFrame)

        return

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", (300, 400),
        tmp.infList, "Information to include:", False, 1,
        util.listify(tmp.cinfo, "name"), "Characters to include:", True, 4)

    ok = False
    if dlg.ShowModal() == wxID_OK:
        ok = True

        for i in range(len(tmp.infList)):
            tmp.inf[i] = dlg.res1[i]

        for i in range(len(tmp.cinfo)):
            tmp.cinfo[i].include = dlg.res2[i]

    dlg.Destroy()

    if not ok:
        return
    
    data = tmp.generate()

    util.showTempPDF(data, cfg, mainFrame)
    
class CharacterReport:
    def __init__(self, ctrl, cfg):

        self.cfg = cfg
        
        ls = ctrl.sp.lines

        # key = character name, value = CharInfo
        chars = {}

        name = None
        scene = None
        
        # how many lines processed for current speech
        curSpeechLines = 0
        
        for i in xrange(len(ls)):
            line = ls[i]

            if (line.lt == config.SCENE) and\
                   (line.lb == config.LB_LAST):
                scene = util.upper(line.text)
                
            elif (line.lt == config.CHARACTER) and\
                   (line.lb == config.LB_LAST):
                name = util.upper(line.text)
                curSpeechLines = 0
                
            elif line.lt in (config.DIALOGUE, config.PAREN) and name:
                ci = chars.get(name)
                if not ci:
                    ci = CharInfo(name)
                    chars[name] = ci

                if scene:
                    ci.scenes[scene] = ci.scenes.get(scene, 0) + 1

                if curSpeechLines == 0:
                    ci.speechCnt += 1

                curSpeechLines += 1
                ci.lineCnt += 1

                words = util.splitToWords(line.text)
                
                ci.wordCnt += len(words)
                ci.wordCharCnt += reduce(lambda x, y: x + len(y), words, 0)
                
                ci.addPage(ctrl.line2page(i))

            else:
                name = None
                curSpeechLines = 0

        # list of CharInfo objects
        self.cinfo = []
        for v in chars.values():
            self.cinfo.append(v)

        self.cinfo.sort(cmpLines)

        self.totalSpeechCnt = self.sum("speechCnt")
        self.totalLineCnt = self.sum("lineCnt")
        self.totalWordCnt = self.sum("wordCnt")
        self.totalWordCharCnt = self.sum("wordCharCnt")

        # information types and what to include
        self.INF_BASIC, self.INF_PAGES, self.INF_LOCATIONS = range(3)
        self.infList = ["Basic information", "Page list", "Location list"]
        self.inf = [True] * len(self.infList)

    # calculate total sum of self.cinfo.{name} and return it.
    def sum(self, name):
        return reduce(lambda tot, ci: tot + getattr(ci, name), self.cinfo, 0)
        
    def generate(self):
        self.doc = pml.Document(self.cfg.paperWidth, self.cfg.paperHeight,
                           self.cfg.paperType)

        # how much to leave empty on each side (mm)
        self.margin = 20.0

        # normal font
        self.fontSize = 12

        charsToLine = int((self.cfg.paperWidth - self.margin * 2.0) /
                          util.points2x(self.fontSize))
        
        # character name font
        nameFs = 14

        self.pg = pml.Page(self.doc)
        self.y = self.margin

        for ci in self.cinfo:
            if not ci.include:
                continue
            
            self.addText(ci.name, fs = nameFs,
                         style = pml.BOLD | pml.UNDERLINED)

            if self.inf[self.INF_BASIC]:
                self.addText("Speeches: %d, Lines: %d (%.2f%%),"
                             " per speech: %.2f" %
                             (ci.speechCnt, ci.lineCnt,
                              (ci.lineCnt * 100.0) / self.totalLineCnt,
                              ci.lineCnt / float(ci.speechCnt)))
                self.addText("Words: %d, per speech: %.2f,"
                             " characters per: %.2f"
                             % (ci.wordCnt, ci.wordCnt / float(ci.speechCnt),
                                ci.wordCharCnt / float(ci.wordCnt)))

                
            if self.inf[self.INF_PAGES]:
                pl = ci.getPageList()
                plWrapped = textwrap.wrap("Pages: %d, list: " % len(ci.pages)
                    + pl, charsToLine, subsequent_indent = "       ")

                for l in plWrapped:
                    self.addText(l)

            if self.inf[self.INF_LOCATIONS]:
                self.y += 2.5

                tmp = []
                for k, v in ci.scenes.iteritems():
                    tmp.append(SceneSpeakInfo(k, v))

                tmp.sort(cmpSpeakLines)

                for sc in tmp:
                    self.addText("%3d %s" % (sc.lines, sc.scene),
                                 x = self.margin * 2.0, fs = 10)
            
            self.y += 5.0
            
        self.doc.add(self.pg)

        return pdf.generate(self.doc)
    
    def addText(self, text, x = None, fs = None, style = pml.NORMAL):
        if x == None:
            x = self.margin

        if fs == None:
            fs = self.fontSize

        yd = util.points2y(fs)

        if (self.y + yd) > (self.cfg.paperHeight - self.margin):
            self.doc.add(self.pg)
            self.pg = pml.Page(self.doc)
            self.y = self.margin
            
        self.pg.add(pml.TextOp(text, x, self.y, fs, style))

        self.y += yd

# information about one character
class CharInfo:
    def __init__(self, name):
        self.name = name

        self.speechCnt = 0
        self.lineCnt = 0
        self.wordCnt = 0
        self.wordCharCnt = 0
        self.pages = []
        self.scenes = {}
        self.include = True
        
    def addPage(self, page):
        if self.pages and (self.pages[-1] == page):
            return
            
        self.pages.append(page)

    # return textual representation of pages where consecutive pages are
    # formatted as "x-y".
    def getPageList(self):
        s = ""

        i = 0
        while 1:
            if i >= len(self.pages):
                break

            p = self.pages[i]
            
            if s != "":
                s += ", "

            s += str(p)
            pg = util.str2int(p, -1)

            if pg != -1:
                endPage = pg
                j = i + 1
                while 1:
                    if j >= len(self.pages):
                        break

                    pg2 = util.str2int(self.pages[j], -1)

                    if pg2 != (endPage + 1):
                        break

                    endPage = pg2
                    j += 1

                if endPage != pg:
                    s += "-%d" % (endPage)
                    i = j
                else:
                    i += 1
            else:
                # fancy page number, e.g. "72A", can't do ranges with them
                i += 1
            
        return s

def cmpLines(c1, c2):
    ret = cmp(c2.lineCnt, c1.lineCnt)

    if ret != 0:
        return ret
    else:
        return cmp(c1.name, c2.name)

# temporary holder for sorting one speaker's scenes
class SceneSpeakInfo:
    def __init__(self, scene, lines):
        self.scene = scene
        self.lines = lines
    
def cmpSpeakLines(ss1, ss2):
    ret = cmp(ss2.lines, ss1.lines)

    if ret != 0:
        return ret
    else:
        return cmp(ss1.scene, ss2.scene)
