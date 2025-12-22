/**
 * Trelby Web - Main Application
 * Entry point that initializes and coordinates all components
 */

class TrelbyApp {
    constructor() {
        this.editor = null;
        this.dialogs = null;
        this.menu = null;
        this.fileIO = null;
        this.exporter = null;
        this.config = null;

        this.autoSaveInterval = null;
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('Initializing Trelby Web...');

        // Load configuration
        this.config = window.TrelbyConfig.load();
        this.applyConfig(this.config);

        // Initialize components
        this.dialogs = new window.TrelbyDialogs();
        this.fileIO = new window.TrelbyFileIO();
        this.exporter = new window.TrelbyExporter();
        this.editor = new window.TrelbyEditor('#main-content');
        this.menu = new window.TrelbyMenuManager(this);

        // Set up callbacks
        this.editor.onModified = () => this._onEditorModified();
        this.editor.onCursorChange = (line, col, page) => this._onCursorChange(line, col, page);

        // Check for auto-save recovery
        await this._checkAutoSaveRecovery();

        // Set up auto-save
        if (this.config.autoSave) {
            this._startAutoSave();
        }

        // Set up before unload warning
        window.addEventListener('beforeunload', (e) => {
            if (this.editor.hasUnsavedChanges()) {
                e.preventDefault();
                e.returnValue = '';
            }
        });

        // Update title
        this._updateTitle();

        console.log('Trelby Web initialized successfully!');
        document.getElementById('status-message').textContent = 'Ready';
    }

    /**
     * Apply configuration to the application
     */
    applyConfig(config) {
        // Apply theme
        document.body.dataset.theme = config.theme;

        // Apply font settings
        document.documentElement.style.setProperty('--font-mono', config.fontFamily);
        document.documentElement.style.setProperty('--screenplay-font-size', config.fontSize + 'pt');

        // Apply page settings
        const { PAPER_SIZES } = window.TrelbyConstants;
        const paper = PAPER_SIZES[config.paperSize];
        if (paper) {
            document.documentElement.style.setProperty('--page-width', (paper.width / 72) + 'in');
            document.documentElement.style.setProperty('--page-height', (paper.height / 72) + 'in');
        }

        document.documentElement.style.setProperty('--margin-top', (config.margins.top / 72) + 'in');
        document.documentElement.style.setProperty('--margin-bottom', (config.margins.bottom / 72) + 'in');
        document.documentElement.style.setProperty('--margin-left', (config.margins.left / 72) + 'in');
        document.documentElement.style.setProperty('--margin-right', (config.margins.right / 72) + 'in');

        // Show/hide line numbers
        if (config.showLineNumbers) {
            document.getElementById('screenplay-editor')?.classList.add('show-line-numbers');
        } else {
            document.getElementById('screenplay-editor')?.classList.remove('show-line-numbers');
        }

        // Save config
        config.save();
    }

    /**
     * Create a new file
     */
    async newFile() {
        if (this.editor.hasUnsavedChanges()) {
            const confirm = await this.dialogs.confirm(
                'You have unsaved changes. Do you want to create a new file?',
                'Unsaved Changes'
            );
            if (!confirm) return;
        }

        const screenplay = this.fileIO.createNew();
        this.editor.loadScreenplay(screenplay);
        this._updateTitle();
        window.TrelbyUtils.toast('New screenplay created', 'success');
    }

    /**
     * Open a file
     */
    async openFile() {
        if (this.editor.hasUnsavedChanges()) {
            const confirm = await this.dialogs.confirm(
                'You have unsaved changes. Do you want to open a different file?',
                'Unsaved Changes'
            );
            if (!confirm) return;
        }

        try {
            const screenplay = await this.fileIO.open();
            if (screenplay) {
                this.editor.loadScreenplay(screenplay);
                this._updateTitle();
                window.TrelbyUtils.toast('File opened successfully', 'success');
            }
        } catch (e) {
            console.error('Error opening file:', e);
            window.TrelbyUtils.toast('Error opening file: ' + e.message, 'error');
        }
    }

    /**
     * Import a file in a specific format
     */
    async importFile(format) {
        if (this.editor.hasUnsavedChanges()) {
            const confirm = await this.dialogs.confirm(
                'You have unsaved changes. Do you want to import a file?',
                'Unsaved Changes'
            );
            if (!confirm) return;
        }

        try {
            const extensions = {
                'fdx': '.fdx',
                'fountain': '.fountain',
                'text': '.txt',
                'trelby': '.trelby'
            };

            const file = await window.TrelbyUtils.pickFile(extensions[format] || '*');
            if (!file) return;

            const content = await window.TrelbyUtils.readFile(file);
            const screenplay = this.fileIO.parseFile(content, file.name);

            if (screenplay) {
                this.editor.loadScreenplay(screenplay);
                this.fileIO.setFilename(file.name.replace(/\.[^.]+$/, '.trelby'));
                this._updateTitle();
                window.TrelbyUtils.toast('File imported successfully', 'success');
            }
        } catch (e) {
            console.error('Error importing file:', e);
            window.TrelbyUtils.toast('Error importing file: ' + e.message, 'error');
        }
    }

    /**
     * Save the current file
     */
    async saveFile() {
        try {
            const success = await this.fileIO.save(this.editor.screenplay);
            if (success) {
                this.editor.screenplay.clearModified();
                document.getElementById('status-modified').textContent = '';
                this._updateTitle();
                window.TrelbyUtils.toast('File saved', 'success');
            }
        } catch (e) {
            console.error('Error saving file:', e);
            window.TrelbyUtils.toast('Error saving file: ' + e.message, 'error');
        }
    }

    /**
     * Save file with a new name
     */
    async saveFileAs() {
        try {
            const success = await this.fileIO.saveAs(this.editor.screenplay);
            if (success) {
                this.editor.screenplay.clearModified();
                document.getElementById('status-modified').textContent = '';
                this._updateTitle();
                window.TrelbyUtils.toast('File saved', 'success');
            }
        } catch (e) {
            console.error('Error saving file:', e);
            window.TrelbyUtils.toast('Error saving file: ' + e.message, 'error');
        }
    }

    /**
     * Export file in a specific format
     */
    async exportFile(format) {
        try {
            const filename = this.fileIO.getFilename().replace(/\.[^.]+$/, '');
            await this.exporter.export(this.editor.screenplay, format, {
                filename: filename + this.fileIO.getExtension(format)
            });
            window.TrelbyUtils.toast(`Exported as ${format.toUpperCase()}`, 'success');
        } catch (e) {
            console.error('Error exporting file:', e);
            window.TrelbyUtils.toast('Error exporting: ' + e.message, 'error');
        }
    }

    /**
     * Run spell check
     */
    async runSpellCheck() {
        const spellDialog = new window.TrelbySpellCheckDialog(
            this.editor.spellChecker,
            this.editor
        );

        const firstWord = await spellDialog.start();
        if (!firstWord) return;

        const showWord = (wordInfo) => {
            if (!wordInfo) {
                this.dialogs.closeTop();
                return;
            }

            this.dialogs.show({
                title: 'Spell Check',
                content: `
                    <div class="spellcheck-content">
                        <div class="spellcheck-word">
                            <span class="misspelled">${window.TrelbyUtils.escapeHtml(wordInfo.word)}</span>
                        </div>
                        <div class="spellcheck-suggestions">
                            <label>Suggestions:</label>
                            <select id="spell-suggestions" size="5">
                                ${wordInfo.suggestions.map(s => `<option value="${window.TrelbyUtils.escapeHtml(s)}">${window.TrelbyUtils.escapeHtml(s)}</option>`).join('')}
                            </select>
                        </div>
                        <p style="color: var(--text-muted); font-size: 12px;">${wordInfo.remaining} words remaining</p>
                    </div>
                `,
                buttons: [
                    {
                        text: 'Ignore',
                        action: () => {
                            showWord(spellDialog.ignore());
                            return false;
                        }
                    },
                    {
                        text: 'Ignore All',
                        action: () => {
                            showWord(spellDialog.ignoreAll());
                            return false;
                        }
                    },
                    {
                        text: 'Add to Dictionary',
                        action: () => {
                            showWord(spellDialog.addToDictionary());
                            return false;
                        }
                    },
                    {
                        text: 'Replace',
                        primary: true,
                        action: (dlg) => {
                            const selected = dlg.querySelector('#spell-suggestions').value;
                            if (selected) {
                                showWord(spellDialog.replace(selected));
                            }
                            return false;
                        }
                    },
                    { text: 'Close', action: 'close' }
                ]
            });
        };

        showWord(firstWord);
    }

    /**
     * Check for auto-save recovery
     */
    async _checkAutoSaveRecovery() {
        if (this.fileIO.hasAutoSave()) {
            const recover = await this.dialogs.confirm(
                'An auto-saved version was found. Would you like to recover it?',
                'Recover Auto-Save'
            );

            if (recover) {
                const data = this.fileIO.loadAutoSave();
                if (data) {
                    this.editor.loadScreenplay(data.screenplay);
                    this.fileIO.setFilename(data.filename || 'Recovered.trelby');
                    this._updateTitle();
                    window.TrelbyUtils.toast('Auto-save recovered', 'success');
                }
            }

            this.fileIO.clearAutoSave();
        }
    }

    /**
     * Start auto-save interval
     */
    _startAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }

        this.autoSaveInterval = setInterval(() => {
            if (this.editor.hasUnsavedChanges()) {
                this.fileIO.autoSave(this.editor.screenplay);
                console.log('Auto-saved');
            }
        }, this.config.autoSaveInterval);
    }

    /**
     * Stop auto-save
     */
    _stopAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    }

    /**
     * Handle editor modification
     */
    _onEditorModified() {
        this._updateTitle();
    }

    /**
     * Handle cursor change
     */
    _onCursorChange(line, col, page) {
        // Could update additional UI here
    }

    /**
     * Update window title
     */
    _updateTitle() {
        const filename = this.fileIO.getFilename();
        const modified = this.editor.hasUnsavedChanges() ? ' *' : '';
        document.title = `${filename}${modified} - Trelby`;
    }
}

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    window.trelbyApp = new TrelbyApp();
    await window.trelbyApp.init();
});

window.TrelbyApp = TrelbyApp;
