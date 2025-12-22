/**
 * Courius - Screenplay Model
 * Main data structure for a screenplay
 */

class Screenplay {
    constructor(config = null) {
        const { LB, LINE_TYPE } = window.CouriusConstants;
        const Line = window.CouriusLine;

        // Configuration
        this.config = config || new window.CouriusConfig();

        // Content
        this.lines = [new Line(LB.LAST, LINE_TYPE.ACTION, '')];

        // Cursor position
        this.cursorLine = 0;
        this.cursorColumn = 0;

        // Selection
        this.selectionStart = null;  // { line, column }
        this.selectionEnd = null;    // { line, column }

        // Title pages
        this.titlePages = [];

        // Auto-completion data
        this.autoCompletion = {
            scenes: new Set(['INT.', 'EXT.', 'INT./EXT.']),
            characters: new Set(),
            transitions: new Set(window.CouriusConstants.TRANSITIONS),
            shots: new Set()
        };

        // Locations mapping
        this.locations = new Map();

        // Headers
        this.headers = {
            firstPage: '',
            otherPages: '%p.',
            showOnFirst: false
        };

        // Metadata
        this.metadata = {
            created: new Date().toISOString(),
            modified: new Date().toISOString(),
            filename: 'Untitled.trelby',
            author: ''
        };

        // State
        this.modified = false;

        // Pagination cache
        this._pageBreaks = null;
    }

    /**
     * Get total number of lines
     */
    get lineCount() {
        return this.lines.length;
    }

    /**
     * Get a line by index
     */
    getLine(index) {
        if (index < 0 || index >= this.lines.length) return null;
        return this.lines[index];
    }

    /**
     * Set a line by index
     */
    setLine(index, line) {
        if (index < 0 || index >= this.lines.length) return false;
        this.lines[index] = line;
        this.markModified();
        return true;
    }

    /**
     * Insert a line at index
     */
    insertLine(index, line) {
        const Line = window.CouriusLine;
        if (index < 0) index = 0;
        if (index > this.lines.length) index = this.lines.length;

        this.lines.splice(index, 0, line || new Line());
        this._updateLineIndices();
        this.markModified();
        return true;
    }

    /**
     * Delete a line at index
     */
    deleteLine(index) {
        if (index < 0 || index >= this.lines.length) return false;
        if (this.lines.length === 1) {
            // Keep at least one line
            this.lines[0] = new window.CouriusLine();
            this.markModified();
            return true;
        }

        this.lines.splice(index, 1);
        this._updateLineIndices();
        this.markModified();
        return true;
    }

    /**
     * Get text of a line
     */
    getLineText(index) {
        const line = this.getLine(index);
        return line ? line.text : '';
    }

    /**
     * Set text of a line
     */
    setLineText(index, text) {
        const line = this.getLine(index);
        if (!line) return false;
        line.text = text;
        this.markModified();
        return true;
    }

    /**
     * Get type of a line
     */
    getLineType(index) {
        const line = this.getLine(index);
        return line ? line.type : null;
    }

    /**
     * Set type of a line
     */
    setLineType(index, type) {
        const line = this.getLine(index);
        if (!line) return false;
        line.type = type;
        this.markModified();
        return true;
    }

    /**
     * Mark screenplay as modified
     */
    markModified() {
        this.modified = true;
        this.metadata.modified = new Date().toISOString();
        this._pageBreaks = null; // Invalidate pagination cache
    }

    /**
     * Clear modified flag
     */
    clearModified() {
        this.modified = false;
    }

    /**
     * Get all text as a single string
     */
    getAllText() {
        return this.lines.map(line => line.text).join('\n');
    }

    /**
     * Get word count
     */
    getWordCount() {
        let count = 0;
        for (const line of this.lines) {
            count += window.CouriusUtils.countWords(line.text);
        }
        return count;
    }

    /**
     * Get page count (approximate)
     */
    getPageCount() {
        const pageBreaks = this.calculatePageBreaks();
        return pageBreaks.length;
    }

    /**
     * Calculate page breaks
     */
    calculatePageBreaks() {
        if (this._pageBreaks) return this._pageBreaks;

        const { LINE_TYPE, ELEMENT_FORMAT } = window.CouriusConstants;
        const linesPerPage = this.config.linesPerPage || 55;

        const pageBreaks = [0]; // First page starts at line 0
        let currentPageLines = 0;

        for (let i = 0; i < this.lines.length; i++) {
            const line = this.lines[i];
            const format = ELEMENT_FORMAT[line.type] || ELEMENT_FORMAT[LINE_TYPE.ACTION];

            // Add spacing before element
            if (i > 0 && line.isLastInParagraph()) {
                currentPageLines += format.beforeSpacing || 0;
            }

            // Count the line
            currentPageLines++;

            // Add spacing after element if it's the last in paragraph
            if (line.isLastInParagraph()) {
                currentPageLines += format.afterSpacing || 0;
            }

            // Check for page break
            if (currentPageLines >= linesPerPage) {
                pageBreaks.push(i + 1);
                currentPageLines = 0;
            }
        }

        this._pageBreaks = pageBreaks;
        return pageBreaks;
    }

    /**
     * Get page number for a line
     */
    getPageForLine(lineIndex) {
        const pageBreaks = this.calculatePageBreaks();
        for (let i = pageBreaks.length - 1; i >= 0; i--) {
            if (lineIndex >= pageBreaks[i]) {
                return i + 1;
            }
        }
        return 1;
    }

    /**
     * Get all scenes
     */
    getScenes() {
        const { LINE_TYPE } = window.CouriusConstants;
        const scenes = [];

        for (let i = 0; i < this.lines.length; i++) {
            const line = this.lines[i];
            if (line.type === LINE_TYPE.SCENE) {
                scenes.push({
                    index: i,
                    text: line.text,
                    page: this.getPageForLine(i)
                });
            }
        }

        return scenes;
    }

    /**
     * Get all characters
     */
    getCharacters() {
        const { LINE_TYPE } = window.CouriusConstants;
        const characters = new Map();

        for (let i = 0; i < this.lines.length; i++) {
            const line = this.lines[i];
            if (line.type === LINE_TYPE.CHARACTER) {
                const name = line.getCharacterName();
                if (name) {
                    if (!characters.has(name)) {
                        characters.set(name, {
                            name,
                            lineCount: 0,
                            dialogueLines: 0,
                            wordCount: 0,
                            scenes: new Set()
                        });
                    }

                    const char = characters.get(name);
                    char.lineCount++;

                    // Count dialogue lines following this character
                    let j = i + 1;
                    let currentScene = this._findPreviousScene(i);

                    while (j < this.lines.length) {
                        const nextLine = this.lines[j];
                        if (nextLine.type === LINE_TYPE.DIALOGUE ||
                            nextLine.type === LINE_TYPE.PAREN) {
                            char.dialogueLines++;
                            char.wordCount += window.CouriusUtils.countWords(nextLine.text);
                            j++;
                        } else {
                            break;
                        }
                    }

                    if (currentScene) {
                        char.scenes.add(currentScene);
                    }
                }
            }
        }

        return characters;
    }

    /**
     * Find the previous scene heading
     */
    _findPreviousScene(lineIndex) {
        const { LINE_TYPE } = window.CouriusConstants;
        for (let i = lineIndex - 1; i >= 0; i--) {
            if (this.lines[i].type === LINE_TYPE.SCENE) {
                return this.lines[i].text;
            }
        }
        return null;
    }

    /**
     * Get all locations
     */
    getLocations() {
        const scenes = this.getScenes();
        const locations = new Map();

        for (const scene of scenes) {
            // Parse location from scene heading
            const match = scene.text.match(/^(?:INT\.|EXT\.|INT\.\/EXT\.|I\/E\.)\s*(.+?)(?:\s*-\s*.+)?$/i);
            if (match) {
                const location = match[1].trim().toUpperCase();
                if (!locations.has(location)) {
                    locations.set(location, {
                        name: location,
                        scenes: []
                    });
                }
                locations.get(location).scenes.push(scene);
            }
        }

        return locations;
    }

    /**
     * Update auto-completion data from content
     */
    updateAutoCompletion() {
        const { LINE_TYPE } = window.CouriusConstants;

        // Clear existing (except defaults)
        this.autoCompletion.characters.clear();

        for (const line of this.lines) {
            switch (line.type) {
                case LINE_TYPE.SCENE:
                    // Extract scene prefix
                    const sceneMatch = line.text.match(/^(INT\.|EXT\.|INT\.\/EXT\.|I\/E\.)/i);
                    if (sceneMatch) {
                        this.autoCompletion.scenes.add(sceneMatch[1].toUpperCase());
                    }
                    break;

                case LINE_TYPE.CHARACTER:
                    const name = line.getCharacterName();
                    if (name) {
                        this.autoCompletion.characters.add(name);
                    }
                    break;

                case LINE_TYPE.TRANSITION:
                    if (line.text.trim()) {
                        this.autoCompletion.transitions.add(line.text.trim().toUpperCase());
                    }
                    break;

                case LINE_TYPE.SHOT:
                    if (line.text.trim()) {
                        this.autoCompletion.shots.add(line.text.trim().toUpperCase());
                    }
                    break;
            }
        }
    }

    /**
     * Get auto-completion suggestions for current context
     */
    getAutoCompletions(lineIndex, prefix) {
        const line = this.getLine(lineIndex);
        if (!line) return [];

        const { LINE_TYPE } = window.CouriusConstants;
        const upperPrefix = prefix.toUpperCase();
        let suggestions = [];

        switch (line.type) {
            case LINE_TYPE.SCENE:
                suggestions = Array.from(this.autoCompletion.scenes)
                    .filter(s => s.startsWith(upperPrefix));
                break;

            case LINE_TYPE.CHARACTER:
                suggestions = Array.from(this.autoCompletion.characters)
                    .filter(s => s.startsWith(upperPrefix));
                break;

            case LINE_TYPE.TRANSITION:
                suggestions = Array.from(this.autoCompletion.transitions)
                    .filter(s => s.startsWith(upperPrefix));
                break;

            case LINE_TYPE.SHOT:
                suggestions = Array.from(this.autoCompletion.shots)
                    .filter(s => s.startsWith(upperPrefix));
                break;
        }

        return suggestions.sort();
    }

    /**
     * Update line indices (for DOM sync)
     */
    _updateLineIndices() {
        // This is called after insertions/deletions
        // The actual index is just the array position
    }

    /**
     * Clone the screenplay
     */
    clone() {
        const copy = new Screenplay();
        copy.config = this.config.clone();
        copy.lines = this.lines.map(line => line.clone());
        copy.cursorLine = this.cursorLine;
        copy.cursorColumn = this.cursorColumn;
        copy.titlePages = window.CouriusUtils.deepClone(this.titlePages);
        copy.autoCompletion = {
            scenes: new Set(this.autoCompletion.scenes),
            characters: new Set(this.autoCompletion.characters),
            transitions: new Set(this.autoCompletion.transitions),
            shots: new Set(this.autoCompletion.shots)
        };
        copy.locations = new Map(this.locations);
        copy.headers = { ...this.headers };
        copy.metadata = { ...this.metadata };
        copy.modified = this.modified;
        return copy;
    }

    /**
     * Convert to JSON for serialization
     */
    toJSON() {
        return {
            version: window.CouriusConstants.VERSION.major,
            config: this.config.toJSON(),
            lines: this.lines.map(line => line.toJSON()),
            titlePages: this.titlePages,
            autoCompletion: {
                scenes: Array.from(this.autoCompletion.scenes),
                characters: Array.from(this.autoCompletion.characters),
                transitions: Array.from(this.autoCompletion.transitions),
                shots: Array.from(this.autoCompletion.shots)
            },
            headers: this.headers,
            metadata: this.metadata
        };
    }

    /**
     * Create from JSON
     */
    static fromJSON(json) {
        const sp = new Screenplay();
        const Line = window.CouriusLine;

        if (json.config) {
            sp.config = window.CouriusConfig.fromJSON(json.config);
        }

        if (json.lines && json.lines.length > 0) {
            sp.lines = json.lines.map(l => Line.fromJSON(l));
        }

        if (json.titlePages) {
            sp.titlePages = json.titlePages;
        }

        if (json.autoCompletion) {
            sp.autoCompletion.scenes = new Set(json.autoCompletion.scenes || []);
            sp.autoCompletion.characters = new Set(json.autoCompletion.characters || []);
            sp.autoCompletion.transitions = new Set(json.autoCompletion.transitions || []);
            sp.autoCompletion.shots = new Set(json.autoCompletion.shots || []);
        }

        if (json.headers) {
            sp.headers = json.headers;
        }

        if (json.metadata) {
            sp.metadata = json.metadata;
        }

        return sp;
    }

    /**
     * Convert to Trelby native file format
     */
    toTrelbyFormat() {
        const { FILE_MARKERS, VERSION } = window.CouriusConstants;
        const lines = [];

        // BOM and version
        lines.push(FILE_MARKERS.BOM + FILE_MARKERS.VERSION_PREFIX + VERSION.major);

        // Auto-completion sections
        for (const [key, set] of Object.entries(this.autoCompletion)) {
            const items = Array.from(set);
            lines.push(`${FILE_MARKERS.BEGIN_PREFIX}Auto-Completion/${key.charAt(0).toUpperCase() + key.slice(1)}`);
            lines.push(`  Enabled:True`);
            lines.push(`  Items:${items.length}`);
            items.forEach((item, i) => {
                lines.push(`  Items/${i + 1}:${item}`);
            });
            lines.push(`${FILE_MARKERS.END_PREFIX}Auto-Completion/${key.charAt(0).toUpperCase() + key.slice(1)}`);
        }

        // Headers
        lines.push(`${FILE_MARKERS.BEGIN_PREFIX}Headers`);
        lines.push(`  First-Page:${this.headers.firstPage}`);
        lines.push(`  Other-Pages:${this.headers.otherPages}`);
        lines.push(`  Show-On-First:${this.headers.showOnFirst}`);
        lines.push(`${FILE_MARKERS.END_PREFIX}Headers`);

        // Script content
        lines.push(FILE_MARKERS.SCRIPT_START);
        for (const line of this.lines) {
            lines.push(line.toTrelbyFormat());
        }

        return lines.join('\n');
    }

    /**
     * Parse from Trelby native file format
     */
    static fromTrelbyFormat(content) {
        const { FILE_MARKERS, LB, LINE_TYPE } = window.CouriusConstants;
        const Line = window.CouriusLine;
        const sp = new Screenplay();

        const lines = content.split('\n');
        let inScript = false;
        let currentSection = null;
        let sectionData = {};

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i];

            // Remove BOM if present
            if (line.startsWith(FILE_MARKERS.BOM)) {
                line = line.substring(1);
            }

            // Version line
            if (line.startsWith(FILE_MARKERS.VERSION_PREFIX)) {
                continue;
            }

            // Script content
            if (line === FILE_MARKERS.SCRIPT_START) {
                inScript = true;
                sp.lines = []; // Clear default line
                continue;
            }

            if (inScript) {
                if (line.length >= 2) {
                    sp.lines.push(Line.fromTrelbyFormat(line));
                } else if (line.length === 0 && sp.lines.length > 0) {
                    // Empty line - might be intentional
                    sp.lines.push(new Line(LB.LAST, LINE_TYPE.ACTION, ''));
                }
                continue;
            }

            // Section begin
            if (line.startsWith(FILE_MARKERS.BEGIN_PREFIX)) {
                currentSection = line.substring(FILE_MARKERS.BEGIN_PREFIX.length);
                sectionData = {};
                continue;
            }

            // Section end
            if (line.startsWith(FILE_MARKERS.END_PREFIX)) {
                // Process collected section data
                if (currentSection?.startsWith('Auto-Completion/')) {
                    const type = currentSection.split('/')[1].toLowerCase();
                    if (sp.autoCompletion[type]) {
                        for (const key in sectionData) {
                            if (key.startsWith('Items/')) {
                                sp.autoCompletion[type].add(sectionData[key]);
                            }
                        }
                    }
                } else if (currentSection === 'Headers') {
                    sp.headers.firstPage = sectionData['First-Page'] || '';
                    sp.headers.otherPages = sectionData['Other-Pages'] || '%p.';
                    sp.headers.showOnFirst = sectionData['Show-On-First'] === 'True';
                }
                currentSection = null;
                continue;
            }

            // Section content
            if (currentSection && line.trim().includes(':')) {
                const colonIndex = line.indexOf(':');
                const key = line.substring(0, colonIndex).trim();
                const value = line.substring(colonIndex + 1);
                sectionData[key] = value;
            }
        }

        // Ensure at least one line
        if (sp.lines.length === 0) {
            sp.lines.push(new Line(LB.LAST, LINE_TYPE.ACTION, ''));
        }

        sp.updateAutoCompletion();
        return sp;
    }
}

window.CouriusScreenplay = Screenplay;
