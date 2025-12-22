/**
 * Courius - File I/O Operations
 * Handles loading and saving screenplays in various formats
 */

class FileIO {
    constructor() {
        this.currentFilename = 'Untitled.trelby';
        this.currentHandle = null; // For File System Access API
    }

    /**
     * Create a new screenplay
     */
    createNew() {
        const screenplay = new window.CouriusScreenplay();
        this.currentFilename = 'Untitled.trelby';
        this.currentHandle = null;
        return screenplay;
    }

    /**
     * Open a file dialog and load a screenplay
     */
    async open() {
        // Try modern File System Access API first
        if ('showOpenFilePicker' in window) {
            try {
                const [handle] = await window.showOpenFilePicker({
                    types: [
                        {
                            description: 'Trelby Screenplay',
                            accept: { 'application/x-trelby': ['.trelby'] }
                        },
                        {
                            description: 'Final Draft',
                            accept: { 'application/xml': ['.fdx'] }
                        },
                        {
                            description: 'Fountain',
                            accept: { 'text/plain': ['.fountain', '.txt'] }
                        },
                        {
                            description: 'All Files',
                            accept: { '*/*': ['*'] }
                        }
                    ]
                });

                const file = await handle.getFile();
                const content = await file.text();

                this.currentFilename = file.name;
                this.currentHandle = handle;

                return this.parseFile(content, file.name);
            } catch (e) {
                if (e.name === 'AbortError') return null;
                console.error('File open error:', e);
            }
        }

        // Fallback to file input
        const file = await window.CouriusUtils.pickFile('.trelby,.fdx,.fountain,.txt');
        if (!file) return null;

        const content = await window.CouriusUtils.readFile(file);
        this.currentFilename = file.name;
        this.currentHandle = null;

        return this.parseFile(content, file.name);
    }

    /**
     * Parse file content based on extension
     */
    parseFile(content, filename) {
        const ext = filename.split('.').pop().toLowerCase();

        switch (ext) {
            case 'trelby':
                return this.parseTrelby(content);
            case 'fdx':
                return this.parseFDX(content);
            case 'fountain':
                return this.parseFountain(content);
            case 'txt':
                return this.parseText(content);
            default:
                // Try to detect format
                if (content.includes('#Version')) {
                    return this.parseTrelby(content);
                } else if (content.includes('<?xml') && content.includes('FinalDraft')) {
                    return this.parseFDX(content);
                } else {
                    return this.parseFountain(content);
                }
        }
    }

    /**
     * Parse Trelby native format
     */
    parseTrelby(content) {
        return window.CouriusScreenplay.fromTrelbyFormat(content);
    }

    /**
     * Parse Final Draft XML format
     */
    parseFDX(content) {
        const { LINE_TYPE, LB } = window.CouriusConstants;
        const Line = window.CouriusLine;
        const screenplay = new window.CouriusScreenplay();
        screenplay.lines = [];

        try {
            const parser = new DOMParser();
            const doc = parser.parseFromString(content, 'text/xml');

            // Map FDX element types to Trelby types
            const typeMap = {
                'Scene Heading': LINE_TYPE.SCENE,
                'Action': LINE_TYPE.ACTION,
                'Character': LINE_TYPE.CHARACTER,
                'Dialogue': LINE_TYPE.DIALOGUE,
                'Parenthetical': LINE_TYPE.PAREN,
                'Transition': LINE_TYPE.TRANSITION,
                'Shot': LINE_TYPE.SHOT,
                'General': LINE_TYPE.ACTION
            };

            const paragraphs = doc.querySelectorAll('Paragraph');

            for (const para of paragraphs) {
                const typeAttr = para.getAttribute('Type') || 'Action';
                const lineType = typeMap[typeAttr] || LINE_TYPE.ACTION;

                // Get text from all Text elements
                const textElements = para.querySelectorAll('Text');
                let text = '';
                for (const textEl of textElements) {
                    text += textEl.textContent || '';
                }

                if (text || screenplay.lines.length === 0) {
                    screenplay.lines.push(new Line(LB.LAST, lineType, text.trim()));
                }
            }

            // Ensure at least one line
            if (screenplay.lines.length === 0) {
                screenplay.lines.push(new Line(LB.LAST, LINE_TYPE.ACTION, ''));
            }

            screenplay.updateAutoCompletion();
            return screenplay;
        } catch (e) {
            console.error('FDX parse error:', e);
            throw new Error('Failed to parse Final Draft file');
        }
    }

    /**
     * Parse Fountain format
     */
    parseFountain(content) {
        const { LINE_TYPE, LB } = window.CouriusConstants;
        const Line = window.CouriusLine;
        const screenplay = new window.CouriusScreenplay();
        screenplay.lines = [];

        const lines = content.split('\n');
        let i = 0;

        // Skip title page if present
        if (lines[0] && lines[0].includes(':')) {
            while (i < lines.length && lines[i].trim() !== '') {
                i++;
            }
            i++; // Skip blank line after title page
        }

        while (i < lines.length) {
            let line = lines[i];
            let lineType = LINE_TYPE.ACTION;
            let text = line;

            // Scene heading (INT./EXT. or forced with .)
            if (/^(INT|EXT|EST|INT\.?\/EXT|I\/E)[\.\s]/i.test(line) ||
                (line.startsWith('.') && line.length > 1 && line[1] !== '.')) {
                lineType = LINE_TYPE.SCENE;
                text = line.startsWith('.') ? line.substring(1) : line;
            }
            // Character (all caps, may have extension)
            else if (/^[A-Z][A-Z0-9 ]*(\s*\([^)]+\))?$/.test(line.trim()) &&
                line.trim().length > 0 &&
                !line.startsWith(' ') &&
                !line.startsWith('\t')) {
                // Check if next line is dialogue
                if (i + 1 < lines.length && lines[i + 1].trim() !== '') {
                    lineType = LINE_TYPE.CHARACTER;
                    text = line;
                }
            }
            // Forced character with @
            else if (line.startsWith('@')) {
                lineType = LINE_TYPE.CHARACTER;
                text = line.substring(1);
            }
            // Parenthetical
            else if (line.trim().startsWith('(') && line.trim().endsWith(')')) {
                lineType = LINE_TYPE.PAREN;
                text = line.trim().slice(1, -1);
            }
            // Transition (ends with TO: or forced with >)
            else if (/TO:$/.test(line.trim()) || line.startsWith('>')) {
                lineType = LINE_TYPE.TRANSITION;
                text = line.startsWith('>') ? line.substring(1).trim() : line.trim();
            }
            // Centered text (for act breaks)
            else if (line.startsWith('>') && line.endsWith('<')) {
                lineType = LINE_TYPE.ACTBREAK;
                text = line.slice(1, -1).trim();
            }
            // Note/Boneyard
            else if (line.startsWith('[[') && line.endsWith(']]')) {
                lineType = LINE_TYPE.NOTE;
                text = line.slice(2, -2).trim();
            }
            // Check if this follows a character (dialogue)
            else if (screenplay.lines.length > 0) {
                const lastLine = screenplay.lines[screenplay.lines.length - 1];
                if ((lastLine.type === LINE_TYPE.CHARACTER ||
                    lastLine.type === LINE_TYPE.DIALOGUE ||
                    lastLine.type === LINE_TYPE.PAREN) &&
                    line.trim() !== '') {
                    lineType = LINE_TYPE.DIALOGUE;
                }
            }

            // Skip empty lines but preserve structure
            if (line.trim() === '' && screenplay.lines.length > 0) {
                // Empty line ends current element
                const lastLine = screenplay.lines[screenplay.lines.length - 1];
                lastLine.lb = LB.LAST;
            } else if (line.trim() !== '' || screenplay.lines.length === 0) {
                screenplay.lines.push(new Line(LB.LAST, lineType, text.trim()));
            }

            i++;
        }

        // Ensure at least one line
        if (screenplay.lines.length === 0) {
            screenplay.lines.push(new Line(LB.LAST, LINE_TYPE.ACTION, ''));
        }

        screenplay.updateAutoCompletion();
        return screenplay;
    }

    /**
     * Parse plain text (basic formatting detection)
     */
    parseText(content) {
        // Use Fountain parser as it handles plain text reasonably well
        return this.parseFountain(content);
    }

    /**
     * Save screenplay to file
     */
    async save(screenplay, format = 'trelby') {
        const content = this.generateContent(screenplay, format);
        const ext = this.getExtension(format);

        // Try File System Access API first
        if (this.currentHandle && 'createWritable' in this.currentHandle) {
            try {
                const writable = await this.currentHandle.createWritable();
                await writable.write(content);
                await writable.close();
                screenplay.clearModified();
                return true;
            } catch (e) {
                console.error('Save error:', e);
            }
        }

        // Fall back to download
        return this.saveAs(screenplay, format);
    }

    /**
     * Save screenplay with new filename
     */
    async saveAs(screenplay, format = 'trelby') {
        const content = this.generateContent(screenplay, format);
        const ext = this.getExtension(format);
        const filename = this.currentFilename.replace(/\.[^.]+$/, '') + ext;

        // Try File System Access API
        if ('showSaveFilePicker' in window) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: filename,
                    types: [
                        {
                            description: this.getFormatDescription(format),
                            accept: { [this.getMimeType(format)]: [ext] }
                        }
                    ]
                });

                const writable = await handle.createWritable();
                await writable.write(content);
                await writable.close();

                this.currentHandle = handle;
                this.currentFilename = handle.name;
                screenplay.clearModified();
                return true;
            } catch (e) {
                if (e.name === 'AbortError') return false;
                console.error('Save error:', e);
            }
        }

        // Fall back to download
        window.CouriusUtils.downloadFile(content, filename, this.getMimeType(format));
        screenplay.clearModified();
        return true;
    }

    /**
     * Generate file content in specified format
     */
    generateContent(screenplay, format) {
        switch (format) {
            case 'trelby':
                return screenplay.toTrelbyFormat();
            case 'json':
                return JSON.stringify(screenplay.toJSON(), null, 2);
            default:
                return screenplay.toTrelbyFormat();
        }
    }

    /**
     * Get file extension for format
     */
    getExtension(format) {
        const extensions = {
            'trelby': '.trelby',
            'json': '.json',
            'fdx': '.fdx',
            'fountain': '.fountain',
            'txt': '.txt',
            'html': '.html',
            'pdf': '.pdf',
            'rtf': '.rtf'
        };
        return extensions[format] || '.txt';
    }

    /**
     * Get MIME type for format
     */
    getMimeType(format) {
        const mimeTypes = {
            'trelby': 'application/x-trelby',
            'json': 'application/json',
            'fdx': 'application/xml',
            'fountain': 'text/plain',
            'txt': 'text/plain',
            'html': 'text/html',
            'pdf': 'application/pdf',
            'rtf': 'application/rtf'
        };
        return mimeTypes[format] || 'text/plain';
    }

    /**
     * Get format description
     */
    getFormatDescription(format) {
        const descriptions = {
            'trelby': 'Trelby Screenplay',
            'json': 'JSON',
            'fdx': 'Final Draft XML',
            'fountain': 'Fountain',
            'txt': 'Plain Text',
            'html': 'HTML',
            'pdf': 'PDF Document',
            'rtf': 'Rich Text Format'
        };
        return descriptions[format] || 'Text File';
    }

    /**
     * Check if file has unsaved changes
     */
    hasUnsavedChanges(screenplay) {
        return screenplay.modified;
    }

    /**
     * Get current filename
     */
    getFilename() {
        return this.currentFilename;
    }

    /**
     * Set current filename
     */
    setFilename(filename) {
        this.currentFilename = filename;
    }

    /**
     * Auto-save to localStorage
     */
    autoSave(screenplay) {
        try {
            const key = 'courius-autosave';
            const data = {
                content: screenplay.toJSON(),
                filename: this.currentFilename,
                timestamp: Date.now()
            };
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (e) {
            console.warn('Auto-save failed:', e);
            return false;
        }
    }

    /**
     * Load auto-saved screenplay
     */
    loadAutoSave() {
        try {
            const key = 'courius-autosave';
            const data = localStorage.getItem(key);
            if (data) {
                const parsed = JSON.parse(data);
                const screenplay = window.CouriusScreenplay.fromJSON(parsed.content);
                this.currentFilename = parsed.filename || 'Recovered.trelby';
                return {
                    screenplay,
                    timestamp: parsed.timestamp
                };
            }
        } catch (e) {
            console.warn('Failed to load auto-save:', e);
        }
        return null;
    }

    /**
     * Clear auto-save
     */
    clearAutoSave() {
        localStorage.removeItem('courius-autosave');
    }

    /**
     * Check if auto-save exists
     */
    hasAutoSave() {
        return localStorage.getItem('courius-autosave') !== null;
    }
}

window.CouriusFileIO = FileIO;
