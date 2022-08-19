# ut:ignore
import os

import config
import misc
import screenplay
import util

initDone = False

def init():
    global initDone

    if not initDone:
        misc.init(False)
        util.init(False)

        initDone = True

# return new, empty Screenplay
def new():
    init()

    return screenplay.Screenplay(config.ConfigGlobal())

# load script from the given file, relative to the current script directory
def load(filename = "test.trelby"):
    init()

    location = os.path.dirname(__file__)+'/fixtures/'
    filename = os.path.join(location, filename)

    return screenplay.Screenplay.load(open(filename, "r").read(),
                                      config.ConfigGlobal())[0]

# load script from given string
def loadString(s: str):
    init()

    return screenplay.Screenplay.load(s, config.ConfigGlobal())[0]

