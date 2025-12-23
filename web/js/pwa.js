/**
 * Courius - Progressive Web App Support
 * Service worker registration, offline support, and PWA features
 */

class PWAManager {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.isOnline = navigator.onLine;

        this._init();
    }

    /**
     * Initialize PWA features
     */
    async _init() {
        // Check if already installed
        this.isInstalled = window.matchMedia('(display-mode: standalone)').matches ||
                          window.navigator.standalone === true;

        // Register service worker
        await this._registerServiceWorker();

        // Setup install prompt
        this._setupInstallPrompt();

        // Setup online/offline detection
        this._setupNetworkDetection();

        // Setup app update detection
        this._setupUpdateDetection();
    }

    /**
     * Register service worker
     */
    async _registerServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            console.log('Service workers not supported');
            return;
        }

        try {
            const registration = await navigator.serviceWorker.register('/web/sw.js', {
                scope: '/web/'
            });

            console.log('Service Worker registered:', registration.scope);

            // Check for updates periodically
            setInterval(() => {
                registration.update();
            }, 60 * 60 * 1000); // Check every hour

            this.registration = registration;
        } catch (error) {
            console.error('Service Worker registration failed:', error);
        }
    }

    /**
     * Setup install prompt handling
     */
    _setupInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;

            // Show install button if not already installed
            if (!this.isInstalled) {
                this._showInstallButton();
            }
        });

        window.addEventListener('appinstalled', () => {
            this.isInstalled = true;
            this.deferredPrompt = null;
            this._hideInstallButton();
            window.CouriusUtils?.toast('App installed successfully!', 'success');
        });
    }

    /**
     * Show install button in UI
     */
    _showInstallButton() {
        const existingBtn = document.getElementById('pwa-install-btn');
        if (existingBtn) return;

        const toolbar = document.querySelector('#toolbar');
        if (!toolbar) return;

        const btn = document.createElement('button');
        btn.id = 'pwa-install-btn';
        btn.className = 'toolbar-btn pwa-install';
        btn.title = 'Install App';
        btn.setAttribute('aria-label', 'Install Courius as app');
        btn.innerHTML = '📲';
        btn.addEventListener('click', () => this.promptInstall());

        toolbar.appendChild(btn);
    }

    /**
     * Hide install button
     */
    _hideInstallButton() {
        const btn = document.getElementById('pwa-install-btn');
        if (btn) btn.remove();
    }

    /**
     * Prompt user to install PWA
     */
    async promptInstall() {
        if (!this.deferredPrompt) {
            window.CouriusUtils?.toast('App is already installed or install not available', 'info');
            return false;
        }

        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;

        if (outcome === 'accepted') {
            console.log('User accepted install prompt');
        } else {
            console.log('User dismissed install prompt');
        }

        this.deferredPrompt = null;
        return outcome === 'accepted';
    }

    /**
     * Setup network detection
     */
    _setupNetworkDetection() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this._updateNetworkStatus();
            window.CouriusUtils?.toast('Back online', 'success');
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this._updateNetworkStatus();
            window.CouriusUtils?.toast('You are offline. Changes will sync when connected.', 'warning');
        });

        this._updateNetworkStatus();
    }

    /**
     * Update network status indicator
     */
    _updateNetworkStatus() {
        document.body.classList.toggle('offline', !this.isOnline);

        const indicator = document.getElementById('network-status');
        if (indicator) {
            indicator.textContent = this.isOnline ? '🌐' : '📴';
            indicator.title = this.isOnline ? 'Online' : 'Offline';
        }
    }

    /**
     * Setup app update detection
     */
    _setupUpdateDetection() {
        if (!this.registration) return;

        this.registration.addEventListener('updatefound', () => {
            const newWorker = this.registration.installing;

            newWorker.addEventListener('statechange', () => {
                if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                    this._showUpdateAvailable();
                }
            });
        });
    }

    /**
     * Show update available notification
     */
    _showUpdateAvailable() {
        const updateBanner = document.createElement('div');
        updateBanner.className = 'update-banner';
        updateBanner.innerHTML = `
            <span>A new version of Courius is available!</span>
            <button id="update-app-btn">Update Now</button>
            <button id="dismiss-update-btn">Later</button>
        `;

        document.body.appendChild(updateBanner);

        document.getElementById('update-app-btn').addEventListener('click', () => {
            this._applyUpdate();
        });

        document.getElementById('dismiss-update-btn').addEventListener('click', () => {
            updateBanner.remove();
        });
    }

    /**
     * Apply pending update
     */
    _applyUpdate() {
        if (this.registration?.waiting) {
            this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
        }
        window.location.reload();
    }

    /**
     * Check if app can work offline
     */
    canWorkOffline() {
        return 'serviceWorker' in navigator && this.registration?.active;
    }

    /**
     * Get install status
     */
    getStatus() {
        return {
            isInstalled: this.isInstalled,
            canInstall: !!this.deferredPrompt,
            isOnline: this.isOnline,
            canWorkOffline: this.canWorkOffline()
        };
    }

    /**
     * Clear offline cache
     */
    async clearCache() {
        if ('caches' in window) {
            const keys = await caches.keys();
            await Promise.all(keys.map(key => caches.delete(key)));
            window.CouriusUtils?.toast('Cache cleared', 'success');
        }
    }
}

window.CouriusPWA = PWAManager;
