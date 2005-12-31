# ut:ignore

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
    
# load script from the given file
def load(filename = "test.blyte"):
    init()

    return screenplay.Screenplay.load(open(filename, "r").read(),
                                      config.ConfigGlobal())[0]
