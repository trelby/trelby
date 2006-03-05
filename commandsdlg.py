import misc
import util

import xml.sax.saxutils as xss
from wxPython.wx import *
from wxPython.html import *

class CommandsDlg(wxFrame):
    def __init__(self, cfgGl):
        wxFrame.__init__(self, None, -1, "Commands",
                         size = (650, 600), style = wxDEFAULT_FRAME_STYLE)

        self.Center()
        
        vsizer = wxBoxSizer(wxVERTICAL)
        self.SetSizer(vsizer)

        s = '<table border="1"><tr><td><b>Key(s)</b></td>'\
            '<td><b>Command</b></td></tr>'

        for cmd in cfgGl.commands:
            s += '<tr><td bgcolor="#dddddd" valign="top">'

            if cmd.keys:
                for key in cmd.keys:
                    k = util.Key.fromInt(key)
                    s += "%s<br>" % xss.escape(k.toStr())
            else:
                s += "No key defined<br>"

            s += '</td><td valign="top">'
            s += "%s" % xss.escape(cmd.desc)
            s += "</td></tr>"

        s += "</table>"
        
        self.html = """
<html><head></head><body>

%s

<pre>
<b>Mouse:</b>

Left click             Position cursor
Left click + drag      Select text
Right click            Unselect

<b>Keyboard shortcuts in Find/Replace dialog:</b>

F                      Find
R                      Replace
</pre>
</body></html>
        """ % s
        
        htmlWin = wxHtmlWindow(self)
        rep = htmlWin.GetInternalRepresentation()
        rep.SetIndent(0, wxHTML_INDENT_BOTTOM)
        htmlWin.SetPage(self.html)
        htmlWin.SetFocus()
        
        vsizer.Add(htmlWin, 1, wxEXPAND)

        id = wxNewId()
        menu = wxMenu()
        menu.Append(id, "&Save as...")

        mb = wxMenuBar()
        mb.Append(menu, "&File")
        self.SetMenuBar(mb)

        EVT_MENU(self, id, self.OnSave)

        self.Layout()

        EVT_CLOSE(self, self.OnCloseWindow)

    def OnCloseWindow(self, event):
        self.Destroy()

    def OnSave(self, event):
        dlg = wxFileDialog(self, "Filename to save as",
            wildcard = "HTML files (*.html)|*.html|All files|*",
            style = wxSAVE | wxOVERWRITE_PROMPT)

        if dlg.ShowModal() == wxID_OK:
            util.writeToFile(misc.fromGUIUnicode(dlg.GetPath()), self.html,
                             self)
            
        dlg.Destroy()
