/**
 * Courius - Enhanced Spell Checker V2
 * Uses Datamuse API for real spell checking with offline dictionary caching
 */

class SpellCheckerV2 {
    constructor() {
        this.enabled = true;
        this.customDictionary = new Set();
        this.cache = new Map();
        this.pendingChecks = new Map();
        this.dbName = 'courius-spellcheck';
        this.dbVersion = 1;
        this.db = null;

        // Common words that don't need checking
        this.commonWords = new Set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'he', 'she', 'it', 'they', 'we', 'you', 'i', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
            'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only',
            'same', 'so', 'than', 'too', 'very', 'just', 'as', 'if', 'then',
            // Screenplay-specific terms
            'int', 'ext', 'day', 'night', 'morning', 'evening', 'continuous',
            'fade', 'cut', 'dissolve', 'smash', 'match', 'angle', 'close',
            'wide', 'pov', 'os', 'vo', 'cont', 'contd', 'beat', 'pause',
            'later', 'flashback', 'intercut', 'montage', 'series', 'shots'
        ]);

        this._init();
    }

    /**
     * Initialize the spell checker
     */
    async _init() {
        await this._openDatabase();
        await this._loadCustomDictionary();
        await this._loadCache();
    }

    /**
     * Open IndexedDB for caching
     */
    async _openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Store for dictionary cache
                if (!db.objectStoreNames.contains('dictionary')) {
                    db.createObjectStore('dictionary', { keyPath: 'word' });
                }

                // Store for custom words
                if (!db.objectStoreNames.contains('custom')) {
                    db.createObjectStore('custom', { keyPath: 'word' });
                }

                // Store for suggestions cache
                if (!db.objectStoreNames.contains('suggestions')) {
                    const store = db.createObjectStore('suggestions', { keyPath: 'word' });
                    store.createIndex('timestamp', 'timestamp');
                }
            };
        });
    }

    /**
     * Load custom dictionary from IndexedDB
     */
    async _loadCustomDictionary() {
        if (!this.db) return;

        return new Promise((resolve) => {
            const transaction = this.db.transaction(['custom'], 'readonly');
            const store = transaction.objectStore('custom');
            const request = store.getAll();

            request.onsuccess = () => {
                const words = request.result || [];
                words.forEach(item => this.customDictionary.add(item.word.toLowerCase()));
                resolve();
            };

            request.onerror = () => resolve();
        });
    }

    /**
     * Load suggestion cache from IndexedDB
     */
    async _loadCache() {
        if (!this.db) return;

        return new Promise((resolve) => {
            const transaction = this.db.transaction(['suggestions'], 'readonly');
            const store = transaction.objectStore('suggestions');
            const request = store.getAll();

            request.onsuccess = () => {
                const items = request.result || [];
                const now = Date.now();
                const maxAge = 7 * 24 * 60 * 60 * 1000; // 7 days

                items.forEach(item => {
                    if (now - item.timestamp < maxAge) {
                        this.cache.set(item.word, item.data);
                    }
                });

                resolve();
            };

            request.onerror = () => resolve();
        });
    }

    /**
     * Save suggestion to cache
     */
    async _saveToCache(word, data) {
        if (!this.db) return;

        return new Promise((resolve) => {
            const transaction = this.db.transaction(['suggestions'], 'readwrite');
            const store = transaction.objectStore('suggestions');
            store.put({ word, data, timestamp: Date.now() });
            transaction.oncomplete = resolve;
            transaction.onerror = () => resolve();
        });
    }

    /**
     * Check if a word is spelled correctly
     */
    async checkWord(word) {
        if (!this.enabled) return { correct: true };

        const normalized = word.toLowerCase().trim();

        // Skip empty or very short words
        if (normalized.length < 2) return { correct: true };

        // Skip numbers
        if (/^\d+$/.test(normalized)) return { correct: true };

        // Skip common words
        if (this.commonWords.has(normalized)) return { correct: true };

        // Check custom dictionary
        if (this.customDictionary.has(normalized)) return { correct: true };

        // Check cache
        if (this.cache.has(normalized)) {
            const cached = this.cache.get(normalized);
            return { correct: cached.correct, suggestions: cached.suggestions };
        }

        // Check pending
        if (this.pendingChecks.has(normalized)) {
            return this.pendingChecks.get(normalized);
        }

        // Query API
        const promise = this._queryAPI(normalized);
        this.pendingChecks.set(normalized, promise);

        try {
            const result = await promise;
            this.cache.set(normalized, result);
            this._saveToCache(normalized, result);
            return result;
        } finally {
            this.pendingChecks.delete(normalized);
        }
    }

    /**
     * Query the Datamuse API for spelling suggestions
     */
    async _queryAPI(word) {
        try {
            // First, check if word is in dictionary using soundlike search
            const response = await fetch(
                `https://api.datamuse.com/words?sp=${encodeURIComponent(word)}&max=10`
            );

            if (!response.ok) {
                throw new Error('API request failed');
            }

            const results = await response.json();

            // Check if word is correct (exact match in results)
            const exactMatch = results.some(r =>
                r.word.toLowerCase() === word.toLowerCase()
            );

            if (exactMatch) {
                return { correct: true, suggestions: [] };
            }

            // Word might be misspelled - get suggestions
            const suggestResponse = await fetch(
                `https://api.datamuse.com/words?sp=${encodeURIComponent(word)}*&max=5`
            );

            const suggestions = await suggestResponse.json();

            // Also try soundlike suggestions
            const soundResponse = await fetch(
                `https://api.datamuse.com/words?sl=${encodeURIComponent(word)}&max=5`
            );

            const soundSuggestions = await soundResponse.json();

            // Combine and deduplicate suggestions
            const allSuggestions = new Set([
                ...suggestions.map(s => s.word),
                ...soundSuggestions.map(s => s.word)
            ]);

            // If we get results but no exact match, it might still be correct
            // Use a heuristic: if top result is very similar, word is likely correct
            if (results.length > 0) {
                const topResult = results[0].word.toLowerCase();
                if (this._similarity(word, topResult) > 0.9) {
                    return { correct: true, suggestions: [] };
                }
            }

            return {
                correct: false,
                suggestions: [...allSuggestions].slice(0, 5)
            };
        } catch (error) {
            console.warn('Spell check API error:', error);
            // On error, assume word is correct to avoid false positives
            return { correct: true, suggestions: [] };
        }
    }

    /**
     * Calculate string similarity (Levenshtein-based)
     */
    _similarity(a, b) {
        const longer = a.length > b.length ? a : b;
        const shorter = a.length > b.length ? b : a;

        if (longer.length === 0) return 1.0;

        const editDistance = this._levenshtein(longer, shorter);
        return (longer.length - editDistance) / longer.length;
    }

    /**
     * Calculate Levenshtein distance
     */
    _levenshtein(a, b) {
        const matrix = [];

        for (let i = 0; i <= b.length; i++) {
            matrix[i] = [i];
        }

        for (let j = 0; j <= a.length; j++) {
            matrix[0][j] = j;
        }

        for (let i = 1; i <= b.length; i++) {
            for (let j = 1; j <= a.length; j++) {
                if (b.charAt(i - 1) === a.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }

        return matrix[b.length][a.length];
    }

    /**
     * Check all words in a text
     */
    async checkText(text) {
        if (!this.enabled || !text) return [];

        const words = text.match(/\b[a-zA-Z']+\b/g) || [];
        const errors = [];

        for (const word of words) {
            const result = await this.checkWord(word);
            if (!result.correct) {
                // Find position in text
                const regex = new RegExp(`\\b${this._escapeRegex(word)}\\b`, 'gi');
                let match;
                while ((match = regex.exec(text)) !== null) {
                    errors.push({
                        word,
                        start: match.index,
                        end: match.index + word.length,
                        suggestions: result.suggestions
                    });
                }
            }
        }

        return errors;
    }

    /**
     * Escape regex special characters
     */
    _escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    /**
     * Add word to custom dictionary
     */
    async addToCustomDictionary(word) {
        const normalized = word.toLowerCase().trim();
        this.customDictionary.add(normalized);

        // Update cache to mark as correct
        this.cache.set(normalized, { correct: true, suggestions: [] });

        // Save to IndexedDB
        if (this.db) {
            const transaction = this.db.transaction(['custom'], 'readwrite');
            const store = transaction.objectStore('custom');
            store.put({ word: normalized });
        }
    }

    /**
     * Remove word from custom dictionary
     */
    async removeFromCustomDictionary(word) {
        const normalized = word.toLowerCase().trim();
        this.customDictionary.delete(normalized);
        this.cache.delete(normalized);

        if (this.db) {
            const transaction = this.db.transaction(['custom'], 'readwrite');
            const store = transaction.objectStore('custom');
            store.delete(normalized);
        }
    }

    /**
     * Get custom dictionary words
     */
    getCustomDictionary() {
        return [...this.customDictionary].sort();
    }

    /**
     * Enable/disable spell checking
     */
    setEnabled(enabled) {
        this.enabled = enabled;
        localStorage.setItem('courius-spellcheck-enabled', String(enabled));
    }

    /**
     * Check if spell checking is enabled
     */
    isEnabled() {
        return this.enabled;
    }

    /**
     * Clear the suggestions cache
     */
    async clearCache() {
        this.cache.clear();

        if (this.db) {
            const transaction = this.db.transaction(['suggestions'], 'readwrite');
            const store = transaction.objectStore('suggestions');
            store.clear();
        }
    }

    /**
     * Get suggestions for a misspelled word
     */
    async getSuggestions(word) {
        const result = await this.checkWord(word);
        return result.suggestions || [];
    }

    /**
     * Highlight misspelled words in an element
     */
    async highlightErrors(element) {
        if (!this.enabled || !element) return;

        const text = element.textContent;
        const errors = await this.checkText(text);

        if (errors.length === 0) {
            // Remove any existing error highlights
            element.querySelectorAll('.spelling-error').forEach(el => {
                el.replaceWith(el.textContent);
            });
            return;
        }

        // Build new HTML with error highlights
        let html = '';
        let lastIndex = 0;

        // Sort errors by position
        errors.sort((a, b) => a.start - b.start);

        // Remove overlapping errors
        const uniqueErrors = [];
        for (const error of errors) {
            const overlaps = uniqueErrors.some(e =>
                (error.start >= e.start && error.start < e.end) ||
                (error.end > e.start && error.end <= e.end)
            );
            if (!overlaps) {
                uniqueErrors.push(error);
            }
        }

        for (const error of uniqueErrors) {
            // Add text before error
            html += this._escapeHTML(text.substring(lastIndex, error.start));

            // Add error with highlight
            html += `<span class="spelling-error" data-word="${this._escapeHTML(error.word)}" data-suggestions="${this._escapeHTML(error.suggestions.join(','))}">${this._escapeHTML(error.word)}</span>`;

            lastIndex = error.end;
        }

        // Add remaining text
        html += this._escapeHTML(text.substring(lastIndex));

        element.innerHTML = html;
    }

    /**
     * Escape HTML entities
     */
    _escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

window.CouriusSpellCheckerV2 = SpellCheckerV2;
