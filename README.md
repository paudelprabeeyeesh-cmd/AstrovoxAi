<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&height=320&color=0:0B0B1A,20:1A1040,50:4C1D95,80:7C3AED,100:EC4899&text=ASTRAVOX%20AI&fontColor=ffffff&fontSize=70&fontAlign=50&fontAlignY=42&desc=Advanced%20AI%20Chat%20Platform&descAlign=50&descAlignY=68&animation=fadeIn&section=header" width="100%"/>
<br/>
# ⚡ ASTRAVOX AI
### *An Advanced, Full-Stack AI Chat Platform.*
 
**React + Vite frontend · FastAPI backend · Supabase (PostgreSQL + Auth) · OpenAI-powered intelligence**
 
<br/>

</div>
---
 
## 📖 Overview
 
**ASTRAVOX AI** is a cutting-edge AI chat platform designed to deliver an intelligent, interactive, and deeply personalized conversational experience. It pairs a modern **React + Vite** frontend with a modular **FastAPI** backend, and relies on **Supabase** for its PostgreSQL database, authentication, and real-time capabilities.
 
The platform was built with three principles at its core:
 
1. **Scalability** — a modular backend structure (`auth`, `chat`, `api`, `memory`, `database`) that can grow without becoming unmanageable.
2. **Maintainability** — clean separation between frontend, backend, and database layers, so each piece can evolve independently.
3. **User experience** — persistent sessions, conversation history, and an AI memory system that makes every conversation feel continuous rather than starting from zero.
Unlike a simple chatbot wrapper, ASTRAVOX PRIME behaves like a small **product**: it has authentication, protected routes, a full dashboard, telemetry, a terminal console, and a settings panel — the scaffolding of a real SaaS application, not just a chat window bolted onto an API call.
 
> **In one sentence:** ASTRAVOX AI is what you get when a conversational AI interface is built with the same rigor as a production web application — auth, persistence, memory, and observability included.
 
---
 
## ✨ Features
 
### 🔐 Authentication & Access Control
 
- **Secure Sign-Up / Login / Logout** — powered end-to-end by Supabase Auth.
- **Password Reset Flow** — self-service account recovery without manual intervention.
- **Persistent Sessions** — users stay logged in across page reloads and browser restarts.
- **Protected Routes** — sensitive views (chat, dashboard, memory panel, settings) are only reachable by authenticated users.
### 💬 AI Chat Experience
 
- **Dynamic Chat Interface** — create new conversations, switch between them, and pick up exactly where you left off.
- **Conversation History** — every message and every conversation thread is persisted and retrievable.
- **Context-Aware Responses** — the AI draws on stored memory and prior conversation turns to respond more relevantly than a stateless chatbot.
- **Multiple Conversations** — manage several distinct chat threads in parallel without cross-contamination of context.
### 🧠 AI Memory System
 
- **Long-Term Memory Storage** — the platform extracts and stores important facts and context from conversations.
- **Personalized Responses** — future replies are shaped by what the AI has previously learned about the user.
- **Memory Panel (UI)** — a dedicated dashboard view where users can inspect, review, and manage what the AI remembers about them.
- **Transparency First** — memory isn't a black box; it's surfaced directly in the UI rather than hidden in a backend table.
### 🖥️ Dashboard
 
The dashboard is the operational home base of the platform and includes:
 
| Panel | Purpose |
| :--- | :--- |
| **Sidebar** | Navigate between conversations and manage chat threads. |
| **Telemetry** | Real-time system diagnostics and usage statistics. |
| **Terminal Console** | An interactive command-line interface for direct system interaction. |
| **Memory Panel** | View, inspect, and manage stored AI memory entries. |
| **Settings Panel** | Configure AI model preferences, themes, and user-specific options. |
 
### 🎨 Design & Experience
 
- **Responsive UI** — built with TailwindCSS to look and behave well across desktop, tablet, and mobile.
- **Theme Support** — user-configurable appearance settings surfaced through the Settings Panel.
- **Consistent Design System** — shared styling primitives across every dashboard panel and chat view.
### 🏗️ Backend Architecture
 
- **Modular FastAPI Design** — cleanly separated modules for `auth`, `chat`, `api`, `memory`, and `database`, so each concern can be developed, tested, and scaled independently.
- **Supabase Integration** — PostgreSQL for structured data, Supabase Auth for identity, and Supabase's real-time layer for live updates.
- **OpenAI-Powered Intelligence** — the conversational core is driven by OpenAI's API, orchestrated through the backend's chat module.
---
 
## 🧠 Architecture
 
```text
┌──────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                │
│           React + Vite SPA · TailwindCSS UI · Protected Routing          │
└────────────────────────────────────┬─────────────────────────────────────┘
                                      │  HTTPS / REST
┌────────────────────────────────────▼─────────────────────────────────────┐
│                         FASTAPI APPLICATION LAYER                        │
│   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐            │
│   │   auth    │  │   chat    │  │  memory   │  │    api    │            │
│   │  module   │  │  module   │  │  module   │  │  module   │            │
│   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘            │
└─────────┼──────────────┼──────────────┼──────────────┼──────────────────┘
          │              │              │              │
          ▼              ▼              ▼              ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │  Supabase   │ │   OpenAI    │ │  Memory     │ │  Realtime   │
   │  Auth       │ │   API       │ │  Store      │ │  Channel    │
   └──────┬──────┘ └─────────────┘ └──────┬──────┘ └──────┬──────┘
          │                               │               │
          └───────────────┬───────────────┴───────────────┘
                           ▼
              ┌────────────────────────────┐
              │   Supabase PostgreSQL DB    │
              │  users · conversations ·    │
              │  messages · memory_entries  │
              └────────────────────────────┘
```
 
### How a message flows through the system
 
1. **Client** — the user types a message in the React chat interface.
2. **Auth Guard** — the protected route confirms an active Supabase session before the request is sent.
3. **Chat Module** — the FastAPI `chat` module receives the message, attaches relevant conversation history, and pulls in anything useful from the `memory` module.
4. **OpenAI Call** — the enriched context is sent to the OpenAI API for a response.
5. **Memory Extraction** — the `memory` module evaluates the exchange for anything worth remembering long-term and persists it.
6. **Persistence** — the message, response, and any new memory entries are written to the Supabase PostgreSQL database.
7. **Response** — the AI's reply streams back to the client and renders in the chat interface, while the dashboard's telemetry panel reflects the updated system state.
---
 
## 🛠️ Tech Stack
 
| Layer | Technology |
| :--- | :--- |
| **Frontend Framework** | React |
| **Build Tool** | Vite |
| **Styling** | TailwindCSS |
| **Backend Framework** | FastAPI (Python) |
| **Database** | Supabase (PostgreSQL) |
| **Authentication** | Supabase Auth |
| **AI Engine** | OpenAI API |
| **Realtime Layer** | Supabase Realtime |
 

 
This split reflects the project's shape well: a JavaScript-heavy React frontend, a substantial Python backend, and a PL/pgSQL layer for Supabase database functions and triggers.
 
---
 
## 📁 Project Structure
 
```text
AstrovoxAi/
├── src/                       # React frontend components and logic
├── 02-Backend/                # FastAPI backend application
│   ├── app/                   # FastAPI application modules
│   │   ├── auth/              # Authentication logic (Supabase Auth integration)
│   │   ├── chat/              # Chat orchestration and OpenAI integration
│   │   ├── api/                # REST API route definitions
│   │   ├── memory/            # AI memory extraction and retrieval
│   │   └── database/           # Database access layer
│   └── requirements.txt        # Python dependencies
├── database/                  # Database schema and migration scripts
│   └── schemas/                # SQL schema definitions
├── .env                       # Environment variables (local configuration)
├── .env.example                # Example environment variables
├── package.json                # Frontend dependencies and scripts
├── vite.config.js              # Vite build configuration
├── index.html                  # Frontend HTML entry point
├── README.md                   # Project overview (this file)
├── SETUP.md                    # Setup and installation guide
├── API.md                      # Full API documentation
├── Architecture.md             # Deeper architectural notes
├── DEVELOPMENT_GUIDE.md        # Guide for contributors
├── QUICK_REFERENCE.md          # Fast lookup for common tasks
├── ROADMAP.md                  # Future development roadmap
└── SECURITY.md                 # Security policy and disclosure process
```
 
> The repository also contains supporting directories such as `Documentation/`, `Testing-QA/`, `DevOps-Deployment/`, `Design-System/`, and `Team-Resources/` for project-wide documentation, QA processes, deployment configuration, and shared design assets.
 
---
 
## 🚦 Getting Started
 
Full setup instructions live in [`SETUP.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/SETUP.md). The short version:
 
### 1. Clone the repository
 
```bash
git clone https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi.git
cd AstrovoxAi
```
 
### 2. Install frontend dependencies
 
```bash
npm install
```
 
### 3. Install backend dependencies
 
```bash
cd 02-Backend
pip install -r requirements.txt
cd ..
```
 
### 4. Configure environment variables
 
```bash
cp .env.example .env
```
 
Populate `.env` with your own Supabase and OpenAI credentials:
 
```text
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
OPENAI_API_KEY=your-openai-api-key
DATABASE_URL=your-postgres-connection-string
```
 
### 5. Run the frontend
 
```bash
npm run dev
```
 
### 6. Run the backend
 
```bash
cd 02-Backend
uvicorn app.main:app --reload
```
 
For a complete walkthrough — including database schema setup and Supabase project configuration — see [`SETUP.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/SETUP.md).
 
---
 
## 🖥️ The Dashboard
 
The dashboard is where the platform stops feeling like "a chatbot" and starts feeling like a real product.
 
### Sidebar
 
The primary navigation surface. Lists active conversations, supports creating new threads, and lets users jump between chats without losing context.
 
### Telemetry
 
A real-time view into how the system is behaving — surfacing usage statistics and diagnostics so both the user and the developer can see the platform's live state rather than treating it as a black box.
 
### Terminal Console
 
An interactive command-line interface embedded directly in the dashboard, giving power users a faster, more direct way to interact with the system than clicking through UI panels.
 
### Memory Panel
 
The visual front-end for the AI memory system (see below) — a place to review what the AI has stored and manage or remove entries.
 
### Settings Panel
 
User-specific configuration: AI model preferences and theme/appearance settings, all scoped to the authenticated user's account.
 
---
 
## 🧬 AI Memory System
 
The memory system is what separates ASTRAVOX AI from a stateless chat wrapper.
 
- **Extraction** — as conversations happen, the `memory` module identifies information worth retaining (preferences, facts, ongoing context).
- **Storage** — extracted memory entries are persisted in the Supabase PostgreSQL database, tied to the user's account.
- **Retrieval** — on future conversations, relevant memory entries are pulled back into context before a response is generated.
- **Personalization** — the net effect is an AI that responds with awareness of who it's talking to, rather than treating every message as the first one.
- **User Control** — the Memory Panel in the dashboard gives users visibility into, and control over, what's being remembered.
---
 
## 📡 API Documentation
 
Full endpoint definitions, request/response formats, and authentication mechanisms are documented in [`API.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/API.md). At a high level, the API surface is organized around the same modules as the backend itself:
 
| Module | Responsibility |
| :--- | :--- |
| **auth** | Sign-up, login, logout, password reset, session validation |
| **chat** | Sending messages, retrieving conversation history, managing threads |
| **memory** | Reading, writing, and managing AI memory entries |
| **api** | Shared/general-purpose endpoints used across the platform |
 
Refer to `API.md` for exact routes, parameters, and example payloads.
 
---
 
## 🗺️ Roadmap
 
Planned and in-progress work is tracked in [`ROADMAP.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/ROADMAP.md). Broad areas of ongoing and future development include:
 
- **Deeper memory intelligence** — smarter extraction and ranking of what's worth remembering.
- **Expanded telemetry** — richer real-time diagnostics in the dashboard.
- **Additional AI model support** — configurable model backends beyond a single provider.
- **Hardened security** — see [`SECURITY.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/SECURITY.md) for the current security policy and how to report issues.
- **Expanded documentation** — continued growth of `Architecture.md`, `DEVELOPMENT_GUIDE.md`, and `QUICK_REFERENCE.md` as the codebase matures.
For the authoritative, up-to-date list, always check `ROADMAP.md` directly in the repository.
 
---
 
## 🤝 Contributing
 
Contributions to ASTRAVOX AI are welcome.
 
1. Check [`ROADMAP.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/ROADMAP.md) for planned features before starting new work.
2. Read [`DEVELOPMENT_GUIDE.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/DEVELOPMENT_GUIDE.md) for coding conventions and project workflow.
3. Open an issue to discuss significant changes before submitting a pull request.
4. Keep pull requests focused — one feature or fix per PR.
5. Follow the project's existing module structure (`auth`, `chat`, `memory`, `api`, `database`) when adding backend functionality.
See [`CONTRIBUTING.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/CONTRIBUTING.md) for full contribution guidelines.
 
---
 
## 🔒 Security
 
Security policy and vulnerability disclosure process are documented in [`SECURITY.md`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/SECURITY.md). Please report suspected vulnerabilities responsibly rather than opening a public issue.
 
---
 
## 👥 Authors
 
<div align="center">
## 👨‍💻 Prabeesh Paudel

# Founder & Chief Executive Officer (CEO)
### AstrovoxAI

**Founder • CEO • AI Developer • Backend Engineer • Product Architect • Technical Lead • AI Systems Engineer • API Developer • Cloud Enthusiast • Product Designer • Open Source Contributor • Startup Builder**

Prabeesh Paudel is the Founder and Chief Executive Officer (CEO) of AstrovoxAI, where he leads the company's product vision, technical strategy, and engineering direction. He is responsible for designing and developing AI-powered applications, backend systems, cloud deployment, API architecture, and the long-term roadmap of the platform.

He works across multiple areas of software engineering, including artificial intelligence, large language model (LLM) integration, retrieval-augmented generation (RAG), backend development, authentication systems, cloud infrastructure, system design, and developer tooling. He enjoys learning through documentation, experimentation, and building real-world software.

### Current Responsibilities
- 🧠 Founder & CEO
- 🤖 AI Developer
- ⚙️ Backend Engineer
- 🏗️ Product Architect
- 💡 Technical Lead
- 🔌 API Engineer
- ☁️ Cloud Infrastructure Developer
- 📦 DevOps Learner
- 🚀 Startup Builder

### Technical Interests
- Artificial Intelligence
- Large Language Models (LLMs)
- Agentic AI Systems
- Retrieval-Augmented Generation (RAG)
- Cloud Computing
- Distributed Systems
- Software Architecture
- Cybersecurity
- Developer Tools
- Automation
- Open Source

### Currently Learning
- Advanced Python
- TypeScript
- Go
- System Design
- Distributed Systems
- Cloud Architecture

> **Mission:** Build practical AI products that solve real-world problems through reliable engineering, continuous learning, and long-term thinking.

 
</div>
ASTRAVOX AI is built and maintained by this team, with ongoing contributions tracked in the repository's [commit history](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/commits/main/) and [contributor graph](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/graphs/contributors).
 
---
 
## 📄 License
 
This project is licensed under the **MIT License** — see [`LICENSE`](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/LICENSE) for the full text.
 
## 📬 Contact & Links
 
- **Repository:** [github.com/paudelprabeeyeesh-cmd/AstrovoxAi](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi)
- **Issues:** [Report a bug or request a feature](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/issues)
- **Setup Guide:** [SETUP.md](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/SETUP.md)
- **API Docs:** [API.md](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/API.md)
- **Architecture Notes:** [Architecture.md](https://github.com/paudelprabeeyeesh-cmd/AstrovoxAi/blob/main/Architecture.md)
<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&height=160&color=0:0B0B1A,20:1A1040,50:4C1D95,80:7C3AED,100:EC4899&section=footer" width="100%"/>
✦ ASTRAVOX AI — an intelligent chat platform, built to last ✦
 
</div>
