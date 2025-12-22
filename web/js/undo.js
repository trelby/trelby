/**
 * Trelby Web - Undo/Redo System
 * Implements undo/redo with state snapshots
 */

class UndoManager {
    constructor(maxStates = 100) {
        this.maxStates = maxStates;
        this.states = [];
        this.currentIndex = -1;
        this.grouping = false;
        this.groupedActions = [];
        this.lastSaveIndex = -1;
    }

    /**
     * Add a new state
     */
    push(state, description = '') {
        // If we're in the middle of the history, remove future states
        if (this.currentIndex < this.states.length - 1) {
            this.states = this.states.slice(0, this.currentIndex + 1);
        }

        // If grouping, add to group instead
        if (this.grouping) {
            this.groupedActions.push({ state, description });
            return;
        }

        // Add new state
        this.states.push({
            state: window.TrelbyUtils.deepClone(state),
            description,
            timestamp: Date.now()
        });
        this.currentIndex = this.states.length - 1;

        // Limit history size
        if (this.states.length > this.maxStates) {
            const removeCount = this.states.length - this.maxStates;
            this.states = this.states.slice(removeCount);
            this.currentIndex -= removeCount;
            this.lastSaveIndex -= removeCount;

            if (this.lastSaveIndex < 0) {
                this.lastSaveIndex = -1;
            }
        }
    }

    /**
     * Undo to previous state
     */
    undo() {
        if (!this.canUndo()) return null;
        this.currentIndex--;
        return window.TrelbyUtils.deepClone(this.states[this.currentIndex].state);
    }

    /**
     * Redo to next state
     */
    redo() {
        if (!this.canRedo()) return null;
        this.currentIndex++;
        return window.TrelbyUtils.deepClone(this.states[this.currentIndex].state);
    }

    /**
     * Check if undo is available
     */
    canUndo() {
        return this.currentIndex > 0;
    }

    /**
     * Check if redo is available
     */
    canRedo() {
        return this.currentIndex < this.states.length - 1;
    }

    /**
     * Get current state
     */
    getCurrentState() {
        if (this.currentIndex < 0 || this.currentIndex >= this.states.length) {
            return null;
        }
        return window.TrelbyUtils.deepClone(this.states[this.currentIndex].state);
    }

    /**
     * Get description of next undo action
     */
    getUndoDescription() {
        if (!this.canUndo()) return '';
        return this.states[this.currentIndex].description;
    }

    /**
     * Get description of next redo action
     */
    getRedoDescription() {
        if (!this.canRedo()) return '';
        return this.states[this.currentIndex + 1].description;
    }

    /**
     * Start grouping actions (for compound operations)
     */
    beginGroup() {
        this.grouping = true;
        this.groupedActions = [];
    }

    /**
     * End grouping and save as single action
     */
    endGroup(description = 'Multiple changes') {
        this.grouping = false;
        if (this.groupedActions.length > 0) {
            // Save only the final state
            const lastAction = this.groupedActions[this.groupedActions.length - 1];
            this.push(lastAction.state, description);
        }
        this.groupedActions = [];
    }

    /**
     * Cancel grouping without saving
     */
    cancelGroup() {
        this.grouping = false;
        this.groupedActions = [];
    }

    /**
     * Mark current position as saved
     */
    markSaved() {
        this.lastSaveIndex = this.currentIndex;
    }

    /**
     * Check if current state is different from last save
     */
    isModified() {
        return this.currentIndex !== this.lastSaveIndex;
    }

    /**
     * Clear all history
     */
    clear() {
        this.states = [];
        this.currentIndex = -1;
        this.lastSaveIndex = -1;
        this.grouping = false;
        this.groupedActions = [];
    }

    /**
     * Get history length
     */
    get length() {
        return this.states.length;
    }
}

/**
 * Specific undo state for screenplay operations
 */
class ScreenplayUndoState {
    constructor(screenplay, cursorLine, cursorColumn, description = '') {
        this.lines = screenplay.lines.map(line => line.toJSON());
        this.cursorLine = cursorLine;
        this.cursorColumn = cursorColumn;
        this.description = description;
    }

    /**
     * Apply this state to a screenplay
     */
    apply(screenplay) {
        const Line = window.TrelbyLine;
        screenplay.lines = this.lines.map(l => Line.fromJSON(l));
        screenplay.cursorLine = this.cursorLine;
        screenplay.cursorColumn = this.cursorColumn;
    }

    /**
     * Convert to plain object
     */
    toJSON() {
        return {
            lines: this.lines,
            cursorLine: this.cursorLine,
            cursorColumn: this.cursorColumn,
            description: this.description
        };
    }

    /**
     * Create from plain object
     */
    static fromJSON(json) {
        const state = new ScreenplayUndoState({ lines: [] }, 0, 0, '');
        state.lines = json.lines;
        state.cursorLine = json.cursorLine;
        state.cursorColumn = json.cursorColumn;
        state.description = json.description;
        return state;
    }
}

window.TrelbyUndoManager = UndoManager;
window.TrelbyScreenplayUndoState = ScreenplayUndoState;
