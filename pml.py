# PML is short for Page Modeling Language, our own neat little PDF-wannabe
# format for expressing a script's complete contents in a neutral way
# that's easy to render to almost anything, e.g. PDF, Postscript, Windows
# GDI, etc.
#

# A PML document is a collection of pages plus possibly some metadata.
# Each page is a collection of simple drawing commands, executed
# sequentially in the order given, assuming "complete overdraw" semantics
# on the output device, i.e. whatever is drawn completely covers things it
# is painted on top of.

# All measurements in PML are in (floating point) millimeters.

# types of drawing operations
OP_TEXT = 0
OP_LINE = 1
OP_PDF = 2

# text flags
NORMAL = 0
BOLD   = 1
ITALIC = 2
UNDERLINED = 4

# A single document.
class Document:

    # (w, h) is size of each page, with pageName being a descriptive name
    # for the size, basically one of "A4", "Letter", or "Custom" for now.
    def __init__(self, w, h, pageName):
        self.w = w
        self.h = h
        self.pageName = pageName
        
        # a collection of Page objects
        self.pages = []

class Page:
    def __init__(self):

        # a collection of Operation objects
        self.ops = []

    def add(self, op):
        self.ops.append(op)

# An abstract base class for all drawing operations.
class DrawOp:
    def __init__(self, type):
        self.type = type

# Draw text string 'text', with upper left corner offsetted (x, y) mm from
# the upper left corner of the page. Font used is 'size'-point Courier,
# with it possibly being bold/italic/underlined as given by the flags.
class TextOp(DrawOp):
    def __init__(self, text, x, y, size, flags = NORMAL):
        DrawOp.__init__(self, OP_TEXT)

        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.flags = flags

# Draw consecutive lines. 'points' is a list of (x, y) pairs (minimum 2
# pairs) and 'width' is the line width, with 0 being the thinnest possible
# line. if 'isClosed' is True, the last point on the list is connected to
# the first one.
class LineOp(DrawOp):
    def __init__(self, points, width, isClosed = False):
        DrawOp.__init__(self, OP_LINE)

        self.points = points
        self.width = width
        self.isClosed = isClosed

# Arbitrary PDF commands. Should not have whitespace in the beginning or
# the end. Should be used only for non-critical things like tweaking line
# join styles etc, because non-PDF renderers will ignore these.
class PDFOp(DrawOp):
    def __init__(self, cmds):
        DrawOp.__init__(self, OP_PDF)

        self.cmds = cmds
