/**
 * Courius - Auto-completion System
 */

class AutoCompletion {
    constructor() {
        this.popup = document.getElementById('autocomplete-popup');
        this.list = document.getElementById('autocomplete-list');
        this.visible = false;
        this.selectedIndex = 0;
        this.suggestions = [];
        this.onSelect = null;
        this.currentPrefix = '';
        this.anchorElement = null;

        this._bindEvents();
    }

    /**
     * Bind keyboard and mouse events
     */
    _bindEvents() {
        document.addEventListener('keydown', (e) => {
            if (!this.visible) return;

            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    this.selectNext();
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.selectPrevious();
                    break;
                case 'Enter':
                case 'Tab':
                    if (this.suggestions.length > 0) {
                        e.preventDefault();
                        this.accept();
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    this.hide();
                    break;
            }
        });

        // Click outside to close
        document.addEventListener('click', (e) => {
            if (this.visible && !this.popup.contains(e.target)) {
                this.hide();
            }
        });

        // List item click
        this.list.addEventListener('click', (e) => {
            const li = e.target.closest('li');
            if (li) {
                const index = Array.from(this.list.children).indexOf(li);
                if (index >= 0) {
                    this.selectedIndex = index;
                    this.accept();
                }
            }
        });
    }

    /**
     * Show auto-completion popup
     */
    show(suggestions, prefix, anchorElement, onSelect) {
        if (suggestions.length === 0) {
            this.hide();
            return;
        }

        this.suggestions = suggestions;
        this.currentPrefix = prefix;
        this.anchorElement = anchorElement;
        this.onSelect = onSelect;
        this.selectedIndex = 0;

        // Render suggestions
        this.list.innerHTML = '';
        for (const suggestion of suggestions) {
            const li = document.createElement('li');
            li.textContent = suggestion;
            this.list.appendChild(li);
        }

        // Update selection
        this._updateSelection();

        // Position popup
        this._positionPopup();

        this.popup.classList.remove('hidden');
        this.visible = true;
    }

    /**
     * Hide auto-completion popup
     */
    hide() {
        this.popup.classList.add('hidden');
        this.visible = false;
        this.suggestions = [];
        this.onSelect = null;
    }

    /**
     * Select next suggestion
     */
    selectNext() {
        if (this.suggestions.length === 0) return;
        this.selectedIndex = (this.selectedIndex + 1) % this.suggestions.length;
        this._updateSelection();
    }

    /**
     * Select previous suggestion
     */
    selectPrevious() {
        if (this.suggestions.length === 0) return;
        this.selectedIndex = (this.selectedIndex - 1 + this.suggestions.length) % this.suggestions.length;
        this._updateSelection();
    }

    /**
     * Accept current selection
     */
    accept() {
        if (this.selectedIndex >= 0 && this.selectedIndex < this.suggestions.length) {
            const selected = this.suggestions[this.selectedIndex];
            if (this.onSelect) {
                this.onSelect(selected, this.currentPrefix);
            }
        }
        this.hide();
    }

    /**
     * Update visual selection
     */
    _updateSelection() {
        const items = this.list.querySelectorAll('li');
        items.forEach((item, index) => {
            item.classList.toggle('selected', index === this.selectedIndex);
        });

        // Scroll into view
        const selectedItem = items[this.selectedIndex];
        if (selectedItem) {
            selectedItem.scrollIntoView({ block: 'nearest' });
        }
    }

    /**
     * Position popup near anchor element
     */
    _positionPopup() {
        if (!this.anchorElement) return;

        const rect = this.anchorElement.getBoundingClientRect();
        const popupRect = this.popup.getBoundingClientRect();

        // Position below the anchor
        let top = rect.bottom + 2;
        let left = rect.left;

        // Adjust if would go off screen
        if (top + popupRect.height > window.innerHeight) {
            top = rect.top - popupRect.height - 2;
        }

        if (left + popupRect.width > window.innerWidth) {
            left = window.innerWidth - popupRect.width - 10;
        }

        this.popup.style.top = `${top}px`;
        this.popup.style.left = `${left}px`;
    }

    /**
     * Check if auto-completion should trigger
     */
    shouldTrigger(lineType, text, cursorPos) {
        const { LINE_TYPE } = window.CouriusConstants;

        // Only trigger for certain element types
        const triggerTypes = [
            LINE_TYPE.SCENE,
            LINE_TYPE.CHARACTER,
            LINE_TYPE.TRANSITION,
            LINE_TYPE.SHOT
        ];

        if (!triggerTypes.includes(lineType)) {
            return false;
        }

        // Need at least 1 character
        const prefix = text.substring(0, cursorPos);
        return prefix.length >= 1;
    }

    /**
     * Get prefix for auto-completion
     */
    getPrefix(text, cursorPos) {
        return text.substring(0, cursorPos).toUpperCase();
    }
}

/**
 * Character name database for suggestions
 */
class NameDatabase {
    constructor() {
        this.names = [];
        this.origins = new Set();
        this.loaded = false;
    }

    /**
     * Load names from embedded data
     */
    async load() {
        // Common names organized by origin
        const defaultNames = {
            'English': [
                'James', 'John', 'Robert', 'Michael', 'William', 'David', 'Richard', 'Joseph', 'Thomas', 'Charles',
                'Mary', 'Patricia', 'Jennifer', 'Linda', 'Elizabeth', 'Barbara', 'Susan', 'Jessica', 'Sarah', 'Karen',
                'Christopher', 'Daniel', 'Matthew', 'Anthony', 'Mark', 'Donald', 'Steven', 'Paul', 'Andrew', 'Joshua',
                'Nancy', 'Betty', 'Margaret', 'Sandra', 'Ashley', 'Kimberly', 'Emily', 'Donna', 'Michelle', 'Dorothy'
            ],
            'Spanish': [
                'Jose', 'Juan', 'Carlos', 'Luis', 'Miguel', 'Antonio', 'Francisco', 'Pedro', 'Manuel', 'Diego',
                'Maria', 'Carmen', 'Ana', 'Rosa', 'Isabel', 'Elena', 'Sofia', 'Lucia', 'Laura', 'Paula'
            ],
            'French': [
                'Jean', 'Pierre', 'Michel', 'Jacques', 'Philippe', 'Alain', 'Bernard', 'Claude', 'François', 'Louis',
                'Marie', 'Jeanne', 'Marguerite', 'Claire', 'Isabelle', 'Sophie', 'Monique', 'Nicole', 'Anne', 'Catherine'
            ],
            'German': [
                'Hans', 'Peter', 'Michael', 'Thomas', 'Andreas', 'Stefan', 'Klaus', 'Wolfgang', 'Frank', 'Jürgen',
                'Anna', 'Maria', 'Emma', 'Hannah', 'Sophie', 'Lena', 'Leonie', 'Mia', 'Laura', 'Lisa'
            ],
            'Italian': [
                'Giuseppe', 'Giovanni', 'Antonio', 'Mario', 'Luigi', 'Francesco', 'Angelo', 'Vincenzo', 'Pietro', 'Salvatore',
                'Maria', 'Anna', 'Giuseppina', 'Rosa', 'Angela', 'Giovanna', 'Teresa', 'Lucia', 'Francesca', 'Carla'
            ],
            'Japanese': [
                'Takeshi', 'Hiroshi', 'Kenji', 'Yuki', 'Satoshi', 'Kazuki', 'Ryu', 'Akira', 'Haruki', 'Ken',
                'Yuki', 'Sakura', 'Hana', 'Aiko', 'Keiko', 'Yumi', 'Naomi', 'Mei', 'Rin', 'Saki'
            ],
            'Chinese': [
                'Wei', 'Ming', 'Jun', 'Feng', 'Lei', 'Yang', 'Chen', 'Lin', 'Zhang', 'Wang',
                'Mei', 'Li', 'Xiao', 'Ying', 'Hui', 'Juan', 'Fang', 'Yan', 'Jing', 'Qing'
            ],
            'Russian': [
                'Ivan', 'Alexei', 'Dmitri', 'Nikolai', 'Sergei', 'Vladimir', 'Mikhail', 'Andrei', 'Boris', 'Viktor',
                'Anna', 'Maria', 'Elena', 'Olga', 'Natalia', 'Tatiana', 'Irina', 'Svetlana', 'Marina', 'Ekaterina'
            ],
            'Arabic': [
                'Mohammed', 'Ahmed', 'Ali', 'Omar', 'Hassan', 'Hussein', 'Ibrahim', 'Youssef', 'Khalid', 'Tariq',
                'Fatima', 'Aisha', 'Maryam', 'Layla', 'Zahra', 'Sara', 'Noor', 'Amira', 'Hana', 'Yasmin'
            ],
            'Indian': [
                'Raj', 'Arjun', 'Vikram', 'Sanjay', 'Amit', 'Ravi', 'Deepak', 'Anil', 'Suresh', 'Rahul',
                'Priya', 'Anita', 'Sunita', 'Rekha', 'Neha', 'Pooja', 'Kavita', 'Anjali', 'Divya', 'Meera'
            ]
        };

        this.names = [];
        for (const [origin, names] of Object.entries(defaultNames)) {
            this.origins.add(origin);
            for (const name of names) {
                this.names.push({
                    name,
                    origin,
                    gender: this._guessGender(name, origin)
                });
            }
        }

        this.loaded = true;
    }

    /**
     * Guess gender based on common patterns
     */
    _guessGender(name, origin) {
        // Very basic heuristic - would need a proper database
        const femaleEndings = ['a', 'e', 'i', 'ie', 'y', 'ine', 'elle', 'ette'];
        const lowerName = name.toLowerCase();

        for (const ending of femaleEndings) {
            if (lowerName.endsWith(ending)) {
                return 'female';
            }
        }

        return 'male';
    }

    /**
     * Search names with filters
     */
    search(query = '', gender = 'any', origin = 'any') {
        let results = this.names;

        if (query) {
            const lowerQuery = query.toLowerCase();
            results = results.filter(n => n.name.toLowerCase().includes(lowerQuery));
        }

        if (gender !== 'any') {
            results = results.filter(n => n.gender === gender);
        }

        if (origin !== 'any') {
            results = results.filter(n => n.origin === origin);
        }

        return results.sort((a, b) => a.name.localeCompare(b.name));
    }

    /**
     * Get all origins
     */
    getOrigins() {
        return Array.from(this.origins).sort();
    }

    /**
     * Get a random name
     */
    getRandom(gender = 'any', origin = 'any') {
        const results = this.search('', gender, origin);
        if (results.length === 0) return null;
        return results[Math.floor(Math.random() * results.length)];
    }
}

window.CouriusAutoCompletion = AutoCompletion;
window.CouriusNameDatabase = NameDatabase;
