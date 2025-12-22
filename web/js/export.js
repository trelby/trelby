/**
 * Courius - Export Functionality
 * Exports screenplays to various formats
 */

class Exporter {
    constructor() {
        // PDF.js library will be loaded dynamically if needed
        this.pdfLibLoaded = false;
    }

    /**
     * Export screenplay to specified format
     */
    async export(screenplay, format, options = {}) {
        switch (format) {
            case 'pdf':
                return this.exportPDF(screenplay, options);
            case 'html':
                return this.exportHTML(screenplay, options);
            case 'txt':
            case 'text':
                return this.exportText(screenplay, options);
            case 'fdx':
                return this.exportFDX(screenplay, options);
            case 'fountain':
                return this.exportFountain(screenplay, options);
            case 'rtf':
                return this.exportRTF(screenplay, options);
            default:
                throw new Error(`Unknown export format: ${format}`);
        }
    }

    /**
     * Export to PDF
     */
    async exportPDF(screenplay, options = {}) {
        // Use jsPDF library (loaded from CDN)
        if (!window.jspdf) {
            await this._loadScript('https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js');
        }

        const { jsPDF } = window.jspdf;
        const { LINE_TYPE, ELEMENT_FORMAT, PAPER_SIZES } = window.CouriusConstants;

        const config = screenplay.config;
        const paperSize = PAPER_SIZES[config.paperSize] || PAPER_SIZES.letter;

        // Create PDF (dimensions in mm)
        const doc = new jsPDF({
            orientation: 'portrait',
            unit: 'pt',
            format: [paperSize.width, paperSize.height]
        });

        // Set font
        doc.setFont('courier', 'normal');
        doc.setFontSize(12);

        const lineHeight = 12; // 12pt font = 12pt line height
        const charsPerLine = 60;
        const marginLeft = config.margins.left;
        const marginTop = config.margins.top;
        const marginBottom = config.margins.bottom;
        const pageHeight = paperSize.height - marginTop - marginBottom;
        const linesPerPage = Math.floor(pageHeight / lineHeight);

        let currentPage = 1;
        let currentY = marginTop;
        let lineOnPage = 0;

        // Add title pages
        for (const titlePage of screenplay.titlePages) {
            // Render title page content
            const lines = titlePage.content.split('\n');
            for (const line of lines) {
                if (titlePage.centered) {
                    doc.text(line, paperSize.width / 2, currentY, { align: 'center' });
                } else {
                    doc.text(line, marginLeft, currentY);
                }
                currentY += lineHeight;
            }
            doc.addPage();
            currentPage++;
            currentY = marginTop;
            lineOnPage = 0;
        }

        // Add watermark if enabled
        const addWatermark = (pageNum) => {
            if (config.watermark?.enabled && config.watermark?.text) {
                doc.saveGraphicsState();
                doc.setTextColor(200, 200, 200);
                doc.setFontSize(config.watermark.fontSize || 48);
                doc.text(
                    config.watermark.text,
                    paperSize.width / 2,
                    paperSize.height / 2,
                    {
                        align: 'center',
                        angle: config.watermark.angle || -45
                    }
                );
                doc.restoreGraphicsState();
                doc.setFontSize(12);
                doc.setTextColor(0, 0, 0);
            }
        };

        // Add page number
        const addPageNumber = (pageNum) => {
            const header = screenplay.headers.otherPages.replace('%p', pageNum.toString());
            doc.text(header, paperSize.width - config.margins.right, marginTop - 24, { align: 'right' });
        };

        addWatermark(currentPage);
        if (screenplay.headers.showOnFirst || currentPage > 1) {
            addPageNumber(currentPage);
        }

        // Render screenplay content
        for (let i = 0; i < screenplay.lines.length; i++) {
            const line = screenplay.lines[i];
            const format = ELEMENT_FORMAT[line.type] || ELEMENT_FORMAT[LINE_TYPE.ACTION];

            // Calculate element-specific margins
            const elementIndent = marginLeft + (format.indent * 7.2); // ~7.2pt per character
            const maxWidth = format.width * 7.2;

            // Get display text
            let text = line.text;
            if (format.caps) {
                text = text.toUpperCase();
            }

            // Word wrap
            const wrappedLines = this._wordWrap(text, format.width);

            // Add spacing before
            if (i > 0 && line.isLastInParagraph()) {
                const spaceBefore = format.beforeSpacing || 0;
                for (let s = 0; s < spaceBefore; s++) {
                    lineOnPage++;
                    currentY += lineHeight;

                    if (lineOnPage >= linesPerPage) {
                        doc.addPage();
                        currentPage++;
                        currentY = marginTop;
                        lineOnPage = 0;
                        addWatermark(currentPage);
                        addPageNumber(currentPage);
                    }
                }
            }

            // Render each wrapped line
            for (const wrappedLine of wrappedLines) {
                // Check for page break
                if (lineOnPage >= linesPerPage) {
                    doc.addPage();
                    currentPage++;
                    currentY = marginTop;
                    lineOnPage = 0;
                    addWatermark(currentPage);
                    addPageNumber(currentPage);
                }

                // Set font style
                if (format.bold) {
                    doc.setFont('courier', 'bold');
                } else {
                    doc.setFont('courier', 'normal');
                }

                // Handle parenthetical
                let displayText = wrappedLine;
                if (line.type === LINE_TYPE.PAREN && wrappedLine === wrappedLines[0]) {
                    displayText = '(' + displayText;
                }
                if (line.type === LINE_TYPE.PAREN && wrappedLine === wrappedLines[wrappedLines.length - 1]) {
                    displayText = displayText + ')';
                }

                // Handle transition (right-aligned)
                if (line.type === LINE_TYPE.TRANSITION) {
                    doc.text(displayText, paperSize.width - config.margins.right, currentY, { align: 'right' });
                } else if (line.type === LINE_TYPE.ACTBREAK) {
                    doc.text(displayText, paperSize.width / 2, currentY, { align: 'center' });
                } else {
                    doc.text(displayText, elementIndent, currentY);
                }

                currentY += lineHeight;
                lineOnPage++;
            }
        }

        // Generate blob and download
        const pdfBlob = doc.output('blob');
        const filename = options.filename || 'screenplay.pdf';

        window.CouriusUtils.downloadFile(pdfBlob, filename, 'application/pdf');

        return true;
    }

    /**
     * Export to HTML
     */
    exportHTML(screenplay, options = {}) {
        const { LINE_TYPE, ELEMENT_FORMAT } = window.CouriusConstants;

        let html = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${this._escapeHtml(screenplay.metadata.filename || 'Screenplay')}</title>
    <style>
        body {
            font-family: 'Courier New', Courier, monospace;
            font-size: 12pt;
            line-height: 1;
            max-width: 8.5in;
            margin: 1in auto;
            padding: 0 1in;
            background: white;
            color: black;
        }
        .scene {
            text-transform: uppercase;
            font-weight: bold;
            margin-top: 24pt;
            margin-bottom: 12pt;
        }
        .action {
            margin-bottom: 12pt;
        }
        .character {
            text-transform: uppercase;
            margin-left: 2in;
            margin-top: 12pt;
        }
        .dialogue {
            margin-left: 1in;
            margin-right: 1.5in;
        }
        .paren {
            margin-left: 1.5in;
            margin-right: 2in;
        }
        .transition {
            text-transform: uppercase;
            text-align: right;
            margin-top: 12pt;
            margin-bottom: 12pt;
        }
        .shot {
            text-transform: uppercase;
            margin-top: 12pt;
            margin-bottom: 12pt;
        }
        .note {
            color: #666;
            font-style: italic;
            margin-left: 0.5in;
            padding: 8pt;
            background: #f5f5f5;
            border-left: 3px solid #999;
        }
        .actbreak {
            text-transform: uppercase;
            text-align: center;
            font-weight: bold;
            margin: 24pt 0;
            padding: 12pt 0;
            border-top: 2px solid black;
            border-bottom: 2px solid black;
        }
        .title-page {
            text-align: center;
            page-break-after: always;
            padding-top: 3in;
        }
        @media print {
            body { margin: 0; padding: 1in; }
            .page-break { page-break-before: always; }
        }
    </style>
</head>
<body>
`;

        // Add title pages
        for (const titlePage of screenplay.titlePages) {
            html += `<div class="title-page">${this._escapeHtml(titlePage.content).replace(/\n/g, '<br>')}</div>\n`;
        }

        // Add screenplay content
        for (const line of screenplay.lines) {
            const className = line.type;
            let text = this._escapeHtml(line.text);

            if (line.type === LINE_TYPE.PAREN) {
                text = `(${text})`;
            }

            html += `<p class="${className}">${text}</p>\n`;
        }

        html += `</body>
</html>`;

        const filename = options.filename || 'screenplay.html';
        window.CouriusUtils.downloadFile(html, filename, 'text/html');

        return html;
    }

    /**
     * Export to plain text
     */
    exportText(screenplay, options = {}) {
        const { LINE_TYPE, ELEMENT_FORMAT } = window.CouriusConstants;
        const lines = [];
        const pageWidth = 60;

        for (let i = 0; i < screenplay.lines.length; i++) {
            const line = screenplay.lines[i];
            const format = ELEMENT_FORMAT[line.type] || ELEMENT_FORMAT[LINE_TYPE.ACTION];

            let text = line.text;
            if (format.caps) {
                text = text.toUpperCase();
            }

            // Add spacing
            if (i > 0 && format.beforeSpacing > 0) {
                for (let s = 0; s < format.beforeSpacing; s++) {
                    lines.push('');
                }
            }

            // Apply indentation
            const indent = ' '.repeat(format.indent);
            const wrapped = this._wordWrap(text, format.width);

            for (const wrappedLine of wrapped) {
                let outputLine = indent + wrappedLine;

                // Handle parenthetical
                if (line.type === LINE_TYPE.PAREN) {
                    if (wrappedLine === wrapped[0]) {
                        outputLine = indent + '(' + wrappedLine;
                    }
                    if (wrappedLine === wrapped[wrapped.length - 1]) {
                        outputLine += ')';
                    }
                }

                // Handle transition (right-align)
                if (line.type === LINE_TYPE.TRANSITION) {
                    outputLine = wrappedLine.padStart(pageWidth);
                }

                // Handle act break (center)
                if (line.type === LINE_TYPE.ACTBREAK) {
                    const padding = Math.floor((pageWidth - wrappedLine.length) / 2);
                    outputLine = ' '.repeat(padding) + wrappedLine;
                }

                lines.push(outputLine);
            }
        }

        const text = lines.join('\n');
        const filename = options.filename || 'screenplay.txt';
        window.CouriusUtils.downloadFile(text, filename, 'text/plain');

        return text;
    }

    /**
     * Export to Final Draft XML
     */
    exportFDX(screenplay, options = {}) {
        const { LINE_TYPE } = window.CouriusConstants;

        // Map Trelby types to FDX types
        const typeMap = {
            [LINE_TYPE.SCENE]: 'Scene Heading',
            [LINE_TYPE.ACTION]: 'Action',
            [LINE_TYPE.CHARACTER]: 'Character',
            [LINE_TYPE.DIALOGUE]: 'Dialogue',
            [LINE_TYPE.PAREN]: 'Parenthetical',
            [LINE_TYPE.TRANSITION]: 'Transition',
            [LINE_TYPE.SHOT]: 'Shot',
            [LINE_TYPE.NOTE]: 'Action',
            [LINE_TYPE.ACTBREAK]: 'Action'
        };

        let xml = `<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="1">
  <Content>
`;

        for (const line of screenplay.lines) {
            const fdxType = typeMap[line.type] || 'Action';
            let text = this._escapeXml(line.text);

            if (line.type === LINE_TYPE.PAREN) {
                text = `(${text})`;
            }

            xml += `    <Paragraph Type="${fdxType}">
      <Text>${text}</Text>
    </Paragraph>
`;
        }

        xml += `  </Content>
</FinalDraft>`;

        const filename = options.filename || 'screenplay.fdx';
        window.CouriusUtils.downloadFile(xml, filename, 'application/xml');

        return xml;
    }

    /**
     * Export to Fountain format
     */
    exportFountain(screenplay, options = {}) {
        const { LINE_TYPE } = window.CouriusConstants;
        const lines = [];

        // Add title page if present
        if (screenplay.titlePages.length > 0) {
            lines.push('Title: ' + (screenplay.metadata.filename || 'Untitled'));
            lines.push('Author: ' + (screenplay.metadata.author || ''));
            lines.push('');
        }

        let lastType = null;

        for (const line of screenplay.lines) {
            let text = line.text;

            // Add blank line between different element types
            if (lastType !== null && lastType !== line.type) {
                if (line.type === LINE_TYPE.SCENE ||
                    line.type === LINE_TYPE.TRANSITION ||
                    lastType === LINE_TYPE.DIALOGUE ||
                    lastType === LINE_TYPE.PAREN) {
                    lines.push('');
                }
            }

            switch (line.type) {
                case LINE_TYPE.SCENE:
                    // Fountain auto-detects INT./EXT., force with . for others
                    if (!/^(INT|EXT|EST|INT\.?\/EXT|I\/E)[\.\s]/i.test(text)) {
                        text = '.' + text;
                    }
                    lines.push(text.toUpperCase());
                    break;

                case LINE_TYPE.CHARACTER:
                    lines.push(text.toUpperCase());
                    break;

                case LINE_TYPE.DIALOGUE:
                    lines.push(text);
                    break;

                case LINE_TYPE.PAREN:
                    lines.push(`(${text})`);
                    break;

                case LINE_TYPE.TRANSITION:
                    // Fountain auto-detects TO:, force with > for others
                    if (!/TO:$/i.test(text)) {
                        text = '> ' + text;
                    }
                    lines.push(text.toUpperCase());
                    break;

                case LINE_TYPE.ACTION:
                    lines.push(text);
                    break;

                case LINE_TYPE.SHOT:
                    // Force as scene heading
                    lines.push('.' + text.toUpperCase());
                    break;

                case LINE_TYPE.NOTE:
                    lines.push(`[[${text}]]`);
                    break;

                case LINE_TYPE.ACTBREAK:
                    lines.push(`> ${text.toUpperCase()} <`);
                    break;

                default:
                    lines.push(text);
            }

            lastType = line.type;
        }

        const fountain = lines.join('\n');
        const filename = options.filename || 'screenplay.fountain';
        window.CouriusUtils.downloadFile(fountain, filename, 'text/plain');

        return fountain;
    }

    /**
     * Export to RTF format
     */
    exportRTF(screenplay, options = {}) {
        const { LINE_TYPE, ELEMENT_FORMAT } = window.CouriusConstants;

        let rtf = `{\\rtf1\\ansi\\deff0
{\\fonttbl{\\f0\\fmodern Courier New;}}
{\\colortbl;\\red0\\green0\\blue0;\\red128\\green128\\blue128;}
\\paperw12240\\paperh15840
\\margl1440\\margr1440\\margt1440\\margb1440
\\f0\\fs24
`;

        for (const line of screenplay.lines) {
            const format = ELEMENT_FORMAT[line.type] || ELEMENT_FORMAT[LINE_TYPE.ACTION];
            let text = this._escapeRtf(line.text);

            if (format.caps) {
                text = text.toUpperCase();
            }

            // Calculate indent in twips (1 inch = 1440 twips)
            const indent = Math.round(format.indent * 120); // ~120 twips per character

            let rtfLine = `\\li${indent}`;

            if (format.bold) {
                rtfLine += '\\b';
            }

            if (line.type === LINE_TYPE.PAREN) {
                text = `(${text})`;
            }

            if (line.type === LINE_TYPE.TRANSITION) {
                rtfLine += '\\qr'; // Right align
            } else if (line.type === LINE_TYPE.ACTBREAK) {
                rtfLine += '\\qc'; // Center
            }

            rtfLine += ` ${text}`;

            if (format.bold) {
                rtfLine += '\\b0';
            }

            rtf += rtfLine + '\\par\n';

            // Add spacing after
            if (format.afterSpacing > 0) {
                for (let s = 0; s < format.afterSpacing; s++) {
                    rtf += '\\par\n';
                }
            }
        }

        rtf += '}';

        const filename = options.filename || 'screenplay.rtf';
        window.CouriusUtils.downloadFile(rtf, filename, 'application/rtf');

        return rtf;
    }

    /**
     * Word wrap text to specified width
     */
    _wordWrap(text, width) {
        return window.CouriusUtils.wordWrap(text, width);
    }

    /**
     * Escape HTML special characters
     */
    _escapeHtml(text) {
        return window.CouriusUtils.escapeHtml(text);
    }

    /**
     * Escape XML special characters
     */
    _escapeXml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&apos;');
    }

    /**
     * Escape RTF special characters
     */
    _escapeRtf(text) {
        return text
            .replace(/\\/g, '\\\\')
            .replace(/\{/g, '\\{')
            .replace(/\}/g, '\\}');
    }

    /**
     * Load external script dynamically
     */
    _loadScript(url) {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = url;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }
}

window.CouriusExporter = Exporter;
