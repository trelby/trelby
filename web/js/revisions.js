/**
 * Courius - Revision Tracking Module
 * Tracks changes with colored revision marks and comparison views
 */

class RevisionManager {
    constructor(screenplay) {
        this.screenplay = screenplay;
        this.revisions = [];
        this.currentRevision = null;
        this.colors = [
            '#FF0000', // Red - 1st revision
            '#0000FF', // Blue - 2nd revision
            '#00FF00', // Green - 3rd revision
            '#FFA500', // Orange - 4th revision
            '#800080', // Purple - 5th revision
            '#FFFF00', // Yellow - 6th revision
            '#00FFFF', // Cyan - 7th revision
            '#FF00FF'  // Magenta - 8th revision
        ];
        this.colorNames = [
            'White (Original)',
            'Blue',
            'Pink',
            'Yellow',
            'Green',
            'Goldenrod',
            'Buff',
            'Salmon',
            'Cherry'
        ];

        this._init();
    }

    /**
     * Initialize from stored revisions
     */
    _init() {
        const stored = localStorage.getItem('courius-revisions');
        if (stored) {
            try {
                const data = JSON.parse(stored);
                this.revisions = data.revisions || [];
                this.currentRevision = data.currentRevision;
            } catch (e) {
                console.warn('Failed to load revisions:', e);
            }
        }
    }

    /**
     * Save revisions to localStorage
     */
    _save() {
        localStorage.setItem('courius-revisions', JSON.stringify({
            revisions: this.revisions,
            currentRevision: this.currentRevision
        }));
    }

    /**
     * Create a new revision snapshot
     */
    createRevision(name) {
        const revision = {
            id: Date.now().toString(36) + Math.random().toString(36).substr(2),
            name: name || `Revision ${this.revisions.length + 1}`,
            date: new Date().toISOString(),
            colorIndex: this.revisions.length % this.colors.length,
            lines: []
        };

        // Store current state
        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            revision.lines.push({
                type: line.type,
                text: line.text,
                lb: line.lb
            });
        }

        this.revisions.push(revision);
        this.currentRevision = revision.id;
        this._save();

        return revision;
    }

    /**
     * Get all revisions
     */
    getRevisions() {
        return this.revisions.map(r => ({
            id: r.id,
            name: r.name,
            date: r.date,
            color: this.colors[r.colorIndex],
            colorName: this.colorNames[r.colorIndex + 1],
            lineCount: r.lines.length
        }));
    }

    /**
     * Get a specific revision
     */
    getRevision(id) {
        return this.revisions.find(r => r.id === id);
    }

    /**
     * Delete a revision
     */
    deleteRevision(id) {
        const index = this.revisions.findIndex(r => r.id === id);
        if (index !== -1) {
            this.revisions.splice(index, 1);

            if (this.currentRevision === id) {
                this.currentRevision = this.revisions.length > 0
                    ? this.revisions[this.revisions.length - 1].id
                    : null;
            }

            this._save();
            return true;
        }
        return false;
    }

    /**
     * Rename a revision
     */
    renameRevision(id, newName) {
        const revision = this.getRevision(id);
        if (revision) {
            revision.name = newName;
            this._save();
            return true;
        }
        return false;
    }

    /**
     * Compare current screenplay with a revision
     */
    compare(revisionId) {
        const revision = this.getRevision(revisionId);
        if (!revision) return null;

        const diff = {
            added: [],
            removed: [],
            modified: [],
            unchanged: []
        };

        const currentLines = [];
        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            currentLines.push({ type: line.type, text: line.text });
        }

        const revisionLines = revision.lines;

        // Use LCS algorithm for comparison
        const lcs = this._computeLCS(revisionLines, currentLines);

        let revIdx = 0;
        let curIdx = 0;
        let lcsIdx = 0;

        while (revIdx < revisionLines.length || curIdx < currentLines.length) {
            if (lcsIdx < lcs.length) {
                const lcsItem = lcs[lcsIdx];

                // Add removed lines (in revision but not in LCS)
                while (revIdx < lcsItem.revisionIndex) {
                    diff.removed.push({
                        lineIndex: revIdx,
                        line: revisionLines[revIdx],
                        revisionColor: this.colors[revision.colorIndex]
                    });
                    revIdx++;
                }

                // Add added lines (in current but not in LCS)
                while (curIdx < lcsItem.currentIndex) {
                    diff.added.push({
                        lineIndex: curIdx,
                        line: currentLines[curIdx],
                        currentIndex: curIdx
                    });
                    curIdx++;
                }

                // Check if line was modified (same position but different content)
                if (revisionLines[revIdx].text !== currentLines[curIdx].text ||
                    revisionLines[revIdx].type !== currentLines[curIdx].type) {
                    diff.modified.push({
                        lineIndex: curIdx,
                        oldLine: revisionLines[revIdx],
                        newLine: currentLines[curIdx],
                        revisionColor: this.colors[revision.colorIndex]
                    });
                } else {
                    diff.unchanged.push({
                        lineIndex: curIdx,
                        line: currentLines[curIdx]
                    });
                }

                revIdx++;
                curIdx++;
                lcsIdx++;
            } else {
                // Remaining lines
                while (revIdx < revisionLines.length) {
                    diff.removed.push({
                        lineIndex: revIdx,
                        line: revisionLines[revIdx],
                        revisionColor: this.colors[revision.colorIndex]
                    });
                    revIdx++;
                }

                while (curIdx < currentLines.length) {
                    diff.added.push({
                        lineIndex: curIdx,
                        line: currentLines[curIdx],
                        currentIndex: curIdx
                    });
                    curIdx++;
                }
            }
        }

        return {
            revision: {
                id: revision.id,
                name: revision.name,
                date: revision.date,
                color: this.colors[revision.colorIndex]
            },
            diff,
            summary: {
                added: diff.added.length,
                removed: diff.removed.length,
                modified: diff.modified.length,
                unchanged: diff.unchanged.length
            }
        };
    }

    /**
     * Compute Longest Common Subsequence
     */
    _computeLCS(a, b) {
        const m = a.length;
        const n = b.length;
        const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

        // Build LCS table
        for (let i = 1; i <= m; i++) {
            for (let j = 1; j <= n; j++) {
                if (this._linesEqual(a[i - 1], b[j - 1])) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                } else {
                    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
                }
            }
        }

        // Backtrack to find LCS
        const lcs = [];
        let i = m, j = n;

        while (i > 0 && j > 0) {
            if (this._linesEqual(a[i - 1], b[j - 1])) {
                lcs.unshift({
                    revisionIndex: i - 1,
                    currentIndex: j - 1
                });
                i--;
                j--;
            } else if (dp[i - 1][j] > dp[i][j - 1]) {
                i--;
            } else {
                j--;
            }
        }

        return lcs;
    }

    /**
     * Check if two lines are equal
     */
    _linesEqual(a, b) {
        return a.type === b.type && a.text === b.text;
    }

    /**
     * Mark lines as revised in the current screenplay
     */
    markAsRevised(lineIndices, revisionColor = null) {
        const color = revisionColor || this.colors[this.revisions.length % this.colors.length];

        for (const index of lineIndices) {
            const line = this.screenplay.getLine(index);
            if (line) {
                line.revisionMark = {
                    color,
                    date: new Date().toISOString()
                };
            }
        }
    }

    /**
     * Clear revision marks from lines
     */
    clearRevisionMarks(lineIndices = null) {
        const indices = lineIndices || Array.from(
            { length: this.screenplay.lineCount },
            (_, i) => i
        );

        for (const index of indices) {
            const line = this.screenplay.getLine(index);
            if (line && line.revisionMark) {
                delete line.revisionMark;
            }
        }
    }

    /**
     * Get lines with revision marks
     */
    getRevisedLines() {
        const revised = [];

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            if (line.revisionMark) {
                revised.push({
                    lineIndex: i,
                    line,
                    mark: line.revisionMark
                });
            }
        }

        return revised;
    }

    /**
     * Restore screenplay to a specific revision
     */
    restore(revisionId) {
        const revision = this.getRevision(revisionId);
        if (!revision) return false;

        // Clear current lines
        while (this.screenplay.lineCount > 0) {
            this.screenplay.deleteLine(0);
        }

        // Restore lines from revision
        const Line = window.CouriusLine;
        const { LB } = window.CouriusConstants;

        for (const lineData of revision.lines) {
            const line = new Line(
                lineData.lb || LB.LAST,
                lineData.type,
                lineData.text
            );
            this.screenplay.addLine(line);
        }

        return true;
    }

    /**
     * Render comparison view as HTML
     */
    renderComparisonHTML(comparison) {
        if (!comparison) return '<p>No comparison available</p>';

        const { revision, diff, summary } = comparison;

        let html = `
            <div class="revision-comparison">
                <div class="comparison-header">
                    <h3>Comparing with: ${this._escapeHTML(revision.name)}</h3>
                    <span class="comparison-date">${new Date(revision.date).toLocaleString()}</span>
                </div>
                <div class="comparison-summary">
                    <span class="added">+${summary.added} added</span>
                    <span class="removed">-${summary.removed} removed</span>
                    <span class="modified">~${summary.modified} modified</span>
                </div>
                <div class="comparison-lines">
        `;

        // Sort all changes by line index
        const allChanges = [
            ...diff.added.map(c => ({ ...c, changeType: 'added' })),
            ...diff.removed.map(c => ({ ...c, changeType: 'removed' })),
            ...diff.modified.map(c => ({ ...c, changeType: 'modified' })),
            ...diff.unchanged.map(c => ({ ...c, changeType: 'unchanged' }))
        ].sort((a, b) => a.lineIndex - b.lineIndex);

        for (const change of allChanges) {
            const lineNum = change.lineIndex + 1;

            switch (change.changeType) {
                case 'added':
                    html += `
                        <div class="diff-line diff-added">
                            <span class="line-num">${lineNum}</span>
                            <span class="diff-marker">+</span>
                            <span class="line-content">${this._escapeHTML(change.line.text)}</span>
                        </div>
                    `;
                    break;

                case 'removed':
                    html += `
                        <div class="diff-line diff-removed" style="border-left-color: ${change.revisionColor}">
                            <span class="line-num">${lineNum}</span>
                            <span class="diff-marker">-</span>
                            <span class="line-content">${this._escapeHTML(change.line.text)}</span>
                        </div>
                    `;
                    break;

                case 'modified':
                    html += `
                        <div class="diff-line diff-modified" style="border-left-color: ${change.revisionColor}">
                            <span class="line-num">${lineNum}</span>
                            <span class="diff-marker">~</span>
                            <div class="line-content">
                                <div class="old-text">${this._escapeHTML(change.oldLine.text)}</div>
                                <div class="new-text">${this._escapeHTML(change.newLine.text)}</div>
                            </div>
                        </div>
                    `;
                    break;

                default:
                    // Unchanged - optionally show for context
                    break;
            }
        }

        html += '</div></div>';
        return html;
    }

    /**
     * Export revisions as JSON
     */
    export() {
        return JSON.stringify({
            exported: new Date().toISOString(),
            revisions: this.revisions
        }, null, 2);
    }

    /**
     * Import revisions from JSON
     */
    import(json) {
        try {
            const data = typeof json === 'string' ? JSON.parse(json) : json;

            if (data.revisions && Array.isArray(data.revisions)) {
                // Merge revisions, avoiding duplicates by ID
                const existingIds = new Set(this.revisions.map(r => r.id));

                for (const revision of data.revisions) {
                    if (!existingIds.has(revision.id)) {
                        this.revisions.push(revision);
                    }
                }

                this._save();
                return true;
            }
        } catch (e) {
            console.error('Failed to import revisions:', e);
        }

        return false;
    }

    /**
     * Escape HTML
     */
    _escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    /**
     * Get revision color for a line
     */
    getLineRevisionColor(lineIndex) {
        const line = this.screenplay.getLine(lineIndex);
        return line?.revisionMark?.color || null;
    }

    /**
     * Clear all revisions
     */
    clearAll() {
        this.revisions = [];
        this.currentRevision = null;
        this._save();
    }
}

window.CouriusRevisions = RevisionManager;
