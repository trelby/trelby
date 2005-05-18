# ut:ignore

import config
import misc
import screenplay
import util

initDone = False

def load(filename = "test.blyte"):
    global initDone
    
    if not initDone:
        misc.init()
        util.init(False)

        initDone = True
    
    return screenplay.Screenplay.load(open(filename, "r").read(),
                                      config.ConfigGlobal())[0]
