# -*- coding: utf-8 -*-

# linebreak types

LB_SPACE = 1

# we don't use this anymore, but we have to keep it in order to be able to
# load old scripts
LB_SPACE2 = 2

LB_NONE = 3
LB_FORCED = 4
LB_LAST = 5

# line types
SCENE = 1
ACTION = 2
CHARACTER = 3
DIALOGUE = 4
PAREN = 5
TRANSITION = 6
SHOT = 7
NOTE = 8
ACTBREAK = 9

import autocompletion
import config
import error
import headers
import locations
import mypager
import pdf
import pml
import spellcheck
import titles
import undo
import util

import copy
import difflib
import re
import sys
import time

from lxml import etree

# screenplay
class Screenplay:
    def __init__(self, cfgGl):
        self.autoCompletion = autocompletion.AutoCompletion()
        self.headers = headers.Headers()
        self.locations = locations.Locations()
        self.titles = titles.Titles()
        self.scDict = spellcheck.Dict()

        self.lines = [ Line(LB_LAST, SCENE) ]

        self.cfgGl = cfgGl
        self.cfg = config.Config()

        # cursor position: line and column
        self.line = 0
        self.column = 0

        # first line shown on screen. use getTopLine/setTopLine to access
        # this.
        self._topLine = 0

        # Mark object if selection active, or None.
        self.mark = None

        # FIXME: document these
        self.pages = [-1, 0]
        self.pagesNoAdjust = [-1, 0]

        # time when last paginated
        self.lastPaginated = 0.0

        # list of active auto-completion strings
        self.acItems = None

        # selected auto-completion item (only valid when acItems contains
        # something)
        self.acSel = -1

        # max nr of auto comp items displayed at once
        self.acMax = 10

        # True if script has had changes done to it after
        # load/save/creation.
        self.hasChanged = False

        # first/last undo objects (undo.Base)
        self.firstUndo = None
        self.lastUndo = None

        # value of this, depending on the user's last action:
        #  undo: the undo object that was used
        #  redo: the next undo object from the one that was used
        #  anything else: None
        self.currentUndo = None

        # estimated amount of memory used by undo objects, in bytes
        self.undoMemoryUsed = 0

    def isModified(self):
        if not self.hasChanged:
            return False

        # nothing of value is ever lost by not saving a completely empty
        # script, and it's annoying getting warnings about unsaved changes
        # on those, so don't do that

        return (len(self.lines) > 1) or bool(self.lines[0].text)

    def markChanged(self, state = True):
        self.hasChanged = state

    def cursorAsMark(self):
        return Mark(self.line, self.column)

    # return True if the line is a parenthetical and not the first line of
    # that element (such lines need an extra space of indenting).
    def needsExtraParenIndent(self, line):
        return (self.lines[line].lt == PAREN) and not self.isFirstLineOfElem(line)

    def getSpacingBefore(self, i):
        if i == 0:
            return 0

        tcfg = self.cfg.types[self.lines[i].lt]

        if self.lines[i - 1].lb == LB_LAST:
            return tcfg.beforeSpacing
        else:
            return tcfg.intraSpacing

    # we implement our own custom deepcopy because it's 8-10x faster than
    # the generic one (times reported by cmdSpeedTest using a 119-page
    # screenplay):
    #
    # ╭─────────────────────────────┬─────────┬────────╮
    # │                             │ Generic │ Custom │
    # ├─────────────────────────────┼─────────┼────────┤
    # │ Intel Core Duo T2050 1.6GHz │  0.173s │ 0.020s │
    # │ Intel i5-2400 3.1GHz        │  0.076s │ 0.007s │
    # ╰─────────────────────────────┴─────────┴────────╯
    def __deepcopy__(self):
        sp = Screenplay(self.cfgGl)
        sp.cfg = copy.deepcopy(self.cfg)

        sp.autoCompletion = copy.deepcopy(self.autoCompletion)
        sp.headers = copy.deepcopy(self.headers)
        sp.locations = copy.deepcopy(self.locations)
        sp.titles = copy.deepcopy(self.titles)
        sp.scDict = copy.deepcopy(self.scDict)

        sp.lines = [Line(ln.lb, ln.lt, ln.text) for ln in self.lines]

        # "open PDF on current page" breaks on scripts we're removing
        # notes from before printing if we don't copy these
        sp.line = self.line
        sp.column = self.column

        return sp

    # save script to a string and return that
    def save(self):
        self.cfg.cursorLine = self.line
        self.cfg.cursorColumn = self.column

        output = ''

        output += '\ufeff'
        output += "#Version 3\n"

        output += "#Begin-Auto-Completion \n"
        output += self.autoCompletion.save()
        output += "#End-Auto-Completion \n"

        output += "#Begin-Config \n"
        output += self.cfg.save()
        output += "#End-Config \n"

        output += "#Begin-Locations \n"
        output += self.locations.save()
        output += "#End-Locations \n"

        output += "#Begin-Spell-Checker-Dict \n"
        output += self.scDict.save()
        output += "#End-Spell-Checker-Dict \n"

        pgs = self.titles.pages
        for pg in range(len(pgs)):
            if pg != 0:
                output += "#Title-Page \n"

            for i in range(len(pgs[pg])):
                output += "#Title-String %s\n" % str(pgs[pg][i])

        for h in self.headers.hdrs:
            output += "#Header-String %s\n" % str(h)

        output += "#Header-Empty-Lines %d\n" % self.headers.emptyLinesAfter

        output += "#Start-Script \n"

        for i in range(len(self.lines)):
            output += str(self.lines[i]) + "\n"

        return output.encode("UTF-8")

    # load script from string s and return a (Screenplay, msg) tuple,
    # where msgs is string (possibly empty) of warnings about the loading
    # process. fatal errors are indicated by raising a MiscError. note
    # that this is a static function.
    @staticmethod
    def load(s, cfgGl):
        lines = s.splitlines()

        sp = Screenplay(cfgGl)

        # remove default empty line
        sp.lines = []

        if len(lines) < 2:
            raise error.MiscError("File has too few lines to be a valid\n"
                                  "screenplay file.")

        key, version = Screenplay.parseConfigLine(lines[0])
        if not key or (key != "Version"):
            raise error.MiscError("File doesn't seem to be a proper\n"
                                  "screenplay file.")

        if version not in ("1", "2", "3"):
            raise error.MiscError("File uses fileformat version '%s',\n"
                                  "which is not supported by this version\n"
                                  "of the program." % version)

        version = int(version)

        # current position at 'lines'
        index = 1

        s, index = Screenplay.getConfigPart(lines, "Auto-Completion", index)
        if s:
            sp.autoCompletion.load(s)

        s, index = Screenplay.getConfigPart(lines, "Config", index)
        if s:
            sp.cfg.load(s)

        s, index = Screenplay.getConfigPart(lines, "Locations", index)
        if s:
            sp.locations.load(s)

        s, index = Screenplay.getConfigPart(lines, "Spell-Checker-Dict",
                                            index)
        if s:
            sp.scDict.load(s)

        # used to keep track that element type only changes after a
        # LB_LAST line.
        prevType = None

        # did we encounter unknown lb types
        unknownLb = False

        # did we encounter unknown element types
        unknownTypes = False

        # did we encounter unknown config lines
        unknownConfigs = False

        # have we seen the Start-Script line. defaults to True in old
        # files which didn't have it.
        startSeen = version < 3

        for i in range(index, len(lines)):
            s = lines[i]

            if len(s) < 2:
                raise error.MiscError("Line %d is too short." % (i + 1))

            if s[0] == "#":
                key, val = Screenplay.parseConfigLine(s)
                if not key:
                    raise error.MiscError("Line %d has invalid syntax for\n"
                                          "config line." % (i + 1))

                if key == "Title-Page":
                    sp.titles.pages.append([])

                elif key == "Title-String":
                    if len(sp.titles.pages) == 0:
                        sp.titles.pages.append([])

                    tmp = titles.TitleString([])
                    tmp.load(val)
                    sp.titles.pages[-1].append(tmp)

                elif key == "Header-String":
                    tmp = headers.HeaderString()
                    tmp.load(val)
                    sp.headers.hdrs.append(tmp)

                elif key == "Header-Empty-Lines":
                    sp.headers.emptyLinesAfter = util.str2int(val, 1, 0, 5)

                elif key == "Start-Script":
                    startSeen = True

                else:
                    unknownConfigs = True

            else:
                if not startSeen:
                    unknownConfigs = True

                    continue

                lb = config.char2lb(s[0], False)
                lt = config.char2lt(s[1], False)
                text = util.toInputStr(util.fromUTF8(s[2:]))

                # convert unknown lb types into LB_SPACE
                if lb == None:
                    lb = LB_SPACE
                    unknownLb = True

                # convert unknown types into ACTION
                if lt == None:
                    lt = ACTION
                    unknownTypes = True

                if prevType and (lt != prevType):
                    raise error.MiscError("Line %d has invalid element"
                                          " type." % (i + 1))

                line = Line(lb, lt, text)
                sp.lines.append(line)

                if lb != LB_LAST:
                    prevType = lt
                else:
                    prevType = None

        if not startSeen:
            raise error.MiscError("Start-Script line not found.")

        if len(sp.lines) == 0:
            raise error.MiscError("File doesn't contain any screenplay"
                                  " lines.")

        if sp.lines[-1].lb != LB_LAST:
            raise error.MiscError("Last line doesn't end an element.")

        if cfgGl.honorSavedPos:
            sp.line = sp.cfg.cursorLine
            sp.column = sp.cfg.cursorColumn
            sp.validatePos()

        sp.reformatAll()
        sp.paginate()
        sp.titles.sort()
        sp.locations.refresh(sp.getSceneNames())

        msgs = []

        if unknownLb:
            msgs.append("Screenplay contained unknown linebreak types.")

        if unknownTypes:
            msgs.append("Screenplay contained unknown element types. These"
                        " have been converted to Action elements.")

        if unknownConfigs:
            msgs.append("Screenplay contained unknown information. This"
                        " probably means that the file was created with a"
                        " newer version of this program.\n\n"
                        "  You'll lose that information if you save over"
                        " the existing file.")

        return (sp, "\n\n".join(msgs))

    # lines is an array of strings. if lines[startIndex] == "Begin-$name
    # ", this searches for a string of "End-$name ", takes all the strings
    # between those two, joins the lines into a single string (lines
    # separated by a "\n") and returns (string,
    # line-index-after-the-end-line). returns ("", startIndex) if
    # startIndex does not contain the start line or startIndex is too big
    # for 'lines'. raises error.MiscError on errors.
    @staticmethod
    def getConfigPart(lines, name, startIndex):
        if (startIndex >= len(lines)) or\
               (lines[startIndex] != ("#Begin-%s " % name)):
            return ("", startIndex)

        try:
            endIndex = lines.index("#End-%s " % name, startIndex)
        except ValueError:
            raise error.MiscError("#End-%s not found" % name)

        return ("\n".join(lines[startIndex + 1:endIndex]), endIndex + 1)

    # parse a line containing a config-value in the format detailed in
    # fileformat.txt. line must have newline stripped from the end
    # already. returns a (key, value) tuple. if line doesn't match the
    # format, (None, None) is returned.
    @staticmethod
    def parseConfigLine(s):
        pattern = re.compile("#([a-zA-Z0-9\-]+) (.*)")
        m = pattern.search(s)
        if m:
            return (m.group(1), m.group(2))
        else:
            return (None, None)

    # apply new config.
    def applyCfg(self, cfg):
        self.firstUndo = None
        self.lastUndo = None
        self.currentUndo = None
        self.undoMemoryUsed = 0

        self.cfg = copy.deepcopy(cfg)
        self.cfg.recalc()
        self.reformatAll()
        self.paginate()

        self.markChanged()

    # return script config as a string.
    def saveCfg(self):
        return self.cfg.save()

    # generate formatted text and return it as a string. if 'dopages' is
    # True, marks pagination in the output.
    def generateText(self, doPages):
        ls = self.lines

        output = util.String()

        for p in range(1, len(self.pages)):
            start, end = self.page2lines(p)

            if doPages and (p != 1):
                s = "%s %d. " % ("-" * 30, p)
                s += "-" * (60 - len(s))
                output += "\n%s\n\n" % s

            for i in range(start, end + 1):
                line = ls[i]
                tcfg = self.cfg.getType(line.lt)

                if tcfg.export.isCaps:
                    text = util.upper(line.text)
                else:
                    text = line.text

                if (i != 0) and (not doPages or (i != start)):
                    output += (self.getSpacingBefore(i) // 10) * "\n"

                if text and self.needsExtraParenIndent(i):
                    text = " " + text

                output += " " * tcfg.indent + text + "\n"

        return str(output)

    # generate HTML output and return it as a string, optionally including
    # notes.
    def generateHtml(self, includeNotes = True):
        ls = self.lines

        # We save space by shorter class names in html.
        htmlMap = {
            ACTION : "ac",
            CHARACTER : "ch",
            DIALOGUE : "di",
            PAREN : "pa",
            SCENE : "sc",
            SHOT : "sh",
            TRANSITION : "tr",
            NOTE : "nt",
            ACTBREAK : "ab",
        }

        # html header for files
        htmlHeader = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>Exported Screenplay</title>
<style type="text/css">
body {background: #ffffff; color: #000000; text-align: center;}
pre, p {font: 12px/14px Courier, "Courier New", monospace !important;}
pre {text-align: left !important; letter-spacing: 0 !important; margin-top: 0px !important; margin-bottom: 0px !important;}
p {text-align: center;}
.title, .footer {margin: 15px;}
.spcenter {margin: 0 auto; width: 500px;}
.sc, .ab {font-weight: bold !important;}
.nt {color: blue; font-style: italic !important;}
</style>
</head>
<body>
"""
        htmlFooter = """<p class = "footer">***<br>
Generated with <a href="http://www.trelby.org">Trelby</a>.</p>
</body>
</html>"""

        content = etree.Element("div")
        content.set("class","spcenter")

        # title pages
        for page in self.titles.pages:
            for ts in page:
                for s in ts.items:
                    para = etree.SubElement(content, "p")
                    para.set("class", "title")
                    para.text = s

            para = etree.SubElement(content, "p")
            para.set("class", "title")
            para.text = "***"

        for i in range(len(ls)):
            line = ls[i]

            if not includeNotes and (line.lt == NOTE):
                continue

            tcfg = self.cfg.getType(line.lt)
            if tcfg.export.isCaps:
                text = util.upper(line.text)
            else:
                text = line.text

            if text and self.needsExtraParenIndent(i):
                text = " " + text

            text = " " * tcfg.indent + text

            # do we need space before this line?
            lineSpaces = self.getSpacingBefore(i) // 10

            for num in range(lineSpaces):
                para = etree.SubElement(content, "pre")
                para.set("class", htmlMap[line.lt])
                para.text = " "

            # and now the line text
            para = etree.SubElement(content, "pre")
            para.set("class", htmlMap[line.lt])
            para.text = str(text)

        bodyText = etree.tostring(content, encoding='UTF-8', pretty_print=True).decode()

        return htmlHeader + bodyText + htmlFooter

    # Return screenplay as list of tuples of the form (elType, elText).
    # forced linebreaks are represented as \n characters.
    def getElementsAsList(self):
        ls = self.lines
        eleList = []
        curLine = ""

        for line in ls:
            lineType = line.lt
            lineText = line.text

            if self.cfg.getType(line.lt).export.isCaps:
                lineText = util.upper(lineText)

            curLine += lineText

            if line.lb == LB_LAST:
                eleList.append((lineType, curLine))
                curLine = ""
            elif line.lb == LB_SPACE:
                curLine += " "
            elif line.lb == LB_FORCED:
                curLine += "\n"

        return eleList

    # Generate a Final Draft XML file and return as string.
    def generateFDX(self):
        eleList = self.getElementsAsList()
        fd = etree.Element("FinalDraft")
        fd.set("DocumentType", "Script")
        fd.set("Template", "No")
        fd.set("Version", "1")
        content = etree.SubElement(fd, "Content")

        xmlMap = {
            ACTION : "Action",
            CHARACTER : "Character",
            DIALOGUE : "Dialogue",
            PAREN : "Parenthetical",
            SCENE : "Scene Heading",
            SHOT : "Shot",
            TRANSITION : "Transition",
            NOTE : "Action",
            ACTBREAK : "New Act",
        }

        for ele in eleList:
            typ, txt = ele
            if typ == NOTE:
                dummyPara = etree.SubElement(content, "Paragraph")
                dummyPara.set("Type", xmlMap[typ])
                scriptnote = etree.SubElement(dummyPara, "ScriptNote")
                scriptnote.set("ID", "1")
                para = etree.SubElement(scriptnote, "Paragraph")
            else:
                para = etree.SubElement(content, "Paragraph")
                para.set("Type", xmlMap[typ])

            paratxt = etree.SubElement(para, "Text")
            paratxt.text = str(txt)

        # FD does not recognize "New Act" by default. It needs an
        # ElementSettings element added.
        eleSet = etree.SubElement(fd, "ElementSettings")
        eleSet.set("Type", xmlMap[ACTBREAK])
        eleSetFont = etree.SubElement(eleSet, "FontSpec")
        eleSetFont.set("Style", "Underline+AllCaps")
        eleSetPara = etree.SubElement(eleSet, "ParagraphSpec")
        eleSetPara.set("Alignment","Center")

        return etree.tostring(
            fd, xml_declaration=True, encoding='UTF-8', pretty_print=True)

    # generate Fountain and return it as a string.
    def generateFountain(self):
        eleList = self.getElementsAsList()
        flines = []
        TWOSPACE = "  "
        sceneStartsList = ("INT", "EXT", "EST", "INT./EXT", "INT/EXT", "I/E", "I./E")

        # does s look like a fountain scene line:
        def looksLikeScene(s):
            s = s.upper()
            looksGood = False
            for t in sceneStartsList:
                if s.startswith(t):
                    looksGood = True
                    break
            return looksGood

        # Generate Title Page
        def generateTitleString(keyword,titleLine,startAt,linePrefix, lineSuffix):
            if (len(titleLine)-startAt)>1:
                # multi-line
                flines.append(keyword)
                for part in titleLine:
                    if startAt > 0:
                        startAt -= 1
                        continue
                    flines.append('    '+linePrefix+part+lineSuffix)
            elif len(titleLine) == 1 and keyword == titleLine[0]:
                flines.append(keyword)
            else:
                flines.append(keyword+' '+titleLine[startAt])

        titleNeeded=True
        kwPattern = re.compile(r'^([A-za-z][^:]+:)')
        for page in self.titles.pages:
            for titleLine in page:
                if titleNeeded and titleLine.isBold and titleLine.isCentered:
                    generateTitleString('Title:',titleLine.items,0,'_**','**_')
                    titleNeeded = False
                elif titleLine.items[0]=='by':
                    generateTitleString('Author:',titleLine.items,2,'','')
                elif kwPattern.match(titleLine.items[0]):
                    generateTitleString(titleLine.items[0],titleLine.items,0,'','')
                else:
                    generateTitleString('Contact:',titleLine.items,0,'','')

        for ele in eleList:
            typ, txt = ele
            lns = txt.split("\n")

            #ensure last element of flines is empty for some types.
            if typ in (SCENE, ACTION, CHARACTER, TRANSITION, SHOT, ACTBREAK, NOTE):
                if flines and flines[-1] != "":
                    flines.append("")

            # special handling of some elements.
            if typ == SCENE:
                # if the line would not be recognized as Scene by fountain,
                # append a "." so it is forced as a scene line.
                if not looksLikeScene(txt):
                    txt = "." + txt

            elif typ == ACTION:
                tmp = []
                for ln in lns:
                    if ln and (ln.isupper() or looksLikeScene(txt)):
                        tmp.append(ln + TWOSPACE)
                    else:
                        tmp.append(ln)
                txt = "\n".join(tmp)

            elif typ == TRANSITION:
                if not txt.endswith("TO:"):
                    txt = "> " + txt

            elif typ == DIALOGUE:
                tmp = []
                for ln in lns:
                    if not ln:
                        tmp.append(TWOSPACE)
                    else:
                        tmp.append(ln)
                txt = "\n".join(tmp)

            elif typ == NOTE:
                txt = "[[" + txt + "]]"

            elif typ == ACTBREAK:
                txt = ">" + txt + "<"

            elif typ == SHOT:
                txt += TWOSPACE

            flines.append(txt)

        return util.toUTF8("\n".join(flines))

    # generate RTF and return it as a string.
    def generateRTF(self):
        ls = self.lines
        s = util.String()

        s += r"{\rtf1\ansi\deff0{\fonttbl{\f0\fmodern Courier;}}" + "\n"

        s+= "{\\stylesheet\n"

        mt = util.mm2twips
        fs = self.cfg.fontSize

        # since some of our units (beforeSpacing, indent, width) are
        # easier to handle if we assume normal font size, this is a scale
        # factor from actual font size to normal font size
        sf = fs / 12.0

        for ti in config.getTIs():
            t = self.cfg.getType(ti.lt)
            tt = t.export

            # font size is expressed as font size * 2 in RTF
            tmp = " \\fs%d" % (fs * 2)

            if tt.isCaps:
                tmp += r" \caps"

            if tt.isBold:
                tmp += r" \b"

            if tt.isItalic:
                tmp += r" \i"

            if tt.isUnderlined:
                tmp += r" \ul"

            # some hairy conversions going on here...
            tmp += r" \li%d\ri%d" % (sf * t.indent * 144,
                mt(self.cfg.paperWidth) -
                      (mt(self.cfg.marginLeft + self.cfg.marginRight) +
                      (t.indent + t.width) * 144 * sf))

            tmp += r" \sb%d" % (sf * t.beforeSpacing * 24)

            s += "{\\s%d%s %s}\n" % (ti.lt, tmp, ti.name)

        s += "}\n"

        s += r"\paperw%d\paperh%d\margt%d\margr%d\margb%d\margl%d" % (
            mt(self.cfg.paperWidth), mt(self.cfg.paperHeight),
            mt(self.cfg.marginTop), mt(self.cfg.marginRight),
            mt(self.cfg.marginBottom), mt(self.cfg.marginLeft))
        s += "\n"

        s += self.titles.generateRTF()

        length = len(ls)
        i = 0

        magicslash = "TRELBY-MAGIC-SLASH"

        while i < length:
            lt = ls[i].lt
            text = ""

            while 1:
                ln = ls[i]
                i += 1

                lb = ln.lb
                text += ln.text

                if lb in (LB_SPACE, LB_NONE):
                    text += config.lb2str(lb)
                elif lb == LB_FORCED:
                    text += magicslash + "line "
                elif lb == LB_LAST:
                    break
                else:
                    raise error.MiscError("Unknown line break style %d"
                                          " in generateRTF" % lb)

            s += (r"{\pard \s%d " % lt) + util.escapeRTF(text).replace(
                magicslash, "\\") + "}{\\par}\n"

        s += "}"

        return str(s)

    # generate PDF and return it as a string. assumes paginate/reformat is
    # 100% correct for the screenplay. isExport is True if this is an
    # "export to file" operation, False if we're just going to launch a
    # PDF viewer with the data.
    def generatePDF(self, isExport):
        return pdf.generate(self.generatePML(isExport))

    # Same arguments as generatePDF, but returns a PML document.
    def generatePML(self, isExport):
        pager = mypager.Pager(self.cfg)
        self.titles.generatePages(pager.doc)

        pager.doc.showTOC = self.cfg.pdfShowTOC

        if not isExport and self.cfg.pdfOpenOnCurrentPage:
            pager.doc.defPage = len(self.titles.pages) + \
                                self.line2page(self.line) - 1

        for i in range(1, len(self.pages)):
            pg = self.generatePMLPage(pager, i, True, True)

            if pg:
                pager.doc.add(pg)
            else:
                break

        for pfi in self.cfg.getPDFFontIds():
            pf = self.cfg.getPDFFont(pfi)

            if pf.pdfName:
                # TODO: it's nasty calling loadFile from here since it
                # uses wxMessageBox. dialog stacking order is also wrong
                # since we don't know the frame to give. so, we should
                # remove references to wxMessageBox from util and instead
                # pass in an ErrorHandlerObject to all functions that need
                # it. then the GUI program can use a subclass of that that
                # stores the frame pointer inside it, and testing
                # framework / other non-interactive uses can use a version
                # that logs errors to stderr / raises an exception /
                # whatever.

                if pf.filename != "":
                    # we load at most 10 MB to avoid a denial-of-service
                    # attack by passing around scripts containing
                    # references to fonts with filenames like "/dev/zero"
                    # etc. no real font that I know of is this big so it
                    # shouldn't hurt.
                    fontProgram = util.loadFile(pf.filename, None,
                                                10 * 1024 * 1024)
                else:
                    fontProgram = None

                pager.doc.addFont(pf.style,
                                  pml.PDFFontInfo(pf.pdfName, fontProgram))

        return pager.doc

    # generate one page of PML data and return it.
    #
    # if forPDF is True, output is meant for PDF generation.
    #
    # if doExtra is False, omits headers and other stuff that is
    # automatically added, i.e. outputs only actual screenplay lines. also
    # text style/capitalization is not done 100% correctly. this should
    # only be True for callers that do not show the results in any way,
    # just calculate things based on text positions.
    #
    # can also return None, which means pagination is not up-to-date and
    # the given page number doesn't point to a valid page anymore, and the
    # caller should stop calling this since all pages have been generated
    # (assuming 1-to-n calling sequence).
    def generatePMLPage(self, pager, pageNr, forPDF, doExtra):
        #lsdjflksj = util.TimerDev("generatePMLPage")

        cfg = self.cfg
        ls = self.lines

        fs = cfg.fontSize
        chX = util.getTextWidth(" ", pml.COURIER, fs)
        chY = util.getTextHeight(fs)
        length = len(ls)

        start = self.pages[pageNr - 1] + 1

        if start >= length:
            # text has been deleted at end of script and pagination has
            # not been updated.
            return None

        # pagination may not be up-to-date, so any overflow text gets
        # dumped onto the last page which may thus be arbitrarily long.
        if pageNr == (len(self.pages) - 1):
            end = length - 1
        else:
            # another side-effect is that if text is deleted at the end,
            # self.pages can point to lines that no longer exist, so we
            # need to clamp it.
            end = util.clamp(self.pages[pageNr], maxVal = length - 1)

        pg = pml.Page(pager.doc)

        # what line we're on, counted from first line after top
        # margin, units = line / 10
        y = 0

        if pageNr != 1:
            if doExtra:
                self.headers.generatePML(pg, str(pageNr), cfg)
            y += self.headers.getNrOfLines() * 10

            if cfg.sceneContinueds and not self.isFirstLineOfScene(start):
                if doExtra:
                    s = cfg.strContinuedPageStart
                    if pager.sceneContNr != 0:
                        s += " (%d)" % (pager.sceneContNr + 1)

                    pg.add(pml.TextOp(s,
                        cfg.marginLeft + pager.sceneIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

                    pager.sceneContNr += 1

                    if cfg.pdfShowSceneNumbers:
                        self.addSceneNumbers(pg, "%d" % pager.scene,
                            cfg.getType(SCENE).width, y, chX, chY)

                y += 20

            if self.needsMore(start - 1):
                if doExtra:
                    pg.add(pml.TextOp(self.getPrevSpeaker(start) +
                        cfg.strDialogueContinued,
                        cfg.marginLeft + pager.charIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

                y += 10

        for i in range(start, end + 1):
            line = ls[i]
            tcfg = cfg.getType(line.lt)

            if i != start:
                y += self.getSpacingBefore(i)

            typ = pml.NORMAL

            if doExtra:
                if forPDF:
                    tt = tcfg.export
                else:
                    tt = tcfg.screen

                if tt.isCaps:
                    text = util.upper(line.text)
                else:
                    text = line.text

                if tt.isBold:
                    typ |= pml.BOLD
                if tt.isItalic:
                    typ |= pml.ITALIC
                if tt.isUnderlined:
                    typ |= pml.UNDERLINED
            else:
                text = line.text

            extraIndent = 1 if self.needsExtraParenIndent(i) else 0

            to = pml.TextOp(text,
                cfg.marginLeft + (tcfg.indent + extraIndent) * chX,
                cfg.marginTop + (y / 10.0) * chY, fs, typ, line = i)

            pg.add(to)

            if forPDF and (tcfg.lt == NOTE) and cfg.pdfOutlineNotes:
                offset = chX / 2.0
                nx = cfg.marginLeft + tcfg.indent * chX
                ny = cfg.marginTop + (y / 10.0) * chY
                nw = tcfg.width * chX
                lw = 0.25

                pg.add(pml.genLine(nx - offset, ny, 0.0, chY, lw))
                pg.add(pml.genLine(nx + nw + offset, ny, 0.0, chY, lw))

                if self.isFirstLineOfElem(i):
                    pg.add(pml.QuarterCircleOp(nx, ny, offset, lw))
                    pg.add(pml.genLine(nx, ny - offset, nw, 0.0, lw))
                    pg.add(pml.QuarterCircleOp(nx + nw, ny, offset, lw, True))

                    pg.add(pml.TextOp("Note",
                        (nx + nx + nw) / 2.0, ny - offset, 6, pml.ITALIC,
                        util.ALIGN_CENTER, util.VALIGN_BOTTOM))

                if self.isLastLineOfElem(i):
                    pg.add(pml.QuarterCircleOp(nx, ny + chY, offset, lw,
                                               False, True))
                    pg.add(pml.genLine(nx, ny + chY + offset, nw, 0.0, lw))
                    pg.add(pml.QuarterCircleOp(nx + nw, ny + chY, offset, lw,
                                               True, True))

            if doExtra and (tcfg.lt == SCENE) and self.isFirstLineOfElem(i):
                pager.sceneContNr = 0

                if cfg.pdfShowSceneNumbers:
                    pager.scene += 1
                    self.addSceneNumbers(pg, "%d" % pager.scene, tcfg.width,
                                         y, chX, chY)

                if cfg.pdfIncludeTOC:
                    if cfg.pdfShowSceneNumbers:
                        s = "%d %s" % (pager.scene, text)
                    else:
                        s = text

                    to.toc = pml.TOCItem(s, to)
                    pager.doc.addTOC(to.toc)

            if doExtra and cfg.pdfShowLineNumbers:
                pg.add(pml.TextOp("%02d" % (i - start + 1),
                    cfg.marginLeft - 3 * chX,
                    cfg.marginTop + (y / 10.0) * chY, fs))

            y += 10

        if self.needsMore(end):
            if doExtra:
                pg.add(pml.TextOp(cfg.strMore,
                        cfg.marginLeft + pager.charIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

            y += 10

        if cfg.sceneContinueds and not self.isLastLineOfScene(end):
            if doExtra:
                pg.add(pml.TextOp(cfg.strContinuedPageEnd,
                        cfg.marginLeft + cfg.sceneContinuedIndent * chX,
                        cfg.marginTop + (y / 10.0 + 1.0) * chY, fs))

            y += 10

        if forPDF and cfg.pdfShowMargins:
            lx = cfg.marginLeft
            rx = cfg.paperWidth - cfg.marginRight
            uy = cfg.marginTop
            dy = cfg.paperHeight - cfg.marginBottom

            pg.add(pml.LineOp([(lx, uy), (rx, uy), (rx, dy), (lx, dy)],
                              0, True))

        return pg

    def addSceneNumbers(self, pg, s, width, y, chX, chY):
        cfg = self.cfg

        pg.add(pml.TextOp(s, cfg.marginLeft - 6 * chX,
             cfg.marginTop + (y / 10.0) * chY, cfg.fontSize))
        pg.add(pml.TextOp(s, cfg.marginLeft + (width + 1) * chX,
            cfg.marginTop + (y / 10.0) * chY, cfg.fontSize))

    # get topLine, clamping it to the valid range in the process.
    def getTopLine(self):
        self._topLine = util.clamp(self._topLine, 0, len(self.lines) - 1)

        return self._topLine

    # set topLine, clamping it to the valid range.
    def setTopLine(self, line):
        self._topLine = util.clamp(line, 0, len(self.lines) - 1)

    def reformatAll(self):
        # doing a reformatAll while we have undo history will completely
        # break undo, so that can't be allowed.
        assert not self.firstUndo

        #sfdlksjf = util.TimerDev("reformatAll")

        line = 0

        while 1:
            line += self.rewrapPara(line)
            if line >= len(self.lines):
                break

    # reformat part of the screenplay. par1 is line number of paragraph to
    # start at, par2 the same for the ending one, inclusive.
    def reformatRange(self, par1, par2):
        ls = self.lines

        # add special tag to last paragraph we'll reformat
        ls[par2].reformatMarker = 0
        end = False

        line = par1
        while 1:
            if hasattr(ls[line], "reformatMarker"):
                del ls[line].reformatMarker
                end = True

            line += self.rewrapPara(line)
            if end:
                break

    # wraps a single line into however many lines are needed, according to
    # the type's width. doesn't modify the input line, returns a list of
    # new lines.
    def wrapLine(self, line):
        ret = []
        width = self.cfg.getType(line.lt).width
        isParen = line.lt == PAREN

        # text remaining to be wrapped
        text = line.text

        while 1:
            # reduce parenthetical width by 1 from second line onwards
            if isParen and ret:
                w = width - 1
            else:
                w = width

            if len(text) <= w:
                ret.append(Line(line.lb, line.lt, text))
                break
            else:
                i = text.rfind(" ", 0, w + 1)

                if i == w:

                    # we allow space characters to go over the line
                    # length, for two reasons:
                    #
                    # 1) it is impossible to get the behavior right
                    # otherwise in situations where a line ends in two
                    # spaces and the user inserts a non-space character at
                    # the end of the line. the cursor must be positioned
                    # at the second space character for this to work
                    # right, and the only way to get that is to allow
                    # spaces to go over the normal line length.
                    #
                    # 2) doing this results in no harm, since space
                    # characters print as empty, so they don't overwrite
                    # anything.

                    i += 1
                    while text[i:i + 1] == " ":
                        i += 1

                    if i == len(text):
                        ret.append(Line(line.lb, line.lt, text))

                        break
                    else:
                        ret.append(Line(LB_SPACE, line.lt, text[0:i - 1]))
                        text = text[i:]

                elif i >= 0:
                    ret.append(Line(LB_SPACE, line.lt, text[0:i]))
                    text = text[i + 1:]

                else:
                    ret.append(Line(LB_NONE, line.lt, text[0:w]))
                    text = text[w:]

        return ret

    # rewrap paragraph starting at given line. returns the number of lines
    # in the wrapped paragraph. if line1 is -1, rewraps paragraph
    # containing self.line. maintains cursor position correctness.
    def rewrapPara(self, line1 = -1):
        ls = self.lines

        if line1 == -1:
            line1 = self.getParaFirstIndexFromLine(self.line)

        line2 = line1

        while ls[line2].lb not in (LB_LAST, LB_FORCED):
            line2 += 1

        if (self.line >= line1) and (self.line <= line2):
            # cursor is in this paragraph, save its offset from the
            # beginning of the paragraph
            cursorOffset = 0

            for i in range(line1, line2 + 1):
                if i == self.line:
                    cursorOffset += self.column

                    break
                else:
                    cursorOffset += len(ls[i].text) + \
                                    len(config.lb2str(ls[i].lb))
        else:
            cursorOffset = -1

        s = ls[line1].text
        for i in range(line1 + 1, line2 + 1):
            s += config.lb2str(ls[i - 1].lb)
            s += ls[i].text

        tmp = Line(ls[line2].lb, ls[line1].lt, s)
        wrappedLines = self.wrapLine(tmp)
        ls[line1:line2 + 1] = wrappedLines

        # adjust cursor position
        if cursorOffset != -1:
            for i in range(line1, line1 + len(wrappedLines)):
                ln = ls[i]
                llen = len(ln.text) + len(config.lb2str(ln.lb))

                if cursorOffset < llen:
                    self.line = i
                    self.column = min(cursorOffset, len(ln.text))
                    break
                else:
                    cursorOffset -= llen

        elif self.line >= line1:
            # cursor position is below current paragraph, modify its
            # linenumber appropriately
            self.line += len(wrappedLines) - (line2 - line1 + 1)

        return len(wrappedLines)

    # rewraps paragraph previous to current one.
    def rewrapPrevPara(self):
        line = self.getParaFirstIndexFromLine(self.line)

        if line == 0:
            return

        line = self.getParaFirstIndexFromLine(line - 1)
        self.rewrapPara(line)

    # rewrap element starting at given line. if line is -1, rewraps
    # element containing self.line.
    def rewrapElem(self, line = -1):
        ls = self.lines

        if line == -1:
            line = self.getElemFirstIndex()

        while 1:
            line += self.rewrapPara(line)

            if ls[line - 1].lb == LB_LAST:
                break

    def isFirstLineOfElem(self, line):
        return (line == 0) or (self.lines[line - 1].lb == LB_LAST)

    def isLastLineOfElem(self, line):
        return self.lines[line].lb == LB_LAST

    def isOnlyLineOfElem(self, line):
        # this is just "isLastLineOfElem(line) and isFirstLineOfElem(line)"
        # inlined here, since it's 130% faster this way.
        return (self.lines[line].lb == LB_LAST) and \
               ((line == 0) or (self.lines[line - 1].lb == LB_LAST))

    # get first index of paragraph
    def getParaFirstIndexFromLine(self, line):
        ls = self.lines

        while 1:
            tmp = line - 1

            if tmp < 0:
                break

            if ls[tmp].lb in (LB_LAST, LB_FORCED):
                break

            line -= 1

        return line

    # get last index of paragraph
    def getParaLastIndexFromLine(self, line):
        ls = self.lines

        while 1:
            if ls[line].lb in (LB_LAST, LB_FORCED):
                break

            if (line + 1) >= len(ls):
                break

            line += 1

        return line

    def getElemFirstIndex(self):
        return self.getElemFirstIndexFromLine(self.line)

    def getElemFirstIndexFromLine(self, line):
        ls = self.lines

        while 1:
            tmp = line - 1

            if tmp < 0:
                break

            if ls[tmp].lb == LB_LAST:
                break

            line -= 1

        return line

    def getElemLastIndex(self):
        return self.getElemLastIndexFromLine(self.line)

    def getElemLastIndexFromLine(self, line):
        ls = self.lines

        while 1:
            if ls[line].lb == LB_LAST:
                break

            if (line + 1) >= len(ls):
                break

            line += 1

        return line

    def getElemIndexes(self):
        return self.getElemIndexesFromLine(self.line)

    def getElemIndexesFromLine(self, line):
        return (self.getElemFirstIndexFromLine(line),
                self.getElemLastIndexFromLine(line))

    def isFirstLineOfScene(self, line):
        if line == 0:
            return True

        ls = self.lines

        if ls[line].lt != SCENE:
            return False

        l = ls[line - 1]

        return (l.lt != SCENE) or (l.lb == LB_LAST)

    def isLastLineOfScene(self, line):
        ls = self.lines

        if ls[line].lb != LB_LAST:
            return False

        if line == (len(ls) - 1):
            return True

        return ls[line + 1].lt == SCENE

    def getTypeOfPrevElem(self, line):
        line = self.getElemFirstIndexFromLine(line)
        line -= 1

        if line < 0:
            return None

        return self.lines[line].lt

    def getTypeOfNextElem(self, line):
        line = self.getElemLastIndexFromLine(line)
        line += 1

        if line >= len(self.lines):
            return None

        return self.lines[line].lt

    def getSceneIndexes(self):
        return self.getSceneIndexesFromLine(self.line)

    def getSceneIndexesFromLine(self, line):
        top, bottom = self.getElemIndexesFromLine(line)
        ls = self.lines

        while 1:
            if ls[top].lt in (SCENE, ACTBREAK):
                break

            tmp = top - 1
            if tmp < 0:
                break

            top = self.getElemIndexesFromLine(tmp)[0]

        while 1:
            tmp = bottom + 1
            if tmp >= len(ls):
                break

            if ls[tmp].lt in (SCENE, ACTBREAK):
                break

            bottom = self.getElemIndexesFromLine(tmp)[1]

        return (top, bottom)

    # return scene number for the given line. if line is -1, return 0.
    def getSceneNumber(self, line):
        ls = self.lines
        sc = SCENE
        scene = 0

        for i in range(line + 1):
            if (ls[i].lt == sc) and self.isFirstLineOfElem(i):
                scene += 1

        return scene

    # return how many elements one must advance to get from element
    # containing line1 to element containing line2. line1 must be <=
    # line2, and either line can be anywhere in their respective elements.
    # returns 0 if they're in the same element, 1 if they're in
    # consecutive elements, etc.
    def elemsDistance(self, line1, line2):
        ls = self.lines

        count = 0
        line = line1

        while line < line2:
            if ls[line].lb == LB_LAST:
                count += 1

            line += 1

        return count

    # returns true if 'line', which must be the last line on a page, needs
    # (MORE) after it and the next page needs a "SOMEBODY (cont'd)".
    def needsMore(self, line):
        ls = self.lines

        return ls[line].lt in (DIALOGUE, PAREN)\
           and (line != (len(ls) - 1)) and\
           ls[line + 1].lt in (DIALOGUE, PAREN)

    # starting at line, go backwards until a line with type of CHARACTER
    # and lb of LAST is found, and return that line's text, possibly
    # upper-cased if CHARACTER's config for export says so.
    def getPrevSpeaker(self, line):
        ls = self.lines

        while 1:
            if line < 0:
                return "UNKNOWN"

            ln = ls[line]

            if (ln.lt == CHARACTER) and (ln.lb == LB_LAST):
                s = ln.text

                if self.cfg.getType(CHARACTER).export.isCaps:
                    s = util.upper(s)

                return s

            line -= 1

    # return total number of characters in script
    def getCharCount(self):
        return sum([len(ln.text) for ln in self.lines])

    def paginate(self):
        #sfdlksjf = util.TimerDev("paginate")

        self.pages = [-1]
        self.pagesNoAdjust = [-1]

        ls = self.lines
        cfg = self.cfg

        length = len(ls)
        lastBreak = -1

        # fast aliases for stuff
        lbl = LB_LAST
        ct = cfg.types
        hdrLines = self.headers.getNrOfLines()

        i = 0
        while 1:
            lp = cfg.linesOnPage * 10

            if i != 0:
                lp -= hdrLines * 10

                # decrease by 2 if we have to put a "CONTINUED:" on top of
                # this page.
                if cfg.sceneContinueds and not self.isFirstLineOfScene(i):
                    lp -= 20

                # decrease by 1 if we have to put a "WHOEVER (cont'd)" on
                # top of this page.
                if self.needsMore(i - 1):
                    lp -= 10

            # just a safeguard
            lp = max(50, lp)

            pageLines = 0
            if i < length:
                pageLines = 10

                # advance i until it points to the last line to put on
                # this page (before adjustments)

                while i < (length - 1):

                    pageLines += 10
                    if ls[i].lb == lbl:
                        pageLines += ct[ls[i + 1].lt].beforeSpacing
                    else:
                        pageLines += ct[ls[i + 1].lt].intraSpacing

                    if pageLines > lp:
                        break

                    i += 1

            if i >= (length - 1):
                if pageLines != 0:
                    self.pages.append(length - 1)
                    self.pagesNoAdjust.append(length - 1)

                break

            self.pagesNoAdjust.append(i)

            line = ls[i]

            if line.lt == SCENE:
                i = self.removeDanglingElement(i, SCENE, lastBreak)

            elif line.lt == SHOT:
                i = self.removeDanglingElement(i, SHOT, lastBreak)
                i = self.removeDanglingElement(i, SCENE, lastBreak)

            elif line.lt == ACTION:
                if line.lb != LB_LAST:
                    first = self.getElemFirstIndexFromLine(i)

                    if first > (lastBreak + 1):
                        linesOnThisPage = i - first + 1
                        if linesOnThisPage < cfg.pbActionLines:
                            i = first - 1

                        i = self.removeDanglingElement(i, SCENE,
                                                       lastBreak)

            elif line.lt == CHARACTER:
                i = self.removeDanglingElement(i, CHARACTER, lastBreak)
                i = self.removeDanglingElement(i, SCENE, lastBreak)

            elif line.lt in (DIALOGUE, PAREN):

                if line.lb != LB_LAST or\
                       self.getTypeOfNextElem(i) in (DIALOGUE, PAREN):

                    cutDialogue = False
                    cutParen = False
                    while 1:
                        oldI = i
                        line = ls[i]

                        if line.lt == PAREN:
                            i = self.removeDanglingElement(i, PAREN,
                              lastBreak)
                            cutParen = True

                        elif line.lt == DIALOGUE:
                            if cutParen:
                                break

                            first = self.getElemFirstIndexFromLine(i)

                            if first > (lastBreak + 1):
                                linesOnThisPage = i - first + 1

                                # do we need to reserve one line for (MORE)
                                reserveLine = not (cutDialogue or cutParen)

                                val = cfg.pbDialogueLines
                                if reserveLine:
                                    val += 1

                                if linesOnThisPage < val:
                                    i = first - 1
                                    cutDialogue = True
                                else:
                                    if reserveLine:
                                        i -= 1
                                    break
                            else:
                                # leave space for (MORE)
                                i -= 1
                                break

                        elif line.lt == CHARACTER:
                            i = self.removeDanglingElement(i, CHARACTER,
                                                           lastBreak)
                            i = self.removeDanglingElement(i, SCENE,
                                                           lastBreak)

                            break

                        else:
                            break

                        if i == oldI:
                            break

            # make sure no matter how buggy the code above is, we always
            # advance at least one line per page
            i = max(i, lastBreak + 1)

            self.pages.append(i)
            lastBreak = i

            i += 1

        self.lastPaginated = time.time()

    def removeDanglingElement(self, line, lt, lastBreak):
        ls = self.lines
        startLine = line

        while 1:
            if line < (lastBreak + 2):
                break

            ln = ls[line]

            if ln.lt != lt:
                break

            # only remove one element at most, to avoid generating
            # potentially thousands of pages in degenerate cases when
            # script only contains scenes or characters or something like
            # that.
            if (line != startLine) and (ln.lb == LB_LAST):
                break

            line -= 1

        return line

    # convert element(s) to given type
    #  - if multiple elements are selected, all are changed
    #  - if not, the change is applied to element under cursor.
    def convertTypeTo(self, lt, saveUndo):
        ls = self.lines
        selection = self.getMarkedLines()

        if selection:
            startSection, endSection = selection
            selectedElems = self.elemsDistance(startSection, endSection) + 1
        else:
            startSection, endSection = self.getElemIndexes()
            selectedElems = 1

        currentLine = startSection

        if saveUndo:
            u = undo.ManyElems(
                self, undo.CMD_MISC, currentLine, selectedElems, selectedElems)

        while currentLine <= endSection:
            first, last = self.getElemIndexesFromLine(currentLine)

            # if changing away from PAREN containing only "()", remove it
            if (first == last) and (ls[first].lt == PAREN) and\
                   (ls[first].text == "()"):
                ls[first].text = ""

                if first == self.line:
                    self.column = 0

            for i in range(first, last + 1):
                ls[i].lt = lt

            # if changing empty element to PAREN, add "()"
            if (first == last) and (ls[first].lt == PAREN) and\
                   (len(ls[first].text) == 0):
                ls[first].text = "()"

                if first == self.line:
                    self.column = 1

            currentLine = last + 1

        if selection:
            self.clearMark()

            # this is moderately complex because we need to deal with
            # forced linebreaks; reformatRange wants paragraph indexes but
            # we are converting elements, so we must find the indexes of
            # the a) first paragraph of the first selected element and b)
            # last paragraph of the last selected element

            self.reformatRange(
                self.getElemFirstIndexFromLine(startSection),
                self.getParaFirstIndexFromLine(self.getElemLastIndexFromLine(endSection)))
        else:
            self.rewrapElem(first)

        self.markChanged()

        if saveUndo:
            u.setAfter(self)
            self.addUndo(u)

    # join lines 'line' and 'line + 1' and position cursor at the join
    # position.
    def joinLines(self, line):
        ls = self.lines
        ln = ls[line]

        pos = len(ln.text)
        ln.text += ls[line + 1].text
        ln.lb = ls[line + 1].lb

        self.setLineTypes(line + 1, ln.lt)
        del ls[line + 1]

        self.line = line
        self.column = pos

    # split current line at current column position.
    def splitLine(self):
        ln = self.lines[self.line]

        s = ln.text
        preStr = s[:self.column]
        postStr = s[self.column:]
        newLine = Line(ln.lb, ln.lt, postStr)
        ln.text = preStr
        ln.lb = LB_FORCED
        self.lines.insert(self.line + 1, newLine)

        self.line += 1
        self.column = 0
        self.markChanged()

    # split element at current position. newType is type to give to the
    # new element.
    def splitElement(self, newType):
        ls = self.lines

        if self.mark:
            self.clearMark()

            return

        u = undo.ManyElems(self, undo.CMD_MISC, self.line, 1, 2)

        if not self.acItems:
            if self.isAtEndOfParen():
                self.column += 1
        else:
            ls[self.line].text = self.acItems[self.acSel]
            self.column = len(ls[self.line].text)

        self.splitLine()
        ls[self.line - 1].lb = LB_LAST

        self.convertTypeTo(newType, False)

        self.rewrapPara()
        self.rewrapPrevPara()
        self.markChanged()

        u.setAfter(self)
        self.addUndo(u)

    # delete character at given position and optionally position
    # cursor there.
    def deleteChar(self, line, column, posCursor = True):
        s = self.lines[line].text
        self.lines[line].text = s[:column] + s[column + 1:]

        if posCursor:
            self.column = column
            self.line = line

    # set line types from 'line' to the end of the element to 'lt'.
    def setLineTypes(self, line, lt):
        ls = self.lines

        while 1:
            ln = ls[line]

            ln.lt = lt
            if ln.lb == LB_LAST:
                break

            line += 1

    def line2page(self, line):
        return self.line2pageReal(line, self.pages)

    def line2pageNoAdjust(self, line):
        return self.line2pageReal(line, self.pagesNoAdjust)

    def line2pageReal(self, line, p):
        lo = 1
        hi = len(p) - 1

        while lo != hi:
            mid = (lo + hi) // 2

            if line <= p[mid]:
                hi = mid
            else:
                lo = mid + 1

        return lo

    # return (startLine, endLine) for given page number (1-based). if
    # pageNr is out of bounds, it is clamped to the valid range. if
    # pagination is out of date and the lines no longer exist, they are
    # clamped to the valid range as well.
    def page2lines(self, pageNr):
        pageNr = util.clamp(pageNr, 1, len(self.pages) - 1)
        last = len(self.lines) - 1

        return (util.clamp(self.pages[pageNr - 1] + 1, 0, last),
                util.clamp(self.pages[pageNr], 0, last))

    # return a list of all page numbers as strings.
    def getPageNumbers(self):
        pages = []

        for p in range(1, len(self.pages)):
            pages.append(str(p))

        return pages

    # return a list of all scene locations in a [(sceneNumber, startLine),
    # ...] format. if script does not start with a scene line, that scene
    # is not included in this list. note that the sceneNumber in the
    # returned list is a string, not a number.
    def getSceneLocations(self):
        ls = self.lines
        sc = SCENE
        scene = 0
        ret = []

        for i in range(len(ls)):
            if (ls[i].lt == sc) and self.isFirstLineOfElem(i):
                scene += 1
                ret.append((str(scene), i))

        return ret

    # return a dictionary of all scene names (single-line text elements
    # only, upper-cased, values = None).
    def getSceneNames(self):
        names = {}

        for ln in self.lines:
            if (ln.lt == SCENE) and (ln.lb == LB_LAST):
                names[util.upper(ln.text)] = None

        return names

    # return a dictionary of all character names (single-line text
    # elements only, lower-cased, values = None).
    def getCharacterNames(self):
        names = {}

        ul = util.lower

        for ln in self.lines:
            if (ln.lt == CHARACTER) and (ln.lb == LB_LAST):
                names[ul(ln.text)] = None

        return names

    # get next word, starting at (line, col). line must be valid, but col
    # can point after the line's length, in which case the search starts
    # at (line + 1, 0). returns (word, line, col), where word is None if
    # at end of script, and (line, col) point to the start of the word.
    # note that this only handles words that are on a single line.
    def getWord(self, line, col):
        ls = self.lines

        while 1:
            if ((line < 0) or (line >= len(ls))):
                return (None, 0, 0)

            s = ls[line].text

            if col >= len(s):
                line += 1
                col = 0

                continue

            ch = s[col : col + 1]

            if not util.isWordBoundary(ch):
                word = ch
                startCol = col
                col += 1

                while col < len(s):
                    ch = s[col : col + 1]

                    if util.isWordBoundary(ch):
                        break

                    word += ch
                    col += 1

                return (word, line, startCol)

            else:
                col += 1

    # returns True if we're at second-to-last character of PAREN element,
    # and last character is ")"
    def isAtEndOfParen(self):
        ls = self.lines

        return self.isLastLineOfElem(self.line) and\
           (ls[self.line].lt == PAREN) and\
           (ls[self.line].text[self.column:] == ")")

    # returns True if pressing TAB at current position would make a new
    # element, False if it would just change element's type.
    def tabMakesNew(self):
        l = self.lines[self.line]

        if self.isAtEndOfParen():
            return True

        if (l.lb != LB_LAST) or (self.column != len(l.text)):
            return False

        if (len(l.text) == 0) and self.isOnlyLineOfElem(self.line):
            return False

        return True

    # if auto-completion is active, clear it and return True. otherwise
    # return False.
    def clearAutoComp(self):
        if not self.acItems:
            return False

        self.acItems = None

        return True

    def fillAutoComp(self):
        ls = self.lines

        lt = ls[self.line].lt
        t = self.autoCompletion.getType(lt)

        if t and t.enabled:
            self.acItems = self.getMatchingText(ls[self.line].text, lt)
            self.acSel = 0

    # page up (dir == -1) or page down (dir == 1) was pressed and we're in
    # auto-comp mode, handle it.
    def pageScrollAutoComp(self, dir):
        if len(self.acItems) > self.acMax:

            if dir < 0:
                self.acSel -= self.acMax

                if self.acSel < 0:
                    self.acSel = len(self.acItems) - 1

            else:
                self.acSel = (self.acSel + self.acMax) % len(self.acItems)

    # get a list of strings (single-line text elements for now) that start
    # with 'text' (not case sensitive) and are of of type 'type'. also
    # mixes in the type's default items from config. ignores current line.
    def getMatchingText(self, text, lt):
        text = util.upper(text)
        t = self.autoCompletion.getType(lt)
        ls = self.lines
        matches = {}
        last = None

        for i in range(len(ls)):
            if (ls[i].lt == lt) and (ls[i].lb == LB_LAST):
                upstr = util.upper(ls[i].text)

                if upstr.startswith(text) and i != self.line:
                    matches[upstr] = None
                    if i < self.line:
                        last = upstr

        for s in t.items:
            upstr = util.upper(s)

            if upstr.startswith(text):
                matches[upstr] = None

        if last:
            del matches[last]

        mlist = list(matches.keys())
        mlist.sort()

        if last:
            mlist.insert(0, last)

        return mlist

    # returns pair (start, end) of marked lines, inclusive. if mark is
    # after the end of the script (text has been deleted since setting
    # it), returns a valid pair (by truncating selection to current
    # end). returns None if no lines marked.
    def getMarkedLines(self):
        if not self.mark:
            return None

        mark = min(len(self.lines) - 1, self.mark.line)

        if self.line < mark:
            return (self.line, mark)
        else:
            return (mark, self.line)

    # returns pair (start, end) (inclusive) of marked columns for the
    # given line (line must be inside the marked lines). 'marked' is the
    # value returned from getMarkedLines. if marked column is invalid
    # (text has been deleted since setting the mark), returns a valid pair
    # by truncating selection as needed. returns None on errors.
    def getMarkedColumns(self, line, marked):
        if not self.mark:
            return None

        # line is not marked at all
        if (line < marked[0]) or (line > marked[1]):
            return None

        ls = self.lines

        # last valid offset for given line's text
        lvo = max(0, len(ls[line].text) - 1)

        # only one line marked
        if (line == marked[0]) and (marked[0] == marked[1]):
            c1 = min(self.mark.column, self.column)
            c2 = max(self.mark.column, self.column)

        # line is between end lines, so totally marked
        elif (line > marked[0]) and (line < marked[1]):
            c1 = 0
            c2 = lvo

        # line is first line marked
        elif line == marked[0]:

            if line == self.line:
                c1 = self.column

            else:
                c1 = self.mark.column

            c2 = lvo

        # line is last line marked
        elif line == marked[1]:

            if line == self.line:
                c2 = self.column

            else:
                c2 = self.mark.column

            c1 = 0

        # should't happen
        else:
            return None

        c1 = util.clamp(c1, 0, lvo)
        c2 = util.clamp(c2, 0, lvo)

        return (c1, c2)

    # checks if a line is marked. 'marked' is the value returned from
    # getMarkedLines.
    def isLineMarked(self, line, marked):
        return (line >= marked[0]) and (line <= marked[1])

    # get selected text as a ClipData object, optionally deleting it from
    # the script. if nothing is selected, returns None.
    def getSelectedAsCD(self, doDelete):
        marked = self.getMarkedLines()

        if not marked:
            return None

        ls = self.lines

        cd = ClipData()

        for i in range(marked[0], marked[1] + 1):
            c1, c2 = self.getMarkedColumns(i, marked)

            ln = ls[i]

            cd.lines.append(Line(ln.lb, ln.lt, ln.text[c1:c2 + 1]))

        cd.lines[-1].lb = LB_LAST

        if not doDelete:
            return cd

        u = undo.AnyDifference(self)

        # range of lines, inclusive, that we need to totally delete
        del1 = sys.maxsize
        del2 = -1

        # delete selected text from the lines
        for i in range(marked[0], marked[1] + 1):
            c1, c2 = self.getMarkedColumns(i, marked)

            ln = ls[i]
            ln.text = ln.text[0:c1] + ln.text[c2 + 1:]

            if i == marked[0]:
                endCol = c1

            # if we removed all text, mark this line to be deleted
            if len(ln.text) == 0:
                del1 = min(del1, i)
                del2 = max(del2, i)

        # adjust linebreaks
        if marked[0] == marked[1]:

            # user has selected text from a single line only

            ln = ls[marked[0]]

            # if it is a single-line element, we never need to modify
            # its linebreak
            if not self.isOnlyLineOfElem(marked[0]):
                # if we're totally deleting the line and it's the last
                # line of a multi-line element, mark the preceding
                # line as the new last line of the element.

                if not ln.text and self.isLastLineOfElem(marked[0]):
                    ls[marked[0] - 1].lb = LB_LAST

        else:

            # now find the line whose linebreak we need to adjust. if
            # the starting line is not completely removed, it is that,
            # otherwise it is the preceding line, unless we delete the
            # first line of the element, in which case there's nothing
            # to adjust.
            if ls[marked[0]].text:
                ln = ls[marked[0]]
            else:
                if not self.isFirstLineOfElem(marked[0]):
                    ln = ls[marked[0] - 1]
                else:
                    ln = None

            if ln:
                # if the selection ends by removing completely the
                # last line of an element, we need to mark the
                # element's new end, otherwise we must set it to
                # LB_NONE so that the new element is reformatted
                # properly.
                if self.isLastLineOfElem(marked[1]) and \
                       not ls[marked[1]].text:
                    ln.lb = LB_LAST
                else:
                    ln.lb = LB_NONE

        # if we're joining two elements we have to change the line
        # types for the latter element (starting from the last marked
        # line, because everything before that will get deleted
        # anyway) to that of the first element.
        self.setLineTypes(marked[1], ls[marked[0]].lt)

        del ls[del1:del2 + 1]

        self.clearMark()

        if len(ls) == 0:
            ls.append(Line(LB_LAST, SCENE))

        self.line = min(marked[0], len(ls) - 1)
        self.column = min(endCol, len(ls[self.line].text))

        self.rewrapElem()
        self.markChanged()

        u.setAfter(self)
        self.addUndo(u)

        return cd

    # paste data into script. clines is a list of Line objects.
    def paste(self, clines):
        if len(clines) == 0:
            return

        u = undo.AnyDifference(self)

        inLines = []
        i = 0

        # wrap all paragraphs into single lines
        while 1:
            if i >= len(clines):
                break

            ln = clines[i]

            newLine = Line(LB_LAST, ln.lt)

            while 1:
                ln = clines[i]
                i += 1

                newLine.text += ln.text

                if ln.lb in (LB_LAST, LB_FORCED):
                    break

                newLine.text += config.lb2str(ln.lb)

            newLine.lb = ln.lb
            inLines.append(newLine)

        # shouldn't happen, but...
        if len(inLines) == 0:
            return

        ls = self.lines

        # where we need to start wrapping
        wrap1 = self.getParaFirstIndexFromLine(self.line)

        ln = ls[self.line]

        atEnd = self.column == len(ln.text)

        if (len(ln.text) == 0) and self.isOnlyLineOfElem(self.line):
            ln.lt = inLines[0].lt

        ln.text = ln.text[:self.column] + inLines[0].text + \
                  ln.text[self.column:]
        self.column += len(inLines[0].text)

        if len(inLines) != 1:

            if not atEnd:
                self.splitLine()
                ls[self.line - 1].lb = inLines[0].lb
                ls[self.line:self.line] = inLines[1:]
                self.line += len(inLines) - 2

                # FIXME: pasting a multi-paragraph ACTION where first line
                # has FORCED lb, in middle of a CHARACTER block, breaks
                # things

            else:
                ls[self.line + 1:self.line + 1] = inLines[1:]
                self.line += len(inLines) - 1

                # FIXME: this doesn't modify .lb, and pasting a
                # multi-paragraph ACTION at end of line in CHARACTER block
                # where that line ends in forced linebreak breaks things.

            self.column = len(ls[self.line].text)

        # FIXME: copy/paste, when copying elements containing forced
        # linebreaks, converts them to end of element? this seems like a
        # bug...

        self.reformatRange(wrap1, self.getParaFirstIndexFromLine(self.line))

        u.setAfter(self)
        self.addUndo(u)

        self.clearMark()
        self.clearAutoComp()
        self.markChanged()

    # returns true if a character, inserted at current position, would
    # need to be capitalized as a start of a sentence.
    def capitalizeNeeded(self):
        if not self.cfgGl.capitalize:
            return False

        ls = self.lines
        line = self.line
        column = self.column

        text = ls[line].text
        if (column < len(text)) and (text[column] != " "):
            return False

        # go backwards at most 4 characters, looking for "!?.", and
        # breaking on anything other than space or ".

        cnt = 1
        while 1:
            column -= 1

            char = None

            if column < 0:
                line -= 1

                if line < 0:
                    return True

                lb = ls[line].lb

                if lb == LB_LAST:
                    return True

                elif lb == LB_SPACE:
                    char = " "
                    column = len(ls[line].text)

                else:
                    text = ls[line].text
                    column = len(text) - 1

                    if column < 0:
                        return True
            else:
                text = ls[line].text

            if not char:
                char = text[column]

            if cnt == 1:
                # must be preceded by a space
                if char != " ":
                    return False
            else:
                if char in (".", "?", "!"):
                    return True
                elif char not in (" ", "\""):
                    return False

            cnt += 1

            if cnt > 4:
                break

        return False

    # find next error in screenplay, starting at given line. returns
    # (line, msg) tuple, where line is -1 if no error was found and the
    # line number otherwise where the error is, and msg is a description
    # of the error
    def findError(self, line):
        ls = self.lines
        cfg = self.cfg

        # type of previous line, or None when a new element starts
        prevType = None

        msg = None
        while 1:
            if line >= len(ls):
                break

            ln = ls[line]
            tcfg = cfg.getType(ln.lt)

            isFirst = self.isFirstLineOfElem(line)
            isLast = self.isLastLineOfElem(line)
            isOnly = isFirst and isLast

            prev = self.getTypeOfPrevElem(line)
            next = self.getTypeOfNextElem(line)

            # notes are allowed to contain empty lines, because a) they do
            # not appear in the final product b) they're basically
            # free-format text anyway, and people may want to format them
            # however they want

            if (len(ln.text) == 0) and (ln.lt != NOTE):
                msg = "Empty line."
                break

            if (len(ln.text.strip("  ")) == 0) and (ln.lt != NOTE):
                msg = "Empty line (contains only spaces)."
                break

            if (ln.lt == PAREN) and isOnly and (ln.text == "()"):
                msg = "Empty parenthetical."
                break

            if ln.text != util.toInputStr(ln.text):
                msg = "Line contains invalid characters (BUG)."
                break

            if len(ln.text.rstrip(" ")) > tcfg.width:
                msg = "Line is too long (BUG)."
                break

            if ln.lt == CHARACTER:
                if isLast and next and next not in (PAREN, DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(next).ti.name, tcfg.ti.name)
                    break

            if ln.lt == PAREN:
                if isFirst and prev and prev not in (CHARACTER, DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (tcfg.ti.name, cfg.getType(prev).ti.name)
                    break

            if ln.lt == DIALOGUE:
                if isFirst and prev and prev not in (CHARACTER, PAREN):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (tcfg.ti.name, cfg.getType(prev).ti.name)
                    break

            if prevType:
                if ln.lt != prevType:
                    msg = "Element contains lines with different line"\
                          " types (BUG)."
                    break

            if ln.lb == LB_LAST:
                prevType = None
            else:
                prevType = ln.lt

            line += 1

        if not msg:
            line = -1

        return (line, msg)

    # compare this script to sp2 (Screenplay), return a PDF file (as a
    # string) of the differences, or None if the scripts are identical.
    def compareScripts(self, sp2):
        s1 = self.generateText(False).split("\n")
        s2 = sp2.generateText(False).split("\n")

        dltTmp = difflib.unified_diff(s1, s2, lineterm = "")

        # get rid of stupid delta generator object that doesn't allow
        # subscription or anything else really. also expands hunk
        # separators into three lines.
        dlt = []
        i = 0
        for s in dltTmp:
            if i >= 3:
                if s[0] == "@":
                    dlt.extend(["1", "2", "3"])
                else:
                    dlt.append(s)

            i += 1

        if len(dlt) == 0:
            return None

        dltTmp = dlt

        # now, generate changed-lines for single-line diffs
        dlt = []
        for i in range(len(dltTmp)):
            s = dltTmp[i]

            dlt.append(s)

            # this checks that we've just added a sequence of lines whose
            # first characters are " -+", where " " means '"not -" or
            # missing line', and that we're either at end of list or next
            # line does not start with "+".

            if (s[0] == "+") and \
               (i != 0) and (dltTmp[i - 1][0] == "-") and (
                (i == 1) or (dltTmp[i - 2][0] != "-")) and (
                (i == (len(dltTmp) - 1)) or (dltTmp[i + 1][0] != "+")):

                # generate line with "^" character at every position that
                # the lines differ

                s1 = dltTmp[i - 1]
                s2 = dltTmp[i]

                minCnt = min(len(s1), len(s2))
                maxCnt = max(len(s1), len(s2))

                res = "^"

                for i in range(1, minCnt):
                    if s1[i] != s2[i]:
                        res += "^"
                    else:
                        res += " "

                res += "^" * (maxCnt - minCnt)

                dlt.append(res)

        tmp = ["  Color information:", "1", "-  Deleted lines",
               "+  Added lines",
               "^  Positions of single-line changes (marked with ^)", "1",
               "2", "2", "3"]
        tmp.extend(dlt)
        dlt = tmp

        cfg = self.cfg
        chY = util.getTextHeight(cfg.fontSize)

        doc = pml.Document(cfg.paperWidth, cfg.paperHeight)

        # how many lines put on current page
        y = 0

        pg = pml.Page(doc)

        # we need to gather text ops for each page into a separate list
        # and add that list to the page only after all other ops are
        # added, otherwise the colored bars will be drawn partially over
        # some characters.
        textOps = []

        for s in dlt:

            if y >= cfg.linesOnPage:
                pg.ops.extend(textOps)
                doc.add(pg)

                pg = pml.Page(doc)

                textOps = []
                y = 0

            if s[0] == "1":
                pass

            elif s[0] == "3":
                pass

            elif s[0] == "2":
                pg.add(pml.PDFOp("0.75 g"))
                w = 50.0
                pg.add(pml.RectOp(doc.w / 2.0 - w / 2.0, cfg.marginTop +
                    y * chY + chY / 4, w, chY / 2.0))
                pg.add(pml.PDFOp("0.0 g"))

            else:
                color = ""

                if s[0] == "-":
                    color = "1.0 0.667 0.667"
                elif s[0] == "+":
                    color = "0.667 1.0 0.667"
                elif s[0] == "^":
                    color = "1.0 1.0 0.467"

                if color:
                    pg.add(pml.PDFOp("%s rg" % color))
                    pg.add(pml.RectOp(cfg.marginLeft, cfg.marginTop + y * chY,
                        doc.w - cfg.marginLeft - 5.0, chY))
                    pg.add(pml.PDFOp("0.0 g"))

                textOps.append(pml.TextOp(s[1:], cfg.marginLeft,
                    cfg.marginTop + y * chY, cfg.fontSize))

            y += 1

        pg.ops.extend(textOps)
        doc.add(pg)

        return pdf.generate(doc)

    # move to line,col, and if mark is True, set mark there
    def gotoPos(self, line, col, mark = False):
        self.clearAutoComp()

        self.line = line
        self.column = col

        if mark and not self.mark:
            self.setMark(line, col)

    # remove all lines whose element types are in tdict as keys.
    def removeElementTypes(self, tdict, saveUndo):
        self.clearAutoComp()

        if saveUndo:
            u = undo.FullCopy(self)

        lsNew = []
        lsOld = self.lines
        sl = self.line

        # how many lines were removed from above the current line
        # (inclusive)
        cnt = 0

        for i in range(len(lsOld)):
            l = lsOld[i]

            if l.lt not in tdict:
                lsNew.append(l)
            else:
                if i <= sl:
                    cnt += 1

        self.line -= cnt

        if len(lsNew) == 0:
            lsNew.append(Line(LB_LAST, SCENE))

        self.lines = lsNew

        self.validatePos()
        self.clearMark()
        self.markChanged()

        if saveUndo:
            u.setAfter(self)
            self.addUndo(u)

    # set mark at given position
    def setMark(self, line, column):
        self.mark = Mark(line, column)

    # clear mark
    def clearMark(self):
        self.mark = None

    # if doIt is True and mark is not yet set, set it at current position.
    def maybeMark(self, doIt):
        if doIt and not self.mark:
            self.setMark(self.line, self.column)

    # make sure current line and column are within the valid bounds.
    def validatePos(self):
        self.line = util.clamp(self.line, 0, len(self.lines) - 1)
        self.column = util.clamp(self.column, 0,
                                 len(self.lines[self.line].text))

    # this must be called after each command (all functions named fooCmd
    # are commands)
    def cmdPost(self, cs):
        # TODO: is this needed?
        self.column = min(self.column, len(self.lines[self.line].text))

        if cs.doAutoComp == cs.AC_DEL:
            self.clearAutoComp()
        elif cs.doAutoComp == cs.AC_REDO:
            self.fillAutoComp()

    # helper function for calling commands. name is the name of the
    # command, e.g. "moveLeft".
    def cmd(self, name, char = None, count = 1):
        for i in range(count):
            cs = CommandState()

            if char:
                cs.char = char

            getattr(self, name + "Cmd")(cs)
            self.cmdPost(cs)

    # call addCharCmd for each character in s. ONLY MEANT TO BE USED IN
    # TEST CODE.
    def cmdChars(self, s):
        for char in s:
            self.cmd("addChar", char = char)

    def moveLeftCmd(self, cs):
        self.maybeMark(cs.mark)

        if self.column > 0:
            self.column -= 1
        else:
            if self.line > 0:
                self.line -= 1
                self.column = len(self.lines[self.line].text)

    def moveRightCmd(self, cs):
        self.maybeMark(cs.mark)

        if self.column != len(self.lines[self.line].text):
            self.column += 1
        else:
            if self.line < (len(self.lines) - 1):
                self.line += 1
                self.column = 0

    def moveUpCmd(self, cs):
        if not self.acItems:
            self.maybeMark(cs.mark)

            if self.line > 0:
                self.line -= 1

        else:
            self.acSel -= 1

            if self.acSel < 0:
                self.acSel = len(self.acItems) - 1

            cs.doAutoComp = cs.AC_KEEP

    def moveDownCmd(self, cs):
        if not self.acItems:
            self.maybeMark(cs.mark)

            if self.line < (len(self.lines) - 1):
                self.line += 1

        else:
            self.acSel = (self.acSel + 1) % len(self.acItems)

            cs.doAutoComp = cs.AC_KEEP

    def moveLineEndCmd(self, cs):
        if self.acItems:
            self.lines[self.line].text = self.acItems[self.acSel]
        else:
            self.maybeMark(cs.mark)

        self.column = len(self.lines[self.line].text)

    def moveLineStartCmd(self, cs):
        self.maybeMark(cs.mark)

        self.column = 0

    def moveStartCmd(self, cs):
        self.maybeMark(cs.mark)

        self.line = 0
        self.setTopLine(0)
        self.column = 0

    def moveEndCmd(self, cs):
        self.maybeMark(cs.mark)

        self.line = len(self.lines) - 1
        self.column = len(self.lines[self.line].text)

    def moveSceneUpCmd(self, cs):
        self.maybeMark(cs.mark)

        tmpUp = self.getSceneIndexes()[0]

        if self.line != tmpUp:
            self.line = tmpUp
        else:
            tmpUp -= 1
            if tmpUp >= 0:
                self.line = self.getSceneIndexesFromLine(tmpUp)[0]

        self.column = 0

    def moveSceneDownCmd(self, cs):
        self.maybeMark(cs.mark)

        tmpBottom = self.getSceneIndexes()[1]
        self.line = min(len(self.lines) - 1, tmpBottom + 1)
        self.column = 0

    def deleteBackwardCmd(self, cs):
        u = None
        mergeUndo = False

        # only merge with the previous item in undo history if:
        #   -we are not in middle of undo/redo
        #   -previous item is "delete backward"
        #   -cursor is exactly where it was left off by the previous item
        if (not self.currentUndo and self.lastUndo and
            (self.lastUndo.getType() == undo.CMD_DEL_BACKWARD) and
            (self.lastUndo.endPos == self.cursorAsMark())):
            u = self.lastUndo
            mergeUndo = True

        if self.column != 0:
            if not mergeUndo:
                u = undo.ManyElems(self, undo.CMD_DEL_BACKWARD, self.line, 1, 1)

            self.deleteChar(self.line, self.column - 1)
            self.markChanged()
            cs.doAutoComp = cs.AC_REDO
        else:
            if self.line != 0:
                ln = self.lines[self.line - 1]

                # delete at start of the line of the first line of the
                # element means "join up with previous element", so is a
                # 2->1 change. otherwise we just delete a character from
                # current element so no element count change.
                if ln.lb == LB_LAST:
                    u = undo.ManyElems(self, undo.CMD_MISC, self.line - 1, 2, 1)
                    mergeUndo = False
                else:
                    if not mergeUndo:
                        u = undo.ManyElems(self, undo.CMD_DEL_BACKWARD, self.line, 1, 1)

                if ln.lb == LB_NONE:
                    self.deleteChar(self.line - 1, len(ln.text) - 1,
                                    False)

                self.joinLines(self.line - 1)

                self.markChanged()

        self.rewrapElem()

        if u:
            if mergeUndo:
                self.addMergedUndo(u)
            else:
                u.setAfter(self)
                self.addUndo(u)

    def deleteForwardCmd(self, cs):
        u = None
        mergeUndo = False

        # only merge with the previous item in undo history if:
        #   -we are not in middle of undo/redo
        #   -previous item is "delete forward"
        #   -cursor is exactly where it was left off by the previous item
        if (not self.currentUndo and self.lastUndo and
            (self.lastUndo.getType() == undo.CMD_DEL_FORWARD) and
            (self.lastUndo.endPos == self.cursorAsMark())):
            u = self.lastUndo
            mergeUndo = True

        if self.column != len(self.lines[self.line].text):
            if not mergeUndo:
                u = undo.ManyElems(self, undo.CMD_DEL_FORWARD, self.line, 1, 1)

            self.deleteChar(self.line, self.column)
            self.markChanged()
            cs.doAutoComp = cs.AC_REDO
        else:
            if self.line != (len(self.lines) - 1):
                ln = self.lines[self.line]

                # delete at end of the line of the last line of the
                # element means "join up with next element", so is a 2->1
                # change. otherwise we just delete a character from
                # current element so no element count change.
                if ln.lb == LB_LAST:
                    u = undo.ManyElems(self, undo.CMD_MISC, self.line, 2, 1)
                    mergeUndo = False
                else:
                    if not mergeUndo:
                        u = undo.ManyElems(self, undo.CMD_DEL_FORWARD, self.line, 1, 1)

                if ln.lb == LB_NONE:
                    self.deleteChar(self.line + 1, 0, False)

                self.joinLines(self.line)

                self.markChanged()

        self.rewrapElem()

        if u:
            if mergeUndo:
                self.addMergedUndo(u)
            else:
                u.setAfter(self)
                self.addUndo(u)

    # aborts stuff, like selection, auto-completion, etc
    def abortCmd(self, cs):
        self.clearMark()

    # select all text of current scene
    def selectSceneCmd(self, cs):
        l1, l2 = self.getSceneIndexes()

        self.setMark(l1, 0)

        self.line = l2
        self.column = len(self.lines[l2].text)

    # select all text of the screenplay. sets mark at beginning and moves
    # cursor to the end.
    def selectAllCmd(self, cs):
        self.setMark(0, 0)

        self.line = len(self.lines) - 1
        self.column = len(self.lines[self.line].text)

    def insertForcedLineBreakCmd(self, cs):
        u = undo.ManyElems(self, undo.CMD_MISC, self.line, 1, 1)

        self.splitLine()

        self.rewrapPara()
        self.rewrapPrevPara()

        u.setAfter(self)
        self.addUndo(u)

    def splitElementCmd(self, cs):
        tcfg = self.cfgGl.getType(self.lines[self.line].lt)
        self.splitElement(tcfg.newTypeEnter)

    def setMarkCmd(self, cs):
        self.setMark(self.line, self.column)

    # either creates a new element or converts the current one to
    # nextTypeTab, depending on circumstances.
    def tabCmd(self, cs):
        if self.mark:
            self.clearMark()

            return

        tcfg = self.cfgGl.getType(self.lines[self.line].lt)

        if self.tabMakesNew():
            self.splitElement(tcfg.newTypeTab)
        else:
            self.convertTypeTo(tcfg.nextTypeTab, True)

    # switch current element to prevTypeTab.
    def toPrevTypeTabCmd(self, cs):
        if self.mark:
            self.clearMark()

            return

        tcfg = self.cfgGl.getType(self.lines[self.line].lt)
        self.convertTypeTo(tcfg.prevTypeTab, True)

    # add character cs.char if it's a valid one.
    def addCharCmd(self, cs):
        char = cs.char

        if len(char) != 1:
            return

        kc = ord(char)

        if not util.isValidInputChar(kc):
            return

        isSpace = char == " "

        # only merge with the previous item in undo history if:
        #   -we are not in middle of undo/redo
        #   -previous item is "add character"
        #   -cursor is exactly where it was left off by the previous item
        #
        # in addition, to get word-level undo, not element-level undo, we
        # want to merge all spaces with the word preceding them, but stop
        # merging when a new word begins. this is implemented by the
        # following algorith:
        #
        # lastUndo    char       merge
        # --------    -------    -----
        # non-space   non-space  Y
        # non-space   space      Y      <- change type of lastUndo to space
        # space       space      Y
        # space       non-space  N

        if (not self.currentUndo and self.lastUndo and
            (self.lastUndo.getType() in (undo.CMD_ADD_CHAR, undo.CMD_ADD_CHAR_SPACE)) and
            (self.lastUndo.endPos == self.cursorAsMark()) and
            not ((self.lastUndo.getType() == undo.CMD_ADD_CHAR_SPACE) and not isSpace)):

            u = self.lastUndo
            mergeUndo = True

            if isSpace:
                u.cmdType = undo.CMD_ADD_CHAR_SPACE
        else:
            mergeUndo = False

            if isSpace:
                u = undo.SinglePara(self, undo.CMD_ADD_CHAR_SPACE, self.line)
            else:
                u = undo.SinglePara(self, undo.CMD_ADD_CHAR, self.line)

        if self.capitalizeNeeded():
            char = util.upper(char)

        ls = self.lines
        s = ls[self.line].text

        if self.cfgGl.capitalizeI and (self.column > 0):
            s = ls[self.line].text

            if s[self.column - 1] == "i":
                if not util.isAlnum(char):
                    doIt = False

                    if self.column > 1:
                        if not util.isAlnum(s[self.column - 2]):
                            doIt = True
                    else:
                        if (self.line == 0) or \
                               (ls[self.line - 1].lb != LB_NONE):
                            doIt = True

                    if doIt:
                        s = util.replace(s, "I", self.column - 1, 1)

        s = s[:self.column] + char + s[self.column:]
        ls[self.line].text = s
        self.column += 1

        tmp = s.upper()
        if (tmp == "EXT.") or (tmp == "INT."):
            if self.isOnlyLineOfElem(self.line):
                ls[self.line].lt = SCENE
        elif (tmp == "(") and\
             ls[self.line].lt in (DIALOGUE, CHARACTER) and\
             self.isOnlyLineOfElem(self.line):
            ls[self.line].lt = PAREN
            ls[self.line].text = "()"

        self.rewrapPara()
        self.markChanged()

        cs.doAutoComp = cs.AC_REDO

        if mergeUndo:
            self.addMergedUndo(u)
        else:
            u.setAfter(self)
            self.addUndo(u)

    def toSceneCmd(self, cs):
        self.convertTypeTo(SCENE, True)

    def toActionCmd(self, cs):
        self.convertTypeTo(ACTION, True)

    def toCharacterCmd(self, cs):
        self.convertTypeTo(CHARACTER, True)

    def toDialogueCmd(self, cs):
        self.convertTypeTo(DIALOGUE, True)

    def toParenCmd(self, cs):
        self.convertTypeTo(PAREN, True)

    def toTransitionCmd(self, cs):
        self.convertTypeTo(TRANSITION, True)

    def toShotCmd(self, cs):
        self.convertTypeTo(SHOT, True)

    def toActBreakCmd(self, cs):
        self.convertTypeTo(ACTBREAK, True)

    def toNoteCmd(self, cs):
        self.convertTypeTo(NOTE, True)

    # return True if we can undo
    def canUndo(self):
        return bool(
            # undo history exists
            self.lastUndo

            # and we either:
            and (
                # are not in the middle of undo/redo
                not self.currentUndo or

                # or are, but can still undo more
                self.currentUndo.prev))

    # return True if we can redo
    def canRedo(self):
        return bool(self.currentUndo)

    def addUndo(self, u):
        if self.currentUndo:
            # new edit action while navigating undo history; throw away
            # any undo history after current point

            if self.currentUndo.prev:
                # not at beginning of undo history; cut off the rest
                self.currentUndo.prev.next = None
                self.lastUndo = self.currentUndo.prev
            else:
                # beginning of undo history; throw everything away
                self.firstUndo = None
                self.lastUndo = None

            self.currentUndo = None

            # we threw away an unknown number of undo items, so we must go
            # through all of the remaining ones and recalculate how much
            # memory is used
            self.undoMemoryUsed = 0

            tmp = self.firstUndo

            while tmp:
                self.undoMemoryUsed += tmp.memoryUsed()
                tmp = tmp.next

        if not self.lastUndo:
            # no undo history at all yet
            self.firstUndo = u
            self.lastUndo = u
        else:
            self.lastUndo.next = u
            u.prev = self.lastUndo
            self.lastUndo = u

        self.undoMemoryUsed += u.memoryUsed()

        # trim undo history until the estimated memory usage is small
        # enough
        while ((self.firstUndo is not self.lastUndo) and
               (self.undoMemoryUsed >= 5000000)):

            tmp = self.firstUndo
            tmp.next.prev = None
            self.firstUndo = tmp.next

            # it shouldn't be technically necessary to reset this, but it
            # might make the GC's job easier, and helps detecting bugs if
            # somebody somehow tries to access this later on
            tmp.next = None

            self.undoMemoryUsed -= tmp.memoryUsed()

        self.currentUndo = None

    def addMergedUndo(self, u):
        assert u is self.lastUndo

        memoryUsedBefore = u.memoryUsed()
        u.setAfter(self)
        memoryUsedAfter = u.memoryUsed()
        memoryUsedDiff = memoryUsedAfter - memoryUsedBefore

        self.undoMemoryUsed += memoryUsedDiff

    def undoCmd(self, cs):
        if not self.canUndo():
            return

        # the action to undo
        if self.currentUndo:
            u = self.currentUndo.prev
        else:
            u = self.lastUndo

        u.undo(self)
        self.currentUndo = u

        self.clearMark()
        self.markChanged()

    def redoCmd(self, cs):
        if not self.canRedo():
            return

        self.currentUndo.redo(self)
        self.currentUndo = self.currentUndo.next

        self.clearMark()
        self.markChanged()

    # check script for internal consistency. raises an AssertionError on
    # errors. ONLY MEANT TO BE USED IN TEST CODE.
    def _validate(self):
        # type of previous line, or None when a new element starts
        prevType = None

        # there must be at least one line
        assert len(self.lines) > 0

        # cursor position must be valid
        assert self.line >= 0
        assert self.line < len(self.lines)
        assert self.column >= 0
        assert self.column <= len(self.lines[self.line].text)

        for ln in self.lines:
            tcfg = self.cfg.getType(ln.lt)

            # lines should not contain invalid characters
            assert ln.text == util.toInputStr(ln.text)

            # lines shouldn't be longer than the type's maximum width,
            # unless the extra characters are all spaces
            assert len(ln.text.rstrip(" ")) <= tcfg.width

            # lines with LB_NONE linebreaks that end in a space should be
            # LB_SPACE instead
            if ln.lb == LB_NONE:
                assert not ln.text.endswith(" ")

            if prevType:
                assert ln.lt == prevType

            if ln.lb == LB_LAST:
                prevType = None
            else:
                prevType = ln.lt

# one line in a screenplay
class Line:
    def __init__(self, lb = LB_LAST, lt = ACTION, text = ""):

        # line break type
        self.lb = lb

        # line type
        self.lt = lt

        # text
        self.text = text

    def __str__(self):
        return config.lb2char(self.lb) + config.lt2char(self.lt)\
               + self.text

    def __ne__(self, other):
        return ((self.lt != other.lt) or (self.lb != other.lb) or
                (self.text != other.text))

    # opposite of __str__. NOTE: only meant for storing data internally by
    # the program! NOT USABLE WITH EXTERNAL INPUT DUE TO COMPLETE LACK OF
    # ERROR CHECKING!
    @staticmethod
    def fromStr(s):
        return Line(config.char2lb(s[0]), config.char2lt(s[1]), s[2:])

# used to keep track of selected area. this marks one of the end-points,
# while the other one is the current position.
class Mark:
    def __init__(self, line, column):
        self.line = line
        self.column = column

    def __eq__(self, other):
        return (self.line == other.line) and (self.column == other.column)

# data held in internal clipboard.
class ClipData:
    def __init__(self):

        # list of Line objects
        self.lines = []

# stuff we need when handling commands in Screenplay.
class CommandState:

    # what to do about auto-completion
    AC_DEL, AC_REDO, AC_KEEP = list(range(3))

    def __init__(self):

        self.doAutoComp = self.AC_DEL

        # only used for inserting characters, in which case this is the
        # character to insert in a string form.
        self.char = None

        # True if this is a movement command and we should set mark at the
        # current position before moving (note that currently this is just
        # set if shift is down)
        self.mark = False

        # True if we need to make current line visible
        self.needsVisifying = True

# keeps a collection of page numbers from a given screenplay, and allows
# formatting of the list intelligently, e.g. "4-7, 9, 11-16".
class PageList:
    def __init__(self, allPages):
        # list of all pages in the screenplay, in the format returned by
        # Screenplay.getPageNumbers().
        self.allPages = allPages

        # key = page number (str), value = unused
        self.pages = {}

    # add page to page list if it's not already there
    def addPage(self, page):
        self.pages[str(page)] = True

    def __len__(self):
        return len(self.pages)

    # merge two PageLists
    def __iadd__(self, other):
        for pg in list(other.pages.keys()):
            self.addPage(pg)

        return self

    # return textual representation of pages where consecutive pages are
    # formatted as "x-y". example: "3, 5-8, 11".
    def __str__(self):
        # one entry for each page from above, containing True if that page
        # is contained in this PageList object
        hasPage = []

        for p in self.allPages:
            hasPage.append(p in list(self.pages.keys()))

        # finished string
        s = ""

        # start index of current range, or -1 if no range in progress
        rangeStart = -1

        for i in range(len(self.allPages)):
            if rangeStart != -1:
                if not hasPage[i]:

                    # range ends

                    if i != (rangeStart + 1):
                        s += "-%s" % self.allPages[i - 1]

                    rangeStart = -1
            else:
                if hasPage[i]:
                    if s:
                        s += ", "

                    s += self.allPages[i]
                    rangeStart = i

        last = len(self.allPages) - 1

        # finish last range if needed
        if (rangeStart != -1) and (rangeStart != last):
            s += "-%s" % self.allPages[last]

        return s
