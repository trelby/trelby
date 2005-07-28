import misc
import pdf
import pml
import scenereport
import screenplay
import util

from wxPython.wx import *

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

        # key = scene name, value = LocationInfo. note that multiple keys
        # can point to the same LocationInfo.
        locations = {}

        # like locations, but this one stores per-scene information
        self.scenes = {}
        
        # make grouped scenes point to the same LocationInfos.
        for sceneList in self.sp.locations.locations:
            li = LocationInfo(self.sp)
            
            for scene in sceneList:
                locations[scene] = li

        # merge scene information for locations and store scene
        # information
        for si in sr.scenes:
            locations.setdefault(si.name, LocationInfo(self.sp)).addScene(si)

            self.scenes.setdefault(si.name, LocationInfo(self.sp)).\
                 addScene(si)

        # remove empty LocationInfos, sort them and store to a list
        tmp = []
        for li in locations.itervalues():
            if (len(li.scenes) > 0) and (li not in tmp):
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

            # list of (scenename, lines_in_scene) tuples, which we sort in
            # DESC(lines_in_scene) ASC(scenename) order.
            tmp = [(scene, self.scenes[scene].lines) for scene in li.scenes]

            # PY2.4: this should work (test it):
            #  tmp.sort(key=itemgetter(0))
            #  tmp.sort(key=itemgetter(1) reverse=True)
            tmp.sort(lambda x, y: cmp(x[0], y[0]))
            tmp.reverse()
            tmp.sort(lambda x, y: cmp(x[1], y[1]))
            tmp.reverse()
            
            for scene, lines in tmp:
                if len(tmp) > 1:
                    pct = " (%d%%)" % util.pct(lines, li.lines)
                else:
                    pct = ""

                tf.addText("%s%s" % (scene, pct), style = pml.BOLD)

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
