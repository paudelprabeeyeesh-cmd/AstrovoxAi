# Frontend Platform Features - Technical Documentation

## Group 1: Accessible Component Primitives and Focus Management
**Files:** `frontend/js/platform/accessibility.js`

### Summary
Implements a comprehensive accessibility toolkit including focus trapping, live region announcements, skip-to-main navigation, and a FocusManager class for managing focus state across modal dialogs and complex widgets.

### Accessibility Implications
- Full keyboard navigation support with Tab/Shift+Tab trapping
- ARIA live region for screen reader announcements
- Skip link for bypassing navigation blocks
- `inert` attribute management for hiding content from assistive tech
- Focus restoration after modal/dialog close
- Supports `role="button"`, `role="link"`, `role="tab"`, `role="menuitem"` selectors

### Performance Characteristics
- Zero dependencies, ~5KB minified
- Focusable element queries cached per container
- Event listeners cleaned up on trap release
- `requestAnimationFrame` for announcement timing

### Browser/Platform Support
- Chrome/Edge 88+
- Firefox 85+
- Safari 14+
- Supports `inert` attribute where available

### Integration Points
- Used by `Modal`, `CommandPalette`, `GlobalSearch` for focus trapping
- Called by `Toast` for ARIA live announcements
- Integrated with `Motion` for animation timing

---

## Group 2: Animation/Transition System with Reduced-Motion Support
**Files:** `frontend/js/platform/motion.js`, `frontend/css/style.css`

### Summary
Provides a declarative animation API using the Web Animations API with automatic `prefers-reduced-motion` respect. Includes fade, slide, scale, pulse, shake, and stagger utilities.

### Accessibility Implications
- All animations automatically disabled when `prefers-reduced-motion: reduce` is set
- No animation lock on critical UI state changes
- Fallback to instant style application for reduced-motion users

### Performance Characteristics
- Uses native Web Animations API (GPU-accelerated)
- Stagger animations batch promises via `Promise.all`
- No layout thrashing - transforms and opacity only
- ~3KB minified

### Browser/Platform Support
- Chrome/Edge 84+
- Firefox 75+
- Safari 13.1+
- Graceful degradation to instant style changes

### Integration Points
- Used by `Modal` (scale in/out)
- Used by `Toast` (slide in/out)
- Used by `Presence` (cursor transitions)
- CSS `prefers-reduced-motion` media query as fallback

---

## Group 3: Markdown/Mermaid/KaTeX/Monaco Integrations
**Files:** `frontend/js/integrations/markdown.js`, `mermaid.js`, `katex.js`, `monaco.js`

### Summary
Lazy-loaded integration adapters for rich content rendering:
- **Markdown:** Lightweight parser supporting headings, lists, code blocks, bold/italic, links
- **Mermaid:** Diagram rendering via CDN with error suppression
- **KaTeX:** Math typesetting with display/inline modes
- **Monaco:** Full code editor with custom AstrovoxDark theme

### Accessibility Implications
- Markdown generates semantic HTML (`<h1>`-`<h3>`, `<pre>`, `<code>`)
- Mermaid errors rendered as readable `<pre>` fallback
- KaTeX respects `throwOnError: false` for graceful degradation
- Monaco editor includes ARIA labels and keyboard navigation

### Performance Characteristics
- All integrations lazy-loaded via CDN on first use
- Script deduplication via DOM query checks
- Monaco ~200KB, Mermaid ~150KB, KaTeX ~30KB - loaded only when needed
- Markdown parser is synchronous, ~2KB

### Browser/Platform Support
- Modern ES2020+ browsers
- Monaco requires WebAssembly support (Chrome 57+, Firefox 52+, Safari 11+)
- Mermaid 10+ requires ES2020
- KaTeX 0.16+ supports all modern browsers

### Integration Points
- `Markdown` used by `ChatApp` for message rendering
- `Mermaid` used by `CodeExecutor` for diagram tabs
- `KaTeX` used by chat for math expressions
- `Monaco` used by `CodeExecutor` for code editing

---

## Group 4: Offline Queue and Sync Primitives
**Files:** `frontend/js/platform/offline.js`, `sync.js`

### Summary
Implements an offline-first request queue with exponential backoff retry, deduplication, background sync API registration, and a merge/push/pull sync primitive for conflict resolution.

### Accessibility Implications
- Queue status announced via `A11y.announce()` when sync completes
- Failed operations logged with accessible error messages
- No disruptive UI during background sync

### Performance Characteristics
- Queue persisted to `localStorage` for durability
- Deduplication via request signature hashing
- Background Sync API reduces polling overhead
- Exponential backoff: 1s, 2s, 4s, 8s, 16s

### Browser/Platform Support
- Background Sync API: Chrome 49+, Edge 79+, not supported in Firefox/Safari
- Falls back to online event listener + polling
- `localStorage` required for queue persistence

### Integration Points
- `OfflineQueue` used by `ChatAPI` for message sending
- `SyncPrimitives` used by `DashboardApp` for state synchronization
- Integrates with `PWA` service worker for background sync

---

## Group 5: PWA Install, Update, and Cache Strategies
**Files:** `frontend/manifest.json`, `sw.js`, `frontend/js/platform/pwa.js`

### Summary
Complete PWA implementation with:
- Web App Manifest for installability (shortcuts, icons, categories)
- Service Worker with stale-while-revalidate caching
- Install prompt capture and user-choice handling
- Update detection via controllerchange event
- Cache versioning for atomic updates

### Accessibility Implications
- Manifest includes `name` and `short_name` for screen readers
- Install button includes `aria-label`
- Update notifications use `Toast` with accessible alerts

### Performance Characteristics
- Precached assets: HTML, CSS, JS (~50KB total)
- Runtime cache for API responses and images
- Stale-while-revalidate for instant loads + background updates
- Cache versioning enables atomic cache swaps

### Browser/Platform Support
- Chrome/Edge 88+ (full PWA support)
- Safari 16.4+ (add to home screen, limited)
- Firefox 125+ (PWA support)
- `beforeinstallprompt` event supported in Chromium browsers

### Integration Points
- `PWA` module used by `App` for install prompt
- Service Worker registered in `index.html`
- Manifest linked in `<head>`
- `OfflineQueue` integrates with SW background sync

---

## Group 6: Command Palette, Modals, Toasts, Tooltips
**Files:** `frontend/js/ui/command-palette.js`, `modal.js`, `toast.js`, `tooltip.js`

### Summary
Accessible UI primitives:
- **CommandPalette:** Cmd+K triggered command search with fuzzy filtering, keyboard navigation, categories
- **Modal:** Focus-trapped dialog with scale animation, ESC close, overlay click dismiss
- **Toast:** Stackable notifications with action buttons, auto-dismiss, type variants (success/error/warning/info)
- **Tooltip:** Hover/focus tooltips with smart positioning and collision detection

### Accessibility Implications
- CommandPalette: `role="dialog"`, `aria-modal`, `role="listbox"`, `role="option"`
- Modal: Focus trap, `aria-labelledby`, ESC dismiss, focus restoration
- Toast: `role="alert"`, `role="region"`, `aria-label="Notifications"`
- Tooltip: `role="tooltip"`, `aria-describedby` on trigger element

### Performance Characteristics
- CommandPalette: DOM recycling, 60fps keyboard navigation
- Modal: Single DOM node, CSS transform animations
- Toast: Max 5 visible toasts, auto-removal via Promise chain
- Tooltip: Single tooltip element reused, position calculated on show

### Browser/Platform Support
- ES2020+ required
- `animate()` API for Modal/Toast transitions
- `details/summary` not used - custom implementations for consistency

### Integration Points
- `CommandPalette` used by `App` for global commands
- `Modal` used by `WidgetFramework` for settings
- `Toast` used by `ChatApp` and `DashboardApp` for notifications
- `Tooltip` used by command palette items and nav links

---

## Group 7: Theme Engine and Design Token System
**Files:** `frontend/js/platform/theme.js`, `design-tokens.js`

### Summary
Runtime theme switching with CSS custom property injection, system preference detection, and a design token registry for spacing, typography, and shadows.

### Accessibility Implications
- Respects `prefers-color-scheme` media query for automatic theme selection
- Theme preference persisted in `localStorage`
- All themes meet WCAG 2.1 AA contrast ratios
- Theme changes announced via `A11y.announce()`

### Performance Characteristics
- CSS custom properties updated via `setProperty` - no reflow
- Theme change triggers single style recalculation
- Design tokens computed once on init
- ~3KB minified

### Browser/Platform Support
- CSS custom properties: Chrome 49+, Firefox 31+, Safari 9.1+
- `prefers-color-scheme`: Chrome 76+, Firefox 67+, Safari 12.1+
- `localStorage` for persistence

### Integration Points
- `ThemeEngine.init()` called by `platform/index.js` on DOMContentLoaded
- Used by all UI components for color values
- `DesignTokens` provides spacing/typography constants

---

## Group 8: Resizable Split-Pane and Workspace Layouts
**Files:** `frontend/js/ui/split-pane.js`

### Summary
Flexbox-based resizable split pane with mouse, touch, and keyboard (arrow keys) support. Includes ARIA separator role with `aria-valuenow` updates.

### Accessibility Implications
- Gutter has `role="separator"` with `aria-orientation`
- `aria-valuenow` updated in real-time during drag
- Keyboard support: Arrow keys (1% step), Shift+Arrow (5% step)
- Min/max size constraints enforced

### Performance Characteristics
- CSS flexbox for layout (no JS layout calculations)
- `requestAnimationFrame` not needed - direct style updates
- Touch and mouse events unified
- ~4KB minified

### Browser/Platform Support
- Flexbox: Chrome 29+, Firefox 28+, Safari 9+
- Touch events: Chrome 48+, Safari 9+
- Mouse events: All browsers

### Integration Points
- Used by `DashboardApp` for sidebar/content split
- Can be used by `ChatApp` for editor/preview split

---

## Group 9: Global Search with Keyboard Navigation
**Files:** `frontend/js/ui/global-search.js`

### Summary
Cmd+K triggered global search overlay with multi-source aggregation, keyboard navigation (Arrow keys + Enter), and source-aware result rendering.

### Accessibility Implications
- `role="dialog"`, `aria-modal="true"`, `aria-label="Global search"`
- Results use `role="listbox"` and `role="option"`
- Keyboard navigation: Arrow Up/Down, Enter to select, Escape to close
- Footer shows keyboard shortcuts

### Performance Characteristics
- Async search across registered sources
- Results capped per source to prevent DOM bloat
- Debounced input handling
- ~7KB minified

### Browser/Platform Support
- ES2020+ required
- `async/await` for parallel source queries

### Integration Points
- Sources registered via `GlobalSearch.registerSource()`
- Used by `App` for global navigation
- Can integrate with `ChatAPI`, `DashboardAPI` for content search

---

## Group 10: Code Execution UI with Language Tabs and Output Panels
**Files:** `frontend/js/ui/code-executor.js`

### Summary
Tabbed code editor with JavaScript execution sandbox, stdout/stderr capture, execution time tracking, and language badge display.

### Accessibility Implications
- Tabs use `role="tablist"` and `role="tab"` with `aria-selected`
- Output panel announced via `role="alert"`
- Run/Clear buttons have `aria-label`

### Performance Characteristics
- `AsyncFunction` constructor for async code execution
- Console methods temporarily overridden for capture
- Execution timeout via AbortController (not implemented in basic version)
- ~7KB minified

### Browser/Platform Support
- ES2020+ for async/await and `AsyncFunction`
- Console override works in all modern browsers

### Integration Points
- Used by `ChatApp` for code generation responses
- Can integrate with `Monaco` for syntax highlighting
- Output rendered in dedicated panel with syntax highlighting classes

---

## Group 11: Multi-modal Input: Voice, Camera, Screen Share
**Files:** `frontend/js/ui/multi-modal-input.js`

### Summary
Unified input component supporting text, voice recording (with MediaRecorder API), camera capture, and screen sharing via `getDisplayMedia`.

### Accessibility Implications
- Toolbar buttons have `aria-label` for each mode
- Active mode indicated visually and semantically
- Status messages announced for listening/capturing/processing states
- Error states use `aria-live` regions

### Performance Characteristics
- Media streams stopped when switching modes
- Audio chunks accumulated in memory during recording
- Blob-based audio upload via FormData
- ~9KB minified

### Browser/Platform Support
- `getUserMedia`: Chrome 53+, Firefox 36+, Safari 11+
- `getDisplayMedia`: Chrome 72+, Firefox 66+, Safari 15+
- `MediaRecorder`: Chrome 47+, Firefox 25+, Safari 14.6+
- Screen share requires HTTPS in production

### Integration Points
- Used by `ChatApp` for multi-modal message sending
- Voice transcription endpoint: `/api/multimodal/transcribe`
- Camera/screen capture preview rendered in `.multimodal-preview`

---

## Group 12: Collaboration Cursors and Presence Indicators
**Files:** `frontend/js/platform/presence.js`

### Summary
Real-time presence system with WebSocket connection, heartbeat mechanism, cursor broadcasting, and user list management. Cursor elements rendered with user-specific colors and name labels.

### Accessibility Implications
- Cursor elements have `aria-hidden="true"` (decorative)
- User updates announced via `A11y.announce()` for new joiners
- Cursor labels use high-contrast user colors

### Performance Characteristics
- Heartbeat every 5 seconds
- Cursor elements hidden after 10 seconds of inactivity
- WebSocket reconnection with exponential backoff (3s base)
- Cursor updates throttled by WebSocket message rate

### Browser/Platform Support
- WebSocket: All modern browsers
- `crypto.randomUUID()`: Chrome 92+, Firefox 95+, Safari 15.4+
- Falls back to timestamp-based IDs if UUID unavailable

### Integration Points
- `Presence.init()` called by `ChatApp` for collaborative editing
- Cursor events emitted via `Presence.on('cursor_move')`
- Integrates with WebSocket infrastructure for real-time updates

---

## Group 13: Dashboard Shell and Widget Framework
**Files:** `frontend/js/platform/widget-framework.js`, `frontend/css/components/platform.css`

### Summary
CSS Grid-based dashboard shell with a widget registration, mounting, and lifecycle management system. Widgets support refresh intervals, on-mount/on-unmount hooks, and resize callbacks.

### Accessibility Implications
- Widget actions have `aria-label` (Refresh, Settings)
- Settings modal integrates with `A11y.trapFocus()`
- Widget errors announced via `role="alert"` in error panel

### Performance Characteristics
- CSS Grid for layout (12-column responsive grid)
- Widget refresh intervals managed via `setInterval`/`clearInterval`
- DOM updates isolated to widget body
- ~4KB minified

### Browser/Platform Support
- CSS Grid: Chrome 57+, Firefox 52+, Safari 10.1+
- `crypto.randomUUID()` for widget IDs

### Integration Points
- `WidgetFramework.register()` used by dashboard widgets
- `Modal` used for widget settings
- `ThemeEngine` provides theme tokens for widget styling

---

## Group 14: Responsive Breakpoints and Mobile Adaptations
**Files:** `frontend/css/components/platform.css`

### Summary
Comprehensive responsive design system with breakpoints at 480px, 768px, and 1200px. Includes mobile-first adaptations for navigation, grids, modals, and command palettes.

### Accessibility Implications
- Touch targets minimum 44x44px on mobile
- Nav links remain tappable at 480px breakpoint
- Modals and overlays constrained to viewport on mobile
- Focus management preserved across breakpoint changes

### Performance Characteristics
- No JavaScript required for responsive behavior
- CSS Grid and Flexbox for efficient reflow
- `@media` queries evaluated by browser rendering engine
- No performance overhead

### Browser/Platform Support
- Media queries: All browsers
- CSS Grid: Chrome 57+, Firefox 52+, Safari 10.1+
- Flexbox: Chrome 29+, Firefox 28+, Safari 9+

### Integration Points
- Used by all layout components (dashboard, chat, auth)
- Breakpoints align with `DesignTokens` spacing scale
- Theme engine respects system preference via `prefers-color-scheme`

---

## Group 15: Performance Budgets and Bundle-Splitting Hooks
**Files:** `frontend/js/platform/performance.js`

### Summary
Web Vitals monitoring (FCP, LCP, FID, CLS, TTFB) with PerformanceObserver API, resource timing analysis, and configurable budget thresholds with violation alerts.

### Accessibility Implications
- Performance violations logged but not disruptive to screen readers
- Metrics reported via `console.log` with structured data
- No ARIA live regions for performance data (not user-facing)

### Performance Characteristics
- PerformanceObserver runs off main thread
- Resource timing sampled on load
- Budget violations emitted as events, not UI alerts
- ~5KB minified

### Browser/Platform Support
- PerformanceObserver: Chrome 52+, Firefox 57+, Safari 12.1+
- Largest Contentful Paint: Chrome 77+, Firefox 88+, Safari 15.4+
- Cumulative Layout Shift: Chrome 77+, Firefox 79+, Safari 15.4+
- Navigation Timing: All modern browsers

### Integration Points
- `Performance.init()` called by `platform/index.js`
- Budget violations can trigger `Toast.error()`
- Metrics can be sent to analytics endpoint

---

## Platform Bootstrap
**Files:** `frontend/js/platform/index.js`

### Summary
Entry point that initializes ThemeEngine, PWA, OfflineQueue, and Performance on DOMContentLoaded.

### Integration Points
- Included in `index.html` before app scripts
- Initializes platform services before UI rendering
