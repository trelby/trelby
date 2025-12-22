/**
 * Courius - Screenwriting Software
 * Constants module
 */

// Line break types
const LB = {
    SPACE: 1,    // Normal space after line
    NONE: 3,     // No space (continuation)
    FORCED: 4,   // Forced line break
    LAST: 5      // Last line of paragraph
};

// Line/element types
const LINE_TYPE = {
    SCENE: 'scene',
    ACTION: 'action',
    CHARACTER: 'character',
    DIALOGUE: 'dialogue',
    PAREN: 'paren',
    TRANSITION: 'transition',
    SHOT: 'shot',
    NOTE: 'note',
    ACTBREAK: 'actbreak'
};

// Map numeric types to string types (for compatibility with .trelby format)
const LINE_TYPE_NUM = {
    1: LINE_TYPE.SCENE,
    2: LINE_TYPE.ACTION,
    3: LINE_TYPE.CHARACTER,
    4: LINE_TYPE.DIALOGUE,
    5: LINE_TYPE.PAREN,
    6: LINE_TYPE.TRANSITION,
    7: LINE_TYPE.SHOT,
    8: LINE_TYPE.NOTE,
    9: LINE_TYPE.ACTBREAK
};

const LINE_TYPE_TO_NUM = {
    [LINE_TYPE.SCENE]: 1,
    [LINE_TYPE.ACTION]: 2,
    [LINE_TYPE.CHARACTER]: 3,
    [LINE_TYPE.DIALOGUE]: 4,
    [LINE_TYPE.PAREN]: 5,
    [LINE_TYPE.TRANSITION]: 6,
    [LINE_TYPE.SHOT]: 7,
    [LINE_TYPE.NOTE]: 8,
    [LINE_TYPE.ACTBREAK]: 9
};

// Element formatting rules (margins in characters for 60 char width)
const ELEMENT_FORMAT = {
    [LINE_TYPE.SCENE]: {
        indent: 0,
        width: 60,
        beforeSpacing: 2,
        afterSpacing: 1,
        caps: true,
        bold: true
    },
    [LINE_TYPE.ACTION]: {
        indent: 0,
        width: 60,
        beforeSpacing: 1,
        afterSpacing: 1,
        caps: false,
        bold: false
    },
    [LINE_TYPE.CHARACTER]: {
        indent: 22,
        width: 38,
        beforeSpacing: 1,
        afterSpacing: 0,
        caps: true,
        bold: false
    },
    [LINE_TYPE.DIALOGUE]: {
        indent: 10,
        width: 35,
        beforeSpacing: 0,
        afterSpacing: 0,
        caps: false,
        bold: false
    },
    [LINE_TYPE.PAREN]: {
        indent: 16,
        width: 26,
        beforeSpacing: 0,
        afterSpacing: 0,
        caps: false,
        bold: false
    },
    [LINE_TYPE.TRANSITION]: {
        indent: 45,
        width: 15,
        beforeSpacing: 1,
        afterSpacing: 1,
        caps: true,
        bold: false
    },
    [LINE_TYPE.SHOT]: {
        indent: 0,
        width: 60,
        beforeSpacing: 1,
        afterSpacing: 1,
        caps: true,
        bold: false
    },
    [LINE_TYPE.NOTE]: {
        indent: 5,
        width: 55,
        beforeSpacing: 1,
        afterSpacing: 1,
        caps: false,
        bold: false
    },
    [LINE_TYPE.ACTBREAK]: {
        indent: 20,
        width: 20,
        beforeSpacing: 2,
        afterSpacing: 2,
        caps: true,
        bold: true
    }
};

// Smart element transitions (what element type comes after Enter)
const ELEMENT_NEXT = {
    [LINE_TYPE.SCENE]: LINE_TYPE.ACTION,
    [LINE_TYPE.ACTION]: LINE_TYPE.ACTION,
    [LINE_TYPE.CHARACTER]: LINE_TYPE.DIALOGUE,
    [LINE_TYPE.DIALOGUE]: LINE_TYPE.CHARACTER,
    [LINE_TYPE.PAREN]: LINE_TYPE.DIALOGUE,
    [LINE_TYPE.TRANSITION]: LINE_TYPE.SCENE,
    [LINE_TYPE.SHOT]: LINE_TYPE.ACTION,
    [LINE_TYPE.NOTE]: LINE_TYPE.ACTION,
    [LINE_TYPE.ACTBREAK]: LINE_TYPE.SCENE
};

// Tab cycling order
const TAB_CYCLE = [
    LINE_TYPE.SCENE,
    LINE_TYPE.ACTION,
    LINE_TYPE.CHARACTER,
    LINE_TYPE.DIALOGUE,
    LINE_TYPE.PAREN,
    LINE_TYPE.TRANSITION
];

// Common scene prefixes
const SCENE_PREFIXES = ['INT.', 'EXT.', 'INT./EXT.', 'EXT./INT.', 'I/E.', 'E/I.'];

// Common transitions
const TRANSITIONS = [
    'CUT TO:',
    'FADE TO:',
    'FADE OUT.',
    'FADE IN:',
    'DISSOLVE TO:',
    'SMASH CUT TO:',
    'MATCH CUT TO:',
    'JUMP CUT TO:',
    'WIPE TO:',
    'TIME CUT:',
    'INTERCUT:'
];

// Paper sizes in points (1 inch = 72 points)
const PAPER_SIZES = {
    letter: { width: 612, height: 792, name: 'US Letter' },  // 8.5" x 11"
    a4: { width: 595, height: 842, name: 'A4' }              // 210mm x 297mm
};

// Default configuration
const DEFAULT_CONFIG = {
    paperSize: 'letter',
    margins: {
        top: 72,      // 1 inch
        bottom: 72,   // 1 inch
        left: 108,    // 1.5 inches
        right: 72     // 1 inch
    },
    fontSize: 12,
    fontFamily: 'Courier New',
    linesPerPage: 55,
    charsPerLine: 60,
    showPageBreaks: true,
    showLineNumbers: false,
    autoSave: false,
    autoSaveInterval: 60000, // 1 minute
    spellCheck: true,
    theme: 'light'
};

// Keyboard shortcuts
const SHORTCUTS = {
    'Ctrl+N': 'new',
    'Ctrl+O': 'open',
    'Ctrl+S': 'save',
    'Ctrl+Shift+S': 'saveAs',
    'Ctrl+P': 'print',
    'Ctrl+Z': 'undo',
    'Ctrl+Y': 'redo',
    'Ctrl+Shift+Z': 'redo',
    'Ctrl+X': 'cut',
    'Ctrl+C': 'copy',
    'Ctrl+V': 'paste',
    'Ctrl+A': 'selectAll',
    'Ctrl+F': 'find',
    'Ctrl+H': 'replace',
    'F3': 'findNext',
    'Shift+F3': 'findPrev',
    'F11': 'fullscreen',
    'Ctrl+1': 'setScene',
    'Ctrl+2': 'setAction',
    'Ctrl+3': 'setCharacter',
    'Ctrl+4': 'setDialogue',
    'Ctrl+5': 'setParen',
    'Ctrl+6': 'setTransition',
    'Ctrl+7': 'setShot',
    'Ctrl+8': 'setNote',
    'Ctrl++': 'zoomIn',
    'Ctrl+=': 'zoomIn',
    'Ctrl+-': 'zoomOut',
    'Ctrl+0': 'zoomReset',
    'Escape': 'closeDialog'
};

// Version info
const VERSION = {
    major: 1,
    minor: 0,
    patch: 0,
    string: '1.0.0',
    name: 'Courius'
};

// File format markers
const FILE_MARKERS = {
    VERSION_PREFIX: '#Version ',
    SCRIPT_START: '#Start-Script',
    BEGIN_PREFIX: '#Begin-',
    END_PREFIX: '#End-',
    BOM: '\uFEFF'  // UTF-8 BOM
};

// Line break characters in .trelby format
const LB_CHARS = {
    '>': LB.SPACE,
    '&': LB.NONE,
    '|': LB.FORCED,
    '.': LB.LAST
};

const LB_TO_CHAR = {
    [LB.SPACE]: '>',
    [LB.NONE]: '&',
    [LB.FORCED]: '|',
    [LB.LAST]: '.'
};

// Line type characters in .trelby format
const LT_CHARS = {
    '\\': LINE_TYPE.SCENE,
    '.': LINE_TYPE.ACTION,
    '_': LINE_TYPE.CHARACTER,
    ':': LINE_TYPE.DIALOGUE,
    '(': LINE_TYPE.PAREN,
    '/': LINE_TYPE.TRANSITION,
    '=': LINE_TYPE.SHOT,
    '%': LINE_TYPE.NOTE
};

const LT_TO_CHAR = {
    [LINE_TYPE.SCENE]: '\\',
    [LINE_TYPE.ACTION]: '.',
    [LINE_TYPE.CHARACTER]: '_',
    [LINE_TYPE.DIALOGUE]: ':',
    [LINE_TYPE.PAREN]: '(',
    [LINE_TYPE.TRANSITION]: '/',
    [LINE_TYPE.SHOT]: '=',
    [LINE_TYPE.NOTE]: '%',
    [LINE_TYPE.ACTBREAK]: '~'
};

// Export all constants
window.CouriusConstants = {
    LB,
    LINE_TYPE,
    LINE_TYPE_NUM,
    LINE_TYPE_TO_NUM,
    ELEMENT_FORMAT,
    ELEMENT_NEXT,
    TAB_CYCLE,
    SCENE_PREFIXES,
    TRANSITIONS,
    PAPER_SIZES,
    DEFAULT_CONFIG,
    SHORTCUTS,
    VERSION,
    FILE_MARKERS,
    LB_CHARS,
    LB_TO_CHAR,
    LT_CHARS,
    LT_TO_CHAR
};
