#!/usr/bin/env python
# add words to ../words_en.dat in the correct place

import sys

if len(sys.argv) < 2:
    raise "add_word.py word1 word2..."

sys.path.insert(0, "..")

import util
util.init(False)

s = util.loadFile("../words_en.dat", None)
if s == None:
    raise "error"

words = {}
lines = s.splitlines()

for it in lines:
    words[util.lower(it)] = None

for arg in sys.argv[1:]:
    words[util.lower(arg)] = None

words = words.keys()
words.sort()

f = open("../words_en.dat", "wb")
for w in words:
    f.write("%s\n" % w)

f.close()
