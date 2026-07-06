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
- **Rate Limiting**: Built-in rate limiting for authentication and chat endpoints to prevent abuse.
- **Docker Support**: Containerized deployment with Docker and Docker Compose for easy production deployment.
- **CI/CD Pipeline**: Automated testing, linting, and security scanning via GitHub Actions.

## Technology Stack

- **Frontend**: React, Vite
- **Backend**: FastAPI, Python 3.9+
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **AI Integration**: OpenAI API
- **Containerization**: Docker, Docker Compose
- **CI/CD**: GitHub Actions

## Getting Started

To set up and run ASTRAVOX PRIME locally, please refer to the [SETUP.md](SETUP.md) guide.

For production deployment, see the [DEPLOYMENT.md](DEPLOYMENT.md) guide.

## API Documentation

For detailed information on the available API endpoints, request/response formats, and authentication mechanisms, please consult the [API.md](API.md) documentation.

## Project Structure

```
AstrovoxAi/
├── src/                    # React frontend components and logic
│   ├── app.jsx            # Main application component
│   ├── auth.jsx           # Authentication component
│   ├── Dashboard.jsx      # Main dashboard
│   ├── Chat.jsx           # Chat interface
│   ├── Sidebar.jsx        # Conversation sidebar
│   ├── MemoryPanel.jsx    # Memory management
│   ├── SettingsPanel.jsx  # User settings
│   ├── telemetry.jsx      # System telemetry
│   ├── terminalconsole.jsx # Terminal console
│   ├── supabase.js        # Supabase client
│   └── main.jsx           # React entry point
├── 02-Backend/            # FastAPI backend application
│   ├── app/
│   │   ├── main.py        # FastAPI app with CORS and rate limiting
│   │   ├── auth.py        # Authentication routes
│   │   ├── chat.py        # Chat routes with rate limiting
│   │   ├── api.py         # API routes
│   │   ├── memory.py      # Memory routes
│   │   ├── database.py    # Database operations
│   │   ├── supabase_client.py # Singleton Supabase client
│   │   └── auth_utils.py  # Shared authentication utilities
│   ├── tests/             # Backend tests
│   └── requirements.txt    # Python dependencies
├── database/               # Database schema and migration scripts
│   ├── schemas/
│   │   └── supabase_setup.sql # Database schema
│   └── migrations/
│       └── 0001_indexes_and_signup_trigger.sql # Performance indexes
├── .github/               # GitHub Actions CI/CD
│   └── workflows/
│       └── ci.yml         # CI/CD pipeline
├── .env.example            # Example environment variables
├── Dockerfile.backend      # Backend Docker configuration
├── Dockerfile.frontend     # Frontend Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── nginx.conf              # Nginx configuration for frontend
├── package.json            # Frontend dependencies and scripts
├── vite.config.js          # Vite build configuration
├── index.html              # Frontend HTML entry point
├── README.md               # Project overview
├── SETUP.md                # Setup and installation guide
├── DEPLOYMENT.md           # Deployment guide
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
- Susanta AI
