import config
import util

import copy

# keep track about one object's variables
class Vars:
    def __init__(self):
        self.cvars = []

    def __iter__(self):
        for v in self.cvars:
            yield v

    # make various dictionaries pointing to the config variables.
    def makeDicts(self):
        self.all = self.getDict()
        self.color = self.getDict(ColorVar)
        self.numeric = self.getDict(NumericVar)
        self.stringLatin1 = self.getDict(StrLatin1Var)

    # return dictionary containing given type of variable objects, or all
    # if typeObj is None.
    def getDict(self, typeObj = None):
        tmp = {}

        for it in self.cvars:
            if not typeObj or isinstance(it, typeObj):
                tmp[it.name] = it

        return tmp

    # get default value of a setting
    def getDefault(self, name):
        return self.all[name].defVal

    # get minimum value of a numeric setting
    def getMin(self, name):
        return self.numeric[name].minVal

    # get maximum value of a numeric setting
    def getMax(self, name):
        return self.numeric[name].maxVal

    # get minimum and maximum value of a numeric setting as a (min,max)
    # tuple.
    def getMinMax(self, name):
        return (self.getMin(name), self.getMax(name))

    def setDefaults(self, obj):
        for it in self.cvars:
            setattr(obj, it.name, copy.deepcopy(it.defVal))

    # transform string 's' (loaded from file) into a form suitable for
    # load() to take.
    @staticmethod
    def makeVals(s):
        tmp = util.fixNL(str(s)).split("\n")

        vals = {}
        for it in tmp:
            if it.find(":") != -1:
                name, v = it.split(":", 1)
                vals[name] = v

        return vals

    def save(self, prefix, obj):
        s = ""

        for it in self.cvars:
            if it.name2:
                s += it.toStr(getattr(obj, it.name), prefix + it.name2)

        return s

    def load(self, vals, prefix, obj):
        for it in self.cvars:
            if it.name2:
                name = prefix + it.name2
                if name in vals:
                    res = it.fromStr(vals, vals[name], name)
                    setattr(obj, it.name, res)
                    del vals[name]

    def addVar(self, var):
        self.cvars.append(var)

    def addBool(self, *params):
        self.addVar(BoolVar(*params))

    def addColor(self, name, r, g, b, name2, descr):
        self.addVar(ColorVar(name + "Color", util.MyColor(r, g, b),
                             "Color/" + name2, descr))

    def addFloat(self, *params):
        self.addVar(FloatVar(*params))

    def addInt(self, *params):
        self.addVar(IntVar(*params))

    def addStrLatin1(self, *params):
        self.addVar(StrLatin1Var(*params))

    def addStrUnicode(self, *params):
        self.addVar(StrUnicodeVar(*params))

    def addStrBinary(self, *params):
        self.addVar(StrBinaryVar(*params))

    def addElemName(self, *params):
        self.addVar(ElementNameVar(*params))

    def addList(self, *params):
        self.addVar(ListVar(*params))

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

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, str(bool(val)))

    def fromStr(self, vals, val, prefix):
        return val == "True"

class ColorVar(ConfVar):
    def __init__(self, name, defVal, name2, descr):
        ConfVar.__init__(self, name, defVal, name2)
        self.descr = descr

    def toStr(self, val, prefix):
        return "%s:%d,%d,%d\n" % (prefix, val.r, val.g, val.b)

    def fromStr(self, vals, val, prefix):
        v = val.split(",")
        if len(v) != 3:
            return copy.deepcopy(self.defVal)

        r = util.str2int(v[0], 0, 0, 255)
        g = util.str2int(v[1], 0, 0, 255)
        b = util.str2int(v[2], 0, 0, 255)

        return util.MyColor(r, g, b)

class NumericVar(ConfVar):
    def __init__(self, name, defVal, name2, minVal, maxVal):
        ConfVar.__init__(self, name, defVal, name2)
        self.minVal = minVal
        self.maxVal = maxVal

class FloatVar(NumericVar):
    def __init__(self, name, defVal, name2, minVal, maxVal, precision = 2):
        NumericVar.__init__(self, name, defVal, name2, minVal, maxVal)
        self.precision = precision

    def toStr(self, val, prefix):
        return "%s:%.*f\n" % (prefix, self.precision, val)

    def fromStr(self, vals, val, prefix):
        return util.str2float(val, self.defVal, self.minVal, self.maxVal)

class IntVar(NumericVar):
    def __init__(self, name, defVal, name2, minVal, maxVal):
        NumericVar.__init__(self, name, defVal, name2, minVal, maxVal)

    def toStr(self, val, prefix):
        return "%s:%d\n" % (prefix, val)

    def fromStr(self, vals, val, prefix):
        return util.str2int(val, self.defVal, self.minVal, self.maxVal)

# ISO-8859-1 (Latin 1) string.
class StrLatin1Var(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, util.toUTF8(val))

    def fromStr(self, vals, val, prefix):
        return util.fromUTF8(val)

# Unicode string.
class StrUnicodeVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, str(val))

    def fromStr(self, vals, val, prefix):
        return val

# binary string, can contain anything. characters outside of printable
# ASCII (and \ itself) are encoded as \XX, where XX is the hex code of the
# character.
class StrBinaryVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, util.encodeStr(val))

    def fromStr(self, vals, val, prefix):
        return util.decodeStr(val)

# screenplay.ACTION <-> "Action"
class ElementNameVar(ConfVar):
    def __init__(self, name, defVal, name2):
        ConfVar.__init__(self, name, defVal, name2)

    def toStr(self, val, prefix):
        return "%s:%s\n" % (prefix, config.lt2ti(val).name)

    def fromStr(self, vals, val, prefix):
        ti = config.name2ti(val)

        if ti:
            return ti.lt
        else:
            return self.defVal

class ListVar(ConfVar):
    def __init__(self, name, defVal, name2, itemType):
        ConfVar.__init__(self, name, defVal, name2)

        # itemType is an instance of one of the *Var classes, and is the
        # type of item contained in the list.
        self.itemType = itemType

    def toStr(self, val, prefix):
        s = ""

        s += "%s:%d\n" % (prefix, len(val))

        i = 1
        for v in val:
            s += self.itemType.toStr(v, prefix + "/%d" % i)
            i += 1

        return s

    def fromStr(self, vals, val, prefix):
        # 1000 is totally arbitrary, increase if needed
        count = util.str2int(val, -1, -1, 1000)
        if count == -1:
            return copy.deepcopy(self.defVal)

        tmp = []
        for i in range(1, count + 1):
            name = prefix + "/%d" % i

            if name in vals:
                res = self.itemType.fromStr(vals, vals[name], name)
                tmp.append(res)
                del vals[name]

        return tmp
