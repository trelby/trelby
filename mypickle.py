import util

from wxPython.wx import wxColour

# keep track about one object's variables
class Vars:
    def __init__(self):
        self.cvars = []

    def __iter__(self):
        for v in self.cvars:
            yield v

    def setDefaults(self, obj):
        for it in self.cvars:
            setattr(obj, it.name, it.defVal)
                
    # convert all tracked variables to a string format and return that.
    def save(self, prefix, obj):
        s = ""
        
        for it in self.cvars:
            if it.name2:
                s += it.toStr(getattr(obj, it.name), prefix + it.name2, obj)

        return s
    
    def addVar(self, var):
        self.cvars.append(var)

    def addBool(self, *params):
        self.addVar(BoolVar(*params))

    def addColor(self, name, r, g, b, name2, descr):
        self.addVar(ColorVar(name + "Color", wxColour(r, g, b),
                             "Color/" + name2, descr))
        
    def addFloat(self, *params):
        self.addVar(FloatVar(*params))
        
    def addInt(self, *params):
        self.addVar(IntVar(*params))

    def addStr(self, *params):
        self.addVar(StrVar(*params))

    def addElemName(self, *params):
        self.addVar(ElementNameVar(*params))

    def addList(self, *params):
        self.addVar(ListVar(*params))

    # return dictionary containing given type of variable objects, or all
    # if typeObj is None.
    def getDict(self, typeObj = None):
        tmp = {}
        
        for it in self.cvars:
            if not typeObj or isinstance(it, typeObj):
                tmp[it.name] = it

        return tmp


class ConfVar:
    # name2 is the name to use while saving/loading the variable. if it's
    # empty, the variable is not loaded/saved, i.e. is used only
    # internally.
    def __init__(self, name, defVal, name2):
        self.name = name
        self.defVal = defVal
        self.name2 = name2

class BoolVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix, obj):
        return "%s:%s\n" % (prefix, str(val))

class ColorVar(ConfVar):
    def __init__(self, name, defVal, name2, descr):
        ConfVar.__init__(self, name, defVal, name2)
        self.descr = descr

    def toStr(self, val, prefix, obj):
        return "%s:%d,%d,%d\n" % (prefix, val.Red(), val.Green(), val.Blue())

class NumericVar(ConfVar):
    def __init__(self, name, defVal, name2, minVal, maxVal):
        ConfVar.__init__(self, name, defVal, name2)
        self.minVal = minVal
        self.maxVal = maxVal

class FloatVar(NumericVar):
    def __init__(self, name, defVal, name2, minVal, maxVal, precision = 2):
        NumericVar.__init__(self, name, defVal, name2, minVal, maxVal)
        self.precision = precision

    def toStr(self, val, prefix, obj):
        return "%s:%.*f\n" % (prefix, self.precision, val)
        
class IntVar(NumericVar):
    def __init__(self, name, defVal, name2, minVal, maxVal):
        NumericVar.__init__(self, name, defVal, name2, minVal, maxVal)

    def toStr(self, val, prefix, obj):
        return "%s:%d\n" % (prefix, val)
        
class StrVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)
        
    def toStr(self, val, prefix, obj):
        return "%s:%s\n" % (prefix, util.encodeStr(val))

class ElementNameVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)
        
    def toStr(self, val, prefix, obj):
        return "%s:%s\n" % (prefix, obj.cfg.getType(val).name)

class ListVar(ConfVar):
    def __init__(self, name, defVal, name2, itemType):
        ConfVar.__init__(self, name, defVal, name2)

        # itemType is an instance of one of the *Var classes, and is the
        # type of item contained in the list.
        self.itemType = itemType
        
    def toStr(self, val, prefix, obj):
        s = ""

        s += "%s:%d\n" % (prefix, len(val))

        i = 1
        for v in val:
            s += self.itemType.toStr(v, prefix + "/%d" % i, obj)
            i += 1

        return s
