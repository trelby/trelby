/**
 * Courius - Utility Functions
 */

const Utils = {
    /**
     * Generate a unique ID
     */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    },

    /**
     * Debounce a function
     */
    debounce(fn, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    /**
     * Throttle a function
     */
    throttle(fn, limit) {
        let inThrottle;
        return function (...args) {
            if (!inThrottle) {
                fn.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Escape HTML entities
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Unescape HTML entities
     */
    unescapeHtml(html) {
        const div = document.createElement('div');
        div.innerHTML = html;
        return div.textContent;
    },

    /**
     * Format text for element type
     */
    formatText(text, elementType, config) {
        const { LINE_TYPE, ELEMENT_FORMAT } = window.CouriusConstants;
        const format = config?.elementFormat?.[elementType] || ELEMENT_FORMAT[elementType];

        if (!format) return text;

        let result = text;

        if (format.caps) {
            result = result.toUpperCase();
        }

        return result;
    },

    /**
     * Word wrap text to specified width
     */
    wordWrap(text, width) {
        if (!text || width <= 0) return [text || ''];

        const words = text.split(/\s+/);
        const lines = [];
        let currentLine = '';

        for (const word of words) {
            if (!currentLine) {
                currentLine = word;
            } else if ((currentLine + ' ' + word).length <= width) {
                currentLine += ' ' + word;
            } else {
                lines.push(currentLine);
                currentLine = word;
            }
        }

        if (currentLine) {
            lines.push(currentLine);
        }

        return lines.length > 0 ? lines : [''];
    },

    /**
     * Count words in text
     */
    countWords(text) {
        if (!text) return 0;
        return text.trim().split(/\s+/).filter(w => w.length > 0).length;
    },

    /**
     * Count characters (excluding spaces)
     */
    countChars(text) {
        if (!text) return 0;
        return text.replace(/\s/g, '').length;
    },

    /**
     * Calculate reading time (words per minute)
     */
    calculateReadingTime(wordCount, wpm = 200) {
        return Math.ceil(wordCount / wpm);
    },

    /**
     * Format duration in minutes to "X min" or "X hr Y min"
     */
    formatDuration(minutes) {
        if (minutes < 60) {
            return `${minutes} min`;
        }
        const hours = Math.floor(minutes / 60);
        const mins = minutes % 60;
        return mins > 0 ? `${hours} hr ${mins} min` : `${hours} hr`;
    },

    /**
     * Deep clone an object
     */
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (Array.isArray(obj)) return obj.map(item => Utils.deepClone(item));

        const clone = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clone[key] = Utils.deepClone(obj[key]);
            }
        }
        return clone;
    },

    /**
     * Compare two objects for equality
     */
    deepEqual(a, b) {
        if (a === b) return true;
        if (typeof a !== typeof b) return false;
        if (typeof a !== 'object' || a === null || b === null) return false;

        const keysA = Object.keys(a);
        const keysB = Object.keys(b);

        if (keysA.length !== keysB.length) return false;

        for (const key of keysA) {
            if (!keysB.includes(key) || !Utils.deepEqual(a[key], b[key])) {
                return false;
            }
        }

        return true;
    },

    /**
     * Download a file
     */
    downloadFile(content, filename, mimeType = 'text/plain') {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    /**
     * Read a file as text
     */
    readFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(reader.error);
            reader.readAsText(file);
        });
    },

    /**
     * Show file picker and return selected file
     */
    async pickFile(accept = '.trelby,.fdx,.fountain,.txt') {
        return new Promise((resolve) => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = accept;
            input.onchange = () => {
                resolve(input.files[0] || null);
            };
            input.click();
        });
    },

    /**
     * Get caret position in contenteditable
     */
    getCaretPosition(element) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return { line: 0, offset: 0 };

        const range = selection.getRangeAt(0);
        let lineElement = range.startContainer;

        // Find the line element
        while (lineElement && !lineElement.classList?.contains('line')) {
            lineElement = lineElement.parentElement;
        }

        if (!lineElement) return { line: 0, offset: 0 };

        const lineIndex = parseInt(lineElement.dataset.line || '0', 10);

        // Calculate offset within the line
        const preCaretRange = range.cloneRange();
        preCaretRange.selectNodeContents(lineElement);
        preCaretRange.setEnd(range.endContainer, range.endOffset);
        const offset = preCaretRange.toString().length;

        return { line: lineIndex, offset };
    },

    /**
     * Set caret position in contenteditable
     */
    setCaretPosition(element, lineIndex, offset) {
        const lineElement = element.querySelector(`[data-line="${lineIndex}"]`);
        if (!lineElement) return;

        const range = document.createRange();
        const selection = window.getSelection();

        // Find the text node and offset
        let currentOffset = 0;
        let targetNode = null;
        let targetOffset = 0;

        const walker = document.createTreeWalker(
            lineElement,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );

        while (walker.nextNode()) {
            const node = walker.currentNode;
            const nodeLength = node.textContent.length;

            if (currentOffset + nodeLength >= offset) {
                targetNode = node;
                targetOffset = offset - currentOffset;
                break;
            }
            currentOffset += nodeLength;
        }

        if (!targetNode) {
            // If no text node found, position at start of line
            targetNode = lineElement;
            targetOffset = 0;
        }

        try {
            range.setStart(targetNode, Math.min(targetOffset, targetNode.length || 0));
            range.collapse(true);
            selection.removeAllRanges();
            selection.addRange(range);
        } catch (e) {
            console.warn('Failed to set caret position:', e);
        }
    },

    /**
     * Get selected text
     */
    getSelectedText() {
        const selection = window.getSelection();
        return selection.toString();
    },

    /**
     * Parse shortcut string to event properties
     */
    parseShortcut(shortcut) {
        const parts = shortcut.toLowerCase().split('+');
        return {
            ctrl: parts.includes('ctrl'),
            shift: parts.includes('shift'),
            alt: parts.includes('alt'),
            meta: parts.includes('meta') || parts.includes('cmd'),
            key: parts[parts.length - 1]
        };
    },

    /**
     * Check if keyboard event matches shortcut
     */
    matchShortcut(event, shortcut) {
        const s = typeof shortcut === 'string' ? Utils.parseShortcut(shortcut) : shortcut;

        const eventKey = event.key.toLowerCase();
        const keyMatch = eventKey === s.key || event.code.toLowerCase() === s.key;

        return keyMatch &&
            event.ctrlKey === s.ctrl &&
            event.shiftKey === s.shift &&
            event.altKey === s.alt &&
            (event.metaKey === s.meta || (s.ctrl && event.metaKey)); // Allow Cmd on Mac
    },

    /**
     * Format date for display
     */
    formatDate(date) {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    /**
     * Simple template rendering
     */
    renderTemplate(template, data) {
        return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
            return data.hasOwnProperty(key) ? Utils.escapeHtml(String(data[key])) : match;
        });
    },

    /**
     * Create element from HTML string
     */
    createElement(html) {
        const template = document.createElement('template');
        template.innerHTML = html.trim();
        return template.content.firstChild;
    },

    /**
     * Show toast notification
     */
    toast(message, type = 'info', duration = 3000) {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Check if we're on macOS
     */
    isMac() {
        return navigator.platform.toLowerCase().includes('mac');
    },

    /**
     * Get modifier key name (Ctrl on Windows/Linux, Cmd on Mac)
     */
    getModKey() {
        return Utils.isMac() ? 'Cmd' : 'Ctrl';
    }
};

window.CouriusUtils = Utils;
