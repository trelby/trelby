import sys

# TODO: Python, at least up to 2.4, does not support Unicode command line
# arguments on Windows. Since UNIXes use UTF-8, just assume all command
# line arguments are UTF-8 for now, and silently ignore any coding errors
# that may result on Windows in some cases.
def init():
    global isTest, conf, filenames

    # script filenames to load
    filenames = []

    # name of config file to use, or None
    conf = None

    # are we in test mode
    isTest = False

    i = 1
    while i < len(sys.argv):
        arg = str(sys.argv[i])

        if arg == "--test":
            isTest = True
        elif arg == "--conf":
            if (i + 1) < len(sys.argv):
                conf = str(sys.argv[i + 1], "UTF-8", "ignore")
                i += 1
        else:
            filenames.append(arg)

        i += 1
