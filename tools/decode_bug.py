#!/usr/bin/env python

import sys

lines = sys.stdin.readlines()

if len(lines) < 4:
    sys.exit("too little lines, #1")

for i in range(len(lines)):
    lines[i] = lines[i].strip()

start = lines.index("---start info---")
end = lines.index("---end info---")

if (end - start) < 3:
    sys.exit("too little lines, #2")

format, hasLicense = lines[start + 1].split()
format = int(format)
hasLicense = int(hasLicense)

if hasLicense:
    start2 = start + 11
else:
    start2 = start + 2

if start2 >= end:
    sys.exit("too little lines #3")

data = ("".join(lines[start2:end]))
data = str(data.decode("rot13"))
data = str(data.decode("base64"))

print data
