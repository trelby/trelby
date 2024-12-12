import array
import collections

class NameArray:
    def __init__(self):
        self.maxCount = 205000
        self.count = 0

        self.name = [None] * self.maxCount
        self.type = array.array('B')
        self.type.frombytes(str.encode(chr(0) * self.maxCount))

        # 0 = female, 1 = male
        self.sex = array.array('B')
        self.sex.frombytes(str.encode(chr(0) * self.maxCount))

        # key = type name, value = count of names for that type
        self.typeNamesCnt = collections.defaultdict(int)

        # key = type name, value = integer id for that type
        self.typeId = {}

        # type names indexed by their integer id
        self.typeNamesById = []

    def append(self, name, type, sex):
        if self.count >= self.maxCount:
            for i in range(1000):
                self.name.append(None)
                self.type.append(0)
                self.sex.append(0)

            self.maxCount += 1000

        typeId = self.addType(type)

        self.name[self.count] = name
        self.type[self.count] = typeId
        self.sex[self.count] = 0 if sex == "F" else 1

        self.count += 1

    def addType(self, type):
        self.typeNamesCnt[type] += 1

        typeId = self.typeId.get(type)

        if typeId is None:
            typeId = len(self.typeNamesById)
            self.typeId[type] = typeId
            self.typeNamesById.append(type)

        return typeId
