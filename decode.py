import namearray
import array

luc = []
lu = []

for i in range(0, 256):
    luc.append(chr(i))
    
    tmp = []
    for i2 in range(8):
        if i & (0x80 >> i2):
            tmp.append(1)
        else:
            tmp.append(0)

    lu.append(tmp)
    
def initBb(data):
    global bo, bio, d

    d = array.array('B')
    d.fromstring(data)

    # byte offset
    bo = 0

    # bit offset
    bio = 8

# get a single bit as an int
def gbi():
    global bio
    
    if bio > 7:
        global bo, c
        
        c = lu[d[bo]]
        bo += 1
        bio = 1

        return c[0]
    else:
        t = c[bio]
        bio += 1

        return t
        
# get a byte as an int
def gby():
    t = 0

    for i in range(8):
        t |= gbi() << (7 - i)

    return t

# get a string. chs is the huffman tree for characters.
def gs():
    st = ""

    r = chs.r
    while 1:
        n = r
        
        while n.v == None:
            n = n.c[gbi()]

        if n.v != 0:
            st += luc[n.v]
        else:
            break

    return st
        
# Huffman tree node
class hn:
    def __init__(self, v = None):

        # left, right child nodes
        self.c = [None, None]

        # value
        self.v = v
            
# Huffman tree.
class ht:

    # loads the huffman tree. if nameArr, read types as strings and record
    # them there
    def __init__(self, nameArr = None):

        # root node
        self.r = hn()
        
        cnt = gby()

        if cnt <= 0:
            raise Exception()
        
        for i in range(cnt):
            le = gby()
            
            if le <= 0:
                raise Exception()
            
            n = self.r
            for i2 in range(le):
                b = gbi()

                if b and not n.c[1]:
                    n.c[1] = hn()
                elif not b and not n.c[0]:
                    n.c[0] = hn()

                n = n.c[b]

            if n.v != None:
                raise Exception()

            if not nameArr:
                n.v = gby()
            else:
                nameArr.typeNames.append(gs())
                nameArr.typeFreqs.append(0)
                n.v = len(nameArr.typeNames) - 1
                
    # get value by reading bits from bitbuffer and going down the tree
    def gv(self):
        n = self.r

        while n.v == None:
            n = n.c[gbi()]

        return n.v
            
# read the name database from 'filename' and return a NameArray object. on
# any error, the item count in it will be zero.
def readNames(filename):
    names = namearray.NameArray()
    
    try:
        f = open(filename, "rb")

        try:
            data = f.read()
        finally:
            f.close()
            
        initBb(data)

        # drop counts
        dcn = ht()

        global chs

        # characters
        chs = ht()

        # types
        tps = ht(names)

        prev = ""

        while 1:
            dc = dcn.gv()
            a = gs()

            if len(a) == 0:
                if dc == 0:
                    break
                else:
                    raise Exception()

            t = tps.gv()
            ism = gbi() == 1

            le = len(prev)
            if dc > le:
                raise Exception()

            nn = prev[0 : le - dc] + a
            names.append(nn, t, ism)
            names.typeFreqs[t] += 1

            prev = nn

        global d
        del d, chs

    except:
        names = namearray.NameArray()

    return names
