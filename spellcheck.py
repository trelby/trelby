import mypickle
import util

import gzip
import StringIO

from wxPython.wx import *

# PY2.4: use a Set object
# dict of words loaded from dict_en.dat. key = word, value = None.
gdict = {}

# load word dictionary. returns True on success or if it's already loaded,
# False on errors.
def loadDict(frame):
    if gdict:
        return True

    # use dict_en.dat if if exists, dict_en.dat.gz otherwise
    fname = "dict_en.dat"
    doGz = False
    
    if not util.fileExists(fname):
        fname += ".gz"
        doGz = True

    s = util.loadFile(fname, frame)
    if s == None:
        return False

    if doGz:
        buf = StringIO.StringIO(s)

        # python's gzip module throws almost arbitrary exceptions in
        # various error conditions, so the only safe thing to do is to
        # catch everything.
        try:
            f = gzip.GzipFile(mode = "r", fileobj = buf)
            s = f.read()
        except:
            wxMessageBox("Error loading file '%s': Decompression failed" % \
                         fname, "Error", wxOK, frame)

            return False
    
    lines = s.splitlines()

    for it in lines:
        # theoretically, we should do util.lower(util.toInputStr(it)), but:
        #
        #  -user's aren't supposed to modify the file
        #
        #  -it takes 1.35 secs, compared to 0.56 secs if we don't, on an
        #   1.33GHz Athlon
        gdict[it] = None
    
    return True

# dictionary, a list of known words that the user has specified.
class Dict:
    cvars = None

    def __init__(self):
        if not self.__class__.cvars:
            v = self.__class__.cvars = mypickle.Vars()

            v.addList("wordsList", [], "Words",
                      mypickle.StrNoEscapeVar("", "", ""))

            v.makeDicts()
            
        self.__class__.cvars.setDefaults(self)

        # we have wordsList that we use for saving/loading, and words,
        # which we use during normal operation. it's possible we should
        # introduce a mypickle.SetVar...

        # key = word, lowercased, value = None
        self.words = {}
        
    # load from string 's'. does not throw any exceptions and silently
    # ignores any errors.
    def load(self, s):
        self.cvars.load(self.cvars.makeVals(s), "", self)

        self.words = {}

        for w in self.wordsList:
            self.words[w] = None

        self.refresh()

    # save to a string and return that.
    def save(self):
        self.wordsList = self.get()

        return self.cvars.save("", self)

    # fix up invalid values.
    def refresh(self):
        ww = {}

        for w in self.words.keys():
            w = self.cleanWord(w)

            if w:
                ww[w] = None
        
        self.words = ww

    # returns True if word is known
    def isKnown(self, word):
        return word in self.words

    # add word
    def add(self, word):
        word = self.cleanWord(word)

        if word:
            self.words[word] = None

    # set words from a list
    def set(self, words):
        self.words = {}

        for w in words:
            self.add(w)

    # get a sorted list of all the words.
    def get(self):
        keys = self.words.keys()
        keys.sort()

        return keys
        
    # clean up word in all possible ways and return it, or an empty string
    # if nothing remains.
    def cleanWord(self, word):
        word = util.splitToWords(util.lower(util.toInputStr(word)))

        if len(word) == 0:
            return ""

        return word[0]

# spell check a script
class SpellChecker:
    def __init__(self, sp, gScDict):
        self.sp = sp

        # user's global dictionary (Dict)
        self.gScDict = gScDict

        # key = word found in character names, value = None
        self.cnames = {}
        
        for it in sp.getCharacterNames():
            for w in util.splitToWords(it):
                self.cnames[w] = None

        self.word = None
        self.line = self.sp.line

        # we can't use the current column, because if the cursor is in the
        # middle of a word, we flag the partial word as misspelled.
        self.col = 0

    # find next possibly misspelled word and store its location. returns
    # True if such a word found.
    def findNext(self):
        line = self.line
        col = self.col

        # clear these so there's no chance of them left pointing to
        # something, we return False, and someone tries to access them
        # anyhow.
        self.word = None
        self.line = 0
        self.col = 0

        while 1:
            word, line, col = self.sp.getWord(line, col)
            
            if not word:
                return False

            if not self.isKnown(word):
                self.word = word
                self.line = line
                self.col = col

                return True
            
            col += len(word)

    # return True if word is a known word.
    def isKnown(self, word):
        word = util.lower(word)

        return word in gdict or \
               word in self.cnames or \
               self.sp.scDict.isKnown(word) or \
               self.gScDict.isKnown(word) or \
               word.isdigit()
