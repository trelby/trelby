/**
 * Courius - Visual Statistics Module
 * Provides visual analysis of screenplay with charts and graphs
 * Uses simple SVG-based charts (no D3 dependency for lighter weight)
 */

class ScreenplayStatistics {
    constructor(screenplay) {
        this.screenplay = screenplay;
        this.stats = null;
    }

    /**
     * Analyze the screenplay and generate statistics
     */
    analyze() {
        this.stats = {
            general: this._analyzeGeneral(),
            scenes: this._analyzeScenes(),
            characters: this._analyzeCharacters(),
            pacing: this._analyzePacing(),
            locations: this._analyzeLocations(),
            dialogueVsAction: this._analyzeDialogueVsAction()
        };

        return this.stats;
    }

    /**
     * General statistics
     */
    _analyzeGeneral() {
        const { LINE_TYPE } = window.CouriusConstants;
        const lineCount = this.screenplay.lineCount;
        let wordCount = 0;
        let charCount = 0;

        const typeCounts = {};
        for (const type of Object.values(LINE_TYPE)) {
            typeCounts[type] = 0;
        }

        for (let i = 0; i < lineCount; i++) {
            const line = this.screenplay.getLine(i);
            typeCounts[line.type] = (typeCounts[line.type] || 0) + 1;

            const text = line.text || '';
            wordCount += text.split(/\s+/).filter(w => w.length > 0).length;
            charCount += text.length;
        }

        return {
            lineCount,
            wordCount,
            charCount,
            pageCount: this.screenplay.getPageCount(),
            estimatedDuration: Math.round(this.screenplay.getPageCount()), // ~1 min per page
            typeCounts
        };
    }

    /**
     * Scene statistics
     */
    _analyzeScenes() {
        const { LINE_TYPE } = window.CouriusConstants;
        const scenes = [];
        let currentScene = null;

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);

            if (line.type === LINE_TYPE.SCENE) {
                if (currentScene) {
                    currentScene.endLine = i - 1;
                    currentScene.lineCount = currentScene.endLine - currentScene.startLine + 1;
                    scenes.push(currentScene);
                }

                const parsed = this._parseSceneHeading(line.text);
                currentScene = {
                    index: scenes.length,
                    startLine: i,
                    text: line.text,
                    ...parsed
                };
            }
        }

        if (currentScene) {
            currentScene.endLine = this.screenplay.lineCount - 1;
            currentScene.lineCount = currentScene.endLine - currentScene.startLine + 1;
            scenes.push(currentScene);
        }

        // Calculate statistics
        const intCount = scenes.filter(s => s.intExt === 'INT').length;
        const extCount = scenes.filter(s => s.intExt === 'EXT').length;
        const mixedCount = scenes.length - intCount - extCount;

        const timeOfDayCounts = {};
        scenes.forEach(s => {
            const tod = s.timeOfDay || 'UNKNOWN';
            timeOfDayCounts[tod] = (timeOfDayCounts[tod] || 0) + 1;
        });

        const avgLength = scenes.length > 0
            ? Math.round(scenes.reduce((sum, s) => sum + s.lineCount, 0) / scenes.length)
            : 0;

        const lengths = scenes.map(s => s.lineCount).sort((a, b) => a - b);
        const shortestScene = lengths[0] || 0;
        const longestScene = lengths[lengths.length - 1] || 0;

        return {
            total: scenes.length,
            interior: intCount,
            exterior: extCount,
            mixed: mixedCount,
            timeOfDayCounts,
            avgLength,
            shortestScene,
            longestScene,
            scenes
        };
    }

    /**
     * Character statistics
     */
    _analyzeCharacters() {
        const { LINE_TYPE } = window.CouriusConstants;
        const characters = new Map();
        let currentCharacter = null;

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);

            if (line.type === LINE_TYPE.CHARACTER) {
                currentCharacter = this._normalizeCharacterName(line.text);

                if (!characters.has(currentCharacter)) {
                    characters.set(currentCharacter, {
                        name: currentCharacter,
                        dialogueLines: 0,
                        wordCount: 0,
                        sceneAppearances: new Set(),
                        firstAppearance: i
                    });
                }
            } else if (line.type === LINE_TYPE.DIALOGUE && currentCharacter) {
                const char = characters.get(currentCharacter);
                if (char) {
                    char.dialogueLines++;
                    char.wordCount += (line.text || '').split(/\s+/).filter(w => w.length > 0).length;
                }
            } else if (line.type === LINE_TYPE.SCENE) {
                currentCharacter = null;
            }
        }

        // Add scene appearances
        const scenes = this._analyzeScenes().scenes;
        for (const scene of scenes) {
            for (let i = scene.startLine; i <= scene.endLine; i++) {
                const line = this.screenplay.getLine(i);
                if (line.type === LINE_TYPE.CHARACTER) {
                    const name = this._normalizeCharacterName(line.text);
                    const char = characters.get(name);
                    if (char) {
                        char.sceneAppearances.add(scene.index);
                    }
                }
            }
        }

        // Convert to array and sort
        const characterList = [...characters.values()]
            .map(c => ({
                ...c,
                sceneCount: c.sceneAppearances.size,
                sceneAppearances: [...c.sceneAppearances]
            }))
            .sort((a, b) => b.dialogueLines - a.dialogueLines);

        return {
            total: characterList.length,
            characters: characterList,
            topSpeakers: characterList.slice(0, 10)
        };
    }

    /**
     * Normalize character name (remove parentheticals)
     */
    _normalizeCharacterName(name) {
        return (name || '')
            .replace(/\s*\(.*\)\s*/g, '')
            .trim()
            .toUpperCase();
    }

    /**
     * Pacing analysis (dialogue vs action over time)
     */
    _analyzePacing() {
        const { LINE_TYPE } = window.CouriusConstants;
        const segments = [];
        const segmentSize = Math.max(1, Math.floor(this.screenplay.lineCount / 20)); // 20 segments

        for (let i = 0; i < this.screenplay.lineCount; i += segmentSize) {
            let dialogueLines = 0;
            let actionLines = 0;
            let otherLines = 0;

            const endLine = Math.min(i + segmentSize, this.screenplay.lineCount);

            for (let j = i; j < endLine; j++) {
                const line = this.screenplay.getLine(j);

                if (line.type === LINE_TYPE.DIALOGUE || line.type === LINE_TYPE.PAREN) {
                    dialogueLines++;
                } else if (line.type === LINE_TYPE.ACTION) {
                    actionLines++;
                } else {
                    otherLines++;
                }
            }

            const total = dialogueLines + actionLines + otherLines;
            segments.push({
                startLine: i,
                endLine: endLine - 1,
                dialogueRatio: total > 0 ? dialogueLines / total : 0,
                actionRatio: total > 0 ? actionLines / total : 0,
                dialogueLines,
                actionLines,
                otherLines
            });
        }

        return {
            segments,
            segmentSize
        };
    }

    /**
     * Location analysis
     */
    _analyzeLocations() {
        const scenes = this._analyzeScenes().scenes;
        const locations = new Map();

        for (const scene of scenes) {
            const location = scene.location || 'UNKNOWN';

            if (!locations.has(location)) {
                locations.set(location, {
                    name: location,
                    count: 0,
                    scenes: [],
                    intCount: 0,
                    extCount: 0
                });
            }

            const loc = locations.get(location);
            loc.count++;
            loc.scenes.push(scene.index);

            if (scene.intExt === 'INT') loc.intCount++;
            else if (scene.intExt === 'EXT') loc.extCount++;
        }

        const locationList = [...locations.values()]
            .sort((a, b) => b.count - a.count);

        return {
            total: locationList.length,
            locations: locationList,
            topLocations: locationList.slice(0, 10)
        };
    }

    /**
     * Dialogue vs Action ratio analysis
     */
    _analyzeDialogueVsAction() {
        const { LINE_TYPE } = window.CouriusConstants;
        let dialogueWords = 0;
        let actionWords = 0;
        let dialogueLines = 0;
        let actionLines = 0;

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            const wordCount = (line.text || '').split(/\s+/).filter(w => w.length > 0).length;

            if (line.type === LINE_TYPE.DIALOGUE) {
                dialogueWords += wordCount;
                dialogueLines++;
            } else if (line.type === LINE_TYPE.ACTION) {
                actionWords += wordCount;
                actionLines++;
            }
        }

        const totalWords = dialogueWords + actionWords;
        const totalLines = dialogueLines + actionLines;

        return {
            dialogueWords,
            actionWords,
            dialogueLines,
            actionLines,
            dialogueWordRatio: totalWords > 0 ? dialogueWords / totalWords : 0,
            dialogueLineRatio: totalLines > 0 ? dialogueLines / totalLines : 0
        };
    }

    /**
     * Parse scene heading
     */
    _parseSceneHeading(text) {
        const normalized = (text || '').toUpperCase().trim();
        const match = normalized.match(/^(INT\.?|EXT\.?|INT\.?\/EXT\.?|I\/E\.?)\s*[-.]?\s*(.+?)\s*[-–—]\s*(.+)$/);

        if (match) {
            return {
                intExt: match[1].replace('.', ''),
                location: match[2].trim(),
                timeOfDay: match[3].trim()
            };
        }

        const match2 = normalized.match(/^(INT\.?|EXT\.?|INT\.?\/EXT\.?|I\/E\.?)\s*[-.]?\s*(.+)$/);
        if (match2) {
            return {
                intExt: match2[1].replace('.', ''),
                location: match2[2].trim(),
                timeOfDay: ''
            };
        }

        return { intExt: '', location: text, timeOfDay: '' };
    }

    /**
     * Render statistics as HTML
     */
    renderHTML() {
        if (!this.stats) this.analyze();

        return `
            <div class="stats-container">
                ${this._renderGeneralStats()}
                ${this._renderSceneStats()}
                ${this._renderCharacterStats()}
                ${this._renderPacingChart()}
                ${this._renderLocationStats()}
            </div>
        `;
    }

    /**
     * Render general statistics section
     */
    _renderGeneralStats() {
        const s = this.stats.general;

        return `
            <div class="stats-section">
                <h3>General Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">${s.pageCount}</div>
                        <div class="stat-label">Pages</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${s.wordCount.toLocaleString()}</div>
                        <div class="stat-label">Words</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">~${s.estimatedDuration} min</div>
                        <div class="stat-label">Est. Duration</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${this.stats.scenes.total}</div>
                        <div class="stat-label">Scenes</div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render scene statistics section
     */
    _renderSceneStats() {
        const s = this.stats.scenes;

        // INT/EXT pie chart
        const total = s.interior + s.exterior + s.mixed;
        const pieData = [
            { label: 'INT', value: s.interior, color: '#4CAF50' },
            { label: 'EXT', value: s.exterior, color: '#2196F3' },
            { label: 'I/E', value: s.mixed, color: '#FF9800' }
        ].filter(d => d.value > 0);

        return `
            <div class="stats-section">
                <h3>Scene Analysis</h3>
                <div class="stats-row">
                    <div class="chart-container">
                        <h4>Interior vs Exterior</h4>
                        ${this._renderPieChart(pieData, 150)}
                    </div>
                    <div class="stats-details">
                        <div class="stat-row">
                            <span>Interior scenes:</span>
                            <span>${s.interior} (${Math.round(s.interior / total * 100)}%)</span>
                        </div>
                        <div class="stat-row">
                            <span>Exterior scenes:</span>
                            <span>${s.exterior} (${Math.round(s.exterior / total * 100)}%)</span>
                        </div>
                        <div class="stat-row">
                            <span>Average scene length:</span>
                            <span>${s.avgLength} lines</span>
                        </div>
                        <div class="stat-row">
                            <span>Longest scene:</span>
                            <span>${s.longestScene} lines</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Render character statistics section
     */
    _renderCharacterStats() {
        const s = this.stats.characters;

        // Bar chart data for top speakers
        const barData = s.topSpeakers.slice(0, 8).map(c => ({
            label: c.name.length > 12 ? c.name.substring(0, 12) + '...' : c.name,
            value: c.dialogueLines
        }));

        return `
            <div class="stats-section">
                <h3>Character Analysis</h3>
                <p class="stats-subtitle">${s.total} speaking characters</p>
                <div class="chart-container">
                    <h4>Top Speakers (by dialogue lines)</h4>
                    ${this._renderBarChart(barData, 400, 200)}
                </div>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>Character</th>
                            <th>Lines</th>
                            <th>Words</th>
                            <th>Scenes</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${s.topSpeakers.slice(0, 10).map(c => `
                            <tr>
                                <td>${this._escapeHTML(c.name)}</td>
                                <td>${c.dialogueLines}</td>
                                <td>${c.wordCount}</td>
                                <td>${c.sceneCount}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    /**
     * Render pacing chart section
     */
    _renderPacingChart() {
        const s = this.stats.pacing;
        const dvaStats = this.stats.dialogueVsAction;

        return `
            <div class="stats-section">
                <h3>Pacing Analysis</h3>
                <div class="stats-row">
                    <div class="chart-container">
                        <h4>Dialogue vs Action (overall)</h4>
                        ${this._renderPieChart([
                            { label: 'Dialogue', value: dvaStats.dialogueWords, color: '#9C27B0' },
                            { label: 'Action', value: dvaStats.actionWords, color: '#FF5722' }
                        ], 150)}
                    </div>
                    <div class="stats-details">
                        <div class="stat-row">
                            <span>Dialogue:</span>
                            <span>${Math.round(dvaStats.dialogueWordRatio * 100)}% of words</span>
                        </div>
                        <div class="stat-row">
                            <span>Action:</span>
                            <span>${Math.round((1 - dvaStats.dialogueWordRatio) * 100)}% of words</span>
                        </div>
                    </div>
                </div>
                <div class="chart-container">
                    <h4>Pacing Through Script</h4>
                    ${this._renderAreaChart(s.segments, 500, 150)}
                </div>
            </div>
        `;
    }

    /**
     * Render location statistics section
     */
    _renderLocationStats() {
        const s = this.stats.locations;

        return `
            <div class="stats-section">
                <h3>Location Analysis</h3>
                <p class="stats-subtitle">${s.total} unique locations</p>
                <table class="stats-table">
                    <thead>
                        <tr>
                            <th>Location</th>
                            <th>Scenes</th>
                            <th>INT</th>
                            <th>EXT</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${s.topLocations.slice(0, 10).map(loc => `
                            <tr>
                                <td>${this._escapeHTML(loc.name)}</td>
                                <td>${loc.count}</td>
                                <td>${loc.intCount}</td>
                                <td>${loc.extCount}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    /**
     * Render a simple SVG pie chart
     */
    _renderPieChart(data, size) {
        if (data.length === 0) return '<p>No data</p>';

        const total = data.reduce((sum, d) => sum + d.value, 0);
        if (total === 0) return '<p>No data</p>';

        const center = size / 2;
        const radius = size / 2 - 10;
        let currentAngle = -Math.PI / 2;

        const slices = data.map(d => {
            const sliceAngle = (d.value / total) * 2 * Math.PI;
            const startAngle = currentAngle;
            const endAngle = currentAngle + sliceAngle;
            currentAngle = endAngle;

            const x1 = center + radius * Math.cos(startAngle);
            const y1 = center + radius * Math.sin(startAngle);
            const x2 = center + radius * Math.cos(endAngle);
            const y2 = center + radius * Math.sin(endAngle);

            const largeArc = sliceAngle > Math.PI ? 1 : 0;

            const path = sliceAngle >= 2 * Math.PI - 0.01
                ? `M ${center} ${center - radius} A ${radius} ${radius} 0 1 1 ${center - 0.01} ${center - radius} Z`
                : `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;

            return { ...d, path };
        });

        const legend = data.map((d, i) => {
            const percent = Math.round((d.value / total) * 100);
            return `<div class="legend-item"><span class="legend-color" style="background:${d.color}"></span>${d.label} (${percent}%)</div>`;
        }).join('');

        return `
            <div class="pie-chart-container">
                <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
                    ${slices.map(s => `<path d="${s.path}" fill="${s.color}" stroke="#fff" stroke-width="2"/>`).join('')}
                </svg>
                <div class="chart-legend">${legend}</div>
            </div>
        `;
    }

    /**
     * Render a simple SVG bar chart
     */
    _renderBarChart(data, width, height) {
        if (data.length === 0) return '<p>No data</p>';

        const maxValue = Math.max(...data.map(d => d.value));
        if (maxValue === 0) return '<p>No data</p>';

        const barWidth = Math.floor((width - 40) / data.length) - 4;
        const chartHeight = height - 40;
        const colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336', '#00BCD4', '#795548', '#607D8B'];

        const bars = data.map((d, i) => {
            const barHeight = (d.value / maxValue) * chartHeight;
            const x = 30 + i * (barWidth + 4);
            const y = chartHeight - barHeight + 10;

            return `
                <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" fill="${colors[i % colors.length]}" rx="2"/>
                <text x="${x + barWidth / 2}" y="${height - 5}" text-anchor="middle" font-size="10" fill="#666">${d.label}</text>
                <text x="${x + barWidth / 2}" y="${y - 5}" text-anchor="middle" font-size="10" fill="#333">${d.value}</text>
            `;
        }).join('');

        return `
            <svg width="${width}" height="${height}" class="bar-chart">
                <line x1="30" y1="10" x2="30" y2="${chartHeight + 10}" stroke="#ccc" stroke-width="1"/>
                <line x1="30" y1="${chartHeight + 10}" x2="${width - 10}" y2="${chartHeight + 10}" stroke="#ccc" stroke-width="1"/>
                ${bars}
            </svg>
        `;
    }

    /**
     * Render a simple SVG area chart for pacing
     */
    _renderAreaChart(segments, width, height) {
        if (segments.length === 0) return '<p>No data</p>';

        const chartWidth = width - 40;
        const chartHeight = height - 30;
        const segmentWidth = chartWidth / segments.length;

        const dialoguePoints = segments.map((s, i) => {
            const x = 30 + i * segmentWidth + segmentWidth / 2;
            const y = 10 + chartHeight * (1 - s.dialogueRatio);
            return `${x},${y}`;
        }).join(' ');

        const actionPoints = segments.map((s, i) => {
            const x = 30 + i * segmentWidth + segmentWidth / 2;
            const y = 10 + chartHeight * (1 - s.actionRatio);
            return `${x},${y}`;
        }).join(' ');

        // Create area paths
        const dialogueArea = `M 30,${10 + chartHeight} L ${dialoguePoints} L ${30 + chartWidth},${10 + chartHeight} Z`;
        const actionArea = `M 30,${10 + chartHeight} L ${actionPoints} L ${30 + chartWidth},${10 + chartHeight} Z`;

        return `
            <svg width="${width}" height="${height}" class="area-chart">
                <defs>
                    <linearGradient id="dialogueGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#9C27B0" stop-opacity="0.7"/>
                        <stop offset="100%" stop-color="#9C27B0" stop-opacity="0.1"/>
                    </linearGradient>
                    <linearGradient id="actionGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="#FF5722" stop-opacity="0.7"/>
                        <stop offset="100%" stop-color="#FF5722" stop-opacity="0.1"/>
                    </linearGradient>
                </defs>
                <path d="${actionArea}" fill="url(#actionGrad)"/>
                <path d="${dialogueArea}" fill="url(#dialogueGrad)"/>
                <polyline points="${dialoguePoints}" fill="none" stroke="#9C27B0" stroke-width="2"/>
                <polyline points="${actionPoints}" fill="none" stroke="#FF5722" stroke-width="2"/>
                <line x1="30" y1="${10 + chartHeight}" x2="${30 + chartWidth}" y2="${10 + chartHeight}" stroke="#ccc"/>
                <text x="15" y="${10 + chartHeight / 2}" font-size="10" fill="#666" transform="rotate(-90, 15, ${10 + chartHeight / 2})">Ratio</text>
                <text x="${30 + chartWidth / 2}" y="${height - 5}" font-size="10" fill="#666" text-anchor="middle">Script Progress →</text>
            </svg>
            <div class="chart-legend">
                <div class="legend-item"><span class="legend-color" style="background:#9C27B0"></span>Dialogue</div>
                <div class="legend-item"><span class="legend-color" style="background:#FF5722"></span>Action</div>
            </div>
        `;
    }

    /**
     * Escape HTML
     */
    _escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    /**
     * Export statistics as JSON
     */
    toJSON() {
        if (!this.stats) this.analyze();
        return JSON.stringify(this.stats, null, 2);
    }

    /**
     * Export statistics as PNG (using canvas)
     */
    async toPNG() {
        // Create temporary container
        const container = document.createElement('div');
        container.style.cssText = 'position:absolute;left:-9999px;width:800px;background:#fff;padding:20px;';
        container.innerHTML = this.renderHTML();
        document.body.appendChild(container);

        // Use html2canvas if available, otherwise return null
        if (typeof html2canvas !== 'undefined') {
            try {
                const canvas = await html2canvas(container);
                document.body.removeChild(container);
                return canvas.toDataURL('image/png');
            } catch (e) {
                console.error('Failed to generate PNG:', e);
            }
        }

        document.body.removeChild(container);
        return null;
    }
}

window.CouriusStatistics = ScreenplayStatistics;
