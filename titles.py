import pml
import util

# a script's title pages.
class Titles:

    def __init__(self):
        # list of lists of TitleString objects
        self.pages = []

    # create semi-standard title page
    def addDefaults(self):
        a = []

        y = 70.0
        a.append(TitleString("UNTITLED SCREENPLAY", y = y, size = 24,
                             isBold = True, font = pml.HELVETICA))
        a.append(TitleString("by", y = y + 15.46))
        a.append(TitleString("My Name Here", y = y + 23.93))

        x = 150.0
        y = 240.0
        a.append(TitleString("42 Random Street", x, y, False))
        a.append(TitleString("Nowhere, CA 90210", x, y + 4.23, False))
        a.append(TitleString("123/456-7890", x, y + 8.46, False))
        a.append(TitleString("no.such@thing.com", x, y + 12.7, False))
        
        self.pages.append(a)

    # add title pages to doc.
    def generatePages(self, doc):
        for page in self.pages:
            pg = pml.Page(doc)

            for s in page:
                s.generatePML(pg)

            doc.add(pg)

    # return a (rough) RTF fragment representation of title pages
    def generateRTF(self):
        s = util.String()

        for page in self.pages:
            for p in page:
                s += p.generateRTF()

            s += "\\page\n"

        return str(s)

    # sort the title strings in y,x order (makes editing them easier
    # and RTF output better)
    def sort(self):
        def tmpfunc(a, b):
            return cmp(a.y, b.y) or cmp(a.x, b.x)

        for page in self.pages:
            page.sort(tmpfunc)
        
    def __eq__(self, other):
        if len(self.pages) != len(other.pages):
            return False

        for pg in xrange(len(self.pages)):

            if len(self.pages[pg]) != len(other.pages[pg]):
                return False
            
            for i in xrange(len(self.pages[pg])):
                if self.pages[pg][i] != other.pages[pg][i]:
                    return False

        return True
    
    def __ne__(self, other):
        return not self == other

# a single string displayed on a title page
class TitleString:
    def __init__(self, text = "", x = 0.0, y = 0.0, isCentered = True,
                 isBold = False, size = 12, font = pml.COURIER):

        # contents of string
        self.text = text

        # position
        self.x = x
        self.y = y

        # size in points
        self.size = size

        # whether this is centered in the horizontal direction
        self.isCentered = isCentered

        # style flags
        self.isBold = isBold
        self.isItalic = False
        self.isUnderlined = False

        # font
        self.font = font

    def getStyle(self):
        fl = self.font

        if self.isBold:
            fl |= pml.BOLD

        if self.isItalic:
            fl |= pml.ITALIC

        if self.isUnderlined:
            fl |= pml.UNDERLINED

        return fl
    
    def generatePML(self, page):
        x = self.x

        align = util.ALIGN_LEFT

        if self.isCentered:
            x = page.doc.w / 2.0
            align = util.ALIGN_CENTER

        page.add(pml.TextOp(self.text, x, self.y, self.size,
                            self.getStyle(), align))

    # return a (rough) RTF fragment representation of this string
    def generateRTF(self):
        tmp = "\\fs%d" % (self.size * 2)

        if self.isCentered:
            tmp += " \qc"

        if self.isBold:
            tmp += r" \b"

        if self.isItalic:
            tmp += r" \i"

        if self.isUnderlined:
            tmp += r" \ul"

        return r"{\pard\plain%s %s}{\par}" % (tmp, util.escapeRTF(self.text))
        
    # parse information from s, which must be a string created by __str__,
    # and set object state accordingly. keeps default settings on any
    # errors, does not throw any exceptions.
    #
    # sample of the format: '0.000000,70.000000,24,cb,Helvetica,,text here'
    def load(self, s):
        a = s.split(",", 6)

        if len(a) != 7:
            return
        
        self.x = util.str2float(a[0], 0.0)
        self.y = util.str2float(a[1], 0.0)
        self.size = util.str2int(a[2], 12, 4, 288)

        self.isCentered, self.isBold, self.isItalic, self.isUnderlined = \
            util.flags2bools(a[3], "cbiu")

        tmp = { "Courier" : pml.COURIER,
                "Helvetica" : pml.HELVETICA,
                "Times" : pml.TIMES_ROMAN }

        self.font = tmp.get(a[4], pml.COURIER)

        self.text = a[6]
                       
    def __str__(self):
        s = "%f,%f,%d," % (self.x, self.y, self.size)

        s += util.bools2flags("cbiu", self.isCentered, self.isBold,
                               self.isItalic, self.isUnderlined)
        s += ","
        
        if self.font == pml.COURIER:
            s += "Courier"
        elif self.font == pml.HELVETICA:
            s += "Helvetica"
        else:
            s += "Times"

        s += ",,%s" % self.text

        return s

    def __eq__(self, other):
        for k in self.__dict__.iterkeys():
            if getattr(self, k) != getattr(other, k):
                return False

        return True
    
    def __ne__(self, other):
        return not self == other
