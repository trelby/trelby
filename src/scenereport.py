import misc
import pdf
import pml
import screenplay
import util

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

            si = SceneInfo(sp)
            si.read(sp, startLine, endLine)
            self.scenes.append(si)

            line = endLine + 1

        # we don't use these, but ScriptReport does
        lineSeq = [si.lines for si in self.scenes]
        self.longestScene = max(lineSeq)
        self.avgScene = sum(lineSeq) / float(len(self.scenes))

        # information about what to include (and yes, the comma is needed
        # to unpack the list)
        self.INF_SPEAKERS, = range(1)
        self.inf = []
        for s in ["Speakers"]:
            self.inf.append(misc.CheckBoxItem(s))

    def generate(self):
        tf = pml.TextFormatter(self.sp.cfg.paperWidth,
                               self.sp.cfg.paperHeight, 15.0, 12)

        for si in self.scenes:
            tf.addSpace(5.0)

            tf.addText("%-4s %s" % (si.number, si.name), style = pml.BOLD)

            tf.addSpace(1.0)

            tf.addText("     Lines: %d (%s%% action), Pages: %d"
                " (%s)" % (si.lines, util.pct(si.actionLines, si.lines),
                len(si.pages), si.pages))

            if self.inf[self.INF_SPEAKERS].selected:
                tf.addSpace(2.5)

                for it in util.sortDict(si.chars):
                    tf.addText("     %3d  %s" % (it[1], it[0]))

        return pdf.generate(tf.doc)

# information about one scene
class SceneInfo:
    def __init__(self, sp):
        # scene number, e.g. "42A"
        self.number = None

        # scene name, e.g. "INT. MOTEL ROOM - NIGHT"
        self.name = None

        # total lines, excluding scene lines
        self.lines = 0

        # action lines
        self.actionLines = 0

        # page numbers
        self.pages = screenplay.PageList(sp.getPageNumbers())

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

        self.pages.addPage(sp.line2page(startLine))

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
            self.pages.addPage(sp.line2page(i))

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
