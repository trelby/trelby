import screenplay

# abstract base class for storing undo history. concrete subclasses
# implement undo/redo for specific actions taken on a screenplay.
class Base:
    def __init__(self, sp):
        # cursor position before the action
        self.startPos = screenplay.Mark(sp.line, sp.column)

        # prev/next undo objects in the history
        self.prev = None
        self.next = None

    def undo(self, sp):
        raise NotImplementedError

    def redo(self, sp):
        raise NotImplementedError

    # set cursor position after the action
    def setEndPos(self, sp):
        self.endPos = screenplay.Mark(sp.line, sp.column)

# stores a full copy of the screenplay before/after the action. used by
# actions that modify the screenplay globally.
class FullCopy(Base):
    def __init__(self, sp):
        Base.__init__(self, sp)

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
