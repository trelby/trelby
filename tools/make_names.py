#!/usr/bin/env python

import string
import sys
import huffman

class name:
    def __init__(self, dropCnt, appendix, origin, isMale):
        self.dropCnt = dropCnt
        self.appendix = appendix
        self.origin = origin
        self.isMale = isMale
        
class item:
    def __repr__(self):
        return "'%s' %6d %s" % (self.val, self.freq, self.code)

def addFreq(h, val):
    if val in h:
        h[val].freq += 1
    else:
        it = item()
        it.val = val
        it.freq = 1
        h[val] = it

def matchingChars(s1, s2):
    i = 0

    while 1:
        if (i >= len(s1)) or (i >= len(s2)):
            break

        if s1[i] != s2[i]:
            break

        i += 1
        
    return i

def encodeByte(b):
    tmp = ""
    
    for i in range(8):
        if b & ((1 << 7) >> i):
            tmp += "1"
        else:
            tmp += "0"

    return tmp
    
def encodeTree(h, valIsChar, charTree = None):
    tmp = ""

    tmp += encodeByte(len(h))

    for i in h.values():
        tmp += encodeByte(len(i.code))
        tmp += i.code

        if not charTree:
            if valIsChar:
                if i.val != "":
                    tmp += encodeByte(ord(i.val))
                else:
                    tmp += encodeByte(0)
            else:
                tmp += encodeByte(i.val)
        else:
            for c in i.val:
                tmp += charTree[c].code
            tmp += charTree[""].code

    return tmp
    
def outputBinary(filename, digits):
    f = open(filename, "wb")

    bytes = len(digits) / 8
    for i in range(bytes):
        byte = 0

        for i2 in range(8):
            if digits[i * 8 + i2] == "1":
                byte |= (1 << 7) >> i2

        f.write(chr(byte))

        if (i % 80000) == 0:
            print "%.2f%% done" % (i * 100.0 / bytes)
    
    f.close()

def printStats(h, name, fullStats = False):
    mi = 500
    ma = -500
    
    for i in h.values():
        mi = min(mi, len(i.code))
        ma = max(ma, len(i.code))

        if fullStats:
            print "'%2s' (%6d): %s" % (i.val, i.freq, i.code)
        
    print "Stats for %-10s %3d total values, min/max code lengths %d / %02d"\
          % (name, len(h), mi, ma)

    if len(h) > 255:
        print "ERROR: More than 255 values!"

f = open("../names.txt", "rt")
lines = f.readlines()
f.close()

names = []
origins = {}
chars = {}
drops = {}

prev = ""
i = 1
for it in lines:
    l = it.strip().split("\t")
    if len(l) != 3:
        raise ("invalid line %d: not 3 fields" % i)

    if len(l[0]) < 2:
        raise ("invalid line %d: name is shorter than 2 bytes" % i)

    if prev >= l[0]:
        raise ("invalid line %d: name doesn't sort after previous" % i)

    if len(l[1]) < 3:
        raise ("invalid line %d: origin is shorter than 3 bytes" % i)

    if l[2] not in ("F", "M"):
        raise ("invalid line %d: invalid gender '%s'" % (i, l[2]))

    mc = matchingChars(prev, l[0])
    dropCnt = len(prev) - mc
    appendix = l[0][mc:]

    names.append(name(dropCnt, appendix, l[1], l[2] == "M"))
    
    addFreq(origins, l[1])
    addFreq(drops, dropCnt)

    for c in appendix:
        addFreq(chars, c)

    # end-of-name marker is coded as an empty string
    addFreq(chars, "")

    prev = l[0]
    i += 1

    if (i % 50000) == 0:
        print "processed %d lines..." % i

for i in origins.values():
    for c in i.val:
        addFreq(chars, c)

    addFreq(chars, "")

huffman.huffmanize(chars)
huffman.huffmanize(origins)
huffman.huffmanize(drops)

cnt = 1
output = []

output.append(encodeTree(drops, False))
output.append(encodeTree(chars, True))
output.append(encodeTree(origins, False, chars))

for i in names:
    tmp = ""

    tmp += drops[i.dropCnt].code
    
    for c in i.appendix:
        tmp += chars[c].code
    tmp += chars[""].code
    
    tmp += origins[i.origin].code

    if i.isMale:
        tmp += "1"
    else:
        tmp += "0"

    output.append(tmp)
    if (cnt % 50000) == 0:
        print "outputted %d lines..." % cnt

    cnt += 1

output.append(drops[0].code)
output.append(chars[""].code)

outputStr = string.join(output, "")

# pad it to an even byte
while (len(outputStr) % 16) != 0:
    outputStr += "1"

outputBinary("../names.dat", outputStr)

printStats(drops, "Drops:")
printStats(origins, "Origins:")
printStats(chars, "Chars:")

print "%d names coded in %.4f bytes per name" % (len(names),
    len(outputStr) / (len(names) * 8.0))
