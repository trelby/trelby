import struct
unpack = struct.unpack

OFFSET_TABLE_SIZE = 12
TABLE_DIR_SIZE = 16
NAME_TABLE_SIZE = 6
NAME_RECORD_SIZE = 12

class ParseError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

def check(val):
    if not val:
        raise ParseError("")

# a parser for TrueType/OpenType fonts.
# http://www.microsoft.com/typography/otspec/default.htm contained the
# spec at the time of the writing.
class Font:

    # load font from string s, which is the whole contents of a font file
    def __init__(self, s):
        # is this a valid font
        self.ok = False

        # parse functions for tables, and a flag for whether each has been
        # parsed successfully
        self.parseFuncs = {
            "head" : [self.parseHead, False],
            "name" : [self.parseName, False],
            "OS/2" : [self.parseOS2, False]
            }

        try:
            self.parse(s)
        except (struct.error, ParseError) as e:
            self.error = e

            return

        self.ok = True

    # check if font was parsed correctly. none of the other
    # (user-oriented) functions can be called if this returns False.
    def isOK(self):
        return self.ok

    # get font's Postscript name.
    def getPostscriptName(self):
        return self.psName

    # returns True if font allows embedding.
    def allowsEmbedding(self):
        return self.embeddingOK

    # parse whole file
    def parse(self, s):
        version, self.tableCnt = unpack(">LH", s[:6])

        check(version == 0x00010000)

        offset = OFFSET_TABLE_SIZE

        for i in range(self.tableCnt):
            self.parseTag(offset, s)
            offset += TABLE_DIR_SIZE

        for name, func in self.parseFuncs.items():
            if not func[1]:
                raise ParseError("Table %s missing/invalid" % name)

    # parse a single tag
    def parseTag(self, offset, s):
        tag, checkSum, tagOffset, length = unpack(">4s3L",
            s[offset : offset + TABLE_DIR_SIZE])

        check(tagOffset >= (OFFSET_TABLE_SIZE +
                            self.tableCnt * TABLE_DIR_SIZE))

        func = self.parseFuncs.get(tag)
        if func:
            func[0](s[tagOffset : tagOffset + length])
            func[1] = True

    # parse head table
    def parseHead(self, s):
        magic = unpack(">L", s[12:16])[0]

        check(magic == 0x5F0F3CF5)

    # parse name table
    def parseName(self, s):
        fmt, nameCnt, storageOffset = unpack(">3H", s[:NAME_TABLE_SIZE])

        check(fmt == 0)

        storage = s[storageOffset:]
        offset = NAME_TABLE_SIZE

        for i in range(nameCnt):
            if self.parseNameRecord(s[offset : offset + NAME_RECORD_SIZE],
                                    storage):
                return

            offset += NAME_RECORD_SIZE

        raise ParseError("No Postscript name found")

    # parse a single name record. s2 is string storage. returns True if
    # this record is a valid Postscript name.
    def parseNameRecord(self, s, s2):
        platformID, encodingID, langID, nameID, strLen, strOffset = \
                    unpack(">6H", s)

        if nameID != 6:
            return False

        if (platformID == 1) and (encodingID == 0) and (langID == 0):
            # Macintosh, 1-byte strings

            self.psName = unpack("%ds" % strLen,
                                 s2[strOffset : strOffset + strLen])[0]

            return True

        elif (platformID == 3) and (encodingID == 1) and (langID == 0x409):
            # Windows, UTF-16BE

            tmp = unpack("%ds" % strLen,
                                 s2[strOffset : strOffset + strLen])[0]

            self.psName = tmp.decode("UTF-16BE", "ignore").encode(
                "ISO-8859-1", "ignore")

            return True

        return False

    def parseOS2(self, s):
        fsType = unpack(">H", s[8:10])[0]

        # the font embedding bits are a mess, the meanings have changed
        # over time in the TrueType/OpenType specs. this is the least
        # restrictive interpretation common to them all.
        self.embeddingOK = (fsType & 0xF) != 2
