import screenplay

import zlib


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
#
# why we store the line data as compressed text, not as a list of Line
# objects, is because it's both faster and uses much less memory to do so.
# figures from a 32-bit machine (a 64-bit machine wastes even more space
# storing Line objects) from speedTest for a 119-page screenplay:
#
#   -Line objects: 1,770 KB, 0.125s
#   -text, not compressed: 352 KB, 0.078s
#   -text, zlib fastest(1): 76 KB, 0.088s
#   -text, zlib medium(6): 36 KB, 0.091s
#   -text, zlib best(9): 35 KB, 0.093s
#   -text, bz2 best(9): 42 KB, 0.228s
#
class FullCopy(Base):
    def __init__(self, sp):
        Base.__init__(self, sp, CMD_MISC)

        lines = [str(ln) for ln in sp.lines]
        self.linesBeforeRaw = zlib.compress("\n".join(lines), 6)

    # called after editing action is over to snapshot the "after" state
    def setAfter(self, sp):
        lines = [str(ln) for ln in sp.lines]
        self.linesAfterRaw = zlib.compress("\n".join(lines), 6)

        self.setEndPos(sp)

    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column

        sp.lines = [screenplay.Line.fromStr(s) for s in
                    zlib.decompress(self.linesBeforeRaw).split("\n")]

    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column

        sp.lines = [screenplay.Line.fromStr(s) for s in
                    zlib.decompress(self.linesAfterRaw).split("\n")]


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
