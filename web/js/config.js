/**
 * Trelby Web - Configuration System
 */

class Config {
    constructor(defaults = {}) {
        const { DEFAULT_CONFIG } = window.TrelbyConstants;

        // Paper settings
        this.paperSize = defaults.paperSize || DEFAULT_CONFIG.paperSize;
        this.margins = { ...DEFAULT_CONFIG.margins, ...defaults.margins };

        // Font settings
        this.fontSize = defaults.fontSize || DEFAULT_CONFIG.fontSize;
        this.fontFamily = defaults.fontFamily || DEFAULT_CONFIG.fontFamily;

        // Layout
        this.linesPerPage = defaults.linesPerPage || DEFAULT_CONFIG.linesPerPage;
        this.charsPerLine = defaults.charsPerLine || DEFAULT_CONFIG.charsPerLine;

        // Display
        this.showPageBreaks = defaults.showPageBreaks ?? DEFAULT_CONFIG.showPageBreaks;
        this.showLineNumbers = defaults.showLineNumbers ?? DEFAULT_CONFIG.showLineNumbers;
        this.theme = defaults.theme || DEFAULT_CONFIG.theme;

        // Auto-save
        this.autoSave = defaults.autoSave ?? DEFAULT_CONFIG.autoSave;
        this.autoSaveInterval = defaults.autoSaveInterval || DEFAULT_CONFIG.autoSaveInterval;

        // Spell check
        this.spellCheck = defaults.spellCheck ?? DEFAULT_CONFIG.spellCheck;

        // Element-specific formatting (can be customized per-element)
        this.elementFormat = this._initElementFormat(defaults.elementFormat);

        // Headers
        this.headers = {
            firstPage: defaults.headers?.firstPage ?? '',
            otherPages: defaults.headers?.otherPages ?? '%p.',
            showOnFirst: defaults.headers?.showOnFirst ?? false
        };

        // Watermark
        this.watermark = {
            enabled: defaults.watermark?.enabled ?? false,
            text: defaults.watermark?.text ?? '',
            fontSize: defaults.watermark?.fontSize ?? 48,
            opacity: defaults.watermark?.opacity ?? 0.3,
            angle: defaults.watermark?.angle ?? -45
        };
    }

    _initElementFormat(customFormat = {}) {
        const { LINE_TYPE, ELEMENT_FORMAT } = window.TrelbyConstants;
        const format = {};

        for (const type of Object.values(LINE_TYPE)) {
            format[type] = {
                ...ELEMENT_FORMAT[type],
                ...customFormat[type]
            };
        }

        return format;
    }

    getPageWidth() {
        const { PAPER_SIZES } = window.TrelbyConstants;
        return PAPER_SIZES[this.paperSize].width;
    }

    getPageHeight() {
        const { PAPER_SIZES } = window.TrelbyConstants;
        return PAPER_SIZES[this.paperSize].height;
    }

    getContentWidth() {
        return this.getPageWidth() - this.margins.left - this.margins.right;
    }

    getContentHeight() {
        return this.getPageHeight() - this.margins.top - this.margins.bottom;
    }

    toJSON() {
        return {
            paperSize: this.paperSize,
            margins: { ...this.margins },
            fontSize: this.fontSize,
            fontFamily: this.fontFamily,
            linesPerPage: this.linesPerPage,
            charsPerLine: this.charsPerLine,
            showPageBreaks: this.showPageBreaks,
            showLineNumbers: this.showLineNumbers,
            theme: this.theme,
            autoSave: this.autoSave,
            autoSaveInterval: this.autoSaveInterval,
            spellCheck: this.spellCheck,
            elementFormat: { ...this.elementFormat },
            headers: { ...this.headers },
            watermark: { ...this.watermark }
        };
    }

    static fromJSON(json) {
        return new Config(json);
    }

    clone() {
        return Config.fromJSON(this.toJSON());
    }

    // Save to localStorage
    save(key = 'trelby-config') {
        try {
            localStorage.setItem(key, JSON.stringify(this.toJSON()));
            return true;
        } catch (e) {
            console.error('Failed to save config:', e);
            return false;
        }
    }

    // Load from localStorage
    static load(key = 'trelby-config') {
        try {
            const data = localStorage.getItem(key);
            if (data) {
                return Config.fromJSON(JSON.parse(data));
            }
        } catch (e) {
            console.error('Failed to load config:', e);
        }
        return new Config();
    }
}

// Global configuration instance
window.TrelbyConfig = Config;
