import os
import gettext

import trelby


def trelby_translations_load():
    """load translations"""
    LOCALEDIR = os.path.dirname(trelby.__file__) + "/locales"
    LANGUAGE = os.environ["LANG"]

    if not os.path.isdir(LOCALEDIR + "/" + LANGUAGE):
        LANGUAGE = "en"

    TRANS = gettext.translation("trelby", localedir=LOCALEDIR, languages=[LANGUAGE])
    TRANS.install()

    return TRANS.gettext
