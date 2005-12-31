#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

from error import *
import autocompletiondlg
import bugreport
import cfgdlg
import characterreport
import charmapdlg
import commandsdlg
import config
import decode
import dialoguechart
import finddlg
import gutil
import headersdlg
import locationreport
import locationsdlg
import misc
import myimport
import mypickle
import namesdlg
import opts
import pml
import scenereport
import scriptreport
import screenplay
import spellcheck
import spellcheckdlg
import spellcheckcfgdlg
import splash
import titlesdlg
import util
import viewmode

import copy
import datetime
import os
import os.path
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

VIEWMODE_DRAFT,\
VIEWMODE_LAYOUT,\
VIEWMODE_SIDE_BY_SIDE,\
VIEWMODE_OVERVIEW_SMALL,\
VIEWMODE_OVERVIEW_LARGE,\
= range(5)

def refreshGuiConfig():
    global cfgGui

    cfgGui = config.ConfigGui(cfgGl)

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
        v.addInt("viewMode", VIEWMODE_LAYOUT, "ViewMode", VIEWMODE_DRAFT,
                 VIEWMODE_OVERVIEW_LARGE)
        v.addStr("license", "", "License")

        v.addList("files", [], "Files",
                  mypickle.StrNoEscapeVar("", "", ""))
        
        v.makeDicts()
        v.setDefaults(self)

        self.height = min(self.height,
            wxSystemSettings_GetMetric(wxSYS_SCREEN_Y) - 50)

        self.vmDraft = viewmode.ViewModeDraft()
        self.vmLayout = viewmode.ViewModeLayout()
        self.vmSideBySide = viewmode.ViewModeSideBySide()
        self.vmOverviewSmall = viewmode.ViewModeOverview(1)
        self.vmOverviewLarge = viewmode.ViewModeOverview(2)

        self.setViewMode(self.viewMode)

        self.makeConfDir()

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

    # set viewmode, the parameter is one of the VIEWMODE_ defines.
    def setViewMode(self, viewMode):
        self.viewMode = viewMode

        if viewMode == VIEWMODE_DRAFT:
            self.vm = self.vmDraft
        elif viewMode == VIEWMODE_LAYOUT:
            self.vm = self.vmLayout
        elif viewMode == VIEWMODE_SIDE_BY_SIDE:
            self.vm = self.vmSideBySide
        elif viewMode == VIEWMODE_OVERVIEW_SMALL:
            self.vm = self.vmOverviewSmall
        else:
            self.vm = self.vmOverviewLarge

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
        util.writeToFile(self.scDictFilename,
                         util.toUTF8(self.scDict.save()), mainFrame)

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
        self.searchLine = -1
        self.searchColumn = -1
        self.searchWidth = -1

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
        s = util.loadFile(fileName, mainFrame)
        if s == None:
            return

        try:
            (sp, msg) = screenplay.Screenplay.load(s, cfgGl)
        except BlyteError, e:
            wxMessageBox("Error loading file:\n\n%s" % e, "Error",
                         wxOK, mainFrame)

            return

        if msg:
            misc.showText(mainFrame, msg, "Warning")
            
        self.clearVars()
        self.sp = sp
        self.setFile(fileName)
        self.refreshCache()

    # save script to given filename. returns True on success.
    def saveFile(self, fileName):
        if util.writeToFile(fileName, self.sp.save(), mainFrame):
            self.setFile(fileName)
            self.sp.markChanged(False)

            return True
        else:
            return False

    def importFile(self, fileName):
        lines = myimport.importTextFile(fileName, mainFrame)

        if not lines:
            return

        self.createEmptySp()
        
        self.sp.lines = lines
        self.sp.reformatAll()
        self.sp.paginate()

    # generate exportable text from given screenplay, or None.
    def getExportText(self, sp):
        inf = []
        inf.append(misc.CheckBoxItem("Include page markers"))

        dlg = misc.CheckBoxDlg(mainFrame, "Output options", inf,
                               "Options:", False)

        if dlg.ShowModal() != wxID_OK:
            dlg.Destroy()

            return None

        return sp.generateText(inf[0].selected)
        
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
        
    def updateTypeCb(self):
        util.reverseComboSelect(mainFrame.typeCb,
                                self.sp.lines[self.sp.line].lt)

    # texts = gd.vm.getScreen(self, False)[0], or None, in which case it's
    # called in this function.
    def isLineVisible(self, line, texts = None):
        if texts == None:
            texts = gd.vm.getScreen(self, False)[0]

        # paranoia never hurts
        if len(texts) == 0:
            return False

        return (line >= texts[0].line) and (line <= texts[-1].line)

    def makeLineVisible(self, line):
        texts = gd.vm.getScreen(self, False)[0]

        if self.isLineVisible(line, texts):
            return

        gd.vm.makeLineVisible(self, line, texts)

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
        self.updateTypeCb()

        sb = mainFrame.statusBar
        
        sb.SetStatusText("Page: %d / %d" % (self.sp.line2page(self.sp.line),
            self.sp.line2page(len(self.sp.lines) - 1)), 2)

        cur = cfgGl.getType(self.sp.lines[self.sp.line].lt)
        
        if self.sp.tabMakesNew():
            s = "%s" % cfgGl.getType(cur.newTypeTab).ti.name
        else:
            s = "%s [change]" % cfgGl.getType(cur.nextTypeTab).ti.name
            
        sb.SetStatusText("Tab: %s" % s, 0)
        sb.SetStatusText("Enter: %s" % cfgGl.getType(cur.newTypeEnter).ti.name,
                         1)

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

        if writeCfg:
            util.writeToFile(gd.confFilename, cfgGl.save(), mainFrame)

    def applyHeaders(self, newHeaders):
        self.sp.headers = newHeaders
        self.sp.markChanged()
        self.OnPaginate()

    # if we have a valid license, or the script is shorter than ~20 pages,
    # return False, otherwise True. in the latter case, also display a
    # message box about this.
    def checkEvalSave(self):

        # slightly obscured 25000...
        stackPtr = 18 * 14 * 16 * 6 + 80 * 11 - 72
        
        if not misc.license and (self.sp.getCharCount() > stackPtr):
            wxMessageBox("The evaluation version of this program doesn't\n"
                         "support saving scripts over 20 pages or so.",
                         "Error", wxOK, mainFrame)
            return True

        return False

    # return an exportable, paginated Screenplay object, or None if for
    # some reason that's not possible / wanted. 'action' is the name of
    # the action, e.g. "export" or "print", that'll be done to the script,
    # and is used in dialogue with the user if needed.
    def getExportable(self, action):
        if cfgGl.checkOnExport:
            line = self.sp.findError(0)[0]

            if line != -1:
                if wxMessageBox("The script seems to contain errors.\n"
                    "Are you sure you want to %s it?" % action, "Confirm",
                     wxYES_NO | wxNO_DEFAULT, mainFrame) == wxNO:

                    return None

        sp = self.sp
        if not misc.license or sp.cfg.pdfRemoveNotes:
            sp = copy.deepcopy(self.sp)

            if sp.cfg.pdfRemoveNotes:
                sp.removeElementTypes({screenplay.NOTE : None})
                
            if not misc.license:
                sp.replace()

        sp.paginate()
        
        return sp

    def OnEraseBackground(self, event):
        pass
        
    def OnSize(self, event):
        size = self.GetClientSize()

        sb = wxEmptyBitmap(size.width, size.height)
        old = getattr(self.__class__, "screenBuf", None)

        if (old == None) or (old.GetDepth() != sb.GetDepth()) or \
           (old.GetHeight() != sb.GetHeight()) or \
           (old.GetWidth() != sb.GetWidth()):
            self.__class__.screenBuf = sb
        
        self.makeLineVisible(self.sp.line)
    
    def OnLeftDown(self, event, mark = False):
        pos = event.GetPosition()
        line, col = gd.vm.pos2linecol(self, pos.x, pos.y)

        if line != None:
            self.sp.gotoPos(line, col, mark)
            self.updateScreen()

    def OnRightDown(self, event):
        self.sp.clearMark()
        self.updateScreen()
        
    def OnMotion(self, event):
        if event.LeftIsDown():
            self.OnLeftDown(event, mark = True)

    def OnMouseWheel(self, event):
        if event.GetWheelRotation() > 0:
            delta = -cfgGl.mouseWheelLines
        else:
            delta = cfgGl.mouseWheelLines
            
        self.sp.setTopLine(self.sp.getTopLine() + delta)
        self.updateScreen()
        
    def OnTypeCombo(self, event):
        lt = mainFrame.typeCb.GetClientData(mainFrame.typeCb.GetSelection())
        self.sp.convertCurrentTo(lt)
        self.SetFocus()
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

        if dlg.ShowModal() == wxID_OK:
            self.sp.autoCompletion = dlg.autoCompletion
            self.sp.markChanged()

        dlg.Destroy()

    def OnTitlesDlg(self):
        dlg = titlesdlg.TitlesDlg(mainFrame, copy.deepcopy(self.sp.titles),
                                  self.sp.cfg, cfgGl)

        if dlg.ShowModal() == wxID_OK:
            self.sp.titles = dlg.titles
            self.sp.markChanged()

        dlg.Destroy()

    def OnHeadersDlg(self):
        dlg = headersdlg.HeadersDlg(mainFrame,
            copy.deepcopy(self.sp.headers), self.sp.cfg, cfgGl,
                                    self.applyHeaders)

        if dlg.ShowModal() == wxID_OK:
            self.applyHeaders(dlg.headers)

        dlg.Destroy()

    def OnLocationsDlg(self):
        dlg = locationsdlg.LocationsDlg(mainFrame, copy.deepcopy(self.sp))

        if dlg.ShowModal() == wxID_OK:
            self.sp.locations = dlg.sp.locations
            self.sp.markChanged()

        dlg.Destroy()
        
    def OnSpellCheckerScriptDictionaryDlg(self):
        dlg = spellcheckcfgdlg.SCDictDlg(mainFrame,
            copy.deepcopy(self.sp.scDict), False)

        if dlg.ShowModal() == wxID_OK:
            self.sp.scDict = dlg.scDict
            self.sp.markChanged()

        dlg.Destroy()

    def OnReportDialogueChart(self):
        self.sp.paginate()
        dialoguechart.genDialogueChart(mainFrame, self.sp, not misc.license)

    def OnReportCharacter(self):
        self.sp.paginate()
        characterreport.genCharacterReport(mainFrame, self.sp,
                                           not misc.license)

    def OnReportLocation(self):
        self.sp.paginate()
        locationreport.genLocationReport(mainFrame, self.sp, not misc.license)

    def OnReportScene(self):
        self.sp.paginate()
        scenereport.genSceneReport(mainFrame, self.sp, not misc.license)

    def OnReportScript(self):
        self.sp.paginate()
        scriptreport.genScriptReport(mainFrame, self.sp, not misc.license)

    def OnCompareScripts(self):
        if mainFrame.notebook.GetPageCount() < 2:
            wxMessageBox("You need at least two scripts open to"
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
            force = dlg.forceSameCfg

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

        if force:
            sp2 = copy.deepcopy(sp2)
            sp2.cfg = copy.deepcopy(sp1.cfg)
            sp2.reformatAll()
            sp2.paginate()
            
        s = sp1.compareScripts(sp2, not misc.license)

        if s:
            gutil.showTempPDF(s, cfgGl, mainFrame)
        else:
            s = "The scripts are identical."
            if not misc.license:
                s += "\n\nHowever, this is the evaluation version of the\n"\
                     "program, which replaces some words in the\n"\
                     "scripts before doing the comparison, which\n"\
                     "might have affected the result."
                
            wxMessageBox(s, "Results", wxOK, mainFrame)

    def canBeClosed(self):
        if self.sp.isModified():
            if wxMessageBox("The script has been modified. Are you sure\n"
                            "you want to discard the changes?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, mainFrame) == wxNO:
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

    def OnCut(self, doUpdate = True, doDelete = True, copyToClip = True):
        marked = self.sp.getMarkedLines()

        if not marked:
            return None

        if not copyToClip and cfgGl.confirmDeletes and (
            (marked[1] - marked[0] + 1) >= cfgGl.confirmDeletes):
            if wxMessageBox("Are you sure you want to delete\n"
                            "the selected text?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxNO:
                return

        cd = self.sp.getSelectedAsCD(doDelete)
        
        if copyToClip:
            mainFrame.clipboard = cd

        if doUpdate:
            self.makeLineVisible(self.sp.line)
            self.updateScreen()

    def OnCopy(self):
        self.OnCut(doDelete = False)

    def OnCopySystemCb(self):
        cd = self.sp.getSelectedAsCD(False)

        if not cd:
            return

        tmpSp = screenplay.Screenplay(cfgGl)
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

        self.sp.paste(clines)
        
        self.makeLineVisible(self.sp.line)
        self.updateScreen()
    
    def OnPasteSystemCb(self):
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
                lines.append(screenplay.Line(screenplay.LB_LAST,
                                             screenplay.ACTION, s))

        self.OnPaste(lines)

    def OnSelectScene(self):
        self.sp.cmd("selectScene")
        
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

        if dlg.ShowModal() == wxID_OK:
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

        if dlg.ShowModal() == wxID_OK:
            page = int(dlg.input)
            self.sp.line = self.sp.page2lines(page)[0]
            self.sp.column = 0

        # we need to refresh the screen in all cases because pagination
        # might have changed
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

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
            
        wxMessageBox(msg, "Results", wxOK, mainFrame)
        
    def OnFind(self):
        self.clearAutoComp()
        
        dlg = finddlg.FindDlg(mainFrame, self)
        dlg.ShowModal()
        dlg.saveState()
        
        if dlg.didReplaces:
            self.sp.reformatAll()
            self.makeLineVisible(self.sp.line)
        
        dlg.Destroy()

        self.searchLine = -1
        self.searchColumn = -1
        self.searchWidth = -1

        self.updateScreen()

    def OnSpellCheckerDlg(self):
        self.clearAutoComp()
        
        wasAtStart = self.sp.line == 0

        wxBeginBusyCursor()
        
        if not spellcheck.loadDict(mainFrame):
            wxEndBusyCursor()
            
            return

        sc = spellcheck.SpellChecker(self.sp, gd.scDict)
        found = sc.findNext()
        
        wxEndBusyCursor()

        if not found:
            s = ""
            
            if not wasAtStart:
                s = "\n\n(Starting position was not at\n"\
                    "the beginning of the script.)"
            wxMessageBox("Spell checker found no errors." + s, "Results",
                         wxOK, mainFrame)

            return

        dlg = spellcheckdlg.SpellCheckDlg(mainFrame, self, sc, gd.scDict)
        dlg.ShowModal()
        
        if dlg.didReplaces:
            self.sp.reformatAll()
            self.makeLineVisible(self.sp.line)

        if dlg.changedGlobalDict:
            gd.saveScDict()
            
        dlg.Destroy()

        self.searchLine = -1
        self.searchColumn = -1
        self.searchWidth = -1

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

        self.sp.removeElementTypes(tdict)
        self.sp.paginate()
        self.makeLineVisible(self.sp.line)
        self.updateScreen()

    def OnSave(self):
        if self.checkEvalSave():
            return
        
        if self.fileName:
            self.saveFile(self.fileName)
        else:
            self.OnSaveScriptAs()

    def OnSaveScriptAs(self):
        if self.checkEvalSave():
            return
        
        dlg = wxFileDialog(mainFrame, "Filename to save as", misc.scriptDir,
            wildcard = "Blyte files (*.blyte)|*.blyte|All files|*",
            style = wxSAVE | wxOVERWRITE_PROMPT)
        if dlg.ShowModal() == wxID_OK:
            misc.scriptDir = dlg.GetDirectory()
            if self.saveFile(dlg.GetPath()):
                gd.mru.add(dlg.GetPath())

        dlg.Destroy()

    def OnExportScript(self):
        sp = self.getExportable("export")
        if not sp:
            return
        
        dlg = wxFileDialog(mainFrame, "Filename to export as",
            misc.scriptDir,
            wildcard = "PDF|*.pdf|RTF|*.rtf|Formatted text|*.txt",
            style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            misc.scriptDir = dlg.GetDirectory()

            choice = dlg.GetFilterIndex()
            if choice == 0:
                data = sp.generatePDF(not misc.license, True)
            elif choice == 1:
                data = sp.generateRTF()
            else:
                data = self.getExportText(sp)

            if data:
                util.writeToFile(dlg.GetPath(), data, mainFrame)

        dlg.Destroy()

    def OnPrint(self):
        sp = self.getExportable("print")
        if not sp:
            return
        
        s = sp.generatePDF(not misc.license, False)
        gutil.showTempPDF(s, cfgGl, mainFrame)

    def OnSettings(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(cfgGl),
                            self.applyGlobalCfg, True)

        if dlg.ShowModal() == wxID_OK:
            self.applyGlobalCfg(dlg.cfg)

        dlg.Destroy()

    def OnScriptSettings(self):
        dlg = cfgdlg.CfgDlg(mainFrame, copy.deepcopy(self.sp.cfg),
                            self.applyCfg, False)

        if dlg.ShowModal() == wxID_OK:
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

    def cmdChangeToTransition(self, cs):
        self.sp.toTransitionCmd(cs)

    def cmdDelete(self, cs):
        if not self.sp.mark:
            self.sp.deleteForwardCmd(cs)
        else:
            self.OnCut(doUpdate = False, copyToClip = False)

    def cmdDeleteBackward(self, cs):
        self.sp.deleteBackwardCmd(cs)

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

    def cmdTest(self, cs):
        pass
    
    def OnKeyChar(self, ev):
        kc = ev.GetKeyCode()

        #print "kc: %d, ctrl/alt/shift: %d, %d, %d" %\
        #      (kc, ev.ControlDown(), ev.AltDown(), ev.ShiftDown())
        
        cs = screenplay.CommandState()
        cs.mark = bool(ev.ShiftDown())

        if not ev.ControlDown() and not ev.AltDown() and \
               util.isValidInputChar(kc):
            cs.char = chr(kc)

            if opts.isTest and (cs.char == "å"):
                self.loadFile("sample.blyte")
            elif opts.isTest and (cs.char == "¤"):
                self.cmdTest(cs)
            else:
                self.sp.addCharCmd(cs)
                
        else:
            cmd = mainFrame.kbdCommands.get(util.Key(kc,
                ev.ControlDown(), ev.AltDown(), ev.ShiftDown()).toInt())

            if cmd:
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
            self.makeLineVisible(self.sp.line)

        self.updateScreen()

    def OnPaint(self, event):
        #ldkjfldsj = util.TimerDev("paint")
        
        ls = self.sp.lines
        dc = wxBufferedPaintDC(self, self.screenBuf)

        size = self.GetClientSize()
        marked = self.sp.getMarkedLines()
        lineh = gd.vm.getLineHeight(self)
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
        
        strings, dpages = gd.vm.getScreen(self, True, True)

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
                    util.drawLine(dc,
                        t.x + self.sp.cfg.getType(l.lt).width * fx, y, 0,
                        lineh)

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
            tw, tmp = dc.GetTextExtent(ac[i])
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

        tmp = wxMenu()

        tmp.Append(ID_SETTINGS_CHANGE, "&Change...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_LOAD, "Load...")
        tmp.Append(ID_SETTINGS_SAVE_AS, "Save as...")
        tmp.AppendSeparator()
        tmp.Append(ID_SETTINGS_SC_DICT, "&Spell checker dictionary...")
        fileMenu.AppendMenu(ID_FILE_SETTINGS, "Se&ttings", tmp)

        fileMenu.AppendSeparator()
        # "most recently used" list comes in here
        fileMenu.AppendSeparator()
        fileMenu.Append(ID_FILE_EXIT, "E&xit\tCTRL-Q")

        editMenu = wxMenu()
        editMenu.Append(ID_EDIT_CUT, "Cu&t\tCTRL-X")
        editMenu.Append(ID_EDIT_COPY, "&Copy\tCTRL-C")
        editMenu.Append(ID_EDIT_PASTE, "&Paste\tCTRL-V")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_COPY_TO_CB, "C&opy (system)")
        editMenu.Append(ID_EDIT_PASTE_FROM_CB, "P&aste (system)")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_SELECT_SCENE, "&Select scene")
        editMenu.Append(ID_EDIT_GOTO_PAGE, "&Goto page...\tCTRL-G")
        editMenu.Append(ID_EDIT_GOTO_SCENE, "Goto sc&ene...\tALT-G")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_FIND, "&Find && Replace...\tCTRL-F")
        editMenu.AppendSeparator()
        editMenu.Append(ID_EDIT_DELETE_ELEMENTS, "&Delete elements...")

        viewMenu = wxMenu()
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_DRAFT, "&Draft")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_LAYOUT, "&Layout")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_SIDE_BY_SIDE, "&Side by side")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_OVERVIEW_SMALL,
                                 "&Overview - Small")
        viewMenu.AppendRadioItem(ID_VIEW_STYLE_OVERVIEW_LARGE,
                                 "O&verview - Large")

        if gd.viewMode == VIEWMODE_DRAFT:
            viewMenu.Check(ID_VIEW_STYLE_DRAFT, True)
        elif gd.viewMode == VIEWMODE_LAYOUT:
            viewMenu.Check(ID_VIEW_STYLE_LAYOUT, True)
        elif gd.viewMode == VIEWMODE_SIDE_BY_SIDE:
            viewMenu.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)
        elif gd.viewMode == VIEWMODE_OVERVIEW_SMALL:
            viewMenu.Check(ID_VIEW_STYLE_OVERVIEW_SMALL, True)
        else:
            viewMenu.Check(ID_VIEW_STYLE_OVERVIEW_LARGE, True)
    
        viewMenu.AppendSeparator()
        viewMenu.AppendCheckItem(ID_VIEW_SHOW_FORMATTING, "&Show formatting")
        
        scriptMenu = wxMenu()
        scriptMenu.Append(ID_SCRIPT_FIND_ERROR, "&Find next error")
        scriptMenu.Append(ID_SCRIPT_PAGINATE, "&Paginate")
        scriptMenu.AppendSeparator()
        scriptMenu.Append(ID_SCRIPT_AUTO_COMPLETION, "&Auto-completion...")
        scriptMenu.Append(ID_SCRIPT_HEADERS, "&Headers...")
        scriptMenu.Append(ID_SCRIPT_LOCATIONS, "&Locations...")
        scriptMenu.Append(ID_SCRIPT_TITLES, "&Title pages...")
        scriptMenu.Append(ID_SCRIPT_SC_DICT, "&Spell checker dictionary...")
        scriptMenu.AppendSeparator()

        tmp = wxMenu()

        tmp.Append(ID_SCRIPT_SETTINGS_CHANGE, "&Change...")
        tmp.AppendSeparator()
        tmp.Append(ID_SCRIPT_SETTINGS_LOAD, "&Load...")
        tmp.Append(ID_SCRIPT_SETTINGS_SAVE_AS, "&Save as...")
        scriptMenu.AppendMenu(ID_SCRIPT_SETTINGS, "&Settings", tmp)

        reportsMenu = wxMenu()
        reportsMenu.Append(ID_REPORTS_SCRIPT_REP, "Sc&ript report")
        reportsMenu.Append(ID_REPORTS_LOCATION_REP, "&Location report...")
        reportsMenu.Append(ID_REPORTS_SCENE_REP, "&Scene report...")
        reportsMenu.Append(ID_REPORTS_CHARACTER_REP, "&Character report...")
        reportsMenu.Append(ID_REPORTS_DIALOGUE_CHART, "&Dialogue chart...")
        
        toolsMenu = wxMenu()
        toolsMenu.Append(ID_TOOLS_SPELL_CHECK, "&Spell checker...")
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

        for t in config.getTIs():
            self.typeCb.Append(t.name, t.lt)

        # this is hidden here because it's somewhat harder to find here
        # than in misc.pyo
        misc.version = "1.2-dev"

        # slightly obfuscated in a desperate attempt to fool at least some
        # people...
        misc.releaseDate = datetime.date(500 * 4 + 5, 10 - 2, -4 + 11)

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

        gd.mru.useMenu(fileMenu, 14)

        EVT_MENU_HIGHLIGHT_ALL(self, self.OnMenuHighlight)
        
        EVT_NOTEBOOK_PAGE_CHANGED(self, self.notebook.GetId(),
                                  self.OnPageChange)
        
        EVT_COMBOBOX(self, self.typeCb.GetId(), self.OnTypeCombo)

        EVT_MENU(self, ID_FILE_NEW, self.OnNewScript)
        EVT_MENU(self, ID_FILE_OPEN, self.OnOpen)
        EVT_MENU(self, ID_FILE_SAVE, self.OnSave)
        EVT_MENU(self, ID_FILE_SAVE_AS, self.OnSaveScriptAs)
        EVT_MENU(self, ID_FILE_IMPORT, self.OnImportScript)
        EVT_MENU(self, ID_FILE_EXPORT, self.OnExportScript)
        EVT_MENU(self, ID_FILE_CLOSE, self.OnCloseScript)
        EVT_MENU(self, ID_FILE_REVERT, self.OnRevertScript)
        EVT_MENU(self, ID_FILE_PRINT, self.OnPrint)
        EVT_MENU(self, ID_SETTINGS_CHANGE, self.OnSettings)
        EVT_MENU(self, ID_SETTINGS_LOAD, self.OnLoadSettings)
        EVT_MENU(self, ID_SETTINGS_SAVE_AS, self.OnSaveSettingsAs)
        EVT_MENU(self, ID_SETTINGS_SC_DICT, self.OnSpellCheckerDictionaryDlg)
        EVT_MENU(self, ID_FILE_EXIT, self.OnExit)
        EVT_MENU(self, ID_EDIT_CUT, self.OnCut)
        EVT_MENU(self, ID_EDIT_COPY, self.OnCopy)
        EVT_MENU(self, ID_EDIT_PASTE, self.OnPaste)
        EVT_MENU(self, ID_EDIT_COPY_TO_CB, self.OnCopySystemCb)
        EVT_MENU(self, ID_EDIT_PASTE_FROM_CB, self.OnPasteSystemCb)
        EVT_MENU(self, ID_EDIT_SELECT_SCENE, self.OnSelectScene)
        EVT_MENU(self, ID_EDIT_GOTO_PAGE, self.OnGotoPage)
        EVT_MENU(self, ID_EDIT_GOTO_SCENE, self.OnGotoScene)
        EVT_MENU(self, ID_EDIT_FIND, self.OnFind)
        EVT_MENU(self, ID_EDIT_DELETE_ELEMENTS, self.OnDeleteElements)
        EVT_MENU(self, ID_VIEW_STYLE_DRAFT, self.OnViewModeChange)
        EVT_MENU(self, ID_VIEW_STYLE_LAYOUT, self.OnViewModeChange)
        EVT_MENU(self, ID_VIEW_STYLE_SIDE_BY_SIDE, self.OnViewModeChange)
        EVT_MENU(self, ID_VIEW_STYLE_OVERVIEW_SMALL, self.OnViewModeChange)
        EVT_MENU(self, ID_VIEW_STYLE_OVERVIEW_LARGE, self.OnViewModeChange)
        EVT_MENU(self, ID_VIEW_SHOW_FORMATTING, self.OnShowFormatting)
        EVT_MENU(self, ID_SCRIPT_FIND_ERROR, self.OnFindNextError)
        EVT_MENU(self, ID_SCRIPT_PAGINATE, self.OnPaginate)
        EVT_MENU(self, ID_SCRIPT_AUTO_COMPLETION, self.OnAutoCompletionDlg)
        EVT_MENU(self, ID_SCRIPT_HEADERS, self.OnHeadersDlg)
        EVT_MENU(self, ID_SCRIPT_LOCATIONS, self.OnLocationsDlg)
        EVT_MENU(self, ID_SCRIPT_TITLES, self.OnTitlesDlg)
        EVT_MENU(self, ID_SCRIPT_SC_DICT,
                 self.OnSpellCheckerScriptDictionaryDlg)
        EVT_MENU(self, ID_SCRIPT_SETTINGS_CHANGE, self.OnScriptSettings)
        EVT_MENU(self, ID_SCRIPT_SETTINGS_LOAD, self.OnLoadScriptSettings)
        EVT_MENU(self, ID_SCRIPT_SETTINGS_SAVE_AS, self.OnSaveScriptSettingsAs)
        EVT_MENU(self, ID_REPORTS_DIALOGUE_CHART, self.OnReportDialogueChart)
        EVT_MENU(self, ID_REPORTS_CHARACTER_REP, self.OnReportCharacter)
        EVT_MENU(self, ID_REPORTS_SCRIPT_REP, self.OnReportScript)
        EVT_MENU(self, ID_REPORTS_LOCATION_REP, self.OnReportLocation)
        EVT_MENU(self, ID_REPORTS_SCENE_REP, self.OnReportScene)
        EVT_MENU(self, ID_TOOLS_SPELL_CHECK, self.OnSpellCheckerDlg)
        EVT_MENU(self, ID_TOOLS_NAME_DB, self.OnNameDatabase)
        EVT_MENU(self, ID_TOOLS_CHARMAP, self.OnCharacterMap)
        EVT_MENU(self, ID_TOOLS_COMPARE_SCRIPTS, self.OnCompareScripts)
        EVT_MENU(self, ID_HELP_COMMANDS, self.OnHelpCommands)
        EVT_MENU(self, ID_HELP_MANUAL, self.OnHelpManual)
        EVT_MENU(self, ID_HELP_ABOUT, self.OnAbout)
        EVT_MENU(self, ID_LICENSE_INFO, self.OnLicenseInfo)
        EVT_MENU(self, ID_LICENSE_UPDATE, self.OnUpdateLicense)
        EVT_MENU(self, ID_LICENSE_RELEASE, self.OnReleaseLicense)
        EVT_MENU_RANGE(self, gd.mru.getIds()[0], gd.mru.getIds()[1],
                       self.OnMRUFile)

        EVT_CLOSE(self, self.OnCloseWindow)

        self.Layout()
        
    def init(self):
        self.updateKbdCommands()
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
            "ID_EDIT_GOTO_SCENE",
            "ID_EDIT_GOTO_PAGE",
            "ID_EDIT_PASTE",
            "ID_EDIT_PASTE_FROM_CB",
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
            "ID_HELP_LICENSE",
            "ID_HELP_MANUAL",
            "ID_LICENSE_INFO",
            "ID_LICENSE_RELEASE",
            "ID_LICENSE_UPDATE",
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
            "ID_VIEW_SHOW_FORMATTING",
            "ID_VIEW_STYLE_DRAFT",
            "ID_VIEW_STYLE_LAYOUT",
            "ID_VIEW_STYLE_OVERVIEW_LARGE",
            "ID_VIEW_STYLE_OVERVIEW_SMALL",
            "ID_VIEW_STYLE_SIDE_BY_SIDE",
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
            if c.sp.isModified():
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
                util.writeToFile(gd.stateFilename, gd.save(), frame)

                wxMessageBox("License successfully updated.",
                             "Information", wxOK, frame)

    def updateKbdCommands(self):
        cfgGl.addShiftKeys()
        
        if cfgGl.getConflictingKeys() != None:
            wxMessageBox("You have at least one key bound to more than one\n"
                         "command. The program will not work correctly until\n"
                         "you fix this.",
                         "Warning", wxOK, self)

        self.kbdCommands = {}

        for cmd in cfgGl.commands:
            if not (cmd.isFixed and cmd.isMenu):
                for key in cmd.keys:
                    self.kbdCommands[key] = cmd

    # open script, in the current tab if it's untouched, or in a new one
    # otherwise
    def openScript(self, filename):
        if not self.notebook.GetPage(self.findPage(self.panel))\
               .ctrl.isUntouched():
            self.panel = self.createNewPanel()

        self.panel.ctrl.loadFile(filename)
        self.panel.ctrl.updateScreen()
        gd.mru.add(filename)
        
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

    def OnNewScript(self, event = None):
        self.panel = self.createNewPanel()

    def OnMRUFile(self, event):
        i = event.GetId() - gd.mru.getIds()[0]
        self.openScript(gd.mru.get(i))

    def OnOpen(self, event = None):
        dlg = wxFileDialog(self, "File to open", misc.scriptDir,
            wildcard = "Blyte files (*.blyte)|*.blyte|All files|*",
            style = wxOPEN)
        
        if dlg.ShowModal() == wxID_OK:
            misc.scriptDir = dlg.GetDirectory()
            self.openScript(dlg.GetPath())

        dlg.Destroy()

    def OnSave(self, event = None):
        self.panel.ctrl.OnSave()

    def OnSaveScriptAs(self, event = None):
        self.panel.ctrl.OnSaveScriptAs()

    def OnImportScript(self, event = None):
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

    def OnExportScript(self, event = None):
        self.panel.ctrl.OnExportScript()

    def OnCloseScript(self, event = None):
        if not self.panel.ctrl.canBeClosed():
            return
        
        if self.notebook.GetPageCount() > 1:
            self.notebook.DeletePage(self.findPage(self.panel))
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
        dlg = wxFileDialog(self, "File to open",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wxOPEN)

        if dlg.ShowModal() == wxID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                c = config.ConfigGlobal()
                c.load(s)
                gd.confFilename = dlg.GetPath()
                
                self.panel.ctrl.applyGlobalCfg(c, False)

        dlg.Destroy()

    def OnSaveSettingsAs(self, event = None):
        dlg = wxFileDialog(self, "Filename to save as",
            defaultDir = os.path.dirname(gd.confFilename),
            defaultFile = os.path.basename(gd.confFilename),
            wildcard = "Setting files (*.conf)|*.conf|All files|*",
            style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            if util.writeToFile(dlg.GetPath(), cfgGl.save(), self):
                gd.confFilename = dlg.GetPath()
            
        dlg.Destroy()

    def OnCut(self, event = None):
        self.panel.ctrl.OnCut()

    def OnCopy(self, event = None):
        self.panel.ctrl.OnCopy()

    def OnCopySystemCb(self, event = None):
        self.panel.ctrl.OnCopySystemCb()

    def OnPaste(self, event = None):
        self.panel.ctrl.OnPaste()

    def OnPasteSystemCb(self, event = None):
        self.panel.ctrl.OnPasteSystemCb()

    def OnSelectScene(self, event = None):
        self.panel.ctrl.OnSelectScene()

    def OnGotoPage(self, event = None):
        self.panel.ctrl.OnGotoPage()

    def OnGotoScene(self, event = None):
        self.panel.ctrl.OnGotoScene()

    def OnFindNextError(self, event = None):
        self.panel.ctrl.OnFindNextError()

    def OnFind(self, event = None):
        self.panel.ctrl.OnFind()

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

    def OnViewModeOverviewSmall(self):
        self.menuBar.Check(ID_VIEW_STYLE_OVERVIEW_SMALL, True)
        self.OnViewModeChange()

    def OnViewModeOverviewLarge(self):
        self.menuBar.Check(ID_VIEW_STYLE_OVERVIEW_LARGE, True)
        self.OnViewModeChange()

    def OnViewModeChange(self, event = None):
        if self.menuBar.IsChecked(ID_VIEW_STYLE_DRAFT):
            mode = VIEWMODE_DRAFT
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_LAYOUT):
            mode = VIEWMODE_LAYOUT
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_SIDE_BY_SIDE):
            mode = VIEWMODE_SIDE_BY_SIDE
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_OVERVIEW_SMALL):
            mode = VIEWMODE_OVERVIEW_SMALL
        else:
            mode = VIEWMODE_OVERVIEW_LARGE

        gd.setViewMode(mode)

        for c in self.getCtrls():
            c.refreshCache()
        
        c = self.panel.ctrl
        c.makeLineVisible(c.sp.line)
        c.updateScreen()

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

        if dlg.ShowModal() == wxID_OK:
            gd.scDict = dlg.scDict
            gd.saveScDict()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self, event = None):
        self.panel.ctrl.OnSpellCheckerScriptDictionaryDlg()

    def OnScriptSettings(self, event = None):
        self.panel.ctrl.OnScriptSettings()

    def OnLoadScriptSettings(self, event = None):
        dlg = wxFileDialog(self, "File to open",
            defaultDir = gd.scriptSettingsPath,
            wildcard = "Script setting files (*.sconf)|*.sconf|All files|*",
            style = wxOPEN)

        if dlg.ShowModal() == wxID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                self.panel.ctrl.sp.loadCfg(s)

                # kinda hacky, but very simple and works
                self.panel.ctrl.applyCfg(self.panel.ctrl.sp.cfg)
                
                gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnSaveScriptSettingsAs(self, event = None):
        dlg = wxFileDialog(self, "Filename to save as",
            defaultDir = gd.scriptSettingsPath,
            wildcard = "Script setting files (*.sconf)|*.sconf|All files|*",
            style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            if util.writeToFile(dlg.GetPath(),
                                self.panel.ctrl.sp.saveCfg(), self):
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

    def OnCharacterMap(self, event = None):
        dlg = charmapdlg.CharMapDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCompareScripts(self, event = None):
        self.panel.ctrl.OnCompareScripts()

    def OnHelpCommands(self, event = None):
        dlg = commandsdlg.CommandsDlg(cfgGl)
        dlg.Show()

    def OnHelpManual(self, event = None):
        util.showPDF(misc.progPath + "/manual.pdf", cfgGl, self)
        
    def OnAbout(self, event = None):
        win = splash.SplashWindow(self, -1)
        win.Show()

    def OnLicenseInfo(self, event = None):
        if misc.license:
            s = "Licensed to: '%s'\n" % misc.license.userId.lstrip()

            s += "License type: %s\n" % misc.license.getTypeStr()
            s += "Upgradable until: %s\n" % misc.license.lastDate.isoformat()

        else:
            s = "Evaluation copy."

        wxMessageBox(s, "License info", wxOK, self)
        
    def OnUpdateLicense(self, event = None):
        dlg = wxFileDialog(self, "License file to open", ".",
            wildcard = "License files (*.lic)|*.lic|All files|*",
            style = wxOPEN)
        
        if dlg.ShowModal() == wxID_OK:
            data = util.loadFile(dlg.GetPath(), self)

            if data != None:
                self.setLicense(data, self, False);

        dlg.Destroy()
    
    def OnReleaseLicense(self, event = None):
        if misc.license == None:
            wxMessageBox("You already are in evaluation mode.", "Error",
                         wxOK, self)
        else:
            if wxMessageBox("Are you sure you want to release your\n"
                            "license information, i.e. go back to\n"
                            "evaluation mode?", "Confirm",
                            wxYES_NO | wxNO_DEFAULT, self) == wxYES:
                misc.license = None
                gd.license = ""
                util.writeToFile(gd.stateFilename, gd.save(), self)

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
            util.writeToFile(gd.stateFilename, gd.save(), self)
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
        global cfgGl, mainFrame, gd

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
        if misc.isUnix and not opts.isTest:
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
        
        cfgGl = config.ConfigGlobal()

        if util.fileExists(gd.confFilename):
            s = util.loadFile(gd.confFilename, None)

            if s:
                cfgGl.load(s)
        else:
            # we want to write out a default config file at startup
            # for various reasons, if no default config file yet
            # exists
            util.writeToFile(gd.confFilename, cfgGl.save(), None)

        refreshGuiConfig()

        # cfgGl.scriptDir is the directory used on startup, while
        # misc.scriptDir is updated every time the user opens/saves
        # something in a different directory.
        misc.scriptDir = cfgGl.scriptDir

        if util.fileExists(gd.stateFilename):
            s = util.loadFile(gd.stateFilename, None)

            if s:
                gd.load(s)
                
        gd.setViewMode(gd.viewMode)

        if util.fileExists(gd.scDictFilename):
            s = util.fromUTF8(util.loadFile(gd.scDictFilename, None))

            if s:
                gd.scDict.load(s)
        
        mainFrame = MyFrame(NULL, -1, "Blyte")
        bugreport.mainFrame = mainFrame
        mainFrame.init()
        
        for arg in opts.filenames:
            mainFrame.openScript(arg)

        mainFrame.Show(True)

        # windows needs this for some reason
        mainFrame.panel.ctrl.SetFocus()
        
        self.SetTopWindow(mainFrame)

        if not opts.isTest:
            win = splash.SplashWindow(mainFrame, 2500)
            win.Show()
            win.Raise()
        
        return True

def main():
    global myApp

    opts.init()
    
    if not opts.isTest:
        brh = bugreport.BugReportHandler()
        sys.stdout = brh
        sys.stderr = brh
    
    myApp = MyApp(0)
    myApp.MainLoop()

main()
