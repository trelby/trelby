import config
import misc
import spellcheck
import undo
import util

import wx

class SpellCheckDlg(wx.Dialog):
    def __init__(self, parent, ctrl, sc, gScDict):
        wx.Dialog.__init__(self, parent, -1, "Spell checker",
                           style = wx.DEFAULT_DIALOG_STYLE | wx.WANTS_CHARS)

        self.ctrl = ctrl

        # spellcheck.SpellCheck
        self.sc = sc

        # user's global spell checker dictionary
        self.gScDict = gScDict

        # have we added any words to global dictionary
        self.changedGlobalDict = False

        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        hsizer.Add(wx.StaticText(self, -1, "Word:"), 0,
                   wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        self.replaceEntry = wx.TextCtrl(self, -1, style = wx.TE_PROCESS_ENTER)
        hsizer.Add(self.replaceEntry, 1, wx.EXPAND)

        vsizer.Add(hsizer, 1, wx.EXPAND | wx.BOTTOM, 15)

        gsizer = wx.FlexGridSizer(2, 2, 10, 10)
        gsizer.AddGrowableCol(1)

        replaceBtn = wx.Button(self, -1, "&Replace")
        gsizer.Add(replaceBtn)

        addScriptBtn = wx.Button(self, -1, "Add to &script dictionary")
        gsizer.Add(addScriptBtn, 0, wx.EXPAND)

        skipBtn = wx.Button(self, -1, "S&kip")
        gsizer.Add(skipBtn)

        addGlobalBtn = wx.Button(self, -1, "Add to &global dictionary")
        gsizer.Add(addGlobalBtn, 0, wx.EXPAND)

        vsizer.Add(gsizer, 0, wx.EXPAND, 0)

        suggestBtn = wx.Button(self, -1, "S&uggest replacement")
        vsizer.Add(suggestBtn, 0, wx.EXPAND | wx.TOP, 10)

        wx.EVT_TEXT_ENTER(self, self.replaceEntry.GetId(), self.OnReplace)

        wx.EVT_BUTTON(self, replaceBtn.GetId(), self.OnReplace)
        wx.EVT_BUTTON(self, addScriptBtn.GetId(), self.OnAddScript)
        wx.EVT_BUTTON(self, addGlobalBtn.GetId(), self.OnAddGlobal)
        wx.EVT_BUTTON(self, skipBtn.GetId(), self.OnSkip)
        wx.EVT_BUTTON(self, suggestBtn.GetId(), self.OnSuggest)

        wx.EVT_CHAR(self, self.OnChar)
        wx.EVT_CHAR(self.replaceEntry, self.OnChar)
        wx.EVT_CHAR(replaceBtn, self.OnChar)
        wx.EVT_CHAR(addScriptBtn, self.OnChar)
        wx.EVT_CHAR(skipBtn, self.OnChar)
        wx.EVT_CHAR(addGlobalBtn, self.OnChar)
        wx.EVT_CHAR(suggestBtn, self.OnChar)

        util.finishWindow(self, vsizer)

        self.showWord()

    def showWord(self):
        self.ctrl.sp.line = self.sc.line
        self.ctrl.sp.column = self.sc.col
        self.ctrl.sp.setMark(self.sc.line, self.sc.col + len(self.sc.word) - 1)

        self.replaceEntry.SetValue(self.sc.word)

        self.ctrl.makeLineVisible(self.sc.line)
        self.ctrl.updateScreen()

    def gotoNext(self, incCol = True):
        if incCol:
            self.sc.col += len(self.sc.word)

        if not self.sc.findNext():
            wx.MessageBox("No more incorrect words found.", "Results",
                          wx.OK, self)

            self.EndModal(wx.ID_OK)

            return

        self.showWord()

    def OnChar(self, event):
        kc = event.GetKeyCode()

        if kc == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_OK)

            return

        event.Skip()

    def OnReplace(self, event):
        if not self.sc.word:
            return

        sp = self.ctrl.sp
        u = undo.SinglePara(sp, undo.CMD_MISC, self.sc.line)

        word = util.toInputStr(misc.fromGUI(self.replaceEntry.GetValue()))
        ls = sp.lines

        sp.gotoPos(self.sc.line, self.sc.col)

        ls[self.sc.line].text = util.replace(
            ls[self.sc.line].text, word,
            self.sc.col, len(self.sc.word))

        sp.rewrapPara(sp.getParaFirstIndexFromLine(self.sc.line))

        # rewrapping a paragraph can have moved the cursor, so get the new
        # location of it, and then advance past the just-changed word
        self.sc.line = sp.line
        self.sc.col = sp.column + len(word)

        sp.clearMark()
        sp.markChanged()

        u.setAfter(sp)
        sp.addUndo(u)

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
        wx.BeginBusyCursor()

        for w in spellcheck.prefixDict[util.getWordPrefix(word)]:
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        for w in self.gScDict.words.iterkeys():
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        for w in self.ctrl.sp.scDict.words.iterkeys():
            if w.startswith(wstart):
                d = self.tryWord(word, wl, w, d, fifo)

        items = fifo.get()

        wx.EndBusyCursor()

        if len(items) == 0:
            wx.MessageBox("No similar words found.", "Results",
                          wx.OK, self)

            return

        dlg = wx.SingleChoiceDialog(
            self, "Most similar words:", "Suggestions", items)

        if dlg.ShowModal() == wx.ID_OK:
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

