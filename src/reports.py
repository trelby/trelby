import gutil
import misc
import util

import characterreport
import locationreport
import scenereport
import scriptreport

import wx

def genSceneReport(mainFrame, sp):
    report = scenereport.SceneReport(sp)

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False)

    ok = False
    if dlg.ShowModal() == wx.ID_OK:
        ok = True

    dlg.Destroy()

    if not ok:
        return

    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

def genLocationReport(mainFrame, sp):
    report = locationreport.LocationReport(scenereport.SceneReport(sp))

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False)

    ok = False
    if dlg.ShowModal() == wx.ID_OK:
        ok = True

    dlg.Destroy()

    if not ok:
        return

    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

def genCharacterReport(mainFrame, sp):
    report = characterreport.CharacterReport(sp)

    if not report.cinfo:
        wx.MessageBox("No characters speaking found.",
                      "Error", wx.OK, mainFrame)

        return

    charNames = []
    for s in util.listify(report.cinfo, "name"):
        charNames.append(misc.CheckBoxItem(s))

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False, charNames,
        "Characters to include:", True)

    ok = False
    if dlg.ShowModal() == wx.ID_OK:
        ok = True

        for i in range(len(report.cinfo)):
            report.cinfo[i].include = charNames[i].selected

    dlg.Destroy()

    if not ok:
        return

    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)

def genScriptReport(mainFrame, sp):
    report = scriptreport.ScriptReport(sp)
    data = report.generate()

    gutil.showTempPDF(data, sp.cfgGl, mainFrame)
