/**
 * Courius - Accessibility Module
 * Provides ARIA support, keyboard navigation, screen reader support, and focus management
 */

class AccessibilityManager {
    constructor() {
        this.announcer = null;
        this.focusTrap = null;
        this.lastFocusedElement = null;
        this.reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

        this._init();
    }

    /**
     * Initialize accessibility features
     */
    _init() {
        this._createAnnouncer();
        this._setupReducedMotionListener();
        this._setupKeyboardNavigation();
        this._addARIALabels();
        this._setupSkipLinks();
    }

    /**
     * Create live region for screen reader announcements
     */
    _createAnnouncer() {
        this.announcer = document.createElement('div');
        this.announcer.id = 'sr-announcer';
        this.announcer.setAttribute('role', 'status');
        this.announcer.setAttribute('aria-live', 'polite');
        this.announcer.setAttribute('aria-atomic', 'true');
        this.announcer.className = 'sr-only';
        document.body.appendChild(this.announcer);

        // Also create an assertive announcer for important messages
        this.assertiveAnnouncer = document.createElement('div');
        this.assertiveAnnouncer.id = 'sr-announcer-assertive';
        this.assertiveAnnouncer.setAttribute('role', 'alert');
        this.assertiveAnnouncer.setAttribute('aria-live', 'assertive');
        this.assertiveAnnouncer.setAttribute('aria-atomic', 'true');
        this.assertiveAnnouncer.className = 'sr-only';
        document.body.appendChild(this.assertiveAnnouncer);
    }

    /**
     * Announce message to screen readers
     */
    announce(message, priority = 'polite') {
        const announcer = priority === 'assertive' ? this.assertiveAnnouncer : this.announcer;

        // Clear and set message (forces re-announcement)
        announcer.textContent = '';
        setTimeout(() => {
            announcer.textContent = message;
        }, 50);
    }

    /**
     * Listen for reduced motion preference changes
     */
    _setupReducedMotionListener() {
        const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
        mediaQuery.addEventListener('change', (e) => {
            this.reducedMotion = e.matches;
            document.body.classList.toggle('reduced-motion', this.reducedMotion);
        });

        if (this.reducedMotion) {
            document.body.classList.add('reduced-motion');
        }
    }

    /**
     * Setup global keyboard navigation
     */
    _setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Show focus outline when using keyboard
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }

            // F6 - Move between major regions
            if (e.key === 'F6') {
                e.preventDefault();
                this._cycleFocusRegions(e.shiftKey);
            }

            // Escape - Close dialogs and menus
            if (e.key === 'Escape') {
                this._handleEscape();
            }
        });

        // Remove focus outline on mouse use
        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }

    /**
     * Cycle focus between major page regions
     */
    _cycleFocusRegions(reverse = false) {
        const regions = [
            document.querySelector('#menu-bar'),
            document.querySelector('#toolbar'),
            document.querySelector('#screenplay-editor'),
            document.querySelector('#status-bar')
        ].filter(Boolean);

        const currentIndex = regions.findIndex(r => r.contains(document.activeElement));
        let nextIndex;

        if (reverse) {
            nextIndex = currentIndex <= 0 ? regions.length - 1 : currentIndex - 1;
        } else {
            nextIndex = (currentIndex + 1) % regions.length;
        }

        const nextRegion = regions[nextIndex];
        const focusable = this._getFocusableElements(nextRegion)[0];
        if (focusable) {
            focusable.focus();
            this.announce(`${nextRegion.getAttribute('aria-label') || 'Region'}`);
        }
    }

    /**
     * Handle Escape key
     */
    _handleEscape() {
        // Close any open dropdowns
        document.querySelectorAll('.menu-dropdown.show').forEach(menu => {
            menu.classList.remove('show');
        });

        // Close autocomplete
        const autocomplete = document.querySelector('.autocomplete-popup');
        if (autocomplete) {
            autocomplete.remove();
        }
    }

    /**
     * Add ARIA labels to interactive elements
     */
    _addARIALabels() {
        // Main regions
        const menuBar = document.querySelector('#menu-bar');
        if (menuBar) {
            menuBar.setAttribute('role', 'menubar');
            menuBar.setAttribute('aria-label', 'Main menu');
        }

        const toolbar = document.querySelector('#toolbar');
        if (toolbar) {
            toolbar.setAttribute('role', 'toolbar');
            toolbar.setAttribute('aria-label', 'Formatting toolbar');
        }

        const editor = document.querySelector('#screenplay-editor');
        if (editor) {
            editor.setAttribute('role', 'textbox');
            editor.setAttribute('aria-label', 'Screenplay editor');
            editor.setAttribute('aria-multiline', 'true');
            editor.setAttribute('aria-describedby', 'editor-instructions');

            // Add hidden instructions
            const instructions = document.createElement('div');
            instructions.id = 'editor-instructions';
            instructions.className = 'sr-only';
            instructions.textContent = 'Screenplay editor. Use Tab to cycle element types. Press Ctrl+1 through Ctrl+8 to change element type. Press Enter for new line.';
            editor.parentNode.insertBefore(instructions, editor);
        }

        const statusBar = document.querySelector('#status-bar');
        if (statusBar) {
            statusBar.setAttribute('role', 'status');
            statusBar.setAttribute('aria-label', 'Document status');
        }

        // Add labels to toolbar buttons
        this._labelToolbarButtons();

        // Add labels to menu items
        this._labelMenuItems();
    }

    /**
     * Label toolbar buttons with ARIA
     */
    _labelToolbarButtons() {
        const buttonLabels = {
            'new': 'New screenplay',
            'open': 'Open file',
            'save': 'Save file',
            'undo': 'Undo',
            'redo': 'Redo',
            'cut': 'Cut',
            'copy': 'Copy',
            'paste': 'Paste',
            'find': 'Find text',
            'viewDraft': 'Draft view',
            'viewLayout': 'Page layout view',
            'viewSidebyside': 'Side by side view',
            'zoomIn': 'Zoom in',
            'zoomOut': 'Zoom out'
        };

        document.querySelectorAll('.toolbar-btn[data-action]').forEach(btn => {
            const action = btn.dataset.action;
            if (buttonLabels[action]) {
                btn.setAttribute('aria-label', buttonLabels[action]);
                btn.setAttribute('role', 'button');

                // Add tooltip
                if (!btn.title) {
                    btn.title = buttonLabels[action];
                }
            }
        });

        // Element type selector
        const elementSelect = document.querySelector('#element-type');
        if (elementSelect) {
            elementSelect.setAttribute('aria-label', 'Current element type');
        }
    }

    /**
     * Label menu items with ARIA
     */
    _labelMenuItems() {
        // Menu buttons
        document.querySelectorAll('.menu-item').forEach(item => {
            item.setAttribute('role', 'menuitem');
            item.setAttribute('tabindex', '-1');

            // Add keyboard shortcut to aria-description if available
            const shortcut = item.dataset.shortcut;
            if (shortcut) {
                item.setAttribute('aria-keyshortcuts', shortcut);
            }
        });

        // Dropdown menus
        document.querySelectorAll('.menu-dropdown').forEach(dropdown => {
            dropdown.setAttribute('role', 'menu');
        });

        // Top-level menu buttons
        document.querySelectorAll('.menu-btn').forEach(btn => {
            btn.setAttribute('role', 'menuitem');
            btn.setAttribute('aria-haspopup', 'true');
            btn.setAttribute('aria-expanded', 'false');
        });
    }

    /**
     * Setup skip links for keyboard navigation
     */
    _setupSkipLinks() {
        const skipLinks = document.createElement('div');
        skipLinks.className = 'skip-links';
        skipLinks.innerHTML = `
            <a href="#screenplay-editor" class="skip-link">Skip to editor</a>
            <a href="#toolbar" class="skip-link">Skip to toolbar</a>
        `;
        document.body.insertBefore(skipLinks, document.body.firstChild);
    }

    /**
     * Create focus trap for modal dialogs
     */
    trapFocus(container) {
        this.lastFocusedElement = document.activeElement;
        this.focusTrap = container;

        const focusableElements = this._getFocusableElements(container);
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        // Focus first element
        firstElement.focus();

        // Setup trap
        container._focusTrapHandler = (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        };

        container.addEventListener('keydown', container._focusTrapHandler);
    }

    /**
     * Release focus trap
     */
    releaseFocus(container) {
        if (container && container._focusTrapHandler) {
            container.removeEventListener('keydown', container._focusTrapHandler);
        }

        if (this.lastFocusedElement && this.lastFocusedElement.focus) {
            this.lastFocusedElement.focus();
        }

        this.focusTrap = null;
        this.lastFocusedElement = null;
    }

    /**
     * Get all focusable elements within a container
     */
    _getFocusableElements(container) {
        const focusableSelectors = [
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
            '[contenteditable="true"]'
        ].join(', ');

        return [...container.querySelectorAll(focusableSelectors)]
            .filter(el => {
                // Check if element is visible
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden';
            });
    }

    /**
     * Announce current line information for screen readers
     */
    announceLineInfo(lineIndex, elementType, pageNumber) {
        const typeLabels = {
            'scene': 'Scene heading',
            'action': 'Action',
            'character': 'Character',
            'dialogue': 'Dialogue',
            'paren': 'Parenthetical',
            'transition': 'Transition',
            'shot': 'Shot',
            'note': 'Note',
            'actbreak': 'Act break'
        };

        const typeLabel = typeLabels[elementType] || elementType;
        this.announce(`Line ${lineIndex + 1}, ${typeLabel}, Page ${pageNumber}`);
    }

    /**
     * Announce action result
     */
    announceAction(action) {
        this.announce(action);
    }

    /**
     * Announce error
     */
    announceError(error) {
        this.announce(error, 'assertive');
    }

    /**
     * Apply high contrast theme
     */
    setHighContrast(enabled) {
        document.body.classList.toggle('high-contrast', enabled);
        localStorage.setItem('courius-high-contrast', enabled);
    }

    /**
     * Check if high contrast is enabled
     */
    isHighContrastEnabled() {
        return localStorage.getItem('courius-high-contrast') === 'true' ||
            window.matchMedia('(prefers-contrast: more)').matches;
    }

    /**
     * Get formatted shortcut for current platform
     */
    formatShortcut(shortcut) {
        const isMac = navigator.platform.toLowerCase().includes('mac');

        if (isMac) {
            return shortcut
                .replace('Ctrl+', '⌘')
                .replace('Alt+', '⌥')
                .replace('Shift+', '⇧');
        }

        return shortcut;
    }

    /**
     * Check animation preference
     */
    shouldReduceMotion() {
        return this.reducedMotion;
    }
}

window.CouriusAccessibility = AccessibilityManager;
