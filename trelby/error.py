# exception classes


class TrelbyError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg

    def __str__(self):
        return str(self.msg)


class ConfigError(TrelbyError):
    def __init__(self, msg):
        TrelbyError.__init__(self, msg)


class MiscError(TrelbyError):
    def __init__(self, msg):
        TrelbyError.__init__(self, msg)
