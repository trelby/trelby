from wxPython.wx import *
from wxPython.html import *

class CommandsDlg(wxDialog):
    def __init__(self, parent):
        wxDialog.__init__(self, parent, -1, "Commands",
                          pos = wxDefaultPosition,
                          size = (550, 600),
                          style = wxDEFAULT_DIALOG_STYLE)

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        html = """
<html></head><body>
<pre>
<b>Mouse:</b>

Left click             Position cursor
Left click + drag      Select area
Right click            Unselect

<b>Keyboard:</b>

Left/Right/Up/Down     Move
Home/End               Move to start/end of line
Page up / Page down    Move one page up/down
CTRL + Home/End        Move to start/end of script

Backspace              Delete previous character
Delete                 Delete current character

ENTER                  Insert new element

TAB                    Change element to next style
SHIFT + TAB            Change element to previous style

SHIFT/CTRL + ENTER     Insert forced linebreak

CTRL + SPACE           Set mark
ESCAPE                 Unselect

Alt + S                Change element to scene heading
Alt + A                Change element to action
Alt + C                Change element to character
Alt + P                Change element to parenthetical
Alt + D                Change element to dialogue
Alt + T                Change element to transition

<b>Menu shortcuts:</b>

CTRL + O               Open file
CTRL + S               Save file

CTRL + X               Cut
CTRL + C               Copy
CTRL + V               Paste

CTRL + Q               Quit program
</pre>
</body></html>
        """
        
        htmlWin = wxHtmlWindow(self)
        rep = htmlWin.GetInternalRepresentation()
        rep.SetIndent(0, wxHTML_INDENT_BOTTOM)
        htmlWin.SetPage(html)
        htmlWin.SetFocus()
        
        vsizer.Add(htmlWin, 1, wxEXPAND)
        
        self.Layout()

        EVT_CLOSE(self, self.OnCloseWindow)

    def OnCloseWindow(self, event):
        self.Destroy()
