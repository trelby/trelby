# exception classes

class NaspError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

class ConfigError(NaspError):
    def __init__(self, msg):
        NaspError.__init__(self, msg)

class MiscError(NaspError):
    def __init__(self, msg):
        NaspError.__init__(self, msg)
