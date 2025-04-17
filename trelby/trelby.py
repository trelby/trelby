# -*- coding: iso-8859-1 -*-

import os
import os.path
import sys

import wx

import trelby
import trelby.config as config
import trelby.misc as misc
import trelby.opts as opts
import trelby.splash as splash
import trelby.util as util
from trelby.globaldata import GlobalData
from trelby.trelbyframe import MyFrame

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


class MyApp(wx.App):

    def OnInit(self):

        if (wx.MAJOR_VERSION != 4) or (wx.MINOR_VERSION < 0):
            wx.MessageBox(
                "You seem to have an invalid version\n"
                "(%s) of wxWidgets installed. This\n"
                "program needs version 4.x." % wx.VERSION_STRING,
                "Error",
                wx.OK,
            )
            sys.exit()

        misc.init()
        util.init()

        gd = GlobalData()

        if misc.isWindows:
            major = sys.getwindowsversion()[0]
            if major < 5:
                wx.MessageBox(
                    "You seem to have a version of Windows\n"
                    "older than Windows 2000, which is the minimum\n"
                    "requirement for this program.",
                    "Error",
                    wx.OK,
                )
                sys.exit()

        if not "unicode" in wx.PlatformInfo:
            wx.MessageBox(
                "You seem to be using a non-Unicode build of\n"
                "wxWidgets. This is not supported.",
                "Error",
                wx.OK,
            )
            sys.exit()

        os.chdir(misc.progPath)

        cfgGl = config.ConfigGlobal()
        gd.cfgGl = cfgGl
        cfgGl.setDefaults()

        if util.fileExists(gd.confFilename):
            s = util.loadFile(gd.confFilename, None)

            if s:
                cfgGl.load(s)
        else:
            # we want to write out a default config file at startup for
            # various reasons, if no default config file yet exists
            util.writeToFile(gd.confFilename, cfgGl.save(), None)

        # refreshGuiConfig()
        gd.cfgGui = config.ConfigGui(gd.cfgGl)

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

        mainFrame = MyFrame(None, -1, "Trelby", gd, self)
        gd.mainFrame = mainFrame
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
    opts.init()

    myApp = MyApp(0)

    myApp.MainLoop()
