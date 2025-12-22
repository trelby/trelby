/**
 * Courius - Dialog System
 * Manages all modal dialogs in the application
 */

class DialogManager {
    constructor() {
        this.container = document.getElementById('dialogs');
        this.openDialogs = [];
        this._bindGlobalEvents();
    }

    /**
     * Bind global keyboard events for dialogs
     */
    _bindGlobalEvents() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.openDialogs.length > 0) {
                this.closeTop();
            }
        });
    }

    /**
     * Create and show a dialog
     */
    show(options) {
        const {
            title = 'Dialog',
            content = '',
            buttons = [{ text: 'OK', primary: true, action: 'close' }],
            width = 'auto',
            height = 'auto',
            className = '',
            onClose = null,
            onOpen = null
        } = options;

        // Create dialog from template
        const template = document.getElementById('dialog-template');
        const dialog = template.content.cloneNode(true).firstElementChild;

        // Set properties
        dialog.querySelector('.dialog-title').textContent = title;
        dialog.querySelector('.dialog-content').innerHTML = content;

        if (className) {
            dialog.querySelector('.dialog').classList.add(className);
        }

        if (width !== 'auto') {
            dialog.querySelector('.dialog').style.width = width;
        }

        // Add buttons
        const buttonsContainer = dialog.querySelector('.dialog-buttons');
        for (const btn of buttons) {
            const button = document.createElement('button');
            button.textContent = btn.text;
            if (btn.primary) button.classList.add('primary');
            if (btn.className) button.classList.add(btn.className);

            button.addEventListener('click', () => {
                if (typeof btn.action === 'function') {
                    const result = btn.action(dialog);
                    if (result !== false) {
                        this.close(dialog);
                    }
                } else if (btn.action === 'close') {
                    this.close(dialog);
                }
            });

            buttonsContainer.appendChild(button);
        }

        // Close button
        dialog.querySelector('.dialog-close').addEventListener('click', () => {
            this.close(dialog);
        });

        // Click outside to close
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) {
                this.close(dialog);
            }
        });

        // Store callbacks
        dialog._onClose = onClose;

        // Add to DOM
        this.container.appendChild(dialog);
        this.openDialogs.push(dialog);

        // Focus first input or button
        setTimeout(() => {
            const focusable = dialog.querySelector('input, select, textarea, button.primary');
            if (focusable) focusable.focus();
            if (onOpen) onOpen(dialog);
        }, 50);

        return dialog;
    }

    /**
     * Close a specific dialog
     */
    close(dialog) {
        if (!dialog) return;

        if (dialog._onClose) {
            dialog._onClose();
        }

        const index = this.openDialogs.indexOf(dialog);
        if (index > -1) {
            this.openDialogs.splice(index, 1);
        }

        dialog.remove();
    }

    /**
     * Close topmost dialog
     */
    closeTop() {
        if (this.openDialogs.length > 0) {
            this.close(this.openDialogs[this.openDialogs.length - 1]);
        }
    }

    /**
     * Close all dialogs
     */
    closeAll() {
        while (this.openDialogs.length > 0) {
            this.close(this.openDialogs[this.openDialogs.length - 1]);
        }
    }

    /**
     * Show an alert dialog
     */
    alert(message, title = 'Alert') {
        return new Promise((resolve) => {
            this.show({
                title,
                content: `<p>${window.CouriusUtils.escapeHtml(message)}</p>`,
                buttons: [{ text: 'OK', primary: true, action: () => { resolve(); return true; } }]
            });
        });
    }

    /**
     * Show a confirm dialog
     */
    confirm(message, title = 'Confirm') {
        return new Promise((resolve) => {
            this.show({
                title,
                content: `<p>${window.CouriusUtils.escapeHtml(message)}</p>`,
                buttons: [
                    { text: 'Cancel', action: () => { resolve(false); return true; } },
                    { text: 'OK', primary: true, action: () => { resolve(true); return true; } }
                ]
            });
        });
    }

    /**
     * Show a prompt dialog
     */
    prompt(message, defaultValue = '', title = 'Input') {
        return new Promise((resolve) => {
            const dialog = this.show({
                title,
                content: `
                    <p>${window.CouriusUtils.escapeHtml(message)}</p>
                    <input type="text" id="prompt-input" value="${window.CouriusUtils.escapeHtml(defaultValue)}" style="width: 100%">
                `,
                buttons: [
                    { text: 'Cancel', action: () => { resolve(null); return true; } },
                    {
                        text: 'OK',
                        primary: true,
                        action: (dlg) => {
                            const value = dlg.querySelector('#prompt-input').value;
                            resolve(value);
                            return true;
                        }
                    }
                ]
            });

            // Handle Enter key
            dialog.querySelector('#prompt-input').addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    resolve(dialog.querySelector('#prompt-input').value);
                    this.close(dialog);
                }
            });
        });
    }

    /**
     * Show Find/Replace dialog
     */
    showFindReplace(options = {}) {
        const { showReplace = false, onFind, onReplace, onReplaceAll } = options;

        const template = document.getElementById('find-dialog-template');
        const content = template.content.cloneNode(true).firstElementChild;

        if (showReplace) {
            content.querySelector('.replace-group').classList.remove('hidden');
        }

        const buttons = [
            { text: 'Find Next', primary: true, action: (dlg) => {
                const query = dlg.querySelector('#find-input').value;
                const options = {
                    matchCase: dlg.querySelector('#find-case').checked,
                    wholeWord: dlg.querySelector('#find-whole').checked,
                    regex: dlg.querySelector('#find-regex').checked
                };
                if (onFind) onFind(query, options);
                return false; // Don't close
            }}
        ];

        if (showReplace) {
            buttons.push({ text: 'Replace', action: (dlg) => {
                const find = dlg.querySelector('#find-input').value;
                const replace = dlg.querySelector('#replace-input').value;
                const options = {
                    matchCase: dlg.querySelector('#find-case').checked,
                    wholeWord: dlg.querySelector('#find-whole').checked,
                    regex: dlg.querySelector('#find-regex').checked
                };
                if (onReplace) onReplace(find, replace, options);
                return false;
            }});

            buttons.push({ text: 'Replace All', action: (dlg) => {
                const find = dlg.querySelector('#find-input').value;
                const replace = dlg.querySelector('#replace-input').value;
                const options = {
                    matchCase: dlg.querySelector('#find-case').checked,
                    wholeWord: dlg.querySelector('#find-whole').checked,
                    regex: dlg.querySelector('#find-regex').checked
                };
                if (onReplaceAll) onReplaceAll(find, replace, options);
                return false;
            }});
        }

        buttons.push({ text: 'Close', action: 'close' });

        return this.show({
            title: showReplace ? 'Find and Replace' : 'Find',
            content: content.innerHTML,
            buttons,
            width: '450px'
        });
    }

    /**
     * Show Settings dialog
     */
    showSettings(config, onSave) {
        const template = document.getElementById('settings-template');
        const content = template.content.cloneNode(true).firstElementChild;

        const dialog = this.show({
            title: 'Settings',
            content: content.innerHTML,
            className: 'large',
            buttons: [
                { text: 'Cancel', action: 'close' },
                {
                    text: 'Save',
                    primary: true,
                    action: (dlg) => {
                        const newConfig = this._extractSettingsFromDialog(dlg, config);
                        if (onSave) onSave(newConfig);
                        return true;
                    }
                }
            ],
            onOpen: (dlg) => {
                this._populateSettings(dlg, config);
                this._bindSettingsTabs(dlg);
            }
        });

        return dialog;
    }

    /**
     * Populate settings dialog with current values
     */
    _populateSettings(dialog, config) {
        // Paper settings
        const paperSize = dialog.querySelector('#paper-size');
        if (paperSize) paperSize.value = config.paperSize;

        const marginTop = dialog.querySelector('#margin-top');
        if (marginTop) marginTop.value = config.margins.top / 72; // Convert from points to inches

        const marginBottom = dialog.querySelector('#margin-bottom');
        if (marginBottom) marginBottom.value = config.margins.bottom / 72;

        const marginLeft = dialog.querySelector('#margin-left');
        if (marginLeft) marginLeft.value = config.margins.left / 72;

        const marginRight = dialog.querySelector('#margin-right');
        if (marginRight) marginRight.value = config.margins.right / 72;

        // Font settings
        const fontFamily = dialog.querySelector('#font-family');
        if (fontFamily) fontFamily.value = config.fontFamily;

        const fontSize = dialog.querySelector('#font-size');
        if (fontSize) fontSize.value = config.fontSize;

        // Display settings
        const showLineNumbers = dialog.querySelector('#show-line-numbers');
        if (showLineNumbers) showLineNumbers.checked = config.showLineNumbers;

        const showPageBreaks = dialog.querySelector('#show-page-breaks');
        if (showPageBreaks) showPageBreaks.checked = config.showPageBreaks;

        const autoSave = dialog.querySelector('#auto-save');
        if (autoSave) autoSave.checked = config.autoSave;

        const theme = dialog.querySelector('#theme');
        if (theme) theme.value = config.theme;
    }

    /**
     * Extract settings from dialog
     */
    _extractSettingsFromDialog(dialog, baseConfig) {
        const config = baseConfig.clone();

        // Paper settings
        const paperSize = dialog.querySelector('#paper-size');
        if (paperSize) config.paperSize = paperSize.value;

        const marginTop = dialog.querySelector('#margin-top');
        if (marginTop) config.margins.top = parseFloat(marginTop.value) * 72;

        const marginBottom = dialog.querySelector('#margin-bottom');
        if (marginBottom) config.margins.bottom = parseFloat(marginBottom.value) * 72;

        const marginLeft = dialog.querySelector('#margin-left');
        if (marginLeft) config.margins.left = parseFloat(marginLeft.value) * 72;

        const marginRight = dialog.querySelector('#margin-right');
        if (marginRight) config.margins.right = parseFloat(marginRight.value) * 72;

        // Font settings
        const fontFamily = dialog.querySelector('#font-family');
        if (fontFamily) config.fontFamily = fontFamily.value;

        const fontSize = dialog.querySelector('#font-size');
        if (fontSize) config.fontSize = parseInt(fontSize.value);

        // Display settings
        const showLineNumbers = dialog.querySelector('#show-line-numbers');
        if (showLineNumbers) config.showLineNumbers = showLineNumbers.checked;

        const showPageBreaks = dialog.querySelector('#show-page-breaks');
        if (showPageBreaks) config.showPageBreaks = showPageBreaks.checked;

        const autoSave = dialog.querySelector('#auto-save');
        if (autoSave) config.autoSave = autoSave.checked;

        const theme = dialog.querySelector('#theme');
        if (theme) config.theme = theme.value;

        return config;
    }

    /**
     * Bind settings tab navigation
     */
    _bindSettingsTabs(dialog) {
        const tabs = dialog.querySelectorAll('.settings-tab');
        const panels = dialog.querySelectorAll('.settings-panel');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const targetPanel = tab.dataset.tab;

                tabs.forEach(t => t.classList.remove('active'));
                panels.forEach(p => p.classList.remove('active'));

                tab.classList.add('active');
                dialog.querySelector(`[data-panel="${targetPanel}"]`).classList.add('active');
            });
        });
    }

    /**
     * Show Title Pages dialog
     */
    showTitlePages(screenplay, onSave) {
        const template = document.getElementById('title-pages-template');
        const content = template.content.cloneNode(true).firstElementChild;

        let titlePages = [...screenplay.titlePages];

        const dialog = this.show({
            title: 'Title Pages',
            content: content.innerHTML,
            className: 'large',
            buttons: [
                { text: 'Cancel', action: 'close' },
                {
                    text: 'Save',
                    primary: true,
                    action: () => {
                        if (onSave) onSave(titlePages);
                        return true;
                    }
                }
            ],
            onOpen: (dlg) => {
                this._setupTitlePagesDialog(dlg, titlePages);
            }
        });

        return dialog;
    }

    /**
     * Setup title pages dialog functionality
     */
    _setupTitlePagesDialog(dialog, titlePages) {
        const select = dialog.querySelector('#title-page-select');
        const content = dialog.querySelector('#title-page-content');
        const centered = dialog.querySelector('#title-centered');
        const addBtn = dialog.querySelector('#add-title-page');
        const removeBtn = dialog.querySelector('#remove-title-page');
        const upBtn = dialog.querySelector('#move-up-title-page');
        const downBtn = dialog.querySelector('#move-down-title-page');

        const updateList = () => {
            select.innerHTML = '';
            titlePages.forEach((page, i) => {
                const option = document.createElement('option');
                option.value = i;
                option.textContent = `Page ${i + 1}`;
                select.appendChild(option);
            });
        };

        const showPage = (index) => {
            if (index >= 0 && index < titlePages.length) {
                content.value = titlePages[index].content || '';
                centered.checked = titlePages[index].centered || false;
            } else {
                content.value = '';
                centered.checked = false;
            }
        };

        const saveCurrent = () => {
            const index = parseInt(select.value);
            if (index >= 0 && index < titlePages.length) {
                titlePages[index].content = content.value;
                titlePages[index].centered = centered.checked;
            }
        };

        select.addEventListener('change', () => {
            saveCurrent();
            showPage(parseInt(select.value));
        });

        content.addEventListener('input', saveCurrent);
        centered.addEventListener('change', saveCurrent);

        addBtn.addEventListener('click', () => {
            saveCurrent();
            titlePages.push({ content: '', centered: true });
            updateList();
            select.value = titlePages.length - 1;
            showPage(titlePages.length - 1);
        });

        removeBtn.addEventListener('click', () => {
            const index = parseInt(select.value);
            if (index >= 0) {
                titlePages.splice(index, 1);
                updateList();
                showPage(Math.min(index, titlePages.length - 1));
            }
        });

        upBtn.addEventListener('click', () => {
            const index = parseInt(select.value);
            if (index > 0) {
                saveCurrent();
                [titlePages[index], titlePages[index - 1]] = [titlePages[index - 1], titlePages[index]];
                updateList();
                select.value = index - 1;
            }
        });

        downBtn.addEventListener('click', () => {
            const index = parseInt(select.value);
            if (index < titlePages.length - 1) {
                saveCurrent();
                [titlePages[index], titlePages[index + 1]] = [titlePages[index + 1], titlePages[index]];
                updateList();
                select.value = index + 1;
            }
        });

        updateList();
        if (titlePages.length > 0) {
            select.value = 0;
            showPage(0);
        }
    }

    /**
     * Show Report dialog
     */
    showReport(report) {
        const template = document.getElementById('report-template');
        const content = template.content.cloneNode(true).firstElementChild;

        const reports = new window.CouriusReports();
        const html = reports.renderAsHTML(report);

        return this.show({
            title: report.title,
            content: content.innerHTML,
            className: 'large',
            buttons: [
                {
                    text: 'Export HTML',
                    action: () => {
                        reports.downloadReport(report, 'html');
                        return false;
                    }
                },
                {
                    text: 'Export CSV',
                    action: () => {
                        reports.downloadReport(report, 'csv');
                        return false;
                    }
                },
                { text: 'Close', primary: true, action: 'close' }
            ],
            onOpen: (dlg) => {
                dlg.querySelector('.report-title').textContent = report.title;
                dlg.querySelector('.report-body').innerHTML = html;
            }
        });
    }

    /**
     * Show Name Database dialog
     */
    showNameDatabase(onInsert) {
        const template = document.getElementById('name-database-template');
        const content = template.content.cloneNode(true).firstElementChild;

        const nameDb = new window.CouriusNameDatabase();
        nameDb.load();

        const dialog = this.show({
            title: 'Name Database',
            content: content.innerHTML,
            buttons: [
                { text: 'Close', action: 'close' }
            ],
            onOpen: (dlg) => {
                const genderSelect = dlg.querySelector('#name-gender');
                const originSelect = dlg.querySelector('#name-origin');
                const searchInput = dlg.querySelector('#name-search');
                const nameList = dlg.querySelector('#name-list');
                const insertBtn = dlg.querySelector('#name-insert');
                const copyBtn = dlg.querySelector('#name-copy');

                // Populate origins
                for (const origin of nameDb.getOrigins()) {
                    const option = document.createElement('option');
                    option.value = origin;
                    option.textContent = origin;
                    originSelect.appendChild(option);
                }

                const updateList = () => {
                    const gender = genderSelect.value;
                    const origin = originSelect.value;
                    const query = searchInput.value;
                    const results = nameDb.search(query, gender, origin);

                    nameList.innerHTML = '';
                    for (const name of results.slice(0, 100)) {
                        const option = document.createElement('option');
                        option.value = name.name;
                        option.textContent = `${name.name} (${name.origin})`;
                        nameList.appendChild(option);
                    }
                };

                genderSelect.addEventListener('change', updateList);
                originSelect.addEventListener('change', updateList);
                searchInput.addEventListener('input', updateList);

                insertBtn.addEventListener('click', () => {
                    const selected = nameList.value;
                    if (selected && onInsert) {
                        onInsert(selected.toUpperCase());
                        this.close(dlg);
                    }
                });

                copyBtn.addEventListener('click', () => {
                    const selected = nameList.value;
                    if (selected) {
                        navigator.clipboard.writeText(selected.toUpperCase());
                        window.CouriusUtils.toast('Name copied to clipboard', 'success');
                    }
                });

                nameList.addEventListener('dblclick', () => {
                    const selected = nameList.value;
                    if (selected && onInsert) {
                        onInsert(selected.toUpperCase());
                        this.close(dlg);
                    }
                });

                updateList();
            }
        });

        return dialog;
    }

    /**
     * Show About dialog
     */
    showAbout() {
        const { VERSION } = window.CouriusConstants;

        return this.show({
            title: 'About Courius',
            content: `
                <div class="about-content">
                    <div class="about-logo">📝</div>
                    <div class="about-title">Courius</div>
                    <div class="about-version">Version ${VERSION.string}</div>
                    <div class="about-description">
                        <p>A free, multiplatform, feature-rich screenwriting program.</p>
                        <p>Originally created as a desktop application, now available in your browser.</p>
                    </div>
                    <div class="about-links">
                        <a href="https://www.trelby.org" target="_blank">Website</a>
                        <a href="https://github.com/trelby/trelby" target="_blank">GitHub</a>
                    </div>
                </div>
            `,
            buttons: [{ text: 'OK', primary: true, action: 'close' }]
        });
    }

    /**
     * Show keyboard shortcuts help
     */
    showKeyboardShortcuts() {
        const { SHORTCUTS } = window.CouriusConstants;

        let html = '<div class="shortcuts-table"><table>';
        for (const [shortcut, action] of Object.entries(SHORTCUTS)) {
            const actionLabel = action.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
            html += `<tr><td><code>${shortcut}</code></td><td>${actionLabel}</td></tr>`;
        }
        html += '</table></div>';

        return this.show({
            title: 'Keyboard Shortcuts',
            content: html,
            buttons: [{ text: 'OK', primary: true, action: 'close' }]
        });
    }
}

window.CouriusDialogs = DialogManager;
