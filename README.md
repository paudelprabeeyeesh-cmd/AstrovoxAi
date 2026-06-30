# ASTRAVOX PRIME

## Advanced AI Chat Platform

ASTRAVOX PRIME is a cutting-edge AI chat platform designed to provide an intelligent and interactive conversational experience. It features a modern React frontend, a robust FastAPI backend, and leverages Supabase for its database and authentication needs. The platform is built with scalability and maintainability in mind, ensuring a seamless experience for users and developers alike.

## Features

- **User Authentication**: Secure sign-up, login, logout, and password reset functionalities powered by Supabase Auth.
- **Persistent Sessions**: Users remain logged in across sessions, providing a continuous experience.
- **Protected Routes**: Ensures that only authenticated users can access sensitive parts of the application.
- **AI Chat Interface**: A dynamic chat environment where users can interact with an AI, create new conversations, and review past interactions.
- **Conversation History**: All messages and conversations are saved and can be loaded for future reference.
- **AI Memory System**: An intelligent memory system that stores important information from conversations, allowing the AI to provide more personalized and context-aware responses.
- **Dashboard**: A comprehensive dashboard featuring:
    - **Sidebar**: For managing and navigating between conversations.
    - **Telemetry**: Real-time system diagnostics and statistics.
    - **Terminal Console**: An interactive command-line interface for system interactions.
    - **Memory Panel**: To view and manage AI memory entries.
    - **Settings Panel**: For user-specific configurations, including AI model preferences and theme settings.
- **Responsive UI**: Designed to provide an optimal viewing and interaction experience across a wide range of devices.
- **Modular Backend**: A FastAPI backend with a clear, modular architecture for easy development and maintenance.
- **Supabase Integration**: Utilizes Supabase for PostgreSQL database, authentication, and real-time capabilities.

## Technology Stack

- **Frontend**: React, Vite, TailwindCSS
- **Backend**: FastAPI, Python
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **AI Integration**: OpenAI API

## Getting Started

To set up and run ASTRAVOX PRIME locally, please refer to the [SETUP.md](SETUP.md) guide.

## API Documentation

For detailed information on the available API endpoints, request/response formats, and authentication mechanisms, please consult the [API.md](API.md) documentation.

## Project Structure

```
AstrovoxAi/
├── src/                    # React frontend components and logic
├── 02-Backend/            # FastAPI backend application
│   ├── app/                # FastAPI application modules (auth, chat, api, memory, database)
│   └── requirements.txt    # Python dependencies
├── database/               # Database schema and migration scripts
│   └── schemas/
├── .env                    # Environment variables (local configuration)
├── .env.example            # Example environment variables
├── package.json            # Frontend dependencies and scripts
├── vite.config.js          # Vite build configuration
├── index.html              # Frontend HTML entry point
├── README.md               # Project overview
├── SETUP.md                # Setup and installation guide
├── API.md                  # API documentation
└── ROADMAP.md              # Future development roadmap
```

## Contributing

We welcome contributions to ASTRAVOX PRIME! Please refer to the [ROADMAP.md](ROADMAP.md) for planned features and consider opening an issue or pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License.

## Authors

- Prabesh Paudel
- Dipson Baral
- Susanta Baral
