# Frontend Advanced Features

## Overview

This document describes the advanced frontend features implemented in AstrovoxAI beyond the base product checklist.

## Real-time Collaboration with CRDT

### CRDTProvider
Location: `src/components/crdt/CRDTProvider.jsx`

A Conflict-free Replicated Data Type (CRDT) provider for real-time collaborative editing. Features:
- WebSocket-based operational transform broadcasting
- Peer presence tracking with deterministic color assignment
- Automatic reconnection on connection loss
- Operation ID generation with lamport clock
- Insert, delete, and update operations with conflict resolution

Usage:
```jsx
import { CRDTProvider, useCRDT } from '../components/crdt/CRDTProvider'

function App() {
  return (
    <CRDTProvider documentId="doc-1" userId="user-123">
      <CollaborativeEditor />
    </CRDTProvider>
  )
}

function CollaborativeEditor() {
  const { insert, update, delete: del } = useCRDT()
  // ...
}
```

### CollaborationProvider
Location: `src/components/crdt/CollaborationProvider.jsx`

Wraps CRDTProvider with user-facing collaboration features:
- Presence sync with periodic heartbeat
- Cursor position broadcasting
- Selection range sharing
- Deterministic color assignment based on user ID hash

## Advanced Markdown Rendering with Syntax Highlighting

### MarkdownRenderer
Location: `src/components/chat/MarkdownRenderer.jsx`

Full markdown pipeline supporting:
- Fenced code blocks with language detection
- KaTeX math rendering (inline and display)
- Mermaid diagram embedding
- Artifact blocks for structured data
- Image, audio, and video embeds
- Animated block transitions

### CodeBlock
Location: `src/components/chat/CodeBlock.jsx`

Code block component with:
- One-click copy to clipboard
- Language label display
- Monospace font rendering
- Scrollable overflow handling

## Artifact System

### ArtifactViewer
Location: `src/components/chat/ArtifactViewer.jsx`

Renders structured artifacts from AI responses:
- JSON artifact parsing with error handling
- Code preview panels
- File download links
- Syntax-highlighted previews

## Voice Input/Output with WebRTC

### VoiceInput
Location: `src/components/chat/VoiceInput.jsx`

Speech-to-text using Web Speech API:
- Continuous recognition mode
- Interim transcript display
- Error handling for unsupported browsers
- Auto-stop on silence

### VoiceOutput
Location: `src/components/chat/VoiceOutput.jsx`

Text-to-speech playback:
- Voice selection from available system voices
- Play/pause/stop controls
- Rate and pitch adjustment
- Auto-read for assistant messages

## Screen Sharing and Whiteboarding

### ScreenShare
Location: `src/components/chat/ScreenShare.jsx`

Screen capture using `getDisplayMedia`:
- Video preview with stop controls
- Track cleanup on unmount
- Error handling for permission denial
- Cursor visibility options

### Whiteboard
Location: `src/components/chat/Whiteboard.jsx`

Canvas-based collaborative whiteboard:
- Freehand drawing with configurable colors and line width
- Undo/redo history stack
- Tool selection (pen, eraser)
- Save and clear actions

## Multi-modal Input Support

### MultiModalInput
Location: `src/components/MultiModalInput.jsx`

Unified input component supporting:
- Text input with auto-resize
- Voice recording via VoiceInput
- Image capture via CameraCapture
- File upload via FileUpload
- Screen sharing via ScreenShare
- Attachment preview and removal
- Keyboard shortcuts (Enter to send, Shift+Enter for newline)

## Progressive Web App with Offline Support

### Service Worker
Location: `public/sw.js`

Cache-first PWA service worker:
- Static asset precaching on install
- Runtime caching for API responses
- Offline fallback page
- Cache versioning and cleanup

### Web Manifest
Location: `public/manifest.webmanifest`

PWA installation manifest:
- App name, short name, and description
- Theme and background colors
- Icon definitions for various sizes
- App shortcuts for quick actions

### OfflineManager
Location: `src/offline/OfflineManager.js`

React hook for offline-first messaging:
- Online/offline event detection
- Message queue with localStorage persistence
- Background sync simulation
- Queue size tracking

## Performance Profiling Dashboard

### PerformanceDashboard
Location: `src/components/dashboards/PerformanceDashboard.jsx`

Real-time performance metrics visualization:
- Latency sparklines (p50 and p99)
- Memory usage tracking
- Throughput graphs
- Live/paused mode toggle
- Time range selection (1h, 24h, 7d)

## Search Component

### Search
Location: `src/components/Search.jsx`

Global search with:
- Debounced API queries
- Keyboard navigation (ArrowUp/Down, Enter, Escape)
- Result type icons and snippets
- Active result highlighting
- Clear button

## Code Execution

### CodeExecution
Location: `src/components/CodeExecution.jsx`

In-browser code execution UI:
- Multi-language support (Python, JS, TS, Go, Rust, Bash)
- One-click execution via API
- Output and error display
- Keyboard shortcut (Ctrl+Enter to run)
- Copy-friendly output panel

## Design System

### DarkModeVariants
Location: `src/design/DarkModeVariants.jsx`

Extended theme variants:
- Astrovox Prime (default dark)
- Midnight (pure black OLED-friendly)
- Ocean Depth (blue-tinted dark)
- Forest (green-tinted dark)
- Sunset (warm orange-tinted dark)

## Testing Enhancements

### New Test Files
- `tests/unit/components/Search.test.jsx` - Search component tests
- `tests/unit/components/CodeExecution.test.jsx` - Code execution tests
- `tests/unit/components/PerformanceDashboard.test.jsx` - Performance dashboard tests
- `tests/unit/components/CRDTProvider.test.jsx` - CRDT context tests
- `tests/unit/components/MultiModalInput.test.jsx` - Multi-modal input tests
- `tests/unit/design/DarkModeVariants.test.jsx` - Theme variant tests
- `tests/unit/service-worker.test.js` - Service worker registration tests

## Configuration Changes

- `index.html`: Added PWA meta tags and manifest link
- `src/main.jsx`: Added service worker registration
- `tests/unit/hooks/OfflineMode.test.js`: Fixed module import path
