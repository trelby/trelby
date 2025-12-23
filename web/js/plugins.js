/**
 * Courius - Plugin Architecture
 * Provides a sandboxed plugin system for extending functionality
 */

class PluginManager {
    constructor(app) {
        this.app = app;
        this.plugins = new Map();
        this.hooks = new Map();
        this.api = this._createAPI();

        this._init();
    }

    /**
     * Initialize plugin system
     */
    _init() {
        // Register core hooks
        this._registerCoreHooks();

        // Load installed plugins from localStorage
        this._loadInstalledPlugins();
    }

    /**
     * Create the plugin API (sandboxed interface)
     */
    _createAPI() {
        const self = this;

        return {
            // Plugin registration
            register: (metadata, plugin) => self._registerPlugin(metadata, plugin),

            // Event hooks
            on: (event, callback) => self._addHook(event, callback),
            off: (event, callback) => self._removeHook(event, callback),
            emit: (event, data) => self._emitHook(event, data),

            // Editor operations (read-only where appropriate)
            editor: {
                getScreenplay: () => self.app.editor?.getScreenplay(),
                getCurrentLine: () => {
                    const editor = self.app.editor;
                    if (!editor) return null;
                    const index = editor._getCurrentLineIndex();
                    return index >= 0 ? editor.screenplay.getLine(index) : null;
                },
                getCurrentLineIndex: () => self.app.editor?._getCurrentLineIndex() || 0,
                getLineCount: () => self.app.editor?.screenplay?.lineCount || 0,
                getWordCount: () => self.app.editor?.screenplay?.getWordCount() || 0,
                getPageCount: () => self.app.editor?.screenplay?.getPageCount() || 0,

                // Write operations require explicit permission
                insertText: (text) => {
                    if (!self._hasPermission('write')) return false;
                    document.execCommand('insertText', false, text);
                    return true;
                },
                setLineType: (index, type) => {
                    if (!self._hasPermission('write')) return false;
                    self.app.editor?.setLineType(index, type);
                    return true;
                }
            },

            // UI operations
            ui: {
                showNotification: (message, type) => {
                    window.CouriusUtils?.toast(message, type);
                },
                showDialog: (options) => {
                    return self.app.dialogs?.show(options);
                },
                addToolbarButton: (config) => self._addToolbarButton(config),
                addMenuItem: (menu, config) => self._addMenuItem(menu, config),
                addSidebarPanel: (config) => self._addSidebarPanel(config)
            },

            // Storage (namespaced per plugin)
            storage: {
                get: (key) => self._getPluginStorage(key),
                set: (key, value) => self._setPluginStorage(key, value),
                remove: (key) => self._removePluginStorage(key)
            },

            // Utilities
            utils: {
                escapeHTML: (str) => window.CouriusSecurity?.escapeHTML(str) || str,
                formatDuration: (mins) => window.CouriusUtils?.formatDuration(mins),
                debounce: (fn, delay) => window.CouriusUtils?.debounce(fn, delay)
            },

            // Constants (read-only)
            constants: {
                LINE_TYPES: { ...window.CouriusConstants?.LINE_TYPE },
                VERSION: { ...window.CouriusConstants?.VERSION }
            }
        };
    }

    /**
     * Register core hooks
     */
    _registerCoreHooks() {
        const events = [
            'screenplay:new',
            'screenplay:open',
            'screenplay:save',
            'screenplay:modified',
            'line:changed',
            'line:added',
            'line:removed',
            'line:typeChanged',
            'cursor:moved',
            'view:changed',
            'export:before',
            'export:after',
            'plugin:loaded',
            'plugin:unloaded'
        ];

        for (const event of events) {
            this.hooks.set(event, []);
        }
    }

    /**
     * Register a plugin
     */
    _registerPlugin(metadata, pluginFactory) {
        const requiredFields = ['id', 'name', 'version'];
        for (const field of requiredFields) {
            if (!metadata[field]) {
                console.error(`Plugin missing required field: ${field}`);
                return false;
            }
        }

        // Check for duplicate
        if (this.plugins.has(metadata.id)) {
            console.warn(`Plugin ${metadata.id} is already registered`);
            return false;
        }

        // Create plugin instance
        const plugin = {
            metadata: {
                id: metadata.id,
                name: metadata.name,
                version: metadata.version,
                author: metadata.author || 'Unknown',
                description: metadata.description || '',
                permissions: metadata.permissions || [],
                enabled: true
            },
            instance: null,
            hooks: []
        };

        try {
            // Create sandboxed instance
            plugin.instance = pluginFactory(this.api);

            // Initialize plugin
            if (typeof plugin.instance.init === 'function') {
                plugin.instance.init();
            }

            this.plugins.set(metadata.id, plugin);
            this._saveInstalledPlugins();
            this._emitHook('plugin:loaded', { pluginId: metadata.id });

            console.log(`Plugin loaded: ${metadata.name} v${metadata.version}`);
            return true;
        } catch (e) {
            console.error(`Failed to load plugin ${metadata.id}:`, e);
            return false;
        }
    }

    /**
     * Unload a plugin
     */
    unloadPlugin(pluginId) {
        const plugin = this.plugins.get(pluginId);
        if (!plugin) return false;

        try {
            // Call cleanup
            if (typeof plugin.instance?.destroy === 'function') {
                plugin.instance.destroy();
            }

            // Remove hooks
            for (const { event, callback } of plugin.hooks) {
                this._removeHook(event, callback);
            }

            this.plugins.delete(pluginId);
            this._saveInstalledPlugins();
            this._emitHook('plugin:unloaded', { pluginId });

            return true;
        } catch (e) {
            console.error(`Failed to unload plugin ${pluginId}:`, e);
            return false;
        }
    }

    /**
     * Enable/disable a plugin
     */
    setPluginEnabled(pluginId, enabled) {
        const plugin = this.plugins.get(pluginId);
        if (!plugin) return false;

        plugin.metadata.enabled = enabled;

        if (enabled && typeof plugin.instance?.enable === 'function') {
            plugin.instance.enable();
        } else if (!enabled && typeof plugin.instance?.disable === 'function') {
            plugin.instance.disable();
        }

        this._saveInstalledPlugins();
        return true;
    }

    /**
     * Add a hook listener
     */
    _addHook(event, callback) {
        if (!this.hooks.has(event)) {
            this.hooks.set(event, []);
        }
        this.hooks.get(event).push(callback);

        // Track which plugin added this hook
        const currentPlugin = this._getCurrentPluginContext();
        if (currentPlugin) {
            currentPlugin.hooks.push({ event, callback });
        }
    }

    /**
     * Remove a hook listener
     */
    _removeHook(event, callback) {
        const hooks = this.hooks.get(event);
        if (hooks) {
            const index = hooks.indexOf(callback);
            if (index !== -1) {
                hooks.splice(index, 1);
            }
        }
    }

    /**
     * Emit a hook event
     */
    _emitHook(event, data = {}) {
        const hooks = this.hooks.get(event);
        if (hooks) {
            for (const callback of hooks) {
                try {
                    callback(data);
                } catch (e) {
                    console.error(`Hook error for ${event}:`, e);
                }
            }
        }
    }

    /**
     * Emit hook (public method for app to use)
     */
    emit(event, data) {
        this._emitHook(event, data);
    }

    /**
     * Check if current plugin has permission
     */
    _hasPermission(permission) {
        const plugin = this._getCurrentPluginContext();
        if (!plugin) return true; // Internal call

        return plugin.metadata.permissions.includes(permission) ||
               plugin.metadata.permissions.includes('*');
    }

    /**
     * Get current plugin context (for permission checking)
     */
    _getCurrentPluginContext() {
        // This would need stack trace analysis in a real implementation
        // For simplicity, we return null (allowing all operations internally)
        return null;
    }

    /**
     * Plugin storage operations
     */
    _getPluginStorage(key) {
        const plugin = this._getCurrentPluginContext();
        const prefix = plugin ? `courius-plugin-${plugin.metadata.id}-` : 'courius-plugin-';
        const stored = localStorage.getItem(prefix + key);
        return stored ? JSON.parse(stored) : null;
    }

    _setPluginStorage(key, value) {
        const plugin = this._getCurrentPluginContext();
        const prefix = plugin ? `courius-plugin-${plugin.metadata.id}-` : 'courius-plugin-';
        localStorage.setItem(prefix + key, JSON.stringify(value));
    }

    _removePluginStorage(key) {
        const plugin = this._getCurrentPluginContext();
        const prefix = plugin ? `courius-plugin-${plugin.metadata.id}-` : 'courius-plugin-';
        localStorage.removeItem(prefix + key);
    }

    /**
     * Add toolbar button
     */
    _addToolbarButton(config) {
        const toolbar = document.querySelector('#toolbar .plugin-buttons');
        if (!toolbar) {
            // Create plugin buttons container
            const container = document.createElement('div');
            container.className = 'toolbar-group plugin-buttons';
            document.querySelector('#toolbar')?.appendChild(container);
        }

        const button = document.createElement('button');
        button.className = 'toolbar-btn';
        button.title = config.tooltip || config.label;
        button.setAttribute('aria-label', config.label);
        button.innerHTML = config.icon || config.label;
        button.addEventListener('click', config.onClick);

        document.querySelector('#toolbar .plugin-buttons')?.appendChild(button);

        return () => button.remove();
    }

    /**
     * Add menu item
     */
    _addMenuItem(menuId, config) {
        const menu = document.querySelector(`#${menuId}-menu`);
        if (!menu) return null;

        const item = document.createElement('div');
        item.className = 'menu-item';
        item.textContent = config.label;
        item.addEventListener('click', config.onClick);

        menu.appendChild(item);

        return () => item.remove();
    }

    /**
     * Add sidebar panel
     */
    _addSidebarPanel(config) {
        // Create panel in scene navigator area
        const sidebar = document.querySelector('#scene-navigator');
        if (!sidebar) return null;

        const panel = document.createElement('div');
        panel.className = 'plugin-panel';
        panel.id = `plugin-panel-${config.id}`;
        panel.innerHTML = `
            <div class="plugin-panel-header">
                <h4>${window.CouriusSecurity?.escapeHTML(config.title) || config.title}</h4>
                <button class="panel-close">&times;</button>
            </div>
            <div class="plugin-panel-content"></div>
        `;

        panel.querySelector('.panel-close').addEventListener('click', () => {
            panel.classList.toggle('collapsed');
        });

        sidebar.appendChild(panel);

        return {
            setContent: (html) => {
                panel.querySelector('.plugin-panel-content').innerHTML = html;
            },
            remove: () => panel.remove()
        };
    }

    /**
     * Save installed plugins to localStorage
     */
    _saveInstalledPlugins() {
        const installed = [...this.plugins.values()].map(p => ({
            id: p.metadata.id,
            enabled: p.metadata.enabled
        }));
        localStorage.setItem('courius-plugins', JSON.stringify(installed));
    }

    /**
     * Load installed plugins
     */
    _loadInstalledPlugins() {
        const stored = localStorage.getItem('courius-plugins');
        if (!stored) return;

        // Plugin scripts would need to be loaded here
        // For now, this just restores enabled/disabled state
    }

    /**
     * Get all registered plugins
     */
    getPlugins() {
        return [...this.plugins.values()].map(p => ({
            ...p.metadata,
            hasInit: typeof p.instance?.init === 'function',
            hasDestroy: typeof p.instance?.destroy === 'function'
        }));
    }

    /**
     * Get plugin by ID
     */
    getPlugin(id) {
        return this.plugins.get(id)?.metadata || null;
    }

    /**
     * Install plugin from URL
     */
    async installFromURL(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch plugin');

            const script = await response.text();

            // Basic security check
            if (script.includes('eval(') || script.includes('Function(')) {
                throw new Error('Plugin contains potentially unsafe code');
            }

            // Create sandboxed execution
            const pluginFunction = new Function('CouriusPlugin', script);
            pluginFunction(this.api);

            return true;
        } catch (e) {
            console.error('Failed to install plugin:', e);
            return false;
        }
    }
}

// Built-in plugins

/**
 * Word Count Goals Plugin
 */
const WordCountGoalsPlugin = (api) => ({
    init() {
        this.goal = api.storage.get('wordGoal') || 0;
        this.sessionStart = api.editor.getWordCount();

        if (this.goal > 0) {
            this._createUI();
        }

        api.on('screenplay:modified', () => this._updateProgress());
    },

    _createUI() {
        this.removeButton = api.ui.addToolbarButton({
            icon: '🎯',
            label: 'Word Goal',
            tooltip: 'Word count goal',
            onClick: () => this._showGoalDialog()
        });
    },

    _showGoalDialog() {
        api.ui.showDialog({
            title: 'Word Count Goal',
            content: `
                <div class="goal-dialog">
                    <label>Daily goal:
                        <input type="number" id="word-goal" value="${this.goal}" min="0">
                    </label>
                    <p>Current: ${api.editor.getWordCount()} words</p>
                    <p>Session: ${api.editor.getWordCount() - this.sessionStart} words</p>
                </div>
            `,
            buttons: [
                { text: 'Cancel', action: 'close' },
                {
                    text: 'Set Goal',
                    primary: true,
                    action: (dlg) => {
                        this.goal = parseInt(dlg.querySelector('#word-goal').value) || 0;
                        api.storage.set('wordGoal', this.goal);
                        this._updateProgress();
                        return true;
                    }
                }
            ]
        });
    },

    _updateProgress() {
        if (this.goal <= 0) return;

        const current = api.editor.getWordCount();
        const progress = Math.min(100, Math.round((current / this.goal) * 100));

        if (current >= this.goal) {
            api.ui.showNotification('🎉 You reached your word goal!', 'success');
        }
    },

    destroy() {
        if (this.removeButton) this.removeButton();
    }
});

/**
 * Pomodoro Timer Plugin
 */
const PomodoroPlugin = (api) => ({
    init() {
        this.workDuration = 25 * 60; // 25 minutes
        this.breakDuration = 5 * 60; // 5 minutes
        this.isRunning = false;
        this.isBreak = false;
        this.timeLeft = this.workDuration;

        this.removeButton = api.ui.addToolbarButton({
            icon: '🍅',
            label: 'Pomodoro',
            tooltip: 'Pomodoro Timer',
            onClick: () => this._toggleTimer()
        });
    },

    _toggleTimer() {
        if (this.isRunning) {
            this._stopTimer();
        } else {
            this._startTimer();
        }
    },

    _startTimer() {
        this.isRunning = true;
        this.timeLeft = this.isBreak ? this.breakDuration : this.workDuration;

        api.ui.showNotification(
            this.isBreak ? '☕ Break time!' : '🍅 Focus time started!',
            'info'
        );

        this.interval = setInterval(() => {
            this.timeLeft--;

            if (this.timeLeft <= 0) {
                this._timerComplete();
            }
        }, 1000);
    },

    _stopTimer() {
        this.isRunning = false;
        if (this.interval) {
            clearInterval(this.interval);
        }
        api.ui.showNotification('Timer stopped', 'info');
    },

    _timerComplete() {
        this._stopTimer();

        if (this.isBreak) {
            api.ui.showNotification('☕ Break over! Ready to focus?', 'success');
        } else {
            api.ui.showNotification('🍅 Pomodoro complete! Take a break.', 'success');
        }

        this.isBreak = !this.isBreak;
    },

    destroy() {
        if (this.interval) clearInterval(this.interval);
        if (this.removeButton) this.removeButton();
    }
});

window.CouriusPlugins = PluginManager;
window.CouriusBuiltinPlugins = {
    WordCountGoals: WordCountGoalsPlugin,
    Pomodoro: PomodoroPlugin
};
