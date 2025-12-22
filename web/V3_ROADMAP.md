# Courius V3 Roadmap

## Critical - Security Fixes
- [ ] Sanitize all innerHTML usage to prevent XSS attacks
- [ ] Add input validation for all file imports (FDX, Fountain, Trelby)
- [ ] Implement Content Security Policy (CSP) headers
- [ ] Sanitize user input in title pages and watermarks

## High Priority - Core Functionality
- [ ] Implement real spell checker with dictionary API (Hunspell.js or similar)
- [ ] Add offline dictionary support with IndexedDB caching
- [ ] Implement proper clipboard API for cross-browser copy/paste
- [ ] Add collaborative editing support (WebRTC or WebSocket)
- [ ] Implement cloud sync (Google Drive, Dropbox, OneDrive)
- [ ] Add user accounts with encrypted cloud storage

## High Priority - Accessibility
- [ ] Add full ARIA labels to all interactive elements
- [ ] Implement keyboard navigation for all dialogs
- [ ] Add screen reader support for editor content
- [ ] Implement focus management and focus trapping in modals
- [ ] Add high contrast theme option
- [ ] Support reduced motion preferences

## Medium Priority - Editor Enhancements
- [ ] Add scene navigator sidebar with drag-and-drop reordering
- [ ] Implement scene cards/index cards view
- [ ] Add beat board/outline view
- [ ] Implement split-screen for comparing drafts
- [ ] Add revision tracking with colored revision marks
- [ ] Implement commenting/notes on specific lines
- [ ] Add character arc tracking
- [ ] Implement smart quotes and em-dash auto-replacement

## Medium Priority - Visual Statistics (D3.js)
- [ ] Scene length visualization (bar chart)
- [ ] Character dialogue distribution (pie chart)
- [ ] Pacing graph (action vs dialogue over time)
- [ ] Location frequency heatmap
- [ ] Character presence timeline
- [ ] Word cloud for dialogue
- [ ] Export statistics as PNG/PDF

## Medium Priority - Export Improvements
- [ ] Add PDF bookmarks for scenes
- [ ] Implement PDF/A archival format
- [ ] Add ePub export for e-readers
- [ ] Implement batch export (multiple formats at once)
- [ ] Add customizable PDF templates
- [ ] Support dual-dialogue formatting in exports
- [ ] Add page lock/page break preview

## Medium Priority - Import Improvements
- [ ] Add Highland (.highland) import
- [ ] Add WriterSolo import
- [ ] Add Celtx (.celtx) import
- [ ] Implement smart format detection
- [ ] Add batch import for multiple files
- [ ] Improve Fountain import edge cases

## Low Priority - Plugin Architecture
- [ ] Design plugin API specification
- [ ] Implement plugin sandbox for security
- [ ] Add plugin marketplace UI
- [ ] Create sample plugins (word count goals, pomodoro timer)
- [ ] Add custom element type plugins
- [ ] Implement theme plugins

## Low Priority - Performance
- [ ] Implement virtual scrolling for large scripts (1000+ pages)
- [ ] Add Web Worker for background spell checking
- [ ] Optimize PDF generation with streaming
- [ ] Implement lazy loading for reports
- [ ] Add service worker for offline support
- [ ] Optimize localStorage usage with compression

## Low Priority - Quality of Life
- [ ] Add auto-update notifications
- [ ] Implement backup history with restore
- [ ] Add screenplay templates (feature, TV, short)
- [ ] Implement "distraction-free" writing mode
- [ ] Add word/page count goals with progress tracking
- [ ] Implement session statistics (words written, time spent)
- [ ] Add typewriter sounds (optional)
- [ ] Implement custom keyboard shortcuts

## Low Priority - Mobile Support
- [ ] Responsive design for tablets
- [ ] Touch-friendly toolbar
- [ ] Swipe gestures for element type switching
- [ ] Mobile-optimized dialogs
- [ ] PWA manifest for home screen installation

## Infrastructure
- [ ] Add unit tests with Jest
- [ ] Add E2E tests with Playwright
- [ ] Set up CI/CD pipeline
- [ ] Add error tracking (Sentry or similar)
- [ ] Create user documentation site
- [ ] Add in-app tutorial/onboarding

## Future Considerations (V4+)
- [ ] AI-powered writing suggestions
- [ ] Character voice consistency checker
- [ ] Automatic scene breakdown for production
- [ ] Integration with casting databases
- [ ] Budget estimation based on script elements
- [ ] Storyboard integration
