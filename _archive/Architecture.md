# ASTRAVOX PRIME - Architecture Document

## 1. Introduction

This document outlines the architectural design of ASTRAVOX PRIME, an advanced AI chat platform. It details the system's components, their interactions, and the technologies employed to ensure a scalable, maintainable, and robust application.

## 2. High-Level Architecture

ASTRAVOX PRIME follows a client-server architecture, separating the user interface from the backend logic and data storage. The system is composed of three main layers:

1.  **Frontend (Client-side)**: A React-based web application providing the user interface.
2.  **Backend (Server-side)**: A FastAPI application handling business logic, API endpoints, and communication with external services.
3.  **Database & Authentication**: Supabase, providing PostgreSQL for data persistence and a comprehensive authentication service.

```mermaid
graph TD
    A[User] -->|Accesses| B(Frontend: React/Vite)
    B -->|API Calls (HTTP/S)| C(Backend: FastAPI)
    C -->|Database Operations| D(Supabase: PostgreSQL)
    C -->|AI Requests| E(OpenAI API)
    D -->|Authentication & Data| B
    E -->|AI Responses| C
```

## 3. Component Breakdown

### 3.1. Frontend

The frontend is built using React with Vite for fast development and TailwindCSS for styling. It is responsible for:

-   Rendering the user interface (Dashboard, Chat, Sidebar, Panels).
-   Managing user input and displaying AI responses.
-   Handling client-side routing and state management.
-   Interacting with the backend API for data fetching and submission.
-   Managing user authentication state via Supabase client-side SDK.

**Key Technologies:**
-   **React**: A JavaScript library for building user interfaces.
-   **Vite**: A next-generation frontend tooling that provides a fast development experience.
-   **TailwindCSS**: A utility-first CSS framework for rapid UI development.
-   **Supabase JS SDK**: Client library for interacting with Supabase services.

### 3.2. Backend

The backend is developed with FastAPI, a modern, fast (high-performance) web framework for building APIs with Python 3.7+. It provides:

-   **API Endpoints**: Exposes RESTful APIs for authentication, chat, memory, and general application data.
-   **Business Logic**: Processes requests, interacts with the database, and communicates with the AI service.
-   **Authentication & Authorization**: Validates user tokens and enforces access control using Supabase's authentication system.
-   **Error Handling & Logging**: Provides robust error handling and logging mechanisms.
-   **Modularity**: Organized into distinct modules (e.g., `auth.py`, `chat.py`, `memory.py`, `api.py`, `database.py`) for clear separation of concerns.

**Key Technologies:**
-   **FastAPI**: High-performance Python web framework.
-   **Uvicorn**: ASGI server for running FastAPI applications.
-   **Pydantic**: Data validation and settings management.
-   **Python-dotenv**: Loading environment variables.
-   **Supabase Python SDK**: Client library for interacting with Supabase services.
-   **OpenAI Python SDK**: For integrating with OpenAI's language models.

### 3.3. Database & Authentication (Supabase)

Supabase serves as the backend-as-a-service, providing a PostgreSQL database and a complete authentication solution.

-   **PostgreSQL Database**: Stores all application data, including user profiles, conversations, messages, AI memory entries, and user settings.
-   **Row Level Security (RLS)**: Implemented to ensure that users can only access and modify their own data, enhancing data privacy and security.
-   **Authentication**: Handles user registration, login, password resets, and session management. It integrates seamlessly with the frontend and backend through its SDKs.
-   **Realtime**: Supabase's real-time capabilities can be leveraged for instant updates in the frontend (e.g., new messages, conversation changes).

**Key Tables:**
-   `users`: Managed by Supabase Auth.
-   `profiles`: Stores additional user information (username, full_name, etc.).
-   `conversations`: Stores chat conversation metadata.
-   `messages`: Stores individual messages within conversations.
-   `ai_memory`: Stores important AI memory entries for personalized interactions.
-   `user_settings`: Stores user-specific application settings.

## 4. Data Flow

1.  **User Interaction**: A user interacts with the React frontend (e.g., sends a message).
2.  **Frontend to Backend**: The frontend sends an authenticated API request (e.g., `POST /chat/message`) to the FastAPI backend.
3.  **Backend Processing**: The backend receives the request, validates it, and extracts the user's identity from the authentication token.
4.  **Database Interaction**: The backend saves the user's message to the Supabase PostgreSQL database via the Supabase Python SDK.
5.  **AI Interaction**: The backend constructs a prompt using conversation history and AI memory (fetched from Supabase) and sends it to the OpenAI API.
6.  **AI Response**: The OpenAI API processes the prompt and returns an AI-generated response.
7.  **Backend to Database (AI Response)**: The backend saves the AI's response to the Supabase database.
8.  **Backend to Frontend**: The backend sends the AI's response back to the frontend.
9.  **Frontend Update**: The frontend updates the UI to display the new AI message.

## 5. Security Considerations

-   **Authentication**: All sensitive API endpoints are protected by JWT-based authentication provided by Supabase.
-   **Authorization (RLS)**: Row Level Security policies are enforced at the database level to prevent unauthorized data access.
-   **Environment Variables**: Sensitive API keys and credentials are stored in environment variables and not hardcoded in the codebase.
-   **CORS**: Cross-Origin Resource Sharing is configured to allow secure communication between the frontend and backend.
-   **Input Validation**: Pydantic models are used in FastAPI to ensure all incoming data conforms to expected schemas, preventing common injection attacks.

## 6. Scalability and Maintainability

-   **Stateless Backend**: The FastAPI backend is designed to be stateless, allowing for easy horizontal scaling.
-   **Modular Design**: Clear separation of concerns in both frontend components and backend modules enhances maintainability and simplifies debugging.
-   **Containerization (Future)**: The application is designed to be easily containerized using Docker, facilitating deployment to cloud platforms like Kubernetes.
-   **Database Scalability**: PostgreSQL, managed by Supabase, offers robust scaling capabilities.

## 7. Future Enhancements

-   **Streaming AI Responses**: Implement server-sent events (SSE) or WebSockets for real-time streaming of AI responses.
-   **Advanced Telemetry**: Integrate more detailed monitoring and analytics for system performance and user behavior.
-   **User Profile Management**: Allow users to update their profile information and preferences directly from the dashboard.
-   **Custom AI Models**: Enable users to configure and use different AI models or fine-tuned models.

This architecture provides a solid foundation for ASTRAVOX PRIME, allowing for continuous development and the integration of advanced AI features while maintaining a secure and performant system. 
