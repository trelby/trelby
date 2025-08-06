from trelby.configpages.aboutpanel import AboutPanel


class GlobalAboutPanel(AboutPanel):
    def __init__(self, parent, id, cfg):
        s = _(
            """This is the config dialog for global settings, which means things
that affect the user interface of the program like interface colors,
keyboard shortcuts, display fonts, and so on.

The settings here are independent of any script being worked on,
and unique to this computer.

None of the settings here have any effect on the generated PDF
output for a script. See Script/Settings for those."""
        )

        AboutPanel.__init__(self, parent, id, cfg, s)
