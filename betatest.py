import random
import sys
import urllib

import util

from wxPython.wx import *

# check whether beta-test period is over, and if so, exit the program.
def check():
    err = ""

    try:
        v = random.randint(467324, 2000000000)

        params = urllib.urlencode({"v": v})
        sock = urllib.urlopen("http://www.oskusoft.com/cgi/betatest.cgi",
                              params)
        s = sock.readline()
        sock.close()

        resp = util.str2int(s, 0)

        if resp == -42:
            err = "Beta-test period for this program version is over."
        else:
            # 13 prime numbers (dunno if the primeness really matters..)
            arr = [4049, 2399, 1753, 5503, 223, 2713, 6551, 701, 2477, 3701,
                   2687, 1223, 7321]

            res = v % 89
            while v > 0:
                res += arr[v % 13]
                v = int(v/13)

            if resp != res:
                err = "Invalid response from beta test server."
            
    except IOError, (errno, strerror):
        err = "Error connecting to beta test server: %s" % strerror

    if err:
        wxMessageBox(err, "Error", wxOK)
        sys.exit()
