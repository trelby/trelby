import config

import re

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
        
