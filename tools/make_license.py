#!/usr/bin/env python

# ** NOTICE ***
#
# this is mostly copied from Blyte itself, with the secret parts included
# (private exponent mainly, toStr) and wxWidgets stuff removed.

import datetime
import sha
import sys

class BlyteError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

# handles license stuff. format of license string:
#
# byte 0: version. 1 for beta testing, 2 for 1.0.
#
# byte 1: type, one of the values from below.
#
# bytes 2-3: last valid upgrade date, coded as number of days from
# 2000-01-01 in MSB.
#
# bytes 4-63: user id (60 bytes), padded with spaces at the start, and of
# the form <spaces> + "John Doe <john.doe@foo.net>"
#
# bytes 64-???: RSA signature of the SHA-1 hash of bytes 0-63, using our
# keys
class License:

    # license types
    STANDARD = 1
    PRODUCTION = 2

    # public exponent
    pubExp = 65537

    # -DONT_INCLUDE-: DON'T INCLUDE THIS IN BLYTE
    # private exponent
    privExp = 18951405765053248602073705735786577941169720505557014329656789810081545470162793395270215001219530221259417538812864521247085842880636830063534551354482142054070397217196441312232990448529060552018310552792021720547582816672694576443931079228758633547960312335663258504933460434940508462845471547594108238897462044130611993656059021426786407952941330023008941584273778105708184497768841625051600572316057743286093420271139862076443685618168682085015129486221024404971460083250788129734979593518331976489175054888500445499636822529451131583663617959698790741355445585619263759213260875531276017270412908449137390857293L

    # public modulus
    pubMod = 29254935334455182042965597757772817301388292845900130682433565746868784488942621381364364162876559936654774402100546511105176419382129217568575288944027703304619282120442896579432657991408527650397456570447078730409302439200998338391377014236607103211227770334291908435704256189487601062996199948526088132202037509875714366181479780973317439978377800228612195110775627486438461629432119946045079582937393673482668070579676014424061995584470961990760405006986126005760445352618843826128863015510277694523358487180922871886359268019390165724063513636205071546516271852479359572341580343117229752020268293334064287174153L

    def __init__(self, type, lastDate, userId):
        # license type
        self.type = type

        # datetime.date object for last date this license applies to
        self.lastDate = lastDate

        # user identification
        self.userId = userId

    # try to construct new License from given string, using frame as
    # parent for error message boxes. returns None on failure.
    def fromStr(s, frame):
        if len(s) < 65:
            raise BlyteError("too short")

        # the 32 is for safety as I'm not entirely sure whether the
        # signature can grow over 256 bytes or not. if we don't have
        # this check, the program tries to calculate rsa signature for
        # whatever multi-megabyte file the user is trying to open,
        # which would take $BIGNUM time.
        if len(s) > (64 + 256 + 32):
            raise BlyteError("too long")

        dig = sha.new(s[:64]).digest()
        d = decrypt(s[64:], License.pubExp, License.pubMod)

        if d != dig:
            raise BlyteError("corrupt data")

        if ord(s[0]) != 1:
            raise BlyteError("incorrect version")

        t = ord(s[1])
        if t not in (License.STANDARD, License.PRODUCTION):
            raise BlyteError("incorrect type")

        ld = datetime.date(2000, 1, 1) + datetime.timedelta(days =
            (ord(s[2]) << 8) | ord(s[3]))

        uid = s[4:64]

        return License(t, ld, uid)

    fromStr = staticmethod(fromStr)

    # -DONT_INCLUDE-: DON'T INCLUDE THIS IN BLYTE
    def toStr(self):
        s = chr(0x01) + chr(self.type)
        td = self.lastDate - datetime.date(2000, 1, 1)
        s += chr((td.days >> 8) & 0xFF) + chr(td.days & 0xFF)

        assert len(self.userId) == 60
        s += self.userId
        
        dig = sha.new(s[:64]).digest()
        signature = encrypt(dig, License.privExp, License.pubMod)
        assert decrypt(signature, License.pubExp, License.pubMod) == dig
        s += signature

        return s

    def getTypeStr(self):
        if self.type == License.STANDARD:
            return "Standard"
        elif self.type == License.PRODUCTION:
            return "Production"
        else:
            return "Unknown"

# do RSA algorithm to s, which is a string, with modulo n and exponent e,
# and return the resulting string. s must not start with byte 0x00.
def crypt(s, e, n):
    m = 0
    for i in range(len(s)):
        m = (m << 8L) + ord(s[i])

    res = pow(m, e, n)

    s2 = ""
    while res != 0:
        s2 += chr(res & 0xFF)
        res >>= 8

    # reverses the string
    return s2[::-1]

# -DONT_INCLUDE-: DON'T INCLUDE THIS IN BLYTE
# we need to add a non-0x00 byte to the beginning to avoid various
# problems with representing binary data as a large number. so encrypt
# adds it and decrypt takes it out.
def encrypt(s, e, n):
    return crypt(chr(0x42) + s, e, n)

# reverse of encrypt (see tools/make_license.py), takes out the extra byte
# from the result.
def decrypt(s, e, n):
    return crypt(s, e, n)[1:]

def main():
    assert len(sys.argv) == 5

    a = sys.argv
    fib = License(License.STANDARD, datetime.date(int(a[1]), int(a[2]),
        int(a[3])), a[4].rjust(60))
    
    s = fib.toStr()
    sys.stdout.write(s)

if __name__ == "__main__":
    main()
