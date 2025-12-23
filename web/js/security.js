/**
 * Courius - Security Module
 * Provides XSS protection, input sanitization, and CSP utilities
 */

const Security = {
    /**
     * Allowed HTML tags for rich text (minimal set)
     */
    ALLOWED_TAGS: ['b', 'i', 'u', 'em', 'strong', 'br', 'p', 'span'],

    /**
     * Allowed attributes for HTML elements
     */
    ALLOWED_ATTRS: ['class', 'id', 'data-line', 'data-type', 'data-page'],

    /**
     * Sanitize HTML string to prevent XSS attacks
     * Uses a whitelist approach - only allows safe tags and attributes
     */
    sanitizeHTML(html) {
        if (!html || typeof html !== 'string') return '';

        // Create a temporary container
        const temp = document.createElement('div');
        temp.innerHTML = html;

        // Recursively sanitize nodes
        this._sanitizeNode(temp);

        return temp.innerHTML;
    },

    /**
     * Recursively sanitize DOM nodes
     */
    _sanitizeNode(node) {
        const childNodes = [...node.childNodes];

        for (const child of childNodes) {
            if (child.nodeType === Node.ELEMENT_NODE) {
                const tagName = child.tagName.toLowerCase();

                // Check if tag is allowed
                if (!this.ALLOWED_TAGS.includes(tagName)) {
                    // Replace with text content or remove
                    if (child.textContent) {
                        const text = document.createTextNode(child.textContent);
                        node.replaceChild(text, child);
                    } else {
                        node.removeChild(child);
                    }
                    continue;
                }

                // Remove disallowed attributes
                const attrs = [...child.attributes];
                for (const attr of attrs) {
                    if (!this.ALLOWED_ATTRS.includes(attr.name)) {
                        child.removeAttribute(attr.name);
                    }

                    // Check for javascript: URLs or event handlers
                    if (attr.value && (
                        attr.value.toLowerCase().includes('javascript:') ||
                        attr.name.startsWith('on')
                    )) {
                        child.removeAttribute(attr.name);
                    }
                }

                // Recursively sanitize children
                this._sanitizeNode(child);
            } else if (child.nodeType === Node.COMMENT_NODE) {
                // Remove comments (can be used for XSS)
                node.removeChild(child);
            }
        }
    },

    /**
     * Escape HTML entities in a string
     */
    escapeHTML(str) {
        if (!str || typeof str !== 'string') return '';

        const escapeMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#x27;',
            '/': '&#x2F;',
            '`': '&#x60;',
            '=': '&#x3D;'
        };

        return str.replace(/[&<>"'`=/]/g, char => escapeMap[char]);
    },

    /**
     * Safely set innerHTML using sanitization
     */
    setInnerHTML(element, html) {
        if (!element) return;
        element.innerHTML = this.sanitizeHTML(html);
    },

    /**
     * Safely set text content (no HTML parsing)
     */
    setTextContent(element, text) {
        if (!element) return;
        element.textContent = text;
    },

    /**
     * Validate and sanitize file content from imports
     */
    sanitizeImportedContent(content, format) {
        if (!content || typeof content !== 'string') return '';

        switch (format) {
            case 'fdx':
                return this._sanitizeFDX(content);
            case 'fountain':
                return this._sanitizeFountain(content);
            case 'trelby':
                return this._sanitizeTrelby(content);
            default:
                return this._sanitizePlainText(content);
        }
    },

    /**
     * Sanitize Final Draft XML content
     */
    _sanitizeFDX(content) {
        try {
            const parser = new DOMParser();
            const doc = parser.parseFromString(content, 'text/xml');

            // Check for parse errors
            const parseError = doc.querySelector('parsererror');
            if (parseError) {
                throw new Error('Invalid XML format');
            }

            // Validate it's a Final Draft document
            const root = doc.documentElement;
            if (root.tagName !== 'FinalDraft') {
                throw new Error('Not a Final Draft document');
            }

            // Remove any script elements or event handlers
            const scripts = doc.querySelectorAll('script, [onclick], [onerror], [onload]');
            scripts.forEach(el => el.remove());

            // Sanitize text content in paragraphs
            const textElements = doc.querySelectorAll('Text');
            textElements.forEach(el => {
                if (el.textContent) {
                    el.textContent = this._sanitizePlainText(el.textContent);
                }
            });

            return new XMLSerializer().serializeToString(doc);
        } catch (e) {
            console.error('FDX sanitization error:', e);
            throw new Error('Invalid or malformed Final Draft file');
        }
    },

    /**
     * Sanitize Fountain content
     */
    _sanitizeFountain(content) {
        // Fountain is plain text - just ensure no control characters
        return this._sanitizePlainText(content);
    },

    /**
     * Sanitize Trelby format content
     */
    _sanitizeTrelby(content) {
        try {
            // Trelby format is a custom text format
            // Validate structure and sanitize content
            const lines = content.split('\n');
            const sanitized = [];

            for (const line of lines) {
                // Remove any potential control characters except newline/tab
                const clean = line.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
                sanitized.push(clean);
            }

            return sanitized.join('\n');
        } catch (e) {
            console.error('Trelby sanitization error:', e);
            throw new Error('Invalid or malformed Trelby file');
        }
    },

    /**
     * Sanitize plain text content
     */
    _sanitizePlainText(content) {
        if (!content || typeof content !== 'string') return '';

        // Remove null bytes and other dangerous control characters
        // Keep newlines, tabs, and normal printable characters
        return content
            .replace(/\x00/g, '') // Remove null bytes
            .replace(/[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '') // Remove control chars except \t \n \r
            .trim();
    },

    /**
     * Validate URL to prevent javascript: and data: URLs
     */
    sanitizeURL(url) {
        if (!url || typeof url !== 'string') return '';

        const trimmed = url.trim().toLowerCase();

        // Block dangerous protocols
        const dangerousProtocols = ['javascript:', 'data:', 'vbscript:', 'file:'];
        for (const protocol of dangerousProtocols) {
            if (trimmed.startsWith(protocol)) {
                return '';
            }
        }

        // Only allow http, https, and relative URLs
        if (trimmed.startsWith('http://') ||
            trimmed.startsWith('https://') ||
            trimmed.startsWith('/') ||
            trimmed.startsWith('./') ||
            trimmed.startsWith('../') ||
            !trimmed.includes(':')) {
            return url;
        }

        return '';
    },

    /**
     * Create a safe DOM element with sanitized content
     */
    createElement(tagName, attributes = {}, textContent = '') {
        const element = document.createElement(tagName);

        // Set safe attributes
        for (const [key, value] of Object.entries(attributes)) {
            if (this.ALLOWED_ATTRS.includes(key) || key.startsWith('data-')) {
                // Ensure no javascript: in attribute values
                if (typeof value === 'string' && !value.toLowerCase().includes('javascript:')) {
                    element.setAttribute(key, value);
                }
            }
        }

        // Set text content (not innerHTML)
        if (textContent) {
            element.textContent = textContent;
        }

        return element;
    },

    /**
     * Sanitize filename for exports
     */
    sanitizeFilename(filename) {
        if (!filename || typeof filename !== 'string') return 'untitled';

        // Remove path traversal attempts and dangerous characters
        return filename
            .replace(/\.\./g, '')
            .replace(/[<>:"/\\|?*\x00-\x1F]/g, '_')
            .replace(/^\.+/, '')
            .trim() || 'untitled';
    },

    /**
     * Validate JSON structure for config/settings
     */
    validateJSON(json, schema) {
        if (typeof json !== 'object' || json === null) {
            return false;
        }

        for (const [key, type] of Object.entries(schema)) {
            if (key in json) {
                const value = json[key];
                if (typeof type === 'string') {
                    if (typeof value !== type) return false;
                } else if (Array.isArray(type)) {
                    if (!type.includes(value)) return false;
                } else if (typeof type === 'object') {
                    if (!this.validateJSON(value, type)) return false;
                }
            }
        }

        return true;
    },

    /**
     * Generate CSP meta tag content
     */
    getCSPContent() {
        return [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: blob:",
            "connect-src 'self' https://api.datamuse.com",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ].join('; ');
    },

    /**
     * Initialize security measures
     */
    init() {
        // Add CSP meta tag if not present
        if (!document.querySelector('meta[http-equiv="Content-Security-Policy"]')) {
            const csp = document.createElement('meta');
            csp.httpEquiv = 'Content-Security-Policy';
            csp.content = this.getCSPContent();
            document.head.appendChild(csp);
        }

        // Add X-Content-Type-Options
        if (!document.querySelector('meta[http-equiv="X-Content-Type-Options"]')) {
            const xcto = document.createElement('meta');
            xcto.httpEquiv = 'X-Content-Type-Options';
            xcto.content = 'nosniff';
            document.head.appendChild(xcto);
        }

        console.log('Security module initialized');
    }
};

window.CouriusSecurity = Security;
