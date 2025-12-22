/**
 * Trelby Web - Menu System
 * Handles menu bar and keyboard shortcuts
 */

class MenuManager {
    constructor(app) {
        this.app = app;
        this.activeMenu = null;
        this._bindEvents();
    }

    /**
     * Bind menu events
     */
    _bindEvents() {
        // Menu item hover/click
        const menuItems = document.querySelectorAll('.menu-item');
        menuItems.forEach(item => {
            item.querySelector('.menu-label').addEventListener('click', (e) => {
                e.stopPropagation();
                this._toggleMenu(item);
            });

            item.addEventListener('mouseenter', () => {
                if (this.activeMenu && this.activeMenu !== item) {
                    this._openMenu(item);
                }
            });
        });

        // Menu options
        document.querySelectorAll('.menu-option[data-action]').forEach(option => {
            option.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = option.dataset.action;
                this._executeAction(action);
                this._closeAllMenus();
            });
        });

        // Close menu on click outside
        document.addEventListener('click', () => {
            this._closeAllMenus();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            this._handleKeyboard(e);
        });

        // Toolbar buttons
        document.querySelectorAll('.toolbar-btn[data-action]').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this._executeAction(action);
            });
        });
    }

    /**
     * Toggle menu open/closed
     */
    _toggleMenu(menuItem) {
        if (this.activeMenu === menuItem) {
            this._closeAllMenus();
        } else {
            this._openMenu(menuItem);
        }
    }

    /**
     * Open a menu
     */
    _openMenu(menuItem) {
        this._closeAllMenus();
        menuItem.classList.add('active');
        this.activeMenu = menuItem;
    }

    /**
     * Close all menus
     */
    _closeAllMenus() {
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });
        this.activeMenu = null;
    }

    /**
     * Handle keyboard shortcuts
     */
    _handleKeyboard(e) {
        const { SHORTCUTS } = window.TrelbyConstants;

        // Build shortcut string
        let shortcut = '';
        if (e.ctrlKey || e.metaKey) shortcut += 'Ctrl+';
        if (e.shiftKey) shortcut += 'Shift+';
        if (e.altKey) shortcut += 'Alt+';

        // Handle special keys
        const key = e.key.length === 1 ? e.key.toUpperCase() : e.key;
        shortcut += key;

        // Also try with just the key code for function keys, etc.
        const altShortcut = shortcut.replace(e.key, e.code);

        // Check if this matches a shortcut
        const action = SHORTCUTS[shortcut] || SHORTCUTS[altShortcut];
        if (action) {
            e.preventDefault();
            this._executeAction(action);
        }
    }

    /**
     * Execute a menu action
     */
    _executeAction(action) {
        const app = this.app;
        const editor = app.editor;
        const dialogs = app.dialogs;

        switch (action) {
            // File menu
            case 'new':
                app.newFile();
                break;
            case 'open':
                app.openFile();
                break;
            case 'save':
                app.saveFile();
                break;
            case 'saveAs':
                app.saveFileAs();
                break;
            case 'importFDX':
            case 'importFountain':
            case 'importText':
            case 'importTrelby':
                app.importFile(action.replace('import', '').toLowerCase());
                break;
            case 'exportPDF':
                app.exportFile('pdf');
                break;
            case 'exportHTML':
                app.exportFile('html');
                break;
            case 'exportText':
                app.exportFile('txt');
                break;
            case 'exportFDX':
                app.exportFile('fdx');
                break;
            case 'exportFountain':
                app.exportFile('fountain');
                break;
            case 'print':
                window.print();
                break;

            // Edit menu
            case 'undo':
                editor.undo();
                break;
            case 'redo':
                editor.redo();
                break;
            case 'cut':
                editor.cut();
                break;
            case 'copy':
                editor.copy();
                break;
            case 'paste':
                editor.paste();
                break;
            case 'selectAll':
                editor.selectAll();
                break;
            case 'find':
                this._showFindDialog(false);
                break;
            case 'replace':
                this._showFindDialog(true);
                break;
            case 'findNext':
                editor.findNext();
                break;
            case 'findPrev':
                editor.findPrevious();
                break;

            // View menu
            case 'viewDraft':
                editor.setViewMode('draft');
                this._updateViewCheckmarks('draft');
                break;
            case 'viewLayout':
                editor.setViewMode('layout');
                this._updateViewCheckmarks('layout');
                break;
            case 'viewSideBySide':
                editor.setViewMode('sidebyside');
                this._updateViewCheckmarks('sidebyside');
                break;
            case 'fullscreen':
                this._toggleFullscreen();
                break;
            case 'zoomIn':
                editor.setZoom(editor.zoom + 0.1);
                break;
            case 'zoomOut':
                editor.setZoom(editor.zoom - 0.1);
                break;
            case 'zoomReset':
                editor.setZoom(1.0);
                break;

            // Script menu
            case 'titlePages':
                dialogs.showTitlePages(editor.screenplay, (pages) => {
                    editor.screenplay.titlePages = pages;
                    editor._notifyModified();
                });
                break;
            case 'headers':
                this._showHeadersDialog();
                break;
            case 'locations':
                this._showLocationsDialog();
                break;
            case 'scSettings':
                dialogs.showSettings(editor.screenplay.config, (newConfig) => {
                    editor.screenplay.config = newConfig;
                    app.applyConfig(newConfig);
                    editor._notifyModified();
                });
                break;
            case 'compareScripts':
                window.TrelbyUtils.toast('Compare scripts coming soon', 'info');
                break;

            // Tools menu
            case 'spellCheck':
                app.runSpellCheck();
                break;
            case 'nameDatabase':
                dialogs.showNameDatabase((name) => {
                    // Insert name at cursor
                    document.execCommand('insertText', false, name);
                });
                break;
            case 'reportScene':
                this._showReport('scene');
                break;
            case 'reportCharacter':
                this._showReport('character');
                break;
            case 'reportLocation':
                this._showReport('location');
                break;
            case 'reportScript':
                this._showReport('script');
                break;
            case 'reportDialogue':
                this._showReport('dialogue');
                break;
            case 'watermark':
                this._showWatermarkDialog();
                break;

            // Help menu
            case 'manual':
                window.open('https://www.trelby.org/manual.html', '_blank');
                break;
            case 'keyboard':
                dialogs.showKeyboardShortcuts();
                break;
            case 'about':
                dialogs.showAbout();
                break;

            // Element type shortcuts
            case 'setScene':
                this._setCurrentLineType('scene');
                break;
            case 'setAction':
                this._setCurrentLineType('action');
                break;
            case 'setCharacter':
                this._setCurrentLineType('character');
                break;
            case 'setDialogue':
                this._setCurrentLineType('dialogue');
                break;
            case 'setParen':
                this._setCurrentLineType('paren');
                break;
            case 'setTransition':
                this._setCurrentLineType('transition');
                break;
            case 'setShot':
                this._setCurrentLineType('shot');
                break;
            case 'setNote':
                this._setCurrentLineType('note');
                break;

            case 'closeDialog':
                dialogs.closeTop();
                break;

            default:
                console.log('Unknown action:', action);
        }
    }

    /**
     * Set current line type
     */
    _setCurrentLineType(type) {
        const lineIndex = this.app.editor._getCurrentLineIndex();
        if (lineIndex >= 0) {
            this.app.editor.setLineType(lineIndex, type);
        }
    }

    /**
     * Show find/replace dialog
     */
    _showFindDialog(showReplace) {
        const editor = this.app.editor;

        this.app.dialogs.showFindReplace({
            showReplace,
            onFind: (query, options) => {
                const matches = editor.find(query, options);
                if (matches.length > 0) {
                    editor.findNext();
                    window.TrelbyUtils.toast(`Found ${matches.length} matches`, 'success');
                } else {
                    window.TrelbyUtils.toast('No matches found', 'warning');
                }
            },
            onReplace: (find, replace, options) => {
                if (editor.findMatches.length === 0) {
                    editor.find(find, options);
                }
                if (editor.replace(replace)) {
                    editor.findNext();
                }
            },
            onReplaceAll: (find, replace, options) => {
                editor.find(find, options);
                const count = editor.replaceAll(replace);
                window.TrelbyUtils.toast(`Replaced ${count} occurrences`, 'success');
            }
        });
    }

    /**
     * Show report dialog
     */
    _showReport(type) {
        const reports = new window.TrelbyReports();
        const screenplay = this.app.editor.screenplay;
        let report;

        switch (type) {
            case 'scene':
                report = reports.generateSceneReport(screenplay);
                break;
            case 'character':
                report = reports.generateCharacterReport(screenplay);
                break;
            case 'location':
                report = reports.generateLocationReport(screenplay);
                break;
            case 'script':
                report = reports.generateScriptReport(screenplay);
                break;
            case 'dialogue':
                report = reports.generateDialogueChart(screenplay);
                break;
        }

        if (report) {
            this.app.dialogs.showReport(report);
        }
    }

    /**
     * Show headers dialog
     */
    _showHeadersDialog() {
        const screenplay = this.app.editor.screenplay;

        this.app.dialogs.show({
            title: 'Headers',
            content: `
                <div class="headers-content">
                    <div class="headers-section">
                        <h4>First Page Header</h4>
                        <input type="text" id="header-first" value="${window.TrelbyUtils.escapeHtml(screenplay.headers.firstPage)}" style="width: 100%">
                    </div>
                    <div class="headers-section">
                        <h4>Other Pages Header</h4>
                        <input type="text" id="header-other" value="${window.TrelbyUtils.escapeHtml(screenplay.headers.otherPages)}" style="width: 100%">
                        <p style="color: var(--text-muted); font-size: 12px; margin-top: 8px;">Use %p for page number</p>
                    </div>
                    <div class="form-group">
                        <label><input type="checkbox" id="header-show-first" ${screenplay.headers.showOnFirst ? 'checked' : ''}> Show header on first page</label>
                    </div>
                </div>
            `,
            buttons: [
                { text: 'Cancel', action: 'close' },
                {
                    text: 'Save',
                    primary: true,
                    action: (dlg) => {
                        screenplay.headers.firstPage = dlg.querySelector('#header-first').value;
                        screenplay.headers.otherPages = dlg.querySelector('#header-other').value;
                        screenplay.headers.showOnFirst = dlg.querySelector('#header-show-first').checked;
                        this.app.editor._notifyModified();
                        return true;
                    }
                }
            ]
        });
    }

    /**
     * Show locations dialog
     */
    _showLocationsDialog() {
        const screenplay = this.app.editor.screenplay;
        const locations = screenplay.getLocations();

        let html = '<div class="locations-content"><div class="locations-list">';

        for (const [name, loc] of locations) {
            html += `
                <div class="location-item">
                    <span>${window.TrelbyUtils.escapeHtml(name)}</span>
                    <span style="color: var(--text-muted); margin-left: auto;">${loc.scenes.length} scene(s)</span>
                </div>
            `;
        }

        html += '</div></div>';

        this.app.dialogs.show({
            title: 'Locations',
            content: html,
            buttons: [{ text: 'Close', primary: true, action: 'close' }]
        });
    }

    /**
     * Show watermark dialog
     */
    _showWatermarkDialog() {
        const config = this.app.editor.screenplay.config;

        this.app.dialogs.show({
            title: 'Watermark Settings',
            content: `
                <div class="watermark-content">
                    <div class="form-group">
                        <label><input type="checkbox" id="wm-enabled" ${config.watermark.enabled ? 'checked' : ''}> Enable watermark</label>
                    </div>
                    <div class="form-group">
                        <label>Text:</label>
                        <input type="text" id="wm-text" value="${window.TrelbyUtils.escapeHtml(config.watermark.text)}" style="width: 100%">
                    </div>
                    <div class="form-group">
                        <label>Font Size:</label>
                        <input type="number" id="wm-fontsize" value="${config.watermark.fontSize}" min="12" max="100">
                    </div>
                    <div class="form-group">
                        <label>Opacity:</label>
                        <input type="range" id="wm-opacity" value="${config.watermark.opacity * 100}" min="10" max="100">
                    </div>
                    <div class="form-group">
                        <label>Angle:</label>
                        <input type="number" id="wm-angle" value="${config.watermark.angle}" min="-90" max="90">
                    </div>
                    <div class="watermark-preview">
                        <span class="watermark-text" id="wm-preview">${window.TrelbyUtils.escapeHtml(config.watermark.text) || 'Preview'}</span>
                    </div>
                </div>
            `,
            buttons: [
                { text: 'Cancel', action: 'close' },
                {
                    text: 'Save',
                    primary: true,
                    action: (dlg) => {
                        config.watermark.enabled = dlg.querySelector('#wm-enabled').checked;
                        config.watermark.text = dlg.querySelector('#wm-text').value;
                        config.watermark.fontSize = parseInt(dlg.querySelector('#wm-fontsize').value);
                        config.watermark.opacity = parseInt(dlg.querySelector('#wm-opacity').value) / 100;
                        config.watermark.angle = parseInt(dlg.querySelector('#wm-angle').value);
                        this.app.editor._notifyModified();
                        return true;
                    }
                }
            ],
            onOpen: (dlg) => {
                // Update preview on input change
                const textInput = dlg.querySelector('#wm-text');
                const preview = dlg.querySelector('#wm-preview');
                textInput.addEventListener('input', () => {
                    preview.textContent = textInput.value || 'Preview';
                });
            }
        });
    }

    /**
     * Update view mode checkmarks
     */
    _updateViewCheckmarks(activeView) {
        document.querySelectorAll('[data-view]').forEach(el => {
            el.textContent = el.dataset.view === activeView ? '\u2713' : '';
        });
    }

    /**
     * Toggle fullscreen mode
     */
    _toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
}

window.TrelbyMenuManager = MenuManager;
