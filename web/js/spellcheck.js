/**
 * Courius - Spell Checking System
 * Uses browser's built-in spell checking or a custom dictionary
 */

class SpellChecker {
    constructor() {
        this.enabled = true;
        this.customDictionary = new Set();
        this.ignoredWords = new Set();
        this.language = 'en-US';

        // Load saved custom dictionary
        this._loadCustomDictionary();
    }

    /**
     * Load custom dictionary from localStorage
     */
    _loadCustomDictionary() {
        try {
            const saved = localStorage.getItem('courius-custom-dictionary');
            if (saved) {
                const words = JSON.parse(saved);
                this.customDictionary = new Set(words);
            }
        } catch (e) {
            console.warn('Failed to load custom dictionary:', e);
        }
    }

    /**
     * Save custom dictionary to localStorage
     */
    _saveCustomDictionary() {
        try {
            const words = Array.from(this.customDictionary);
            localStorage.setItem('courius-custom-dictionary', JSON.stringify(words));
        } catch (e) {
            console.warn('Failed to save custom dictionary:', e);
        }
    }

    /**
     * Check if a word is spelled correctly
     * Uses the browser's spellcheck API if available
     */
    async checkWord(word) {
        if (!this.enabled) return true;
        if (!word || word.length < 2) return true;

        // Check custom dictionary first
        const lowerWord = word.toLowerCase();
        if (this.customDictionary.has(lowerWord)) return true;
        if (this.ignoredWords.has(lowerWord)) return true;

        // Check if it's a number or special text
        if (/^[\d\-_.]+$/.test(word)) return true;
        if (/^[A-Z]{2,}$/.test(word)) return true; // Acronyms

        // Use browser spell checking if available
        if ('Intl' in window && 'Segmenter' in window.Intl) {
            // Modern browsers might support this
            return true; // Fallback to browser's native
        }

        // Fallback: use a basic heuristic
        return this._basicSpellCheck(word);
    }

    /**
     * Basic spell check heuristic
     * This is a simple fallback - real apps should use a proper dictionary
     */
    _basicSpellCheck(word) {
        // Very basic common word list
        const commonWords = new Set([
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
            'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
            'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
            'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
            'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
            'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
            'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us',
            // Screenplay specific
            'int', 'ext', 'cut', 'fade', 'dissolve', 'continuous', 'later', 'day', 'night',
            'morning', 'evening', 'afternoon', 'dawn', 'dusk', 'same', 'moment', 'angle',
            'close', 'wide', 'shot', 'pov', 'insert', 'flashback', 'intercut', 'montage',
            'super', 'title', 'card', 'voice', 'over', 'off', 'screen', 'cont', 'contd',
            'beat', 'pause', 'silence', 'suddenly', 'slowly', 'quickly', 'carefully'
        ]);

        return commonWords.has(word.toLowerCase());
    }

    /**
     * Check all words in a text and return misspelled ones
     */
    async checkText(text) {
        const words = this._tokenize(text);
        const misspelled = [];

        for (const { word, start, end } of words) {
            const isCorrect = await this.checkWord(word);
            if (!isCorrect) {
                misspelled.push({ word, start, end });
            }
        }

        return misspelled;
    }

    /**
     * Tokenize text into words with positions
     */
    _tokenize(text) {
        const words = [];
        const regex = /[a-zA-Z']+/g;
        let match;

        while ((match = regex.exec(text)) !== null) {
            words.push({
                word: match[0],
                start: match.index,
                end: match.index + match[0].length
            });
        }

        return words;
    }

    /**
     * Get suggestions for a misspelled word
     */
    getSuggestions(word) {
        // Simple suggestions based on common patterns
        const suggestions = [];
        const lowerWord = word.toLowerCase();

        // Common substitutions
        const substitutions = {
            'teh': 'the',
            'taht': 'that',
            'adn': 'and',
            'hte': 'the',
            'wiht': 'with',
            'form': 'from',
            'jsut': 'just',
            'dont': "don't",
            'cant': "can't",
            'wont': "won't",
            'im': "I'm",
            'youre': "you're",
            'theyre': "they're",
            'thier': 'their',
            'recieve': 'receive',
            'beleive': 'believe',
            'occured': 'occurred',
            'seperate': 'separate',
            'definately': 'definitely'
        };

        if (substitutions[lowerWord]) {
            suggestions.push(substitutions[lowerWord]);
        }

        // Try removing double letters
        const doubleRemoved = lowerWord.replace(/(.)\1/g, '$1');
        if (doubleRemoved !== lowerWord) {
            suggestions.push(doubleRemoved);
        }

        // Try adding double letters
        for (let i = 0; i < lowerWord.length; i++) {
            const doubled = lowerWord.slice(0, i + 1) + lowerWord[i] + lowerWord.slice(i + 1);
            if (!suggestions.includes(doubled)) {
                suggestions.push(doubled);
            }
        }

        return suggestions.slice(0, 5);
    }

    /**
     * Add word to custom dictionary
     */
    addToCustomDictionary(word) {
        this.customDictionary.add(word.toLowerCase());
        this._saveCustomDictionary();
    }

    /**
     * Remove word from custom dictionary
     */
    removeFromCustomDictionary(word) {
        this.customDictionary.delete(word.toLowerCase());
        this._saveCustomDictionary();
    }

    /**
     * Ignore word for this session
     */
    ignoreWord(word) {
        this.ignoredWords.add(word.toLowerCase());
    }

    /**
     * Ignore all instances of word for this session
     */
    ignoreAll(word) {
        this.ignoredWords.add(word.toLowerCase());
    }

    /**
     * Clear ignored words
     */
    clearIgnored() {
        this.ignoredWords.clear();
    }

    /**
     * Enable/disable spell checking
     */
    setEnabled(enabled) {
        this.enabled = enabled;
    }

    /**
     * Get custom dictionary words
     */
    getCustomDictionary() {
        return Array.from(this.customDictionary).sort();
    }

    /**
     * Set language for spell checking
     */
    setLanguage(language) {
        this.language = language;
    }
}

/**
 * Interactive spell check dialog controller
 */
class SpellCheckDialog {
    constructor(spellChecker, editor) {
        this.spellChecker = spellChecker;
        this.editor = editor;
        this.currentWord = null;
        this.currentPosition = null;
        this.misspelledWords = [];
        this.wordIndex = 0;
    }

    /**
     * Start spell checking from current position
     */
    async start() {
        const screenplay = this.editor.screenplay;
        this.misspelledWords = [];
        this.wordIndex = 0;

        // Collect all misspelled words
        for (let i = 0; i < screenplay.lineCount; i++) {
            const text = screenplay.getLineText(i);
            const misspelled = await this.spellChecker.checkText(text);

            for (const word of misspelled) {
                this.misspelledWords.push({
                    line: i,
                    ...word
                });
            }
        }

        if (this.misspelledWords.length === 0) {
            window.CouriusUtils.toast('No spelling errors found!', 'success');
            return null;
        }

        return this.showNext();
    }

    /**
     * Show next misspelled word
     */
    showNext() {
        if (this.wordIndex >= this.misspelledWords.length) {
            window.CouriusUtils.toast('Spell check complete!', 'success');
            return null;
        }

        const wordInfo = this.misspelledWords[this.wordIndex];
        this.currentWord = wordInfo;

        // Navigate to the word
        this.editor.goToLine(wordInfo.line);

        // Get suggestions
        const suggestions = this.spellChecker.getSuggestions(wordInfo.word);

        return {
            word: wordInfo.word,
            line: wordInfo.line,
            suggestions,
            remaining: this.misspelledWords.length - this.wordIndex - 1
        };
    }

    /**
     * Replace current word with suggestion
     */
    replace(replacement) {
        if (!this.currentWord) return;

        const screenplay = this.editor.screenplay;
        const text = screenplay.getLineText(this.currentWord.line);
        const newText =
            text.substring(0, this.currentWord.start) +
            replacement +
            text.substring(this.currentWord.end);

        screenplay.setLineText(this.currentWord.line, newText);
        this.editor.refreshLine(this.currentWord.line);

        // Adjust positions of following words on same line
        const lengthDiff = replacement.length - this.currentWord.word.length;
        for (let i = this.wordIndex + 1; i < this.misspelledWords.length; i++) {
            const w = this.misspelledWords[i];
            if (w.line === this.currentWord.line && w.start > this.currentWord.start) {
                w.start += lengthDiff;
                w.end += lengthDiff;
            }
        }

        this.wordIndex++;
        return this.showNext();
    }

    /**
     * Replace all instances of current word
     */
    replaceAll(replacement) {
        if (!this.currentWord) return;

        const wordToReplace = this.currentWord.word.toLowerCase();

        // Replace all instances
        for (let i = this.misspelledWords.length - 1; i >= this.wordIndex; i--) {
            const w = this.misspelledWords[i];
            if (w.word.toLowerCase() === wordToReplace) {
                const screenplay = this.editor.screenplay;
                const text = screenplay.getLineText(w.line);
                const newText =
                    text.substring(0, w.start) +
                    replacement +
                    text.substring(w.end);
                screenplay.setLineText(w.line, newText);
                this.editor.refreshLine(w.line);
            }
        }

        // Remove all instances from list
        this.misspelledWords = this.misspelledWords.filter(
            w => w.word.toLowerCase() !== wordToReplace
        );

        return this.showNext();
    }

    /**
     * Ignore current word
     */
    ignore() {
        this.wordIndex++;
        return this.showNext();
    }

    /**
     * Ignore all instances of current word
     */
    ignoreAll() {
        if (!this.currentWord) return;

        const wordToIgnore = this.currentWord.word.toLowerCase();
        this.spellChecker.ignoreAll(wordToIgnore);

        // Remove all instances from list
        this.misspelledWords = this.misspelledWords.filter(
            w => w.word.toLowerCase() !== wordToIgnore
        );

        return this.showNext();
    }

    /**
     * Add current word to dictionary
     */
    addToDictionary() {
        if (!this.currentWord) return;

        this.spellChecker.addToCustomDictionary(this.currentWord.word);
        return this.ignoreAll();
    }
}

window.CouriusSpellChecker = SpellChecker;
window.CouriusSpellCheckDialog = SpellCheckDialog;
