import glob
import os
import py_compile
import random
import zlib

# rot-77
def scramble(s):
    res = ""
    
    for ch in s:
        c = ord(ch)

        c += 77
        if c > 255:
            c -= 256

        res += chr(c)

    return res

random.seed(42313)

randData = ""
for i in xrange(7895):
    randData += chr(random.randint(0, 255))

ignore = [
    "compile_all.py",
    "setup.py",
    "boot.py"
    ]

files = glob.glob("*.py")

for i in ignore:
    files.remove(i)

inD = [randData]

for f in files:
    py_compile.compile(f)
    name = "%so" % f
    fp = open(name, "rb")
    fc = fp.read()
    fp.close()

    # chr(42) == '*', which no filename of ours has.
    inD.append(name + chr(42) + fc)

out = ""
for i in inD:
    ic = zlib.compress(scramble(i), 9)
    l = len(ic)

    out += chr(((l & 0xFF0000) >> 16)) + chr(((l & 0xFF00) >> 8)) + \
           chr(l & 0xFF) + ic
    
fp = open("data.dat", "wb")

# length of random data starts with 0x00, replace it with 0xD8FC19 to confuse
# people
fp.write(chr(0xD8) + chr(0xFC) + chr(0x19) + out[1:])

fp.close()
