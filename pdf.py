import util

class PDFExporter:
    def __init__(self):
        pass

    # generate PDF document from given data. returns a string containing
    # the PDF data.
    def generate(self):

        # the stupid 'f' thingy in the xref table is an object of some
        # kind or something...
        self.objectCnt = 1
        
        self.data = util.String()
        self.xref = util.String()

        self.addXref(65535, "f")

        self.data += "%PDF-1.4\n"
        
        # FIXME: test data, remove
        pages = 1
        fonts = 1
        fontObjNr = 5
        kids = "[3 0 R]"
        parentPageObjNr = 2
        
        self.addObj("<< /Type /Catalog\n"
                    "/Pages 2 0 R\n"
                    ">>")

        self.addObj("<< /Type /Pages\n"
                    "/Kids %s\n"
                    "/Count %d\n"
                    "/MediaBox [0 0 612 792]\n"
                    "/Resources << /Font << /F1 %d 0 R >> >>\n"
                    ">>" % (kids, pages, fontObjNr))

        self.addObj("<< /Type /Page\n"
                    "/Parent %d 0 R\n"
                    "/Contents 4 0 R\n"
                    ">>" % (parentPageObjNr))

        self.addObj("<< /Length 44 >>\n"
                    "stream\n"
                    "BT\n"
                    "/F1 12 Tf\n"
                    "100 100 Td\n"
                    "(Hello World) Tj\n"
                    "ET\n"
                    "endstream"
                    )

        self.addObj("<< /Type /Font\n"
                    "/Subtype /Type1\n"
                    "/BaseFont /Courier\n"
                    "/Encoding /WinAnsiEncoding\n"
                    ">>")

        xrefPos = self.data.getPos()

        self.data += "xref\n0 6\n"
        self.data += str(self.xref) + "\n"

        self.data += "trailer\n<< /Size 6\n/Root 1 0 R\n>>\n"
        self.data += "startxref\n%d\n%%%%EOF\n" % (xrefPos)

        return str(self.data)

    # add new object. 's' is all data between 'obj/endobj' tags, excluding
    # newlines. adds an xref for the object also.
    def addObj(self, s):
        self.addXref()
        self.data += "%d 0 obj\n%s\nendobj\n" % (self.objectCnt, s)
        self.objectCnt += 1
        
    # add a reference to the xref table, using generation 'gen' and type
    # 'typ'.
    def addXref(self, gen = 0, typ = "n"):
        self.xref += "%010d %05d %s \n" % (self.data.getPos(), gen, typ)
