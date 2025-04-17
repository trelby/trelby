# -*- coding: utf-8 -*-

import trelby.config as config

# constants that could not be removed yet
from trelby.screenplay import ACTION, LB_LAST


# one line in a screenplay
class Line:
    def __init__(self, lb=LB_LAST, lt=ACTION, text=""):

        # line break type
        self.lb = lb

        # line type
        self.lt = lt

        # text
        self.text = text

    def __str__(self):
        return config.lb2char(self.lb) + config.lt2char(self.lt) + self.text

    def __repr__(self) -> str:
        return self.__str__()

    def __ne__(self, other):
        return (
            (self.lt != other.lt) or (self.lb != other.lb) or (self.text != other.text)
        )

    def __eq__(self, other):
        return not self.__ne__(other)

    # opposite of __str__. NOTE: only meant for storing data internally by
    # the program! NOT USABLE WITH EXTERNAL INPUT DUE TO COMPLETE LACK OF
    # ERROR CHECKING!
    @staticmethod
    def fromStr(s):
        return Line(config.char2lb(s[0]), config.char2lt(s[1]), s[2:])
