#!/usr/bin/env python
# ut:ignore

# FIXME: handle KeyboardInterrupt so testing can be aborted

import glob
import optparse
import os
import re
import sys
import time
import traceback
import types

VERSION = 0.1

def main():
    parser = optparse.OptionParser(version = "%%prog %s" % VERSION)
    parser.add_option("--file", dest="file", help="FILE to test")
    parser.add_option("--function", dest="func", help="FUNCTION to test")
    parser.add_option("--file-at-a-time", action="store_true", dest="faat",
        default = False, help="run tests from each file in the same"
        " process (faster, but coarser if tests fail)")

    (opts, args) = parser.parse_args()

    if opts.file:
        return doTest(opts)
    else:
        return doTests(opts)

# returns a list of all function names from the given file that start with
# "test".
def getTestFuncs(filename):
    funcs = {}

    f = open(filename, "r")

    for line in f:
        mo = re.match("def (test[a-zA-Z0-9_]*)\(", line)

        if mo:
            name = mo.group(1)

            if name in funcs:
                sys.exit("Error: Function '%s' defined twice." % name)

            funcs[name] = None

    return list(funcs)

# read lines from file 'filename' until one starting with not '#' is
# found, looking for strings matching 'ut:key=val', and storing the
# results in a dictionary which is returned. a missing '=val' part is
# indicated by None as the key's value.
def getFlags(filename):
    fp = open(filename, "r")

    ret = {}
    while 1:
        s = fp.readline()
        if not s or (s[0] != "#"):
            break

        # FIXME: very lame, make this actually work as the documentation
        # says.

        if s.find("ut:ignore") != -1:
            ret["ignore"] = None

    fp.close()

    return ret

# run tests from a single file, either all of them or a specific one.
def doTest(opts):
    # FIXME
    sys.path.insert(0, "../src")

    # strip .py suffix
    name = opts.file[0:-3]

    exec("import %s" % name)

    mod = eval("%s" % name)
    attr = dir(mod)

    if "init" in attr:
        mod.init()

    if opts.faat:
        funcs = getTestFuncs(opts.file)
    else:
        funcs = [opts.func]

    if not funcs:
        print "[--- No tests found in %s ---]" % name
        sys.exit(1)

    for f in funcs:
        print "[Testing %s:%s]" % (name, f)
        getattr(mod, f)()

    return 0

# run all tests
def doTests(opts):
    # FIXME
    sys.path.insert(0, "../src")

    # total number of tests (files)
    cntTotal = 0

    # number of tests (files) that failed
    cntFailed = 0

    t = time.time()

    # FIXME: allow specifying which files to test

    fnames = sorted(glob.glob("*.py"))

    for fname in fnames:
        flags = getFlags(fname)

        if flags.has_key("ignore"):
            continue

        # strip .py suffix
        name = fname[0:-3]

        if opts.faat:
            # FIXME
            ret = os.system("./do_tests.py --file %s --file-at-a-time" % (
                fname))

            cntTotal += 1
            if ret != 0:
                cntFailed += 1
        else:
            funcs = getTestFuncs(fname)

            if not funcs:
                print "[--- No tests found in %s ---]" % name
                cntTotal += 1
                cntFailed += 1

            for f in funcs:
                # FIXME
                ret = os.system("./do_tests.py --file %s --function %s" % (
                    fname, f))

                cntTotal += 1
                if ret != 0:
                    cntFailed += 1

    t = time.time() - t

    if opts.faat:
        s = "files"
    else:
        s = "tests"

    print "Tested %d %s, out of which %d failed, in %.2f seconds" % (
        cntTotal, s, cntFailed, t)

    return 0 if (cntFailed == 0) else 1

sys.exit(main())
