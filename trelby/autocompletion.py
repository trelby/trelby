import trelby.mypickle as mypickle
import trelby.screenplay as screenplay
import trelby.util as util
from trelby.autocompletiontype import AutoCompletionType as Type


# manages auto completion information for a single script.
class AutoCompletion:
    def __init__(self):
        # type configs, key = line type, value = Type
        self.types = {}

        # element types
        t = Type(screenplay.SCENE)
        self.types[t.ti.lt] = t

        t = Type(screenplay.CHARACTER)
        self.types[t.ti.lt] = t

        t = Type(screenplay.TRANSITION)
        t.items = [
            "BACK TO:",
            "CROSSFADE:",
            "CUT TO:",
            "DISSOLVE TO:",
            "FADE IN:",
            "FADE OUT",
            "FADE TO BLACK",
            "FLASHBACK TO:",
            "JUMP CUT TO:",
            "MATCH CUT TO:",
            "SLOW FADE TO BLACK",
            "SMASH CUT TO:",
            "TIME CUT:",
        ]
        self.types[t.ti.lt] = t

        t = Type(screenplay.SHOT)
        self.types[t.ti.lt] = t

        self.refresh()

    # load config from string 's'. does not throw any exceptions, silently
    # ignores any errors, and always leaves config in an ok state.
    def load(self, s):
        vals = mypickle.Vars.makeVals(s)

        for t in self.types.values():
            t.load(vals, "AutoCompletion/")

        self.refresh()

    # save config into a string and return that.
    def save(self):
        s = ""

        for t in self.types.values():
            s += t.save("AutoCompletion/")

        return s

    # fix up invalid values and uppercase everything.
    def refresh(self):
        for t in self.types.values():
            tmp = []

            for v in t.items:
                v = util.upper(util.toInputStr(v)).strip()

                if len(v) > 0:
                    tmp.append(v)

            t.items = tmp

    # get type's Type, or None if it doesn't exist.
    def getType(self, lt):
        return self.types.get(lt)
