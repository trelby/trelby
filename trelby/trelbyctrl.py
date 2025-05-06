# -*- coding: iso-8859-1 -*-

import copy
import os
import os.path
import time

import wx

import trelby
import trelby.autocompletiondlg as autocompletiondlg
import trelby.cfgdlg as cfgdlg
import trelby.config as config
import trelby.dialoguechart as dialoguechart
import trelby.finddlg as finddlg
import trelby.gutil as gutil
import trelby.headersdlg as headersdlg
import trelby.locationsdlg as locationsdlg
import trelby.misc as misc
import trelby.myimport as myimport
import trelby.opts as opts
import trelby.pml as pml
import trelby.reports as reports
import trelby.screenplay as screenplay
import trelby.spellcheck as spellcheck
import trelby.spellcheckcfgdlg as spellcheckcfgdlg
import trelby.spellcheckdlg as spellcheckdlg
import trelby.titlesdlg as titlesdlg
import trelby.util as util
import trelby.watermarkdlg as watermarkdlg
from trelby.error import TrelbyError
from trelby.ids import ID_EDIT_REDO, ID_EDIT_UNDO, idToLTMap
from trelby.line import Line

# Boolean to determine if toolbar should be shown or not.
toolbarshown = True

# keycodes
KC_CTRL_A = 1
KC_CTRL_B = 2
KC_CTRL_D = 4
KC_CTRL_E = 5
KC_CTRL_F = 6
KC_CTRL_N = 14
KC_CTRL_P = 16
KC_CTRL_V = 22


class MyCtrl(wx.Control):

    def __init__(self, parent, id, gd):
        style = wx.WANTS_CHARS | wx.FULL_REPAINT_ON_RESIZE | wx.NO_BORDER
        wx.Control.__init__(self, parent, id, style=style)

        self.panel = parent
        self.gd = gd

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
        self.updateScreen(redraw=False)

    def refreshGuiConfig(self):
        self.gd.cfgGui = config.ConfigGui(self.gd.cfgGl)

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
        self.findDlgMatchWholeWord = False
        self.findDlgMatchCase = False
        self.findDlgDirUp = False
        self.findDlgUseExtra = False
        self.findDlgElements = None

    def createEmptySp(self):
        self.clearVars()
        self.sp = screenplay.Screenplay(self.gd.cfgGl)
        self.sp.titles.addDefaults()
        self.sp.headers.addDefaults()
        self.setFile(None)
        self.refreshCache()

    # update stuff that depends on configuration / view mode etc.
    def refreshCache(self):
        self.chX = util.getTextWidth(" ", pml.COURIER, self.sp.cfg.fontSize)
        self.chY = util.getTextHeight(self.sp.cfg.fontSize)

        self.pageW = self.gd.vm.getPageWidth(self)

        # conversion factor from mm to pixels
        self.mm2p = self.pageW / self.sp.cfg.paperWidth

        # page width and height on screen, in pixels
        self.pageW = int(self.pageW)
        self.pageH = int(self.mm2p * self.sp.cfg.paperHeight)

    def getCfgGui(self):
        return self.gd.cfgGui

    def loadFile(self, fileName):
        s = str(util.loadFile(fileName, self.gd.mainFrame))
        if s == None:
            return

        try:
            (sp, msg) = screenplay.Screenplay.load(s, self.gd.cfgGl)
        except TrelbyError as e:
            wx.MessageBox(
                "Error loading file:\n\n%s" % e, "Error", wx.OK, self.gd.mainFrame
            )

            return

        if msg:
            misc.showText(self.gd.mainFrame, msg, "Warning")

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

        if util.writeToFile(fileName, self.sp.save(), self.gd.mainFrame):
            self.setFile(fileName)
            self.sp.markChanged(False)
            self.gd.mru.add(fileName)

            return True
        else:
            return False

    def importFile(self, fileName):
        titlePages = False
        if fileName.endswith("fdx"):
            lines = myimport.importFDX(fileName, self.gd.mainFrame)
        elif fileName.endswith("celtx"):
            lines = myimport.importCeltx(fileName, self.gd.mainFrame)
        elif fileName.endswith("astx"):
            lines = myimport.importAstx(fileName, self.gd.mainFrame)
        elif fileName.endswith("fountain"):
            lines, titlePages = myimport.importFountain(
                fileName, self.gd.mainFrame, self.sp.titles.pages
            )
        elif fileName.endswith("fadein"):
            lines = myimport.importFadein(fileName, self.gd.mainFrame)
        else:
            lines = myimport.importTextFile(fileName, self.gd.mainFrame)

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

        dlg = misc.CheckBoxDlg(
            self.gd.mainFrame, "Output options", inf, "Options:", False
        )

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()

            return None

        return sp.generateText(inf[0].selected)

    def getExportHtml(self, sp):
        inf = []
        inf.append(misc.CheckBoxItem("Include Notes"))

        dlg = misc.CheckBoxDlg(
            self.gd.mainFrame, "Output options", inf, "Options:", False
        )

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
        self.gd.mainFrame.setTitle(self.fileNameDisplay)

    def setDisplayName(self, name):
        i = 1
        while 1:
            if i == 1:
                tmp = name
            else:
                tmp = name + "-%d" % i

            matched = False

            for c in self.gd.mainFrame.getCtrls():
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
        self.gd.mainFrame.setTabText(self.panel, self.fileNameDisplay)

    # texts = self.gd.vm.getScreen(self, False)[0], or None, in which case it's
    # called in this function.
    def isLineVisible(self, line, texts=None):
        if texts == None:
            texts = self.gd.vm.getScreen(self, False)[0]

        # paranoia never hurts
        if len(texts) == 0:
            return False

        return (line >= texts[0].line) and (line <= texts[-1].line)

    def makeLineVisible(self, line, direction=config.SCROLL_CENTER):
        texts = self.gd.vm.getScreen(self, False)[0]

        if self.isLineVisible(line, texts):
            return

        self.gd.vm.makeLineVisible(self, line, texts, direction)

    def adjustScrollBar(self):
        height = self.GetClientSize().height

        # rough approximation of how many lines fit onto the screen.
        # accuracy is not that important for this, so we don't even care
        # about draft / layout mode differences.
        approx = int(((height / self.mm2p) / self.chY) / 1.3)

        self.panel.scrollBar.SetScrollbar(
            self.sp.getTopLine(), approx, len(self.sp.lines) + approx - 1, approx
        )

    def clearAutoComp(self):
        if self.sp.clearAutoComp():
            self.Refresh(False)

    # returns true if there are no contents at all and we're not
    # attached to any file
    def isUntouched(self):
        if (
            self.fileName
            or (len(self.sp.lines) > 1)
            or (len(self.sp.lines[0].text) > 0)
        ):
            return False
        else:
            return True

    def updateScreen(self, redraw=True, setCommon=True):
        self.adjustScrollBar()

        if setCommon:
            self.updateCommon()

        if redraw:
            self.Refresh(False)

    # update GUI elements shared by all scripts, like statusbar etc
    def updateCommon(self):
        cur = self.gd.cfgGl.getType(self.sp.lines[self.sp.line].lt)

        if self.sp.tabMakesNew():
            tabNext = "%s" % self.gd.cfgGl.getType(cur.newTypeTab).ti.name
        else:
            tabNext = "%s" % self.gd.cfgGl.getType(cur.nextTypeTab).ti.name

        enterNext = self.gd.cfgGl.getType(cur.newTypeEnter).ti.name

        page = self.sp.line2page(self.sp.line)
        pageCnt = self.sp.line2page(len(self.sp.lines) - 1)

        self.gd.mainFrame.statusCtrl.SetValues(
            page, pageCnt, cur.ti.name, tabNext, enterNext
        )

        canUndo = self.sp.canUndo()
        canRedo = self.sp.canRedo()

        self.gd.mainFrame.menuBar.Enable(ID_EDIT_UNDO, canUndo)
        self.gd.mainFrame.menuBar.Enable(ID_EDIT_REDO, canRedo)

        self.gd.mainFrame.toolBar.EnableTool(ID_EDIT_UNDO, canUndo)
        self.gd.mainFrame.toolBar.EnableTool(ID_EDIT_REDO, canRedo)

    # apply per-script config
    def applyCfg(self, newCfg):
        self.sp.applyCfg(newCfg)

        self.refreshCache()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    # apply global config
    def applyGlobalCfg(self, newCfgGl, writeCfg=True):

        oldCfgGl = self.gd.cfgGl

        self.gd.cfgGl = copy.deepcopy(newCfgGl)

        # if user has ventured from the old default directory, keep it as
        # the current one, otherwise set the new default as current.
        if misc.scriptDir == oldCfgGl.scriptDir:
            misc.scriptDir = self.gd.cfgGl.scriptDir

        self.gd.cfgGl.recalc()
        self.refreshGuiConfig()
        self.gd.mainFrame.updateKbdCommands()

        for c in self.gd.mainFrame.getCtrls():
            c.sp.cfgGl = self.gd.cfgGl
            c.refreshCache()
            c.makeLineVisible(c.sp.line)
            c.adjustScrollBar()

        self.updateScreen()

        # in case tab colors have been changed
        self.gd.mainFrame.tabCtrl.Refresh(False)
        self.gd.mainFrame.statusCtrl.Refresh(False)
        self.gd.mainFrame.noFSBtn.Refresh(False)
        self.gd.mainFrame.toolBar.SetBackgroundColour(self.gd.cfgGui.tabBarBgColor)

        if writeCfg:
            util.writeToFile(
                self.gd.confFilename, self.gd.cfgGl.save(), self.gd.mainFrame
            )

        self.gd.mainFrame.checkFonts()

    def applyHeaders(self, newHeaders):
        self.sp.headers = newHeaders
        self.sp.markChanged()
        self.OnPaginate()

    # return an exportable, paginated Screenplay object, or None if for
    # some reason that's not possible / wanted. 'action' is the name of
    # the action, e.g. "export" or "print", that'll be done to the script,
    # and is used in dialogue with the user if needed.
    def getExportable(self, action):
        if self.gd.cfgGl.checkOnExport:
            line = self.sp.findError(0)[0]

            if line != -1:
                if (
                    wx.MessageBox(
                        "The script seems to contain errors.\n"
                        "Are you sure you want to %s it?" % action,
                        "Confirm",
                        wx.YES_NO | wx.NO_DEFAULT,
                        self.gd.mainFrame,
                    )
                    == wx.NO
                ):

                    return None

        sp = self.sp
        if sp.cfg.pdfRemoveNotes:
            sp = copy.deepcopy(self.sp)
            sp.removeElementTypes({screenplay.NOTE: None}, False)

        sp.paginate()

        return sp

    def OnEraseBackground(self, event):
        pass

    def OnSize(self, event):
        if misc.doDblBuf:
            size = self.GetClientSize()

            sb = wx.Bitmap(size.width, size.height)
            old = getattr(self.__class__, "screenBuf", None)

            if (
                (old == None)
                or (old.GetDepth() != sb.GetDepth())
                or (old.GetHeight() != sb.GetHeight())
                or (old.GetWidth() != sb.GetWidth())
            ):
                self.__class__.screenBuf = sb

        self.makeLineVisible(self.sp.line)

    def OnLeftDown(self, event, mark=False):
        if not self.mouseSelectActive:
            self.sp.clearMark()
            self.updateScreen()

        pos = event.GetPosition()
        line, col = self.gd.vm.pos2linecol(self, pos.x, pos.y)

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
            self.OnLeftDown(event, mark=True)

    def OnRightDown(self, event):
        pos = event.GetPosition()
        line, col = self.gd.vm.pos2linecol(self, pos.x, pos.y)

        if self.sp.mark:
            m = self.gd.mainFrame.rightClickMenuWithCut
        else:
            m = self.gd.mainFrame.rightClickMenu

            if line is not None and (line != self.sp.line):
                self.sp.gotoPos(line, col, False)
                self.updateScreen()

        self.PopupMenu(m)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            delta = -self.gd.cfgGl.mouseWheelLines
        else:
            delta = self.gd.cfgGl.mouseWheelLines

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
        dlg = autocompletiondlg.AutoCompletionDlg(
            self.gd.mainFrame, copy.deepcopy(self.sp.autoCompletion)
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.autoCompletion = dlg.autoCompletion
            self.sp.markChanged()

        dlg.Destroy()

    def OnTitlesDlg(self):
        dlg = titlesdlg.TitlesDlg(
            self.gd.mainFrame, copy.deepcopy(self.sp.titles), self.sp.cfg, self.gd.cfgGl
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.titles = dlg.titles
            self.sp.markChanged()

        dlg.Destroy()

    def OnHeadersDlg(self):
        dlg = headersdlg.HeadersDlg(
            self.gd.mainFrame,
            copy.deepcopy(self.sp.headers),
            self.sp.cfg,
            self.gd.cfgGl,
            self.applyHeaders,
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.applyHeaders(dlg.headers)

        dlg.Destroy()

    def OnLocationsDlg(self):
        dlg = locationsdlg.LocationsDlg(self.gd.mainFrame, copy.deepcopy(self.sp))

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.locations = dlg.sp.locations
            self.sp.markChanged()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self):
        dlg = spellcheckcfgdlg.SCDictDlg(
            self.gd.mainFrame, copy.deepcopy(self.sp.scDict), False
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.sp.scDict = dlg.scDict
            self.sp.markChanged()

        dlg.Destroy()

    def OnWatermark(self):
        dlg = watermarkdlg.WatermarkDlg(
            self.gd.mainFrame, self.sp, self.fileNameDisplay.replace(".trelby", "")
        )
        dlg.ShowModal()
        dlg.Destroy()

    def OnReportDialogueChart(self):
        self.sp.paginate()
        dialoguechart.genDialogueChart(self.gd.mainFrame, self.sp)

    def OnReportCharacter(self):
        self.sp.paginate()
        reports.genCharacterReport(self.gd.mainFrame, self.sp)

    def OnReportLocation(self):
        self.sp.paginate()
        reports.genLocationReport(self.gd.mainFrame, self.sp)

    def OnReportScene(self):
        self.sp.paginate()
        reports.genSceneReport(self.gd.mainFrame, self.sp)

    def OnReportScript(self):
        self.sp.paginate()
        reports.genScriptReport(self.gd.mainFrame, self.sp)

    def OnCompareScripts(self):
        if self.gd.mainFrame.tabCtrl.getPageCount() < 2:
            wx.MessageBox(
                "You need at least two scripts open to" " compare them.",
                "Error",
                wx.OK,
                self.gd.mainFrame,
            )

            return

        items = []
        for c in self.gd.mainFrame.getCtrls():
            items.append(c.fileNameDisplay)

        dlg = misc.ScriptChooserDlg(self.gd.mainFrame, items)

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
            wx.MessageBox(
                "You can't compare a script to itself.",
                "Error",
                wx.OK,
                self.gd.mainFrame,
            )

            return

        c1 = self.gd.mainFrame.tabCtrl.getPage(sel1).ctrl
        c2 = self.gd.mainFrame.tabCtrl.getPage(sel2).ctrl

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
            gutil.showTempPDF(s, self.gd.cfgGl, self.gd.mainFrame)
        else:
            wx.MessageBox(
                "The scripts are identical.", "Results", wx.OK, self.gd.mainFrame
            )

    def canBeClosed(self):
        if self.sp.isModified():
            if (
                wx.MessageBox(
                    "The script has been modified. Are you sure\n"
                    "you want to discard the changes?",
                    "Confirm",
                    wx.YES_NO | wx.NO_DEFAULT,
                    self.gd.mainFrame,
                )
                == wx.NO
            ):
                return False

        return True

    # page up (dir == -1) or page down (dir == 1) was pressed, handle it.
    # cs = CommandState.
    def pageCmd(self, cs, dir):
        if self.sp.acItems:
            cs.doAutoComp = cs.AC_KEEP
            self.sp.pageScrollAutoComp(dir)

            return

        texts, dpages = self.gd.vm.getScreen(self, False)

        # if user has scrolled with scrollbar so that cursor isn't seen,
        # just make cursor visible and don't move
        if not self.isLineVisible(self.sp.line, texts):
            self.gd.vm.makeLineVisible(self, self.sp.line, texts)
            cs.needsVisifying = False

            return

        self.sp.maybeMark(cs.mark)
        self.gd.vm.pageCmd(self, cs, dir, texts, dpages)

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
    def OnCut(self, doUpdate=True, doDelete=True, copyToClip=True):
        marked = self.sp.getMarkedLines()

        if not marked:
            return False

        cd = self.sp.getSelectedAsCD(doDelete)

        if copyToClip:
            self.gd.mainFrame.clipboard = cd

        if doUpdate:
            self.makeLineVisible(self.sp.line)
            self.updateScreen()

        return doDelete

    def OnCopy(self):
        self.OnCut(doDelete=False)

    def OnCopySystem(self, formatted=False):
        cd = self.sp.getSelectedAsCD(False)

        if not cd:
            return

        tmpSp = screenplay.Screenplay(self.gd.cfgGl)
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

    def OnPaste(self, clines=None):
        if not clines:
            cd = self.gd.mainFrame.clipboard

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
                lines.append(Line(screenplay.LB_LAST, screenplay.ACTION, s))

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

        dlg = misc.TextInputDlg(
            self.gd.mainFrame,
            "Enter scene number (%s - %s):" % (scenes[0][0], scenes[-1][0]),
            "Goto scene",
            validateFunc,
        )

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

        dlg = misc.TextInputDlg(
            self.gd.mainFrame,
            "Enter page number (%s - %s):" % (pages[0], pages[-1]),
            "Goto page",
            validateFunc,
        )

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

        wx.MessageBox(msg, "Results", wx.OK, self.gd.mainFrame)

    def OnFind(self):
        self.sp.clearMark()
        self.clearAutoComp()
        self.updateScreen()

        dlg = finddlg.FindDlg(self.gd.mainFrame, self)
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

        if not spellcheck.loadDict(self.gd.mainFrame):
            wx.EndBusyCursor()

            return

        sc = spellcheck.SpellChecker(self.sp, self.gd.scDict)
        found = sc.findNext()

        wx.EndBusyCursor()

        if not found:
            s = ""

            if not wasAtStart:
                s = (
                    "\n\n(Starting position was not at\n"
                    "the beginning of the script.)"
                )
            wx.MessageBox(
                "Spell checker found no errors." + s,
                "Results",
                wx.OK,
                self.gd.mainFrame,
            )

            return

        dlg = spellcheckdlg.SpellCheckDlg(self.gd.mainFrame, self, sc, self.gd.scDict)
        dlg.ShowModal()

        if dlg.changedGlobalDict:
            self.gd.saveScDict()

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

        dlg = misc.CheckBoxDlg(
            self.gd.mainFrame,
            "Delete elements",
            types,
            "Element types to delete:",
            True,
        )

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

        dlg = wx.FileDialog(
            self.gd.mainFrame,
            "Filename to save as",
            defaultDir=dDir,
            defaultFile=dFile,
            wildcard="Trelby files (*.trelby)|*.trelby|All files|*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )
        if dlg.ShowModal() == wx.ID_OK:
            self.saveFile(dlg.GetPath())

        dlg.Destroy()

    def OnExportScript(self):
        sp = self.getExportable("export")
        if not sp:
            return

        dlg = wx.FileDialog(
            self.gd.mainFrame,
            "Filename to export as",
            misc.scriptDir,
            wildcard="PDF|*.pdf|"
            "RTF|*.rtf|"
            "Final Draft XML|*.fdx|"
            "HTML|*.html|"
            "Fountain|*.fountain|"
            "Formatted text|*.txt",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )

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
                util.writeToFile(fileName, data, self.gd.mainFrame)

        dlg.Destroy()

    def OnPrint(self):
        sp = self.getExportable("print")
        if not sp:
            return

        s = sp.generatePDF(False)
        gutil.showTempPDF(s, self.gd.cfgGl, self.gd.mainFrame)

    def OnSettings(self):
        dlg = cfgdlg.CfgDlg(
            self.gd.mainFrame, copy.deepcopy(self.gd.cfgGl), self.applyGlobalCfg, True
        )

        if dlg.ShowModal() == wx.ID_OK:
            self.applyGlobalCfg(dlg.cfg)

        dlg.Destroy()

    def OnScriptSettings(self):
        dlg = cfgdlg.CfgDlg(
            self.gd.mainFrame, copy.deepcopy(self.sp.cfg), self.applyCfg, False
        )

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

    def cmdChangeToActBreak(self, cs):
        self.sp.toActBreakCmd(cs)

    def cmdChangeToTransition(self, cs):
        self.sp.toTransitionCmd(cs)

    def cmdDelete(self, cs):
        if not self.sp.mark:
            self.sp.deleteForwardCmd(cs)
        else:
            self.OnCut(doUpdate=False, copyToClip=False)

    def cmdDeleteBackward(self, cs):
        if not self.sp.mark:
            self.sp.deleteBackwardCmd(cs)
        else:
            self.OnCut(doUpdate=False, copyToClip=False)

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

    def cmdMoveNextWord(self, cs):
        self.sp.moveNextWordCmd(cs)

    def cmdMovePageDown(self, cs):
        self.pageCmd(cs, 1)

    def cmdMovePageUp(self, cs):
        self.pageCmd(cs, -1)

    def cmdMovePrevWord(self, cs):
        self.sp.movePrevWordCmd(cs)

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

        if not ev.ControlDown() and not ev.AltDown() and util.isValidInputChar(kc):
            # WX2.6-FIXME: we should probably use GetUnicodeKey() (dunno
            # how to get around the isValidInputChar test in the preceding
            # line, need to test what GetUnicodeKey() returns on
            # non-input-character events)

            addChar = True

            # If there's something selected, either remove it, or clear selection.
            if self.sp.mark and self.gd.cfgGl.overwriteSelectionOnInsert:
                if not self.OnCut(doUpdate=False, copyToClip=False):
                    self.sp.clearMark()
                    addChar = False

            if addChar:
                cs.char = chr(kc)

                if opts.isTest and (cs.char == "�"):
                    self.loadFile("sample.trelby")
                elif opts.isTest and (cs.char == "�"):
                    self.cmdTest(cs)
                elif opts.isTest and (cs.char == "�"):
                    self.cmdSpeedTest(cs)
                else:
                    self.sp.addCharCmd(cs)

        else:
            cmd = self.gd.mainFrame.kbdCommands.get(
                util.Key(kc, ev.ControlDown(), ev.AltDown(), ev.ShiftDown()).toInt()
            )

            if cmd:
                scrollDirection = cmd.scrollDirection
                if cmd.isMenu:
                    getattr(self.gd.mainFrame, "On" + cmd.name)()
                    return
                else:
                    getattr(self, "cmd" + cmd.name)(cs)
            else:
                ev.Skip()
                return

        self.sp.cmdPost(cs)

        if self.gd.cfgGl.paginateInterval > 0:
            now = time.time()

            if (now - self.sp.lastPaginated) >= self.gd.cfgGl.paginateInterval:
                self.sp.paginate()

                cs.needsVisifying = True

        if cs.needsVisifying:
            self.makeLineVisible(self.sp.line, scrollDirection)

        self.updateScreen()

    def OnPaint(self, event):
        # ldkjfldsj = util.TimerDev("paint")

        ls = self.sp.lines

        if misc.doDblBuf:
            dc = wx.BufferedPaintDC(self, self.screenBuf)
        else:
            dc = wx.PaintDC(self)

        size = self.GetClientSize()
        marked = self.sp.getMarkedLines()
        lineh = self.gd.vm.getLineHeight(self)
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

        strings, dpages = self.gd.vm.getScreen(self, True, True)

        dc.SetBrush(self.gd.cfgGui.workspaceBrush)
        dc.SetPen(self.gd.cfgGui.workspacePen)
        dc.DrawRectangle(0, 0, size.width, size.height)

        dc.SetPen(self.gd.cfgGui.tabBorderPen)
        dc.DrawLine(0, 0, 0, size.height)

        if not dpages:
            # draft mode; draw an infinite page
            lx = util.clamp((size.width - self.pageW) // 2, 0)
            rx = lx + self.pageW

            dc.SetBrush(self.gd.cfgGui.textBgBrush)
            dc.SetPen(self.gd.cfgGui.textBgPen)
            dc.DrawRectangle(lx, 5, self.pageW, size.height - 5)

            dc.SetPen(self.gd.cfgGui.pageBorderPen)
            dc.DrawLine(lx, 5, lx, size.height)
            dc.DrawLine(rx, 5, rx, size.height)

        else:
            dc.SetBrush(self.gd.cfgGui.textBgBrush)
            dc.SetPen(self.gd.cfgGui.pageBorderPen)
            for dp in dpages:
                dc.DrawRectangle(dp.x1, dp.y1, dp.x2 - dp.x1 + 1, dp.y2 - dp.y1 + 1)

            dc.SetPen(self.gd.cfgGui.pageShadowPen)
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
                    dc.SetPen(self.gd.cfgGui.notePen)
                    dc.SetBrush(self.gd.cfgGui.noteBrush)

                    nx = t.x - 5
                    nw = self.sp.cfg.getType(l.lt).width * fx + 10

                    dc.DrawRectangle(nx, y, nw, lineh)

                    dc.SetPen(self.gd.cfgGui.textPen)
                    util.drawLine(dc, nx - 1, y, 0, lineh)
                    util.drawLine(dc, nx + nw, y, 0, lineh)

                    if self.sp.isFirstLineOfElem(i):
                        util.drawLine(dc, nx - 1, y - 1, nw + 2, 0)

                    if self.sp.isLastLineOfElem(i):
                        util.drawLine(dc, nx - 1, y + lineh, nw + 2, 0)

                if marked and self.sp.isLineMarked(i, marked):
                    c1, c2 = self.sp.getMarkedColumns(i, marked)

                    dc.SetPen(self.gd.cfgGui.selectedPen)
                    dc.SetBrush(self.gd.cfgGui.selectedBrush)

                    dc.DrawRectangle(t.x + c1 * fx, y, (c2 - c1 + 1) * fx, lineh)

                if self.gd.mainFrame.showFormatting:
                    dc.SetPen(self.gd.cfgGui.bluePen)
                    util.drawLine(dc, t.x, y, 0, lineh)

                    extraIndent = 1 if self.sp.needsExtraParenIndent(i) else 0

                    util.drawLine(
                        dc,
                        t.x + (self.sp.cfg.getType(l.lt).width - extraIndent) * fx,
                        y,
                        0,
                        lineh,
                    )

                    dc.SetTextForeground(self.gd.cfgGui.redColor)
                    dc.SetFont(self.gd.cfgGui.fonts[pml.NORMAL].font)
                    dc.DrawText(config.lb2char(l.lb), t.x - 10, y)

                if not dpages:
                    if self.gd.cfgGl.pbi == config.PBI_REAL_AND_UNADJ:
                        if self.sp.line2pageNoAdjust(i) != self.sp.line2pageNoAdjust(
                            i + 1
                        ):
                            dc.SetPen(self.gd.cfgGui.pagebreakNoAdjustPen)
                            util.drawLine(dc, 0, y + lineh - 1, size.width, 0)

                    if self.gd.cfgGl.pbi in (
                        config.PBI_REAL,
                        config.PBI_REAL_AND_UNADJ,
                    ):
                        thisPage = self.sp.line2page(i)

                        if thisPage != self.sp.line2page(i + 1):
                            dc.SetPen(self.gd.cfgGui.pagebreakPen)
                            util.drawLine(dc, 0, y + lineh - 1, size.width, 0)

                if i == self.sp.line:
                    posX = t.x
                    cursorY = y
                    acFi = fi
                    dc.SetPen(self.gd.cfgGui.cursorPen)
                    dc.SetBrush(self.gd.cfgGui.cursorBrush)
                    dc.DrawRectangle(t.x + self.sp.column * fx, y, fx, fi.fy)

            if len(t.text) != 0:
                # tl = texts.get(fi.font)
                if fi.font not in texts:
                    # if tl == None:
                    tl = ([], [], [])
                    texts.append((fi.font, tl))

                tl[0].append(t.text)
                tl[1].append((t.x, y))
                if t.line != -1:
                    if self.gd.cfgGl.useCustomElemColors:
                        tl[2].append(self.gd.cfgGui.lt2textColor(ls[t.line].lt))
                    else:
                        tl[2].append(self.gd.cfgGui.textColor)
                else:
                    tl[2].append(self.gd.cfgGui.textHdrColor)

                if t.isUnderlined:
                    if t.line != -1:
                        uli = ulines
                    else:
                        uli = ulinesHdr

                    uli.append((t.x, y + lineh - 1, len(t.text) * fx - 1))

        if ulines:
            dc.SetPen(self.gd.cfgGui.textPen)

            for ul in ulines:
                util.drawLine(dc, ul[0], ul[1], ul[2], 0)

        if ulinesHdr:
            dc.SetPen(self.gd.cfgGui.textHdrPen)

            for ul in ulinesHdr:
                util.drawLine(dc, ul[0], ul[1], ul[2], 0)

        for tl in texts:
            self.gd.vm.drawTexts(self, dc, tl)

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

        dc.SetPen(self.gd.cfgGui.autoCompPen)
        dc.SetBrush(self.gd.cfgGui.autoCompBrush)
        dc.DrawRectangle(posX, posY, w, h)

        dc.SetTextForeground(self.gd.cfgGui.autoCompFgColor)

        for i in range(startPos, endPos):
            if i == asel:
                dc.SetPen(self.gd.cfgGui.autoCompRevPen)
                dc.SetBrush(self.gd.cfgGui.autoCompRevBrush)
                dc.SetTextForeground(self.gd.cfgGui.autoCompBgColor)
                dc.DrawRectangle(
                    posX + offset - selBleed,
                    posY + offset + (i - startPos) * fi.fy - selBleed,
                    itemW,
                    fi.fy + selBleed * 2,
                )
                dc.SetTextForeground(self.gd.cfgGui.autoCompBgColor)
                dc.SetPen(self.gd.cfgGui.autoCompPen)
                dc.SetBrush(self.gd.cfgGui.autoCompBrush)

            dc.DrawText(ac[i], posX + offset, posY + offset + (i - startPos) * fi.fy)

            if i == asel:
                dc.SetTextForeground(self.gd.cfgGui.autoCompFgColor)

        if doSbw:
            dc.SetPen(self.gd.cfgGui.autoCompPen)
            dc.SetBrush(self.gd.cfgGui.autoCompRevBrush)
            util.drawLine(dc, posX + w - offset * 2 - sbw, posY, 0, h)
            dc.DrawRectangle(
                posX + w - offset - sbw,
                posY + offset - selBleed + int((float(startPos) / len(ac)) * sbh),
                sbw,
                int((float(show) / len(ac)) * sbh),
            )
