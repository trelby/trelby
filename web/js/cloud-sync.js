/**
 * Courius - Cloud Sync Module
 * Provides integration with Google Drive, Dropbox, and OneDrive
 */

class CloudSync {
    constructor(app) {
        this.app = app;
        this.providers = new Map();
        this.activeProvider = null;
        this.syncStatus = 'disconnected';
        this.lastSync = null;
        this.autoSync = false;
        this.syncInterval = null;

        this._init();
    }

    /**
     * Initialize cloud sync
     */
    _init() {
        // Register built-in providers
        this._registerProvider('googledrive', new GoogleDriveProvider());
        this._registerProvider('dropbox', new DropboxProvider());
        this._registerProvider('onedrive', new OneDriveProvider());

        // Load settings
        this._loadSettings();

        // Setup auto-sync if enabled
        if (this.autoSync && this.activeProvider) {
            this._startAutoSync();
        }
    }

    /**
     * Register a cloud provider
     */
    _registerProvider(id, provider) {
        this.providers.set(id, provider);
    }

    /**
     * Load settings from localStorage
     */
    _loadSettings() {
        const settings = localStorage.getItem('courius-cloud-settings');
        if (settings) {
            try {
                const data = JSON.parse(settings);
                this.activeProvider = data.activeProvider;
                this.autoSync = data.autoSync || false;
                this.lastSync = data.lastSync;
            } catch (e) {
                console.warn('Failed to load cloud settings:', e);
            }
        }
    }

    /**
     * Save settings to localStorage
     */
    _saveSettings() {
        localStorage.setItem('courius-cloud-settings', JSON.stringify({
            activeProvider: this.activeProvider,
            autoSync: this.autoSync,
            lastSync: this.lastSync
        }));
    }

    /**
     * Get available providers
     */
    getProviders() {
        return [...this.providers.entries()].map(([id, provider]) => ({
            id,
            name: provider.name,
            icon: provider.icon,
            connected: provider.isConnected()
        }));
    }

    /**
     * Connect to a cloud provider
     */
    async connect(providerId) {
        const provider = this.providers.get(providerId);
        if (!provider) {
            throw new Error(`Unknown provider: ${providerId}`);
        }

        this.syncStatus = 'connecting';
        this._notifyStatusChange();

        try {
            await provider.connect();
            this.activeProvider = providerId;
            this.syncStatus = 'connected';
            this._saveSettings();
            this._notifyStatusChange();

            return true;
        } catch (e) {
            this.syncStatus = 'error';
            this._notifyStatusChange();
            throw e;
        }
    }

    /**
     * Disconnect from current provider
     */
    async disconnect() {
        if (this.activeProvider) {
            const provider = this.providers.get(this.activeProvider);
            if (provider) {
                await provider.disconnect();
            }
        }

        this.activeProvider = null;
        this.syncStatus = 'disconnected';
        this._stopAutoSync();
        this._saveSettings();
        this._notifyStatusChange();
    }

    /**
     * Sync current file to cloud
     */
    async sync() {
        if (!this.activeProvider) {
            throw new Error('No cloud provider connected');
        }

        const provider = this.providers.get(this.activeProvider);
        if (!provider || !provider.isConnected()) {
            throw new Error('Provider not connected');
        }

        this.syncStatus = 'syncing';
        this._notifyStatusChange();

        try {
            const screenplay = this.app.editor?.getScreenplay();
            if (!screenplay) {
                throw new Error('No screenplay to sync');
            }

            const filename = this.app.fileIO?.getFilename() || 'Untitled.trelby';
            const content = this.app.fileIO?.serializeScreenplay(screenplay);

            await provider.uploadFile(filename, content);

            this.lastSync = new Date().toISOString();
            this.syncStatus = 'connected';
            this._saveSettings();
            this._notifyStatusChange();

            window.CouriusUtils?.toast('Synced to cloud', 'success');
            return true;
        } catch (e) {
            this.syncStatus = 'error';
            this._notifyStatusChange();
            throw e;
        }
    }

    /**
     * List files from cloud
     */
    async listFiles() {
        if (!this.activeProvider) {
            throw new Error('No cloud provider connected');
        }

        const provider = this.providers.get(this.activeProvider);
        if (!provider || !provider.isConnected()) {
            throw new Error('Provider not connected');
        }

        return provider.listFiles();
    }

    /**
     * Download file from cloud
     */
    async downloadFile(fileId) {
        if (!this.activeProvider) {
            throw new Error('No cloud provider connected');
        }

        const provider = this.providers.get(this.activeProvider);
        if (!provider || !provider.isConnected()) {
            throw new Error('Provider not connected');
        }

        return provider.downloadFile(fileId);
    }

    /**
     * Delete file from cloud
     */
    async deleteFile(fileId) {
        if (!this.activeProvider) {
            throw new Error('No cloud provider connected');
        }

        const provider = this.providers.get(this.activeProvider);
        return provider.deleteFile(fileId);
    }

    /**
     * Enable/disable auto-sync
     */
    setAutoSync(enabled) {
        this.autoSync = enabled;
        this._saveSettings();

        if (enabled) {
            this._startAutoSync();
        } else {
            this._stopAutoSync();
        }
    }

    /**
     * Start auto-sync interval
     */
    _startAutoSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }

        // Sync every 5 minutes
        this.syncInterval = setInterval(() => {
            if (this.app.editor?.hasUnsavedChanges()) {
                this.sync().catch(e => console.warn('Auto-sync failed:', e));
            }
        }, 5 * 60 * 1000);
    }

    /**
     * Stop auto-sync
     */
    _stopAutoSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
    }

    /**
     * Notify status change
     */
    _notifyStatusChange() {
        const event = new CustomEvent('cloud-sync-status', {
            detail: {
                status: this.syncStatus,
                provider: this.activeProvider,
                lastSync: this.lastSync
            }
        });
        document.dispatchEvent(event);
    }

    /**
     * Get current status
     */
    getStatus() {
        return {
            status: this.syncStatus,
            provider: this.activeProvider,
            lastSync: this.lastSync,
            autoSync: this.autoSync
        };
    }
}

/**
 * Base class for cloud providers
 */
class CloudProvider {
    constructor() {
        this.name = 'Unknown';
        this.icon = '☁️';
        this.connected = false;
        this.accessToken = null;
    }

    isConnected() {
        return this.connected && this.accessToken;
    }

    async connect() {
        throw new Error('Not implemented');
    }

    async disconnect() {
        this.connected = false;
        this.accessToken = null;
    }

    async uploadFile(filename, content) {
        throw new Error('Not implemented');
    }

    async downloadFile(fileId) {
        throw new Error('Not implemented');
    }

    async listFiles() {
        throw new Error('Not implemented');
    }

    async deleteFile(fileId) {
        throw new Error('Not implemented');
    }
}

/**
 * Google Drive Provider
 */
class GoogleDriveProvider extends CloudProvider {
    constructor() {
        super();
        this.name = 'Google Drive';
        this.icon = '📁';
        this.clientId = ''; // Set your client ID here
        this.scope = 'https://www.googleapis.com/auth/drive.file';
    }

    async connect() {
        // OAuth flow would go here
        // For demo purposes, show a placeholder
        return new Promise((resolve, reject) => {
            // In production, this would open OAuth popup
            const confirmed = confirm(
                'Connect to Google Drive?\n\n' +
                'Note: In production, this would open Google OAuth.\n' +
                'For demo, this simulates a successful connection.'
            );

            if (confirmed) {
                this.connected = true;
                this.accessToken = 'demo-token';
                localStorage.setItem('courius-gdrive-token', this.accessToken);
                resolve();
            } else {
                reject(new Error('User cancelled'));
            }
        });
    }

    async disconnect() {
        await super.disconnect();
        localStorage.removeItem('courius-gdrive-token');
    }

    async uploadFile(filename, content) {
        if (!this.isConnected()) throw new Error('Not connected');

        // In production, this would use Google Drive API
        console.log(`Would upload ${filename} to Google Drive`);

        // Store locally for demo
        const files = JSON.parse(localStorage.getItem('courius-gdrive-files') || '[]');
        const existing = files.findIndex(f => f.name === filename);

        const fileData = {
            id: existing >= 0 ? files[existing].id : Date.now().toString(36),
            name: filename,
            content,
            modified: new Date().toISOString()
        };

        if (existing >= 0) {
            files[existing] = fileData;
        } else {
            files.push(fileData);
        }

        localStorage.setItem('courius-gdrive-files', JSON.stringify(files));
        return fileData.id;
    }

    async listFiles() {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-gdrive-files') || '[]');
        return files.map(f => ({
            id: f.id,
            name: f.name,
            modified: f.modified
        }));
    }

    async downloadFile(fileId) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-gdrive-files') || '[]');
        const file = files.find(f => f.id === fileId);

        if (!file) throw new Error('File not found');
        return { name: file.name, content: file.content };
    }

    async deleteFile(fileId) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-gdrive-files') || '[]');
        const index = files.findIndex(f => f.id === fileId);

        if (index >= 0) {
            files.splice(index, 1);
            localStorage.setItem('courius-gdrive-files', JSON.stringify(files));
        }
    }
}

/**
 * Dropbox Provider
 */
class DropboxProvider extends CloudProvider {
    constructor() {
        super();
        this.name = 'Dropbox';
        this.icon = '📦';
    }

    async connect() {
        return new Promise((resolve, reject) => {
            const confirmed = confirm(
                'Connect to Dropbox?\n\n' +
                'Note: In production, this would open Dropbox OAuth.\n' +
                'For demo, this simulates a successful connection.'
            );

            if (confirmed) {
                this.connected = true;
                this.accessToken = 'demo-token';
                localStorage.setItem('courius-dropbox-token', this.accessToken);
                resolve();
            } else {
                reject(new Error('User cancelled'));
            }
        });
    }

    async disconnect() {
        await super.disconnect();
        localStorage.removeItem('courius-dropbox-token');
    }

    async uploadFile(filename, content) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-dropbox-files') || '[]');
        const existing = files.findIndex(f => f.name === filename);

        const fileData = {
            id: existing >= 0 ? files[existing].id : Date.now().toString(36),
            name: filename,
            content,
            modified: new Date().toISOString()
        };

        if (existing >= 0) {
            files[existing] = fileData;
        } else {
            files.push(fileData);
        }

        localStorage.setItem('courius-dropbox-files', JSON.stringify(files));
        return fileData.id;
    }

    async listFiles() {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-dropbox-files') || '[]');
        return files.map(f => ({
            id: f.id,
            name: f.name,
            modified: f.modified
        }));
    }

    async downloadFile(fileId) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-dropbox-files') || '[]');
        const file = files.find(f => f.id === fileId);

        if (!file) throw new Error('File not found');
        return { name: file.name, content: file.content };
    }

    async deleteFile(fileId) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-dropbox-files') || '[]');
        const index = files.findIndex(f => f.id === fileId);

        if (index >= 0) {
            files.splice(index, 1);
            localStorage.setItem('courius-dropbox-files', JSON.stringify(files));
        }
    }
}

/**
 * OneDrive Provider
 */
class OneDriveProvider extends CloudProvider {
    constructor() {
        super();
        this.name = 'OneDrive';
        this.icon = '☁️';
    }

    async connect() {
        return new Promise((resolve, reject) => {
            const confirmed = confirm(
                'Connect to OneDrive?\n\n' +
                'Note: In production, this would open Microsoft OAuth.\n' +
                'For demo, this simulates a successful connection.'
            );

            if (confirmed) {
                this.connected = true;
                this.accessToken = 'demo-token';
                localStorage.setItem('courius-onedrive-token', this.accessToken);
                resolve();
            } else {
                reject(new Error('User cancelled'));
            }
        });
    }

    async disconnect() {
        await super.disconnect();
        localStorage.removeItem('courius-onedrive-token');
    }

    async uploadFile(filename, content) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-onedrive-files') || '[]');
        const existing = files.findIndex(f => f.name === filename);

        const fileData = {
            id: existing >= 0 ? files[existing].id : Date.now().toString(36),
            name: filename,
            content,
            modified: new Date().toISOString()
        };

        if (existing >= 0) {
            files[existing] = fileData;
        } else {
            files.push(fileData);
        }

        localStorage.setItem('courius-onedrive-files', JSON.stringify(files));
        return fileData.id;
    }

    async listFiles() {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-onedrive-files') || '[]');
        return files.map(f => ({
            id: f.id,
            name: f.name,
            modified: f.modified
        }));
    }

    async downloadFile(fileId) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-onedrive-files') || '[]');
        const file = files.find(f => f.id === fileId);

        if (!file) throw new Error('File not found');
        return { name: file.name, content: file.content };
    }

    async deleteFile(fileId) {
        if (!this.isConnected()) throw new Error('Not connected');

        const files = JSON.parse(localStorage.getItem('courius-onedrive-files') || '[]');
        const index = files.findIndex(f => f.id === fileId);

        if (index >= 0) {
            files.splice(index, 1);
            localStorage.setItem('courius-onedrive-files', JSON.stringify(files));
        }
    }
}

window.CouriusCloudSync = CloudSync;
