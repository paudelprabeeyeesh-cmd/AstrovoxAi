# Component Library

Reusable React components for building Astrovox integrations.

## Installation

```bash
npm install @astrovox/components
```

## Components

### Chat Components
- `ChatInterface` - Full chat UI
- `StreamingMessage` - Streaming message display
- `MessageActions` - Copy, edit, delete actions
- `MarkdownRenderer` - Markdown + KaTeX + Mermaid
- `CodeBlock` - Syntax highlighted code
- `MediaEmbed` - Image, audio, video, file embedding
- `FileUpload` - Drag & drop file upload
- `VoiceInput` - Voice input with Web Speech API
- `VoiceOutput` - Text-to-speech output
- `CameraCapture` - Camera photo capture
- `ScreenShare` - Screen sharing
- `Whiteboard` - Collaborative whiteboard

### Workspace Components
- `MultiChatTabs` - Multiple chat tabs
- `ChatBranching` - Branch conversations
- `FolderSystem` - Folder management
- `DragDropList` - Drag-and-drop conversation reordering
- `TeamWorkspace` - Team collaboration
- `SharedConversations` - Shared content

### UI Components
- `NotificationCenter` - Notification management
- `KeyboardShortcuts` - Keyboard navigation
- `KeyboardShortcutCheatsheet` - Keyboard shortcut reference overlay
- `ThemeEngine` - Theme management
- `ThemeSwitcher` - Enhanced theme switcher with live preview
- `CommandPalette` - Global command palette (Cmd+K)
- `Toast` - Toast notification system
- `Modal` - Modal/dialog with focus trap
- `Tooltip` - Tooltip system with positioning
- `Skeleton` - Skeleton loading states
- `EmptyState` - Empty-state illustrations
- `Avatar` - Avatar/initials generator
- `SplitPane` - Resizable split-pane layouts
- `A11yProvider` - Accessibility context

### Admin Components
- `InternalAdmin` - Internal admin panel
- `CustomerAdmin` - Customer admin panel

### Dashboard Components
- `AnalyticsDashboard` - Analytics metrics
- `CostDashboard` - Cost tracking
- `UsageDashboard` - Usage statistics
- `IncidentDashboard` - Incident management
- `FeatureFlagsDashboard` - Feature flags
- `ModelPerformanceDashboard` - Model metrics

## Usage

```tsx
import { ChatInterface, ThemeEngine } from '@astrovox/components'

function App() {
  return (
    <ThemeEngine>
      <ChatInterface session={session} />
    </ThemeEngine>
  )
}
```
