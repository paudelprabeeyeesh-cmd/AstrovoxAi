# ASTRAVOX AI - Setup Guide Created By 🥇Prabesh Paudel

## Prerequisites

- Node.js 18+ (for frontend)
- Python 3.9+ (for backend)
- Supabase account and project
- OpenAI API key

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi
```

### 2. Environment Setup

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:
- `VITE_SUPABASE_URL`: Your Supabase project URL
- `VITE_SUPABASE_ANON_KEY`: Your Supabase anon key
- `OPENAI_API_KEY`: Your OpenAI API key

### 3. Frontend Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 4. Backend Setup

```bash
# Navigate to backend directory
cd 02-Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

### 5. Database Setup

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Run the SQL from `database/schemas/supabase_setup.sql`
4. This will create all necessary tables with RLS policies

## Features

### Authentication
- Sign up with email and password
- Login with email and password
- Forgot password functionality
- Session persistence
- Protected routes

### Chat
- Create multiple conversations
- Send messages to AI
- View conversation history
- Real-time message updates
- Typing indicators

### Memory System
- Save important information
- Retrieve user context
- Auto-extract from conversations
- Memory-based AI responses

### Dashboard
- Sidebar with conversation list
- Chat interface
- Terminal console
- System telemetry
- Memory panel
- Settings panel

## API Endpoints

### Authentication
- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/logout` - Logout user
- `POST /auth/reset-password` - Reset password
- `GET /auth/me` - Get current user

### Chat
- `POST /chat/conversations` - Create conversation
- `GET /chat/conversations` - List conversations
- `GET /chat/conversations/{id}` - Get conversation
- `GET /chat/conversations/{id}/messages` - Get messages
- `POST /chat/message` - Send message
- `DELETE /chat/conversations/{id}` - Delete conversation

### Memory
- `POST /memory/save` - Save memory entry
- `GET /memory` - Get user memory
- `POST /memory/extract-from-conversation` - Extract from conversation
- `POST /memory/auto-extract` - Auto-extract using LLM

### API
- `GET /api/status` - API status
- `GET /api/me` - Current user info
- `GET /api/stats` - User statistics
- `GET /api/memory` - Get memory

## Troubleshooting

### Frontend won't connect to backend
- Make sure backend is running on `http://localhost:8000`
- Check CORS settings in backend
- Verify `VITE_API_URL` in `.env`

### Supabase connection issues
- Verify `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- Check that tables exist in Supabase
- Verify RLS policies are correctly set

### OpenAI API errors
- Verify `OPENAI_API_KEY` is correct
- Check API key has sufficient credits
- Verify model name is correct (gpt-4 or gpt-3.5-turbo)

## Development

### Project Structure

```
AstrovoxAi/
├── src/                    # React frontend
│   ├── app.jsx            # Main app component
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
├── 02-Backend/            # FastAPI backend
│   ├── app/
│   │   ├── main.py        # FastAPI app
│   │   ├── auth.py        # Authentication routes
│   │   ├── chat.py        # Chat routes
│   │   ├── api.py         # API routes
│   │   ├── memory.py      # Memory routes
│   │   └── database.py    # Database operations
│   └── requirements.txt    # Python dependencies
├── database/
│   └── schemas/
│       └── supabase_setup.sql # Database schema
├── .env                   # Environment variables
├── package.json           # Frontend dependencies
├── vite.config.js         # Vite configuration
└── index.html             # HTML entry point
```

## Deployment

### Frontend (Vercel/Netlify)
1. Push code to GitHub
2. Connect repository to Vercel/Netlify
3. Set environment variables
4. Deploy

### Backend (Railway/Render)
1. Push code to GitHub
2. Connect repository to Railway/Render
3. Set environment variables
4. Deploy

## Support

For issues or questions, please create an issue on GitHub or contact the development team.

## License

This project is licensed under the MIT License.
