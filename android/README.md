# Astrovox AI - Android App

## Overview

Native Android app built with Kotlin, Jetpack Compose, and Coroutines.

## Architecture

- Jetpack Compose for UI
- Coroutines + Flow for async
- Retrofit for networking
- Room for local storage
- SpeechRecognizer for voice input
- TextToSpeech for voice output

## Features

- Native chat interface
- Voice input
- Voice output
- Push notifications
- Offline mode with Room
- Background sync with WorkManager

## Getting Started

```bash
# Open in Android Studio
open AstrovoxAI.android

# Or build with Gradle
./gradlew assembleRelease
```

## Project Structure

```
app/src/main/java/ai/astrovox/
├── AstrovoxAIApplication.kt
├── data/
│   ├── local/
│   │   ├── AppDatabase.kt
│   │   └── entities/
│   ├── remote/
│   │   └── ApiService.kt
│   └── repository/
│       └── ChatRepository.kt
├── domain/
│   ├── model/
│   │   ├── Message.kt
│   │   └── Conversation.kt
│   └── usecase/
│       └── SendMessageUseCase.kt
├── presentation/
│   ├── chat/
│   │   ├── ChatScreen.kt
│   │   └── ChatViewModel.kt
│   └── conversations/
│       ├── ConversationsScreen.kt
│       └── ConversationsViewModel.kt
└── ui/theme/
    ├── Color.kt
    ├── Theme.kt
    └── Type.kt
```

## Build

```bash
./gradlew assembleRelease
```
