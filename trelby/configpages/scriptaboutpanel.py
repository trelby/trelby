from trelby.configpages.aboutpanel import AboutPanel


class ScriptAboutPanel(AboutPanel):
    def __init__(self, parent, id, cfg):
        s = _(
            """This is the config dialog for script format settings, which means
things that affect the generated PDF output of a script. Things like
paper size, indendation/line widths/font styles for the different
element types, and so on.

The settings here are saved within the screenplay itself.

If you're looking for the user interface settings (colors, keyboard
shortcuts, etc.), those are found in File/Settings."""
        )

        AboutPanel.__init__(self, parent, id, cfg, s)
