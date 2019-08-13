import pml
import util

# a script's headers.
class Headers:

    def __init__(self):
        # list of HeaderString objects
        self.hdrs = []

        # how many empty lines after the headers
        self.emptyLinesAfter = 1

    # create standard headers
    def addDefaults(self):
        h = HeaderString()
        h.text = "${PAGE}."
        h.align = util.ALIGN_RIGHT
        h.line = 1

        self.hdrs.append(h)

    # return how many header lines there are. includes number of empty
    # lines after possible headers.
    def getNrOfLines(self):
        nr = 0

        for h in self.hdrs:
            nr = max(nr, h.line)

        if nr > 0:
            nr += self.emptyLinesAfter

        return nr

    # add headers to given page. 'pageNr' must be a string.
    def generatePML(self, page, pageNr, cfg):
        for h in self.hdrs:
            h.generatePML(page, pageNr, cfg)

# a single header string
class HeaderString:
    def __init__(self):

        # which line, 1-based
        self.line = 1

        # x offset, in characters
        self.xoff = 0

        # contents of string
        self.text = ""

        # whether this is centered in the horizontal direction
        self.align = util.ALIGN_CENTER

        # style flags
        self.isBold = False
        self.isItalic = False
        self.isUnderlined = False

    def generatePML(self, page, pageNr, cfg):
        fl = 0

        if self.isBold:
            fl |= pml.BOLD

        if self.isItalic:
            fl |= pml.ITALIC

        if self.isUnderlined:
            fl |= pml.UNDERLINED

        if self.align == util.ALIGN_LEFT:
            x = cfg.marginLeft
        elif self.align == util.ALIGN_CENTER:
            x = (cfg.marginLeft + (cfg.paperWidth - cfg.marginRight)) / 2.0
        else:
            x = cfg.paperWidth - cfg.marginRight

        fs = cfg.fontSize

        if self.xoff != 0:
            x += util.getTextWidth(" ", pml.COURIER, fs) * self.xoff

        y = cfg.marginTop + (self.line - 1) * util.getTextHeight(fs)

        text = self.text.replace("${PAGE}", pageNr)

        page.add(pml.TextOp(text, x, y, fs, fl, self.align))

    # parse information from s, which must be a string created by __str__,
    # and set object state accordingly. keeps default settings on any
    # errors, does not throw any exceptions.
    #
    # sample of the format: '1,0,r,,${PAGE}.'
    def load(self, s):
        a = util.fromUTF8(s).split(",", 4)

        if len(a) != 5:
            return

        self.line = util.str2int(a[0], 1, 1, 5)
        self.xoff = util.str2int(a[1], 0, -100, 100)

        l, c, self.isBold, self.isItalic, self.isUnderlined = \
            util.flags2bools(a[2], "lcbiu")

        if l:
            self.align = util.ALIGN_LEFT
        elif c:
            self.align = util.ALIGN_CENTER
        else:
            self.align = util.ALIGN_RIGHT

        self.text = a[4]

    def __str__(self):
        s = "%d,%d," % (self.line, self.xoff)

        if self.align == util.ALIGN_LEFT:
            s += "l"
        elif self.align == util.ALIGN_CENTER:
            s += "c"
        else:
            s += "r"

        s += util.bools2flags("biu", self.isBold, self.isItalic,
                              self.isUnderlined)

        s += ",,%s" % self.text

        return s
