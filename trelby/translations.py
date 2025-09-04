"""Translation related functions"""

import os
import gettext
import re

import trelby


def trelby_translations_load():
    """load translations"""
    localedir = os.path.dirname(trelby.__file__) + "/locales"
    if "LANG" in os.environ:
        language = os.environ["LANG"]
    else:
        language = "en"

    if not os.path.isdir(localedir + "/" + language):
        base_language = re.split("[^a-zA-Z]", language)[0]
        if os.path.isdir(localedir + "/" + base_language):
            language = base_language
        else:
            language = "en"

    trans = gettext.translation("trelby", localedir=localedir, languages=[language])
    trans.install()

    return trans.gettext
