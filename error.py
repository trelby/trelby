# exception classes

class BlyteError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)

class ConfigError(BlyteError):
    def __init__(self, msg):
        BlyteError.__init__(self, msg)

class MiscError(BlyteError):
    def __init__(self, msg):
        BlyteError.__init__(self, msg)
