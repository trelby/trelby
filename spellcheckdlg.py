import config
import misc
import spellcheck
import util

from wxPython.wx import *

class SpellCheckDlg(wxDialog):
    def __init__(self, parent, ctrl, sc, gScDict):
        wxDialog.__init__(self, parent, -1, "Spell checker",
                          style = wxDEFAULT_DIALOG_STYLE | wxWANTS_CHARS)

        self.ctrl = ctrl

        # spellcheck.SpellCheck
        self.sc = sc

        # user's global spell checker dictionary
        self.gScDict = gScDict
        
        # have we replaced any text in the script
        self.didReplaces = False

        # have we added any words to global dictionary
        self.changedGlobalDict = False
        
        vsizer = wxBoxSizer(wxVERTICAL)
        
        hsizer = wxBoxSizer(wxHORIZONTAL)
        
        hsizer.Add(wxStaticText(self, -1, "Word:"), 0,
                   wxALIGN_CENTER_VERTICAL | wxRIGHT, 10)
        self.replaceEntry = wxTextCtrl(self, -1, style = wxTE_PROCESS_ENTER)
        hsizer.Add(self.replaceEntry, 1, wxEXPAND)
        
        vsizer.Add(hsizer, 1, wxEXPAND | wxBOTTOM, 15)

        gsizer = wxFlexGridSizer(2, 2, 10, 10)
        gsizer.AddGrowableCol(1)
        
        replaceBtn = wxButton(self, -1, "&Replace")
        gsizer.Add(replaceBtn)

        addScriptBtn = wxButton(self, -1, "Add to &script dictionary")
        gsizer.Add(addScriptBtn, 0, wxEXPAND)

        skipBtn = wxButton(self, -1, "S&kip")
        gsizer.Add(skipBtn)

        addGlobalBtn = wxButton(self, -1, "Add to &global dictionary")
        gsizer.Add(addGlobalBtn, 0, wxEXPAND)

        vsizer.Add(gsizer, 0, wxEXPAND, 0)

        suggestBtn = wxButton(self, -1, "S&uggest replacement")
        vsizer.Add(suggestBtn, 0, wxEXPAND | wxTOP, 10)

        EVT_TEXT_ENTER(self, self.replaceEntry.GetId(), self.OnReplace)

        EVT_BUTTON(self, replaceBtn.GetId(), self.OnReplace)
        EVT_BUTTON(self, addScriptBtn.GetId(), self.OnAddScript)
        EVT_BUTTON(self, addGlobalBtn.GetId(), self.OnAddGlobal)
        EVT_BUTTON(self, skipBtn.GetId(), self.OnSkip)
        EVT_BUTTON(self, suggestBtn.GetId(), self.OnSuggest)

        EVT_CHAR(self, self.OnChar)
        EVT_CHAR(self.replaceEntry, self.OnChar)
        EVT_CHAR(replaceBtn, self.OnChar)
        EVT_CHAR(addScriptBtn, self.OnChar)
        EVT_CHAR(skipBtn, self.OnChar)
        EVT_CHAR(addGlobalBtn, self.OnChar)
        EVT_CHAR(suggestBtn, self.OnChar)

        util.finishWindow(self, vsizer)

        self.showWord()

    def showWord(self):
        self.ctrl.sp.line = self.sc.line
        self.ctrl.sp.column = self.sc.col
        self.ctrl.searchLine = self.sc.line
        self.ctrl.searchColumn = self.sc.col
        self.ctrl.searchWidth = len(self.sc.word)

        self.replaceEntry.SetValue(self.sc.word)

        self.ctrl.makeLineVisible(self.sc.line)
        self.ctrl.updateScreen()

    def gotoNext(self, incCol = True):
        if incCol:
            self.sc.col += len(self.sc.word)

        if not self.sc.findNext():
            wxMessageBox("No more incorrect words found.", "Results",
                         wxOK, self)

            self.EndModal(wxID_OK)

            return

        self.showWord()
        
    def OnChar(self, event):
        kc = event.GetKeyCode()

        if kc == WXK_ESCAPE:
            self.EndModal(wxID_OK)
            
            return

        event.Skip()

    def OnReplace(self, event):
        if not self.sc.word:
            return
        
        word = util.toInputStr(misc.fromGUI(self.replaceEntry.GetValue()))
        ls = self.ctrl.sp.lines

        ls[self.sc.line].text = util.replace(
            ls[self.sc.line].text, word,
            self.sc.col, len(self.sc.word))

        self.ctrl.searchLine = -1

        diff = len(word) - len(self.sc.word)

        self.sc.col += len(self.sc.word) + diff
        self.didReplaces = True
        self.ctrl.sp.markChanged()
        self.gotoNext(False)
        
    def OnSkip(self, event = None, autoFind = False):
        if not self.sc.word:
            return

        self.gotoNext()

    def OnAddScript(self, event):
        if not self.sc.word:
            return
        
        self.ctrl.sp.scDict.add(self.sc.word)
        self.ctrl.sp.markChanged()
        self.gotoNext()
        
    def OnAddGlobal(self, event):
        if not self.sc.word:
            return
        
        self.gScDict.add(self.sc.word)
        self.changedGlobalDict = True
        
        self.gotoNext()

    def OnSuggest(self, event):
        if not self.sc.word:
            return

        isAllCaps = self.sc.word == util.upper(self.sc.word)
        isCapitalized = self.sc.word[:1] == util.upper(self.sc.word[:1])
        
        word = util.lower(self.sc.word)
        
        wl = len(word)
        wstart = word[:2]
        d = 500
        fifo = util.FIFO(5)
        wxBeginBusyCursor()

        for w in spellcheck.prefixDict[util.getWordPrefix(word)].iterkeys():
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        for w in self.gScDict.words.iterkeys():
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)
            
        for w in self.ctrl.sp.scDict.words.iterkeys():
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        items = fifo.get()

        wxEndBusyCursor()

        if len(items) == 0:
            wxMessageBox("No similar words found.", "Results",
                         wxOK, self)

            return

        dlg = wxSingleChoiceDialog(self, "Most similar words:",
                                   "Suggestions", items)
        
        if dlg.ShowModal() == wxID_OK:
            sel = dlg.GetSelection()

            newWord = items[sel]

            if isAllCaps:
                newWord = util.upper(newWord)
            elif isCapitalized:
                newWord = util.capitalize(newWord)
                
            self.replaceEntry.SetValue(newWord)

        dlg.Destroy()

    # if w2 is closer to w1 in Levenshtein distance than d, add it to
    # fifo. return min(d, new_distance).
    def tryWord(self, w1, w1len, w2, d, fifo):
        if abs(w1len - len(w2)) > 3:
            return d

        d2 = spellcheck.lev(w1, w2)

        if d2 <= d:
            fifo.add(w2)

            return d2

        return d

