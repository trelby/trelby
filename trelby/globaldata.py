# -*- coding: iso-8859-1 -*-

import os
import os.path

import wx

import trelby.misc as misc
import trelby.mypickle as mypickle
import trelby.opts as opts
import trelby.spellcheck as spellcheck
import trelby.util as util
import trelby.viewmode as viewmode


# keeps (hopefully all) global data
class GlobalData:

    # global variables previously floating around the trelby.py file
    mainFrame = None
    cfgGui = None
    cfgGl = None

    # constants
    (
        VIEWMODE_DRAFT,
        VIEWMODE_LAYOUT,
        VIEWMODE_SIDE_BY_SIDE,
    ) = list(range(3))

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
        v.addInt(
            "viewMode",
            self.VIEWMODE_DRAFT,
            "ViewMode",
            self.VIEWMODE_DRAFT,
            self.VIEWMODE_SIDE_BY_SIDE,
        )

        v.addList("files", [], "Files", mypickle.StrUnicodeVar("", "", ""))

        v.makeDicts()
        v.setDefaults(self)

        self.height = min(
            self.height, wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y) - 50
        )

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
                wx.MessageBox(
                    "Error creating configuration directory\n"
                    "'%s': %s" % (misc.confPath, os.strerror),
                    "Error",
                    wx.OK,
                    None,
                )

    # set viewmode, the parameter is one of the VIEWMODE_ defines.
    def setViewMode(self, viewMode):
        self.viewMode = viewMode

        if viewMode == self.VIEWMODE_DRAFT:
            self.vm = self.vmDraft
        elif viewMode == self.VIEWMODE_LAYOUT:
            self.vm = self.vmLayout
        elif viewMode == self.VIEWMODE_SIDE_BY_SIDE:
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
        util.writeToFile(self.scDictFilename, self.scDict.save(), self.mainFrame)
