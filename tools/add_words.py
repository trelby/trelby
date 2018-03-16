#!/usr/bin/env python
# add words to ../dict_en.dat in the correct place

import sys

if len(sys.argv) < 2:
    raise Exception("add_word.py word1 word2...")

sys.path.insert(0, "../src")

import misc
import util

util.init(False)
misc.init(False)

s = util.loadFile("../dict_en.dat", None)
if s == None:
    raise Exception("error")

words = {}
lines = s.splitlines()

for it in lines:
    words[util.lower(it)] = None

for arg in sys.argv[1:]:
    words[util.lower(arg)] = None

words = list(words.keys())
words.sort()

f = open("../dict_en.dat", "wb")
for w in words:
    f.write("%s\n" % w)

f.close()
