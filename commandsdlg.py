from wxPython.wx import *
from wxPython.html import *

class CommandsDlg(wxDialog):
    def __init__(self, parent):
        wxDialog.__init__(self, parent, -1, "Commands",
                          pos = wxDefaultPosition,
                          size = (650, 600),
                          style = wxDEFAULT_DIALOG_STYLE | wxRESIZE_BORDER)

        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        html = """
<html></head><body>
<pre>
<b>Mouse:</b>

Left click             Position cursor
Left click + drag      Select text
Right click            Unselect

<b>Keyboard commands:</b>

<b>Editing:</b>
 
Left/Right/Up/Down     Move
Home/End               Move to start/end of line
CTRL + Up/Down         Move one scene up/down
Page up / Page down    Move one page up/down
CTRL + Home/End        Move to start/end of script

Backspace              Delete previous character
Delete                 Delete current character

ENTER                  Insert new element

TAB                    Change element to next style
SHIFT + TAB            Change element to previous style

SHIFT/CTRL + ENTER     Insert forced linebreak

CTRL + SPACE           Start selection
CTRL + A               Select current scene
ESCAPE                 Unselect

CTRL + F               Find / Replace

<b>In Find/Replace dialog:</b>

F                      Find
R                      Replace

<b>During Auto-Completion:</b>

Up/Down/Page up/       Move selection
 Page down            
Enter                  Complete selection, start new element
End                    Complete selection
ESCAPE                 Abort auto-completion

<b>Commands:</b>

CTRL + E               Find next error in screenplay

Alt + S                Change element to scene heading
Alt + A                Change element to action
Alt + C                Change element to character
Alt + P                Change element to parenthetical
Alt + D                Change element to dialogue
Alt + T                Change element to transition
Alt + N                Change element to note

CTRL + O               Open file
CTRL + S               Save file

CTRL + X / Delete      Cut
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
