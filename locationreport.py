import misc
import pdf
import pml
import scenereport
import screenplay
import util

from wxPython.wx import *

# FIXME: Screenplay should contain information about which scenes
# constitute a location, and that should be saved/loaded. is it config
# data or script data? good question...it also needs a config GUI.

def genLocationReport(mainFrame, sp):
    report = LocationReport(scenereport.SceneReport(sp))

    dlg = misc.CheckBoxDlg(mainFrame, "Report type", report.inf,
        "Information to include:", False)

    ok = False
    if dlg.ShowModal() == wxID_OK:
        ok = True

    dlg.Destroy()

    if not ok:
        return
    
    data = report.generate()

    util.showTempPDF(data, sp.cfgGl, mainFrame)

class LocationReport:
    # sr = SceneReport
    def __init__(self, sr):
        self.sp = sr.sp

        # location mapping. a list of lists of strings, where the strings
        # are scene names and the inner list lists scenes to combine into
        # one location.
        # FIXME: get this from screenplay
        locMap = [
            ["INT. ROOM 413 - DAY.",
             "INT. ROOM 413 - (CONTINUOUS) - DAY.",
             "INT. ROOM 413 - DAWN.",
             "INT. ROOM 413 - NIGHT."]
            ]

        # key = scene name, value = LocationInfo. note that multiple keys
        # can point to the same LocationInfo.
        locations = {}

        # like locations, but this one stores per-scene information
        self.scenes = {}
        
        # make grouped scenes point to the same LocationInfos.
        for sceneList in locMap:
            li = LocationInfo(self.sp)
            
            for scene in sceneList:
                locations[scene] = li

        # merge scene information
        for si in sr.scenes:
            li = locations.setdefault(si.name, LocationInfo(self.sp)).\
                 addScene(si)
            li = self.scenes.setdefault(si.name, LocationInfo(self.sp)).\
                 addScene(si)

        # remove empty LocationInfos, sort them (and their contents), and
        # store to a list
        tmp = []
        for li in locations.itervalues():
            if (len(li.scenes) > 0) and (li not in tmp):
                li.scenes.sort()
                tmp.append(li)

        def sortFunc(o1, o2):
            ret = cmp(o2.lines, o1.lines)

            if ret != 0:
                return ret
            else:
                return cmp(o1.scenes[0], o2.scenes[0])

        tmp.sort(sortFunc)

        self.locations = tmp

        # information about what to include (and yes, the comma is needed
        # to unpack the list)
        self.INF_SPEAKERS, = range(1)
        self.inf = []
        for s in ["Speakers"]:
            self.inf.append(misc.CheckBoxItem(s))

    def generate(self):
        tf = pml.TextFormatter(self.sp.cfg.paperWidth,
                               self.sp.cfg.paperHeight, 15.0, 12)

        scriptLines = sum([li.lines for li in self.locations])

        for li in self.locations:
            tf.addSpace(5.0)

            # FIXME: sort by tmp (&name), highest first
            for scene in li.scenes:
                if len(li.scenes) > 1:
                    tmp = " (%d%%)" % util.pct(self.scenes[scene].lines,
                                               li.lines)
                else:
                    tmp = ""

                tf.addText("%s%s" % (scene, tmp), style = pml.BOLD)

            tf.addSpace(1.0)

            tf.addWrappedText("Lines: %d (%d%% action, %d%% of script),"
                " Scenes: %d, Pages: %d (%s)" % (li.lines,
                util.pct(li.actionLines, li.lines),
                util.pct(li.lines, scriptLines), li.sceneCount,
                len(li.pages), li.pages), "  ")
            

            if self.inf[self.INF_SPEAKERS].selected:
                tf.addSpace(2.5)
                
                for it in util.sortDict(li.chars):
                    tf.addText("     %3d  %s" % (it[1], it[0]))
            
        return pdf.generate(tf.doc)

# information about one location
class LocationInfo:
    def __init__(self, sp):
        # number of scenes
        self.sceneCount = 0
        
        # scene names, e.g. ["INT. MOTEL ROOM - NIGHT", "EXT. MOTEL -
        # NIGHT"]
        self.scenes = []

        # total lines, excluding scene lines
        self.lines = 0

        # action lines
        self.actionLines = 0

        # page numbers
        self.pages = screenplay.PageList(sp.getPageNumbers())

        # key = character name (upper cased), value = number of dialogue
        # lines
        self.chars = {}

    # add a scene. si = SceneInfo
    def addScene(self, si):
        if si.name not in self.scenes:
            self.scenes.append(si.name)
        
        self.sceneCount += 1
        self.lines += si.lines
        self.actionLines += si.actionLines
        self.pages += si.pages

        for name, dlines in si.chars.iteritems():
            self.chars[name] = self.chars.get(name, 0) + dlines
