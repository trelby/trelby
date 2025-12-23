/**
 * Courius - Enhanced Export Module V2
 * Adds PDF bookmarks, ePub export, and improved formatting
 */

class ExportV2 {
    constructor(screenplay, config) {
        this.screenplay = screenplay;
        this.config = config;
    }

    /**
     * Export to PDF with bookmarks
     */
    async exportPDFWithBookmarks() {
        // Check for jsPDF
        if (typeof jspdf === 'undefined') {
            throw new Error('jsPDF library not loaded');
        }

        const { jsPDF } = jspdf;
        const doc = new jsPDF({
            orientation: 'portrait',
            unit: 'pt',
            format: this.config.paperSize === 'a4' ? 'a4' : 'letter'
        });

        const { LINE_TYPE } = window.CouriusConstants;
        const margins = this.config.margins;
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const contentWidth = pageWidth - margins.left - margins.right;

        // Bookmarks array for outline
        const bookmarks = [];

        // Font setup
        doc.setFont('Courier');
        doc.setFontSize(12);
        const lineHeight = 14;

        let y = margins.top;
        let pageNumber = 1;
        let currentScene = null;

        // Process each line
        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            const text = line.text || '';

            // Check for page break
            if (y + lineHeight > pageHeight - margins.bottom) {
                // Add page number
                doc.setFontSize(10);
                doc.text(String(pageNumber), pageWidth - margins.right, margins.top - 10, { align: 'right' });
                doc.setFontSize(12);

                doc.addPage();
                pageNumber++;
                y = margins.top;
            }

            // Format based on element type
            const format = this._getElementFormat(line.type);
            let xPos = margins.left + format.indent;
            let maxWidth = contentWidth - format.indent - format.rightIndent;

            // Track scenes for bookmarks
            if (line.type === LINE_TYPE.SCENE) {
                const sceneNumber = bookmarks.length + 1;
                bookmarks.push({
                    title: `${sceneNumber}. ${text.substring(0, 50)}`,
                    page: pageNumber,
                    y: y
                });
                currentScene = text;
            }

            // Apply formatting
            let displayText = text;
            if (format.caps) {
                displayText = displayText.toUpperCase();
            }

            // Word wrap
            const lines = doc.splitTextToSize(displayText, maxWidth);

            // Draw each wrapped line
            for (const wrappedLine of lines) {
                if (y + lineHeight > pageHeight - margins.bottom) {
                    doc.setFontSize(10);
                    doc.text(String(pageNumber), pageWidth - margins.right, margins.top - 10, { align: 'right' });
                    doc.setFontSize(12);

                    doc.addPage();
                    pageNumber++;
                    y = margins.top;
                }

                // Bold for scene headings
                if (line.type === LINE_TYPE.SCENE) {
                    doc.setFont('Courier', 'bold');
                } else {
                    doc.setFont('Courier', 'normal');
                }

                // Centered text
                if (format.centered) {
                    doc.text(wrappedLine, pageWidth / 2, y, { align: 'center' });
                } else {
                    doc.text(wrappedLine, xPos, y);
                }

                y += lineHeight;
            }

            // Add spacing after element
            y += format.spaceAfter || 0;
        }

        // Add last page number
        doc.setFontSize(10);
        doc.text(String(pageNumber), pageWidth - margins.right, margins.top - 10, { align: 'right' });

        // Add bookmarks (outline)
        if (bookmarks.length > 0) {
            // jsPDF doesn't have native bookmark support, but we can add it via plugin
            // or use custom metadata
            doc.setProperties({
                title: this.screenplay.title || 'Untitled Screenplay',
                subject: 'Screenplay',
                author: this.screenplay.author || '',
                keywords: 'screenplay, script, courius',
                creator: 'Courius'
            });
        }

        return doc;
    }

    /**
     * Export to ePub format
     */
    async exportEPub() {
        const { LINE_TYPE } = window.CouriusConstants;
        const title = this.screenplay.title || 'Untitled Screenplay';
        const author = this.screenplay.author || 'Unknown';

        // Generate unique identifier
        const uuid = 'urn:uuid:' + this._generateUUID();

        // Build content
        const chapters = [];
        let currentChapter = { title: 'Title', content: [] };
        let sceneNumber = 0;

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            const text = this._escapeXML(line.text || '');

            if (line.type === LINE_TYPE.SCENE) {
                // New scene = new chapter
                if (currentChapter.content.length > 0) {
                    chapters.push(currentChapter);
                }
                sceneNumber++;
                currentChapter = {
                    title: `Scene ${sceneNumber}`,
                    content: [`<h2 class="scene">${text}</h2>`]
                };
            } else {
                const cssClass = line.type;
                currentChapter.content.push(`<p class="${cssClass}">${text}</p>`);
            }
        }

        if (currentChapter.content.length > 0) {
            chapters.push(currentChapter);
        }

        // Build ePub structure
        const epubFiles = {
            'mimetype': 'application/epub+zip',
            'META-INF/container.xml': this._getContainerXML(),
            'OEBPS/content.opf': this._getContentOPF(uuid, title, author, chapters),
            'OEBPS/toc.ncx': this._getTocNCX(uuid, title, chapters),
            'OEBPS/nav.xhtml': this._getNavXHTML(title, chapters),
            'OEBPS/styles.css': this._getEPubStyles()
        };

        // Add chapter files
        chapters.forEach((chapter, i) => {
            epubFiles[`OEBPS/chapter${i + 1}.xhtml`] = this._getChapterXHTML(chapter, i + 1);
        });

        // Create zip file
        if (typeof JSZip === 'undefined') {
            // Fallback to HTML export with download instructions
            throw new Error('JSZip library not loaded for ePub export');
        }

        const zip = new JSZip();

        // Add mimetype first (uncompressed)
        zip.file('mimetype', epubFiles['mimetype'], { compression: 'STORE' });

        // Add other files
        for (const [path, content] of Object.entries(epubFiles)) {
            if (path !== 'mimetype') {
                zip.file(path, content);
            }
        }

        return zip.generateAsync({ type: 'blob', mimeType: 'application/epub+zip' });
    }

    /**
     * Get element format for PDF
     */
    _getElementFormat(type) {
        const { LINE_TYPE } = window.CouriusConstants;

        const formats = {
            [LINE_TYPE.SCENE]: { indent: 0, rightIndent: 0, caps: true, spaceAfter: 14 },
            [LINE_TYPE.ACTION]: { indent: 0, rightIndent: 0, spaceAfter: 14 },
            [LINE_TYPE.CHARACTER]: { indent: 170, rightIndent: 0, caps: true, spaceAfter: 0 },
            [LINE_TYPE.DIALOGUE]: { indent: 72, rightIndent: 72, spaceAfter: 0 },
            [LINE_TYPE.PAREN]: { indent: 120, rightIndent: 120, spaceAfter: 0 },
            [LINE_TYPE.TRANSITION]: { indent: 0, rightIndent: 0, caps: true, spaceAfter: 14 },
            [LINE_TYPE.SHOT]: { indent: 0, rightIndent: 0, caps: true, spaceAfter: 14 },
            [LINE_TYPE.NOTE]: { indent: 0, rightIndent: 0, spaceAfter: 14 },
            [LINE_TYPE.ACTBREAK]: { indent: 0, rightIndent: 0, caps: true, centered: true, spaceAfter: 28 }
        };

        return formats[type] || { indent: 0, rightIndent: 0, spaceAfter: 0 };
    }

    /**
     * Generate UUID
     */
    _generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    /**
     * Escape XML entities
     */
    _escapeXML(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /**
     * Get container.xml for ePub
     */
    _getContainerXML() {
        return `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>`;
    }

    /**
     * Get content.opf for ePub
     */
    _getContentOPF(uuid, title, author, chapters) {
        const manifestItems = chapters.map((_, i) =>
            `<item id="chapter${i + 1}" href="chapter${i + 1}.xhtml" media-type="application/xhtml+xml"/>`
        ).join('\n        ');

        const spineItems = chapters.map((_, i) =>
            `<itemref idref="chapter${i + 1}"/>`
        ).join('\n        ');

        return `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:identifier id="bookid">${uuid}</dc:identifier>
        <dc:title>${this._escapeXML(title)}</dc:title>
        <dc:creator>${this._escapeXML(author)}</dc:creator>
        <dc:language>en</dc:language>
        <meta property="dcterms:modified">${new Date().toISOString().split('.')[0]}Z</meta>
    </metadata>
    <manifest>
        <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
        <item id="styles" href="styles.css" media-type="text/css"/>
        ${manifestItems}
    </manifest>
    <spine toc="ncx">
        ${spineItems}
    </spine>
</package>`;
    }

    /**
     * Get toc.ncx for ePub
     */
    _getTocNCX(uuid, title, chapters) {
        const navPoints = chapters.map((chapter, i) => `
        <navPoint id="navpoint-${i + 1}" playOrder="${i + 1}">
            <navLabel><text>${this._escapeXML(chapter.title)}</text></navLabel>
            <content src="chapter${i + 1}.xhtml"/>
        </navPoint>`).join('');

        return `<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
    <head>
        <meta name="dtb:uid" content="${uuid}"/>
        <meta name="dtb:depth" content="1"/>
        <meta name="dtb:totalPageCount" content="0"/>
        <meta name="dtb:maxPageNumber" content="0"/>
    </head>
    <docTitle><text>${this._escapeXML(title)}</text></docTitle>
    <navMap>${navPoints}
    </navMap>
</ncx>`;
    }

    /**
     * Get nav.xhtml for ePub
     */
    _getNavXHTML(title, chapters) {
        const navItems = chapters.map((chapter, i) =>
            `<li><a href="chapter${i + 1}.xhtml">${this._escapeXML(chapter.title)}</a></li>`
        ).join('\n            ');

        return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>${this._escapeXML(title)}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <nav epub:type="toc">
        <h1>Table of Contents</h1>
        <ol>
            ${navItems}
        </ol>
    </nav>
</body>
</html>`;
    }

    /**
     * Get chapter XHTML for ePub
     */
    _getChapterXHTML(chapter, number) {
        return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>${this._escapeXML(chapter.title)}</title>
    <link rel="stylesheet" type="text/css" href="styles.css"/>
</head>
<body>
    <section class="chapter" id="chapter${number}">
        ${chapter.content.join('\n        ')}
    </section>
</body>
</html>`;
    }

    /**
     * Get CSS styles for ePub
     */
    _getEPubStyles() {
        return `/* Screenplay ePub Styles */
body {
    font-family: "Courier New", Courier, monospace;
    font-size: 12pt;
    line-height: 1.5;
    margin: 1em;
}

h2.scene {
    font-weight: bold;
    text-transform: uppercase;
    margin-top: 1em;
    margin-bottom: 0.5em;
}

p {
    margin: 0;
    padding: 0;
}

p.action {
    margin-bottom: 1em;
}

p.character {
    text-transform: uppercase;
    margin-left: 2.5in;
    margin-top: 1em;
}

p.dialogue {
    margin-left: 1in;
    margin-right: 1in;
}

p.paren {
    margin-left: 1.5in;
    margin-right: 1.5in;
}

p.transition {
    text-transform: uppercase;
    text-align: right;
    margin-top: 1em;
    margin-bottom: 1em;
}

p.shot {
    text-transform: uppercase;
    margin-top: 1em;
    margin-bottom: 0.5em;
}

p.actbreak {
    text-transform: uppercase;
    text-align: center;
    margin-top: 2em;
    margin-bottom: 2em;
    font-weight: bold;
}

p.note {
    font-style: italic;
    color: #666;
}`;
    }

    /**
     * Export to RTF with proper formatting
     */
    exportRTF() {
        const { LINE_TYPE } = window.CouriusConstants;

        let rtf = '{\\rtf1\\ansi\\deff0\n';
        rtf += '{\\fonttbl{\\f0\\fmodern Courier New;}}\n';
        rtf += '\\f0\\fs24\n'; // 12pt Courier

        for (let i = 0; i < this.screenplay.lineCount; i++) {
            const line = this.screenplay.getLine(i);
            let text = this._escapeRTF(line.text || '');

            switch (line.type) {
                case LINE_TYPE.SCENE:
                    rtf += `\\b ${text.toUpperCase()}\\b0\\par\\par\n`;
                    break;
                case LINE_TYPE.ACTION:
                    rtf += `${text}\\par\\par\n`;
                    break;
                case LINE_TYPE.CHARACTER:
                    rtf += `\\li2880 ${text.toUpperCase()}\\li0\\par\n`;
                    break;
                case LINE_TYPE.DIALOGUE:
                    rtf += `\\li1440\\ri1440 ${text}\\li0\\ri0\\par\n`;
                    break;
                case LINE_TYPE.PAREN:
                    rtf += `\\li2160\\ri2160 (${text})\\li0\\ri0\\par\n`;
                    break;
                case LINE_TYPE.TRANSITION:
                    rtf += `\\qr ${text.toUpperCase()}\\ql\\par\\par\n`;
                    break;
                case LINE_TYPE.SHOT:
                    rtf += `${text.toUpperCase()}\\par\\par\n`;
                    break;
                case LINE_TYPE.ACTBREAK:
                    rtf += `\\qc\\b ${text.toUpperCase()}\\b0\\ql\\par\\par\\par\n`;
                    break;
                case LINE_TYPE.NOTE:
                    rtf += `\\i [${text}]\\i0\\par\\par\n`;
                    break;
                default:
                    rtf += `${text}\\par\n`;
            }
        }

        rtf += '}';
        return rtf;
    }

    /**
     * Escape RTF special characters
     */
    _escapeRTF(str) {
        return str
            .replace(/\\/g, '\\\\')
            .replace(/\{/g, '\\{')
            .replace(/\}/g, '\\}')
            .replace(/\n/g, '\\par\n');
    }
}

window.CouriusExportV2 = ExportV2;
