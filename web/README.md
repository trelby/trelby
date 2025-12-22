# Courius

A fully functioning HTML/JavaScript screenwriting application, originally ported from Trelby.

## Features

- **Full Screenplay Editor** - Write screenplays with proper formatting
- **Element Types** - Scene, Action, Character, Dialogue, Parenthetical, Transition, Shot, Note, Act Break
- **View Modes** - Draft, Layout (page preview), and Side-by-Side views
- **File Operations** - New, Open, Save (using File System Access API or downloads)
- **Import Formats** - Trelby (.trelby), Final Draft (.fdx), Fountain (.fountain), Plain Text
- **Export Formats** - PDF, HTML, Plain Text, Final Draft XML, Fountain, RTF
- **Auto-completion** - Smart suggestions for scenes, characters, transitions
- **Spell Checking** - Built-in spell checker with custom dictionary
- **Find/Replace** - Full search and replace with regex support
- **Reports** - Scene, Character, Location, Script, and Dialogue reports
- **Undo/Redo** - Full undo history
- **Title Pages** - Create and manage multiple title pages
- **Headers/Footers** - Customizable page headers with page numbers
- **Watermarks** - Add watermarks to exported PDFs
- **Settings** - Customize paper size, margins, fonts, and display options
- **Keyboard Shortcuts** - Full keyboard navigation
- **Themes** - Light, Dark, and Sepia themes
- **Auto-save** - Automatic backup to localStorage

## Usage

Simply open `index.html` in a modern web browser (Chrome, Firefox, Edge, Safari).

```bash
# Or serve with a local web server:
python -m http.server 8000
# Then open http://localhost:8000/web/
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New screenplay |
| Ctrl+O | Open file |
| Ctrl+S | Save file |
| Ctrl+Shift+S | Save as |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+X | Cut |
| Ctrl+C | Copy |
| Ctrl+V | Paste |
| Ctrl+A | Select all |
| Ctrl+F | Find |
| Ctrl+H | Replace |
| F3 | Find next |
| Ctrl+1 | Set element to Scene |
| Ctrl+2 | Set element to Action |
| Ctrl+3 | Set element to Character |
| Ctrl+4 | Set element to Dialogue |
| Ctrl+5 | Set element to Parenthetical |
| Ctrl+6 | Set element to Transition |
| Ctrl+7 | Set element to Shot |
| Ctrl+8 | Set element to Note |
| Tab | Cycle element types |
| Enter | Smart line break |
| Ctrl+Enter | Force page break |
| F11 | Toggle fullscreen |

## Browser Compatibility

- Chrome/Edge 86+ (full File System Access API support)
- Firefox 86+ (file download fallback)
- Safari 14+ (file download fallback)

## Architecture

The app is built with vanilla JavaScript (no frameworks) for maximum portability:

- `index.html` - Main HTML structure
- `css/` - Stylesheets
  - `main.css` - Core styles and theming
  - `editor.css` - Screenplay editor styles
  - `toolbar.css` - Toolbar styles
  - `dialogs.css` - Dialog/modal styles
- `js/` - JavaScript modules
  - `constants.js` - Application constants
  - `config.js` - Configuration management
  - `utils.js` - Utility functions
  - `line.js` - Line data model
  - `screenplay.js` - Screenplay data model
  - `undo.js` - Undo/redo system
  - `autocompletion.js` - Auto-completion
  - `spellcheck.js` - Spell checking
  - `fileio.js` - File I/O operations
  - `export.js` - Export functionality
  - `reports.js` - Report generation
  - `dialogs.js` - Dialog management
  - `editor.js` - Main editor component
  - `menu.js` - Menu and shortcuts
  - `app.js` - Application entry point

## License

GPL v2.
