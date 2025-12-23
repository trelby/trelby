/**
 * Courius - Scene Navigator Sidebar
 * Provides scene overview, drag-and-drop reordering, and quick navigation
 */

class SceneNavigator {
    constructor(editor) {
        this.editor = editor;
        this.container = null;
        this.scenes = [];
        this.selectedScene = null;
        this.draggedScene = null;
        this.isOpen = false;

        this._init();
    }

    /**
     * Initialize the navigator
     */
    _init() {
        this._createContainer();
        this._bindEvents();
    }

    /**
     * Create the navigator container
     */
    _createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'scene-navigator';
        this.container.className = 'scene-navigator';
        this.container.setAttribute('role', 'complementary');
        this.container.setAttribute('aria-label', 'Scene Navigator');

        this.container.innerHTML = `
            <div class="scene-nav-header">
                <h3>Scenes</h3>
                <div class="scene-nav-actions">
                    <button class="nav-btn" id="nav-collapse-all" title="Collapse all" aria-label="Collapse all scenes">
                        <span>−</span>
                    </button>
                    <button class="nav-btn" id="nav-expand-all" title="Expand all" aria-label="Expand all scenes">
                        <span>+</span>
                    </button>
                    <button class="nav-btn" id="nav-close" title="Close navigator" aria-label="Close scene navigator">
                        <span>×</span>
                    </button>
                </div>
            </div>
            <div class="scene-nav-search">
                <input type="text" id="scene-search" placeholder="Search scenes..." aria-label="Search scenes">
            </div>
            <div class="scene-nav-stats">
                <span id="scene-count">0 scenes</span>
                <span id="page-count">0 pages</span>
            </div>
            <div class="scene-nav-list" id="scene-list" role="listbox" aria-label="Scene list">
            </div>
        `;

        // Insert before editor container
        const editorContainer = document.getElementById('editor-container');
        editorContainer.parentNode.insertBefore(this.container, editorContainer);
    }

    /**
     * Bind event listeners
     */
    _bindEvents() {
        // Close button
        this.container.querySelector('#nav-close').addEventListener('click', () => {
            this.toggle();
        });

        // Collapse/Expand all
        this.container.querySelector('#nav-collapse-all').addEventListener('click', () => {
            this.collapseAll();
        });

        this.container.querySelector('#nav-expand-all').addEventListener('click', () => {
            this.expandAll();
        });

        // Search
        const searchInput = this.container.querySelector('#scene-search');
        searchInput.addEventListener('input', (e) => {
            this.filter(e.target.value);
        });

        // Scene list events
        const sceneList = this.container.querySelector('#scene-list');

        sceneList.addEventListener('click', (e) => {
            const sceneItem = e.target.closest('.scene-item');
            if (sceneItem) {
                const lineIndex = parseInt(sceneItem.dataset.line);
                this.navigateTo(lineIndex);
            }
        });

        sceneList.addEventListener('keydown', (e) => {
            this._handleKeyDown(e);
        });

        // Drag and drop
        sceneList.addEventListener('dragstart', (e) => {
            this._handleDragStart(e);
        });

        sceneList.addEventListener('dragover', (e) => {
            this._handleDragOver(e);
        });

        sceneList.addEventListener('drop', (e) => {
            this._handleDrop(e);
        });

        sceneList.addEventListener('dragend', (e) => {
            this._handleDragEnd(e);
        });
    }

    /**
     * Handle keyboard navigation
     */
    _handleKeyDown(e) {
        const items = [...this.container.querySelectorAll('.scene-item:not(.hidden)')];
        const currentIndex = items.findIndex(item => item === document.activeElement);

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (currentIndex < items.length - 1) {
                    items[currentIndex + 1].focus();
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (currentIndex > 0) {
                    items[currentIndex - 1].focus();
                }
                break;

            case 'Enter':
            case ' ':
                e.preventDefault();
                if (document.activeElement.classList.contains('scene-item')) {
                    const lineIndex = parseInt(document.activeElement.dataset.line);
                    this.navigateTo(lineIndex);
                }
                break;

            case 'Home':
                e.preventDefault();
                items[0]?.focus();
                break;

            case 'End':
                e.preventDefault();
                items[items.length - 1]?.focus();
                break;
        }
    }

    /**
     * Handle drag start
     */
    _handleDragStart(e) {
        const sceneItem = e.target.closest('.scene-item');
        if (!sceneItem) return;

        this.draggedScene = sceneItem;
        sceneItem.classList.add('dragging');

        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', sceneItem.dataset.sceneIndex);
    }

    /**
     * Handle drag over
     */
    _handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        const sceneItem = e.target.closest('.scene-item');
        if (!sceneItem || sceneItem === this.draggedScene) return;

        const rect = sceneItem.getBoundingClientRect();
        const midY = rect.top + rect.height / 2;

        // Remove all drop indicators
        this.container.querySelectorAll('.drop-above, .drop-below').forEach(el => {
            el.classList.remove('drop-above', 'drop-below');
        });

        if (e.clientY < midY) {
            sceneItem.classList.add('drop-above');
        } else {
            sceneItem.classList.add('drop-below');
        }
    }

    /**
     * Handle drop
     */
    _handleDrop(e) {
        e.preventDefault();

        const sceneItem = e.target.closest('.scene-item');
        if (!sceneItem || !this.draggedScene || sceneItem === this.draggedScene) return;

        const fromIndex = parseInt(this.draggedScene.dataset.sceneIndex);
        const toIndex = parseInt(sceneItem.dataset.sceneIndex);
        const dropAbove = sceneItem.classList.contains('drop-above');

        // Calculate actual insertion index
        let insertIndex = dropAbove ? toIndex : toIndex + 1;
        if (fromIndex < insertIndex) insertIndex--;

        // Reorder scenes in screenplay
        this._reorderScene(fromIndex, insertIndex);

        // Clean up
        this.container.querySelectorAll('.drop-above, .drop-below').forEach(el => {
            el.classList.remove('drop-above', 'drop-below');
        });
    }

    /**
     * Handle drag end
     */
    _handleDragEnd(e) {
        if (this.draggedScene) {
            this.draggedScene.classList.remove('dragging');
            this.draggedScene = null;
        }

        this.container.querySelectorAll('.drop-above, .drop-below').forEach(el => {
            el.classList.remove('drop-above', 'drop-below');
        });
    }

    /**
     * Reorder scene in the screenplay
     */
    _reorderScene(fromIndex, toIndex) {
        if (fromIndex === toIndex) return;

        const screenplay = this.editor.getScreenplay();
        const scenes = this._extractScenes(screenplay);

        if (fromIndex < 0 || fromIndex >= scenes.length) return;
        if (toIndex < 0 || toIndex > scenes.length) return;

        const fromScene = scenes[fromIndex];
        const toScene = scenes[toIndex] || { startLine: screenplay.lineCount };

        // Calculate line ranges
        const fromStart = fromScene.startLine;
        const fromEnd = fromIndex < scenes.length - 1
            ? scenes[fromIndex + 1].startLine
            : screenplay.lineCount;

        // Extract lines to move
        const linesToMove = [];
        for (let i = fromStart; i < fromEnd; i++) {
            linesToMove.push(screenplay.getLine(i).clone());
        }

        // Remove original lines (from end to start to maintain indices)
        for (let i = fromEnd - 1; i >= fromStart; i--) {
            screenplay.deleteLine(i);
        }

        // Adjust insert position if needed
        let insertAt = toScene.startLine;
        if (fromIndex < toIndex) {
            insertAt -= linesToMove.length;
        }

        // Insert lines at new position
        for (let i = 0; i < linesToMove.length; i++) {
            screenplay.insertLine(insertAt + i, linesToMove[i]);
        }

        // Refresh editor and navigator
        this.editor._render();
        this.refresh();

        // Announce change
        if (window.couriusApp?.accessibility) {
            window.couriusApp.accessibility.announce(`Scene moved to position ${toIndex + 1}`);
        }
    }

    /**
     * Toggle navigator visibility
     */
    toggle() {
        this.isOpen = !this.isOpen;
        this.container.classList.toggle('open', this.isOpen);
        document.getElementById('editor-container').classList.toggle('with-navigator', this.isOpen);

        if (this.isOpen) {
            this.refresh();
        }

        // Save state
        localStorage.setItem('courius-navigator-open', String(this.isOpen));
    }

    /**
     * Open navigator
     */
    open() {
        if (!this.isOpen) {
            this.toggle();
        }
    }

    /**
     * Close navigator
     */
    close() {
        if (this.isOpen) {
            this.toggle();
        }
    }

    /**
     * Refresh the scene list
     */
    refresh() {
        const screenplay = this.editor.getScreenplay();
        this.scenes = this._extractScenes(screenplay);

        const sceneList = this.container.querySelector('#scene-list');
        sceneList.innerHTML = '';

        this.scenes.forEach((scene, index) => {
            const item = this._createSceneItem(scene, index);
            sceneList.appendChild(item);
        });

        // Update stats
        this.container.querySelector('#scene-count').textContent =
            `${this.scenes.length} scene${this.scenes.length !== 1 ? 's' : ''}`;
        this.container.querySelector('#page-count').textContent =
            `${screenplay.getPageCount()} page${screenplay.getPageCount() !== 1 ? 's' : ''}`;
    }

    /**
     * Extract scenes from screenplay
     */
    _extractScenes(screenplay) {
        const scenes = [];
        const { LINE_TYPE } = window.CouriusConstants;

        for (let i = 0; i < screenplay.lineCount; i++) {
            const line = screenplay.getLine(i);
            if (line.type === LINE_TYPE.SCENE) {
                const text = line.text.trim();
                const page = screenplay.getPageForLine(i);

                // Parse scene heading
                const parsed = this._parseSceneHeading(text);

                // Count lines until next scene or end
                let lineCount = 1;
                for (let j = i + 1; j < screenplay.lineCount; j++) {
                    if (screenplay.getLine(j).type === LINE_TYPE.SCENE) break;
                    lineCount++;
                }

                // Estimate duration (roughly 1 min per page, adjusted by line count)
                const duration = Math.max(1, Math.round(lineCount / 50));

                scenes.push({
                    startLine: i,
                    text,
                    page,
                    lineCount,
                    duration,
                    ...parsed
                });
            }
        }

        return scenes;
    }

    /**
     * Parse scene heading into components
     */
    _parseSceneHeading(text) {
        const normalized = text.toUpperCase().trim();

        // Match INT./EXT./INT/EXT + location + time of day
        const match = normalized.match(/^(INT\.?|EXT\.?|INT\.?\/EXT\.?|I\/E\.?)\s*[-.]?\s*(.+?)\s*[-–—]\s*(.+)$/);

        if (match) {
            return {
                intExt: match[1].replace('.', ''),
                location: match[2].trim(),
                timeOfDay: match[3].trim()
            };
        }

        // Try without time of day
        const match2 = normalized.match(/^(INT\.?|EXT\.?|INT\.?\/EXT\.?|I\/E\.?)\s*[-.]?\s*(.+)$/);

        if (match2) {
            return {
                intExt: match2[1].replace('.', ''),
                location: match2[2].trim(),
                timeOfDay: ''
            };
        }

        return {
            intExt: '',
            location: text,
            timeOfDay: ''
        };
    }

    /**
     * Create scene item element
     */
    _createSceneItem(scene, index) {
        const item = document.createElement('div');
        item.className = 'scene-item';
        item.dataset.line = scene.startLine;
        item.dataset.sceneIndex = index;
        item.setAttribute('role', 'option');
        item.setAttribute('tabindex', '0');
        item.setAttribute('draggable', 'true');

        // Color code by INT/EXT
        const colorClass = scene.intExt === 'INT' ? 'interior' :
                          scene.intExt === 'EXT' ? 'exterior' : 'mixed';

        item.innerHTML = `
            <div class="scene-number">${index + 1}</div>
            <div class="scene-content">
                <div class="scene-heading ${colorClass}">
                    <span class="scene-int-ext">${window.CouriusSecurity?.escapeHTML(scene.intExt) || scene.intExt}</span>
                    <span class="scene-location">${window.CouriusSecurity?.escapeHTML(scene.location) || scene.location}</span>
                </div>
                <div class="scene-meta">
                    <span class="scene-time">${window.CouriusSecurity?.escapeHTML(scene.timeOfDay) || scene.timeOfDay}</span>
                    <span class="scene-page">p.${scene.page}</span>
                    <span class="scene-duration">~${scene.duration}m</span>
                </div>
            </div>
            <div class="scene-drag-handle" aria-hidden="true">⋮⋮</div>
        `;

        return item;
    }

    /**
     * Navigate to a scene
     */
    navigateTo(lineIndex) {
        this.editor.goToLine(lineIndex);

        // Highlight in editor
        const lineElement = document.querySelector(`[data-line="${lineIndex}"]`);
        if (lineElement) {
            lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            lineElement.classList.add('highlight');
            setTimeout(() => lineElement.classList.remove('highlight'), 1000);
        }

        // Update selection in navigator
        this.container.querySelectorAll('.scene-item').forEach(item => {
            item.classList.remove('selected');
            item.setAttribute('aria-selected', 'false');
        });

        const sceneItem = this.container.querySelector(`[data-line="${lineIndex}"]`);
        if (sceneItem) {
            sceneItem.classList.add('selected');
            sceneItem.setAttribute('aria-selected', 'true');
        }
    }

    /**
     * Filter scenes by search query
     */
    filter(query) {
        const normalized = query.toLowerCase().trim();

        this.container.querySelectorAll('.scene-item').forEach(item => {
            const text = item.textContent.toLowerCase();
            const matches = !normalized || text.includes(normalized);
            item.classList.toggle('hidden', !matches);
        });
    }

    /**
     * Collapse all scene details
     */
    collapseAll() {
        this.container.querySelectorAll('.scene-item').forEach(item => {
            item.classList.add('collapsed');
        });
    }

    /**
     * Expand all scene details
     */
    expandAll() {
        this.container.querySelectorAll('.scene-item').forEach(item => {
            item.classList.remove('collapsed');
        });
    }

    /**
     * Get current scene at cursor position
     */
    getCurrentScene() {
        const lineIndex = this.editor._getCurrentLineIndex();

        for (let i = this.scenes.length - 1; i >= 0; i--) {
            if (this.scenes[i].startLine <= lineIndex) {
                return this.scenes[i];
            }
        }

        return null;
    }

    /**
     * Highlight current scene in navigator
     */
    highlightCurrentScene() {
        const currentScene = this.getCurrentScene();
        if (!currentScene) return;

        this.container.querySelectorAll('.scene-item').forEach(item => {
            const isCurrentScene = parseInt(item.dataset.line) === currentScene.startLine;
            item.classList.toggle('current', isCurrentScene);
        });
    }
}

window.CouriusSceneNavigator = SceneNavigator;
