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

import util

# types of drawing operations
OP_TEXT = 0
OP_LINE = 1
OP_RECT = 2
OP_PDF = 3

# text flags. don't change these unless you know what you're doing.
NORMAL = 0
BOLD   = 1
ITALIC = 2
COURIER = 0
TIMES_ROMAN = 4
HELVETICA = 8
UNDERLINED = 16

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

    def add(self, page):
        self.pages.append(page)

class Page:
    def __init__(self, doc):

        # link to containing document
        self.doc = doc
        
        # a collection of Operation objects
        self.ops = []

    def add(self, op):
        self.ops.append(op)

# An abstract base class for all drawing operations.
class DrawOp:
    def __init__(self, type):
        self.type = type

# Draw text string 'text', at position (x, y) mm from the upper left
# corner of the page. Font used is 'size' points, and Courier / Times/
# Helvetica as indicated by the flags, possibly being bold / italic /
# underlined.
#
# FIXME: text alignment is only supported for Courier fonts for now.
class TextOp(DrawOp):
    def __init__(self, text, x, y, size, flags = NORMAL | COURIER,
                 align = util.ALIGN_LEFT, valign = util.VALIGN_TOP):
        DrawOp.__init__(self, OP_TEXT)

        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.flags = flags

        if align != util.ALIGN_LEFT:
            w = util.points2x(size) * len(text)

            if align == util.ALIGN_CENTER:
                self.x -= w / 2
            elif align == util.ALIGN_RIGHT:
                self.x -= w

        if valign != util.VALIGN_TOP:
            h = util.points2y(size)
            
            if valign == util.VALIGN_CENTER:
                self.y -= h / 2
            elif valign == util.VALIGN_BOTTOM:
                self.y -= h

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

# helper function for creating simple lines
def genLine(x, y, xd, yd, width):
    return LineOp([(x, y), (x + xd, y + yd)], width)

# Draw a rectangle, possibly filled, with specified lineWidth. (x, y) is
# position of upper left corner. Line width of filled rectangles is
# ignored.
class RectOp(DrawOp):
    def __init__(self, x, y, width, height, lineWidth, isFilled = False):
        DrawOp.__init__(self, OP_RECT)

        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.lw = lineWidth
        self.isFilled = isFilled

# Arbitrary PDF commands. Should not have whitespace in the beginning or
# the end. Should be used only for non-critical things like tweaking line
# join styles etc, because non-PDF renderers will ignore these.
class PDFOp(DrawOp):
    def __init__(self, cmds):
        DrawOp.__init__(self, OP_PDF)

        self.cmds = cmds
