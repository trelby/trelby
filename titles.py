import pml
import util

# a script's title pages.
class Titles:

    def __init__(self):
        # list of lists of TitleString objects
        self.pages = []

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

        # whether this is centered in the horizontal direction
        self.isCentered = isCentered

        # size in points
        self.size = size

        # style flags
        self.isBold = isBold
        self.isItalic = False
        self.isUnderlined = False

        # font
        self.font = font

    def generatePML(self, page):
        x = self.x

        fl = self.font

        if self.isBold:
            fl |= pml.BOLD

        if self.isItalic:
            fl |= pml.ITALIC

        if self.isUnderlined:
            fl |= pml.UNDERLINED

        align = util.ALIGN_LEFT

        if self.isCentered:
            x = page.doc.w / 2
            align = util.ALIGN_CENTER

        page.add(pml.TextOp(self.text, x, self.y, self.size, fl, align))

    def __eq__(self, other):
        for k in self.__dict__.iterkeys():
            if getattr(self, k) != getattr(other, k):
                return False

        return True
    
    def __ne__(self, other):
        return not self == other
