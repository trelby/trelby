import screenplay

import zlib


# possible command types. only used for possibly merging consecutive edits.
CMD_ADD_CHAR, CMD_MISC = range(2)

# convert a list of Screenplay.Line objects into an unspecified, but
# compact, form of storage. storage2lines will convert this back to the
# original form.
#
# the return type is a tuple: (numberOfLines, ...). the number and type of
# elements after the first is of no concern to the caller.
#
# implementation notes:
#
#   tuple[1]: bool; True if tuple[2] is zlib-compressed
#
#   tuple[2]: string; the line objects converted to their string
#   representation and joined by the "\n" character
#
def lines2storage(lines):
    lines = [str(ln) for ln in lines]
    linesStr = "\n".join(lines)

    # instead of having an arbitrary cutoff figure ("compress if < X
    # bytes"), always compress, but only use the compressed version if
    # it's shorter than the non-compressed one.

    linesStrCompressed = zlib.compress(linesStr, 6)

    if len(linesStrCompressed) < len(linesStr):
        return (len(lines), True, linesStrCompressed)
    else:
        return (len(lines), False, linesStr)

# see lines2storage.
def storage2lines(storage):
    if storage[1]:
        linesStr = zlib.decompress(storage[2])
    else:
        linesStr = storage[2]

    return [screenplay.Line.fromStr(s) for s in linesStr.split("\n")]

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
# we store the line data as compressed text, not as a list of Line
# objects, because it takes much less memory to do so. figures from a
# 32-bit machine (a 64-bit machine wastes even more space storing Line
# objects) from speedTest for a 120-page screenplay (Casablanca):
#
#   -Line objects:         1,737 KB, 0.113s
#   -text, not compressed:   267 KB, 0.076s
#   -text, zlib fastest(1):  127 KB, 0.090s
#   -text, zlib medium(6):   109 KB, 0.115s
#   -text, zlib best(9):     107 KB, 0.126s
#   -text, bz2 best(9):       88 KB, 0.147s
class FullCopy(Base):
    def __init__(self, sp):
        Base.__init__(self, sp, CMD_MISC)

        self.linesBeforeRaw = lines2storage(sp.lines)

    # called after editing action is over to snapshot the "after" state
    def setAfter(self, sp):
        self.linesAfterRaw = lines2storage(sp.lines)
        self.setEndPos(sp)

    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column
        sp.lines = storage2lines(self.linesBeforeRaw)

    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column
        sp.lines = storage2lines(self.linesAfterRaw)


# stores a single modified paragraph
class SinglePara(Base):
    # line is any line belonging to the modified paragraph. there is no
    # requirement for the cursor to be in this paragraph.
    def __init__(self, sp, cmdType, line):
        Base.__init__(self, sp, cmdType)

        self.elemStartLine = sp.getParaFirstIndexFromLine(line)
        endLine = sp.getParaLastIndexFromLine(line)

        self.linesBefore = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

        # FIXME: debug stuff, remove
        #print "init: start: %d end: %d line: %d" % (self.elemStartLine, endLine, line)

    # called after editing action is over to snapshot the "after" state
    def setAfter(self, sp):
        # if all we did was modify a single paragraph, the index of its
        # starting line can not have changed, because that would mean one of
        # the paragraphs above us had changed as well, which is a logical
        # impossibility. so we can find the dimensions of the modified
        # paragraph by starting at the first line.

        endLine = sp.getParaLastIndexFromLine(self.elemStartLine)

        # FIXME: debug stuff, remove
        #print "setAfter: start: %d end: %d" % (self.elemStartLine, endLine)

        self.linesAfter = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

        self.setEndPos(sp)

    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column

        # FIXME: debug stuff, remove
        #print "undo: start: %d len: %d" % (self.elemStartLine, self.linesAfter[0]))

        sp.lines[self.elemStartLine : self.elemStartLine + self.linesAfter[0]] = \
            storage2lines(self.linesBefore)

    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column

        sp.lines[self.elemStartLine : self.elemStartLine + self.linesBefore[0]] = \
            storage2lines(self.linesAfter)
