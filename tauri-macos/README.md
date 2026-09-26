# Astrovox AI - macOS App

## Overview

Native macOS app built with Tauri, Rust backend, and web frontend.

## Architecture

- Tauri 2.x for native shell
- Rust backend for system tray, chat, updates, auth, and deep links
- Vite + vanilla JS frontend for the chat UI

## Features

- Native chat interface via Tauri webview
- System tray integration with show/hide/quit
- Auto-update checker
- Deep link support
- Persistent settings via app data directory

## Getting Started

```bash
cd tauri-macos
npm install
npm run dev
```

## Build

```bash
npm run tauri build
```

## Project Structure

```
tauri-macos/
├── src/
│   ├── index.html
│   ├── main.js
│   └── styles.css
├── src-tauri/
│   ├── src/
│   │   ├── main.rs
│   │   ├── lib.rs
│   │   ├── chat/
│   │   ├── settings/
│   │   ├── updater/
│   │   ├── auth/
│   │   └── deep_link/
│   ├── Cargo.toml
│   └── tauri.conf.json
├── package.json
└── vite.config.js
```
