import config
import titles
import headers

import copy
import re

# screenplay
class Screenplay:
    def __init__(self):
        self.titles = titles.Titles()
        self.headers = headers.Headers()
        self.lines = []
        
    def __eq__(self, other):
        if len(self.lines) != len(other.lines):
            return False

        if self.titles != other.titles:
            return False
        
        if self.headers != other.headers:
            return False
        
        for i in xrange(len(self.lines)):
            if self.lines[i] != other.lines[i]:
                return False

        return True
    
    def __ne__(self, other):
        return not self == other
    
    def getSpacingBefore(self, i, cfg):
        if i == 0:
            return 0

        tcfg = cfg.types[self.lines[i].lt]
        
        if self.lines[i - 1].lb == config.LB_LAST:
            return tcfg.beforeSpacing
        else:
            return tcfg.intraSpacing

    def replace(self):
        for i in xrange(len(self.lines)):
            self.lines[i].replace()
            
    # this is ~8x faster than the generic deepcopy, which makes a
    # noticeable difference at least on an Athlon 1.3GHz (0.06s versus
    # 0.445s)
    def __deepcopy__(self, memo):
        sp = Screenplay()
        l = sp.lines

        sp.titles = copy.deepcopy(self.titles)
        sp.headers = copy.deepcopy(self.headers)

        for i in xrange(len(self.lines)):
            ln = self.lines[i]
            l.append(Line(ln.lb, ln.lt, ln.text))

        return sp

# one line in a screenplay
class Line:
    def __init__(self, lb = config.LB_LAST, lt = config.ACTION, text = ""):

        # line break type
        self.lb = lb

        # line type
        self.lt = lt

        # text
        self.text = text

    def __eq__(self, other):
        return (self.lb == other.lb) and (self.lt == other.lt) and\
               (self.text == other.text)
    
    def __ne__(self, other):
        return not self == other
        
    def __str__(self):
        return config.lb2text(self.lb) + config.lt2text(self.lt)\
               + self.text

    # replace some words, rendering the script useless except for
    # evaluation purposes
    def replace(self):
        self.text = re.sub(r"\b(\w){3}\b", "BUY", self.text)
        self.text = re.sub(r"\b(\w){4}\b", "DEMO", self.text)
        self.text = re.sub(r"\b(\w){5}\b", "TRIAL", self.text)
        self.text = re.sub(r"\b(\w){6}\b", "*TEST*", self.text)
        self.text = re.sub(r"\b(\w){7}\b", "LIMITED", self.text)
        self.text = re.sub(r"\b(\w){10}\b", "EVALUATION", self.text)
        
