#!/usr/bin/env python

import sys

data = sys.stdin.read()
data = str(data.decode("rot13"))
data = str(data.decode("base64"))

print data
