#!/usr/bin/env python

#import sys

class myimport:
    def find_module(fullname, path = None):
        print "find_module: %s / %s" % (fullname, path)

        return None

    find_module = staticmethod(find_module)

# disabled for now, enable when resuming experiments with custom
# code-archives
#sys.meta_path.append(myimport())

# import main

# main.main()
