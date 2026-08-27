# -*- coding: iso-8859-1 -*-

import copy
import os
import os.path
import signal
import webbrowser
from functools import partial

import wx
import wx.svg

import trelby
import trelby.charmapdlg as charmapdlg
import trelby.commandsdlg as commandsdlg
import trelby.config as config
import trelby.misc as misc
import trelby.namesdlg as namesdlg
import trelby.spellcheckcfgdlg as spellcheckcfgdlg
import trelby.splash as splash
import trelby.util as util
from trelby.ids import *
from trelby.trelbypanel import MyPanel


def to_mnemonics(mnemonic, menu_text):
    """Set the given keyboard mnemonic for the given menu item text.

    Menu text must be already translated and can include a keyboard shortcut.

    This is useful for maintaining keyboard mnemonics across translations
    and to not pollute translation files with ampersands.

    NOTE: macOS and Gnome do not support keyboard mnemonics.

    Args:
        mnemonic: character of the keyboard mnemonic.
        menu_text: text of the menu item --without the mnemonic.

    Returns:
        Translated menu text with the mnemonic.
        If the mnemonic character is not in the translated menu text,
        appends it at the end of the menu command text.

    """
    mnemonic = mnemonic.strip()[0].casefold()
    text, separator, shortcut = menu_text.partition('\t')

    if mnemonic in text.casefold():
        method = str.lower
        if mnemonic.upper() in text:
            method = str.upper
        text = text.replace(method(mnemonic), f'&{method(mnemonic)}', 1)
    else:
        text = f'{text} (&{mnemonic.upper()})'

    return ''.join([text, separator, shortcut])


class MyFrame(wx.Frame):

    def __init__(self, parent, id, title, gd, myApp):
        wx.Frame.__init__(self, parent, id, title, name="Trelby")

        if misc.isUnix:
            # automatically reaps zombies
            signal.signal(signal.SIGCHLD, signal.SIG_IGN)

        self.clipboard = None
        self.showFormatting = False
        self.gd = gd
        self.myApp = myApp

        self.SetSizeHints(gd.cvars.getMin("width"), gd.cvars.getMin("height"))

        self.Move(gd.posX, gd.posY)
        self.SetSize(wx.Size(gd.width, gd.height))

        util.removeTempFiles(misc.tmpPrefix)

        self.mySetIcons()
        # self.allocIds()

        menu_file = wx.Menu()
        menu_file.Append(
            ID_FILE_NEW, to_mnemonics('N', _("New") + "\tCTRL-N")
        )
        menu_file.Append(
            ID_FILE_OPEN, to_mnemonics('O', _("Open") + "...\tCTRL-O")
        )
        menu_file.Append(
            ID_FILE_SAVE, to_mnemonics('S', _("Save") + "\tCTRL-S")
        )
        menu_file.Append(
            ID_FILE_SAVE_AS, to_mnemonics('A', _("Save As") + "...")
        )
        menu_file.Append(
            ID_FILE_CLOSE, to_mnemonics('C', _("Close") + "\tCTRL-W")
        )
        menu_file.Append(
            ID_FILE_REVERT, to_mnemonics('R', _("Revert"))
        )
        menu_file.AppendSeparator()
        menu_file.Append(
            ID_FILE_IMPORT, to_mnemonics('I', _("Import") + "...")
        )
        menu_file.Append(
            ID_FILE_EXPORT, to_mnemonics('E', _("Export") + "...")
        )
        menu_file.AppendSeparator()
        menu_file.Append(
            ID_FILE_PRINT,
            to_mnemonics('P', _("Print to PDF") + "\tCTRL-P")
        )
        menu_file.AppendSeparator()

        menu_file_settings = wx.Menu()

        menu_file_settings.Append(
            ID_SETTINGS_CHANGE, to_mnemonics('C', _("Change") + "...")
        )
        menu_file_settings.AppendSeparator()
        menu_file_settings.Append(
            ID_SETTINGS_LOAD, _("Load") + "..."
        )
        menu_file_settings.Append(
            ID_SETTINGS_SAVE_AS, _("Save as") + "..."
        )
        menu_file_settings.AppendSeparator()
        menu_file_settings.Append(
            ID_SETTINGS_SC_DICT,
            to_mnemonics('S', _("Spell checker dictionary") + "...")
        )

        menu_file.Append(
            ID_FILE_SETTINGS,
            to_mnemonics('t', _("Settings")),
            menu_file_settings
        )

        menu_file.AppendSeparator()
        # "most recently used" list comes in here
        menu_file.AppendSeparator()

        menu_file.Append(
            ID_FILE_EXIT, to_mnemonics('x', _("Exit") + "\tCTRL-Q")
        )

        menu_edit = wx.Menu()
        menu_edit.Append(
            ID_EDIT_UNDO, to_mnemonics('U', _("Undo") + "\tCTRL-Z")
        )
        menu_edit.Append(
            ID_EDIT_REDO, to_mnemonics('R', _("Redo") + "\tCTRL-Y")
        )
        menu_edit.AppendSeparator()
        menu_edit.Append(
            ID_EDIT_CUT, to_mnemonics('t', _("Cut") + "\tCTRL-X")
        )
        menu_edit.Append(
            ID_EDIT_COPY, to_mnemonics('C', _("Copy") + "\tCTRL-C")
        )
        menu_edit.Append(
            ID_EDIT_PASTE, to_mnemonics('P', _("Paste") + "\tCTRL-V")
        )
        menu_edit.AppendSeparator()

        menu_edit_copy = wx.Menu()
        menu_edit_copy.Append(
            ID_EDIT_COPY_TO_CB, to_mnemonics('U', _("Unformatted"))
        )
        menu_edit_copy.Append(
            ID_EDIT_COPY_TO_CB_FMT, to_mnemonics('F', _("Formatted"))
        )

        menu_edit.Append(
            ID_EDIT_COPY_SYSTEM,
            to_mnemonics('o', _("Copy (system)")),
            menu_edit_copy
        )
        menu_edit.Append(
            ID_EDIT_PASTE_FROM_CB, to_mnemonics('a', _("Paste (system)"))
        )
        menu_edit.AppendSeparator()
        menu_edit.Append(
            ID_EDIT_SELECT_SCENE, to_mnemonics('S', _("Select scene"))
        )
        menu_edit.Append(
            ID_EDIT_SELECT_ALL, to_mnemonics('l', _("Select all"))
        )
        menu_edit.Append(
            ID_EDIT_GOTO_PAGE,
            to_mnemonics('G', _("Goto page") + "...\tCTRL-G")
        )
        menu_edit.Append(
            ID_EDIT_GOTO_SCENE,
            to_mnemonics('e', _("Goto scene") + "...\tALT-G")
        )
        menu_edit.AppendSeparator()
        menu_edit.Append(
            ID_EDIT_INSERT_NBSP, _("Insert non-breaking space")
        )
        menu_edit.AppendSeparator()
        menu_edit.Append(
            ID_EDIT_FIND,
            to_mnemonics('F', _("Find && Replace") + "...\tCTRL-F")
        )
        menu_edit.AppendSeparator()
        menu_edit.Append(
            ID_EDIT_DELETE_ELEMENTS,
            to_mnemonics('D', _("Delete elements") + "...")
        )

        menu_view = wx.Menu()
        menu_view.AppendRadioItem(
            ID_VIEW_STYLE_DRAFT, to_mnemonics('D', _("Draft"))
        )
        menu_view.AppendRadioItem(
            ID_VIEW_STYLE_LAYOUT, to_mnemonics('L', _("Layout"))
        )
        menu_view.AppendRadioItem(
            ID_VIEW_STYLE_SIDE_BY_SIDE, to_mnemonics('S', _("Side by side"))
        )
        menu_view.AppendCheckItem(
            ID_SHOW_HIDE_TOOLBAR, to_mnemonics('H', _("Show/Hide Toolbar"))
        )

        if gd.viewMode == gd.VIEWMODE_DRAFT:
            menu_view.Check(ID_VIEW_STYLE_DRAFT, True)
        elif gd.viewMode == gd.VIEWMODE_LAYOUT:
            menu_view.Check(ID_VIEW_STYLE_LAYOUT, True)
        else:
            menu_view.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)

        menu_view.AppendSeparator()
        menu_view.AppendCheckItem(
            ID_VIEW_SHOW_FORMATTING, to_mnemonics('f', _("Show formatting"))
        )
        menu_view.Append(
            ID_VIEW_FULL_SCREEN, to_mnemonics('u', _("Fullscreen") + "\tF11")
        )

        menu_script = wx.Menu()
        menu_script.Append(
            ID_SCRIPT_FIND_ERROR, to_mnemonics('F', _("Find next error"))
        )
        menu_script.Append(
            ID_SCRIPT_PAGINATE, to_mnemonics('P', _("Paginate"))
        )
        menu_script.AppendSeparator()
        menu_script.Append(
            ID_SCRIPT_AUTO_COMPLETION,
            to_mnemonics('A', _("Auto-completion") + "...")
        )
        menu_script.Append(
            ID_SCRIPT_HEADERS, to_mnemonics('H', _("Headers") + "...")
        )
        menu_script.Append(
            ID_SCRIPT_LOCATIONS, to_mnemonics('L', _("Locations") + "...")
        )
        menu_script.Append(
            ID_SCRIPT_TITLES, to_mnemonics('i', _("Title pages") + "...")
        )
        menu_script.Append(
            ID_SCRIPT_SC_DICT,
            to_mnemonics('S', _("Spell checker dictionary..."))
        )
        menu_script.AppendSeparator()

        menu_script_settings = wx.Menu()

        menu_script_settings.Append(
            ID_SCRIPT_SETTINGS_CHANGE, to_mnemonics('C', _("Change") + "...")
        )
        menu_script_settings.AppendSeparator()
        menu_script_settings.Append(
            ID_SCRIPT_SETTINGS_LOAD, to_mnemonics('L', _("Load") + "...")
        )
        menu_script_settings.Append(
            ID_SCRIPT_SETTINGS_SAVE_AS,
            to_mnemonics('S', _("Save as") + "...")
        )
        menu_script.Append(
            ID_SCRIPT_SETTINGS,
            to_mnemonics('t', _("Settings")),
            menu_script_settings
        )

        menu_reports = wx.Menu()
        menu_reports.Append(
            ID_REPORTS_SCRIPT_REP, to_mnemonics('r', _("Script report"))
        )
        menu_reports.Append(
            ID_REPORTS_LOCATION_REP,
            to_mnemonics('L', _("Location report") + "...")
        )
        menu_reports.Append(
            ID_REPORTS_SCENE_REP, to_mnemonics('S', _("Scene report") + "...")
        )
        menu_reports.Append(
            ID_REPORTS_CHARACTER_REP,
            to_mnemonics('C', _("Character report") + "...")
        )
        menu_reports.Append(
            ID_REPORTS_DIALOGUE_CHART,
            to_mnemonics('D', _("Dialogue chart") + "...")
        )

        menu_tools = wx.Menu()
        menu_tools.Append(
            ID_TOOLS_SPELL_CHECK,
            to_mnemonics('S', _("Spell checker") + "...")
        )
        menu_tools.Append(
            ID_TOOLS_NAME_DB, to_mnemonics('N', _("Name database") + "...")
        )
        menu_tools.Append(
            ID_TOOLS_CHARMAP, to_mnemonics('C', _("Character map") + "...")
        )
        menu_tools.Append(
            ID_TOOLS_COMPARE_SCRIPTS,
            to_mnemonics('o', _("Compare scripts") + "...")
        )
        menu_tools.Append(
            ID_TOOLS_WATERMARK,
            to_mnemonics('G', _("Generate watermarked PDFs") + "...")
        )

        menu_help = wx.Menu()
        menu_help.Append(
            ID_HELP_COMMANDS, to_mnemonics('C', _("Commands") + "...")
        )
        menu_help.Append(
            ID_HELP_MANUAL, to_mnemonics('M', _("Manual"))
        )
        menu_help.AppendSeparator()
        menu_help.Append(
            ID_HELP_ABOUT, to_mnemonics('A', _("About") + "...")
        )
        menu_help.Append(wx.ID_ABOUT, to_mnemonics('A', _("About") + "..."))

        self.menuBar = wx.MenuBar()
        self.menuBar.Append(menu_file, to_mnemonics('F', _("File")))
        self.menuBar.Append(menu_edit, to_mnemonics('E', _("Edit")))
        self.menuBar.Append(menu_view, to_mnemonics('V', _("View")))
        self.menuBar.Append(menu_script, to_mnemonics('S', _("Script")))
        self.menuBar.Append(menu_reports, to_mnemonics('R', _("Reports")))
        self.menuBar.Append(menu_tools, to_mnemonics('T', _("Tools")))
        self.menuBar.Append(menu_help, to_mnemonics('H', _("Help")))
        self.SetMenuBar(self.menuBar)

        self.toolBar = self.CreateToolBar(wx.TB_VERTICAL)
        self.toolBar.SetToolBitmapSize(self.FromDIP(wx.Size(32, 32)))

        def addTB(id, iconFilename, toolTip):
            filepath = misc.getFullPath(("trelby/resources/%s" % iconFilename))

            # neat hack to change the color of the SVG
            with open(filepath, "r") as svg_file:
                svg_content = svg_file.read()

            if wx.SystemSettings.GetAppearance().IsDark():
                svg_content = svg_content.replace(
                    "fill:#000000", "fill:#CCCCCC"
                )
            svg_content = svg_content.encode('utf-8')

            # svg_image = wx.svg.SVGimage.CreateFromBytes(svg_content)
            bitmap = wx.BitmapBundle.FromSVG(svg_content, wx.Size(32, 32))

            self.toolBar.AddTool(
                id,
                "",
                bitmap,
                shortHelp=toolTip,
            )

        addTB(ID_FILE_NEW, "new.svg", _("New script"))
        addTB(ID_FILE_OPEN, "open.svg", _("Open Script") + "...")
        addTB(ID_FILE_SAVE, "save.svg", _("Save") + "...")
        addTB(ID_FILE_SAVE_AS, "saveas.svg", _("Save as") + "...")
        addTB(ID_FILE_CLOSE, "close.svg", _("Close Script"))
        addTB(ID_TOOLBAR_SCRIPTSETTINGS, "scrset.svg", _("Script settings"))
        addTB(ID_FILE_PRINT, "pdf.svg", _("Print to PDF"))

        self.toolBar.AddSeparator()

        addTB(ID_FILE_IMPORT, "import.svg", _("Import a text script"))
        addTB(ID_FILE_EXPORT, "export.svg", _("Export script"))

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_UNDO, "undo.svg", _("Undo"))
        addTB(ID_EDIT_REDO, "redo.svg", _("Redo"))

        self.toolBar.AddSeparator()

        addTB(ID_EDIT_FIND, "find.svg", _("Find / Replace"))
        addTB(ID_TOOLBAR_VIEWS, "view.svg", _("View mode"))
        addTB(ID_TOOLBAR_REPORTS, "report.svg", _("Script reports"))
        addTB(ID_TOOLBAR_TOOLS, "tools.svg", _("Tools"))
        addTB(ID_TOOLBAR_SETTINGS, "settings.svg", _("Global settings"))

        self.toolBar.SetBackgroundColour(gd.cfgGui.tabBarBgColor)
        self.toolBar.Realize()

        self.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_SIZE, self.OnSize)

        vsizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(vsizer)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.noFSBtn = misc.MyFSButton(self, -1, self.getCfgGui)
        self.noFSBtn.SetToolTip(_("Exit fullscreen"))
        self.noFSBtn.Show(False)
        hsizer.Add(self.noFSBtn)

        self.Bind(wx.EVT_BUTTON, self.ToggleFullscreen, id=self.noFSBtn.GetId())

        self.tabCtrl = misc.MyTabCtrl(self, -1, self.getCfgGui)
        hsizer.Add(self.tabCtrl, 1, wx.EXPAND)

        self.statusCtrl = misc.MyStatus(self, -1, self.getCfgGui)
        hsizer.Add(self.statusCtrl)

        vsizer.Add(hsizer, 0, wx.EXPAND)

        tmp = misc.MyTabCtrl2(self, -1, self.tabCtrl)
        vsizer.Add(tmp, 1, wx.EXPAND)

        vsizer.Add(wx.StaticLine(self, -1), 0, wx.EXPAND)

        gd.mru.useMenu(menu_file, 14)

        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnMenuHighlight)

        self.tabCtrl.setPageChangedFunc(self.OnPageChange)

        # see OnRightDown
        self.rightClickMenu = wx.Menu()
        self.rightClickMenuWithCut = wx.Menu()

        for m in (self.rightClickMenu, self.rightClickMenuWithCut):
            tmp = wx.Menu()

            tmp.Append(
                ID_ELEM_TO_SCENE, to_mnemonics('S', _("Scene"))
            )
            tmp.Append(
                ID_ELEM_TO_ACTION, to_mnemonics('A', _("Action"))
            )
            tmp.Append(
                ID_ELEM_TO_CHARACTER, to_mnemonics('C', _("Character"))
            )
            tmp.Append(
                ID_ELEM_TO_PAREN, to_mnemonics('P', _("Parenthetical"))
            )
            tmp.Append(
                ID_ELEM_TO_DIALOGUE, to_mnemonics('D', _("Dialogue"))
            )
            tmp.Append(
                ID_ELEM_TO_TRANSITION, to_mnemonics('T', _("Transition"))
            )
            tmp.Append(
                ID_ELEM_TO_SHOT, to_mnemonics('o', _("Shot"))
            )
            tmp.Append(
                ID_ELEM_TO_ACTBREAK, to_mnemonics('b', _("Act break"))
            )
            tmp.Append(
                ID_ELEM_TO_NOTE, to_mnemonics('N', _("Note"))
            )

            m.AppendSubMenu(tmp, _("Element type"))
            m.AppendSeparator()

            if m is self.rightClickMenuWithCut:
                m.Append(ID_EDIT_CUT, _("Cut"))
                m.Append(ID_EDIT_COPY, _("Copy"))

            m.Append(ID_EDIT_PASTE, _("Paste"))

            self.Bind(wx.EVT_MENU, self.OnNewScript, id=ID_FILE_NEW)
            self.Bind(wx.EVT_MENU, self.OnOpen, id=ID_FILE_OPEN)
            self.Bind(wx.EVT_MENU, self.OnSave, id=ID_FILE_SAVE)
            self.Bind(wx.EVT_MENU, self.OnSaveScriptAs, id=ID_FILE_SAVE_AS)
            self.Bind(wx.EVT_MENU, self.OnImportScript, id=ID_FILE_IMPORT)
            self.Bind(wx.EVT_MENU, self.OnExportScript, id=ID_FILE_EXPORT)
            self.Bind(wx.EVT_MENU, self.OnCloseScript, id=ID_FILE_CLOSE)
            self.Bind(wx.EVT_MENU, self.OnRevertScript, id=ID_FILE_REVERT)
            self.Bind(wx.EVT_MENU, self.OnPrint, id=ID_FILE_PRINT)
            self.Bind(wx.EVT_MENU, self.OnSettings, id=ID_SETTINGS_CHANGE)
            self.Bind(wx.EVT_MENU, self.OnLoadSettings, id=ID_SETTINGS_LOAD)
            self.Bind(wx.EVT_MENU, self.OnSaveSettingsAs, id=ID_SETTINGS_SAVE_AS)
            self.Bind(
                wx.EVT_MENU, self.OnSpellCheckerDictionaryDlg, id=ID_SETTINGS_SC_DICT
            )
            self.Bind(wx.EVT_MENU, self.OnExit, id=ID_FILE_EXIT)
            self.Bind(wx.EVT_MENU, self.OnUndo, id=ID_EDIT_UNDO)
            self.Bind(wx.EVT_MENU, self.OnRedo, id=ID_EDIT_REDO)
            self.Bind(wx.EVT_MENU, self.OnCut, id=ID_EDIT_CUT)
            self.Bind(wx.EVT_MENU, self.OnCopy, id=ID_EDIT_COPY)
            self.Bind(wx.EVT_MENU, self.OnPaste, id=ID_EDIT_PASTE)
            self.Bind(wx.EVT_MENU, self.OnCopySystemCb, id=ID_EDIT_COPY_TO_CB)
            self.Bind(
                wx.EVT_MENU, self.OnCopySystemCbFormatted, id=ID_EDIT_COPY_TO_CB_FMT
            )
            self.Bind(wx.EVT_MENU, self.OnPasteSystemCb, id=ID_EDIT_PASTE_FROM_CB)
            self.Bind(wx.EVT_MENU, self.OnSelectScene, id=ID_EDIT_SELECT_SCENE)
            self.Bind(wx.EVT_MENU, self.OnSelectAll, id=ID_EDIT_SELECT_ALL)
            self.Bind(wx.EVT_MENU, self.OnGotoPage, id=ID_EDIT_GOTO_PAGE)
            self.Bind(wx.EVT_MENU, self.OnGotoScene, id=ID_EDIT_GOTO_SCENE)
            self.Bind(wx.EVT_MENU, self.OnInsertNbsp, id=ID_EDIT_INSERT_NBSP)
            self.Bind(wx.EVT_MENU, self.OnFind, id=ID_EDIT_FIND)
            self.Bind(wx.EVT_MENU, self.OnDeleteElements, id=ID_EDIT_DELETE_ELEMENTS)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_DRAFT)
            self.Bind(wx.EVT_MENU, self.ShowHideToolbar, id=ID_SHOW_HIDE_TOOLBAR)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_LAYOUT)
            self.Bind(wx.EVT_MENU, self.OnViewModeChange, id=ID_VIEW_STYLE_SIDE_BY_SIDE)
            self.Bind(wx.EVT_MENU, self.OnShowFormatting, id=ID_VIEW_SHOW_FORMATTING)
            self.Bind(wx.EVT_MENU, self.ToggleFullscreen, id=ID_VIEW_FULL_SCREEN)
            self.Bind(wx.EVT_MENU, self.OnFindNextError, id=ID_SCRIPT_FIND_ERROR)
            self.Bind(wx.EVT_MENU, self.OnPaginate, id=ID_SCRIPT_PAGINATE)
            self.Bind(
                wx.EVT_MENU, self.OnAutoCompletionDlg, id=ID_SCRIPT_AUTO_COMPLETION
            )
            self.Bind(wx.EVT_MENU, self.OnHeadersDlg, id=ID_SCRIPT_HEADERS)
            self.Bind(wx.EVT_MENU, self.OnLocationsDlg, id=ID_SCRIPT_LOCATIONS)
            self.Bind(wx.EVT_MENU, self.OnTitlesDlg, id=ID_SCRIPT_TITLES)
            self.Bind(
                wx.EVT_MENU,
                self.OnSpellCheckerScriptDictionaryDlg,
                id=ID_SCRIPT_SC_DICT,
            )
            self.Bind(wx.EVT_MENU, self.OnScriptSettings, id=ID_SCRIPT_SETTINGS_CHANGE)
            self.Bind(
                wx.EVT_MENU, self.OnLoadScriptSettings, id=ID_SCRIPT_SETTINGS_LOAD
            )
            self.Bind(
                wx.EVT_MENU, self.OnSaveScriptSettingsAs, id=ID_SCRIPT_SETTINGS_SAVE_AS
            )
            self.Bind(
                wx.EVT_MENU, self.OnReportDialogueChart, id=ID_REPORTS_DIALOGUE_CHART
            )
            self.Bind(wx.EVT_MENU, self.OnReportCharacter, id=ID_REPORTS_CHARACTER_REP)
            self.Bind(wx.EVT_MENU, self.OnReportScript, id=ID_REPORTS_SCRIPT_REP)
            self.Bind(wx.EVT_MENU, self.OnReportLocation, id=ID_REPORTS_LOCATION_REP)
            self.Bind(wx.EVT_MENU, self.OnReportScene, id=ID_REPORTS_SCENE_REP)
            self.Bind(wx.EVT_MENU, self.OnSpellCheckerDlg, id=ID_TOOLS_SPELL_CHECK)
            self.Bind(wx.EVT_MENU, self.OnNameDatabase, id=ID_TOOLS_NAME_DB)
            self.Bind(wx.EVT_MENU, self.OnCharacterMap, id=ID_TOOLS_CHARMAP)
            self.Bind(wx.EVT_MENU, self.OnCompareScripts, id=ID_TOOLS_COMPARE_SCRIPTS)
            self.Bind(wx.EVT_MENU, self.OnWatermark, id=ID_TOOLS_WATERMARK)
            self.Bind(wx.EVT_MENU, self.OnHelpCommands, id=ID_HELP_COMMANDS)
            self.Bind(wx.EVT_MENU, self.OnHelpManual, id=ID_HELP_MANUAL)
            self.Bind(wx.EVT_MENU, self.OnAbout, id=ID_HELP_ABOUT)
            self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)

        self.Bind(
            wx.EVT_MENU_RANGE,
            self.OnMRUFile,
            id=gd.mru.getIds()[0],
            id2=gd.mru.getIds()[1],
        )

        self.Bind(
            wx.EVT_MENU_RANGE,
            self.OnChangeType,
            id=ID_ELEM_TO_ACTION,
            id2=ID_ELEM_TO_TRANSITION,
        )

        def addTBMenu(id, menu):
            self.Bind(wx.EVT_MENU, partial(self.OnToolBarMenu, menu=menu), id=id)

        addTBMenu(ID_TOOLBAR_SETTINGS, menu_file_settings)
        addTBMenu(ID_TOOLBAR_SCRIPTSETTINGS, menu_script_settings)
        addTBMenu(ID_TOOLBAR_REPORTS, menu_reports)
        addTBMenu(ID_TOOLBAR_VIEWS, menu_view)
        addTBMenu(ID_TOOLBAR_TOOLS, menu_tools)

        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)

        self.Layout()

    def init(self):
        self.updateKbdCommands()
        self.panel = self.createNewPanel()

    def mySetIcons(self):
        wx.Image.AddHandler(wx.PNGHandler())

        ib = wx.IconBundle()

        for sz in ("16", "32", "64", "128", "256"):
            ib.AddIcon(wx.Icon(misc.getBitmap("trelby/resources/icon%s.png" % sz)))

        self.SetIcons(ib)

    # def allocIds(self):

    #     g = globals()

    #     # see OnChangeType
    #     g["idToLTMap"] = {
    #         ID_ELEM_TO_SCENE: screenplay.SCENE,
    #         ID_ELEM_TO_ACTION: screenplay.ACTION,
    #         ID_ELEM_TO_CHARACTER: screenplay.CHARACTER,
    #         ID_ELEM_TO_DIALOGUE: screenplay.DIALOGUE,
    #         ID_ELEM_TO_PAREN: screenplay.PAREN,
    #         ID_ELEM_TO_TRANSITION: screenplay.TRANSITION,
    #         ID_ELEM_TO_SHOT: screenplay.SHOT,
    #         ID_ELEM_TO_ACTBREAK: screenplay.ACTBREAK,
    #         ID_ELEM_TO_NOTE: screenplay.NOTE,
    #     }

    def createNewPanel(self):
        newPanel = MyPanel(self.tabCtrl.getTabParent(), -1, self.gd)
        self.tabCtrl.addPage(newPanel, "")
        newPanel.ctrl.setTabText()
        newPanel.ctrl.SetFocus()

        return newPanel

    def setTitle(self, text):
        self.SetTitle("Trelby - %s" % text)

    def setTabText(self, panel, text):
        i = self.findPage(panel)

        if i != -1:
            # strip out ".trelby" suffix from tab names (it's a bit
            # complicated since if we open the same file multiple times,
            # we have e.g. "foo.trelby" and "foo.trelby<2>", so actually
            # we just strip out ".trelby" if it's found anywhere in the
            # string)

            s = text.replace(".trelby", "")
            self.tabCtrl.setTabText(i, s)

    # iterates over all tabs and finds out the corresponding page number
    # for the given panel.
    def findPage(self, panel):
        for i in range(self.tabCtrl.getPageCount()):
            p = self.tabCtrl.getPage(i)
            if p == panel:
                return i

        return -1

    # get list of MyCtrl objects for all open scripts
    def getCtrls(self):
        l = []

        for i in range(self.tabCtrl.getPageCount()):
            l.append(self.tabCtrl.getPage(i).ctrl)

        return l

    # returns True if any open script has been modified
    def isModifications(self):
        for c in self.getCtrls():
            if c.sp.isModified():
                return True

        return False

    def updateKbdCommands(self):
        self.gd.cfgGl.addShiftKeys()

        if self.gd.cfgGl.getConflictingKeys() != None:
            wx.MessageBox(
                _(
                    "You have at least one key bound to more than one\ncommand. The program will not work correctly until\nyou fix this."
                ),
                _("Warning"),
                wx.OK,
                self,
            )

        self.kbdCommands = {}

        for cmd in self.gd.cfgGl.commands:
            if not (cmd.isFixed and cmd.isMenu):
                for key in cmd.keys:
                    self.kbdCommands[key] = cmd

    # open script, in the current tab if it's untouched, or in a new one
    # otherwise
    def openScript(self, filename):
        if not self.tabCtrl.getPage(self.findPage(self.panel)).ctrl.isUntouched():
            self.panel = self.createNewPanel()

        self.panel.ctrl.loadFile(filename)
        self.panel.ctrl.updateScreen()
        self.gd.mru.add(filename)

    def checkFonts(self):
        names = ["Normal", "Bold", "Italic", "Bold-Italic"]
        failed = []

        for i, fi in enumerate(self.gd.cfgGui.fonts):
            if not util.isFixedWidth(fi.font):
                failed.append(names[i])

        if failed:
            wx.MessageBox(
                _(
                    "The fonts listed below are not fixed width and\nwill cause the program not to function correctly.\nPlease change the fonts at File/Settings/Change.\n\n\n"
                ).join(failed),
                _("Error"),
                wx.OK,
                self,
            )

    # If we get focus, pass it on to ctrl.
    def OnFocus(self, event):
        self.panel.ctrl.SetFocus()

    def OnMenuHighlight(self, event):
        # default implementation modifies status bar, so we need to
        # override it and do nothing
        pass

    def OnPageChange(self, page):
        self.panel = self.tabCtrl.getPage(page)
        self.panel.ctrl.SetFocus()
        self.panel.ctrl.updateCommon()
        self.setTitle(self.panel.ctrl.fileNameDisplay)

    def selectScript(self, toNext):
        current = self.tabCtrl.getSelectedPageIndex()
        pageCnt = self.tabCtrl.getPageCount()

        if toNext:
            pageNr = current + 1
        else:
            pageNr = current - 1

        if pageNr == -1:
            pageNr = pageCnt - 1
        elif pageNr == pageCnt:
            pageNr = 0

        if pageNr == current:
            # only one tab, nothing to do
            return

        self.tabCtrl.selectPage(pageNr)

    def OnScriptNext(self, event=None):
        self.selectScript(True)

    def OnScriptPrev(self, event=None):
        self.selectScript(False)

    def OnNewScript(self, event=None):
        self.panel = self.createNewPanel()

    def OnMRUFile(self, event):
        i = event.GetId() - self.gd.mru.getIds()[0]
        self.openScript(self.gd.mru.get(i))

    def OnOpen(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to open"),
            misc.scriptDir,
            wildcard="Trelby "
            + _("files")
            + " (*.trelby)|*.trelby|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()
            self.openScript(dlg.GetPath())

        dlg.Destroy()

    def OnSave(self, event=None):
        self.panel.ctrl.OnSave()

    def OnSaveScriptAs(self, event=None):
        self.panel.ctrl.OnSaveScriptAs()

    def OnImportScript(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to import"),
            misc.scriptDir,
            wildcard=_("Importable")
            + " "
            + _("files")
            + "(*.txt;*.fdx;*.celtx;*.astx;*.fountain;*.fadein)|"
            + "*.fdx;*.txt;*.celtx;*.astx;*.fountain;*.fadein|"
            + _("Formatted")
            + " "
            + _("text")
            + " "
            + _("files")
            + "(*.txt)|*.txt|"
            + "Final Draft XML(*.fdx)|*.fdx|"
            + "Celtx "
            + _("files")
            + " (*.celtx)|*.celtx|"
            + "Adobe Story XML "
            + _("files")
            + " (*.astx)|*.astx|"
            + "Fountain "
            + _("files")
            + " (*.fountain)|*.fountain|"
            + "Fadein "
            + _("files")
            + " (*.fadein)|*.fadein|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            misc.scriptDir = dlg.GetDirectory()

            if not self.tabCtrl.getPage(self.findPage(self.panel)).ctrl.isUntouched():
                self.panel = self.createNewPanel()

            self.panel.ctrl.importFile(dlg.GetPath())
            self.panel.ctrl.updateScreen()

        dlg.Destroy()

    def OnExportScript(self, event=None):
        self.panel.ctrl.OnExportScript()

    def OnCloseScript(self, event=None):
        if not self.panel.ctrl.canBeClosed():
            return

        if self.tabCtrl.getPageCount() > 1:
            self.tabCtrl.deletePage(self.tabCtrl.getSelectedPageIndex())
        else:
            self.panel.ctrl.createEmptySp()
            self.panel.ctrl.updateScreen()

    def OnRevertScript(self, event=None):
        self.panel.ctrl.OnRevertScript()

    def OnPrint(self, event=None):
        self.panel.ctrl.OnPrint()

    def OnSettings(self, event=None):
        self.panel.ctrl.OnSettings()

    def OnLoadSettings(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to open"),
            defaultDir=os.path.dirname(self.gd.confFilename),
            defaultFile=os.path.basename(self.gd.confFilename),
            wildcard=_("Setting")
            + " "
            + _("files")
            + " (*.conf)|*.conf|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                c = config.ConfigGlobal()
                c.load(s)
                self.gd.confFilename = dlg.GetPath()

                self.panel.ctrl.applyGlobalCfg(c, False)

        dlg.Destroy()

    def OnSaveSettingsAs(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("Filename to save as"),
            defaultDir=os.path.dirname(self.gd.confFilename),
            defaultFile=os.path.basename(self.gd.confFilename),
            wildcard=_("Setting")
            + " "
            + _("files")
            + " (*.conf)|*.conf|"
            + _("All files")
            + "|*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), self.gd.cfgGl.save(), self):
                self.gd.confFilename = dlg.GetPath()

        dlg.Destroy()

    def OnUndo(self, event=None):
        self.panel.ctrl.OnUndo()

    def OnRedo(self, event=None):
        self.panel.ctrl.OnRedo()

    def OnCut(self, event=None):
        self.panel.ctrl.OnCut()

    def OnCopy(self, event=None):
        self.panel.ctrl.OnCopy()

    def OnCopySystemCb(self, event=None):
        self.panel.ctrl.OnCopySystem(formatted=False)

    def OnCopySystemCbFormatted(self, event=None):
        self.panel.ctrl.OnCopySystem(formatted=True)

    def OnPaste(self, event=None):
        self.panel.ctrl.OnPaste()

    def OnPasteSystemCb(self, event=None):
        self.panel.ctrl.OnPasteSystemCb()

    def OnSelectScene(self, event=None):
        self.panel.ctrl.OnSelectScene()

    def OnSelectAll(self, event=None):
        self.panel.ctrl.OnSelectAll()

    def OnGotoPage(self, event=None):
        self.panel.ctrl.OnGotoPage()

    def OnGotoScene(self, event=None):
        self.panel.ctrl.OnGotoScene()

    def OnFindNextError(self, event=None):
        self.panel.ctrl.OnFindNextError()

    def OnFind(self, event=None):
        self.panel.ctrl.OnFind()

    def OnInsertNbsp(self, event=None):
        self.panel.ctrl.OnInsertNbsp()

    def OnDeleteElements(self, event=None):
        self.panel.ctrl.OnDeleteElements()

    def OnToggleShowFormatting(self, event=None):
        self.menuBar.Check(
            ID_VIEW_SHOW_FORMATTING, not self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING)
        )
        self.showFormatting = not self.showFormatting
        self.panel.ctrl.Refresh(False)

    def OnShowFormatting(self, event=None):
        self.showFormatting = self.menuBar.IsChecked(ID_VIEW_SHOW_FORMATTING)
        self.panel.ctrl.Refresh(False)

    def OnViewModeDraft(self):
        self.menuBar.Check(ID_VIEW_STYLE_DRAFT, True)
        self.OnViewModeChange()

    def ShowHideToolbar(self, event=None):
        self.CheckToolbar = self.menuBar.IsChecked(ID_SHOW_HIDE_TOOLBAR)

        if self.CheckToolbar == True:
            self.toolBar.Hide()

        else:
            self.toolBar.Show()

    def OnViewModeLayout(self):
        self.menuBar.Check(ID_VIEW_STYLE_LAYOUT, True)
        self.OnViewModeChange()

    def OnViewModeSideBySide(self):
        self.menuBar.Check(ID_VIEW_STYLE_SIDE_BY_SIDE, True)
        self.OnViewModeChange()

    def OnViewModeChange(self, event=None):
        if self.menuBar.IsChecked(ID_VIEW_STYLE_DRAFT):
            mode = self.gd.VIEWMODE_DRAFT
        elif self.menuBar.IsChecked(ID_VIEW_STYLE_LAYOUT):
            mode = self.gd.VIEWMODE_LAYOUT
        else:
            mode = self.gd.VIEWMODE_SIDE_BY_SIDE

        self.gd.setViewMode(mode)

        for c in self.getCtrls():
            c.refreshCache()

        c = self.panel.ctrl
        c.makeLineVisible(c.sp.line)
        c.updateScreen()

    def ToggleFullscreen(self, event=None):
        self.noFSBtn.Show(not self.IsFullScreen())
        self.ShowFullScreen(not self.IsFullScreen(), wx.FULLSCREEN_ALL)
        self.panel.ctrl.SetFocus()

    def OnPaginate(self, event=None):
        self.panel.ctrl.OnPaginate()

    def OnAutoCompletionDlg(self, event=None):
        self.panel.ctrl.OnAutoCompletionDlg()

    def OnTitlesDlg(self, event=None):
        self.panel.ctrl.OnTitlesDlg()

    def OnHeadersDlg(self, event=None):
        self.panel.ctrl.OnHeadersDlg()

    def OnLocationsDlg(self, event=None):
        self.panel.ctrl.OnLocationsDlg()

    def OnSpellCheckerDictionaryDlg(self, event=None):
        dlg = spellcheckcfgdlg.SCDictDlg(self, copy.deepcopy(self.gd.scDict), True)

        if dlg.ShowModal() == wx.ID_OK:
            self.gd.scDict = dlg.scDict
            self.gd.saveScDict()

        dlg.Destroy()

    def OnSpellCheckerScriptDictionaryDlg(self, event=None):
        self.panel.ctrl.OnSpellCheckerScriptDictionaryDlg()

    def OnWatermark(self, event=None):
        self.panel.ctrl.OnWatermark()

    def OnScriptSettings(self, event=None):
        self.panel.ctrl.OnScriptSettings()

    def OnLoadScriptSettings(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("File to open"),
            defaultDir=self.gd.scriptSettingsPath,
            wildcard=_("Script")
            + " "
            + _("setting")
            + " "
            + _("files")
            + " (*.sconf)|*.sconf|"
            + _("All files")
            + "|*",
            style=wx.FD_OPEN,
        )

        if dlg.ShowModal() == wx.ID_OK:
            s = util.loadFile(dlg.GetPath(), self)

            if s:
                cfg = config.Config()
                cfg.load(s)
                self.panel.ctrl.applyCfg(cfg)

                self.gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnSaveScriptSettingsAs(self, event=None):
        dlg = wx.FileDialog(
            self,
            _("Filename to save as"),
            defaultDir=self.gd.scriptSettingsPath,
            wildcard=_("Script")
            + " "
            + _("setting")
            + _("files")
            + " (*.sconf)|*.sconf|"
            + _("All files")
            + "|*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        )

        if dlg.ShowModal() == wx.ID_OK:
            if util.writeToFile(dlg.GetPath(), self.panel.ctrl.sp.saveCfg(), self):
                self.gd.scriptSettingsPath = os.path.dirname(dlg.GetPath())

        dlg.Destroy()

    def OnReportCharacter(self, event=None):
        self.panel.ctrl.OnReportCharacter()

    def OnReportDialogueChart(self, event=None):
        self.panel.ctrl.OnReportDialogueChart()

    def OnReportLocation(self, event=None):
        self.panel.ctrl.OnReportLocation()

    def OnReportScene(self, event=None):
        self.panel.ctrl.OnReportScene()

    def OnReportScript(self, event=None):
        self.panel.ctrl.OnReportScript()

    def OnSpellCheckerDlg(self, event=None):
        self.panel.ctrl.OnSpellCheckerDlg()

    def OnNameDatabase(self, event=None):
        if not namesdlg.readNames(self):
            wx.MessageBox(_("Error opening name database."), _("Error"), wx.OK, self)

            return

        dlg = namesdlg.NamesDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCharacterMap(self, event=None):
        dlg = charmapdlg.CharMapDlg(self, self.panel.ctrl)
        dlg.ShowModal()
        dlg.Destroy()

    def OnCompareScripts(self, event=None):
        self.panel.ctrl.OnCompareScripts()

    def OnChangeType(self, event):
        self.panel.ctrl.OnChangeType(event)

    def OnHelpCommands(self, event=None):
        dlg = commandsdlg.CommandsDlg(self.gd.cfgGl)
        dlg.Show()

    def OnHelpManual(self, event=None):
        webbrowser.open("file://" + misc.getFullPath("trelby/manual.html"))

    def OnAbout(self, event=None):
        win = splash.SplashWindow(self, -1)
        win.Show()

    def OnToolBarMenu(self, event, menu):
        self.PopupMenu(menu)

    def OnCloseWindow(self, event):
        doExit = True
        if event.CanVeto() and self.isModifications():
            close_msg_box = wx.MessageDialog(
                self,
                _("You have unsaved changes. Do\nyou want to save your changes?"),
                _("Save Changes"),
                wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT,
            )
            close_msg_box.SetYesNoLabels(wx.ID_SAVE, to_mnemonics('D', _("Don't save")))
            response = close_msg_box.ShowModal()
            if response == wx.ID_YES:
                self.OnSave()
            elif response == wx.ID_CANCEL:
                doExit = False

        if doExit:
            util.writeToFile(self.gd.stateFilename, self.gd.save(), self)
            util.removeTempFiles(misc.tmpPrefix)
            self.Destroy()
            self.myApp.ExitMainLoop()
        else:
            event.Veto()

    def OnExit(self, event):
        self.Close(False)

    def OnMove(self, event):
        self.gd.posX, self.gd.posY = self.GetPosition()
        event.Skip()

    def OnSize(self, event):
        self.gd.width, self.gd.height = self.GetSize()
        event.Skip()

    def getCfgGui(self):
        return self.gd.cfgGui
