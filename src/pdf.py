import fontinfo
import pml
import util

# PDF transform matrixes where key is the angle from x-axis
# in counter-clockwise direction.
TRANSFORM_MATRIX = {
    45 : (1, 1, -1, 1),
    90 : (0, 1, -1, 0),
}

# users should only use this.
def generate(doc):
    tmp = PDFExporter(doc)
    return tmp.generate()

# An abstract base class for all PDF drawing operations.
class PDFDrawOp:

    # write PDF drawing operations corresponding to the PML object pmlOp
    # to output (util.String). pe = PDFExporter.
    def draw(self, pmlOp, pageNr, output, pe):
        raise Exception("draw not implemented")

class PDFTextOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        if pmlOp.toc:
            pmlOp.toc.pageObjNr = pe.pageObjs[pageNr].nr

        # we need to adjust y position since PDF uses baseline of text as
        # the y pos, but pml uses top of the text as y pos. The Adobe
        # standard Courier family font metrics give 157 units in 1/1000
        # point units as the Descender value, thus giving (1000 - 157) =
        # 843 units from baseline to top of text.

        # http://partners.adobe.com/asn/tech/type/ftechnotes.jsp contains
        # the "Font Metrics for PDF Core 14 Fonts" document.

        x = pe.x(pmlOp.x)
        y = pe.y(pmlOp.y) - 0.843 * pmlOp.size

        newFont = "F%d %d" % (pe.getFontNr(pmlOp.flags), pmlOp.size)
        if newFont != pe.currentFont:
            output += "/%s Tf\n" % newFont
            pe.currentFont = newFont

        if pmlOp.angle is not None:
            matrix = TRANSFORM_MATRIX.get(pmlOp.angle)

            if matrix:
                output += "BT\n"\
                    "%f %f %f %f %f %f Tm\n"\
                    "(%s) Tj\n"\
                    "ET\n" % (matrix[0], matrix[1], matrix[2], matrix[3],
                              x, y, pe.escapeStr(pmlOp.text))
            else:
                # unsupported angle, don't print it.
                pass
        else:
            output += "BT\n"\
                "%f %f Td\n"\
                "(%s) Tj\n"\
                "ET\n" % (x, y, pe.escapeStr(pmlOp.text))

        if pmlOp.flags & pml.UNDERLINED:

            undLen = fontinfo.getMetrics(pmlOp.flags).getTextWidth(
                pmlOp.text, pmlOp.size)

            # all standard PDF fonts have the underline line 100 units
            # below baseline with a thickness of 50
            undY = y - 0.1 * pmlOp.size

            output += "%f w\n"\
                      "%f %f m\n"\
                      "%f %f l\n"\
                      "S\n" % (0.05 * pmlOp.size, x, undY, x + undLen, undY)

class PDFLineOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        p = pmlOp.points

        pc = len(p)

        if pc < 2:
            print("LineOp contains only %d points" % pc)

            return

        output += "%f w\n"\
                  "%s m\n" % (pe.mm2points(pmlOp.width), pe.xy(p[0]))

        for i in range(1, pc):
            output += "%s l\n" % (pe.xy(p[i]))

        if pmlOp.isClosed:
            output += "s\n"
        else:
            output += "S\n"

class PDFRectOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        if pmlOp.lw != -1:
            output += "%f w\n" % pe.mm2points(pmlOp.lw)

        output += "%f %f %f %f re\n" % (
            pe.x(pmlOp.x),
            pe.y(pmlOp.y) - pe.mm2points(pmlOp.height),
            pe.mm2points(pmlOp.width), pe.mm2points(pmlOp.height))

        if pmlOp.fillType == pml.NO_FILL:
            output += "S\n"
        elif pmlOp.fillType == pml.FILL:
            output += "f\n"
        elif pmlOp.fillType == pml.STROKE_FILL:
            output += "B\n"
        else:
            print("Invalid fill type for RectOp")

class PDFQuarterCircleOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        sX = pmlOp.flipX and -1 or 1
        sY = pmlOp.flipY and -1 or 1

        # The traditional constant is: 0.552284749
        # however, as described here:
        # http://spencermortensen.com/articles/bezier-circle/,
        # this has a maximum radial drift of 0.027253%.
        # The constant calculated by Spencer Mortensen
        # has a max. drift of 0.019608% which is 28% better.
        A = pmlOp.radius * 0.551915024494

        output += "%f w\n"\
                  "%s m\n" % (pe.mm2points(pmlOp.width),
                              pe.xy((pmlOp.x - pmlOp.radius * sX, pmlOp.y)))

        output += "%f %f %f %f %f %f c\n" % (
            pe.x(pmlOp.x - pmlOp.radius * sX), pe.y(pmlOp.y - A * sY),
            pe.x(pmlOp.x - A * sX), pe.y(pmlOp.y - pmlOp.radius * sY),
            pe.x(pmlOp.x), pe.y(pmlOp.y - pmlOp.radius * sY))

        output += "S\n"

class PDFArbitraryOp(PDFDrawOp):
    def draw(self, pmlOp, pageNr, output, pe):
        output += "%s\n" % pmlOp.cmds

# used for keeping track of used fonts
class FontInfo:
    def __init__(self, name):
        self.name = name

        # font number (the name in the /F PDF command), or -1 if not used
        self.number = -1

        # PDFObject that contains the /Font object for this font, or None
        self.pdfObj = None

# one object in a PDF file
class PDFObject:
    def __init__(self, nr, data = ""):
        # PDF object number
        self.nr = nr

        # all data between 'obj/endobj' tags, excluding newlines
        self.data = data

        # start position of object, stored in the xref table. initialized
        # when the object is written out (by the caller of write).
        self.xrefPos = -1

    # write object to output (util.String).
    def write(self, output):
        output += "%d 0 obj\n" % self.nr
        output += self.data
        output += "\nendobj\n"

class PDFExporter:
    # see genWidths
    _widthsStr = None

    def __init__(self, doc):
        # pml.Document
        self.doc = doc

    # generate PDF document and return it as a string
    def generate(self):
        #lsdjflksj = util.TimerDev("generate")
        doc = self.doc

        # fast lookup of font information
        self.fonts = {
            pml.COURIER : FontInfo("Courier"),
            pml.COURIER | pml.BOLD: FontInfo("Courier-Bold"),
            pml.COURIER | pml.ITALIC: FontInfo("Courier-Oblique"),
            pml.COURIER | pml.BOLD | pml.ITALIC:
              FontInfo("Courier-BoldOblique"),

            pml.HELVETICA : FontInfo("Helvetica"),
            pml.HELVETICA | pml.BOLD: FontInfo("Helvetica-Bold"),
            pml.HELVETICA | pml.ITALIC: FontInfo("Helvetica-Oblique"),
            pml.HELVETICA | pml.BOLD | pml.ITALIC:
              FontInfo("Helvetica-BoldOblique"),

            pml.TIMES_ROMAN : FontInfo("Times-Roman"),
            pml.TIMES_ROMAN | pml.BOLD: FontInfo("Times-Bold"),
            pml.TIMES_ROMAN | pml.ITALIC: FontInfo("Times-Italic"),
            pml.TIMES_ROMAN | pml.BOLD | pml.ITALIC:
              FontInfo("Times-BoldItalic"),
            }

        # list of PDFObjects
        self.objects = []

        # number of fonts used
        self.fontCnt = 0

        # PDF object count. it starts at 1 because the 'f' thingy in the
        # xref table is an object of some kind or something...
        self.objectCnt = 1

        pages = len(doc.pages)

        self.catalogObj = self.addObj()
        self.infoObj = self.createInfoObj()
        pagesObj = self.addObj()

        # we only create this when needed, in genWidths
        self.widthsObj = None

        if doc.tocs:
            self.outlinesObj = self.addObj()

            # each outline is a single PDF object
            self.outLineObjs = []

            for i in range(len(doc.tocs)):
                self.outLineObjs.append(self.addObj())

            self.outlinesObj.data = ("<< /Type /Outlines\n"
                                     "/Count %d\n"
                                     "/First %d 0 R\n"
                                     "/Last %d 0 R\n"
                                     ">>" % (len(doc.tocs),
                                             self.outLineObjs[0].nr,
                                             self.outLineObjs[-1].nr))

            outlinesStr = "/Outlines %d 0 R\n" % self.outlinesObj.nr

            if doc.showTOC:
                outlinesStr += "/PageMode /UseOutlines\n"

        else:
            outlinesStr = ""

        # each page has two PDF objects: 1) a /Page object that links to
        # 2) a stream object that has the actual page contents.
        self.pageObjs = []
        self.pageContentObjs = []

        for i in range(pages):
            self.pageObjs.append(self.addObj("<< /Type /Page\n"
                                             "/Parent %d 0 R\n"
                                             "/Contents %d 0 R\n"
                                             ">>" % (pagesObj.nr,
                                                     self.objectCnt + 1)))
            self.pageContentObjs.append(self.addObj())

        if doc.defPage != -1:
            outlinesStr += "/OpenAction [%d 0 R /XYZ null null 0]\n" % (
                self.pageObjs[0].nr + doc.defPage * 2)

        self.catalogObj.data = ("<< /Type /Catalog\n"
                                "/Pages %d 0 R\n"
                                "%s"
                                ">>" % (pagesObj.nr, outlinesStr))

        for i in range(pages):
            self.genPage(i)

        kids = util.String()
        kids += "["
        for obj in self.pageObjs:
            kids += "%d 0 R\n" % obj.nr
        kids += "]"

        fontStr = ""
        for fi in self.fonts.values():
            if fi.number != -1:
                fontStr += "/F%d %d 0 R " % (fi.number, fi.pdfObj.nr)

        pagesObj.data = ("<< /Type /Pages\n"
                         "/Kids %s\n"
                         "/Count %d\n"
                         "/MediaBox [0 0 %f %f]\n"
                         "/Resources << /Font <<\n"
                         "%s >> >>\n"
                         ">>" % (str(kids), pages, self.mm2points(doc.w),
                                 self.mm2points(doc.h), fontStr))

        if doc.tocs:
            for i in range(len(doc.tocs)):
                self.genOutline(i)

        return self.genPDF()

    def createInfoObj(self):
        version = self.escapeStr(self.doc.version)

        if self.doc.uniqueId:
            extra = "/Keywords (%s)\n" % self.doc.uniqueId
        else:
            extra = ""

        return self.addObj("<< /Creator (Trelby %s)\n"
                           "/Producer (Trelby %s)\n"
                           "%s"
                           ">>" % (version, version, extra))

    # create a PDF object containing a 256-entry array for the widths of a
    # font, with all widths being 600
    def genWidths(self):
        if self.widthsObj:
            return

        if not self.__class__._widthsStr:
            self.__class__._widthsStr = "[%s]" % ("600 " * 256).rstrip()

        self.widthsObj = self.addObj(self.__class__._widthsStr)

    # generate a single page
    def genPage(self, pageNr):
        pg = self.doc.pages[pageNr]

        # content stream
        cont = util.String()

        self.currentFont = ""

        for op in pg.ops:
            op.pdfOp.draw(op, pageNr, cont, self)

        self.pageContentObjs[pageNr].data = self.genStream(str(cont))

    # generate outline number 'i'
    def genOutline(self, i):
        toc = self.doc.tocs[i]
        obj = self.outLineObjs[i]

        if i != (len(self.doc.tocs) - 1):
            nextStr = "/Next %d 0 R\n" % (obj.nr + 1)
        else:
            nextStr = ""

        if i != 0:
            prevStr = "/Prev %d 0 R\n" % (obj.nr - 1)
        else:
            prevStr = ""

        obj.data = ("<< /Parent %d 0 R\n"
                    "/Dest [%d 0 R /XYZ %f %f 0]\n"
                    "/Title (%s)\n"
                    "%s"
                    "%s"
                    ">>" % (
            self.outlinesObj.nr, toc.pageObjNr, self.x(toc.op.x),
            self.y(toc.op.y), self.escapeStr(toc.text),
            prevStr, nextStr))

    # generate a stream object's contents. 's' is all data between
    # 'stream/endstream' tags, excluding newlines.
    def genStream(self, s, isFontStream = False):
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

    # add a new object and return it. 'data' is all data between
    # 'obj/endobj' tags, excluding newlines.
    def addObj(self, data = ""):
        obj = PDFObject(self.objectCnt, data)
        self.objects.append(obj)
        self.objectCnt += 1

        return obj

    # write out object to 'output' (util.String)
    def writeObj(self, output, obj):
        obj.xrefPos = len(output)
        obj.write(output)

    # write a xref table entry to 'output' (util.String), using position
    # 'pos, generation 'gen' and type 'typ'.
    def writeXref(self, output, pos, gen = 0, typ = "n"):
        output += "%010d %05d %s \n" % (pos, gen, typ)

    # generate PDF file and return it as a string
    def genPDF(self):
        data = util.String()

        data += "%PDF-1.5\n"

        for obj in self.objects:
            self.writeObj(data, obj)

        xrefStartPos = len(data)

        data += "xref\n0 %d\n" % self.objectCnt
        self.writeXref(data, 0, 65535, "f")

        for obj in self.objects:
            self.writeXref(data, obj.xrefPos)

        data += "\n"

        data += ("trailer\n"
                 "<< /Size %d\n"
                 "/Root %d 0 R\n"
                 "/Info %d 0 R\n>>\n" % (
            self.objectCnt, self.catalogObj.nr, self.infoObj.nr))

        data += "startxref\n%d\n%%%%EOF\n" % xrefStartPos

        return str(data)

    # get font number to use for given flags. also creates the PDF object
    # for the font if it does not yet exist.
    def getFontNr(self, flags):
        # the "& 15" gets rid of the underline flag
        fi = self.fonts.get(flags & 15)

        if not fi:
            print("PDF.getfontNr: invalid flags %d" % flags)

            return 0

        if fi.number == -1:
            fi.number = self.fontCnt
            self.fontCnt += 1

            # the "& 15" gets rid of the underline flag
            pfi = self.doc.fonts.get(flags & 15)

            if not pfi:
                fi.pdfObj = self.addObj("<< /Type /Font\n"
                                        "/Subtype /Type1\n"
                                        "/BaseFont /%s\n"
                                        "/Encoding /WinAnsiEncoding\n"
                                        ">>" % fi.name)
            else:
                self.genWidths()

                fi.pdfObj = self.addObj("<< /Type /Font\n"
                                        "/Subtype /TrueType\n"
                                        "/BaseFont /%s\n"
                                        "/Encoding /WinAnsiEncoding\n"
                                        "/FirstChar 0\n"
                                        "/LastChar 255\n"
                                        "/Widths %d 0 R\n"
                                        "/FontDescriptor %d 0 R\n"
                                        ">>" % (pfi.name, self.widthsObj.nr,
                                                self.objectCnt + 1))

                fm = fontinfo.getMetrics(flags)

                if pfi.fontProgram:
                    fpStr = "/FontFile2 %d 0 R\n" % (self.objectCnt + 1)
                else:
                    fpStr = ""

                # we use a %s format specifier for the italic angle since
                # it sometimes contains integers, sometimes floating point
                # values.
                self.addObj("<< /Type /FontDescriptor\n"
                            "/FontName /%s\n"
                            "/FontWeight %d\n"
                            "/Flags %d\n"
                            "/FontBBox [%d %d %d %d]\n"
                            "/ItalicAngle %s\n"
                            "/Ascent %s\n"
                            "/Descent %s\n"
                            "/CapHeight %s\n"
                            "/StemV %s\n"
                            "/StemH %s\n"
                            "/XHeight %d\n"
                            "%s"
                            ">>" % (pfi.name,
                                    fm.fontWeight,
                                    fm.flags,
                                    fm.bbox[0], fm.bbox[1],
                                    fm.bbox[2], fm.bbox[3],
                                    fm.italicAngle,
                                    fm.ascent,
                                    fm.descent,
                                    fm.capHeight,
                                    fm.stemV,
                                    fm.stemH,
                                    fm.xHeight,
                                    fpStr))

                if pfi.fontProgram:
                    self.addObj(self.genStream(pfi.fontProgram, True))

        return fi.number

    # escape string
    def escapeStr(self, s):
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    # convert mm to points (1/72 inch).
    def mm2points(self, mm):
        # 2.834 = 72 / 25.4
        return mm * 2.83464567

    # convert x coordinate
    def x(self, x):
        return self.mm2points(x)

    # convert y coordinate
    def y(self, y):
        return self.mm2points(self.doc.h - y)

    # convert xy, which is (x, y) pair, into PDF coordinates, and format
    # it as "%f %f", and return that.
    def xy(self, xy):
        x = self.x(xy[0])
        y = self.y(xy[1])

        return "%f %f" % (x, y)
