import fontinfo
import pml
import util

# users should only use this.
def generate(doc):
    tmp = PDFExporter(doc)
    return tmp.generate()

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
        pagesObj = self.addObj()

        if doc.tocs:
            self.outlinesObj = self.addObj()

            # each outline is a single PDF object
            self.outLineObjs = []
            
            for i in xrange(len(doc.tocs)):
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
        
        for i in xrange(pages):
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

        for i in xrange(pages):
            self.genPage(i)

        kids = util.String()
        kids += "["
        for obj in self.pageObjs:
            kids += "%d 0 R\n" % obj.nr
        kids += "]"

        fontStr = ""
        for fi in self.fonts.itervalues():
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
            for i in xrange(len(doc.tocs)):
                self.genOutline(i)

        return self.genPDF()

    # generate a single page
    def genPage(self, pageNr):
        pg = self.doc.pages[pageNr]

        # content stream
        cont = util.String()

        currentFont = ""

        for op in pg.ops:
            if op.type == pml.OP_TEXT:

                if op.toc:
                    op.toc.pageObjNr = self.pageObjs[pageNr].nr

                # we need to adjust y position since PDF uses baseline of
                # text as the y pos, but pml uses top of the text as y
                # pos. The Adobe standard Courier family font metrics give
                # 157 units in 1/1000 point units as the Descender value,
                # thus giving (1000 - 157) = 843 units from baseline to
                # top of text.

                # http://partners.adobe.com/asn/tech/type/ftechnotes.jsp
                # contains the "Font Metrics for PDF Core 14 Fonts"
                # document.

                x = self.x(op.x)
                y = self.y(op.y) - 0.843 * op.size

                newFont = "F%d %d" % (self.getFontNr(op.flags), op.size)
                if newFont != currentFont:
                    cont += "/%s Tf\n" % newFont
                    currentFont = newFont

                cont += "BT\n"\
                        "%f %f Td\n"\
                        "(%s) Tj\n"\
                        "ET\n" % (x, y, self.escapeStr(op.text))

                if op.flags & pml.UNDERLINED:

                    undLen = fontinfo.getTextWidth(op.text, op.flags,
                                                   op.size)

                    # all standard PDF fonts have the underline line 100
                    # units below baseline with a thickness of 50
                    undY = y - 0.1 * op.size

                    cont += "%f w\n"\
                            "%f %f m\n"\
                            "%f %f l\n"\
                            "S\n" % (0.05 * op.size, x, undY,
                                     x + undLen, undY)

            elif op.type == pml.OP_LINE:
                p = op.points

                pc = len(p)

                if pc < 2:
                    print "LineOp contains only %d points" % pc

                    continue

                cont += "%f w\n"\
                        "%s m\n" % (self.mm2points(op.width),
                                    self.xy(p[0]))

                for i in range(1, pc):
                    cont += "%s l\n" % (self.xy(p[i]))

                if op.isClosed:
                    cont += "s\n"
                else:
                    cont += "S\n"

            elif op.type == pml.OP_RECT:
                if op.lw != -1:
                    cont += "%f w\n" % self.mm2points(op.lw)

                cont += "%f %f %f %f re\n" % (
                    self.x(op.x),
                    self.y(op.y) - self.mm2points(op.height),
                    self.mm2points(op.width), self.mm2points(op.height))

                if op.fillType == pml.NO_FILL:
                    cont += "S\n"
                elif op.fillType == pml.FILL:
                    cont += "f\n"
                elif op.fillType == pml.STROKE_FILL:
                    cont += "B\n"
                else:
                    print "Invalid fill type for pml.OP_RECT"

                    continue

            elif op.type == pml.OP_QC:
                sX = op.flipX and -1 or 1
                sY = op.flipY and -1 or 1

                # the literature on how to emulate quarter circles with
                # Bezier curves is sketchy, but the one thing that is
                # clear is that the two control points have to be on (1,
                # A) and (A, 1) (on a unit circle), and empirically
                # choosing A to be half of the radius results in the best
                # looking quarter circle.
                A = op.radius * 0.5

                cont += "%f w\n"\
                        "%s m\n" % (self.mm2points(op.width),
                                    self.xy((op.x - op.radius * sX, op.y)))

                cont += "%f %f %f %f %f %f c\n" % (
                    self.x(op.x - op.radius * sX), self.y(op.y - A * sY),
                    self.x(op.x - A * sX), self.y(op.y - op.radius * sY),
                    self.x(op.x), self.y(op.y - op.radius * sY))

                cont += "S\n"

            elif op.type == pml.OP_PDF:
                cont += "%s\n" % op.cmds

            else:
                print "unknown op type %d" % op.type

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
    def genStream(self, s):
        compress = True

        filterStr = " "
        if compress:
            s = s.encode("zlib")
            filterStr = "\n/Filter /FlateDecode "
        
        return ("<< /Length %d%s>>\n"
                "stream\n"
                "%s\n"
                "endstream" % (len(s), filterStr, s))

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
        
        data += "%PDF-1.4\n"

        for obj in self.objects:
            self.writeObj(data, obj)

        xrefStartPos = len(data)

        data += "xref\n0 %d\n" % self.objectCnt
        self.writeXref(data, 0, 65535, "f")

        for obj in self.objects:
            self.writeXref(data, obj.xrefPos)

        data += "\n"

        data += "trailer\n<< /Size %d\n/Root %d 0 R\n>>\n"\
                % (self.objectCnt, self.catalogObj.nr)
            
        data += "startxref\n%d\n%%%%EOF\n" % xrefStartPos

        return str(data)
        
    # get font number to use for given flags. also creates the PDF object
    # for the font if it does not yet exist.
    def getFontNr(self, flags):
        # the "& 15" gets rid of the underline flag
        fi = self.fonts.get(flags & 15)

        if not fi:
            print "PDF.getfontNr: invalid flags %d" % flags

            return 0

        if fi.number == -1:
            fi.number = self.fontCnt
            fi.pdfObj = self.addObj("<< /Type /Font\n"
                                    "/Subtype /Type1\n"
                                    "/BaseFont /%s\n"
                                    "/Encoding /WinAnsiEncoding\n"
                                    ">>" % fi.name)
            self.fontCnt += 1

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
