# Astrovox AI - iOS App

## Overview

Native iOS app built with SwiftUI and Combine.

## Architecture

- SwiftUI for UI
- Combine for reactive programming
- URLSession for networking
- Core Data for local storage
- Speech framework for voice input
- AVFoundation for voice output

## Features

- Native chat interface
- Voice input (Speech framework)
- Voice output (AVSpeechSynthesizer)
- Push notifications
- Offline mode with Core Data
- Background sync

## Getting Started

```bash
# Open in Xcode
open AstrovoxAI.xcodeproj

# Or use Swift Package Manager
swift build
```

## Project Structure

```
AstrovoxAI/
├── AstrovoxAIApp.swift
├── Models/
│   ├── Message.swift
│   ├── Conversation.swift
│   └── User.swift
├── Views/
│   ├── ChatView.swift
│   ├── ConversationsListView.swift
│   └── SettingsView.swift
├── ViewModels/
│   ├── ChatViewModel.swift
│   └── ConversationsViewModel.swift
├── Services/
│   ├── APIService.swift
│   ├── OfflineService.swift
│   └── SyncService.swift
└── Resources/
    ├── Assets.xcassets
    └── Info.plist
```

## Build

```bash
xcodebuild -project AstrovoxAI.xcodeproj -scheme AstrovoxAI -configuration Release
```
