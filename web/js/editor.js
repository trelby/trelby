/**
 * Trelby Web - Screenplay Editor
 * Main editor component handling all text editing operations
 */

class ScreenplayEditor {
    constructor(containerSelector) {
        this.container = document.querySelector(containerSelector);
        this.editorElement = document.getElementById('screenplay-editor');
        this.elementTypeSelect = document.getElementById('element-type');
        this.layoutView = document.getElementById('layout-view');

        // Core state
        this.screenplay = new window.TrelbyScreenplay();
        this.undoManager = new window.TrelbyUndoManager();
        this.autoCompletion = new window.TrelbyAutoCompletion();
        this.spellChecker = new window.TrelbySpellChecker();

        // View state
        this.viewMode = 'draft'; // 'draft', 'layout', 'sidebyside'
        this.zoom = 1.0;

        // Find state
        this.findQuery = '';
        this.findOptions = {};
        this.findMatches = [];
        this.currentMatchIndex = -1;

        // Callbacks
        this.onModified = null;
        this.onCursorChange = null;

        // Initialize
        this._bindEvents();
        this._render();
        this._saveUndoState('Initial state');
    }

    /**
     * Bind all event listeners
     */
    _bindEvents() {
        // Editor input events
        this.editorElement.addEventListener('input', (e) => this._handleInput(e));
        this.editorElement.addEventListener('keydown', (e) => this._handleKeyDown(e));
        this.editorElement.addEventListener('click', (e) => this._handleClick(e));
        this.editorElement.addEventListener('paste', (e) => this._handlePaste(e));

        // Element type selector
        this.elementTypeSelect.addEventListener('change', (e) => {
            const lineIndex = this._getCurrentLineIndex();
            if (lineIndex >= 0) {
                this.setLineType(lineIndex, e.target.value);
            }
        });

        // Selection change for cursor position updates
        document.addEventListener('selectionchange', () => {
            this._updateCursorInfo();
            this._checkAutoCompletion();
        });
    }

    /**
     * Handle text input
     */
    _handleInput(e) {
        const lineIndex = this._getCurrentLineIndex();
        if (lineIndex < 0) return;

        // Get text from DOM
        const lineElement = this._getLineElement(lineIndex);
        if (!lineElement) return;

        const text = lineElement.textContent || '';
        this.screenplay.setLineText(lineIndex, text);

        this._saveUndoState('Typing');
        this._notifyModified();
        this._updateLayoutView();
    }

    /**
     * Handle keyboard shortcuts and special keys
     */
    _handleKeyDown(e) {
        const { LINE_TYPE, TAB_CYCLE, ELEMENT_NEXT } = window.TrelbyConstants;

        // Handle auto-completion navigation first
        if (this.autoCompletion.visible) {
            if (['ArrowUp', 'ArrowDown', 'Enter', 'Tab', 'Escape'].includes(e.key)) {
                return; // Let auto-completion handle it
            }
        }

        // Element type shortcuts (Ctrl+1-8)
        if (e.ctrlKey && !e.shiftKey && !e.altKey) {
            const typeMap = {
                '1': LINE_TYPE.SCENE,
                '2': LINE_TYPE.ACTION,
                '3': LINE_TYPE.CHARACTER,
                '4': LINE_TYPE.DIALOGUE,
                '5': LINE_TYPE.PAREN,
                '6': LINE_TYPE.TRANSITION,
                '7': LINE_TYPE.SHOT,
                '8': LINE_TYPE.NOTE
            };

            if (typeMap[e.key]) {
                e.preventDefault();
                const lineIndex = this._getCurrentLineIndex();
                if (lineIndex >= 0) {
                    this.setLineType(lineIndex, typeMap[e.key]);
                }
                return;
            }
        }

        // Tab - cycle element types
        if (e.key === 'Tab' && !e.ctrlKey && !this.autoCompletion.visible) {
            e.preventDefault();
            const lineIndex = this._getCurrentLineIndex();
            if (lineIndex >= 0) {
                const currentType = this.screenplay.getLineType(lineIndex);
                const currentIndex = TAB_CYCLE.indexOf(currentType);

                let nextIndex;
                if (e.shiftKey) {
                    nextIndex = currentIndex <= 0 ? TAB_CYCLE.length - 1 : currentIndex - 1;
                } else {
                    nextIndex = (currentIndex + 1) % TAB_CYCLE.length;
                }

                this.setLineType(lineIndex, TAB_CYCLE[nextIndex]);
            }
            return;
        }

        // Enter - smart line break
        if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) {
            e.preventDefault();
            this._handleEnter();
            return;
        }

        // Ctrl+Enter - force page break
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            this._insertPageBreak();
            return;
        }

        // Backspace at start of line - merge with previous
        if (e.key === 'Backspace') {
            const { line, offset } = window.TrelbyUtils.getCaretPosition(this.editorElement);
            if (offset === 0 && line > 0) {
                e.preventDefault();
                this._mergeLinesUp(line);
                return;
            }
        }

        // Delete at end of line - merge with next
        if (e.key === 'Delete') {
            const lineIndex = this._getCurrentLineIndex();
            const lineElement = this._getLineElement(lineIndex);
            if (lineElement) {
                const text = this.screenplay.getLineText(lineIndex);
                const { offset } = window.TrelbyUtils.getCaretPosition(this.editorElement);
                if (offset >= text.length && lineIndex < this.screenplay.lineCount - 1) {
                    e.preventDefault();
                    this._mergeLinesDown(lineIndex);
                    return;
                }
            }
        }
    }

    /**
     * Handle Enter key - smart line break
     */
    _handleEnter() {
        const { LINE_TYPE, ELEMENT_NEXT, LB } = window.TrelbyConstants;
        const Line = window.TrelbyLine;

        const lineIndex = this._getCurrentLineIndex();
        if (lineIndex < 0) return;

        const currentLine = this.screenplay.getLine(lineIndex);
        const { offset } = window.TrelbyUtils.getCaretPosition(this.editorElement);
        const text = currentLine.text;

        // Get the next element type
        const nextType = ELEMENT_NEXT[currentLine.type] || LINE_TYPE.ACTION;

        // If cursor is at end of line
        if (offset >= text.length) {
            // If line is empty and type is action, stay as action
            if (text.trim() === '' && currentLine.type === LINE_TYPE.ACTION) {
                return;
            }

            // Create new line with appropriate type
            const newLine = new Line(LB.LAST, nextType, '');
            this.screenplay.insertLine(lineIndex + 1, newLine);
            this._render();
            this._focusLine(lineIndex + 1, 0);
        } else {
            // Split the line at cursor
            const beforeText = text.substring(0, offset);
            const afterText = text.substring(offset);

            currentLine.text = beforeText;
            const newLine = new Line(LB.LAST, currentLine.type, afterText);
            this.screenplay.insertLine(lineIndex + 1, newLine);

            this._render();
            this._focusLine(lineIndex + 1, 0);
        }

        this._saveUndoState('Insert line');
        this._notifyModified();
    }

    /**
     * Handle click event
     */
    _handleClick(e) {
        // Update element type selector
        setTimeout(() => {
            const lineIndex = this._getCurrentLineIndex();
            if (lineIndex >= 0) {
                const type = this.screenplay.getLineType(lineIndex);
                this.elementTypeSelect.value = type;
            }
        }, 0);
    }

    /**
     * Handle paste event
     */
    _handlePaste(e) {
        e.preventDefault();

        const text = e.clipboardData.getData('text/plain');
        if (!text) return;

        // Insert text at cursor
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.deleteContents();

            // Split into lines and insert
            const lines = text.split('\n');
            const lineIndex = this._getCurrentLineIndex();

            if (lines.length === 1) {
                // Single line - just insert
                const textNode = document.createTextNode(lines[0]);
                range.insertNode(textNode);
                range.setStartAfter(textNode);
                range.collapse(true);
                selection.removeAllRanges();
                selection.addRange(range);

                // Update screenplay
                const lineElement = this._getLineElement(lineIndex);
                this.screenplay.setLineText(lineIndex, lineElement.textContent);
            } else {
                // Multiple lines - insert multiple lines
                const { LB, LINE_TYPE } = window.TrelbyConstants;
                const Line = window.TrelbyLine;
                const currentType = this.screenplay.getLineType(lineIndex);

                // Insert first line at cursor
                const firstLine = lines[0];
                const textNode = document.createTextNode(firstLine);
                range.insertNode(textNode);

                // Insert remaining lines
                for (let i = 1; i < lines.length; i++) {
                    const newLine = new Line(LB.LAST, currentType, lines[i]);
                    this.screenplay.insertLine(lineIndex + i, newLine);
                }

                this._render();
                this._focusLine(lineIndex + lines.length - 1, lines[lines.length - 1].length);
            }
        }

        this._saveUndoState('Paste');
        this._notifyModified();
    }

    /**
     * Merge current line with previous
     */
    _mergeLinesUp(lineIndex) {
        if (lineIndex <= 0) return;

        const prevLine = this.screenplay.getLine(lineIndex - 1);
        const currentLine = this.screenplay.getLine(lineIndex);

        const cursorPos = prevLine.text.length;
        prevLine.text += currentLine.text;
        this.screenplay.deleteLine(lineIndex);

        this._render();
        this._focusLine(lineIndex - 1, cursorPos);
        this._saveUndoState('Merge lines');
        this._notifyModified();
    }

    /**
     * Merge current line with next
     */
    _mergeLinesDown(lineIndex) {
        if (lineIndex >= this.screenplay.lineCount - 1) return;

        const currentLine = this.screenplay.getLine(lineIndex);
        const nextLine = this.screenplay.getLine(lineIndex + 1);

        const cursorPos = currentLine.text.length;
        currentLine.text += nextLine.text;
        this.screenplay.deleteLine(lineIndex + 1);

        this._render();
        this._focusLine(lineIndex, cursorPos);
        this._saveUndoState('Merge lines');
        this._notifyModified();
    }

    /**
     * Insert a page break marker
     */
    _insertPageBreak() {
        const lineIndex = this._getCurrentLineIndex();
        if (lineIndex < 0) return;

        const lineElement = this._getLineElement(lineIndex);
        if (lineElement) {
            lineElement.classList.add('page-break');
            lineElement.dataset.page = String(this.screenplay.getPageForLine(lineIndex));
        }
    }

    /**
     * Set line type
     */
    setLineType(lineIndex, type) {
        this.screenplay.setLineType(lineIndex, type);
        this.elementTypeSelect.value = type;

        // Update DOM
        const lineElement = this._getLineElement(lineIndex);
        if (lineElement) {
            // Remove all type classes
            for (const t of Object.values(window.TrelbyConstants.LINE_TYPE)) {
                lineElement.classList.remove(t);
            }
            lineElement.classList.add(type);
            lineElement.dataset.type = type;
        }

        this._saveUndoState('Change element type');
        this._notifyModified();
        this._updateLayoutView();
    }

    /**
     * Get current line index from cursor position
     */
    _getCurrentLineIndex() {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return -1;

        let node = selection.anchorNode;
        while (node && !node.classList?.contains('line')) {
            node = node.parentElement;
        }

        if (node && node.dataset.line !== undefined) {
            return parseInt(node.dataset.line, 10);
        }

        return -1;
    }

    /**
     * Get line DOM element by index
     */
    _getLineElement(index) {
        return this.editorElement.querySelector(`[data-line="${index}"]`);
    }

    /**
     * Render the entire screenplay to DOM
     */
    _render() {
        this.editorElement.innerHTML = '';

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            const lineElement = this._createLineElement(i, line);
            this.editorElement.appendChild(lineElement);
        }

        this._updateLayoutView();
        this._updateStatusBar();
    }

    /**
     * Create a line DOM element
     */
    _createLineElement(index, line) {
        const div = document.createElement('div');
        div.className = `line ${line.type}`;
        div.dataset.line = index;
        div.dataset.type = line.type;
        div.textContent = line.text;
        div.contentEditable = 'true';

        // Add page break indicator if needed
        const pageBreaks = this.screenplay.calculatePageBreaks();
        if (pageBreaks.includes(index) && index > 0) {
            div.classList.add('page-break');
            div.dataset.page = String(pageBreaks.indexOf(index) + 1);
        }

        return div;
    }

    /**
     * Refresh a single line's display
     */
    refreshLine(index) {
        const line = this.screenplay.getLine(index);
        const lineElement = this._getLineElement(index);

        if (lineElement && line) {
            // Update class
            for (const t of Object.values(window.TrelbyConstants.LINE_TYPE)) {
                lineElement.classList.remove(t);
            }
            lineElement.classList.add(line.type);
            lineElement.dataset.type = line.type;
        }
    }

    /**
     * Focus on a specific line and position
     */
    _focusLine(lineIndex, offset = 0) {
        const lineElement = this._getLineElement(lineIndex);
        if (!lineElement) return;

        lineElement.focus();

        // Set cursor position
        const range = document.createRange();
        const selection = window.getSelection();

        if (lineElement.childNodes.length > 0) {
            const textNode = lineElement.childNodes[0];
            const pos = Math.min(offset, textNode.length || 0);
            range.setStart(textNode, pos);
        } else {
            range.setStart(lineElement, 0);
        }

        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
    }

    /**
     * Update cursor info in status bar
     */
    _updateCursorInfo() {
        const { line, offset } = window.TrelbyUtils.getCaretPosition(this.editorElement);
        const page = this.screenplay.getPageForLine(line);

        document.getElementById('page-info').textContent = `Page ${page}`;
        document.getElementById('line-info').textContent = `Line ${line + 1}`;
        document.getElementById('col-info').textContent = `Col ${offset + 1}`;

        // Update element type selector
        if (line >= 0) {
            const type = this.screenplay.getLineType(line);
            if (type) {
                this.elementTypeSelect.value = type;
            }
        }

        if (this.onCursorChange) {
            this.onCursorChange(line, offset, page);
        }
    }

    /**
     * Update status bar with word/page counts
     */
    _updateStatusBar() {
        const words = this.screenplay.getWordCount();
        const pages = this.screenplay.getPageCount();

        document.getElementById('status-wordcount').textContent = `Words: ${words}`;
        document.getElementById('status-pagecount').textContent = `Pages: ${pages}`;
    }

    /**
     * Check and show auto-completion if appropriate
     */
    _checkAutoCompletion() {
        const lineIndex = this._getCurrentLineIndex();
        if (lineIndex < 0) return;

        const line = this.screenplay.getLine(lineIndex);
        const { offset } = window.TrelbyUtils.getCaretPosition(this.editorElement);

        if (this.autoCompletion.shouldTrigger(line.type, line.text, offset)) {
            const prefix = this.autoCompletion.getPrefix(line.text, offset);
            const suggestions = this.screenplay.getAutoCompletions(lineIndex, prefix);

            if (suggestions.length > 0) {
                const lineElement = this._getLineElement(lineIndex);
                this.autoCompletion.show(suggestions, prefix, lineElement, (selected, prefix) => {
                    // Replace text with selected suggestion
                    const newText = selected + line.text.substring(offset);
                    this.screenplay.setLineText(lineIndex, newText);

                    // Re-render and position cursor
                    const lineEl = this._getLineElement(lineIndex);
                    if (lineEl) {
                        lineEl.textContent = newText;
                        this._focusLine(lineIndex, selected.length);
                    }

                    this._saveUndoState('Auto-complete');
                    this._notifyModified();
                });
            } else {
                this.autoCompletion.hide();
            }
        } else {
            this.autoCompletion.hide();
        }
    }

    /**
     * Update the layout view (page preview)
     */
    _updateLayoutView() {
        if (this.viewMode === 'draft') return;

        const pageContainer = document.getElementById('page-container');
        if (!pageContainer) return;

        pageContainer.innerHTML = '';

        const pageBreaks = this.screenplay.calculatePageBreaks();
        const { LINE_TYPE } = window.TrelbyConstants;

        for (let p = 0; p < pageBreaks.length; p++) {
            const startLine = pageBreaks[p];
            const endLine = p < pageBreaks.length - 1 ? pageBreaks[p + 1] : this.screenplay.lineCount;

            const page = document.createElement('div');
            page.className = 'page';
            page.dataset.page = p + 1;

            const pageContent = document.createElement('div');
            pageContent.className = 'page-content';

            for (let i = startLine; i < endLine; i++) {
                const line = this.screenplay.getLine(i);
                const lineDiv = document.createElement('div');
                lineDiv.className = line.type;

                let text = line.text;
                if (line.type === LINE_TYPE.PAREN) {
                    text = `(${text})`;
                }

                lineDiv.textContent = text;
                pageContent.appendChild(lineDiv);
            }

            const pageNumber = document.createElement('div');
            pageNumber.className = 'page-number';
            pageNumber.textContent = String(p + 1);

            page.appendChild(pageContent);
            page.appendChild(pageNumber);
            pageContainer.appendChild(page);
        }
    }

    /**
     * Set view mode
     */
    setViewMode(mode) {
        this.viewMode = mode;
        const container = document.getElementById('editor-container');

        container.classList.remove('view-draft', 'view-layout', 'view-sidebyside');
        container.classList.add(`view-${mode}`);

        if (mode !== 'draft') {
            this._updateLayoutView();
        }

        // Update toolbar buttons
        document.querySelectorAll('.view-modes .toolbar-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-action="view${mode.charAt(0).toUpperCase() + mode.slice(1)}"]`)?.classList.add('active');
    }

    /**
     * Save undo state
     */
    _saveUndoState(description) {
        const state = new window.TrelbyScreenplayUndoState(
            this.screenplay,
            this._getCurrentLineIndex(),
            window.TrelbyUtils.getCaretPosition(this.editorElement).offset,
            description
        );
        this.undoManager.push(state.toJSON(), description);
    }

    /**
     * Undo last action
     */
    undo() {
        const state = this.undoManager.undo();
        if (state) {
            this._restoreState(state);
        }
    }

    /**
     * Redo last undone action
     */
    redo() {
        const state = this.undoManager.redo();
        if (state) {
            this._restoreState(state);
        }
    }

    /**
     * Restore editor state
     */
    _restoreState(state) {
        const undoState = window.TrelbyScreenplayUndoState.fromJSON(state);
        undoState.apply(this.screenplay);

        this._render();
        this._focusLine(state.cursorLine, state.cursorColumn);
        this._notifyModified();
    }

    /**
     * Notify that screenplay was modified
     */
    _notifyModified() {
        this.screenplay.markModified();
        document.getElementById('status-modified').textContent = 'Modified';

        if (this.onModified) {
            this.onModified();
        }
    }

    /**
     * Find text in screenplay
     */
    find(query, options = {}) {
        this.findQuery = query;
        this.findOptions = options;
        this.findMatches = [];
        this.currentMatchIndex = -1;

        if (!query) return [];

        const { matchCase, wholeWord, regex } = options;

        let pattern;
        if (regex) {
            try {
                pattern = new RegExp(query, matchCase ? 'g' : 'gi');
            } catch (e) {
                console.error('Invalid regex:', e);
                return [];
            }
        } else {
            let escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            if (wholeWord) {
                escaped = `\\b${escaped}\\b`;
            }
            pattern = new RegExp(escaped, matchCase ? 'g' : 'gi');
        }

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const text = this.screenplay.getLineText(i);
            let match;

            while ((match = pattern.exec(text)) !== null) {
                this.findMatches.push({
                    line: i,
                    start: match.index,
                    end: match.index + match[0].length,
                    text: match[0]
                });
            }
        }

        return this.findMatches;
    }

    /**
     * Find next match
     */
    findNext() {
        if (this.findMatches.length === 0) return null;

        this.currentMatchIndex = (this.currentMatchIndex + 1) % this.findMatches.length;
        const match = this.findMatches[this.currentMatchIndex];

        this._focusLine(match.line, match.start);
        this._selectRange(match.line, match.start, match.end);

        return match;
    }

    /**
     * Find previous match
     */
    findPrevious() {
        if (this.findMatches.length === 0) return null;

        this.currentMatchIndex = (this.currentMatchIndex - 1 + this.findMatches.length) % this.findMatches.length;
        const match = this.findMatches[this.currentMatchIndex];

        this._focusLine(match.line, match.start);
        this._selectRange(match.line, match.start, match.end);

        return match;
    }

    /**
     * Replace current match
     */
    replace(replacement) {
        if (this.currentMatchIndex < 0 || this.currentMatchIndex >= this.findMatches.length) {
            return false;
        }

        const match = this.findMatches[this.currentMatchIndex];
        const text = this.screenplay.getLineText(match.line);
        const newText = text.substring(0, match.start) + replacement + text.substring(match.end);

        this.screenplay.setLineText(match.line, newText);
        this.refreshLine(match.line);

        // Update match positions
        const lengthDiff = replacement.length - (match.end - match.start);
        for (let i = this.currentMatchIndex + 1; i < this.findMatches.length; i++) {
            if (this.findMatches[i].line === match.line) {
                this.findMatches[i].start += lengthDiff;
                this.findMatches[i].end += lengthDiff;
            }
        }

        // Remove current match from list
        this.findMatches.splice(this.currentMatchIndex, 1);
        if (this.currentMatchIndex >= this.findMatches.length) {
            this.currentMatchIndex = 0;
        }

        this._render();
        this._saveUndoState('Replace');
        this._notifyModified();

        return true;
    }

    /**
     * Replace all matches
     */
    replaceAll(replacement) {
        if (this.findMatches.length === 0) return 0;

        let count = 0;

        // Process from end to avoid position shifts
        for (let i = this.findMatches.length - 1; i >= 0; i--) {
            const match = this.findMatches[i];
            const text = this.screenplay.getLineText(match.line);
            const newText = text.substring(0, match.start) + replacement + text.substring(match.end);
            this.screenplay.setLineText(match.line, newText);
            count++;
        }

        this.findMatches = [];
        this.currentMatchIndex = -1;

        this._render();
        this._saveUndoState('Replace all');
        this._notifyModified();

        return count;
    }

    /**
     * Select a range of text
     */
    _selectRange(lineIndex, start, end) {
        const lineElement = this._getLineElement(lineIndex);
        if (!lineElement || !lineElement.childNodes[0]) return;

        const textNode = lineElement.childNodes[0];
        const range = document.createRange();
        range.setStart(textNode, Math.min(start, textNode.length));
        range.setEnd(textNode, Math.min(end, textNode.length));

        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }

    /**
     * Go to specific line
     */
    goToLine(lineIndex) {
        if (lineIndex < 0 || lineIndex >= this.screenplay.lineCount) return;
        this._focusLine(lineIndex, 0);
    }

    /**
     * Go to specific page
     */
    goToPage(pageNumber) {
        const pageBreaks = this.screenplay.calculatePageBreaks();
        if (pageNumber < 1 || pageNumber > pageBreaks.length) return;
        this._focusLine(pageBreaks[pageNumber - 1], 0);
    }

    /**
     * Select all text
     */
    selectAll() {
        const range = document.createRange();
        range.selectNodeContents(this.editorElement);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
    }

    /**
     * Cut selected text
     */
    cut() {
        document.execCommand('cut');
        this._handleInput();
    }

    /**
     * Copy selected text
     */
    copy() {
        document.execCommand('copy');
    }

    /**
     * Paste from clipboard
     */
    async paste() {
        try {
            const text = await navigator.clipboard.readText();
            document.execCommand('insertText', false, text);
        } catch (e) {
            console.error('Paste failed:', e);
        }
    }

    /**
     * Set zoom level
     */
    setZoom(level) {
        this.zoom = Math.max(0.5, Math.min(2.0, level));
        this.editorElement.style.transform = `scale(${this.zoom})`;
        this.editorElement.style.transformOrigin = 'top left';
    }

    /**
     * Load a screenplay
     */
    loadScreenplay(screenplay) {
        this.screenplay = screenplay;
        this.undoManager.clear();
        this._render();
        this._focusLine(0, 0);
        this._saveUndoState('Load screenplay');
        document.getElementById('status-modified').textContent = '';
    }

    /**
     * Get the current screenplay
     */
    getScreenplay() {
        return this.screenplay;
    }

    /**
     * Check if there are unsaved changes
     */
    hasUnsavedChanges() {
        return this.screenplay.modified;
    }
}

window.TrelbyEditor = ScreenplayEditor;
