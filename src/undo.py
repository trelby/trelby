import screenplay

import zlib

# Which command uses which undo object:
#
# command                type
# -------                ------
#
# removeElementTypes     FullCopy
# addChar                SinglePara (possibly merged)
#   charmap
#   namesDlg
# spellCheck             SinglePara
# findAndReplace         SinglePara
# NewElement             ManyElems(1, 2)
# Tab:
#   (end of elem)        ManyElems(1, 2)
#   (middle of elem)     ManyElems(1, 1)
# TabPrev                ManyElems(1, 1)
# insertForcedLineBreak  ManyElems(1, 1)
# deleteForward:
#   (not end of elem)    ManyElems(1, 1) (possibly merged)
#   (end of elem)        ManyElems(2, 1)
# deleteBackward:
#   (not start of elem)  ManyElems(1, 1) (possibly merged)
#   (start of elem)      ManyElems(2, 1)
# convertTypeTo          ManyElems(N, N)
# cut                    AnyDifference
# paste                  AnyDifference


# extremely rough estimate for the base memory usage of a single undo
# object, WITHOUT counting the actual textual differences stored inside
# it. so this figure accounts for the Python object overhead, member
# variable overhead, memory allocation overhead, etc.
#
# this figure does not need to be very accurate.
BASE_MEMORY_USAGE = 1500

# possible command types. only used for possibly merging consecutive
# edits.
(CMD_ADD_CHAR,
 CMD_ADD_CHAR_SPACE,
 CMD_DEL_FORWARD,
 CMD_DEL_BACKWARD,
 CMD_MISC) = list(range(5))

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
    if not lines:
        return (0,)

    lines = [str(ln) for ln in lines]
    linesStr = "\n".join(lines)

    # instead of having an arbitrary cutoff figure ("compress if < X
    # bytes"), always compress, but only use the compressed version if
    # it's shorter than the non-compressed one.

    linesStrCompressed = zlib.compress(linesStr.encode(), 6)

    if len(linesStrCompressed) < len(linesStr):
        return (len(lines), True, linesStrCompressed)
    else:
        return (len(lines), False, linesStr.encode())

# see lines2storage.
def storage2lines(storage):
    if storage[0] == 0:
        return []

    if storage[1]:
        linesStr = zlib.decompress(storage[2]).decode()
    else:
        linesStr = storage[2].decode()

    return [screenplay.Line.fromStr(s) for s in linesStr.split("\n")]

# how much memory is used by the given storage object
def memoryUsed(storage):
    # 16 is a rough estimate for the first two tuple members' memory usage

    if storage[0] == 0:
        return 16

    return 16 + len(storage[2])

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

    # rough estimate of how much memory is used by this undo object. can
    # be overridden by subclasses that need something different.
    def memoryUsed(self):
        return (BASE_MEMORY_USAGE + memoryUsed(self.linesBefore) +
                memoryUsed(self.linesAfter))

    # default implementation for undo. can be overridden by subclasses
    # that need something different.
    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column

        sp.lines[self.elemStartLine : self.elemStartLine + self.linesAfter[0]] = \
            storage2lines(self.linesBefore)

    # default implementation for redo. can be overridden by subclasses
    # that need something different.
    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column

        sp.lines[self.elemStartLine : self.elemStartLine + self.linesBefore[0]] = \
            storage2lines(self.linesAfter)

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

        self.elemStartLine = 0
        self.linesBefore = lines2storage(sp.lines)

    # called after editing action is over to snapshot the "after" state
    def setAfter(self, sp):
        self.linesAfter = lines2storage(sp.lines)
        self.setEndPos(sp)


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

    def setAfter(self, sp):
        # if all we did was modify a single paragraph, the index of its
        # starting line can not have changed, because that would mean one of
        # the paragraphs above us had changed as well, which is a logical
        # impossibility. so we can find the dimensions of the modified
        # paragraph by starting at the first line.

        endLine = sp.getParaLastIndexFromLine(self.elemStartLine)

        self.linesAfter = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

        self.setEndPos(sp)


# stores N modified consecutive elements
class ManyElems(Base):
    # line is any line belonging to the first modified element. there is
    # no requirement for the cursor to be in this paragraph.
    # nrOfElemsStart is how many elements there are before the edit
    # operaton and nrOfElemsEnd is how many there are after. so an edit
    # operation splitting an element would pass in (1, 2) while an edit
    # operation combining two elements would pass in (2, 1).
    def __init__(self, sp, cmdType, line, nrOfElemsStart, nrOfElemsEnd):
        Base.__init__(self, sp, cmdType)

        self.nrOfElemsEnd = nrOfElemsEnd

        self.elemStartLine, endLine = sp.getElemIndexesFromLine(line)

        # find last line of last element to include in linesBefore
        for i in range(nrOfElemsStart - 1):
            endLine = sp.getElemLastIndexFromLine(endLine + 1)

        self.linesBefore = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

    def setAfter(self, sp):
        endLine = sp.getElemLastIndexFromLine(self.elemStartLine)

        for i in range(self.nrOfElemsEnd - 1):
            endLine = sp.getElemLastIndexFromLine(endLine + 1)

        self.linesAfter = lines2storage(
            sp.lines[self.elemStartLine : endLine + 1])

        self.setEndPos(sp)

# stores a single block of changed lines by diffing before/after states of
# a screenplay
class AnyDifference(Base):
    def __init__(self, sp):
        Base.__init__(self, sp, CMD_MISC)

        self.linesBefore = [screenplay.Line(ln.lb, ln.lt, ln.text) for ln in sp.lines]

    def setAfter(self, sp):
        self.a, self.b, self.x, self.y = mySequenceMatcher(self.linesBefore, sp.lines)

        self.removed = lines2storage(self.linesBefore[self.a : self.b])
        self.inserted = lines2storage(sp.lines[self.x : self.y])

        self.setEndPos(sp)

        del self.linesBefore

    def memoryUsed(self):
        return (BASE_MEMORY_USAGE + memoryUsed(self.removed) +
                memoryUsed(self.inserted))

    def undo(self, sp):
        sp.line, sp.column = self.startPos.line, self.startPos.column

        sp.lines[self.x : self.y] = storage2lines(self.removed)

    def redo(self, sp):
        sp.line, sp.column = self.endPos.line, self.endPos.column

        sp.lines[self.a : self.b] = storage2lines(self.inserted)


# Our own implementation of difflib.SequenceMatcher, since the actual one
# is too slow for our custom needs.
#
# l1, l2 = lists to diff. List elements must have __ne__ defined.
#
# Return a, b, x, y such that l1[a:b] could be replaced with l2[x:y] to
# convert l1 into l2.
def mySequenceMatcher(l1, l2):
    len1 = len(l1)
    len2 = len(l2)

    if len1 >= len2:
        bigger = l1
        smaller = l2
        bigLen = len1
        smallLen = len2
        l1Big = True
    else:
        bigger = l2
        smaller = l1
        bigLen = len2
        smallLen = len1
        l1Big = False

    i = 0
    a = b = 0

    m1found = False

    while a < smallLen:
        if not m1found and (bigger[a] != smaller[a]):
            b = a
            m1found = True
            break

        a += 1

    if not m1found:
        a = b = smallLen

    num = smallLen - a + 1
    i = 1
    c = bigLen
    d = smallLen

    while (i <= num) and (i <= smallLen):
        c = bigLen - i + 1
        d = smallLen - i + 1

        if bigger[-i] != smaller[-i]:
            break

        i += 1

    if not l1Big:
        a, c, b, d = a, d, b, c

    return a, c, b, d
