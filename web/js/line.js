/**
 * Trelby Web - Line Model
 * Represents a single line in the screenplay
 */

class Line {
    constructor(lb = null, type = null, text = '') {
        const { LB, LINE_TYPE } = window.TrelbyConstants;

        this.lb = lb ?? LB.LAST;
        this.type = type ?? LINE_TYPE.ACTION;
        this.text = text;
    }

    /**
     * Clone this line
     */
    clone() {
        return new Line(this.lb, this.type, this.text);
    }

    /**
     * Check if this line is empty
     */
    isEmpty() {
        return this.text.length === 0;
    }

    /**
     * Check if this is the last line of a paragraph
     */
    isLastInParagraph() {
        const { LB } = window.TrelbyConstants;
        return this.lb === LB.LAST || this.lb === LB.FORCED;
    }

    /**
     * Convert to plain object for serialization
     */
    toJSON() {
        return {
            lb: this.lb,
            type: this.type,
            text: this.text
        };
    }

    /**
     * Create from plain object
     */
    static fromJSON(json) {
        return new Line(json.lb, json.type, json.text);
    }

    /**
     * Convert to Trelby file format line
     */
    toTrelbyFormat() {
        const { LB_TO_CHAR, LT_TO_CHAR } = window.TrelbyConstants;
        const lbChar = LB_TO_CHAR[this.lb] || '.';
        const ltChar = LT_TO_CHAR[this.type] || '.';
        return lbChar + ltChar + this.text;
    }

    /**
     * Parse from Trelby file format line
     */
    static fromTrelbyFormat(line) {
        const { LB_CHARS, LT_CHARS, LB, LINE_TYPE } = window.TrelbyConstants;

        if (line.length < 2) {
            return new Line(LB.LAST, LINE_TYPE.ACTION, line);
        }

        const lbChar = line[0];
        const ltChar = line[1];
        const text = line.substring(2);

        const lb = LB_CHARS[lbChar] ?? LB.LAST;
        const type = LT_CHARS[ltChar] ?? LINE_TYPE.ACTION;

        return new Line(lb, type, text);
    }

    /**
     * Get display text (with formatting applied)
     */
    getDisplayText(config) {
        const { ELEMENT_FORMAT } = window.TrelbyConstants;
        const format = config?.elementFormat?.[this.type] || ELEMENT_FORMAT[this.type];

        let text = this.text;
        if (format?.caps) {
            text = text.toUpperCase();
        }
        return text;
    }

    /**
     * Check if this is a scene heading
     */
    isSceneHeading() {
        const { LINE_TYPE } = window.TrelbyConstants;
        return this.type === LINE_TYPE.SCENE;
    }

    /**
     * Check if this is dialogue
     */
    isDialogue() {
        const { LINE_TYPE } = window.TrelbyConstants;
        return this.type === LINE_TYPE.DIALOGUE;
    }

    /**
     * Check if this is a character name
     */
    isCharacter() {
        const { LINE_TYPE } = window.TrelbyConstants;
        return this.type === LINE_TYPE.CHARACTER;
    }

    /**
     * Get character name (strips parentheticals like (V.O.))
     */
    getCharacterName() {
        if (!this.isCharacter()) return null;
        return this.text.replace(/\s*\([^)]*\)\s*$/, '').trim().toUpperCase();
    }

    /**
     * Check if this is a transition
     */
    isTransition() {
        const { LINE_TYPE } = window.TrelbyConstants;
        return this.type === LINE_TYPE.TRANSITION;
    }

    /**
     * Compare with another line
     */
    equals(other) {
        if (!other) return false;
        return this.lb === other.lb &&
            this.type === other.type &&
            this.text === other.text;
    }
}

window.TrelbyLine = Line;
