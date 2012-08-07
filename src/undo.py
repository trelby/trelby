import screenplay

# possible command types. only used for possibly merging consecutive edits.
CMD_ADD_CHAR, CMD_MISC = range(2)

# abstract base class for storing undo history. concrete subclasses
# implement undo/redo for specific actions taken on a screenplay.
class Base:
    def __init__(self, sp, cmdType):
        # cursor position before the action
        self.startPos = sp.cursorAsMark()

        # type of action; one of the CMD_ values
        self.cmdType = cmdType

        # prev/next undo objects in the history
        self.prev = None
        self.next = None

    # set cursor position after the action
    def setEndPos(self, sp):
        self.endPos = sp.cursorAsMark()

    def getType(self):
        return self.cmdType

    def undo(self, sp):
        raise NotImplementedError

    def redo(self, sp):
        raise NotImplementedError


# stores a full copy of the screenplay before/after the action. used by
# actions that modify the screenplay globally.
class FullCopy(Base):
    def __init__(self, sp):
        Base.__init__(self, sp, CMD_MISC)

        self.linesBefore = [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in sp.lines]

    # called after editing action is over to snapshot the "after" state
    def setAfter(self, sp):
        self.linesAfter = [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in sp.lines]
        self.setEndPos(sp)

    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column
        sp.lines = [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in self.linesBefore]

    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column
        sp.lines = [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in self.linesAfter]


# stores a single modified paragraph
class SinglePara(Base):
    # line is any line belonging to the modified paragraph. there is no
    # requirement for the cursor to be in this paragraph.
    def __init__(self, sp, cmdType, line):
        Base.__init__(self, sp, cmdType)

        self.elemStartLine = sp.getParaFirstIndexFromLine(line)
        endLine = sp.getParaLastIndexFromLine(line)

        self.linesBefore = [
            screenplay.Line(ln.lb, ln.lt, ln.text) for ln in
            sp.lines[self.elemStartLine : endLine + 1]]

        # FIXME: debug stuff, remove
        #print "init: start: %d end: %d line: %d" % (self.elemStartLine, endLine, line)

    # called after editing action is over to snapshot the "after" state
    def setAfter(self, sp):
        # if all we did was modify a single paragraph, the index of its
        # starting line can not have changed, because that would mean one of
        # the paragraphs above us had changed as well, which is a logical
        # impossibility. so we can find the dimensions of the modified
        # paragraph by starting at the first line.

        endLine = sp.getParaLastIndexFromLine(self.startPos.line)

        # FIXME: debug stuff, remove
        #print "setAfter: start: %d end: %d" % (self.elemStartLine, endLine)

        self.linesAfter = [
            screenplay.Line(ln.lb, ln.lt, ln.text) for ln in
            sp.lines[self.elemStartLine : endLine + 1]]

        self.setEndPos(sp)

    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column

        # FIXME: debug stuff, remove
        #print "undo: start: %d len: %d" % (self.elemStartLine, len(self.linesAfter))

        sp.lines[self.elemStartLine : self.elemStartLine + len(self.linesAfter)] = \
            [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in self.linesBefore]

    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column

        sp.lines[self.elemStartLine : self.elemStartLine + len(self.linesBefore)] = \
            [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in self.linesAfter]
