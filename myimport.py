import config
import screenplay
import util

import re

from wxPython.wx import *

# special linetype that means that indent contains action and scene lines,
# and scene lines are the ones that begin with "EXT." or "INT."
SCENE_ACTION = -2
    
# import text file from fileName, return list of Line objects for the
# screenplay or None if something went wrong. returned list always
# contains at least one line.
def importTextFile(fileName, frame):

    # the 1 MB limit is arbitrary, we just want to avoid getting a
    # MemoryError exception for /dev/zero etc.
    data = util.loadFile(fileName, frame, 1000000)

    if data == None:
        return None

    if len(data) == 0:
        wxMessageBox("File is empty.", "Error", wxOK, frame)

        return

    data = util.fixNL(data)
    lines = data.split("\n")

    tabWidth = 4

    # key = indent level, value = Indent
    indDict = {}

    for i in range(len(lines)):
        s = util.toInputStr(lines[i].rstrip().expandtabs(tabWidth))

        # don't count empty lines towards indentation statistics
        if s.strip() == "":
            lines[i] = ""

            continue

        cnt = util.countInitial(s, " ")

        ind = indDict.get(cnt)
        if not ind:
            ind = Indent(cnt)
            indDict[cnt] = ind

        tmp = s.upper()

        if util.multiFind(tmp, ["EXT.", "INT."]):
            ind.sceneStart += 1

        if util.multiFind(tmp, ["CUT TO:", "DISSOLVE TO:"]):
            ind.trans += 1

        if re.match(r"^ +\(.*\)$", tmp):
            ind.paren += 1

        ind.lines.append(s.lstrip())
        lines[i] = s

    if len(indDict) == 0:
        wxMessageBox("File contains only empty lines.", "Error", wxOK, frame)

        return

    # scene/action indent
    setType(SCENE_ACTION, indDict, lambda v: v.sceneStart)

    # indent with most lines is dialogue in non-pure-action scripts
    setType(config.DIALOGUE, indDict, lambda v: len(v.lines))

    # remaining indent with lines is character most likely
    setType(config.CHARACTER, indDict, lambda v: len(v.lines))

    # transitions
    setType(config.TRANSITION, indDict, lambda v: v.trans)
    
    # parentheticals
    setType(config.PAREN, indDict, lambda v: v.paren)

    # some text files have this type of parens:
    #
    #        JOE
    #      (smiling and
    #       hopping along)
    #
    # this handles them.
    parenIndent = findIndent(indDict, lambda v: v.lt == config.PAREN)
    if parenIndent != -1:
        paren2Indent = findIndent(indDict,
            lambda v, var: (v.lt == -1) and (v.indent == var),
            parenIndent + 1)

        if paren2Indent != -1:
            indDict[paren2Indent].lt = config.PAREN
    
    # set line type to ACTION for any indents not recognized
    for v in indDict.itervalues():
        if v.lt == -1:
            v.lt = config.ACTION

    dlg = ImportDlg(frame, indDict.values())

    if dlg.ShowModal() != wxID_OK:
        dlg.Destroy()

        return

    dlg.Destroy()
        
    ret = []

    for i in range(len(lines)):
        s = lines[i]
        cnt = util.countInitial(s, " ")
        s = s.lstrip()
        sUp = s.upper()
        
        if s:
            lt = indDict[cnt].lt

            if lt == SCENE_ACTION:
                if s.startswith("EXT.") or s.startswith("INT."):
                    lt = config.SCENE
                else:
                    lt = config.ACTION

            if ret and (ret[-1].lt != lt):
                ret[-1].lb = config.LB_LAST

            if lt == config.CHARACTER:
                if sUp.endswith("(CONT'D)"):
                    s = sUp[:-8].rstrip()

            elif lt == config.PAREN:
                if s == "(continuing)":
                    s = ""

            if s:
                line = screenplay.Line(config.LB_AUTO_SPACE, lt, s)
                ret.append(line)

        elif ret:
            ret[-1].lb = config.LB_LAST

    if len(ret) == 0:
        ret.append(screenplay.Line(config.LB_LAST, config.ACTION))

    # make sure the last line ends an element
    ret[-1].lb = config.LB_LAST
    
    return ret

# go through indents, find the one with maximum value in something, and
# set its linetype to given lt.
def setType(lt, indDict, func):
    maxCount = 0
    found = -1
    
    for v in indDict.itervalues():
        # don't touch indents already set
        if v.lt != -1:
            continue
        
        val = func(v)

        if val > maxCount:
            maxCount = val
            found = v.indent

    if found != -1:
        indDict[found].lt = lt

# go through indents calling func(it, *vars) on each. return indent count
# for the indent func returns True, or -1 if it returns False for each.
def findIndent(indDict, func, *vars):
    for v in indDict.itervalues():
        if func(v, *vars):
            return v.indent

    return -1

# information about one indent level in imported text files.
class Indent:
    def __init__(self, indent):

        # indent level, i.e. spaces at the beginning
        self.indent = indent

        # lines with this indent, leading spaces removed
        self.lines = []

        # assigned line type, or -1 if not assigned yet.
        self.lt = -1

        # how many of the lines start with "EXT." or "INT."
        self.sceneStart = 0

        # how many of the lines have "CUT TO:" or "DISSOLVE TO:"
        self.trans = 0

        # how many of the lines have a form of "^ +\(.*)$", i.e. are most
        # likely parentheticals
        self.paren = 0


class ImportDlg(wxDialog):
    def __init__(self, parent, indents):
        wxDialog.__init__(self, parent, -1, "Adjust styles",
                          style = wxDEFAULT_DIALOG_STYLE)

        self.SetClientSizeWH(500, 500);
        self.Center()

        indents.sort(lambda i1, i2: -cmp(len(i1.lines), len(i2.lines)))
        
        panel = wxPanel(self, -1)
        
        vsizer = wxBoxSizer(wxVERTICAL)

        tmp = wxStaticText(panel, -1, "Input:")
        vsizer.Add(tmp)
        
        self.inputLb = wxListBox(panel, -1, size = (200, 200))
        for it in indents:
            self.inputLb.Append("%d lines (indented %d characters)" %
                                (len(it.lines), it.indent), it)
            
        vsizer.Add(self.inputLb, 1, wxEXPAND)

        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(panel, -1, "Style:"), 0,
                   wxALIGN_CENTER_VERTICAL)
        self.styleCombo = wxComboBox(panel, -1, style = wxCB_READONLY)

        cfg = config.currentCfg
        
        self.styleCombo.Append("Scene / Action", SCENE_ACTION)
        for t in cfg.types.values():
            self.styleCombo.Append(t.name, t.lt)

        util.setWH(self.styleCombo, w = 125)
        
        hsizer.Add(self.styleCombo, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxTOP | wxBOTTOM, 10)

        vsizer.Add(wxStaticText(panel, -1, "Lines:"))

        self.linesEntry = wxTextCtrl(panel, -1, style = wxTE_MULTILINE |
                                     wxTE_DONTWRAP )
        vsizer.Add(self.linesEntry, 2, wxEXPAND)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)

        hsizer.Add(1, 1, 1)
        
        cancelBtn = wxButton(panel, -1, "Cancel")
        hsizer.Add(cancelBtn)
        
        okBtn = wxButton(panel, -1, "OK")
        hsizer.Add(okBtn, 0, wxLEFT, 10)

        vsizer.Add(hsizer, 0, wxEXPAND | wxTOP, 10)

        panel.SetSizer(vsizer)

        vmsizer = wxBoxSizer(wxVERTICAL)
        vmsizer.Add(panel, 1, wxEXPAND | wxALL, 10)
        
        self.SetSizer(vmsizer)

        EVT_COMBOBOX(self, self.styleCombo.GetId(), self.OnStyleCombo)
        EVT_LISTBOX(self, self.inputLb.GetId(), self.OnInputLb)
        
        EVT_BUTTON(self, cancelBtn.GetId(), self.OnCancel)
        EVT_BUTTON(self, okBtn.GetId(), self.OnOK)

        self.inputLb.SetSelection(0)
        self.OnInputLb()
        
    def OnOK(self, event):
        self.EndModal(wxID_OK)

    def OnCancel(self, event):
        self.EndModal(wxID_CANCEL)

    def OnInputLb(self, event = None):
        ind = self.inputLb.GetClientData(self.inputLb.GetSelection())

        util.reverseComboSelect(self.styleCombo, ind.lt)
        self.linesEntry.SetValue("\n".join(ind.lines))

    def OnStyleCombo(self, event):
        ind = self.inputLb.GetClientData(self.inputLb.GetSelection())
        ind.lt = self.styleCombo.GetClientData(self.styleCombo.GetSelection())
