import array

class NameArray:
    def __init__(self):
        self.maxCount = 205000
        self.count = 0
        
        self.name = [None,] * self.maxCount

        self.type = array.array('B')
        self.type.fromstring(chr(0) * self.maxCount)

        self.sex = array.array('B')
        self.sex.fromstring(chr(0) * self.maxCount)

        # these two are indexed by type, first contains type names, second
        # frequencies.
        self.typeNames = []
        self.typeFreqs = []

    def append(self, name, type, sex):
        if self.count >= self.maxCount:
            for i in range(1000):
                self.name.append(None)
                self.type.append(0)
                self.sex.append(0)

            self.maxCount += 1000

        self.name[self.count] = name
        self.type[self.count] = type
        self.sex[self.count] = sex

        self.count += 1
        
    def toStr(self, n):
        if self.sex[n]:
            s = "M"
        else:
            s = "F"
            
        return "%s\t%s\t%s" % (self.name[n], self.typeNames[self.type[n]],
                               s)
