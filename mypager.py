import config
import pml

# used to iteratively add PML pages to a document
class Pager:
    def __init__(self, sp, cfg):
        self.sp = sp
        self.doc = pml.Document(cfg.paperWidth, cfg.paperHeight)

        # used in several places, so keep around
        self.charIndent = cfg.getType(config.CHARACTER).indent
        self.sceneIndent = cfg.getType(config.SCENE).indent

        # current scene number
        self.scene = 0

        # number of CONTINUED:'s lines added for current scene
        self.sceneContNr = 0
