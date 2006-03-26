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

import pdf
import util

import textwrap

# text flags. don't change these unless you know what you're doing.
NORMAL = 0
BOLD   = 1
ITALIC = 2
COURIER = 0
TIMES_ROMAN = 4
HELVETICA = 8
UNDERLINED = 16

# fill types
NO_FILL = 0
FILL = 1
STROKE_FILL = 2

# A single document.
class Document:

    # (w, h) is the size of each page.
    def __init__(self, w, h):
        self.w = w
        self.h = h
        
        # a collection of Page objects
        self.pages = []

        # a collection of TOCItem objects
        self.tocs = []

        # whether to show TOC by default on document open
        self.showTOC = False

        # page number to display on document open, or -1
        self.defPage = -1

    def add(self, page):
        self.pages.append(page)

    def addTOC(self, toc):
        self.tocs.append(toc)

class Page:
    def __init__(self, doc):

        # link to containing document
        self.doc = doc
        
        # a collection of Operation objects
        self.ops = []

    def add(self, op):
        self.ops.append(op)

    # add demo stamp.
    def addDemoStamp(self):
        # list of lines which together draw a "DEMO" in a 45-degree angle
        # over the page. coordinates are percentages of page width/height.
        dl = [
            # D
            [ (0.056, 0.286), (0.208, 0.156), (0.23, 0.31), (0.056, 0.286) ],

            # E
            [ (0.356, 0.542), (0.238, 0.42), (0.38, 0.302), (0.502, 0.4) ],
            [ (0.328, 0.368), (0.426, 0.452) ],

            # M
            [ (0.432, 0.592), (0.574, 0.466), (0.522, 0.650),
              (0.722, 0.62), (0.604, 0.72) ],

            # O
            [ (0.67, 0.772), (0.794, 0.678), (0.896, 0.766),
              (0.772, 0.858), (0.67, 0.772) ]
            ]

        self.add(PDFOp("q 0.5 G")) 
        self.add(PDFOp("1 J 1 j"))

        for path in dl:
            p = []
            for point in path:
                p.append((point[0] * self.doc.w, point[1] * self.doc.h))

            self.add(LineOp(p, 10))

        self.add(PDFOp("Q"))

# Table of content item (Outline item, in PDF lingo)
class TOCItem:
    def __init__(self, text, op):
        # text to show in TOC
        self.text = text

        # pointer to the TextOp that this item links to (used to get the
        # correct positioning information)
        self.op = op

        # the PDF object number of the page we point to
        self.pageObjNr = -1

# An abstract base class for all drawing operations.
class DrawOp:
    pass

# Draw text string 'text', at position (x, y) mm from the upper left
# corner of the page. Font used is 'size' points, and Courier / Times/
# Helvetica as indicated by the flags, possibly being bold / italic /
# underlined.
class TextOp(DrawOp):
    pdfOp = pdf.PDFTextOp()
    
    def __init__(self, text, x, y, size, flags = NORMAL | COURIER,
                 align = util.ALIGN_LEFT, valign = util.VALIGN_TOP,
                 line = -1):
        self.text = text
        self.x = x
        self.y = y
        self.size = size
        self.flags = flags

        # TOCItem, by default we have none
        self.toc = None
        
        # index of line in Screenplay.lines, or -1 if some other text.
        # only used when drawing display, pdf output doesn't use this.
        self.line = line
        
        if align != util.ALIGN_LEFT:
            w = util.getTextWidth(text, flags, size)

            if align == util.ALIGN_CENTER:
                self.x -= w / 2.0
            elif align == util.ALIGN_RIGHT:
                self.x -= w

        if valign != util.VALIGN_TOP:
            h = util.getTextHeight(size)
            
            if valign == util.VALIGN_CENTER:
                self.y -= h / 2.0
            elif valign == util.VALIGN_BOTTOM:
                self.y -= h

# Draw consecutive lines. 'points' is a list of (x, y) pairs (minimum 2
# pairs) and 'width' is the line width, with 0 being the thinnest possible
# line. if 'isClosed' is True, the last point on the list is connected to
# the first one.
class LineOp(DrawOp):
    pdfOp = pdf.PDFLineOp()

    def __init__(self, points, width, isClosed = False):
        self.points = points
        self.width = width
        self.isClosed = isClosed

# helper function for creating simple lines
def genLine(x, y, xd, yd, width):
    return LineOp([(x, y), (x + xd, y + yd)], width)

# Draw a rectangle, possibly filled, with specified lineWidth (which can
# be -1 if fillType is FILL). (x, y) is position of upper left corner.
class RectOp(DrawOp):
    pdfOp = pdf.PDFRectOp()

    def __init__(self, x, y, width, height, fillType = FILL, lineWidth = -1):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.fillType = fillType
        self.lw = lineWidth

# Draw a quarter circle centered at (x, y) with given radius and line
# width. By default it will be the upper left quadrant of a circle, but
# using the flip[XY] parameters you can choose other quadrants.
class QuarterCircleOp(DrawOp):
    pdfOp = pdf.PDFQuarterCircleOp()

    def __init__(self, x, y, radius, width, flipX = False, flipY = False):
        self.x = x
        self.y = y
        self.radius = radius
        self.width = width
        self.flipX = flipX
        self.flipY = flipY
        
# Arbitrary PDF commands. Should not have whitespace in the beginning or
# the end. Should be used only for non-critical things like tweaking line
# join styles etc, because non-PDF renderers will ignore these.
class PDFOp(DrawOp):
    pdfOp = pdf.PDFArbitraryOp()

    def __init__(self, cmds):
        self.cmds = cmds

# create a PML document containing text (possibly linewrapped) divided
# into pages automatically.
class TextFormatter:
    def __init__(self, width, height, margin, fontSize, addDs):
        self.doc = Document(width, height)

        # how much to leave empty on each side (mm)
        self.margin = margin

        # font size
        self.fontSize = fontSize

        # whether to add a demo stamp to each page
        self.addDs = addDs
        
        # number of chararacters that fit on a single line
        self.charsToLine = int((width - margin * 2.0) /
                               util.getTextWidth(" ", COURIER, fontSize))
        
        self.createPage()
        
    # add new empty page, select it as current, reset y pos
    def createPage(self):
        self.pg = Page(self.doc)

        if self.addDs:
            self.pg.addDemoStamp()
            
        self.doc.add(self.pg)
        self.y = self.margin

    # add blank vertical space, unless we're at the top of the page
    def addSpace(self, mm):
        if self.y > self.margin:
            self.y += mm

    # add text
    def addText(self, text, x = None, fs = None, style = NORMAL):
        if x == None:
            x = self.margin

        if fs == None:
            fs = self.fontSize

        yd = util.getTextHeight(fs)

        if (self.y + yd) > (self.doc.h - self.margin):
            self.createPage()
            
        self.pg.add(TextOp(text, x, self.y, fs, style))

        self.y += yd

    # wrap text into lines that fit on the page, using Courier and default
    # font size and style, and add the lines. 'indent' is the text to
    # prefix lines other than the first one with.
    def addWrappedText(self, text, indent):
        tmp = textwrap.wrap(text, self.charsToLine,
                subsequent_indent = indent)
        
        for s in tmp:
            self.addText(s)
