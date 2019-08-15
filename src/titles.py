import pml
import util
import functools

# a script's title pages.
class Titles:

    def __init__(self):
        # list of lists of TitleString objects
        self.pages = []

    # create semi-standard title page
    def addDefaults(self):
        a = []

        y = 105.0
        a.append(TitleString(["UNTITLED SCREENPLAY"], y = y, size = 24,
                             isBold = True, font = pml.HELVETICA))
        a.append(TitleString(["by", "", "My Name Here"], y = y + 15.46))

        x = 15.0
        y = 240.0
        a.append(TitleString(["123/456-7890", "no.such@thing.com"], x, y + 8.46, False))

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
        def cmpfunc(a, b):
            return ((a.y > b.y) - (a.y < b.y)) or ((a.x > b.x) - (a.x < a.y))

        for page in self.pages:
            page = sorted(page, key=functools.cmp_to_key(cmpfunc))

# a single string displayed on a title page
class TitleString:
    def __init__(self, items, x = 0.0, y = 0.0, isCentered = True,
                 isBold = False, size = 12, font = pml.COURIER):

        # list of text strings
        self.items = items

        # position
        self.x = x
        self.y = y

        # size in points
        self.size = size

        # whether this is centered in the horizontal direction
        self.isCentered = isCentered

        # whether this is right-justified (xpos = rightmost edge of last
        # character)
        self.isRightJustified = False

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

    def getAlignment(self):
        if self.isCentered:
            return util.ALIGN_CENTER
        elif self.isRightJustified:
            return util.ALIGN_RIGHT
        else:
            return util.ALIGN_LEFT

    def setAlignment(self, align):
        if align == util.ALIGN_CENTER:
            self.isCentered = True
            self.isRightJustified = False
        elif align == util.ALIGN_RIGHT:
            self.isCentered = False
            self.isRightJustified = True
        else:
            self.isCentered = False
            self.isRightJustified = False

    def generatePML(self, page):
        y = self.y

        for line in self.items:
            x = self.x

            if self.isCentered:
                x = page.doc.w / 2.0

            page.add(pml.TextOp(line, x, y, self.size,
                                self.getStyle(), self.getAlignment()))

            y += util.getTextHeight(self.size)

    # return a (rough) RTF fragment representation of this string
    def generateRTF(self):
        s = ""

        for line in self.items:
            tmp = "\\fs%d" % (self.size * 2)

            if self.isCentered:
                tmp += " \qc"
            elif self.isRightJustified:
                tmp += " \qr"

            if self.isBold:
                tmp += r" \b"

            if self.isItalic:
                tmp += r" \i"

            if self.isUnderlined:
                tmp += r" \ul"

            s += r"{\pard\plain%s %s}{\par}" % (tmp, util.escapeRTF(line))

        return s

    # parse information from s, which must be a string created by __str__,
    # and set object state accordingly. keeps default settings on any
    # errors, does not throw any exceptions.
    #
    # sample of the format: '0.000000,70.000000,24,cb,Helvetica,,text here'
    def load(self, s):
        a = util.fromUTF8(s).split(",", 6)

        if len(a) != 7:
            return

        self.x = util.str2float(a[0], 0.0)
        self.y = util.str2float(a[1], 0.0)
        self.size = util.str2int(a[2], 12, 4, 288)

        self.isCentered, self.isRightJustified, self.isBold, self.isItalic, \
            self.isUnderlined = util.flags2bools(a[3], "crbiu")

        tmp = { "Courier" : pml.COURIER,
                "Helvetica" : pml.HELVETICA,
                "Times" : pml.TIMES_ROMAN }

        self.font = tmp.get(a[4], pml.COURIER)
        self.items = util.unescapeStrings(a[6])

    def __str__(self):
        s = "%f,%f,%d," % (self.x, self.y, self.size)

        s += util.bools2flags("crbiu", self.isCentered, self.isRightJustified, self.isBold,
                               self.isItalic, self.isUnderlined)
        s += ","

        if self.font == pml.COURIER:
            s += "Courier"
        elif self.font == pml.HELVETICA:
            s += "Helvetica"
        else:
            s += "Times"

        s += ",,%s" % util.escapeStrings(self.items)

        return s
