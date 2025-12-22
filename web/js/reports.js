/**
 * Trelby Web - Reports
 * Generate various screenplay analysis reports
 */

class Reports {
    constructor() {
        this.currentReport = null;
    }

    /**
     * Generate a scene report
     */
    generateSceneReport(screenplay) {
        const scenes = screenplay.getScenes();

        const report = {
            title: 'Scene Report',
            summary: {
                totalScenes: scenes.length,
                interiorScenes: 0,
                exteriorScenes: 0,
                dayScenes: 0,
                nightScenes: 0
            },
            data: []
        };

        for (let i = 0; i < scenes.length; i++) {
            const scene = scenes[i];
            const sceneData = {
                number: i + 1,
                page: scene.page,
                lineNumber: scene.index + 1,
                heading: scene.text,
                intExt: '',
                location: '',
                timeOfDay: ''
            };

            // Parse scene heading
            const match = scene.text.match(/^(INT\.?|EXT\.?|INT\.?\/EXT\.?|I\/E\.?)\s*(.+?)(?:\s*-\s*(.+))?$/i);
            if (match) {
                sceneData.intExt = match[1].toUpperCase();
                sceneData.location = match[2].trim();
                sceneData.timeOfDay = match[3] ? match[3].trim() : '';

                // Count types
                if (sceneData.intExt.startsWith('INT')) {
                    report.summary.interiorScenes++;
                } else if (sceneData.intExt.startsWith('EXT')) {
                    report.summary.exteriorScenes++;
                }

                const time = sceneData.timeOfDay.toUpperCase();
                if (time.includes('DAY') || time.includes('MORNING') || time.includes('AFTERNOON')) {
                    report.summary.dayScenes++;
                } else if (time.includes('NIGHT') || time.includes('EVENING') || time.includes('DUSK')) {
                    report.summary.nightScenes++;
                }
            }

            report.data.push(sceneData);
        }

        this.currentReport = report;
        return report;
    }

    /**
     * Generate a character report
     */
    generateCharacterReport(screenplay) {
        const characters = screenplay.getCharacters();

        const report = {
            title: 'Character Report',
            summary: {
                totalCharacters: characters.size,
                totalDialogueLines: 0,
                totalWords: 0
            },
            data: []
        };

        for (const [name, char] of characters) {
            report.summary.totalDialogueLines += char.dialogueLines;
            report.summary.totalWords += char.wordCount;

            report.data.push({
                name: name,
                appearances: char.lineCount,
                dialogueLines: char.dialogueLines,
                wordCount: char.wordCount,
                sceneCount: char.scenes.size,
                scenes: Array.from(char.scenes)
            });
        }

        // Sort by dialogue lines (most speaking first)
        report.data.sort((a, b) => b.dialogueLines - a.dialogueLines);

        this.currentReport = report;
        return report;
    }

    /**
     * Generate a location report
     */
    generateLocationReport(screenplay) {
        const locations = screenplay.getLocations();

        const report = {
            title: 'Location Report',
            summary: {
                totalLocations: locations.size,
                totalScenes: 0
            },
            data: []
        };

        for (const [name, loc] of locations) {
            report.summary.totalScenes += loc.scenes.length;

            // Categorize by INT/EXT
            let intCount = 0;
            let extCount = 0;
            const pages = new Set();

            for (const scene of loc.scenes) {
                pages.add(scene.page);
                if (scene.text.startsWith('INT')) intCount++;
                else if (scene.text.startsWith('EXT')) extCount++;
            }

            report.data.push({
                location: name,
                sceneCount: loc.scenes.length,
                interiorCount: intCount,
                exteriorCount: extCount,
                pages: Array.from(pages).sort((a, b) => a - b),
                scenes: loc.scenes.map(s => s.text)
            });
        }

        // Sort by scene count
        report.data.sort((a, b) => b.sceneCount - a.sceneCount);

        this.currentReport = report;
        return report;
    }

    /**
     * Generate a full script report
     */
    generateScriptReport(screenplay) {
        const { LINE_TYPE } = window.TrelbyConstants;

        const report = {
            title: 'Script Report',
            summary: {
                totalPages: screenplay.getPageCount(),
                totalLines: screenplay.lineCount,
                totalWords: screenplay.getWordCount(),
                estimatedRuntime: 0, // 1 page = ~1 minute
                elementCounts: {}
            },
            data: {
                scenes: [],
                characters: [],
                pageBreakdown: []
            }
        };

        // Count element types
        for (const type of Object.values(LINE_TYPE)) {
            report.summary.elementCounts[type] = 0;
        }

        for (const line of screenplay.lines) {
            report.summary.elementCounts[line.type]++;
        }

        // Estimated runtime (1 page ≈ 1 minute)
        report.summary.estimatedRuntime = report.summary.totalPages;

        // Get scene and character data
        const scenes = screenplay.getScenes();
        const characters = screenplay.getCharacters();

        report.data.scenes = scenes.slice(0, 10).map((s, i) => ({
            number: i + 1,
            heading: s.text.substring(0, 50) + (s.text.length > 50 ? '...' : ''),
            page: s.page
        }));

        report.data.characters = Array.from(characters.values())
            .sort((a, b) => b.dialogueLines - a.dialogueLines)
            .slice(0, 10)
            .map(c => ({
                name: c.name,
                dialogueLines: c.dialogueLines,
                wordCount: c.wordCount
            }));

        // Page breakdown
        const pageBreaks = screenplay.calculatePageBreaks();
        for (let i = 0; i < pageBreaks.length; i++) {
            const startLine = pageBreaks[i];
            const endLine = (i < pageBreaks.length - 1) ? pageBreaks[i + 1] - 1 : screenplay.lineCount - 1;

            let pageWords = 0;
            let pageDialogue = 0;
            let pageAction = 0;

            for (let j = startLine; j <= endLine; j++) {
                const line = screenplay.getLine(j);
                if (line) {
                    pageWords += window.TrelbyUtils.countWords(line.text);
                    if (line.type === LINE_TYPE.DIALOGUE) pageDialogue++;
                    if (line.type === LINE_TYPE.ACTION) pageAction++;
                }
            }

            report.data.pageBreakdown.push({
                page: i + 1,
                words: pageWords,
                dialogueLines: pageDialogue,
                actionLines: pageAction
            });
        }

        this.currentReport = report;
        return report;
    }

    /**
     * Generate a dialogue chart (shows dialogue distribution)
     */
    generateDialogueChart(screenplay) {
        const characters = screenplay.getCharacters();

        const report = {
            title: 'Dialogue Chart',
            summary: {
                totalDialogue: 0,
                characterCount: characters.size
            },
            data: []
        };

        // Calculate total dialogue
        for (const char of characters.values()) {
            report.summary.totalDialogue += char.wordCount;
        }

        // Create chart data
        for (const [name, char] of characters) {
            const percentage = report.summary.totalDialogue > 0
                ? (char.wordCount / report.summary.totalDialogue * 100).toFixed(1)
                : 0;

            report.data.push({
                character: name,
                words: char.wordCount,
                lines: char.dialogueLines,
                percentage: parseFloat(percentage),
                bar: '█'.repeat(Math.round(percentage / 2))
            });
        }

        // Sort by word count
        report.data.sort((a, b) => b.words - a.words);

        this.currentReport = report;
        return report;
    }

    /**
     * Render report as HTML table
     */
    renderAsHTML(report) {
        let html = `<div class="report">
            <h2>${window.TrelbyUtils.escapeHtml(report.title)}</h2>
            <div class="report-summary">`;

        // Render summary
        for (const [key, value] of Object.entries(report.summary)) {
            if (typeof value === 'object') continue;
            const label = this._formatLabel(key);
            html += `<div class="summary-item"><span class="label">${label}:</span> <span class="value">${value}</span></div>`;
        }

        html += `</div>`;

        // Render data table if present
        if (report.data && report.data.length > 0) {
            html += `<table class="report-table">`;

            // Header row
            const firstRow = report.data[0];
            html += `<thead><tr>`;
            for (const key of Object.keys(firstRow)) {
                if (Array.isArray(firstRow[key])) continue; // Skip arrays
                html += `<th>${this._formatLabel(key)}</th>`;
            }
            html += `</tr></thead>`;

            // Data rows
            html += `<tbody>`;
            for (const row of report.data) {
                html += `<tr>`;
                for (const [key, value] of Object.entries(row)) {
                    if (Array.isArray(value)) continue;
                    html += `<td>${window.TrelbyUtils.escapeHtml(String(value))}</td>`;
                }
                html += `</tr>`;
            }
            html += `</tbody></table>`;
        }

        html += `</div>`;
        return html;
    }

    /**
     * Export report as CSV
     */
    exportAsCSV(report) {
        if (!report.data || report.data.length === 0) {
            return '';
        }

        const rows = [];

        // Header row
        const firstRow = report.data[0];
        const headers = Object.keys(firstRow).filter(k => !Array.isArray(firstRow[k]));
        rows.push(headers.map(h => this._formatLabel(h)).join(','));

        // Data rows
        for (const row of report.data) {
            const values = headers.map(h => {
                const value = row[h];
                // Escape commas and quotes
                if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                    return `"${value.replace(/"/g, '""')}"`;
                }
                return String(value);
            });
            rows.push(values.join(','));
        }

        return rows.join('\n');
    }

    /**
     * Format camelCase/snake_case to readable label
     */
    _formatLabel(key) {
        return key
            .replace(/([A-Z])/g, ' $1')
            .replace(/_/g, ' ')
            .replace(/^\w/, c => c.toUpperCase())
            .trim();
    }

    /**
     * Download report as file
     */
    downloadReport(report, format = 'html') {
        const filename = report.title.toLowerCase().replace(/\s+/g, '-');

        if (format === 'csv') {
            const csv = this.exportAsCSV(report);
            window.TrelbyUtils.downloadFile(csv, `${filename}.csv`, 'text/csv');
        } else {
            const html = this.renderAsHTML(report);
            const fullHtml = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>${report.title}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .report-summary { margin: 20px 0; padding: 10px; background: #f5f5f5; }
        .summary-item { margin: 5px 0; }
        .label { font-weight: bold; }
        .report-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .report-table th, .report-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .report-table th { background: #f0f0f0; }
        .report-table tr:nth-child(even) { background: #fafafa; }
    </style>
</head>
<body>${html}</body>
</html>`;
            window.TrelbyUtils.downloadFile(fullHtml, `${filename}.html`, 'text/html');
        }
    }
}

window.TrelbyReports = Reports;
