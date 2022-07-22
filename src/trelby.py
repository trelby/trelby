# -*- coding: iso-8859-1 -*-

from error import TrelbyError
import autocompletiondlg
import cfgdlg
import charmapdlg
import commandsdlg
import config
import dialoguechart
import finddlg
import gutil
import headersdlg
import locationsdlg
import misc
import myimport
import mypickle
import namesdlg
import opts
import pml
import reports
import screenplay
import spellcheck
import spellcheckcfgdlg
import spellcheckdlg
import splash
import titlesdlg
import util
import viewmode
import watermarkdlg
import webbrowser

import copy
import os
import os.path
import os
import signal
import sys
import time
import wx

from functools import partial

#keycodes
KC_CTRL_A = 1
KC_CTRL_B = 2
KC_CTRL_D = 4
KC_CTRL_E = 5
KC_CTRL_F = 6
KC_CTRL_N = 14
KC_CTRL_P = 16
KC_CTRL_V = 22

VIEWMODE_DRAFT,\
VIEWMODE_LAYOUT,\
VIEWMODE_SIDE_BY_SIDE,\
= list(range(3))

def refreshGuiConfig():
    global cfgGui

    cfgGui = config.ConfigGui(cfgGl)

def getCfgGui():
    return cfgGui

# keeps (some) global data
class GlobalData:
    def __init__(self):

        self.confFilename = misc.confPath + "/default.conf"
        self.stateFilename = misc.confPath + "/state"
        self.scDictFilename = misc.confPath + "/spell_checker_dictionary"

        # current script config path
        self.scriptSettingsPath = misc.confPath

        # global spell checker (user) dictionary
        self.scDict = spellcheck.Dict()

        # recently used files list
        self.mru = misc.MRUFiles(5)

        if opts.conf:
            self.confFilename = opts.conf

        v = self.cvars = mypickle.Vars()

        v.addInt("posX", 0, "PositionX", -20, 9999)
        v.addInt("posY", 0, "PositionY", -20, 9999)

        # linux has bigger font by default so it needs a wider window
        defaultW = 750
        if misc.isUnix:
            defaultW = 800

        v.addInt("width", defaultW, "Width", 500, 9999)

        v.addInt("height", 830, "Height", 300, 9999)
        v.addInt("viewMode", VIEWMODE_DRAFT, "ViewMode", VIEWMODE_DRAFT,
                 VIEWMODE_SIDE_BY_SIDE)

        v.addList("files", [], "Files",
                  mypickle.StrUnicodeVar("", "", ""))

        v.makeDicts()
        v.setDefaults(self)

        self.height = min(self.height,
            wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y) - 50)

        self.vmDraft = viewmode.ViewModeDraft()
        self.vmLayout = viewmode.ViewModeLayout()
        self.vmSideBySide = viewmode.ViewModeSideBySide()

        self.setViewMode(self.viewMode)

        self.makeConfDir()

    def makeConfDir(self):
        makeDir = not util.fileExists(misc.confPath)

        if makeDir:
            try:
                os.mkdir(misc.toPath(misc.confPath), mode=0o755)
            except OSError(os.errno, os.strerror):
                wx.MessageBox("Error creating configuration directory\n"
                              "'%s': %s" % (misc.confPath, os.strerror),
                              "Error", wx.OK, None)

    # set viewmode, the parameter is one of the VIEWMODE_ defines.
    def setViewMode(self, viewMode):
        self.viewMode = viewMode

        if viewMode == VIEWMODE_DRAFT:
            self.vm = self.vmDraft
        elif viewMode == VIEWMODE_LAYOUT:
            self.vm = self.vmLayout
        elif viewMode == VIEWMODE_SIDE_BY_SIDE:
            self.vm = self.vmSideBySide
        else:
            self.vm = self.vmDraft

    # load from string 's'. does not throw any exceptions and silently
    # ignores any errors.
    def load(self, s):
        self.cvars.load(self.cvars.makeVals(s), "", self)
        self.mru.items = self.files

    # save to a string and return that.
    def save(self):
        self.files = self.mru.items

        return self.cvars.save("", self)

    # save global spell checker dictionary to disk
    def saveScDict(self):
        util.writeToFile(self.scDictFilename, self.scDict.save(), mainFrame)

class MyPanel(wx.Panel):

    def __init__(self, parent, id):
        wx.Panel.__init__(
            self, parent, id,
            # wxMSW/Windows does not seem to support
            # wx.NO_BORDER, which sucks
            style = wx.WANTS_CHARS | wx.NO_BORDER)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.scrollBar = wx.ScrollBar(self, -1, style = wx.SB_VERTICAL)
        self.ctrl = MyCtrl(self, -1)

        hsizer.Add(self.ctrl, 1, wx.EXPAND)
        hsizer.Add(self.scrollBar, 0, wx.EXPAND)

        self.scrollBar.Bind(wx.EVT_COMMAND_SCROLL, self.ctrl.OnScroll)

        self.scrollBar.Bind(wx.EVT_SET_FOCUS, self.OnScrollbarFocus)

        self.SetSizer(hsizer)

    # we never want the scrollbar to get the keyboard focus, pass it on to
    # the main widget
    def OnScrollbarFocus(self, event):
        self.ctrl.SetFocus()

class MyCtrl(wx.Control):

    def __init__(self, parent, id):
        style = wx.WANTS_CHARS | wx.FULL_REPAINT_ON_RESIZE | wx.NO_BORDER
        wx.Control.__init__(self, parent, id, style = style)

        self.panel = parent

        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.Bind(wx.EVT_CHAR, self.OnKeyChar)

        self.createEmptySp()
        self.updateScreen(redraw = False)

    def OnChangeType(self, event):
        cs = screenplay.CommandState()

        lt = idToLTMap[event.GetId()]

        self.sp.convertTypeTo(lt, True)
        self.sp.cmdPost(cs)

        if cs.needsVisifying:
            self.makeLineVisible(self.sp.line)

        self.updateScreen()

    def clearVars(self):
        self.mouseSelectActive = False

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
        self.sp = screenplay.Screenplay(cfgGl)
        self.sp.titles.addDefaults()
        self.sp.headers.addDefaults()
        self.setFile(None)
        self.refreshCache()

    # update stuff that depends on configuration / view mode etc.
    def refreshCache(self):
        self.chX = util.getTextWidth(" ", pml.COURIER, self.sp.cfg.fontSize)
        self.chY = util.getTextHeight(self.sp.cfg.fontSize)

        self.pageW = gd.vm.getPageWidth(self)

        # conversion factor from mm to pixels
        self.mm2p = self.pageW / self.sp.cfg.paperWidth

        # page width and height on screen, in pixels
        self.pageW = int(self.pageW)
        self.pageH = int(self.mm2p * self.sp.cfg.paperHeight)

    def getCfgGui(self):
        return cfgGui

    def loadFile(self, fileName):
        s = str(util.loadFile(fileName, mainFrame))
        if s == None:
            return

        try:
            (sp, msg) = screenplay.Screenplay.load(s, cfgGl)
        except TrelbyError as e:
            wx.MessageBox("Error loading file:\n\n%s" % e, "Error",
                          wx.OK, mainFrame)

            return

        if msg:
            misc.showText(mainFrame, msg, "Warning")

        self.clearVars()
        self.sp = sp
        self.setFile(fileName)
        self.refreshCache()

        # saved cursor position might be anywhere, so we can't just
        # display the first page
        self.makeLineVisible(self.sp.line)

    # save script to given filename. returns True on success.
    def saveFile(self, fileName):
        fileName = str(util.ensureEndsIn(fileName, ".trelby"))

        if util.writeToFile(fileName, self.sp.save(), mainFrame):
            self.setFile(fileName)
            self.sp.markChanged(False)
            gd.mru.add(fileName)

            return True
        else:
            return False

    def importFile(self, fileName):
        titlePages = False
        if fileName.endswith("fdx"):
            lines = myimport.importFDX(fileName, mainFrame)
        elif fileName.endswith("celtx"):
            lines = myimport.importCeltx(fileName, mainFrame)
        elif fileName.endswith("astx"):
            lines = myimport.importAstx(fileName, mainFrame)
        elif fileName.endswith("fountain"):
            lines, titlePages = myimport.importFountain(fileName, mainFrame, self.sp.titles.pages)
        elif fileName.endswith("fadein"):
            lines = myimport.importFadein(fileName, mainFrame)
        else:
            lines = myimport.importTextFile(fileName, mainFrame)

        if not lines:
            return

        self.createEmptySp()

        self.sp.lines = lines
        if titlePages:
            self.sp.titles.pages = titlePages
        self.sp.reformatAll()
        self.sp.paginate()
        self.sp.markChanged(True)

    # generate exportable text from given screenplay, or None.
    def getExportText(self, sp):
        inf = []
        inf.append(misc.CheckBoxItem("Include page markers"))

        dlg = misc.CheckBoxDlg(mainFrame, "Output options", inf,
                               "Options:", False)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()

            return None

        return sp.generateText(inf[0].selected)

    def getExportHtml(self, sp):
        inf = []
        inf.append(misc.CheckBoxItem("Include Notes"))

        dlg = misc.CheckBoxDlg(mainFrame, "Output options", inf,
                               "Options:", False)

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()

            return None

        return sp.generateHtml(inf[0].selected)

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
                tmp = name + "-%d" % i

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

    # texts = gd.vm.getScreen(self, False)[0], or None, in which case it's
    # called in this function.
    def isLineVisible(self, line, texts = None):
        if texts == None:
            texts = gd.vm.getScreen(self, False)[0]

        # paranoia never hurts
        if len(texts) == 0:
            return False

        return (line >= texts[0].line) and (line <= texts[-1].line)

    def makeLineVisible(self, line, direction = config.SCROLL_CENTER):
        texts = gd.vm.getScreen(self, False)[0]

        if self.isLineVisible(line, texts):
            return

        gd.vm.makeLineVisible(self, line, texts, direction)

    def adjustScrollBar(self):
        height = self.GetClientSize().height

        # rough approximation of how many lines fit onto the screen.
        # accuracy is not that important for this, so we don't even care
        # about draft / layout mode differences.
        approx = int(((height / self.mm2p) / self.chY) / 1.3)

        self.panel.scrollBar.SetScrollbar(self.sp.getTopLine(), approx,
            len(self.sp.lines) + approx - 1, approx)

    def clearAutoComp(self):
        if self.sp.clearAutoComp():
            self.Refresh(False)

    # returns true if there are no contents at all and we're not
    # attached to any file
    def isUntouched(self):
        if self.fileName or (len(self.sp.lines) > 1) or \
           (len(self.sp.lines[0].text) > 0):
            return False
        else:
            return True

    def updateScreen(self, redraw = True, setCommon = True):
        self.adjustScrollBar()

        if setCommon:
            self.updateCommon()

        if redraw:
            self.Refresh(False)

    # update GUI elements shared by all scripts, like statusbar etc
    def updateCommon(self):
        cur = cfgGl.getType(self.sp.lines[self.sp.line].lt)

        if self.sp.tabMakesNew():
            tabNext = "%s" % cfgGl.getType(cur.newTypeTab).ti.name
        else:
            tabNext = "%s" % cfgGl.getType(cur.nextTypeTab).ti.name

        enterNext = cfgGl.getType(cur.newTypeEnter).ti.name

        page = self.sp.line2page(self.sp.line)
        pageCnt = self.sp.line2page(len(self.sp.lines) - 1)

        mainFrame.statusCtrl.SetValues(page, pageCnt, cur.ti.name, tabNext, enterNext)

        canUndo = self.sp.canUndo()
        canRedo = self.sp.canRedo()

        mainFrame.menuBar.Enable(ID_EDIT_UNDO, canUndo)
        mainFrame.menuBar.Enable(ID_EDIT_REDO, canRedo)

        mainFrame.toolBar.EnableTool(ID_EDIT_UNDO, canUndo)
        mainFrame.toolBar.EnableTool(ID_EDIT_REDO, canRedo)

    # apply per-script config
    def applyCfg(self, newCfg):
        self.sp.applyCfg(newCfg)

        self.refreshCache()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    # apply global config
    def applyGlobalCfg(self, newCfgGl, writeCfg = True):
        global cfgGl

        oldCfgGl = cfgGl

        cfgGl = copy.deepcopy(newCfgGl)

        # if user has ventured from the old default directory, keep it as
        # the current one, otherwise set the new default as current.
        if misc.scriptDir == oldCfgGl.scriptDir:
            misc.scriptDir = cfgGl.scriptDir

        cfgGl.recalc()
        refreshGuiConfig()
        mainFrame.updateKbdCommands()

        for c in mainFrame.getCtrls():
            c.sp.cfgGl = cfgGl
            c.refreshCache()
            c.makeLineVisible(c.sp.line)
            c.adjustScrollBar()

        self.updateScreen()

        # in case tab colors have been changed
        mainFrame.tabCtrl.Refresh(False)
        mainFrame.statusCtrl.Refresh(False)
        mainFrame.noFSBtn.Refresh(False)
        mainFrame.toolBar.SetBackgroundColour(cfgGui.tabBarBgColor)

        if writeCfg:
            util.writeToFile(gd.confFilename, cfgGl.save(), mainFrame)

        mainFrame.checkFonts()

    def applyHeaders(self, newHeaders):
        self.sp.headers = newHeaders
        self.sp.markChanged()
        self.OnPaginate()

    # return an exportable, paginated Screenplay object, or None if for
    # some reason that's not possible / wanted. 'action' is the name of
    # the action, e.g. "export" or "print", that'll be done to the script,
    # and is used in dialogue with the user if needed.
    def getExportable(self, action):
        if cfgGl.checkOnExport:
            line = self.sp.findError(0)[0]

            if line != -1:
                if wx.MessageBox(
                    "The script seems to contain errors.\n"
                    "Are you sure you want to %s it?" % action, "Confirm",
                     wx.YES_NO | wx.NO_DEFAULT, mainFrame) == wx.NO:

                    return None

        sp = self.sp
        if sp.cfg.pdfRemoveNotes:
            sp = copy.deepcopy(self.sp)
            sp.removeElementTypes({screenplay.NOTE : None}, False)

        sp.paginate()

        return sp

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event):
        if misc.doDblBuf:
            size = self.GetClientSize()

            sb = wx.Bitmap(size.width, size.height)
            old = getattr(self.__class__, "screenBuf", None)

            if (old == None) or (old.GetDepth() != sb.GetDepth()) or \
               (old.GetHeight() != sb.GetHeight()) or \
               (old.GetWidth() != sb.GetWidth()):
                self.__class__.screenBuf = sb

        self.makeLineVisible(self.sp.line)

    def OnLeftDown(self, event, mark = False):
        if not self.mouseSelectActive:
            self.sp.clearMark()
            self.updateScreen()

        pos = event.GetPosition()
        line, col = gd.vm.pos2linecol(self, pos.x, pos.y)

        self.mouseSelectActive = True

        if line is not None:
            self.sp.gotoPos(line, col, mark)
            self.updateScreen()

    def OnLeftUp(self, event):
        self.mouseSelectActive = False

        # to avoid phantom selections (Windows sends some strange events
        # sometimes), check if anything worthwhile is actually selected.
        cd = self.sp.getSelectedAsCD(False)

        if not cd or ((len(cd.lines) == 1) and (len(cd.lines[0].text) < 2)):
            self.sp.clearMark()

    def OnMotion(self, event):
        if event.LeftIsDown():
            self.OnLeftDown(event, mark = True)

    def OnRightDown(self, event):
        pos = event.GetPosition()
        line, col = gd.vm.pos2linecol(self, pos.x, pos.y)

        if self.sp.mark:
            m = mainFrame.rightClickMenuWithCut
        else:
            m = mainFrame.rightClickMenu

            if line is not None and (line != self.sp.line):
                self.sp.gotoPos(line, col, False)
                self.updateScreen()

        self.PopupMenu(m)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            delta = -cfgGl.mouseWheelLines
        else:
            delta = cfgGl.mouseWheelLines

        self.sp.setTopLine(self.sp.getTopLine() + delta)
        self.updateScreen()

    def OnScroll(self, event):
        pos = self.panel.scrollBar.GetThumbPosition()
        self.sp.setTopLine(pos)
        self.sp.clearAutoComp()
        self.updateScreen()

    def OnPaginate(self):
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnAutoCompletionDlg(self):
        dlg = autocompletiondlg.AutoCompletionDlg(mainFrame,
            copy.deepcopy(self.sp.autoCompletion))

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.autoCompletion = dlg.autoCompletion
            self.sp.markChanged()

        dlg.Destroy()

    def OnTitlesDlg(self):
        dlg = titlesdlg.TitlesDlg(mainFrame, copy.deepcopy(self.sp.titles),
                                  self.sp.cfg, cfgGl)

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.titles = dlg.titles
            self.sp.markChanged()

        dlg.Destroy()

    def OnHeadersDlg(self):
        dlg = headersdlg.HeadersDlg(mainFrame,
            copy.deepcopy(self.sp.headers), self.sp.cfg, cfgGl,
                                    self.applyHeaders)

        if dlg.ShowModal() == wx.ID_OK:
            self.applyHeaders(dlg.headers)

        dlg.Destroy()

    def OnLocationsDlg(self):
        dlg = locationsdlg.LocationsDlg(mainFrame, copy.deepcopy(self.sp))

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.locations = dlg.sp.locations
            self.sp.markChanged()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self):
        dlg = spellcheckcfgdlg.SCDictDlg(mainFrame,
            copy.deepcopy(self.sp.scDict), False)

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.scDict = dlg.scDict
            self.sp.markChanged()

        dlg.Destroy()

    def OnWatermark(self):
        dlg = watermarkdlg.WatermarkDlg(
            mainFrame, self.sp, self.fileNameDisplay.replace(".trelby", ""))
        dlg.ShowModal()
        dlg.Destroy()

    def OnReportDialogueChart(self):
        self.sp.paginate()
        dialoguechart.genDialogueChart(mainFrame, self.sp)

    def OnReportCharacter(self):
        self.sp.paginate()
        reports.genCharacterReport(mainFrame, self.sp)

    def OnReportLocation(self):
        self.sp.paginate()
        reports.genLocationReport(mainFrame, self.sp)

    def OnReportScene(self):
        self.sp.paginate()
        reports.genSceneReport(mainFrame, self.sp)

    def OnReportScript(self):
        self.sp.paginate()
        reports.genScriptReport(mainFrame, self.sp)

    def OnCompareScripts(self):
        if mainFrame.tabCtrl.getPageCount() < 2:
            wx.MessageBox("You need at least two scripts open to"
                          " compare them.", "Error", wx.OK, mainFrame)

            return

        items = []
        for c in mainFrame.getCtrls():
            items.append(c.fileNameDisplay)

        dlg = misc.ScriptChooserDlg(mainFrame, items)

        sel1 = -1
        sel2 = -1
        if dlg.ShowModal() == wx.ID_OK:
            sel1 = dlg.sel1
            sel2 = dlg.sel2
            force = dlg.forceSameCfg

        dlg.Destroy()

        if sel1 == -1:
            return

        if sel1 == sel2:
            wx.MessageBox("You can't compare a script to itself.", "Error",
                          wx.OK, mainFrame)

            return

        c1 = mainFrame.tabCtrl.getPage(sel1).ctrl
        c2 = mainFrame.tabCtrl.getPage(sel2).ctrl

        sp1 = c1.getExportable("compare")
        sp2 = c2.getExportable("compare")

        if not sp1 or not sp2:
            return

        if force:
            sp2 = copy.deepcopy(sp2)
            sp2.cfg = copy.deepcopy(sp1.cfg)
            sp2.reformatAll()
            sp2.paginate()

        s = sp1.compareScripts(sp2)

        if s:
            gutil.showTempPDF(s, cfgGl, mainFrame)
        else:
            wx.MessageBox("The scripts are identical.", "Results", wx.OK,
                          mainFrame)

    def canBeClosed(self):
        if self.sp.isModified():
            if wx.MessageBox("The script has been modified. Are you sure\n"
                             "you want to discard the changes?", "Confirm",
                             wx.YES_NO | wx.NO_DEFAULT, mainFrame) == wx.NO:
                return False

        return True

    # page up (dir == -1) or page down (dir == 1) was pressed, handle it.
    # cs = CommandState.
    def pageCmd(self, cs, dir):
        if self.sp.acItems:
            cs.doAutoComp = cs.AC_KEEP
            self.sp.pageScrollAutoComp(dir)

            return

        texts, dpages = gd.vm.getScreen(self, False)

        # if user has scrolled with scrollbar so that cursor isn't seen,
        # just make cursor visible and don't move
        if not self.isLineVisible(self.sp.line, texts):
            gd.vm.makeLineVisible(self, self.sp.line, texts)
            cs.needsVisifying = False

            return

        self.sp.maybeMark(cs.mark)
        gd.vm.pageCmd(self, cs, dir, texts, dpages)

    def OnRevertScript(self):
        if self.fileName:
            if not self.canBeClosed():
                return

            self.loadFile(self.fileName)
            self.updateScreen()

    def OnUndo(self):
        self.sp.cmd("undo")
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnRedo(self):
        self.sp.cmd("redo")
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    # returns True if something was deleted
    def OnCut(self, doUpdate = True, doDelete = True, copyToClip = True):
        marked = self.sp.getMarkedLines()

        if not marked:
            return False

        cd = self.sp.getSelectedAsCD(doDelete)

        if copyToClip:
            mainFrame.clipboard = cd

        if doUpdate:
            self.makeLineVisible(self.sp.line)
            self.updateScreen()

        return doDelete

    def OnCopy(self):
        self.OnCut(doDelete = False)

    def OnCopySystem(self, formatted = False):
        cd = self.sp.getSelectedAsCD(False)

        if not cd:
            return

        tmpSp = screenplay.Screenplay(cfgGl)
        tmpSp.lines = cd.lines

        if formatted:
            # have to call paginate, otherwise generateText will not
            # process all the text
            tmpSp.paginate()
            s = tmpSp.generateText(False)
        else:
            s = util.String()

            for ln in tmpSp.lines:
                txt = ln.text

                if tmpSp.cfg.getType(ln.lt).export.isCaps:
                    txt = util.upper(txt)

                s += txt + config.lb2str(ln.lb)

            s = str(s).replace("\n", os.linesep)

        if wx.TheClipboard.Open():
            wx.TheClipboard.UsePrimarySelection(False)

            wx.TheClipboard.Clear()
            wx.TheClipboard.AddData(wx.TextDataObject(s))
            wx.TheClipboard.Flush()

            wx.TheClipboard.Close()

    def OnPaste(self, clines = None):
        if not clines:
            cd = mainFrame.clipboard

            if not cd:
                return

            clines = cd.lines

        self.sp.paste(clines)

        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnPasteSystemCb(self):
        s = ""

        if wx.TheClipboard.Open():
            wx.TheClipboard.UsePrimarySelection(False)

            df = wx.DataFormat(wx.DF_TEXT)

            if wx.TheClipboard.IsSupported(df):
                data = wx.TextDataObject()
                wx.TheClipboard.GetData(data)
                s = util.cleanInput(data.GetText())

            wx.TheClipboard.Close()

        s = util.fixNL(s)

        if len(s) == 0:
            return

        inLines = s.split("\n")

        # shouldn't be possible, but...
        if len(inLines) == 0:
            return

        lines = []

        for s in inLines:
            if s:
                lines.append(screenplay.Line(screenplay.LB_LAST,
                                             screenplay.ACTION, s))

        self.OnPaste(lines)

    def OnSelectScene(self):
        self.sp.cmd("selectScene")

        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnSelectAll(self):
        self.sp.cmd("selectAll")

        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnGotoScene(self):
        self.sp.paginate()
        self.clearAutoComp()

        scenes = self.sp.getSceneLocations()

        def validateFunc(s):
            if s in [x[0] for x in scenes]:
                return ""
            else:
                return "Invalid scene number."

        dlg = misc.TextInputDlg(mainFrame, "Enter scene number (%s - %s):" %\
            (scenes[0][0], scenes[-1][0]), "Goto scene", validateFunc)

        if dlg.ShowModal() == wx.ID_OK:
            for it in scenes:
                if it[0] == dlg.input:
                    self.sp.line = it[1]
                    self.sp.column = 0

                    break

        # we need to refresh the screen in all cases because pagination
        # might have changed
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnGotoPage(self):
        self.sp.paginate()
        self.clearAutoComp()

        pages = self.sp.getPageNumbers()

        def validateFunc(s):
            if s in pages:
                return ""
            else:
                return "Invalid page number."

        dlg = misc.TextInputDlg(mainFrame, "Enter page number (%s - %s):" %\
            (pages[0], pages[-1]), "Goto page", validateFunc)

        if dlg.ShowModal() == wx.ID_OK:
            page = int(dlg.input)
            self.sp.line = self.sp.page2lines(page)[0]
            self.sp.column = 0

        # we need to refresh the screen in all cases because pagination
        # might have changed
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnInsertNbsp(self):
        self.OnKeyChar(util.MyKeyEvent(160))

    def OnFindNextError(self):
        self.clearAutoComp()

        line, msg = self.sp.findError(self.sp.line)

        if line != -1:
            self.sp.line = line
            self.sp.column = 0

            self.makeLineVisible(self.sp.line)
            self.updateScreen()

        else:
            msg = "No errors found."

        wx.MessageBox(msg, "Results", wx.OK, mainFrame)

    def OnFind(self):
        self.sp.clearMark()
        self.clearAutoComp()
        self.updateScreen()

        dlg = finddlg.FindDlg(mainFrame, self)
        dlg.ShowModal()
        dlg.saveState()
        dlg.Destroy()

        self.sp.clearMark()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnSpellCheckerDlg(self):
        self.sp.clearMark()
        self.clearAutoComp()

        wasAtStart = self.sp.line == 0

        wx.BeginBusyCursor()

        if not spellcheck.loadDict(mainFrame):
            wx.EndBusyCursor()

            return

        sc = spellcheck.SpellChecker(self.sp, gd.scDict)
        found = sc.findNext()

        wx.EndBusyCursor()

        if not found:
            s = ""

            if not wasAtStart:
                s = "\n\n(Starting position was not at\n"\
                    "the beginning of the script.)"
            wx.MessageBox("Spell checker found no errors." + s, "Results",
                          wx.OK, mainFrame)

            return

        dlg = spellcheckdlg.SpellCheckDlg(mainFrame, self, sc, gd.scDict)
        dlg.ShowModal()

        if dlg.changedGlobalDict:
            gd.saveScDict()

        dlg.Destroy()

        self.sp.clearMark()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnDeleteElements(self):
        # even though Screenplay.removeElementTypes does this as well, do
        # it here so that screen is cleared from the auto-comp box before
        # we open the dialog
        self.clearAutoComp()

        types = []
        for t in config.getTIs():
            types.append(misc.CheckBoxItem(t.name, False, t.lt))

        dlg = misc.CheckBoxDlg(mainFrame, "Delete elements", types,
                               "Element types to delete:", True)

        ok = False
        if dlg.ShowModal() == wx.ID_OK:
            ok = True

            tdict = misc.CheckBoxItem.getClientData(types)

        dlg.Destroy()

        if not ok or (len(tdict) == 0):
            return

        self.sp.removeElementTypes(tdict, True)
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnSave(self):
        if self.fileName:
            self.saveFile(self.fileName)
        else:
            self.OnSaveScriptAs()

    def OnSaveScriptAs(self):
        if self.fileName:
            dDir = os.path.dirname(self.fileName)
            dFile = os.path.basename(self.fileName)
        else:
            dDir = misc.scriptDir
            dFile = ""

        dlg = wx.FileDialog(mainFrame, "Filename to save as",
            defaultDir = dDir,
            defaultFile = dFile,
            wildcard = "Trelby files (*.trelby)|*.trelby|All files|*",
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnExportScript(self):
        sp = self.getExportable("export")
        if not sp:
            return

        dlg = wx.FileDialog(mainFrame, "Filename to export as",
            misc.scriptDir,
            wildcard = "PDF|*.pdf|"
                       "RTF|*.rtf|"
                       "Final Draft XML|*.fdx|"
                       "HTML|*.html|"
                       "Fountain|*.fountain|"
                       "Formatted text|*.txt",
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()

            choice = dlg.GetFilterIndex()
            if choice == 0:
                data = sp.generatePDF(True)
                suffix = ".pdf"
            elif choice == 1:
                data = sp.generateRTF()
                suffix = ".rtf"
            elif choice == 2:
                data = sp.generateFDX()
                suffix = ".fdx"
            elif choice == 3:
                data = self.getExportHtml(sp)
                suffix = ".html"
            elif choice == 4:
                data = sp.generateFountain()
                suffix = ".fountain"
            else:
                data = self.getExportText(sp)
                suffix = ".txt"

            fileName = util.ensureEndsIn(dlg.GetPath(), suffix)

            if data:
                util.writeToFile(fileName, data, mainFrame)

        dlg.Destroy()

    def OnPrint(self):
        sp = self.getExportable("print")
        if not sp:
            return

        s = sp.generatePDF(False)
        gutil.showTempPDF(s, cfgGl, mainFrame)

    def OnSettings(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(cfgGl),
                            self.applyGlobalCfg, True)

        if dlg.ShowModal() == wx.ID_OK:
            self.applyGlobalCfg(dlg.cfg)

        dlg.Destroy()

    def OnScriptSettings(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(self.sp.cfg),
                            self.applyCfg, False)

        if dlg.ShowModal() == wx.ID_OK:
            self.applyCfg(dlg.cfg)

        dlg.Destroy()

    def cmdAbort(self, cs):
        self.sp.abortCmd(cs)

    def cmdChangeToAction(self, cs):
        self.sp.toActionCmd(cs)

    def cmdChangeToCharacter(self, cs):
        self.sp.toCharacterCmd(cs)

    def cmdChangeToDialogue(self, cs):
        self.sp.toDialogueCmd(cs)

    def cmdChangeToNote(self, cs):
        self.sp.toNoteCmd(cs)

    def cmdChangeToParenthetical(self, cs):
        self.sp.toParenCmd(cs)

    def cmdChangeToScene(self, cs):
        self.sp.toSceneCmd(cs)

    def cmdChangeToShot(self, cs):
        self.sp.toShotCmd(cs)

    def cmdChangeToActBreak(self,cs):
        self.sp.toActBreakCmd(cs)

    def cmdChangeToTransition(self, cs):
        self.sp.toTransitionCmd(cs)

    def cmdDelete(self, cs):
        if not self.sp.mark:
            self.sp.deleteForwardCmd(cs)
        else:
            self.OnCut(doUpdate = False, copyToClip = False)

    def cmdDeleteBackward(self, cs):
        if not self.sp.mark:
            self.sp.deleteBackwardCmd(cs)
        else:
            self.OnCut(doUpdate = False, copyToClip = False)

    def cmdForcedLineBreak(self, cs):
        self.sp.insertForcedLineBreakCmd(cs)

    def cmdMoveDown(self, cs):
        self.sp.moveDownCmd(cs)

    def cmdMoveEndOfLine(self, cs):
        self.sp.moveLineEndCmd(cs)

    def cmdMoveEndOfScript(self, cs):
        self.sp.moveEndCmd(cs)

    def cmdMoveLeft(self, cs):
        self.sp.moveLeftCmd(cs)

    def cmdMovePageDown(self, cs):
        self.pageCmd(cs, 1)

    def cmdMovePageUp(self, cs):
        self.pageCmd(cs, -1)

    def cmdMoveRight(self, cs):
        self.sp.moveRightCmd(cs)

    def cmdMoveSceneDown(self, cs):
        self.sp.moveSceneDownCmd(cs)

    def cmdMoveSceneUp(self, cs):
        self.sp.moveSceneUpCmd(cs)

    def cmdMoveStartOfLine(self, cs):
        self.sp.moveLineStartCmd(cs)

    def cmdMoveStartOfScript(self, cs):
        self.sp.moveStartCmd(cs)

    def cmdMoveUp(self, cs):
        self.sp.moveUpCmd(cs)

    def cmdNewElement(self, cs):
        self.sp.splitElementCmd(cs)

    def cmdSetMark(self, cs):
        self.sp.setMarkCmd(cs)

    def cmdTab(self, cs):
        self.sp.tabCmd(cs)

    def cmdTabPrev(self, cs):
        self.sp.toPrevTypeTabCmd(cs)

    def cmdSpeedTest(self, cs):
        import undo
        self.speedTestUndo = []

        def testUndoFullCopy():
            u = undo.FullCopy(self.sp)
            u.setAfter(self.sp)
            self.speedTestUndo.append(u)

        def testReformatAll():
            self.sp.reformatAll()

        def testPaginate():
            self.sp.paginate()

        def testUpdateScreen():
            self.updateScreen()
            self.Update()

        def testAddRemoveChar():
            self.OnKeyChar(util.MyKeyEvent(ord("a")))
            self.OnKeyChar(util.MyKeyEvent(wx.WXK_BACK))

        def testDeepcopy():
            copy.deepcopy(self.sp)

        # contains (name, func) tuples
        tests = []

        for name, var in locals().items():
            if callable(var):
                tests.append((name, var))

        tests.sort()
        count = 100

        print(("-" * 20))

        for name, func in tests:
            t = time.time()

            for i in range(count):
                func()

            t = time.time() - t

            print("%.5f seconds per %s" % (t / count, name))

        print("-" * 20)

        # it's annoying having the program ask if you want to save after
        # running these tests, so pretend the script hasn't changed
        self.sp.markChanged(False)

    def cmdTest(self, cs):
        pass

    def OnKeyChar(self, ev):
        kc = ev.GetKeyCode()

        cs = screenplay.CommandState()
        cs.mark = bool(ev.ShiftDown())
        scrollDirection = config.SCROLL_CENTER

        if not ev.ControlDown() and not ev.AltDown() and \
               util.isValidInputChar(kc):
            # WX2.6-FIXME: we should probably use GetUnicodeKey() (dunno
            # how to get around the isValidInputChar test in the preceding
            # line, need to test what GetUnicodeKey() returns on
            # non-input-character events)

            addChar = True

            # If there's something selected, either remove it, or clear selection.
            if self.sp.mark and cfgGl.overwriteSelectionOnInsert:
                if not self.OnCut(doUpdate = False, copyToClip = False):
                    self.sp.clearMark()
                    addChar = False

            if addChar:
                cs.char = chr(kc)

                if opts.isTest and (cs.char == "å"):
                    self.loadFile("sample.trelby")
                elif opts.isTest and (cs.char == "¤"):
                    self.cmdTest(cs)
                elif opts.isTest and (cs.char == "½"):
                    self.cmdSpeedTest(cs)
                else:
                    self.sp.addCharCmd(cs)

        else:
            cmd = mainFrame.kbdCommands.get(util.Key(kc,
                ev.ControlDown(), ev.AltDown(), ev.ShiftDown()).toInt())

            if cmd:
                scrollDirection = cmd.scrollDirection
                if cmd.isMenu:
                    getattr(mainFrame, "On" + cmd.name)()
                    return
                else:
                    getattr(self, "cmd" + cmd.name)(cs)
            else:
                ev.Skip()
                return

        self.sp.cmdPost(cs)

        if cfgGl.paginateInterval > 0:
            now = time.time()

            if (now - self.sp.lastPaginated) >= cfgGl.paginateInterval:
                self.sp.paginate()

                cs.needsVisifying = True

        if cs.needsVisifying:
            self.makeLineVisible(self.sp.line, scrollDirection)

        self.updateScreen()

    def OnPaint(self, event):
        #ldkjfldsj = util.TimerDev("paint")

        ls = self.sp.lines

        if misc.doDblBuf:
            dc = wx.BufferedPaintDC(self, self.screenBuf)
        else:
            dc = wx.PaintDC(self)

        size = self.GetClientSize()
        marked = self.sp.getMarkedLines()
        lineh = gd.vm.getLineHeight(self)
        posX = -1
        cursorY = -1

        # auto-comp FontInfo
        acFi = None

        # key = font, value = ([text, ...], [(x, y), ...], [wx.Colour, ...])
        texts = []

        # lists of underline-lines to draw, one for normal text and one
        # for header texts. list objects are (x, y, width) tuples.
        ulines = []
        ulinesHdr = []

        strings, dpages = gd.vm.getScreen(self, True, True)

        dc.SetBrush(cfgGui.workspaceBrush)
        dc.SetPen(cfgGui.workspacePen)
        dc.DrawRectangle(0, 0, size.width, size.height)

        dc.SetPen(cfgGui.tabBorderPen)
        dc.DrawLine(0,0,0,size.height)

        if not dpages:
            # draft mode; draw an infinite page
            lx = util.clamp((size.width - self.pageW) // 2, 0)
            rx = lx + self.pageW

            dc.SetBrush(cfgGui.textBgBrush)
            dc.SetPen(cfgGui.textBgPen)
            dc.DrawRectangle(lx, 5, self.pageW, size.height - 5)

            dc.SetPen(cfgGui.pageBorderPen)
            dc.DrawLine(lx, 5, lx, size.height)
            dc.DrawLine(rx, 5, rx, size.height)

        else:
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

                if l.lt == screenplay.NOTE:
                    dc.SetPen(cfgGui.notePen)
                    dc.SetBrush(cfgGui.noteBrush)

                    nx = t.x - 5
                    nw = self.sp.cfg.getType(l.lt).width * fx + 10

                    dc.DrawRectangle(nx, y, nw, lineh)

                    dc.SetPen(cfgGui.textPen)
                    util.drawLine(dc, nx - 1, y, 0, lineh)
                    util.drawLine(dc, nx + nw, y, 0, lineh)

                    if self.sp.isFirstLineOfElem(i):
                        util.drawLine(dc, nx - 1, y - 1, nw + 2, 0)

                    if self.sp.isLastLineOfElem(i):
                        util.drawLine(dc, nx - 1, y + lineh,
                                      nw + 2, 0)

                if marked and self.sp.isLineMarked(i, marked):
                    c1, c2 = self.sp.getMarkedColumns(i, marked)

                    dc.SetPen(cfgGui.selectedPen)
                    dc.SetBrush(cfgGui.selectedBrush)

                    dc.DrawRectangle(t.x + c1 * fx, y, (c2 - c1 + 1) * fx,
                        lineh)

                if mainFrame.showFormatting:
                    dc.SetPen(cfgGui.bluePen)
                    util.drawLine(dc, t.x, y, 0, lineh)

                    extraIndent = 1 if self.sp.needsExtraParenIndent(i) else 0

                    util.drawLine(dc,
                        t.x + (self.sp.cfg.getType(l.lt).width - extraIndent) * fx,
                        y, 0, lineh)

                    dc.SetTextForeground(cfgGui.redColor)
                    dc.SetFont(cfgGui.fonts[pml.NORMAL].font)
                    dc.DrawText(config.lb2char(l.lb), t.x - 10, y)

                if not dpages:
                    if cfgGl.pbi == config.PBI_REAL_AND_UNADJ:
                        if self.sp.line2pageNoAdjust(i) != \
                               self.sp.line2pageNoAdjust(i + 1):
                            dc.SetPen(cfgGui.pagebreakNoAdjustPen)
                            util.drawLine(dc, 0, y + lineh - 1,
                                size.width, 0)

                    if cfgGl.pbi in (config.PBI_REAL,
                                   config.PBI_REAL_AND_UNADJ):
                        thisPage = self.sp.line2page(i)

                        if thisPage != self.sp.line2page(i + 1):
                            dc.SetPen(cfgGui.pagebreakPen)
                            util.drawLine(dc, 0, y + lineh - 1,
                                size.width, 0)

                if i == self.sp.line:
                    posX = t.x
                    cursorY = y
                    acFi = fi
                    dc.SetPen(cfgGui.cursorPen)
                    dc.SetBrush(cfgGui.cursorBrush)
                    dc.DrawRectangle(t.x + self.sp.column * fx, y, fx, fi.fy)

            if len(t.text) != 0:
                #tl = texts.get(fi.font)
                if fi.font not in texts:
                #if tl == None:
                    tl = ([], [], [])
                    texts.append((fi.font, tl))

                tl[0].append(t.text)
                tl[1].append((t.x, y))
                if t.line != -1:
                    if cfgGl.useCustomElemColors:
                        tl[2].append(cfgGui.lt2textColor(ls[t.line].lt))
                    else:
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

        for tl in texts:
            gd.vm.drawTexts(self, dc, tl)

        if self.sp.acItems and (cursorY > 0):
            self.drawAutoComp(dc, posX, cursorY, acFi)

    def drawAutoComp(self, dc, posX, cursorY, fi):
        ac = self.sp.acItems
        asel = self.sp.acSel

        offset = 5
        selBleed = 2

        # scroll bar width
        sbw = 10

        size = self.GetClientSize()

        dc.SetFont(fi.font)

        show = min(self.sp.acMax, len(ac))
        doSbw = show < len(ac)

        startPos = (asel // show) * show
        endPos = min(startPos + show, len(ac))
        if endPos == len(ac):
            startPos = max(0, endPos - show)

        w = 0
        for i in range(len(ac)):
            tw = dc.GetTextExtent(ac[i])[0]
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
            if i == asel:
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

            dc.DrawText(ac[i], posX + offset, posY + offset +
                        (i - startPos) * fi.fy)

            if i == asel:
                dc.SetTextForeground(cfgGui.autoCompFgColor)

        if doSbw:
            dc.SetPen(cfgGui.autoCompPen)
            dc.SetBrush(cfgGui.autoCompRevBrush)
            util.drawLine(dc, posX + w - offset * 2 - sbw,
                posY, 0, h)
            dc.DrawRectangle(posX + w - offset - sbw,
                posY + offset - selBleed + int((float(startPos) /
                     len(ac)) * sbh),
                sbw, int((float(show) / len(ac)) * sbh))

class MyFrame(wx.Frame):

    def __init__(self, parent, id, title):
        wx.Frame.__init__(self, parent, id, title, name = "Trelby")

        if misc.isUnix:
            # automatically reaps zombies
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)

        self.clipboard = None
        self.showFormatting = False

        self.SetSizeHints(gd.cvars.getMin("width"),
                          gd.cvars.getMin("height"))

        self.Move(gd.posX, gd.posY)
        self.SetSize(wx.Size(gd.width, gd.height))

        util.removeTempFiles(misc.tmpPrefix)

        self.mySetIcons()
        self.allocIds()

        fileMenu = wx.Menu()
        fileMenu.Append(ID_FILE_NEW, "&New\tCTRL-N")
        fileMenu.Append(ID_FILE_OPEN, "&Open...\tCTRL-O")
        fileMenu.Append(ID_FILE_SAVE, "&Save\tCTRL-S")
        fileMenu.Append(ID_FILE_SAVE_AS, "Save &As...")
        fileMenu.Append(ID_FILE_CLOSE, "&Close\tCTRL-W")
        fileMenu.Append(ID_FILE_REVERT, "&Revert")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_IMPORT, "&Import...")
        fileMenu.Append(ID_FILE_EXPORT, "&Export...")
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_PRINT, "&Print (via PDF)\tCTRL-P")
        fileMenu.AppendSeparator()

        tmp = wx.Menu()

        tmp.Append(ID_SETTINGS_CHANGE, "&Change...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_LOAD, "Load...")
        tmp.Append(ID_SETTINGS_SAVE_AS, "Save as...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_SC_DICT, "&Spell checker dictionary...")
        settingsMenu = tmp

        fileMenu.Append(ID_FILE_SETTINGS, "Se&ttings", tmp)

        fileMenu.AppendSeparator()
        # "most recently used" list comes in here
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_EXIT, "E&xit\tCTRL-Q")

        editMenu = wx.Menu()
        editMenu.Append(ID_EDIT_UNDO, "&Undo\tCTRL-Z")
        editMenu.Append(ID_EDIT_REDO, "&Redo\tCTRL-Y")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_CUT, "Cu&t\tCTRL-X")
        editMenu.Append(ID_EDIT_COPY, "&Copy\tCTRL-C")
        editMenu.Append(ID_EDIT_PASTE, "&Paste\tCTRL-V")
        editMenu.AppendSeparator()

        tmp = wx.Menu()
        tmp.Append(ID_EDIT_COPY_TO_CB, "&Unformatted")
        tmp.Append(ID_EDIT_COPY_TO_CB_FMT, "&Formatted")

        editMenu.Append(ID_EDIT_COPY_SYSTEM, "C&opy (system)", tmp)
        editMenu.Append(ID_EDIT_PASTE_FROM_CB, "P&aste (system)")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_SELECT_SCENE, "&Select scene")
        editMenu.Append(ID_EDIT_SELECT_ALL, "Select a&ll")
        editMenu.Append(ID_EDIT_GOTO_PAGE, "&Goto page...\tCTRL-G")
        editMenu.Append(ID_EDIT_GOTO_SCENE, "Goto sc&ene...\tALT-G")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_INSERT_NBSP, "Insert non-breaking space")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_FIND, "&Find && Replace...\tCTRL-F")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_DELETE_ELEMENTS, "&Delete elements...")

        viewMenu = wx.Menu()
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_DRAFT, "&Draft")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_LAYOUT, "&Layout")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_SIDE_BY_SIDE, "&Side by side")

        if gd.viewMode == VIEWMODE_DRAFT:
            viewMenu.Check(ID_VIEW_STYLE_DRAFT, True)
        elif gd.viewMode == VIEWMODE_LAYOUT:
            viewMenu.Check(ID_VIEW_STYLE_LAYOUT, True)
        else:
            viewMenu.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)

        viewMenu.AppendSeparator()
        viewMenu.AppendCheckItem(ID_VIEW_SHOW_FORMATTING, "&Show formatting")
        viewMenu.Append(ID_VIEW_FULL_SCREEN, "&Fullscreen\tF11")

        scriptMenu = wx.Menu()
        scriptMenu.Append(ID_SCRIPT_FIND_ERROR, "&Find next error")
        scriptMenu.Append(ID_SCRIPT_PAGINATE, "&Paginate")
        scriptMenu.AppendSeparator()
        scriptMenu.Append(ID_SCRIPT_AUTO_COMPLETION, "&Auto-completion...")
        scriptMenu.Append(ID_SCRIPT_HEADERS, "&Headers...")
        scriptMenu.Append(ID_SCRIPT_LOCATIONS, "&Locations...")
        scriptMenu.Append(ID_SCRIPT_TITLES, "&Title pages...")
        scriptMenu.Append(ID_SCRIPT_SC_DICT, "&Spell checker dictionary...")
        scriptMenu.AppendSeparator()

        tmp = wx.Menu()

        tmp.Append(ID_SCRIPT_SETTINGS_CHANGE, "&Change...")
        tmp.AppendSeparator()
        tmp.Append(ID_SCRIPT_SETTINGS_LOAD, "&Load...")
        tmp.Append(ID_SCRIPT_SETTINGS_SAVE_AS, "&Save as...")
        scriptMenu.Append(ID_SCRIPT_SETTINGS, "&Settings", tmp)
        scriptSettingsMenu = tmp

        reportsMenu = wx.Menu()
        reportsMenu.Append(ID_REPORTS_SCRIPT_REP, "Sc&ript report")
        reportsMenu.Append(ID_REPORTS_LOCATION_REP, "&Location report...")
        reportsMenu.Append(ID_REPORTS_SCENE_REP, "&Scene report...")
        reportsMenu.Append(ID_REPORTS_CHARACTER_REP, "&Character report...")
        reportsMenu.Append(ID_REPORTS_DIALOGUE_CHART, "&Dialogue chart...")

        toolsMenu = wx.Menu()
        toolsMenu.Append(ID_TOOLS_SPELL_CHECK, "&Spell checker...")
        toolsMenu.Append(ID_TOOLS_NAME_DB, "&Name database...")
        toolsMenu.Append(ID_TOOLS_CHARMAP, "&Character map...")
        toolsMenu.Append(ID_TOOLS_COMPARE_SCRIPTS, "C&ompare scripts...")
        toolsMenu.Append(ID_TOOLS_WATERMARK, "&Generate watermarked PDFs...")

        helpMenu = wx.Menu()
        helpMenu.Append(ID_HELP_COMMANDS, "&Commands...")
        helpMenu.Append(ID_HELP_MANUAL, "&Manual")
        helpMenu.AppendSeparator()
        helpMenu.Append(ID_HELP_ABOUT, "&About...")

        self.menuBar = wx.MenuBar()
        self.menuBar.Append(fileMenu, "&File")
        self.menuBar.Append(editMenu, "&Edit")
        self.menuBar.Append(viewMenu, "&View")
        self.menuBar.Append(scriptMenu, "Scr&ipt")
        self.menuBar.Append(reportsMenu, "&Reports")
        self.menuBar.Append(toolsMenu, "Too&ls")
        self.menuBar.Append(helpMenu, "&Help")
        self.SetMenuBar(self.menuBar)

        self.toolBar = self.CreateToolBar(wx.TB_VERTICAL)

        def addTB(id, iconFilename, toolTip):
            self.toolBar.AddTool(
                id, "", misc.getBitmap("resources/%s" % iconFilename),
                shortHelp=toolTip)

        addTB(ID_FILE_NEW, "new.png", "New script")
        addTB(ID_FILE_OPEN, "open.png", "Open Script..")
        addTB(ID_FILE_SAVE, "save.png", "Save..")
        addTB(ID_FILE_SAVE_AS, "saveas.png", "Save as..")
        addTB(ID_FILE_CLOSE, "close.png", "Close Script")
        addTB(ID_TOOLBAR_SCRIPTSETTINGS, "scrset.png", "Script settings")
        addTB(ID_FILE_PRINT, "pdf.png", "Print (via PDF)")

        self.toolBar.AddSeparator()

        addTB(ID_FILE_IMPORT, "import.png", "Import a text script")
        addTB(ID_FILE_EXPORT, "export.png", "Export script")

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_UNDO, "undo.png", "Undo")
        addTB(ID_EDIT_REDO, "redo.png", "Redo")

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_FIND, "find.png", "Find / Replace")
        addTB(ID_TOOLBAR_VIEWS, "layout.png", "View mode")
        addTB(ID_TOOLBAR_REPORTS, "report.png", "Script reports")
        addTB(ID_TOOLBAR_TOOLS, "tools.png", "Tools")
        addTB(ID_TOOLBAR_SETTINGS, "settings.png", "Global settings")

        self.toolBar.SetBackgroundColour(cfgGui.tabBarBgColor)
        self.toolBar.Realize()

        self.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vsizer)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.noFSBtn = misc.MyFSButton(self, -1, getCfgGui)
        self.noFSBtn.SetToolTip("Exit fullscreen")
        self.noFSBtn.Show(False)
        hsizer.Add(self.noFSBtn)

        self.Bind(wx.EVT_BUTTON, self.ToggleFullscreen, id=self.noFSBtn.GetId())

        self.tabCtrl = misc.MyTabCtrl(self, -1, getCfgGui)
        hsizer.Add(self.tabCtrl, 1, wx.EXPAND)

        self.statusCtrl = misc.MyStatus(self, -1, getCfgGui)
        hsizer.Add(self.statusCtrl)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        tmp = misc.MyTabCtrl2(self, -1, self.tabCtrl)
        vsizer.Add(tmp, 1, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND)


        gd.mru.useMenu(fileMenu, 14)

        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnMenuHighlight)

        self.tabCtrl.setPageChangedFunc(self.OnPageChange)

        # see OnRightDown
        self.rightClickMenu = wx.Menu()
        self.rightClickMenuWithCut = wx.Menu()

        for m in (self.rightClickMenu, self.rightClickMenuWithCut):
            tmp = wx.Menu()

            tmp.Append(ID_ELEM_TO_SCENE, "&Scene")
            tmp.Append(ID_ELEM_TO_ACTION, "&Action")
            tmp.Append(ID_ELEM_TO_CHARACTER, "&Character")
            tmp.Append(ID_ELEM_TO_PAREN, "&Parenthetical")
            tmp.Append(ID_ELEM_TO_DIALOGUE, "&Dialogue")
            tmp.Append(ID_ELEM_TO_TRANSITION, "&Transition")
            tmp.Append(ID_ELEM_TO_SHOT, "Sh&ot")
            tmp.Append(ID_ELEM_TO_ACTBREAK, "Act &break")
            tmp.Append(ID_ELEM_TO_NOTE, "&Note")

            m.AppendSubMenu(tmp, "Element type")
            m.AppendSeparator()

            if m is self.rightClickMenuWithCut:
                m.Append(ID_EDIT_CUT, "Cut")
                m.Append(ID_EDIT_COPY, "Copy")

            m.Append(ID_EDIT_PASTE, "Paste")

            self.Bind(wx.EVT_MENU, self.OnNewScript, id=ID_FILE_NEW)
            self.Bind(wx.EVT_MENU, self.OnOpen, id=ID_FILE_OPEN)
            self.Bind(wx.EVT_MENU, self.OnSave, id=ID_FILE_SAVE)
            self.Bind(wx.EVT_MENU, self.OnSaveScriptAs, id=ID_FILE_SAVE_AS)
            self.Bind(wx.EVT_MENU, self.OnImportScript, id=ID_FILE_IMPORT)
            self.Bind(wx.EVT_MENU, self.OnExportScript, id=ID_FILE_EXPORT)
            self.Bind(wx.EVT_MENU, self.OnCloseScript, id=ID_FILE_CLOSE)
            self.Bind(wx.EVT_MENU, self.OnRevertScript, id=ID_FILE_REVERT)
            self.Bind(wx.EVT_MENU, self.OnPrint, id=ID_FILE_PRINT)
            self.Bind(wx.EVT_MENU, self.OnSettings, id=ID_SETTINGS_CHANGE)
            self.Bind(wx.EVT_MENU, self.OnLoadSettings, id=ID_SETTINGS_LOAD)
            self.Bind(wx.EVT_MENU, self.OnSaveSettingsAs, id=ID_SETTINGS_SAVE_AS)
            self.Bind(wx.EVT_MENU, self.OnSpellCheckerDictionaryDlg, id=ID_SETTINGS_SC_DICT)
            self.Bind(wx.EVT_MENU, self.OnExit, id=ID_FILE_EXIT)
            self.Bind(wx.EVT_MENU, self.OnUndo, id=ID_EDIT_UNDO)
            self.Bind(wx.EVT_MENU, self.OnRedo, id=ID_EDIT_REDO)
            self.Bind(wx.EVT_MENU, self.OnCut, id=ID_EDIT_CUT)
            self.Bind(wx.EVT_MENU, self.OnCopy, id=ID_EDIT_COPY)
            self.Bind(wx.EVT_MENU, self.OnPaste, id=ID_EDIT_PASTE)
            self.Bind(wx.EVT_MENU, self.OnCopySystemCb, id=ID_EDIT_COPY_TO_CB)
            self.Bind(wx.EVT_MENU, self.OnCopySystemCbFormatted, id=ID_EDIT_COPY_TO_CB_FMT)
            self.Bind(wx.EVT_MENU, self.OnPasteSystemCb, id=ID_EDIT_PASTE_FROM_CB)
            self.Bind(wx.EVT_MENU, self.OnSelectScene, id=ID_EDIT_SELECT_SCENE)
            self.Bind(wx.EVT_MENU, self.OnSelectAll, id=ID_EDIT_SELECT_ALL)
            self.Bind(wx.EVT_MENU, self.OnGotoPage, id=ID_EDIT_GOTO_PAGE)
            self.Bind(wx.EVT_MENU, self.OnGotoScene, id=ID_EDIT_GOTO_SCENE)
            self.Bind(wx.EVT_MENU, self.OnInsertNbsp, id=ID_EDIT_INSERT_NBSP)
            self.Bind(wx.EVT_MENU, self.OnFind, id=ID_EDIT_FIND)
            self.Bind(wx.EVT_MENU, self.OnDeleteElements, id=ID_EDIT_DELETE_ELEMENTS)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_DRAFT)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_LAYOUT)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_SIDE_BY_SIDE)
            self.Bind(wx.EVT_MENU, self.OnShowFormatting, id=ID_VIEW_SHOW_FORMATTING)
            self.Bind(wx.EVT_MENU, self.ToggleFullscreen, id=ID_VIEW_FULL_SCREEN)
            self.Bind(wx.EVT_MENU, self.OnFindNextError, id=ID_SCRIPT_FIND_ERROR)
            self.Bind(wx.EVT_MENU, self.OnPaginate, id=ID_SCRIPT_PAGINATE)
            self.Bind(wx.EVT_MENU, self.OnAutoCompletionDlg, id=ID_SCRIPT_AUTO_COMPLETION)
            self.Bind(wx.EVT_MENU, self.OnHeadersDlg, id=ID_SCRIPT_HEADERS)
            self.Bind(wx.EVT_MENU, self.OnLocationsDlg, id=ID_SCRIPT_LOCATIONS)
            self.Bind(wx.EVT_MENU, self.OnTitlesDlg, id=ID_SCRIPT_TITLES)
            self.Bind(wx.EVT_MENU, self.OnSpellCheckerScriptDictionaryDlg, id=ID_SCRIPT_SC_DICT)
            self.Bind(wx.EVT_MENU, self.OnScriptSettings, id=ID_SCRIPT_SETTINGS_CHANGE)
            self.Bind(wx.EVT_MENU, self.OnLoadScriptSettings, id=ID_SCRIPT_SETTINGS_LOAD)
            self.Bind(wx.EVT_MENU, self.OnSaveScriptSettingsAs, id=ID_SCRIPT_SETTINGS_SAVE_AS)
            self.Bind(wx.EVT_MENU, self.OnReportDialogueChart, id=ID_REPORTS_DIALOGUE_CHART)
            self.Bind(wx.EVT_MENU, self.OnReportCharacter, id=ID_REPORTS_CHARACTER_REP)
            self.Bind(wx.EVT_MENU, self.OnReportScript, id=ID_REPORTS_SCRIPT_REP)
            self.Bind(wx.EVT_MENU, self.OnReportLocation, id=ID_REPORTS_LOCATION_REP)
            self.Bind(wx.EVT_MENU, self.OnReportScene, id=ID_REPORTS_SCENE_REP)
            self.Bind(wx.EVT_MENU, self.OnSpellCheckerDlg, id=ID_TOOLS_SPELL_CHECK)
            self.Bind(wx.EVT_MENU, self.OnNameDatabase, id=ID_TOOLS_NAME_DB)
            self.Bind(wx.EVT_MENU, self.OnCharacterMap, id=ID_TOOLS_CHARMAP)
            self.Bind(wx.EVT_MENU, self.OnCompareScripts, id=ID_TOOLS_COMPARE_SCRIPTS)
            self.Bind(wx.EVT_MENU, self.OnWatermark, id=ID_TOOLS_WATERMARK)
            self.Bind(wx.EVT_MENU, self.OnHelpCommands, id=ID_HELP_COMMANDS)
            self.Bind(wx.EVT_MENU, self.OnHelpManual, id=ID_HELP_MANUAL)
            self.Bind(wx.EVT_MENU, self.OnAbout, id=ID_HELP_ABOUT)


        self.Bind(wx.EVT_MENU_RANGE, self.OnMRUFile, id=gd.mru.getIds()[0], id2=gd.mru.getIds()[1])

        self.Bind(wx.EVT_MENU_RANGE, self.OnChangeType, id=ID_ELEM_TO_ACTION, id2=ID_ELEM_TO_TRANSITION)

        def addTBMenu(id, menu):
            self.Bind(wx.EVT_MENU, partial(self.OnToolBarMenu, menu=menu), id=id)

        addTBMenu(ID_TOOLBAR_SETTINGS, settingsMenu)
        addTBMenu(ID_TOOLBAR_SCRIPTSETTINGS, scriptSettingsMenu)
        addTBMenu(ID_TOOLBAR_REPORTS, reportsMenu)
        addTBMenu(ID_TOOLBAR_VIEWS, viewMenu)
        addTBMenu(ID_TOOLBAR_TOOLS, toolsMenu)

        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)

        self.Layout()

    def init(self):
        self.updateKbdCommands()
        self.panel = self.createNewPanel()

    def mySetIcons(self):
        wx.Image.AddHandler(wx.PNGHandler())

        ib = wx.IconBundle()

        for sz in ("16", "32", "64", "128", "256"):
            ib.AddIcon(wx.Icon(misc.getBitmap("resources/icon%s.png" % sz)))

        self.SetIcons(ib)

    def allocIds(self):
        names = [
            "ID_EDIT_UNDO",
            "ID_EDIT_REDO",
            "ID_EDIT_COPY",
            "ID_EDIT_COPY_SYSTEM",
            "ID_EDIT_COPY_TO_CB",
            "ID_EDIT_COPY_TO_CB_FMT",
            "ID_EDIT_CUT",
            "ID_EDIT_DELETE_ELEMENTS",
            "ID_EDIT_FIND",
            "ID_EDIT_GOTO_SCENE",
            "ID_EDIT_GOTO_PAGE",
            "ID_EDIT_INSERT_NBSP",
            "ID_EDIT_PASTE",
            "ID_EDIT_PASTE_FROM_CB",
            "ID_EDIT_SELECT_ALL",
            "ID_EDIT_SELECT_SCENE",
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
            "ID_HELP_MANUAL",
            "ID_REPORTS_CHARACTER_REP",
            "ID_REPORTS_DIALOGUE_CHART",
            "ID_REPORTS_LOCATION_REP",
            "ID_REPORTS_SCENE_REP",
            "ID_REPORTS_SCRIPT_REP",
            "ID_SCRIPT_AUTO_COMPLETION",
            "ID_SCRIPT_FIND_ERROR",
            "ID_SCRIPT_HEADERS",
            "ID_SCRIPT_LOCATIONS",
            "ID_SCRIPT_PAGINATE",
            "ID_SCRIPT_SC_DICT",
            "ID_SCRIPT_SETTINGS",
            "ID_SCRIPT_SETTINGS_CHANGE",
            "ID_SCRIPT_SETTINGS_LOAD",
            "ID_SCRIPT_SETTINGS_SAVE_AS",
            "ID_SCRIPT_TITLES",
            "ID_SETTINGS_CHANGE",
            "ID_SETTINGS_LOAD",
            "ID_SETTINGS_SAVE_AS",
            "ID_SETTINGS_SC_DICT",
            "ID_TOOLS_CHARMAP",
            "ID_TOOLS_COMPARE_SCRIPTS",
            "ID_TOOLS_NAME_DB",
            "ID_TOOLS_SPELL_CHECK",
            "ID_TOOLS_WATERMARK",
            "ID_VIEW_SHOW_FORMATTING",
            "ID_VIEW_STYLE_DRAFT",
            "ID_VIEW_STYLE_LAYOUT",
            "ID_VIEW_STYLE_SIDE_BY_SIDE",
            "ID_TOOLBAR_SETTINGS",
            "ID_TOOLBAR_SCRIPTSETTINGS",
            "ID_TOOLBAR_REPORTS",
            "ID_TOOLBAR_VIEWS",
            "ID_TOOLBAR_TOOLS",
            "ID_VIEW_FULL_SCREEN",
            "ID_ELEM_TO_ACTION",
            "ID_ELEM_TO_CHARACTER",
            "ID_ELEM_TO_DIALOGUE",
            "ID_ELEM_TO_NOTE",
            "ID_ELEM_TO_PAREN",
            "ID_ELEM_TO_SCENE",
            "ID_ELEM_TO_SHOT",
            "ID_ELEM_TO_ACTBREAK",
            "ID_ELEM_TO_TRANSITION",
            ]

        g = globals()

        for n in names:
            g[n] = wx.NewId()

        # see OnChangeType
        g["idToLTMap"] = {
            ID_ELEM_TO_SCENE : screenplay.SCENE,
            ID_ELEM_TO_ACTION : screenplay.ACTION,
            ID_ELEM_TO_CHARACTER : screenplay.CHARACTER,
            ID_ELEM_TO_DIALOGUE : screenplay.DIALOGUE,
            ID_ELEM_TO_PAREN : screenplay.PAREN,
            ID_ELEM_TO_TRANSITION : screenplay.TRANSITION,
            ID_ELEM_TO_SHOT : screenplay.SHOT,
            ID_ELEM_TO_ACTBREAK : screenplay.ACTBREAK,
            ID_ELEM_TO_NOTE : screenplay.NOTE,
            }

    def createNewPanel(self):
        newPanel = MyPanel(self.tabCtrl.getTabParent(), -1)
        self.tabCtrl.addPage(newPanel, "")
        newPanel.ctrl.setTabText()
        newPanel.ctrl.SetFocus()

        return newPanel

    def setTitle(self, text):
        self.SetTitle("Trelby - %s" % text)

    def setTabText(self, panel, text):
        i = self.findPage(panel)

        if i != -1:
            # strip out ".trelby" suffix from tab names (it's a bit
            # complicated since if we open the same file multiple times,
            # we have e.g. "foo.trelby" and "foo.trelby<2>", so actually
            # we just strip out ".trelby" if it's found anywhere in the
            # string)

            s = text.replace(".trelby", "")
            self.tabCtrl.setTabText(i, s)

    # iterates over all tabs and finds out the corresponding page number
    # for the given panel.
    def findPage(self, panel):
        for i in range(self.tabCtrl.getPageCount()):
            p = self.tabCtrl.getPage(i)
            if p == panel:
                return i

        return -1

    # get list of MyCtrl objects for all open scripts
    def getCtrls(self):
        l = []

        for i in range(self.tabCtrl.getPageCount()):
            l.append(self.tabCtrl.getPage(i).ctrl)

        return l

    # returns True if any open script has been modified
    def isModifications(self):
        for c in self.getCtrls():
            if c.sp.isModified():
                return True

        return False

    def updateKbdCommands(self):
        cfgGl.addShiftKeys()

        if cfgGl.getConflictingKeys() != None:
            wx.MessageBox("You have at least one key bound to more than one\n"
                          "command. The program will not work correctly until\n"
                          "you fix this.",
                          "Warning", wx.OK, self)

        self.kbdCommands = {}

        for cmd in cfgGl.commands:
            if not (cmd.isFixed and cmd.isMenu):
                for key in cmd.keys:
                    self.kbdCommands[key] = cmd

    # open script, in the current tab if it's untouched, or in a new one
    # otherwise
    def openScript(self, filename):
        if not self.tabCtrl.getPage(self.findPage(self.panel))\
               .ctrl.isUntouched():
            self.panel = self.createNewPanel()

        self.panel.ctrl.loadFile(filename)
        self.panel.ctrl.updateScreen()
        gd.mru.add(filename)

    def checkFonts(self):
        names = ["Normal", "Bold", "Italic", "Bold-Italic"]
        failed = []

        for i, fi in enumerate(cfgGui.fonts):
            if not util.isFixedWidth(fi.font):
                failed.append(names[i])

        if failed:
            wx.MessageBox(
                "The fonts listed below are not fixed width and\n"
                "will cause the program not to function correctly.\n"
                "Please change the fonts at File/Settings/Change.\n\n"
                + "\n".join(failed), "Error", wx.OK, self)

    # If we get focus, pass it on to ctrl.
    def OnFocus(self, event):
        self.panel.ctrl.SetFocus()

    def OnMenuHighlight(self, event):
        # default implementation modifies status bar, so we need to
        # override it and do nothing
        pass

    def OnPageChange(self, page):
        self.panel = self.tabCtrl.getPage(page)
        self.panel.ctrl.SetFocus()
        self.panel.ctrl.updateCommon()
        self.setTitle(self.panel.ctrl.fileNameDisplay)

    def selectScript(self, toNext):
        current = self.tabCtrl.getSelectedPageIndex()
        pageCnt = self.tabCtrl.getPageCount()

        if toNext:
            pageNr = current + 1
        else:
            pageNr = current - 1

        if pageNr == -1:
            pageNr = pageCnt - 1
        elif pageNr == pageCnt:
            pageNr = 0

        if pageNr == current:
            # only one tab, nothing to do
            return

        self.tabCtrl.selectPage(pageNr)

    def OnScriptNext(self, event = None):
        self.selectScript(True)

    def OnScriptPrev(self, event = None):
        self.selectScript(False)

    def OnNewScript(self, event = None):
        self.panel = self.createNewPanel()

    def OnMRUFile(self, event):
        i = event.GetId() - gd.mru.getIds()[0]
        self.openScript(gd.mru.get(i))

    def OnOpen(self, event = None):
        dlg = wx.FileDialog(self, "File to open",
            misc.scriptDir,
            wildcard = "Trelby files (*.trelby)|*.trelby|All files|*",
            style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()
            self.openScript(dlg.GetPath())

        dlg.Destroy()

    def OnSave(self, event = None):
        self.panel.ctrl.OnSave()

    def OnSaveScriptAs(self, event = None):
        self.panel.ctrl.OnSaveScriptAs()

    def OnImportScript(self, event = None):
        dlg = wx.FileDialog(self, "File to import",
            misc.scriptDir,
            wildcard = "Importable files (*.txt;*.fdx;*.celtx;*.astx;*.fountain;*.fadein)|" +
                       "*.fdx;*.txt;*.celtx;*.astx;*.fountain;*.fadein|" +
                       "Formatted text files (*.txt)|*.txt|" +
                       "Final Draft XML(*.fdx)|*.fdx|" +
                       "Celtx files (*.celtx)|*.celtx|" +
                       "Adobe Story XML files (*.astx)|*.astx|" +
                       "Fountain files (*.fountain)|*.fountain|" +
                       "Fadein files (*.fadein)|*.fadein|" +
                       "All files|*",
            style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()

            if not self.tabCtrl.getPage(self.findPage(self.panel))\
                   .ctrl.isUntouched():
                self.panel = self.createNewPanel()

            self.panel.ctrl.importFile(dlg.GetPath())
            self.panel.ctrl.updateScreen()

        dlg.Destroy()

    def OnExportScript(self, event = None):
        self.panel.ctrl.OnExportScript()

    def OnCloseScript(self, event = None):
        if not self.panel.ctrl.canBeClosed():
            return

        if self.tabCtrl.getPageCount() > 1:
            self.tabCtrl.deletePage(self.tabCtrl.getSelectedPageIndex())
        else:
            self.panel.ctrl.createEmptySp()
            self.panel.ctrl.updateScreen()

    def OnRevertScript(self, event = None):
        self.panel.ctrl.OnRevertScript()

    def OnPrint(self, event = None):
        self.panel.ctrl.OnPrint()

    def OnSettings(self, event = None):
        self.panel.ctrl.OnSettings()

    def OnLoadSettings(self, event = None):
        dlg = wx.FileDialog(self, "File to open",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                c = config.ConfigGlobal()
                c.load(s)
                gd.confFilename = dlg.GetPath()

                self.panel.ctrl.applyGlobalCfg(c, False)

        dlg.Destroy()

    def OnSaveSettingsAs(self, event = None):
        dlg = wx.FileDialog(self, "Filename to save as",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), cfgGl.save(), self):
                gd.confFilename = dlg.GetPath()

        dlg.Destroy()

    def OnUndo(self, event = None):
        self.panel.ctrl.OnUndo()

    def OnRedo(self, event = None):
        self.panel.ctrl.OnRedo()

    def OnCut(self, event = None):
        self.panel.ctrl.OnCut()

    def OnCopy(self, event = None):
        self.panel.ctrl.OnCopy()

    def OnCopySystemCb(self, event = None):
        self.panel.ctrl.OnCopySystem(formatted = False)

    def OnCopySystemCbFormatted(self, event = None):
        self.panel.ctrl.OnCopySystem(formatted = True)

    def OnPaste(self, event = None):
        self.panel.ctrl.OnPaste()

    def OnPasteSystemCb(self, event = None):
        self.panel.ctrl.OnPasteSystemCb()

    def OnSelectScene(self, event = None):
        self.panel.ctrl.OnSelectScene()

    def OnSelectAll(self, event = None):
        self.panel.ctrl.OnSelectAll()

    def OnGotoPage(self, event = None):
        self.panel.ctrl.OnGotoPage()

    def OnGotoScene(self, event = None):
        self.panel.ctrl.OnGotoScene()

    def OnFindNextError(self, event = None):
        self.panel.ctrl.OnFindNextError()

    def OnFind(self, event = None):
        self.panel.ctrl.OnFind()

    def OnInsertNbsp(self, event = None):
        self.panel.ctrl.OnInsertNbsp()

    def OnDeleteElements(self, event = None):
        self.panel.ctrl.OnDeleteElements()

    def OnToggleShowFormatting(self, event = None):
        self.menuBar.Check(ID_VIEW_SHOW_FORMATTING,
            not self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING))
        self.showFormatting = not self.showFormatting
        self.panel.ctrl.Refresh(False)

    def OnShowFormatting(self, event = None):
        self.showFormatting = self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING)
        self.panel.ctrl.Refresh(False)

    def OnViewModeDraft(self):
        self.menuBar.Check(ID_VIEW_STYLE_DRAFT, True)
        self.OnViewModeChange()

    def OnViewModeLayout(self):
        self.menuBar.Check(ID_VIEW_STYLE_LAYOUT, True)
        self.OnViewModeChange()

    def OnViewModeSideBySide(self):
        self.menuBar.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)
        self.OnViewModeChange()

    def OnViewModeChange(self, event = None):
        if self.menuBar.IsChecked(ID_VIEW_STYLE_DRAFT):
            mode = VIEWMODE_DRAFT
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_LAYOUT):
            mode = VIEWMODE_LAYOUT
        else:
            mode = VIEWMODE_SIDE_BY_SIDE

        gd.setViewMode(mode)

        for c in self.getCtrls():
            c.refreshCache()

        c = self.panel.ctrl
        c.makeLineVisible(c.sp.line)
        c.updateScreen()

    def ToggleFullscreen(self, event = None):
        self.noFSBtn.Show(not self.IsFullScreen())
        self.ShowFullScreen(not self.IsFullScreen(), wx.FULLSCREEN_ALL)
        self.panel.ctrl.SetFocus()

    def OnPaginate(self, event = None):
        self.panel.ctrl.OnPaginate()

    def OnAutoCompletionDlg(self, event = None):
        self.panel.ctrl.OnAutoCompletionDlg()

    def OnTitlesDlg(self, event = None):
        self.panel.ctrl.OnTitlesDlg()

    def OnHeadersDlg(self, event = None):
        self.panel.ctrl.OnHeadersDlg()

    def OnLocationsDlg(self, event = None):
        self.panel.ctrl.OnLocationsDlg()

    def OnSpellCheckerDictionaryDlg(self, event = None):
        dlg = spellcheckcfgdlg.SCDictDlg(self, copy.deepcopy(gd.scDict),
                                         True)

        if dlg.ShowModal() == wx.ID_OK:
            gd.scDict = dlg.scDict
            gd.saveScDict()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self, event = None):
        self.panel.ctrl.OnSpellCheckerScriptDictionaryDlg()

    def OnWatermark(self, event = None):
        self.panel.ctrl.OnWatermark()

    def OnScriptSettings(self, event = None):
        self.panel.ctrl.OnScriptSettings()

    def OnLoadScriptSettings(self, event = None):
        dlg = wx.FileDialog(self, "File to open",
            defaultDir = gd.scriptSettingsPath,
            wildcard = "Script setting files (*.sconf)|*.sconf|All files|*",
            style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                cfg = config.Config()
                cfg.load(s)
                self.panel.ctrl.applyCfg(cfg)

                gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnSaveScriptSettingsAs(self, event = None):
        dlg = wx.FileDialog(self, "Filename to save as",
            defaultDir = gd.scriptSettingsPath,
            wildcard = "Script setting files (*.sconf)|*.sconf|All files|*",
            style = wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), self.panel.ctrl.sp.saveCfg(), self):
                gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnReportCharacter(self, event = None):
        self.panel.ctrl.OnReportCharacter()

    def OnReportDialogueChart(self, event = None):
        self.panel.ctrl.OnReportDialogueChart()

    def OnReportLocation(self, event = None):
        self.panel.ctrl.OnReportLocation()

    def OnReportScene(self, event = None):
        self.panel.ctrl.OnReportScene()

    def OnReportScript(self, event = None):
        self.panel.ctrl.OnReportScript()

    def OnSpellCheckerDlg(self, event = None):
        self.panel.ctrl.OnSpellCheckerDlg()

    def OnNameDatabase(self, event = None):
        if not namesdlg.readNames(self):
            wx.MessageBox("Error opening name database.", "Error",
                          wx.OK, self)

            return

        dlg = namesdlg.NamesDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCharacterMap(self, event = None):
        dlg = charmapdlg.CharMapDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCompareScripts(self, event = None):
        self.panel.ctrl.OnCompareScripts()

    def OnChangeType(self, event):
        self.panel.ctrl.OnChangeType(event)

    def OnHelpCommands(self, event = None):
        dlg = commandsdlg.CommandsDlg(cfgGl)
        dlg.Show()

    def OnHelpManual(self, event = None):
        webbrowser.open("file://" + misc.getFullPath("manual.html"))

    def OnAbout(self, event = None):
        win = splash.SplashWindow(self, -1)
        win.Show()

    def OnToolBarMenu(self, event, menu):
        self.PopupMenu(menu)

    def OnCloseWindow(self, event):
        doExit = True
        if event.CanVeto() and self.isModifications():
            if wx.MessageBox("You have unsaved changes. Are\n"
                             "you sure you want to exit?", "Confirm",
                             wx.YES_NO | wx.NO_DEFAULT, self) == wx.NO:
                doExit = False

        if doExit:
            util.writeToFile(gd.stateFilename, gd.save(), self)
            util.removeTempFiles(misc.tmpPrefix)
            self.Destroy()
            myApp.ExitMainLoop()
        else:
            event.Veto()

    def OnExit(self, event):
        self.Close(False)

    def OnMove(self, event):
        gd.posX, gd.posY = self.GetPosition()
        event.Skip()

    def OnSize(self, event):
        gd.width, gd.height = self.GetSize()
        event.Skip()

class MyApp(wx.App):

    def OnInit(self):
        global cfgGl, mainFrame, gd

        if (wx.MAJOR_VERSION != 4) or (wx.MINOR_VERSION < 0):
            wx.MessageBox("You seem to have an invalid version\n"
                          "(%s) of wxWidgets installed. This\n"
                          "program needs version 4.x." %
                          wx.VERSION_STRING, "Error", wx.OK)
            sys.exit()

        misc.init()
        util.init()

        gd = GlobalData()

        if misc.isWindows:
            major = sys.getwindowsversion()[0]
            if major < 5:
                wx.MessageBox("You seem to have a version of Windows\n"
                              "older than Windows 2000, which is the minimum\n"
                              "requirement for this program.", "Error", wx.OK)
                sys.exit()

        if not "unicode" in wx.PlatformInfo:
            wx.MessageBox("You seem to be using a non-Unicode build of\n"
                          "wxWidgets. This is not supported.",
                          "Error", wx.OK)
            sys.exit()

        os.chdir(misc.progPath)

        cfgGl = config.ConfigGlobal()
        cfgGl.setDefaults()

        if util.fileExists(gd.confFilename):
            s = util.loadFile(gd.confFilename, None)

            if s:
                cfgGl.load(s)
        else:
            # we want to write out a default config file at startup for
            # various reasons, if no default config file yet exists
            util.writeToFile(gd.confFilename, cfgGl.save(), None)

        refreshGuiConfig()

        # cfgGl.scriptDir is the directory used on startup, while
        # misc.scriptDir is updated every time the user opens something in
        # a different directory.
        misc.scriptDir = cfgGl.scriptDir

        if util.fileExists(gd.stateFilename):
            s = util.loadFile(gd.stateFilename, None)

            if s:
                gd.load(s)

        gd.setViewMode(gd.viewMode)

        if util.fileExists(gd.scDictFilename):
            s = util.loadFile(gd.scDictFilename, None)

            if s:
                gd.scDict.load(s)

        mainFrame = MyFrame(None, -1, "Trelby")
        mainFrame.init()

        for arg in opts.filenames:
            mainFrame.openScript(arg)

        mainFrame.Show(True)

        # windows needs this for some reason
        mainFrame.panel.ctrl.SetFocus()

        self.SetTopWindow(mainFrame)

        mainFrame.checkFonts()

        if cfgGl.splashTime > 0:
            win = splash.SplashWindow(mainFrame, cfgGl.splashTime * 1000)
            win.Show()
            win.Raise()

        return True

def main():
    global myApp

    opts.init()

    myApp = MyApp(0)
    myApp.MainLoop()
