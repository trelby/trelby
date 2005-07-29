import misc
import pdf
import pml
import screenplay
import util

from wxPython.wx import *

def genCharacterReport(mainFrame, sp, addDs):
    report = CharacterReport(sp)

    if not report.cinfo:
        wxMessageBox("No characters speaking found.",
                     "Error", wxOK, mainFrame)

        return

    charNames = []
    for s in util.listify(report.cinfo, "name"):
        charNames.append(misc.CheckBoxItem(s))
    
    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False, charNames,
        "Characters to include:", True)

    ok = False
    if dlg.ShowModal() == wxID_OK:
        ok = True

        for i in range(len(report.cinfo)):
            report.cinfo[i].include = charNames[i].selected

    dlg.Destroy()

    if not ok:
        return
    
    data = report.generate(addDs)

    util.showTempPDF(data, sp.cfgGl, mainFrame)
    
class CharacterReport:
    def __init__(self, sp):

        self.sp = sp
        
        ls = sp.lines

        # key = character name, value = CharInfo
        chars = {}

        name = None
        scene = "(NO SCENE NAME)"
        
        # how many lines processed for current speech
        curSpeechLines = 0
        
        for i in xrange(len(ls)):
            line = ls[i]

            if (line.lt == screenplay.SCENE) and\
                   (line.lb == screenplay.LB_LAST):
                scene = util.upper(line.text)
                
            elif (line.lt == screenplay.CHARACTER) and\
                   (line.lb == screenplay.LB_LAST):
                name = util.upper(line.text)
                curSpeechLines = 0
                
            elif line.lt in (screenplay.DIALOGUE, screenplay.PAREN) and name:
                ci = chars.get(name)
                if not ci:
                    ci = CharInfo(name, sp)
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
                
                ci.pages.addPage(sp.line2page(i))

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
        self.inf = []
        for s in ["Basic information", "Page list", "Location list"]:
            self.inf.append(misc.CheckBoxItem(s))

    # calculate total sum of self.cinfo.{name} and return it.
    def sum(self, name):
        return reduce(lambda tot, ci: tot + getattr(ci, name), self.cinfo, 0)
        
    def generate(self, addDs):
        tf = pml.TextFormatter(self.sp.cfg.paperWidth,
                               self.sp.cfg.paperHeight, 20.0, 12, addDs)

        for ci in self.cinfo:
            if not ci.include:
                continue
            
            tf.addText(ci.name, fs = 14,
                       style = pml.BOLD | pml.UNDERLINED)

            if self.inf[self.INF_BASIC].selected:
                tf.addText("Speeches: %d, Lines: %d (%.2f%%),"
                    " per speech: %.2f" % (ci.speechCnt, ci.lineCnt,
                    (ci.lineCnt * 100.0) / self.totalLineCnt,
                    ci.lineCnt / float(ci.speechCnt)))

                tf.addText("Words: %d, per speech: %.2f,"
                    " characters per: %.2f" % (ci.wordCnt,
                    ci.wordCnt / float(ci.speechCnt),
                    ci.wordCharCnt / float(ci.wordCnt)))
                
            if self.inf[self.INF_PAGES].selected:
                tf.addWrappedText("Pages: %d, list: %s" % (len(ci.pages),
                    ci.pages), "       ")

            if self.inf[self.INF_LOCATIONS].selected:
                tf.addSpace(2.5)

                for it in util.sortDict(ci.scenes):
                    tf.addText("%3d %s" % (it[1], it[0]),
                               x = tf.margin * 2.0, fs = 10)
            
            tf.addSpace(5.0)
            
        return pdf.generate(tf.doc)

# information about one character
class CharInfo:
    def __init__(self, name, sp):
        self.name = name

        self.speechCnt = 0
        self.lineCnt = 0
        self.wordCnt = 0
        self.wordCharCnt = 0
        self.scenes = {}
        self.include = True
        self.pages = screenplay.PageList(sp.getPageNumbers())

def cmpLines(c1, c2):
    ret = cmp(c2.lineCnt, c1.lineCnt)

    if ret != 0:
        return ret
    else:
        return cmp(c1.name, c2.name)
