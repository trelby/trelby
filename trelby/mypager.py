import trelby.pml as pml
import trelby.screenplay as screenplay


# used to iteratively add PML pages to a document
class Pager:
    def __init__(self, cfg):
        self.doc = pml.Document(cfg.paperWidth, cfg.paperHeight)

        # used in several places, so keep around
        self.charIndent = cfg.getType(screenplay.CHARACTER).indent
        self.sceneIndent = cfg.getType(screenplay.SCENE).indent

        # current scene number
        self.scene = 0

        # number of CONTINUED:'s lines added for current scene
        self.sceneContNr = 0
