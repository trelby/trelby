#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

from error import *
import bugreport
import cfgdlg
import charmapdlg
import commandsdlg
import config
import decode
import dialoguechart
import finddlg
import headers
import headersdlg
import misc
import myimport
import mypickle
import namesdlg
import pdf
import pml
import report
import screenplay
import splash
import titles
import titlesdlg
import util

import codecs
import copy
import datetime
import difflib
import os
import os.path
import re
import signal
import sys
import time
from wxPython.wx import *

#keycodes
KC_CTRL_A = 1
KC_CTRL_B = 2
KC_CTRL_D = 4
KC_CTRL_E = 5
KC_CTRL_F = 6
KC_CTRL_N = 14
KC_CTRL_P = 16
KC_CTRL_V = 22

def refreshGuiConfig():
    global cfgGui

    cfgGui = config.ConfigGui(cfg)

# keeps (some) global data
class GlobalData:
    def __init__(self):

        self.confFilename = misc.confPath + "/default.conf"
        self.stateFilename = misc.confPath + "/state"

        if "--conf" in sys.argv:
            i = sys.argv.index("--conf")

            if (i + 1) >= len(sys.argv):
                wxMessageBox("Missing argument to --conf parameter.",
                             "Error")
            else:
                self.confFilename = sys.argv[i + 1]

        v = self.cvars = mypickle.Vars()

        v.addInt("posX", 0, "PositionX", -20, 9999)
        v.addInt("posY", 0, "PositionY", -20, 9999)

        # linux has bigger font by default so it needs a wider window
        defaultW = 750
        if misc.isUnix:
            defaultW = 800

        v.addInt("width", defaultW, "Width", 500, 9999)
        
        v.addInt("height", 830, "Height", 300, 9999)
        v.addBool("isDraft", False, "IsDraftMode")
        v.addStr("license", "", "License")
        
        v.makeDicts()
        v.setDefaults(self)

        self.height = min(self.height,
            wxSystemSettings_GetMetric(wxSYS_SCREEN_Y) - 50)

        self.makeConfDir()

    # update stuff that depends on configuration / window size etc.
    def refresh(self):
        self.chX = util.getTextWidth(" ", pml.COURIER, cfg.fontSize)
        self.chY = util.getTextHeight(cfg.fontSize)

        self.pageW = (cfg.paperWidth / self.chX) * cfgGui.fonts[pml.NORMAL].fx

        # conversion factor from mm to pixels
        self.mm2p = self.pageW / cfg.paperWidth

        # page width and height on screen, in pixels
        self.pageW = int(self.pageW)
        self.pageH = int(self.mm2p * cfg.paperHeight)

    def makeConfDir(self):
        makeDir = False

        try:
            os.stat(misc.confPath)
        except OSError:
            makeDir = True

        if makeDir:
            try:
                os.mkdir(misc.confPath, 0755)
            except OSError, (errno, strerror):
                wxMessageBox("Error creating configuration directory\n"
                             "'%s': %s" % (misc.confPath, strerror), "Error",
                             wxOK, None)

# a piece of text on screen.
class TextString:
    def __init__(self, line, text, x, y, fi, isUnderlined, partial):

        # if this object is a screenplay line, this is the index of the
        # corresponding line in the Screenplay.lines list. otherwise this
        # is -1 (used for stuff like CONTINUED: etc).
        self.line = line

        # x,y coordinates in pixels from widget's topleft corner
        self.x = x
        self.y = y

        # text and its FontInfo and underline status
        self.text = text
        self.fi = fi
        self.isUnderlined = isUnderlined

        # if True, bottom cut off, i.e. only partially visible
        self.partial = partial

# a page shown on screen.
class DisplayPage:
    def __init__(self, x1 = -1, y1 = -1, x2 = -1, y2 = -1):

        # coordinates in pixels
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

# used to iteratively add PML pages to a document
class Pager:
    def __init__(self, sp):
        self.sp = sp
        self.doc = pml.Document(cfg.paperWidth, cfg.paperHeight)

        # used in several places, so keep around
        self.charIndent = cfg.getType(config.CHARACTER).indent
        self.sceneIndent = cfg.getType(config.SCENE).indent

        # current scene number
        self.scene = 0

        # number of CONTINUED:'s lines added for current scene
        self.sceneContNr = 0

# caches pml.Pages for operations that repeatedly construct them over and
# over again without the page contents changing
class PageCache:
    def __init__(self, ctrl):
        self.ctrl = ctrl
        
        # cached pages. key = pageNr, value = pml.Page
        self.pages = {}

    def getPage(self, pager, pageNr):
        pg = self.pages.get(pageNr)

        if not pg:
            pg = self.ctrl.generatePMLPage(pager, pageNr, False, False)
            self.pages[pageNr] = pg
            
        return pg

# used to keep track of selected area. this marks one of the end-points,
# while the other one is the current position.
class Mark:
    def __init__(self, line, column):
        self.line = line
        self.column = column

# data held in internal clipboard.
class ClipData:
    def __init__(self):

        # list of screenplay.Line objects
        self.lines = []
        
class Screenplay:
    def __init__(self):
        self.titles = titles.Titles()
        self.headers = headers.Headers()
        self.lines = []
        
    def __eq__(self, other):
        if len(self.lines) != len(other.lines):
            return False

        if self.titles != other.titles:
            return False
        
        if self.headers != other.headers:
            return False
        
        for i in xrange(len(self.lines)):
            if self.lines[i] != other.lines[i]:
                return False

        return True
    
    def __ne__(self, other):
        return not self == other
    
    def getSpacingBefore(self, i):
        if i == 0:
            return 0

        tcfg = cfg.types[self.lines[i].lt]
        
        if self.lines[i - 1].lb == config.LB_LAST:
            return tcfg.beforeSpacing
        else:
            return tcfg.intraSpacing

    def replace(self):
        for i in xrange(len(self.lines)):
            self.lines[i].replace()

    # this is ~8x faster than the generic deepcopy, which makes a
    # noticeable difference at least on an Athlon 1.3GHz (0.06s versus
    # 0.445s)
    def __deepcopy__(self, memo):
        sp = Screenplay()
        l = sp.lines

        sp.titles = copy.deepcopy(self.titles)
        sp.headers = copy.deepcopy(self.headers)

        for i in xrange(len(self.lines)):
            ln = self.lines[i]
            l.append(screenplay.Line(ln.lb, ln.lt, ln.text))

        return sp
            
class MyPanel(wxPanel):

    def __init__(self, parent, id):
        wxPanel.__init__(self, parent, id, style = wxWANTS_CHARS)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        self.scrollBar = wxScrollBar(self, -1, style = wxSB_VERTICAL)
        self.ctrl = MyCtrl(self, -1)

        hsizer.Add(self.ctrl, 1, wxEXPAND)
        hsizer.Add(self.scrollBar, 0, wxEXPAND)
        
        EVT_COMMAND_SCROLL(self, self.scrollBar.GetId(),
                           self.ctrl.OnScroll)

        EVT_SET_FOCUS(self.scrollBar, self.OnScrollbarFocus)
                           
        self.SetSizer(hsizer)

    # we never want the scrollbar to get the keyboard focus, pass it on to
    # the main widget
    def OnScrollbarFocus(self, event):
        self.ctrl.SetFocus()
    
class MyCtrl(wxControl):

    def __init__(self, parent, id):
        wxControl.__init__(self, parent, id, style=wxWANTS_CHARS)

        self.panel = parent
        
        EVT_SIZE(self, self.OnSize)
        EVT_PAINT(self, self.OnPaint)
        EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
        EVT_LEFT_DOWN(self, self.OnLeftDown)
        EVT_LEFT_DCLICK(self, self.OnLeftDown)
        EVT_RIGHT_DOWN(self, self.OnRightDown)
        EVT_MOTION(self, self.OnMotion)
        EVT_MOUSEWHEEL(self, self.OnMouseWheel)
        EVT_CHAR(self, self.OnKeyChar)

        self.createEmptySp()
        self.updateScreen(redraw = False)

    def clearVars(self):
        self.line = 0
        self.column = 0
        self._topLine = 0
        self.mark = None
        self.autoComp = None
        self.autoCompSel = -1
        self.searchLine = -1
        self.searchColumn = -1
        self.searchWidth = -1
        self.pages = [-1, 0]
        self.pagesNoAdjust = [-1, 0]
        self.maxAutoCompItems = 10
        self.lastPaginated = 0.0

        # find dialog stored settings
        self.findDlgFindText = ""
        self.findDlgReplaceText = ""
        self.findDlgMatchWholeWord= False
        self.findDlgMatchCase = False
        self.findDlgDirUp = False
        self.findDlgUseExtra = False
        self.findDlgElements = None
        
    def createEmptySp(self):
        self.clearVars()
        self.sp = Screenplay()
        self.sp.titles.addDefaults()
        self.sp.headers.addDefaults()
        self.sp.lines.append(screenplay.Line(config.LB_LAST, config.SCENE))
        self.setFile(None)
        self.makeBackup()
        
    def loadFile(self, fileName):
        try:
            try:
                f = open(fileName, "rb")

                try:
                    bom = f.read(3)
                    if bom != codecs.BOM_UTF8:
                        raise MiscError("File is not a Blyte screenplay.")
                    
                    lines = f.readlines()
                finally:
                    f.close()

            except IOError, (errno, strerror):
                raise MiscError("IOError: %s" % strerror)
            
            sp = Screenplay()

            # used to keep track that element type only changes after a
            # LB_LAST line.
            prevType = None

            # did we encounter characters not in ISO-8859-1
            invalidChars = False

            # did we encounter characters in ISO-8859-1, but undesired
            unwantedChars = False

            # convert to ISO-8859-1, remove newlines
            for i in xrange(len(lines)):
                try:
                    s = unicode(lines[i], "UTF-8")
                except ValueError:
                    raise MiscError("Line %d contains invalid UTF-8 data."
                                    % (i + 1))

                try:
                    s = s.encode("ISO-8859-1")
                except ValueError:
                    invalidChars = True
                    s = s.encode("ISO-8859-1", "backslashreplace")

                s = util.fixNL(s.rstrip("\n"))
                
                newS = util.toInputStr(s)
                if s != newS:
                    unwantedChars = True
                    
                lines[i] = newS

            if len(lines) < 2:
                raise MiscError("File has too few lines to be a valid"
                                " screenplay file.")

            key, version = self.parseConfigLine(lines[0])
            if not key or (key != "Version"):
                raise MiscError("File doesn't seem to be a proper"
                                " screenplay file.")

            if version != "1":
                raise MiscError("File uses fileformat version '%s',\n"
                                "while this version of the program only"
                                " supports version '1'." % version)

            # did we encounter unknown lb types
            unknownLb = False
            
            # did we encounter unknown element types
            unknownTypes = False

            # did we encounter unknown config lines
            unknownConfigs = False

            for i in xrange(1, len(lines)):
                s = lines[i]

                if len(s) < 2:
                    raise MiscError("Line %d is too short." % (i + 1))
                
                if s[0] == "#":
                    key, val = self.parseConfigLine(s)
                    if not key:
                        raise MiscError("Line %d has invalid syntax for"
                            " config line." % (i + 1))

                    if key == "Title-Page":
                        sp.titles.pages.append([])
                        
                    elif key == "Title-String":
                        if len(sp.titles.pages) == 0:
                            sp.titles.pages.append([])

                        tmp = titles.TitleString()
                        tmp.load(val)
                        sp.titles.pages[-1].append(tmp)

                    elif key == "Header-String":
                        tmp = headers.HeaderString()
                        tmp.load(val)
                        sp.headers.hdrs.append(tmp)

                    elif key == "Header-Empty-Lines":
                        sp.headers.emptyLinesAfter = util.str2int(val, 1, 0, 5)

                    else:
                        unknownConfigs = True
                        
                else:
                    lb = config.text2lb(s[0], False)
                    lt = config.text2lt(s[1], False)
                    text = s[2:]

                    # convert unknown lb types into LB_SPACE
                    if lb == None:
                        lb = config.LB_SPACE
                        unknownLb = True
                        
                    # convert unknown types into ACTION
                    if lt == None:
                        lt = config.ACTION
                        unknownTypes = True
                    
                    if prevType and (lt != prevType):
                        raise MiscError("Line %d has invalid element type." %
                             (i + 1))

                    line = screenplay.Line(lb, lt, text)
                    sp.lines.append(line)

                    if lb != config.LB_LAST:
                        prevType = lt
                    else:
                        prevType = None

            if len(sp.lines) == 0:
                raise MiscError("Empty file.")

            if sp.lines[-1].lb != config.LB_LAST:
                raise MiscError("Last line doesn't end an element.")

            self.clearVars()
            self.sp = sp
            self.reformatAll(False)
            self.setFile(fileName)
            self.makeBackup()
            self.paginate()

            if unknownLb:
                wxMessageBox("Screenplay contained unknown linebreak types.\n"
                             "These have been converted to a space.",
                             "Warning",
                             wxOK, mainFrame)

            if unknownTypes:
                wxMessageBox("Screenplay contained unknown element types.\n"
                             "These have been converted to Action elements.",
                             "Warning",
                             wxOK, mainFrame)

            if unknownConfigs:
                wxMessageBox("Screenplay contained unknown information.\n"
                             "This probably means that the file was created\n"
                             "with a newer version of this program.\n\n"
                             "You'll lose that information if you save over\n"
                             "the existing file.\n",
                             "Warning", wxOK, mainFrame)

            if invalidChars:
                wxMessageBox("Screenplay contained characters not in the\n"
                             "ISO-8859-1 character set, which is all that\n"
                             "this version of the program supports.\n\n"
                             "These characters have been converted to their\n"
                             "Unicode escape sequences. Search for '\u' to\n"
                             "find them.", "Warning", wxOK, mainFrame)

            if unwantedChars:
                wxMessageBox("Screenplay contained invalid characters.\n"
                             "These characters have been converted to '|'.",
                             "Warning", wxOK, mainFrame)
                
            return True

        except BlyteError, e:
            wxMessageBox("Error loading file: %s" % e, "Error",
                         wxOK, mainFrame)

            return False

    def saveFile(self, fileName):
        ls = self.sp.lines

        output = util.String()

        output += codecs.BOM_UTF8
        output += "#Version 1\n"

        pgs = self.sp.titles.pages
        for pg in xrange(len(pgs)):
            if pg != 0:
                output += "#Title-Page \n"

            for i in xrange(len(pgs[pg])):
                output += "#Title-String %s\n" % util.toUTF8(str(pgs[pg][i]))

        for h in self.sp.headers.hdrs:
            output += "#Header-String %s\n" % util.toUTF8(str(h))

        output += "#Header-Empty-Lines %d\n" % self.sp.headers.emptyLinesAfter
        
        for i in xrange(len(ls)):
            output += util.toUTF8(str(ls[i]) + "\n")

        if util.writeToFile(fileName, str(output), mainFrame):
            self.setFile(fileName)
            self.makeBackup()

    def importFile(self, fileName):
        lines = myimport.importTextFile(fileName, mainFrame)

        if not lines:
            return
        
        sp = Screenplay()
        sp.lines = lines

        self.clearVars()
        self.sp = sp
        self.reformatAll(False)
        self.setFile(None)
        self.makeBackup()
        self.paginate()

    # generate exportable text from given screenplay, or None.
    def getExportText(self, sp):
        inf = []
        inf.append(misc.CheckBoxItem("Include page markers"))

        dlg = misc.CheckBoxDlg(mainFrame, "Output options", inf,
                               "Options:", False)

        if dlg.ShowModal() != wxID_OK:
            dlg.Destroy()

            return None

        return self.generateText(sp, inf[0].selected)

    # generate formatted text from given screenplay and return it as a
    # string. if 'dopages' is True, marks pagination in the output.
    def generateText(self, sp, doPages):
        ls = sp.lines
        
        output = util.String()

        for p in xrange(1, len(self.pages)):
            start = self.pages[p - 1] + 1
            end = self.pages[p]

            if doPages and (p != 1):
                s = "%s %d. " % ("-" * 30, p)
                s += "-" * (60 - len(s))
                output += "\n%s\n\n" % s

            for i in xrange(start, end + 1):
                line = ls[i]
                tcfg = cfg.getType(line.lt)

                if tcfg.export.isCaps:
                    text = util.upper(line.text)
                else:
                    text = line.text

                if (i != 0) and (not doPages or (i != start)):
                    output += (sp.getSpacingBefore(i) / 10) * "\n"

                output += " " * tcfg.indent + text + "\n"

        return str(output)

    # generate PDF file from given screenplay and return it as a string.
    # assumes paginate/reformat is 100% correct for the screenplay.
    def generatePDF(self, sp):
        #lsdjflksj = util.TimerDev("generatePDF")

        pager = Pager(sp)
        sp.titles.generatePages(pager.doc)
        
        for i in xrange(1, len(self.pages)):
            pg = self.generatePMLPage(pager, i, True, True)

            if pg:
                pager.doc.add(pg)
            else:
                break
            
        return pdf.generate(pager.doc)

    # generate one page of PML data and return it.
    #
    # if forPDF is True, output is meant for PDF generation (demo stamps,
    # print settings, etc).
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

        sp = pager.sp
        ls = sp.lines
        fs = cfg.fontSize
        chX = gd.chX
        chY = gd.chY
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
                sp.headers.generatePML(pg, str(pageNr), cfg)
            y += sp.headers.getNrOfLines() * 10

            if cfg.sceneContinueds and not self.isFirstLineOfScene(start):
                if doExtra:
                    s = "CONTINUED:"
                    if pager.sceneContNr != 0:
                        s += " (%d)" % (pager.sceneContNr + 1)

                    pg.add(pml.TextOp(s,
                        cfg.marginLeft + pager.sceneIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

                    pager.sceneContNr += 1

                    if cfg.pdfShowSceneNumbers:
                        self.addSceneNumbers(pg, "%d" % pager.scene,
                            cfg.getType(config.SCENE).width, y)

                y += 20

            if self.needsMore(start - 1):
                if doExtra:
                    pg.add(pml.TextOp(self.getPrevSpeaker(start) +
                        " (cont'd)",
                        cfg.marginLeft + pager.charIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

                y += 10

        for i in xrange(start, end + 1):
            line = ls[i]
            tcfg = cfg.getType(line.lt)

            if i != start:
                y += sp.getSpacingBefore(i)

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
                
            pg.add(pml.TextOp(text,
                cfg.marginLeft + tcfg.indent * chX,
                cfg.marginTop + (y / 10.0) * chY, fs, typ, line = i))

            if doExtra and (tcfg.lt == config.SCENE) and \
                   self.isFirstLineOfElem(i):
                pager.sceneContNr = 0

                if cfg.pdfShowSceneNumbers:
                    pager.scene += 1
                    self.addSceneNumbers(pg, "%d" % pager.scene, tcfg.width,
                                         y)

            if doExtra and cfg.pdfShowLineNumbers:
                pg.add(pml.TextOp("%02d" % (i - start + 1),
                    cfg.marginLeft - 3 * chX,
                    cfg.marginTop + (y / 10.0) * chY, fs))

            y += 10

        if self.needsMore(end):
            if doExtra:
                pg.add(pml.TextOp("(MORE)",
                        cfg.marginLeft + pager.charIndent * chX,
                        cfg.marginTop + (y / 10.0) * chY, fs))

            y += 10

        if cfg.sceneContinueds and not self.isLastLineOfScene(end):
            if doExtra:
                pg.add(pml.TextOp("(CONTINUED)",
                        cfg.marginLeft + 45 * chX,
                        cfg.marginTop + (y / 10.0 + 1.0) * chY, fs))

            y += 10

        if forPDF:
            if not misc.license:
                self.addDemoStamp(pg)

            if cfg.pdfShowMargins:
                lx = cfg.marginLeft
                rx = cfg.paperWidth - cfg.marginRight
                uy = cfg.marginTop
                dy = cfg.paperHeight - cfg.marginBottom

                pg.add(pml.LineOp([(lx, uy), (rx, uy), (rx, dy), (lx, dy)],
                                  0, True))

        return pg

    def addSceneNumbers(self, pg, s, width, y):
        pg.add(pml.TextOp(s, cfg.marginLeft - 6 * gd.chX,
             cfg.marginTop + (y / 10.0) * gd.chY, cfg.fontSize))
        pg.add(pml.TextOp(s, cfg.marginLeft + (width + 1) * gd.chX,
            cfg.marginTop + (y / 10.0) * gd.chY, cfg.fontSize))
        
    # add demo stamp to given pml.Page object. this modifies line join
    # parameters, so should only be called when the page is otherwise
    # ready.
    def addDemoStamp(self, pg):
        # list of lines which together draw a "DEMO" in a 45-degree angle
        # over the page. coordinates are percentages of page width/height.
        dl = [
            # D
            [ (0.056, 0.286), (0.208, 0.156), (0.23, 0.31), (0.056, 0.286) ],

            # E
            [ (0.356, 0.542), (0.238, 0.42), (0.38, 0.302), (0.502, 0.4) ],
            [ (0.328, 0.368), (0.426, 0.452) ],

            # M
            [ (0.432, 0.592), (0.574, 0.466), (0.522, 0.650),
              (0.722, 0.62), (0.604, 0.72) ],

            # O
            [ (0.67, 0.772), (0.794, 0.678), (0.896, 0.766),
              (0.772, 0.858), (0.67, 0.772) ]
            ]

        pg.add(pml.PDFOp("1 J 1 j"))

        for path in dl:
            p = []
            for point in path:
                p.append((point[0] * pg.doc.w, point[1] * pg.doc.h))

            pg.add(pml.LineOp(p, 10))

    def makeBackup(self):
        self.backup = copy.deepcopy(self.sp)

    def setFile(self, fileName):
        self.fileName = fileName
        if fileName:
            self.setDisplayName(os.path.basename(fileName))
        else:
            self.setDisplayName("untitled")

        self.setTabText()
        mainFrame.setTitle(self.fileNameDisplay)

    def setDisplayName(self, name):
        i = 1
        while 1:
            if i == 1:
                tmp = name
            else:
                tmp = name + "<%d>" % i

            matched = False
            
            for c in mainFrame.getCtrls():
                if c == self:
                    continue

                if c.fileNameDisplay == tmp:
                    matched = True

                    break

            if not matched:
                break

            i += 1
            
        self.fileNameDisplay = tmp

    def setTabText(self):
        mainFrame.setTabText(self.panel, self.fileNameDisplay)
        
    # parse a line containing a config-value in the format detailed in
    # fileformat.txt. line must have newline stripped from the end
    # already. returns a (key, value) tuple. if line doesn't match the
    # format, (None, None) is returned.
    def parseConfigLine(self, s):
        m = re.match("#([a-zA-Z0-9\-]+) (.*)", s)

        if m:
            return (m.group(1), m.group(2))
        else:
            return (None, None)
        
    def updateTypeCb(self):
        util.reverseComboSelect(mainFrame.typeCb,
                                self.sp.lines[self.line].lt)

    def reformatAll(self, makeVisible = True):
        line = 0
        while 1:
            line += self.rewrapPara(line)
            if line >= len(self.sp.lines):
                break

        if makeVisible:
            self.makeLineVisible(self.line)

    # reformat part of script. par1 is line number of paragraph to start
    # at, par2 the same for the ending one, inclusive.
    def reformatRange(self, par1, par2):
        ls = self.sp.lines

        # add special tag to last paragraph we'll reformat
        ls[par2].reformatMarker = 0
        end = false

        line = par1
        while 1:
            if hasattr(ls[line], "reformatMarker"):
                del ls[line].reformatMarker
                end = True
                
            line += self.rewrapPara(line)
            if end:
                break

    def clearAutoComp(self):
        if self.autoComp:
            self.autoComp = None
            self.Refresh(False)

    def fillAutoComp(self):
        ls = self.sp.lines

        tcfg = cfg.getType(ls[self.line].lt)
        if tcfg.doAutoComp:
            self.autoComp = self.getMatchingText(ls[self.line].text,
                                                 tcfg.lt)
            self.autoCompSel = 0

    # wraps a single line into however many lines are needed, according to
    # the type's width. doesn't modify the input line, returns a list of
    # new lines.
    def wrapLine(self, line):
        ret = []
        w = cfg.getType(line.lt).width
        
        # text remaining to be wrapped
        text = line.text
        
        while 1:
            if len(text) <= w:
                ret.append(screenplay.Line(line.lb, line.lt, text))
                break
            else:
                i = text.rfind(" ", 0, w + 1)

                if (i == w) and (text[w + 1:w + 2] == " "):
                    
                    ret.append(screenplay.Line(config.LB_SPACE2, line.lt,
                                               text[0:i]))
                    text = text[i + 2:]

                elif i >= 0:
                    ret.append(screenplay.Line(config.LB_SPACE, line.lt,
                                               text[0:i]))
                    text = text[i + 1:]
                    
                else:
                    ret.append(screenplay.Line(config.LB_NONE, line.lt,
                                               text[0:w]))
                    text = text[w:]
                    
        return ret

    # rewrap paragraph starting at given line. returns the number of lines
    # in the wrapped paragraph. if line1 is -1, rewraps paragraph
    # containing self.line. maintains cursor position correctness.
    def rewrapPara(self, line1 = -1):
        ls = self.sp.lines

        if line1 == -1:
            line1 = self.getParaFirstIndexFromLine(self.line)

        line2 = line1

        while ls[line2].lb not in (config.LB_LAST, config.LB_FORCED):
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

        tmp = screenplay.Line(ls[line2].lb, ls[line1].lt, s)
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
        
    def convertCurrentTo(self, lt):
        ls = self.sp.lines
        first, last = self.getElemIndexes()

        # if changing away from PAREN containing only "()", remove it
        if (first == last) and (ls[first].lt == config.PAREN) and\
           (ls[first].text == "()"):
            ls[first].text = ""
            self.column = 0
            
        for i in range(first, last + 1):
            ls[i].lt = lt

        # if changing empty element to PAREN, add "()"
        if (first == last) and (ls[first].lt == config.PAREN) and\
               (len(ls[first].text) == 0):
            ls[first].text = "()"
            self.column = 1

        # rewrap whole element
        line = first
        while 1:
            line += self.rewrapPara(line)
            if ls[line - 1].lb == config.LB_LAST:
                break

    # join lines 'line' and 'line + 1' and position cursor at the join
    # position.
    def joinLines(self, line):
        ls = self.sp.lines
        pos = len(ls[line].text)
        ls[line].text += ls[line + 1].text
        ls[line].lb = ls[line + 1].lb
        del ls[line + 1]

        self.line = line
        self.column = pos

    # split current line at current column position.
    def splitLine(self):
        ln = self.sp.lines[self.line]
        s = ln.text
        preStr = s[:self.column]
        postStr = s[self.column:]
        newLine = screenplay.Line(ln.lb, ln.lt, postStr)
        ln.text = preStr
        ln.lb = config.LB_FORCED
        self.sp.lines.insert(self.line + 1, newLine)
        self.line += 1
        self.column = 0

    # split element at current position. newType is type to give to the
    # new element.
    def splitElement(self, newType):
        ls = self.sp.lines
        
        if not self.autoComp:
            if self.isAtEndOfParen():
                self.column += 1
        else:
            ls[self.line].text = self.autoComp[self.autoCompSel]
            self.column = len(ls[self.line].text)

        self.splitLine()
        ls[self.line - 1].lb = config.LB_LAST

        self.convertCurrentTo(newType)
        
        self.rewrapPara()
        self.rewrapPrevPara()

    # delete character at given position and optionally position
    # cursor there.
    def deleteChar(self, line, column, posCursor = True):
        s = self.sp.lines[line].text
        self.sp.lines[line].text = s[:column] + s[column + 1:]
        
        if posCursor:
            self.column = column
            self.line = line

    # get first index of paragraph
    def getParaFirstIndexFromLine(self, line):
        ls = self.sp.lines
        
        while 1:
            tmp = line - 1
            if tmp < 0:
                break
            if ls[tmp].lb in (config.LB_LAST, config.LB_FORCED):
                break
            line -= 1

        return line

    # get last index of paragraph
    def getParaLastIndexFromLine(self, line):
        ls = self.sp.lines

        while 1:
            if ls[line].lb in (config.LB_LAST, config.LB_FORCED):
                break
            if (line + 1) >= len(ls):
                break
            line += 1

        return line

    def getElemFirstIndex(self):
        return self.getElemFirstIndexFromLine(self.line)

    def getElemFirstIndexFromLine(self, line):
        ls = self.sp.lines
        
        while 1:
            tmp = line - 1
            if tmp < 0:
                break
            if ls[tmp].lb == config.LB_LAST:
                break
            line -= 1

        return line
    
    def getElemLastIndex(self):
        return self.getElemLastIndexFromLine(self.line)
    
    def getElemLastIndexFromLine(self, line):
        ls = self.sp.lines

        while 1:
            if ls[line].lb == config.LB_LAST:
                break
            if (line + 1) >= len(ls):
                break
            line += 1

        return line

    def isFirstLineOfElem(self, line):
        return (line == 0) or (self.sp.lines[line - 1].lb == config.LB_LAST)

    def isLastLineOfElem(self, line):
        return self.sp.lines[line].lb == config.LB_LAST

    def isOnlyLineOfElem(self, line):
        # this is just "isLastLineOfElem(line) and isFirstLineOfElem(line)"
        # inlined here, since it's 130% faster this way.
        return (self.sp.lines[line].lb == config.LB_LAST) and \
               ((line == 0) or (self.sp.lines[line - 1].lb ==
                                config.LB_LAST))

    def getElemIndexes(self):
        return self.getElemIndexesFromLine(self.line)

    def getElemIndexesFromLine(self, line):
        return (self.getElemFirstIndexFromLine(line),
                self.getElemLastIndexFromLine(line))

    def getSceneIndexes(self):
        return self.getSceneIndexesFromLine(self.line)

    def isFirstLineOfScene(self, line):
        if line == 0:
            return True

        ls = self.sp.lines

        if ls[line].lt != config.SCENE:
            return False

        l = ls[line - 1]
        
        if (l.lt != config.SCENE) or (l.lb == config.LB_LAST):
            return True
        else:
            return False

    def isLastLineOfScene(self, line):
        ls = self.sp.lines

        if ls[line].lb != config.LB_LAST:
            return False
        
        if line == (len(ls) - 1):
            return True

        if ls[line + 1].lt == config.SCENE:
            return True
        else:
            return False

    def getTypeOfPrevElem(self, line):
        line = self.getElemFirstIndexFromLine(line)
        line -= 1
        if line < 0:
            return None

        return self.sp.lines[line].lt

    def getTypeOfNextElem(self, line):
        line = self.getElemLastIndexFromLine(line)
        line += 1
        if line >= len(self.sp.lines):
            return None

        return self.sp.lines[line].lt
    
    def getSceneIndexesFromLine(self, line):
        top, bottom = self.getElemIndexesFromLine(line)
        ls = self.sp.lines
        
        while 1:
            if ls[top].lt == config.SCENE:
                break
            
            tmp = top - 1
            if tmp < 0:
                break
            
            top, nothing = self.getElemIndexesFromLine(tmp)

        while 1:
            tmp = bottom + 1
            if tmp >= len(ls):
                break
            
            if ls[tmp].lt == config.SCENE:
                break
            
            nothing, bottom = self.getElemIndexesFromLine(tmp)

        return (top, bottom)

    # return scene number for the line before 'line'.
    def getSceneNumber(self, line):
        #lskdjf = util.TimerDev("getSceneNumber")
        ls = self.sp.lines
        cs = config.SCENE
        scene = 0

        for i in xrange(line):
            if (ls[i].lt == cs) and self.isFirstLineOfElem(i):
                scene += 1

        return scene
        
    # get a description of what the current screen contains. returns
    # (texts, dpages), where texts = [TextString, ...], dpages =
    # [DisplayPage, ...]. dpages is None if draft mode is in use or
    # doExtra is False. doExtra has same meaning as for generatePMLPage
    # otherwise. pageCache, if given, is used in layout mode to cache PML
    # pages. it should only be given when doExtra = False as the cached
    # pages aren't accurate down to that level.
    def getScreen(self, doExtra, pageCache = None):
        #lskdjf = util.TimerDev("getScreen")
        texts = []
        dpages = []

        width, height = self.GetClientSizeTuple()

        if gd.isDraft:
            ls = self.sp.lines
            y = cfg.offsetY
            i = self.getTopLine()
            cox = cfg.offsetX
            fyd = cfg.fontYdelta
            length = len(ls)
            
            while (y < height) and (i < length):
                y += int((self.sp.getSpacingBefore(i) / 10.0) * fyd)

                if y >= height:
                    break

                partial = (y + fyd) > height

                l = ls[i]
                tcfg = cfg.getType(l.lt)

                if tcfg.screen.isCaps:
                    text = util.upper(l.text)
                else:
                    text = l.text

                fi = cfgGui.getType(l.lt)
                texts.append(TextString(i, text,
                    cox + tcfg.indent * fi.fx, y, fi,
                    tcfg.screen.isUnderlined, partial))

                y += fyd
                i += 1
        else:
            # gap between pages (pixels)
            pageGap = 10
            pager = Pager(self.sp)

            mm2p = gd.mm2p
            fontY = cfgGui.fonts[pml.NORMAL].fy
            cox = util.clamp((width - gd.pageW) / 2, 0)
            
            y = 0
            topLine = self.getTopLine()
            pageNr = self.line2page(topLine)

            if doExtra and cfg.pdfShowSceneNumbers:
                pager.scene = self.getSceneNumber(topLine)

            # find out starting place (if something bugs, generatePMLPage
            # below could return None, but it shouldn't happen...)
            if pageCache:
                pg = pageCache.getPage(pager, pageNr)
            else:
                pg = self.generatePMLPage(pager, pageNr, False, doExtra)

            topOfPage = True
            for op in pg.ops:
                if (op.type != pml.OP_TEXT) or (op.line == -1):
                    continue

                if op.line == topLine:
                    if not topOfPage:
                        y = -int(op.y * mm2p)
                    else:
                        y = pageGap

                    break
                else:
                    topOfPage = False

            # create pages, convert them to display format, repeat until
            # script ends or we've filled the display.
            
            done = False
            while 1:
                if done or (y >= height):
                    break
                
                if not pg:
                    pageNr += 1
                    if pageNr >= len(self.pages):
                        break

                    # we'd have to go back an arbitrary number of pages to
                    # get an accurate number for this in the worst case,
                    # so disable it altogether.
                    pager.sceneContNr = 0

                    if pageCache:
                        pg = pageCache.getPage(pager, pageNr)
                    else:
                        pg = self.generatePMLPage(pager, pageNr, False,
                                                  doExtra)
                    if not pg:
                        break

                dp = DisplayPage(cox, y, cox + gd.pageW, y + gd.pageH)
                dpages.append(dp)

                pageY = y

                for op in pg.ops:
                    if op.type != pml.OP_TEXT:
                        continue

                    ypos = int(pageY + op.y * mm2p)

                    # TODO: show partial lines at top of screen, or not?
                    if ypos < 0:
                        continue
                    
                    y = max(y, ypos)
                    
                    if y >= height:
                        done = True
                        break

                    partial = (ypos + fontY) > height
                    
                    texts.append(TextString(op.line, op.text,
                        int(cox + op.x * mm2p), ypos,
                        cfgGui.fonts[op.flags & 3],
                        op.flags & pml.UNDERLINED, partial))

                y = pageY + gd.pageH + pageGap
                pg = None

            # if user has inserted new text causing the script to overflow
            # the last page, we need to make the last page extra-long on
            # the screen.
            if dpages and texts and (pageNr >= (len(self.pages) - 1)):

                lastY = texts[-1].y + fontY
                if lastY >= dpages[-1].y2:
                    dpages[-1].y2 = lastY + 10
            else:
                pass

        return (texts, dpages)

    def getLinesOnScreen(self, pageCache = None):
        lines = 0

        for t in self.getScreen(False, pageCache)[0]:
            if not t.partial:
                lines += 1

        return lines

    # return height for one line on screen
    def getLineHeight(self):
        if gd.isDraft:
            return cfg.fontYdelta
        else:
            # the + 1.0 avoids occasional non-consecutive backgrounds for
            # lines.
            return int(gd.chY * gd.mm2p + 1.0)
        
    def pos2linecol(self, pos):
        sel = None
        lineh = self.getLineHeight()
        
        for t in self.getScreen(False)[0]:
            if t.line == -1:
                continue

            sel = t
            
            if (t.y + lineh) > pos.y:
                break

        # shouldn't happen, but let's check anyway
        if sel == None:
            return (0, 0)

        line = sel.line
        l = self.sp.lines[line]

        column = util.clamp(int((pos.x - sel.x) / sel.fi.fx), 0, len(l.text))

        return (line, column)

    def line2page(self, line):
        return self.line2pageReal(line, self.pages)

    def line2pageNoAdjust(self, line):
        return self.line2pageReal(line, self.pagesNoAdjust)

    def line2pageReal(self, line, p):
        lo = 1
        hi = len(p) - 1

        while lo != hi:
            mid = (lo + hi) / 2

            if line <= p[mid]:
                hi = mid
            else:
                lo = mid + 1

        return lo

    # returns True if we're at second-to-last character of PAREN element,
    # and last character is ")"
    def isAtEndOfParen(self):
        ls = self.sp.lines
        
        return self.isLastLineOfElem(self.line) and\
           (ls[self.line].lt == config.PAREN) and\
           (ls[self.line].text[self.column:] == ")")

    # returns True if pressing TAB at current position would make a new
    # element, False if it would just change element's type.
    def tabMakesNew(self):
        l = self.sp.lines[self.line]

        if self.isAtEndOfParen():
            return True
        
        if (l.lb != config.LB_LAST) or (self.column != len(l.text)):
            return False

        if (len(l.text) == 0) and self.isOnlyLineOfElem(self.line):
            return False

        return True

    # get topLine, clamping it to the valid range in the process.
    def getTopLine(self):
        self._topLine = util.clamp(self._topLine, 0, len(self.sp.lines) - 1)

        return self._topLine

    # set topLine, clamping it to the valid range.
    def setTopLine(self, line):
        self._topLine = util.clamp(line, 0, len(self.sp.lines) - 1)

    # los = results of self.getLinesOnScreen(), or if None, in which case
    # it's called in this function.
    def isLineVisible(self, line, los = None):
        if los == None:
            los = self.getLinesOnScreen()
            
        top = self.getTopLine()
        bottom = top + los - 1

        return (line >= top) and (line <= bottom)
        
    def makeLineVisible(self, line):
        #dlkj = util.TimerDev("makeLineVisible")

        los = self.getLinesOnScreen()
        if self.isLineVisible(line, los):
            return

        # TODO: this is kinda braindead...
        
        self.setTopLine(max(0, int(line - (los * 0.66))))
        if not self.isLineVisible(line):
            self.setTopLine(line)
        
    def adjustScrollBar(self):
        height = self.GetClientSize().height

        # rough approximation of how many lines fit onto the screen.
        # accuracy is not that important for this, so we don't even care
        # about draft / layout mode differences.
        approx = int(((height / gd.mm2p) / gd.chY) / 1.3)
        
        self.panel.scrollBar.SetScrollbar(self.getTopLine(), approx,
            len(self.sp.lines) + approx - 1, approx)

    # get a list of strings (single-line text elements for now) that start
    # with 'text' (not case sensitive) and are of of type 'type'. also
    # mixes in the type's default items from config. ignores current line.
    def getMatchingText(self, text, lt):
        text = util.upper(text)
        tcfg = cfg.getType(lt)
        ls = self.sp.lines
        matches = {}
        last = None

        for i in range(len(ls)):
            if (ls[i].lt == lt) and (ls[i].lb == config.LB_LAST):
                upstr = util.upper(ls[i].text)
                
                if upstr.startswith(text) and i != self.line:
                    matches[upstr] = None
                    if i < self.line:
                        last = upstr

        for i in tcfg.autoCompList:
            upstr = util.upper(i)
            
            if upstr.startswith(text):
                matches[upstr] = None

        if last:
            del matches[last]
            
        mlist = matches.keys()
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
        
        mark = min(len(self.sp.lines) - 1, self.mark.line)

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

        ls = self.sp.lines

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
    # script. if nothing is selected, returns None.
    def getSelected(self, doDelete):
        marked = self.getMarkedLines()

        if not marked:
            return None

        ls = self.sp.lines

        cd = ClipData()
        
        for i in xrange(marked[0], marked[1] + 1):
            c1, c2 = self.getMarkedColumns(i, marked)

            ln = ls[i]
            
            cd.lines.append(screenplay.Line(ln.lb, ln.lt, ln.text[c1:c2 + 1]))

        cd.lines[-1].lb = config.LB_LAST

        if doDelete:

            # range of lines, inclusive, that we need to totally delete
            del1 = sys.maxint
            del2 = -1

            # delete selected text from the lines
            for i in xrange(marked[0], marked[1] + 1):
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

            ln = ls[marked[0]]
            
            if marked[0] != marked[1]:

                # if we're totally removing the last line selected, and
                # it's the last line of its element, mark first line
                # selected as last line of its element so that the
                # following element is not joined to that one.
                
                if self.isLastLineOfElem(marked[1]) and \
                       not(ls[marked[1]].text):
                    ln.lb = config.LB_LAST
                else:
                    ln.lb = config.LB_NONE

            else:

                # if we're totally removing a single line, and that line
                # is the last line of a multi-line element, mark the
                # preceding line as the new last line of the element.

                if not ln.text and (marked[0] != 0) and \
                       not self.isFirstLineOfElem(marked[0]) and \
                       self.isLastLineOfElem(marked[0]):
                    ls[marked[0] - 1].lb = config.LB_LAST
                        
            del ls[del1:del2 + 1]

            self.mark = None

            if len(ls) == 0:
                ls.append(screenplay.Line(config.LB_LAST, config.SCENE))

            self.line = min(marked[0], len(ls) - 1)
            self.column = min(endCol, len(ls[self.line].text))

            self.rewrapPara()
            
        return cd

    # returns true if there are no contents at all and we're not
    # attached to any file
    def isUntouched(self):
        if self.fileName or (len(self.sp.lines) > 1) or \
           (len(self.sp.lines[0].text) > 0):
            return False
        else:
            return True

    # returns True if the current contents differ from the version
    # supposedly on the disk (content at last load/save time), or if
    # this is totally new modified content and doesn't have disk
    # backing yet
    def isModified(self):
        return self.sp != self.backup

    # if doIt is True and mark is not yet set, set it at current position.
    def maybeMark(self, doIt):
        if doIt and not self.mark:
            self.mark = Mark(self.line, self.column)

    # returns true if a character, inserted at current position, would
    # need to be capitalized as a start of a sentence.
    def capitalizeNeeded(self):
        if not cfg.capitalize:
            return False
        
        ls = self.sp.lines
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

                if lb == config.LB_LAST:
                    return True

                elif lb in (config.LB_SPACE, config.LB_SPACE2):
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
        ls = self.sp.lines

        msg = None
        while 1:
            if line >= len(ls):
                break

            l = ls[line]

            isFirst = self.isFirstLineOfElem(line)
            isLast = self.isLastLineOfElem(line)
            isOnly = isFirst and isLast

            prev = self.getTypeOfPrevElem(line)
            next = self.getTypeOfNextElem(line)
            
            if len(l.text) == 0:
                msg = "Empty line."
                break

            if len(l.text.strip()) == 0:
                msg = "Empty line (contains only whitespace)."
                break

            if (l.lt == config.PAREN) and isOnly and (l.text == "()"):
                msg = "Empty parenthetical."
                break

            if l.lt == config.CHARACTER:
                if isLast and next and next not in\
                       (config.PAREN, config.DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(next).name,
                           cfg.getType(l.lt).name)
                    break

            if l.lt == config.PAREN:
                if isFirst and prev and prev not in\
                       (config.CHARACTER, config.DIALOGUE):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(l.lt).name, cfg.getType(prev).name)
                    break

            if l.lt == config.DIALOGUE:
                if isFirst and prev and prev not in\
                       (config.CHARACTER, config.PAREN):
                    msg = "Element type '%s' can not follow type '%s'." %\
                          (cfg.getType(l.lt).name, cfg.getType(prev).name)
                    break

            line += 1
            
        if not msg:
            line = -1

        return (line, msg)

    # returns true if 'line', which must be the last line on a page, needs
    # (MORE) after it and the next page needs a "SOMEBODY (cont'd)"
    def needsMore(self, line):
        ls = self.sp.lines
        if ls[line].lt in (config.DIALOGUE, config.PAREN)\
           and (line != (len(ls) - 1)) and\
           ls[line + 1].lt in (config.DIALOGUE, config.PAREN):
            return True
        else:
            return False

    # starting at line, go backwards until a line with type of CHARACTER
    # and lb of LAST is found, and return that line's text, possibly
    # upper-cased if CHARACTER's config for export says so.
    def getPrevSpeaker(self, line):
        ls = self.sp.lines

        while 1:
            if line < 0:
                return "UNKNOWN"

            ln = ls[line]
            
            if (ln.lt == config.CHARACTER) and (ln.lb == config.LB_LAST):
                s = ln.text
                
                if cfg.getType(config.CHARACTER).export.isCaps:
                    s = util.upper(s)
                
                return s

            line -= 1

    def paginate(self):
        #sfdlksjf = util.TimerDev("paginate")
        
        self.pages = [-1]
        self.pagesNoAdjust = [-1]

        ls = self.sp.lines
        length = len(ls)
        lastBreak = -1

        # fast aliases for stuff
        lbl = config.LB_LAST
        ct = cfg.types
        hdrLines = self.sp.headers.getNrOfLines()
        
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

            if line.lt == config.SCENE:
                i = self.removeDanglingElement(i, config.SCENE, lastBreak)

            elif line.lt == config.ACTION:
                if line.lb != config.LB_LAST:
                    first = self.getElemFirstIndexFromLine(i)

                    if first > (lastBreak + 1):
                        linesOnThisPage = i - first + 1
                        if linesOnThisPage < cfg.pbActionLines:
                            i = first - 1

                        i = self.removeDanglingElement(i, config.SCENE,
                                                       lastBreak)

            elif line.lt == config.CHARACTER:
                i = self.removeDanglingElement(i, config.CHARACTER, lastBreak)
                i = self.removeDanglingElement(i, config.SCENE, lastBreak)

            elif line.lt in (config.DIALOGUE, config.PAREN):
                
                if line.lb != config.LB_LAST or\
                       self.getTypeOfNextElem(i) in\
                       (config.DIALOGUE, config.PAREN):

                    cutDialogue = False
                    cutParen = False
                    while 1:
                        oldI = i
                        line = ls[i]
                        
                        if line.lt == config.PAREN:
                            i = self.removeDanglingElement(i, config.PAREN,
                              lastBreak)
                            cutParen = True

                        elif line.lt == config.DIALOGUE:
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

                        elif line.lt == config.CHARACTER:
                            i = self.removeDanglingElement(i,
                              config.CHARACTER, lastBreak)
                            i = self.removeDanglingElement(i,
                              config.SCENE, lastBreak)

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
        ls = self.sp.lines
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
            if (line != startLine) and (ln.lb == config.LB_LAST):
                break
            
            line -= 1

        return line
        
    def updateScreen(self, redraw = True, setCommon = True):
        self.adjustScrollBar()
        
        if setCommon:
            self.updateCommon()
            
        if redraw:
            self.Refresh(False)

    # update GUI elements shared by all scripts, like statusbar etc
    def updateCommon(self):
        self.updateTypeCb()

        sb = mainFrame.statusBar
        
        sb.SetStatusText("Page: %d / %d" % (self.line2page(self.line),
            self.line2page(len(self.sp.lines) - 1)), 2)

        cur = cfg.getType(self.sp.lines[self.line].lt)
        
        if self.tabMakesNew():
            s = "%s" % cfg.getType(cur.newTypeTab).name
        else:
            s = "%s [change]" % cfg.getType(cur.nextTypeTab).name
            
        sb.SetStatusText("Tab: %s" % s, 0)
        sb.SetStatusText("Enter: %s" % cfg.getType(cur.newTypeEnter).name,
                         1)

    def applyCfg(self, newCfg, writeCfg = True):
        global cfg
        
        oldCfg = cfg

        cfg = copy.deepcopy(newCfg)
        config.currentCfg = cfg

        # if user has ventured from the old default directory, keep it as
        # the current one, otherwise set the new default as current.
        if misc.scriptDir == oldCfg.scriptDir:
            misc.scriptDir = cfg.scriptDir
        
        cfg.recalc()
        refreshGuiConfig()
        gd.refresh()
        
        for c in mainFrame.getCtrls():
            c.reformatAll()
            c.paginate()
            c.adjustScrollBar()

        self.updateScreen()

        if writeCfg:
            util.writeToFile(gd.confFilename, cfg.save(), mainFrame)

    def applyHeaders(self, newHeaders):
        self.sp.headers = newHeaders
        self.OnPaginate()

    def checkEval(self):
        if not misc.license:
            wxMessageBox("This feature is not supported in the\n"
                         "evaluation version.", "Notice",
                         wxOK, mainFrame)
            return True

        return False

    # return an exportable, paginated Screenplay object, or None if for
    # some reason that's not possible / wanted. 'action' is the name of
    # the action, e.g. "export" or "print", that'll be done to the script,
    # and is used in dialogue with the user if needed.
    def getExportable(self, action):
        if cfg.checkOnExport:
            line, msg = self.findError(0)

            if line != -1:
                if wxMessageBox("The script seems to contain errors.\n"
                    "Are you sure you want to %s it?" % action, "Confirm",
                     wxYES_NO | wxNO_DEFAULT, mainFrame) == wxNO:

                    return None

        self.paginate()

        sp = self.sp
        if not misc.license:
            sp = copy.deepcopy(self.sp)
            sp.replace()

        return sp

    def OnEraseBackground(self, event):
        pass
        
    def OnSize(self, event):
        size = self.GetClientSize()
        self.screenBuf = wxEmptyBitmap(size.width, size.height)
        self.makeLineVisible(self.line)
    
    def OnLeftDown(self, event, mark = False):
        self.autoComp = None
        self.line, self.column = self.pos2linecol(event.GetPosition())

        if mark and not self.mark:
            self.mark = Mark(self.line, self.column)
            
        self.updateScreen()

    def OnRightDown(self, event):
        self.mark = None
        self.updateScreen()
        
    def OnMotion(self, event):
        if event.LeftIsDown():
            self.OnLeftDown(event, mark = True)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            delta = -cfg.mouseWheelLines
        else:
            delta = cfg.mouseWheelLines
            
        self.setTopLine(self.getTopLine() + delta)
        self.updateScreen()
        
    def OnTypeCombo(self, event):
        lt = mainFrame.typeCb.GetClientData(mainFrame.typeCb.GetSelection())
        self.convertCurrentTo(lt)
        self.SetFocus()
        self.updateScreen()

    def OnScroll(self, event):
        pos = self.panel.scrollBar.GetThumbPosition()
        self.setTopLine(pos)
        self.autoComp = None
        self.updateScreen()

    def OnPaginate(self):
        self.paginate()
        self.makeLineVisible(self.line)
        self.updateScreen()

    def OnTitles(self):
        dlg = titlesdlg.TitlesDlg(mainFrame, copy.deepcopy(self.sp.titles),
                                  cfg)

        if dlg.ShowModal() == wxID_OK:
            self.sp.titles = dlg.titles

        dlg.Destroy()

    def OnHeaders(self):
        dlg = headersdlg.HeadersDlg(mainFrame,
            copy.deepcopy(self.sp.headers), cfg, self.applyHeaders)

        if dlg.ShowModal() == wxID_OK:
            self.applyHeaders(dlg.headers)

        dlg.Destroy()
        
    def OnDialogueChart(self):
        self.paginate()
        dialoguechart.genDialogueChart(mainFrame, self, cfg)

    def OnCharacterReport(self):
        self.paginate()
        report.genCharacterReport(mainFrame, self, cfg)

    def OnCompareScripts(self):
        if mainFrame.notebook.GetPageCount() < 2:
            wxMessageBox("You need two at least two scripts open to"
                         " compare them.", "Error", wxOK, mainFrame)

            return

        items = []
        for c in mainFrame.getCtrls():
            items.append(c.fileNameDisplay)

        dlg = misc.ScriptChooserDlg(mainFrame, items)

        sel1 = -1
        sel2 = -1
        if dlg.ShowModal() == wxID_OK:
            sel1 = dlg.sel1
            sel2 = dlg.sel2
        
        dlg.Destroy()

        if sel1 == -1:
            return

        if sel1 == sel2:
            wxMessageBox("You can't compare a script to itself.", "Error",
                         wxOK, mainFrame)

            return
        
        c1 = mainFrame.notebook.GetPage(sel1).ctrl
        c2 = mainFrame.notebook.GetPage(sel2).ctrl
        
        sp1 = c1.getExportable("compare")
        sp2 = c2.getExportable("compare")

        if not sp1 or not sp2:
            return

        s1 = c1.generateText(sp1, False).split("\n")
        s2 = c2.generateText(sp2, False).split("\n")

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
            s = "The scripts are identical."
            if not misc.license:
                s += "\n\nHowever, this is the evaluation version of the\n"\
                     "program, which replaces some words in the\n"\
                     "scripts before doing the comparison, which\n"\
                     "might have affected the result."
                
            wxMessageBox(s, "Results", wxOK, mainFrame)

            return
        
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
        
        fs = cfg.fontSize
        chY = util.getTextHeight(fs)
        
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
                pg.add(pml.RectOp(doc.w / 2.0 - w /2.0, cfg.marginTop +
                    y * chY + chY / 4, w, chY / 2, -1, True))
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
                        doc.w - cfg.marginLeft - 5.0, chY, -1, True))
                    pg.add(pml.PDFOp("0.0 g"))

                textOps.append(pml.TextOp(s[1:], cfg.marginLeft,
                    cfg.marginTop + y * chY, fs))

            y += 1

        pg.ops.extend(textOps)
        doc.add(pg)

        if not misc.license:
            for pg in doc.pages:
                self.addDemoStamp(pg)

        tmp = pdf.generate(doc)
        util.showTempPDF(tmp, cfg, mainFrame)

    def canBeClosed(self):
        if self.isModified():
            if wxMessageBox("The script has been modified. Are you sure\n"
                            "you want to discard the changes?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, mainFrame) == wxNO:
                return False

        return True

    def OnRevert(self):
        if self.fileName:
            if not self.canBeClosed():
                return
        
            self.loadFile(self.fileName)
            self.updateScreen()

    def OnCut(self, doUpdate = True, doDelete = True, copyToClip = True):
        marked = self.getMarkedLines()

        if not marked:
            return None

        if not copyToClip and cfg.confirmDeletes and (
            (marked[1] - marked[0] + 1) >= cfg.confirmDeletes):
            if wxMessageBox("Are you sure you want to delete\n"
                            "the selected text?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxNO:
                return

        cd = self.getSelected(doDelete)
        
        if copyToClip:
            mainFrame.clipboard = cd

        if doUpdate:
            self.makeLineVisible(self.line)
            self.updateScreen()

    def OnCopy(self):
        self.OnCut(doDelete = False)

    def OnCopyCb(self):
        cd = self.getSelected(False)

        if not cd:
            return

        tmpSp = Screenplay()
        tmpSp.lines = cd.lines

        if not misc.license:
            tmpSp.replace()

        s = util.String()
        for ln in tmpSp.lines:
            s += ln.text + config.lb2str(ln.lb)

        s = str(s).replace("\n", os.linesep)
        
        if wxTheClipboard.Open():
            wxTheClipboard.UsePrimarySelection(True)
            
            wxTheClipboard.Clear()
            wxTheClipboard.AddData(wxTextDataObject(s))
            wxTheClipboard.Flush()
                
            wxTheClipboard.Close()

    def OnPaste(self, clines = None):
        if not clines:
            cd = mainFrame.clipboard

            if not cd:
                return

            clines = cd.lines
        
        # shouldn't happen, but...
        if len(clines) == 0:
            return

        inLines = []
        i = 0

        # wrap all paragraphs into single lines
        while 1:
            if i >= len(clines):
                break
            
            ln = clines[i]
            
            newLine = screenplay.Line(config.LB_LAST, ln.lt)

            while 1:
                ln = clines[i]
                i += 1
                
                newLine.text += ln.text
                
                if ln.lb in (config.LB_LAST, config.LB_FORCED):
                    break
            
                newLine.text += config.lb2str(ln.lb)
                
            newLine.lb = ln.lb
            inLines.append(newLine)

        # shouldn't happen, but...
        if len(inLines) == 0:
            return
        
        ls = self.sp.lines
        
        # where we need to start wrapping
        wrap1 = self.getParaFirstIndexFromLine(self.line)
        
        ln = ls[self.line]
        
        wasEmpty = len(ln.text) == 0
        atEnd = self.column == len(ln.text)
        
        ln.text = ln.text[:self.column] + inLines[0].text + \
                  ln.text[self.column:]
        self.column += len(inLines[0].text)

        if wasEmpty:
            ln.lt = inLines[0].lt
        
        if len(inLines) != 1:

            if not atEnd:
                self.splitLine()
                ls[self.line - 1].lb = inLines[0].lb
                ls[self.line:self.line] = inLines[1:]
                self.line += len(inLines) - 2
            else:
                ls[self.line + 1:self.line + 1] = inLines[1:]
                self.line += len(inLines) - 1

            self.column = len(ls[self.line].text)

        self.reformatRange(wrap1, self.getParaFirstIndexFromLine(self.line))

        self.mark = None
        self.autoComp = None
        
        self.makeLineVisible(self.line)
        self.updateScreen()
    
    def OnPasteCb(self):
        s = ""
        
        if wxTheClipboard.Open():
            wxTheClipboard.UsePrimarySelection(True)
            
            df = wxDataFormat(wxDF_TEXT)
            
            if wxTheClipboard.IsSupported(df):
                data = wxTextDataObject()
                wxTheClipboard.GetData(data)
                s = data.GetText()
                
            wxTheClipboard.Close()

        s = util.fixNL(s)
        
        if len(s) == 0:
            return

        inLines = s.split("\n")

        # shouldn't be possible, but...
        if len(inLines) == 0:
            return

        lines = []

        for s in inLines:
            s = util.toInputStr(s)

            if len(s) != 0:
                lines.append(screenplay.Line(config.LB_LAST, config.ACTION,
                                             s))

        self.OnPaste(lines)
                
    def OnSelectScene(self):
        self.clearAutoComp()

        l1, l2 = self.getSceneIndexes()
        
        self.mark = Mark(l1, 0)

        self.line = l2
        self.column = len(self.sp.lines[l2].text)

        self.makeLineVisible(self.line)
        self.updateScreen()

    def OnFindError(self):
        self.clearAutoComp()

        line, msg = self.findError(self.line)

        if line != -1:
            self.line = line
            self.column = 0
            
            self.makeLineVisible(self.line)
            self.updateScreen()
            
        else:
            msg = "No errors found."
            
        wxMessageBox(msg, "Results", wxOK, mainFrame)
        
    def OnFind(self):
        self.clearAutoComp()
        
        dlg = finddlg.FindDlg(mainFrame, self, cfg)
        dlg.ShowModal()
        dlg.saveState()
        
        if dlg.didReplaces:
            self.reformatAll()
        
        dlg.Destroy()

        self.searchLine = -1
        self.searchColStart = -1
        self.searchWidth = -1

        self.updateScreen()

    def OnDeleteElements(self):
        self.clearAutoComp()

        types = []
        for t in cfg.types.values():
            types.append(misc.CheckBoxItem(t.name, False, t.lt))

        dlg = misc.CheckBoxDlg(mainFrame, "Delete elements", types,
                               "Element types to delete:", True)

        ok = False
        if dlg.ShowModal() == wxID_OK:
            ok = True

            tdict = misc.CheckBoxItem.getClientData(types)
            
        dlg.Destroy()

        if not ok or (len(tdict) == 0):
            return

        if wxMessageBox("Are you sure you want to delete\n"
                        "the selected elements?", "Confirm",
                        wxYES_NO | wxNO_DEFAULT, self) == wxNO:
            return

        lsNew = []
        lsOld = self.sp.lines

        for l in lsOld:
            if l.lt not in tdict:
                lsNew.append(l)

        if len(lsNew) == 0:
            lsNew.append(screenplay.Line(config.LB_LAST, config.SCENE))

        self.sp.lines = lsNew
        
        self.line = 0
        self.column = 0
        self.setTopLine(0)
        self.mark = None
        
        self.paginate()
        self.updateScreen()

    def OnSave(self):
        if self.checkEval():
            return
        
        if self.fileName:
            self.saveFile(self.fileName)
        else:
            self.OnSaveAs()

    def OnSaveAs(self):
        if self.checkEval():
            return
        
        dlg = wxFileDialog(mainFrame, "Filename to save as", misc.scriptDir,
            wildcard = "Blyte files (*.blyte)|*.blyte|All files|*",
            style = wxSAVE | wxOVERWRITE_PROMPT)
        if dlg.ShowModal() == wxID_OK:
            misc.scriptDir = dlg.GetDirectory()
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnExport(self):
        sp = self.getExportable("export")
        if not sp:
            return
        
        dlg = wxFileDialog(mainFrame, "Filename to export as",
            misc.scriptDir, wildcard = "PDF|*.pdf|Formatted text|*.txt",
            style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            misc.scriptDir = dlg.GetDirectory()
            
            if dlg.GetFilterIndex() == 0:
                data = self.generatePDF(sp)
            else:
                data = self.getExportText(sp)

            if data:
                util.writeToFile(dlg.GetPath(), data, mainFrame)

        dlg.Destroy()

    def OnPrint(self):
        sp = self.getExportable("print")
        if not sp:
            return
        
        s = self.generatePDF(sp)
        util.showTempPDF(s, cfg, mainFrame)

    def OnCfg(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(cfg), self.applyCfg)
        if dlg.ShowModal() == wxID_OK:
            self.applyCfg(dlg.cfg)

        dlg.Destroy()
        
    def OnKeyChar(self, ev):
        #ldkjfjv = util.TimerDev("OnKeyChar")
        
        kc = ev.GetKeyCode()
        
        #print "kc: %d, ctrl/alt/shift: %d, %d, %d" %\
        #      (kc, ev.ControlDown(), ev.AltDown(), ev.ShiftDown())
        
        ls = self.sp.lines
        tcfg = cfg.getType(ls[self.line].lt)

        # TODO: call ensureCorrectLine()?

        # what to do about auto-completion
        AC_DEL = 0
        AC_REDO = 1
        AC_KEEP = 2

        doAutoComp = AC_DEL
        doUpdate = True

        if isinstance(ev, util.MyKeyEvent) and (ev.noUpdate):
            doUpdate = False
        
        # 10 == CTRL+Enter under wxMSW
        if (kc == WXK_RETURN) or (kc == 10):
            if ev.ShiftDown() or ev.ControlDown():
                self.splitLine()
                
                self.rewrapPara()
                self.rewrapPrevPara()
            else:
                self.splitElement(tcfg.newTypeEnter)

        elif kc == WXK_BACK:
            if self.column == 0:
                if (self.line != 0):
                    ln = ls[self.line - 1]

                    if ln.lb == config.LB_SPACE2:
                        ln.lb = config.LB_SPACE
                    else:
                        if ln.lb == config.LB_NONE:
                            self.deleteChar(self.line - 1, len(ln.text) - 1,
                                            False)
                        
                        self.joinLines(self.line - 1)
            else:
                self.deleteChar(self.line, self.column - 1)
                doAutoComp = AC_REDO

            self.rewrapPara()
            
        elif kc == WXK_DELETE:
            if not self.mark:
                if self.column == len(ls[self.line].text):
                    if self.line != (len(ls) - 1):
                        ln = ls[self.line]

                        if ln.lb == config.LB_SPACE2:
                            ln.lb = config.LB_SPACE
                        else:
                            if ln.lb == config.LB_NONE:
                                self.deleteChar(self.line + 1, 0, False)

                            self.joinLines(self.line)
                else:
                    self.deleteChar(self.line, self.column)
                    doAutoComp = AC_REDO

                self.rewrapPara()
            else:
                self.OnCut(doUpdate = False, copyToClip = False)

        elif ev.ControlDown():
            if kc == WXK_SPACE:
                self.mark = Mark(self.line, self.column)
                
            elif kc == WXK_HOME:
                self.maybeMark(ev.ShiftDown())
                
                self.line = 0
                self.setTopLine(0)
                self.column = 0
                
            elif kc == WXK_END:
                self.maybeMark(ev.ShiftDown())
                
                self.line = len(ls) - 1
                self.column = len(ls[self.line].text)

            elif kc == WXK_UP:
                self.maybeMark(ev.ShiftDown())
                
                tmpUp, nothing = self.getSceneIndexes()

                if self.line != tmpUp:
                    self.line = tmpUp
                else:
                    tmpUp -= 1
                    if tmpUp >= 0:
                        self.line, nothing = self.getSceneIndexesFromLine(
                            tmpUp)
                    
                self.column = 0

            elif kc == WXK_DOWN:
                self.maybeMark(ev.ShiftDown())
                
                nothing, tmpBottom = self.getSceneIndexes()
                self.line = min(len(ls) - 1, tmpBottom + 1)
                self.column = 0
                
            else:
                ev.Skip()
                return
                
        elif kc == WXK_LEFT:
            self.maybeMark(ev.ShiftDown())
            
            self.column = max(self.column - 1, 0)
            
        elif kc == WXK_RIGHT:
            self.maybeMark(ev.ShiftDown())
            
            self.column = min(self.column + 1, len(ls[self.line].text))
            
        elif kc == WXK_DOWN:
            if not self.autoComp:
                self.maybeMark(ev.ShiftDown())
                
                if self.line < (len(ls) - 1):
                    self.line += 1

            else:
                self.autoCompSel = (self.autoCompSel + 1) % len(self.autoComp)
                doAutoComp = AC_KEEP
                        
        elif kc == WXK_UP:
            if not self.autoComp:
                self.maybeMark(ev.ShiftDown())
                
                if self.line > 0:
                    self.line -= 1
                    
            else:
                self.autoCompSel = self.autoCompSel - 1
                if self.autoCompSel < 0:
                    self.autoCompSel = len(self.autoComp) - 1
                doAutoComp = AC_KEEP
                    
        elif kc == WXK_HOME:
            self.maybeMark(ev.ShiftDown())
            
            self.column = 0
            
        elif kc == WXK_END:
            if self.autoComp:
                ls[self.line].text = self.autoComp[self.autoCompSel]
            else:
                self.maybeMark(ev.ShiftDown())
                
            self.column = len(ls[self.line].text)
                
        elif kc == WXK_PRIOR:
            if not self.autoComp:
                self.maybeMark(ev.ShiftDown())

                pc = PageCache(self)
                los = self.getLinesOnScreen(pc)

                if not self.isLineVisible(self.line, los):
                    # if cursor isn't visible, it's hard to know what
                    # "page up" is supposed to mean, so just go up a few
                    # lines.
                    self.line = util.clamp(self.line - 5, 0, len(ls) - 1)
                else:
                    tl = self.getTopLine()
                    if tl == (len(ls) - 1):
                        self.setTopLine(tl - 5)
                    else:
                        self.line = tl

                        while 1:
                            tl = self.getTopLine()
                            if tl == 0:
                                break

                            lastLine = tl + self.getLinesOnScreen(pc) - 1

                            if self.line > lastLine:
                                # line scrolled off screen, back up one line
                                self.setTopLine(tl + 1)
                                break
                            elif self.line == lastLine:
                                break

                            self.setTopLine(tl - 1)
            else:
                if len(self.autoComp) > self.maxAutoCompItems:
                    self.autoCompSel = self.autoCompSel - self.maxAutoCompItems
                    if self.autoCompSel < 0:
                        self.autoCompSel = len(self.autoComp) - 1
                
                doAutoComp = AC_KEEP
            
        elif kc == WXK_NEXT:
            if not self.autoComp:
                self.maybeMark(ev.ShiftDown())
                
                los = self.getLinesOnScreen()

                if self.isLineVisible(self.line, los):
                    self.line = util.clamp(self.getTopLine() + los - 1,
                        0, len(ls) - 1)
                    self.setTopLine(self.line - 1)
                else:
                    # if cursor isn't visible, it's hard to know what
                    # "page down" is supposed to mean, so just go down a
                    # few lines.
                    self.line = util.clamp(self.line + 5, 0, len(ls) - 1)
                    
            else:
                if len(self.autoComp) > self.maxAutoCompItems:
                    self.autoCompSel = (self.autoCompSel +
                        self.maxAutoCompItems) % len(self.autoComp)
                
                doAutoComp = AC_KEEP
            
        elif ev.AltDown() and (kc < 256):
            ch = chr(kc).upper()
            lt = None
            if ch == "S":
                lt = config.SCENE
            elif ch == "A":
                lt = config.ACTION
            elif ch == "C":
                lt = config.CHARACTER
            elif ch == "D":
                lt = config.DIALOGUE
            elif ch == "P":
                lt = config.PAREN
            elif ch == "T":
                lt = config.TRANSITION
            elif ch == "N":
                lt = config.NOTE

            if lt != None:
                self.convertCurrentTo(lt)
            else:
                ev.Skip()
                return
            
        elif kc == WXK_TAB:
            if self.tabMakesNew():
                self.splitElement(tcfg.newTypeTab)
            else:
                if not ev.ShiftDown():
                    lt = tcfg.nextTypeTab
                else:
                    lt = tcfg.prevTypeTab

                self.convertCurrentTo(lt)

        elif kc == WXK_ESCAPE:
            self.mark = None

        # debug stuff
        # FIXME: enable these when --test is on
#         elif (kc < 256) and (chr(kc) == "å"):
#             self.loadFile("default.blyte")
#         elif (kc < 256) and (chr(kc) == "¤"):
#             pass

        elif util.isValidInputChar(kc):
            char = chr(kc)

            if self.capitalizeNeeded():
                char = util.upper(char)
            
            s = ls[self.line].text
            s = s[:self.column] + char + s[self.column:]
            ls[self.line].text = s
            self.column += 1
                
            tmp = s.upper()
            if (tmp == "EXT.") or (tmp == "INT."):
                if self.isOnlyLineOfElem(self.line):
                    ls[self.line].lt = config.SCENE
            elif (tmp == "(") and\
                 ls[self.line].lt in (config.DIALOGUE, config.CHARACTER) and\
                 self.isOnlyLineOfElem(self.line):
                ls[self.line].lt = config.PAREN
                ls[self.line].text = "()"

            self.rewrapPara()

            doAutoComp = AC_REDO

        else:
            ev.Skip()
            return

        # TODO: call ensureCorrectLine()?
        self.column = min(self.column, len(ls[self.line].text))

        if doAutoComp == AC_DEL:
            self.autoComp = None
        elif doAutoComp == AC_REDO:
            self.fillAutoComp()

        if doUpdate:
            if cfg.paginateInterval > 0:
                now = time.time()
                if (now - self.lastPaginated) >= cfg.paginateInterval:
                    self.paginate()
                
            self.makeLineVisible(self.line)
            self.updateScreen()

    def OnPaint(self, event):
        #ldkjfldsj = util.TimerDev("paint")
        
        ls = self.sp.lines
        dc = wxBufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        marked = self.getMarkedLines()
        lineh = self.getLineHeight()
        posX = -1
        cursorY = -1

        # auto-comp FontInfo
        acFi = None

        # key = font, value = ([text, ...], [(x, y), ...], [wxColour, ...])
        texts = {}

        # lists of underline-lines to draw, one for normal text and one
        # for header texts. list objects are (x, y, width) tuples.
        ulines = []
        ulinesHdr = []
        
        strings, dpages = self.getScreen(True)

        if not dpages:
            dc.SetBrush(cfgGui.textBgBrush)
            dc.SetPen(cfgGui.textBgPen)

            dc.DrawRectangle(0, 0, size.width, size.height)

        else:
            dc.SetBrush(cfgGui.workspaceBrush)
            dc.SetPen(cfgGui.workspacePen)

            dc.DrawRectangle(0, 0, size.width, size.height)
            
            dc.SetBrush(cfgGui.textBgBrush)
            dc.SetPen(cfgGui.pageBorderPen)
            for dp in dpages:
                dc.DrawRectangle(dp.x1, dp.y1, dp.x2 - dp.x1 + 1,
                                 dp.y2 - dp.y1 + 1)

            dc.SetPen(cfgGui.pageShadowPen)
            for dp in dpages:
                # + 2 because DrawLine doesn't draw to end point but stops
                # one pixel short...
                dc.DrawLine(dp.x1 + 1, dp.y2 + 1, dp.x2 + 1, dp.y2 + 1)
                dc.DrawLine(dp.x2 + 1, dp.y1 + 1, dp.x2 + 1, dp.y2 + 2)

        for t in strings:
            i = t.line
            y = t.y
            fi = t.fi
            fx = fi.fx

            if i != -1:
                l = ls[i]
                tcfg = cfg.getType(l.lt)

                if l.lt == config.NOTE:
                    dc.SetPen(cfgGui.notePen)
                    dc.SetBrush(cfgGui.noteBrush)

                    nx = t.x - 5
                    nw = tcfg.width * fx + 10

                    dc.DrawRectangle(nx, y, nw, lineh)

                    dc.SetPen(cfgGui.textPen)
                    util.drawLine(dc, nx - 1, y, 0, lineh)
                    util.drawLine(dc, nx + nw, y, 0, lineh)

                    if self.isFirstLineOfElem(i):
                        util.drawLine(dc, nx - 1, y - 1, nw + 2, 0)

                    if self.isLastLineOfElem(i):
                        util.drawLine(dc, nx - 1, y + lineh,
                                      nw + 2, 0)

                if marked and self.isLineMarked(i, marked):
                    c1, c2 = self.getMarkedColumns(i, marked)

                    dc.SetPen(cfgGui.selectedPen)
                    dc.SetBrush(cfgGui.selectedBrush)

                    dc.DrawRectangle(t.x + c1 * fx, y, (c2 - c1 + 1) * fx,
                        lineh)

                if mainFrame.showFormatting:
                    dc.SetPen(cfgGui.bluePen)
                    util.drawLine(dc, t.x, y, 0, lineh)
                    util.drawLine(dc, t.x + tcfg.width * fx, y, 0,
                                  lineh)

                    dc.SetTextForeground(cfgGui.redColor)
                    dc.SetFont(cfgGui.fonts[pml.NORMAL].font)
                    dc.DrawText(config.lb2text(l.lb), t.x - 10, y)

                if not dpages:
                    if cfg.pbi == config.PBI_REAL_AND_UNADJ:
                        if self.line2pageNoAdjust(i) != \
                               self.line2pageNoAdjust(i + 1):
                            dc.SetPen(cfgGui.pagebreakNoAdjustPen)
                            util.drawLine(dc, 0, y + lineh - 1,
                                size.width, 0)

                    if cfg.pbi in (config.PBI_REAL,
                                   config.PBI_REAL_AND_UNADJ):
                        thisPage = self.line2page(i)

                        if thisPage != self.line2page(i + 1):
                            dc.SetPen(cfgGui.pagebreakPen)
                            util.drawLine(dc, 0, y + lineh - 1,
                                size.width, 0)

                if i == self.line:
                    posX = t.x
                    cursorY = y
                    acFi = fi
                    dc.SetPen(cfgGui.cursorPen)
                    dc.SetBrush(cfgGui.cursorBrush)
                    dc.DrawRectangle(t.x + self.column * fx, y, fx, fi.fy)

                if i == self.searchLine:
                    dc.SetPen(cfgGui.searchPen)
                    dc.SetBrush(cfgGui.searchBrush)
                    dc.DrawRectangle(t.x + self.searchColumn * fx, y,
                                     self.searchWidth * fx, fi.fy)

            if len(t.text) != 0:
                tl = texts.get(fi.font)
                if tl == None:
                    tl = ([], [], [])
                    texts[fi.font] = tl
                    
                tl[0].append(t.text)
                tl[1].append((t.x, y))
                if t.line != -1:
                    tl[2].append(cfgGui.textColor)
                else:
                    tl[2].append(cfgGui.textHdrColor)
                
                if t.isUnderlined:
                    if t.line != -1:
                        uli = ulines
                    else:
                        uli = ulinesHdr

                    uli.append((t.x, y + lineh - 1,
                               len(t.text) * fx - 1))

        if ulines:
            dc.SetPen(cfgGui.textPen)
            
            for ul in ulines:
                util.drawLine(dc, ul[0], ul[1], ul[2], 0)

        if ulinesHdr:
            dc.SetPen(cfgGui.textHdrPen)
            
            for ul in ulinesHdr:
                util.drawLine(dc, ul[0], ul[1], ul[2], 0)

        dc.SetTextForeground(cfgGui.textColor)

        for tl in texts.iteritems():
            dc.SetFont(tl[0])

            dc.DrawTextList(tl[1][0], tl[1][1], tl[1][2])
        
        if self.autoComp and (cursorY > 0):
            self.drawAutoComp(dc, posX, cursorY, acFi)

    def drawAutoComp(self, dc, posX, cursorY, fi):
        offset = 5

        # scroll bar width
        sbw = 10
        
        selBleed = 2

        size = self.GetClientSize()
        
        dc.SetFont(fi.font)

        show = min(self.maxAutoCompItems, len(self.autoComp))
        doSbw = show < len(self.autoComp)
        
        startPos = (self.autoCompSel / show) * show
        endPos = min(startPos + show, len(self.autoComp))
        if endPos == len(self.autoComp):
            startPos = max(0, endPos - show)

        w = 0
        for i in range(len(self.autoComp)):
            tw, tmp = dc.GetTextExtent(self.autoComp[i])
            w = max(w, tw)

        w += offset * 2
        h = show * fi.fy + offset * 2

        itemW = w - offset * 2 + selBleed * 2
        if doSbw:
            w += sbw + offset * 2
            sbh = h - offset * 2 + selBleed * 2

        posY = cursorY + fi.fy + 5

        # if the box doesn't fit on the screen in the normal position, put
        # it above the current line. if it doesn't fit there either,
        # that's just too bad, we don't support window sizes that small.
        if (posY + h) > size.height:
            posY = cursorY - h - 1
        
        dc.SetPen(cfgGui.autoCompPen)
        dc.SetBrush(cfgGui.autoCompBrush)
        dc.DrawRectangle(posX, posY, w, h)

        dc.SetTextForeground(cfgGui.autoCompFgColor)

        for i in range(startPos, endPos):
            if i == self.autoCompSel:
                dc.SetPen(cfgGui.autoCompRevPen)
                dc.SetBrush(cfgGui.autoCompRevBrush)
                dc.SetTextForeground(cfgGui.autoCompBgColor)
                dc.DrawRectangle(posX + offset - selBleed,
                    posY + offset + (i - startPos) * fi.fy - selBleed,
                    itemW,
                    fi.fy + selBleed * 2)
                dc.SetTextForeground(cfgGui.autoCompBgColor)
                dc.SetPen(cfgGui.autoCompPen)
                dc.SetBrush(cfgGui.autoCompBrush)
                
            dc.DrawText(self.autoComp[i], posX + offset, posY + offset +
                        (i - startPos) * fi.fy)

            if i == self.autoCompSel:
                dc.SetTextForeground(cfgGui.autoCompFgColor)

        if doSbw:
            dc.SetPen(cfgGui.autoCompPen)
            dc.SetBrush(cfgGui.autoCompRevBrush)
            util.drawLine(dc, posX + w - offset * 2 - sbw,
                posY, 0, h)
            dc.DrawRectangle(posX + w - offset - sbw,
                posY + offset - selBleed + int((float(startPos) /
                     len(self.autoComp)) * sbh),
                sbw,
                int((float(show) / len(self.autoComp)) * sbh))

class MyFrame(wxFrame):

    def __init__(self, parent, id, title):
        wxFrame.__init__(self, parent, id, title, name = "Blyte")

        if misc.isUnix:
            # automatically reaps zombies
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)
        
        self.clipboard = None
        self.showFormatting = False

        self.SetSizeHints(gd.cvars.getMin("width"),
                          gd.cvars.getMin("height"))

        self.MoveXY(gd.posX, gd.posY)
        self.SetSize(wxSize(gd.width, gd.height))
        
        util.removeTempFiles(misc.tmpPrefix)

        self.mySetIcons()
        self.allocIds()
        
        fileMenu = wxMenu()
        fileMenu.Append(ID_FILE_NEW, "&New")
        fileMenu.Append(ID_FILE_OPEN, "&Open...\tCTRL-O")
        fileMenu.Append(ID_FILE_SAVE, "&Save\tCTRL-S")
        fileMenu.Append(ID_FILE_SAVE_AS, "Save &As...")
        fileMenu.Append(ID_FILE_CLOSE, "&Close")
        fileMenu.Append(ID_FILE_REVERT, "&Revert")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_IMPORT, "&Import...")
        fileMenu.Append(ID_FILE_EXPORT, "&Export...")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_PRINT, "&Print\tCTRL-P")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_SETTINGS, "Se&ttings...")
        fileMenu.Append(ID_FILE_CFG_LOAD, "Load...")
        fileMenu.Append(ID_FILE_CFG_SAVE_AS, "Save as...")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_EXIT, "E&xit\tCTRL-Q")

        editMenu = wxMenu()
        editMenu.Append(ID_EDIT_CUT, "Cu&t\tCTRL-X")
        editMenu.Append(ID_EDIT_COPY, "&Copy\tCTRL-C")
        editMenu.Append(ID_EDIT_PASTE, "&Paste\tCTRL-V")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_COPY_TO_CB, "C&opy to clipboard")
        editMenu.Append(ID_EDIT_PASTE_FROM_CB, "P&aste from clipboard")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_SELECT_SCENE, "&Select scene\tCTRL-A")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_FIND, "&Find && Replace...\tCTRL-F")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_DELETE_ELEMENTS, "&Remove elements...")

        viewMenu = wxMenu()
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_DRAFT, "&Draft")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_LAYOUT, "&Layout")

        if gd.isDraft:
            viewMenu.Check(ID_VIEW_STYLE_DRAFT, True)
        else:
            viewMenu.Check(ID_VIEW_STYLE_LAYOUT, True)

        viewMenu.AppendSeparator()
        viewMenu.AppendCheckItem(ID_VIEW_SHOW_FORMATTING, "&Show formatting")
        
        scriptMenu = wxMenu()
        scriptMenu.Append(ID_SCRIPT_FIND_ERROR, "&Find next error\tCTRL-E")

        scriptMenu.Append(ID_SCRIPT_PAGINATE, "&Paginate")
        scriptMenu.Append(ID_SCRIPT_TITLES, "&Title pages...")
        scriptMenu.Append(ID_SCRIPT_HEADERS, "&Headers...")

        reportsMenu = wxMenu()
        reportsMenu.Append(ID_REPORTS_DIALOGUE_CHART, "&Dialogue chart")
        reportsMenu.Append(ID_REPORTS_CHARACTER_REP, "&Character report...")
        
        toolsMenu = wxMenu()
        toolsMenu.Append(ID_TOOLS_NAME_DB, "&Name database...")
        toolsMenu.Append(ID_TOOLS_CHARMAP, "&Character map...")
        toolsMenu.Append(ID_TOOLS_COMPARE_SCRIPTS, "C&ompare scripts...")

        helpMenu = wxMenu()
        helpMenu.Append(ID_HELP_COMMANDS, "&Commands...")
        helpMenu.Append(ID_HELP_MANUAL, "&Manual")
        helpMenu.AppendSeparator()

        tmp = wxMenu()
        tmp.Append(ID_LICENSE_INFO, "&Information...")
        tmp.Append(ID_LICENSE_UPDATE, "&Update...")
        tmp.Append(ID_LICENSE_RELEASE, "&Release")
        
        helpMenu.AppendMenu(ID_HELP_LICENSE, "&License", tmp)
        helpMenu.AppendSeparator()
        helpMenu.Append(ID_HELP_ABOUT, "&About...")
        
        self.menuBar = wxMenuBar()
        self.menuBar.Append(fileMenu, "&File")
        self.menuBar.Append(editMenu, "&Edit")
        self.menuBar.Append(viewMenu, "&View")
        self.menuBar.Append(scriptMenu, "Scr&ipt")
        self.menuBar.Append(reportsMenu, "&Reports")
        self.menuBar.Append(toolsMenu, "Too&ls")
        self.menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(self.menuBar)

        EVT_MOVE(self, self.OnMove)
        EVT_SIZE(self, self.OnSize)

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.typeCb = wxComboBox(self, -1, style = wxCB_READONLY)

        for t in cfg.types.values():
            self.typeCb.Append(t.name, t.lt)

        # this is hidden here because it's somewhat harder to find here
        # than in misc.pyo
        misc.version = "1.0"

        # slightly obfuscated in a desperate attempt to fool at least some
        # people...
        misc.releaseDate = datetime.date(500 * 4 + 4, 5 + 7, 14 + 6 - 1)

        misc.license = None

        if gd.license:
            self.setLicense(gd.license, None, True)
            
        hsizer.Add(self.typeCb)

        vsizer.Add(hsizer, 0, wxALL, 5)
        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND)

        self.notebook = wxNotebook(self, -1, style = wxCLIP_CHILDREN)
        vsizer.Add(self.notebook, 1, wxEXPAND)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND)

        self.statusBar = wxStatusBar(self)
        self.statusBar.SetFieldsCount(3)
        self.statusBar.SetStatusWidths([-2, -2, -1])
        self.SetStatusBar(self.statusBar)

        EVT_MENU_HIGHLIGHT_ALL(self, self.OnMenuHighlight)
        
        EVT_NOTEBOOK_PAGE_CHANGED(self, self.notebook.GetId(),
                                  self.OnPageChange)
        
        EVT_COMBOBOX(self, self.typeCb.GetId(), self.OnTypeCombo)

        EVT_MENU(self, ID_FILE_NEW, self.OnNew)
        EVT_MENU(self, ID_FILE_OPEN, self.OnOpen)
        EVT_MENU(self, ID_FILE_SAVE, self.OnSave)
        EVT_MENU(self, ID_FILE_SAVE_AS, self.OnSaveAs)
        EVT_MENU(self, ID_FILE_IMPORT, self.OnImport)
        EVT_MENU(self, ID_FILE_EXPORT, self.OnExport)
        EVT_MENU(self, ID_FILE_CLOSE, self.OnClose)
        EVT_MENU(self, ID_FILE_REVERT, self.OnRevert)
        EVT_MENU(self, ID_FILE_PRINT, self.OnPrint)
        EVT_MENU(self, ID_FILE_SETTINGS, self.OnCfg)
        EVT_MENU(self, ID_FILE_CFG_LOAD, self.OnCfgLoad)
        EVT_MENU(self, ID_FILE_CFG_SAVE_AS, self.OnCfgSaveAs)
        EVT_MENU(self, ID_FILE_EXIT, self.OnExit)
        EVT_MENU(self, ID_EDIT_CUT, self.OnCut)
        EVT_MENU(self, ID_EDIT_COPY, self.OnCopy)
        EVT_MENU(self, ID_EDIT_PASTE, self.OnPaste)
        EVT_MENU(self, ID_EDIT_COPY_TO_CB, self.OnCopyCb)
        EVT_MENU(self, ID_EDIT_PASTE_FROM_CB, self.OnPasteCb)
        EVT_MENU(self, ID_EDIT_SELECT_SCENE, self.OnSelectScene)
        EVT_MENU(self, ID_EDIT_FIND, self.OnFind)
        EVT_MENU(self, ID_EDIT_DELETE_ELEMENTS, self.OnDeleteElements)
        EVT_MENU(self, ID_VIEW_STYLE_DRAFT, self.OnStyleChange)
        EVT_MENU(self, ID_VIEW_STYLE_LAYOUT, self.OnStyleChange)
        EVT_MENU(self, ID_VIEW_SHOW_FORMATTING, self.OnShowFormatting)
        EVT_MENU(self, ID_SCRIPT_FIND_ERROR, self.OnFindError)
        EVT_MENU(self, ID_SCRIPT_PAGINATE, self.OnPaginate)
        EVT_MENU(self, ID_SCRIPT_TITLES, self.OnTitles)
        EVT_MENU(self, ID_SCRIPT_HEADERS, self.OnHeaders)
        EVT_MENU(self, ID_REPORTS_DIALOGUE_CHART, self.OnDialogueChart)
        EVT_MENU(self, ID_REPORTS_CHARACTER_REP, self.OnCharacterReport)
        EVT_MENU(self, ID_TOOLS_NAME_DB, self.OnNameDb)
        EVT_MENU(self, ID_TOOLS_CHARMAP, self.OnCharMap)
        EVT_MENU(self, ID_TOOLS_COMPARE_SCRIPTS, self.OnCompareScripts)
        EVT_MENU(self, ID_HELP_COMMANDS, self.OnHelpCommands)
        EVT_MENU(self, ID_HELP_MANUAL, self.OnHelpManual)
        EVT_MENU(self, ID_HELP_ABOUT, self.OnAbout)
        EVT_MENU(self, ID_LICENSE_INFO, self.OnLicenseInfo)
        EVT_MENU(self, ID_LICENSE_UPDATE, self.OnLicenseUpdate)
        EVT_MENU(self, ID_LICENSE_RELEASE, self.OnLicenseRelease)

        EVT_CLOSE(self, self.OnCloseWindow)

        self.Layout()
        
    def init(self):
        self.panel = self.createNewPanel()

    def mySetIcons(self):
        wxImage_AddHandler(wxPNGHandler())

        ib = wxIconBundle()
        
        img = wxImage("icon32.png", wxBITMAP_TYPE_PNG)
        imgS = wxImage("icon16.png", wxBITMAP_TYPE_PNG)

        bitmap = wxBitmapFromImage(img)
        icon = wxIconFromBitmap(bitmap)
        ib.AddIcon(icon)

        bitmap = wxBitmapFromImage(imgS)
        icon = wxIconFromBitmap(bitmap)
        ib.AddIcon(icon)

        self.SetIcons(ib)

    def allocIds(self):
        names = [
            "ID_EDIT_COPY",
            "ID_EDIT_COPY_TO_CB",
            "ID_EDIT_CUT",
            "ID_EDIT_DELETE_ELEMENTS",
            "ID_EDIT_FIND",
            "ID_EDIT_PASTE",
            "ID_EDIT_PASTE_FROM_CB",
            "ID_EDIT_SELECT_SCENE",
            "ID_FILE_CFG_LOAD",
            "ID_FILE_CFG_SAVE_AS",
            "ID_FILE_CLOSE",
            "ID_FILE_EXIT",
            "ID_FILE_EXPORT",
            "ID_FILE_IMPORT",
            "ID_FILE_NEW",
            "ID_FILE_OPEN",
            "ID_FILE_PRINT",
            "ID_FILE_REVERT",
            "ID_FILE_SAVE",
            "ID_FILE_SAVE_AS",
            "ID_FILE_SETTINGS",
            "ID_HELP_ABOUT",
            "ID_HELP_COMMANDS",
            "ID_HELP_LICENSE",
            "ID_HELP_MANUAL",
            "ID_LICENSE_INFO",
            "ID_LICENSE_RELEASE",
            "ID_LICENSE_UPDATE",
            "ID_REPORTS_CHARACTER_REP",
            "ID_REPORTS_DIALOGUE_CHART",
            "ID_SCRIPT_FIND_ERROR",
            "ID_SCRIPT_HEADERS",
            "ID_SCRIPT_PAGINATE",
            "ID_SCRIPT_TITLES",
            "ID_TOOLS_CHARMAP",
            "ID_TOOLS_COMPARE_SCRIPTS",
            "ID_TOOLS_NAME_DB",
            "ID_VIEW_SHOW_FORMATTING",
            "ID_VIEW_STYLE_DRAFT",
            "ID_VIEW_STYLE_LAYOUT"
            ]

        g = globals()
        
        for n in names:
            g[n] = wxNewId()

    def createNewPanel(self):
        newPanel = MyPanel(self.notebook, -1)
        self.notebook.AddPage(newPanel, "", True)
        newPanel.ctrl.setTabText()
        newPanel.ctrl.SetFocus()

        return newPanel

    def setTitle(self, text):
        self.SetTitle("Blyte - %s" % text)

    def setTabText(self, panel, text):
        i = self.findPage(panel)
        if i != -1:
            self.notebook.SetPageText(i, text)
    
    # notebook.GetSelection() returns invalid values, eg. it can return 1
    # when there is only one tab in existence, so it can't be relied on.
    # this is currently worked around by never using that function,
    # instead this iterates over all tabs and finds out the correct page
    # number.
    def findPage(self, panel):
        for i in range(self.notebook.GetPageCount()):
            p = self.notebook.GetPage(i)
            if p == panel:
                return i

        return -1

    # get list of MyCtrl objects for all open scripts
    def getCtrls(self):
        l = []

        for i in range(self.notebook.GetPageCount()):
            l.append(self.notebook.GetPage(i).ctrl)

        return l

    # returns True if any open script has been modified
    def isModifications(self):
        for c in self.getCtrls():
            if c.isModified():
                return True

        return False

    # try to set license from s.
    def setLicense(self, s, frame, isStarting):
        lic = util.License.fromStr(s, frame)

        if lic:
            if misc.releaseDate > lic.lastDate:
                wxMessageBox("License is only valid for program\n"
                    "versions released before %s." % lic.lastDate.isoformat(),
                    "Error", wxOK, frame)

                return
                
            misc.license = lic
            gd.license = s

            if not isStarting:
                util.writeToFile(gd.stateFilename, gd.cvars.save("", gd),
                                 frame)

                wxMessageBox("License successfully updated.",
                             "Information", wxOK, frame)
        
    def OnMenuHighlight(self, event):
        # default implementation modifies status bar, so we need to
        # override it and do nothing
        pass

    def OnPageChange(self, event):
        newPage = event.GetSelection()
        self.panel = self.notebook.GetPage(newPage)
        self.panel.ctrl.SetFocus()
        self.panel.ctrl.updateCommon()
        self.setTitle(self.panel.ctrl.fileNameDisplay)
        
    def OnNew(self, event = None):
        self.panel = self.createNewPanel()

    def OnOpen(self, event):
        dlg = wxFileDialog(self, "File to open", misc.scriptDir,
            wildcard = "Blyte files (*.blyte)|*.blyte|All files|*",
            style = wxOPEN)
        
        if dlg.ShowModal() == wxID_OK:
            misc.scriptDir = dlg.GetDirectory()
            
            if not self.notebook.GetPage(self.findPage(self.panel))\
                   .ctrl.isUntouched():
                self.panel = self.createNewPanel()

            self.panel.ctrl.loadFile(dlg.GetPath())
            self.panel.ctrl.updateScreen()

        dlg.Destroy()

    def OnSave(self, event):
        self.panel.ctrl.OnSave()

    def OnSaveAs(self, event):
        self.panel.ctrl.OnSaveAs()

    def OnImport(self, event):
        dlg = wxFileDialog(self, "File to import", misc.scriptDir,
            wildcard = "Text files (*.txt)|*.txt|All files|*",
            style = wxOPEN)
        
        if dlg.ShowModal() == wxID_OK:
            misc.scriptDir = dlg.GetDirectory()

            if not self.notebook.GetPage(self.findPage(self.panel))\
                   .ctrl.isUntouched():
                self.panel = self.createNewPanel()

            self.panel.ctrl.importFile(dlg.GetPath())
            self.panel.ctrl.updateScreen()

        dlg.Destroy()

    def OnExport(self, event):
        self.panel.ctrl.OnExport()

    def OnClose(self, event = None):
        if not self.panel.ctrl.canBeClosed():
            return
        
        if self.notebook.GetPageCount() > 1:
            self.notebook.DeletePage(self.findPage(self.panel))
        else:
            self.panel.ctrl.createEmptySp()
            self.panel.ctrl.updateScreen()

    def OnRevert(self, event):
        self.panel.ctrl.OnRevert()

    def OnPrint(self, event):
        self.panel.ctrl.OnPrint()

    def OnCfg(self, event):
        self.panel.ctrl.OnCfg()

    def OnCfgLoad(self, event):
        dlg = wxFileDialog(self, "File to open",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wxOPEN)

        if dlg.ShowModal() == wxID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                c = config.Config()
                c.load(s)
                gd.confFilename = dlg.GetPath()
                
                self.panel.ctrl.applyCfg(c, False)

        dlg.Destroy()

    def OnCfgSaveAs(self, event):
        dlg = wxFileDialog(self, "Filename to save as",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            if util.writeToFile(dlg.GetPath(), cfg.save(), self):
                gd.confFilename = dlg.GetPath()
            
        dlg.Destroy()

    def OnCut(self, event):
        self.panel.ctrl.OnCut()

    def OnCopy(self, event):
        self.panel.ctrl.OnCopy()

    def OnCopyCb(self, event):
        self.panel.ctrl.OnCopyCb()

    def OnPaste(self, event):
        self.panel.ctrl.OnPaste()

    def OnPasteCb(self, event):
        self.panel.ctrl.OnPasteCb()

    def OnSelectScene(self, event):
        self.panel.ctrl.OnSelectScene()

    def OnFindError(self, event):
        self.panel.ctrl.OnFindError()

    def OnFind(self, event):
        self.panel.ctrl.OnFind()

    def OnDeleteElements(self, event):
        self.panel.ctrl.OnDeleteElements()

    def OnShowFormatting(self, event):
        self.showFormatting = self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING)
        self.panel.ctrl.Refresh(False)

    def OnStyleChange(self, event):
        gd.isDraft = self.menuBar.IsChecked(ID_VIEW_STYLE_DRAFT)

        c = self.panel.ctrl
        c.makeLineVisible(c.line)
        c.updateScreen()

    def OnPaginate(self, event = None):
        self.panel.ctrl.OnPaginate()

    def OnTitles(self, event):
        self.panel.ctrl.OnTitles()

    def OnHeaders(self, event):
        self.panel.ctrl.OnHeaders()

    def OnDialogueChart(self, event):
        self.panel.ctrl.OnDialogueChart()

    def OnCharacterReport(self, event):
        self.panel.ctrl.OnCharacterReport()

    def OnNameDb(self, event):
        if not hasattr(self, "names"):
            self.statusBar.SetStatusText("Opening name database...", 1)
            wxSafeYield()
            wxBeginBusyCursor()
            self.names = decode.readNames("names.dat")
            wxEndBusyCursor()
            self.panel.ctrl.updateCommon()

            if self.names.count == 0:
                wxMessageBox("Error opening name database", "Error",
                             wxOK, self)
                del self.names

                return

        dlg = namesdlg.NamesDlg(self, self.panel.ctrl, self.names)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCharMap(self, event):
        dlg = charmapdlg.CharMapDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCompareScripts(self, event):
        self.panel.ctrl.OnCompareScripts()

    def OnHelpCommands(self, event):
        dlg = commandsdlg.CommandsDlg()
        dlg.Show()

    def OnHelpManual(self, event):
        util.showPDF(misc.progPath + "/manual.pdf", cfg, self)
        
    def OnAbout(self, event):
        win = splash.SplashWindow(self, -1)
        win.Show()

    def OnLicenseInfo(self, event):
        if misc.license:
            s = "Licensed to: '%s'\n" % misc.license.userId.lstrip()

            s += "License type: %s\n" % misc.license.getTypeStr()
            s += "Upgradable until: %s\n" % misc.license.lastDate.isoformat()

        else:
            s = "Evaluation copy."

        wxMessageBox(s, "License info", wxOK, self)
        
    def OnLicenseUpdate(self, event):
        dlg = wxFileDialog(self, "License file to open", ".",
            wildcard = "License files (*.lic)|*.lic|All files|*",
            style = wxOPEN)
        
        if dlg.ShowModal() == wxID_OK:
            data = util.loadFile(dlg.GetPath(), self)

            if data != None:
                self.setLicense(data, self, False);

        dlg.Destroy()
    
    def OnLicenseRelease(self, event):
        if misc.license == None:
            wxMessageBox("You already are in evaluation mode.", "Error",
                         wxOK, self)
        else:
            if wxMessageBox("Are you sure you want to release your\n"
                            "license information, i.e. go back to\n"
                            "evaluation mode?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxYES:
                misc.license = None

    def OnTypeCombo(self, event):
        self.panel.ctrl.OnTypeCombo(event)

    def OnCloseWindow(self, event):
        doExit = True
        if event.CanVeto() and self.isModifications():
            if wxMessageBox("You have unsaved changes. Are\n"
                            "you sure you want to exit?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxNO:
                doExit = False

        if doExit:
            util.writeToFile(gd.stateFilename, gd.cvars.save("", gd),
                             self)
            util.removeTempFiles(misc.tmpPrefix)
            self.Destroy()
            myApp.ExitMainLoop()
        else:
            event.Veto()

    def OnExit(self, event):
        self.Close(False)
        
    def OnMove(self, event):
        gd.posX, gd.posY = self.GetPositionTuple()
        event.Skip()

    def OnSize(self, event):
        gd.width, gd.height = self.GetSizeTuple()
        event.Skip()

class MyApp(wxApp):

    def OnInit(self):
        global cfg, mainFrame, gd

        if (wxMAJOR_VERSION != 2) or (wxMINOR_VERSION != 4) or (
            wxRELEASE_NUMBER < 2):
            wxMessageBox("You seem to have an invalid version\n"
                         "(%s) of wxWidgets installed. This\n"
                         "program needs version 2.4.x, where\n"
                         "x >= 2." % wxVERSION_STRING, "Error", wxOK)
            sys.exit()

        misc.init()
        util.init()

        # if we're on linux and running a released version, remove all
        # ~/.oskusoft-tmp/*.pyo files now, we've already loaded them all,
        # and we don't want them lying around for the user to stumble on.
        if misc.isUnix and "--test" not in sys.argv:
            tmpDir = os.environ["HOME"] + "/.oskusoft-tmp"
            os.chdir(tmpDir)
            os.system("rm -f *.pyo")
            os.rmdir(tmpDir)
            
        gd = GlobalData()

        if misc.isWindows:
            major = sys.getwindowsversion()[0]
            if major < 5:
                wxMessageBox("You seem to have a version of Windows\n"
                             "older than Windows 2000, which is the minimum\n"
                             "requirement for this program. There are no\n"
                             "guarantees that this program will work\n"
                             "correctly on this machine.", "Error", wxOK)

        os.chdir(misc.progPath)
        
        cfg = config.Config()
        config.currentCfg = cfg

        if util.fileExists(gd.confFilename):
            s = util.loadFile(gd.confFilename, None)

            if s:
                cfg.load(s)
        else:
            # we want to write out a default config file at startup
            # for various reasons, if no default config file yet
            # exists
            util.writeToFile(gd.confFilename, cfg.save(), None)

        refreshGuiConfig()

        # cfg.scriptDir is the directory used on startup, while
        # misc.scriptDir is updated every time the user opens/saves
        # something in a different directory.
        misc.scriptDir = cfg.scriptDir

        if util.fileExists(gd.stateFilename):
            s = util.loadFile(gd.stateFilename, None)

            if s:
                gd.cvars.load(gd.cvars.makeVals(s), "", gd)

        # we now have both config and gd, init stuff that needs both
        gd.refresh()
        
        mainFrame = MyFrame(NULL, -1, "Blyte")
        bugreport.mainFrame = mainFrame
        mainFrame.init()
        mainFrame.Show(True)

        # windows needs this for some reason
        mainFrame.panel.ctrl.SetFocus()
        
        self.SetTopWindow(mainFrame)

        if "--test" not in sys.argv:
            win = splash.SplashWindow(mainFrame, 2500)
            win.Show()
            win.Raise()
        
        return True

def main():
    global myApp

    if "--test" not in sys.argv:
        brh = bugreport.BugReportHandler()
        sys.stdout = brh
        sys.stderr = brh
    
    myApp = MyApp(0)
    myApp.MainLoop()

main()
