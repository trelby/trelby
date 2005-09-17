import sys

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
        arg = sys.argv[i]

        if arg == "--test":
            isTest = True
        elif arg == "--conf":
            if (i + 1) < len(sys.argv):
                conf = sys.argv[i + 1]
                i += 1
        else:
            filenames.append(arg)

        i += 1
