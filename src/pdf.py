import uuid
from typing import Optional, Tuple, Dict, AnyStr

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

import pml
import util

# PDF transform matrixes where key is the angle from x-axis
# in counter-clockwise direction.
TRANSFORM_MATRIX = {
    45 : (1, 1, -1, 1),
    90 : (0, 1, -1, 0),
}

# users should only use this.
def generate(doc: 'pml.Document') -> bytes:
    tmp = PDFExporter(doc)
    return tmp.generate()

# An abstract base class for all PDF drawing operations.
class PDFDrawOp:

    # write PDF drawing operations corresponding to the PML object pmlOp
    # to output (util.String). pe = PDFExporter.
    def draw(self, pmlOp: 'pml.DrawOp', pageNr: int, pe: 'PDFExporter', canvas: Canvas) -> None:
        raise Exception("draw not implemented")

class PDFTextOp(PDFDrawOp):
    def draw(self, pmlOp: 'pml.DrawOp', pageNr: int, pe: 'PDFExporter', canvas) -> None:
        if not isinstance(pmlOp, pml.TextOp):
            raise Exception("PDFTextOp is only compatible with pml.TextOp, got "+type(pmlOp).__name__)

        # we need to adjust y position since PDF uses baseline of text as
        # the y pos, but pml uses top of the text as y pos. The Adobe
        # standard Courier family font metrics give 157 units in 1/1000
        # point units as the Descender value, thus giving (1000 - 157) =
        # 843 units from baseline to top of text.

        # http://partners.adobe.com/asn/tech/type/ftechnotes.jsp contains
        # the "Font Metrics for PDF Core 14 Fonts" document.

        x = pe.x(pmlOp.x)
        y = pe.y(pmlOp.y) - 0.843 * pmlOp.size

        newFont = pe.getFontForFlags(pmlOp.flags)
        canvas.setFont(newFont, pmlOp.size)

        if pmlOp.angle is not None:
            matrix = TRANSFORM_MATRIX.get(pmlOp.angle)

            if matrix:
                canvas.addLiteral("BT\n"\
                    "%f %f %f %f %f %f Tm\n"\
                    "(%s) Tj\n"\
                    "ET\n" % (matrix[0], matrix[1], matrix[2], matrix[3],
                              x, y, pe.escapeStr(pmlOp.text))) # TODO: Doing this with addLiteral, non-latin characters won't work in watermarks. There must be a better way to do this with reportlab, that we do it this way is for historical reasons and because no one took the time to change it
            else:
                # unsupported angle, don't print it.
                pass
        else:
            canvas.drawString(x, y, pmlOp.text)

        if pmlOp.flags & pml.UNDERLINED:

            undLen = canvas.stringWidth(pmlOp.text, newFont, pmlOp.size)

            # all standard PDF fonts have the underline line 100 units
            # below baseline with a thickness of 50
            undY = y - 0.1 * pmlOp.size
            canvas.setLineWidth(0.05 * pmlOp.size)

            canvas.line(x, undY, x + undLen, undY)

        # create bookmark for table of contents if applicable
        if pmlOp.toc:
            bookmarkKey = uuid.uuid4().hex  # we need a unique key to link the bookmark in toc – TODO: generate a more speaking one
            canvas.bookmarkHorizontal(bookmarkKey, pe.x(pmlOp.x), pe.y(pmlOp.y))
            canvas.addOutlineEntry(pmlOp.toc.text, bookmarkKey)

class PDFLineOp(PDFDrawOp):
    def draw(self, pmlOp: 'pml.DrawOp', pageNr: int, pe: 'PDFExporter', canvas):
        if not isinstance(pmlOp, pml.LineOp):
            raise Exception("PDFLineOp is only compatible with pml.LineOp, got "+type(pmlOp).__name__)

        points = pmlOp.points
        numberOfPoints = len(points)

        if numberOfPoints < 2:
            print("LineOp contains only %d points" % numberOfPoints)

            return

        canvas.setLineWidth(pe.mm2points(pmlOp.width))

        lines = []
        for i in range(0, numberOfPoints - 1):
            lines.append(pe.xy(points[i]) + pe.xy(points[i+1]))

        if pmlOp.isClosed:
            lines.append(pe.xy(points[i+1]) + pe.xy(points[0]))

        canvas.lines(lines)

class PDFRectOp(PDFDrawOp):
    def draw(self, pmlOp: 'pml.DrawOp', pageNr: int, pe: 'PDFExporter', canvas) -> None:
        if not isinstance(pmlOp, pml.RectOp):
            raise Exception("PDFRectOp is only compatible with pml.RectOp, got "+type(pmlOp).__name__)

        if pmlOp.lw != -1:
            canvas.setLineWidth(pe.mm2points(pmlOp.lw))

        canvas.rect(
            pe.x(pmlOp.x),
            pe.y(pmlOp.y) - pe.mm2points(pmlOp.height),
            pe.mm2points(pmlOp.width),
            pe.mm2points(pmlOp.height),
            pmlOp.fillType == pml.NO_FILL or pmlOp.fillType == pml.STROKE_FILL,
            pmlOp.fillType == pml.FILL or pmlOp.fillType == pml.STROKE_FILL
        )

class PDFQuarterCircleOp(PDFDrawOp):
    def draw(self, pmlOp: 'pml.DrawOp', pageNr: int, pe: 'PDFExporter', canvas) -> None:
        if not isinstance(pmlOp, pml.QuarterCircleOp):
            raise Exception("PDFQuarterCircleOp is only compatible with pml.QuarterCircleOp, got "+type(pmlOp).__name__)

        sX = pmlOp.flipX and -1 or 1
        sY = pmlOp.flipY and -1 or 1

        # The traditional constant is: 0.552284749
        # however, as described here:
        # http://spencermortensen.com/articles/bezier-circle/,
        # this has a maximum radial drift of 0.027253%.
        # The constant calculated by Spencer Mortensen
        # has a max. drift of 0.019608% which is 28% better.
        A = pmlOp.radius * 0.551915024494

        canvas.setLineWidth(pe.mm2points(pmlOp.width))
        canvas.bezier(
            pe.x(pmlOp.x - pmlOp.radius * sX),
            pe.y(pmlOp.y),
            pe.x(pmlOp.x - pmlOp.radius * sX),
            pe.y(pmlOp.y - A * sY),
            pe.x(pmlOp.x - A * sX),
            pe.y(pmlOp.y - pmlOp.radius * sY),
            pe.x(pmlOp.x), pe.y(pmlOp.y - pmlOp.radius * sY)
        )

class PDFArbitraryOp(PDFDrawOp):
    def draw(self, pmlOp: 'pml.DrawOp', pageNr: int, pe: 'PDFExporter', canvas) -> None:
        if not isinstance(pmlOp, pml.PDFOp):
            raise Exception("PDFArbitraryOp is only compatible with pml.PDFOp, got "+type(pmlOp).__name__)

        canvas.addLiteral("%s\n" % pmlOp.cmds)

# used for keeping track of used fonts
class FontInfo:
    def __init__(self, name: str):
        self.name: str = name

        # font number (the name in the /F PDF command), or -1 if not used
        self.number: int = -1

        # PDFObject that contains the /Font object for this font, or None
        self.pdfObj: Optional[PDFObject] = None

# one object in a PDF file
class PDFObject:
    def __init__(self, nr: int, data: str = ""):
        # PDF object number
        self.nr: int = nr

        # all data between 'obj/endobj' tags, excluding newlines
        self.data: str = data

    # write object to canvas.
    def write(self, canvas: Canvas) -> None:
        code = "%d 0 obj\n" % self.nr
        code += self.data
        code += "\nendobj\n"
        canvas.addLiteral(code)

class PDFExporter:
    # see genWidths
    _widthsStr: Optional[str] = None

    def __init__(self, doc: 'pml.Document'):
        self.doc: pml.Document = doc
        # fast lookup of font information
        self.fonts: Dict[int, FontInfo] = {
            pml.COURIER: FontInfo("Courier"),
            pml.COURIER | pml.BOLD: FontInfo("Courier-Bold"),
            pml.COURIER | pml.ITALIC: FontInfo("Courier-Oblique"),
            pml.COURIER | pml.BOLD | pml.ITALIC:
                FontInfo("Courier-BoldOblique"),

            pml.HELVETICA: FontInfo("Helvetica"),
            pml.HELVETICA | pml.BOLD: FontInfo("Helvetica-Bold"),
            pml.HELVETICA | pml.ITALIC: FontInfo("Helvetica-Oblique"),
            pml.HELVETICA | pml.BOLD | pml.ITALIC:
                FontInfo("Helvetica-BoldOblique"),

            pml.TIMES_ROMAN: FontInfo("Times-Roman"),
            pml.TIMES_ROMAN | pml.BOLD: FontInfo("Times-Bold"),
            pml.TIMES_ROMAN | pml.ITALIC: FontInfo("Times-Italic"),
            pml.TIMES_ROMAN | pml.BOLD | pml.ITALIC:
                FontInfo("Times-BoldItalic"),
        }

    # generate PDF document and return it as a string
    def generate(self) -> bytes:
        doc = self.doc
        canvas = Canvas(
            '',
            pdfVersion=(1, 5),
            pagesize=(self.mm2points(doc.w), self.mm2points(doc.h)),
            initialFontName=self.getFontForFlags(pml.NORMAL),
        )

        # set PDF info
        version = self.doc.version
        canvas.setCreator('Trelby '+version)
        canvas.setProducer('Trelby '+version)
        if self.doc.uniqueId:
            canvas.setKeywords(self.doc.uniqueId)


        if doc.defPage != -1:
            # canvas.addLiteral("/OpenAction [%d 0 R /XYZ null null 0]\n" % (self.pageObjs[0].nr + doc.defPage * 2)) # this should make the PDF reader open the PDF at the desired page
            # TODO: This doesn't seem to be easily doable with reportlab. /OpenAction is considered a security threat by some (as it allows executing JavaScript), so I think it's unlikely they'll add support. Also, this feature didn't work with many PDF viewers anyway; I tested Evince, Okular and pdf.js in Firefox, and they all didn't support it. So maybe, we should remove this feature entirely?
            pass

        numberOfPages: int = len(doc.pages)

        # draw pages
        for i in range(numberOfPages):
            pg = self.doc.pages[i]
            for op in pg.ops:
                op.pdfOp.draw(op, i, self, canvas)

            if i < numberOfPages - 1:
                canvas.showPage()

        if doc.showTOC:
            canvas.showOutline()

        return canvas.getpdfdata()

    # generate a stream object's contents. 's' is all data between
    # 'stream/endstream' tags, excluding newlines.
    def genStream(self, s, isFontStream = False) -> str:
        compress = False

        # embedded TrueType font program streams for some reason need a
        # Length1 entry that records the uncompressed length of the stream
        if isFontStream:
            lenStr = "/Length1 %d\n" % len(s)
        else:
            lenStr = ""

        filterStr = " "
        if compress:
            s = s.encode("zlib")
            filterStr = "/Filter /FlateDecode\n"

        return ("<< /Length %d\n%s%s>>\n"
                "stream\n"
                "%s\n"
                "endstream" % (len(s), lenStr, filterStr, s))


    # get font name to use for given flags. also registers the font in reportlabs if it does not yet exist.
    def getFontForFlags(self, flags: int) -> str:
        # the "& 15" gets rid of the underline flag
        fontInfo = self.fonts.get(flags & 15)

        if not fontInfo:
            raise Exception("PDF.getfontNr: invalid flags %d" % flags)

        # the "& 15" gets rid of the underline flag
        customFontInfo = self.doc.fonts.get(flags & 15)

        if not customFontInfo:
            return fontInfo.name

        if not customFontInfo.name in pdfmetrics.getRegisteredFontNames():
            if not customFontInfo.fontFileName:
                raise Exception('Font name "%s" is not known and no font file name provided. Please provide a file name for this font in the settings or use the default font.' % customFontInfo.name)
            pdfmetrics.registerFont(TTFont(customFontInfo.name, customFontInfo.fontFileName))

        return customFontInfo.name

    # escape string
    def escapeStr(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # convert mm to points (1/72 inch).
    def mm2points(self, mm: float) -> float:
        # 2.834 = 72 / 25.4
        return mm * 2.83464567

    # convert x coordinate
    def x(self, x: float) -> float:
        return self.mm2points(x)

    # convert y coordinate
    def y(self, y: float) -> float:
        return self.mm2points(self.doc.h - y)

    # convert xy, which is (x, y) pair, into PDF coordinates
    def xy(self, xy: Tuple[float, float]) -> Tuple[float, float]:
        x = self.x(xy[0])
        y = self.y(xy[1])

        return (x, y)
