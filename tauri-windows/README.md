# Tauri Desktop Apps

Astrovox AI desktop apps are built with Tauri for Windows, macOS, and Linux.

## Prerequisites

- Node.js 18+
- Rust 1.70+
- Platform-specific build tools

## Build

### Windows
```bash
cd tauri-windows
npm install
npm run tauri build
```

### macOS
```bash
cd tauri-macos
npm install
npm run tauri build
```

### Linux
```bash
cd tauri-linux
npm install
npm run tauri build
```

## Features

- Native window management
- System tray integration
- Auto-update support
- File system access
- Native notifications

## Auto-Update

Apps use Tauri's built-in updater:

```json
{
  "updater": {
    "endpoints": ["https://releases.astrovox.ai/{{target}}/{{current_version}}"],
    "dialog": true,
    "pubkey": "YOUR_PUBLIC_KEY"
  }
}
```
