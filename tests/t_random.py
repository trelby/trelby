# ut:ignore

# FIXME
import sys
sys.path.insert(0, "..")

import u

import random

# runs random operations on a screenplay as a way of trying to
# automatically find bugs. note that this is not part of the normal test
# run, this has to be run manually.

def main():
    funcs = [
        "moveLeft",
        "moveRight",
        "moveUp",
        "moveDown",
        "moveLineEnd",
        "moveLineStart",
        "moveStart",
        "moveEnd",
        "moveSceneUp",
        "moveSceneDown",
        "deleteBackward",
        "deleteForward",
        "abort",
        "selectScene",
        "insertForcedLineBreak",
        "splitElement",
        "setMark",
        "tab",
        "toPrevTypeTab",
        "addChar",
        "toScene",
        "toAction",
        "toCharacter",
        "toDialogue",
        "toParen",
        "toTransition",
        "toShot",
        "toNote"
        ]

    #import datetime
    cnt = 0
    while True:
        print "Count %d" % cnt
        rounds = max(1, int(random.gauss(15000, 4000)))
        #rounds = max(1, int(random.gauss(15, 5)))
        
        ops = []
        failed = False
        
        # every 10th time, test operations on an empty script
        if (cnt % 10) == 0:
            sp = u.new()
            ops.append("NEW")
        else:
            sp = u.load()
            ops.append("LOAD")

        #print datetime.datetime.today()
        for i in xrange(rounds):
            cmdName = funcs[random.randint(0, len(funcs) - 1)]

            if cmdName == "addChar":
                char = chr(random.randint(0, 255))
            else:
                char = None

    #         if char:
    #             print "%s (%d)" % (cmdName, ord(char))
    #         else:
    #             print "%s" % cmdName

            ops.append((cmdName, char))
            sp.cmd(cmdName, char)

            try:
                sp._validate()
            except KeyboardInterrupt:
                raise
            except:
                save(cnt, sp.save(), ops)
                failed = True
                
                break

        if not failed:
            s = sp.save()

            try:
                u.loadString(s)
            except:
                save(cnt, s, ops)

        cnt += 1

# save information about round 'cnt' to files so it can be analyzed. s is
# the result from Screenplay.save(), ops is a list of operations.
def save(cnt, s, ops):
    filename = "%d.blyte" % cnt
    print "Saving failed script to %s" % filename
    f = open(filename, "w")
    f.write(s)
    f.close()

    f = open("%d.ops" % cnt, "w")
    f.write(str(ops))
    f.close()
    
main()
