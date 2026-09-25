# Data Flow Diagrams

Detailed data flows through the Astrovox AI system.

## Overview

Data flows through Astrovox AI in several distinct paths: user authentication, chat messages, streaming responses, memory operations, and background processing.

## 1. User Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant S as Supabase Auth
    participant D as Database

    U->>F: Enter credentials
    F->>A: POST /auth/login
    A->>S: Verify credentials
    S-->>A: JWT tokens
    A->>D: Create/update session
    A-->>F: Return tokens
    F->>F: Store tokens securely
    F-->>U: Redirect to chat
```

### Flow Details

1. User enters email and password
2. Frontend sends POST to `/auth/login`
3. API validates against Supabase Auth
4. Supabase returns JWT access and refresh tokens
5. API stores session in database
6. Frontend stores tokens in secure HTTP-only cookies or localStorage
7. User is redirected to the chat interface

## 2. Chat Message Flow (Non-Streaming)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant M as Memory Service
    participant R as LLM Router
    participant L as LLM Provider
    participant D as Database

    U->>F: Type message
    F->>A: POST /chat/message
    A->>A: Validate JWT
    A->>D: Load conversation history
    A->>M: Load relevant memories
    M-->>A: Memory context
    A->>R: Select optimal provider/model
    R->>L: Send prompt with context
    L-->>R: Complete response
    R-->>A: Formatted response
    A->>D: Save user message
    A->>D: Save AI response
    A-->>F: Return response
    F-->>U: Display response
```

### Flow Details

1. User types message and sends
2. Frontend sends authenticated POST to `/chat/message`
3. API validates JWT and loads conversation history from database
4. Memory service retrieves relevant long-term memories
5. LLM Router selects best provider/model based on cost, speed, and capability
6. Provider generates response with full context
7. Response is saved to database with user message
8. Frontend displays the response to the user

## 3. Chat Message Flow (Streaming)

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant R as LLM Router
    participant L as LLM Provider
    participant D as Database

    U->>F: Type message
    F->>A: POST /chat/stream
    A->>A: Validate JWT
    A->>D: Load conversation history
    A->>R: Select provider
    R->>L: Stream request
    loop Token streaming
        L-->>R: Token delta
        R-->>A: Token delta
        A-->>F: SSE event
        F-->>U: Update UI in real-time
    end
    A->>D: Save complete messages
```

### Flow Details

1. User types message and sends
2. Frontend sends authenticated POST to `/chat/stream`
3. API sets up Server-Sent Events (SSE) connection
4. LLM provider streams tokens as they are generated
5. Each token is forwarded to frontend via SSE
6. Frontend updates UI incrementally
7. Once complete, full messages are persisted to database

## 4. Memory Operations Flow

```mermaid
sequenceDiagram
    participant A as API
    participant E as Embedding Service
    participant V as Vector Store
    participant D as Database

    A->>A: Extract key facts from conversation
    A->>E: Generate embedding
    E-->>A: Vector embedding
    A->>V: Store embedding with metadata
    V-->>A: Confirmation

    Note over A,D: Later retrieval

    A->>V: Search similar embeddings
    V-->>A: Relevant memories
    A->>D: Load memory details
    D-->>A: Memory objects
    A->>A: Inject into prompt context
```

### Flow Details

1. After conversation, system extracts key facts
2. Facts are embedded using embedding model (OpenAI/Gemini)
3. Embeddings are stored in vector database (pgvector)
4. On next conversation, system searches for relevant memories
5. Retrieved memories are injected into the prompt context

## 5. File Upload Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant S as Storage
    participant D as Database

    U->>F: Select file
    F->>A: POST /upload (multipart)
    A->>A: Validate file (type, size)
    A->>S: Upload to Supabase Storage
    S-->>A: File URL
    A->>D: Save file metadata
    A->>A: Trigger RAG processing (if enabled)
    A-->>F: Return file info
    F-->>U: Show upload confirmation
```

### Flow Details

1. User selects file via drag-drop or file picker
2. Frontend uploads file as multipart form data
3. API validates file type and size
4. File is uploaded to Supabase Storage
5. Metadata (name, size, type, URL) is saved to database
6. If RAG is enabled, file is processed for embeddings

## 6. Agent Workflow Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as API
    participant W as Workflow Engine
    participant AG as Agent
    participant T as Tool Service
    participant L as LLM Provider

    U->>F: Trigger agent workflow
    F->>A: POST /workflows/execute
    A->>W: Create workflow execution
    W->>AG: Initialize agent
    loop Step execution
        AG->>L: Generate plan/action
        L-->>AG: Decision
        AG->>T: Execute tool if needed
        T-->>AG: Tool result
        AG->>W: Update state
    end
    W-->>A: Workflow complete
    A->>D: Save results
    A-->>F: Return results
    F-->>U: Display workflow output
```

### Flow Details

1. User triggers an agent workflow
2. API creates a workflow execution instance
3. Workflow engine initializes the agent with tools and goals
4. Agent iteratively decides actions and executes tools
5. Each step updates workflow state
6. On completion, results are saved to database
7. Frontend displays the workflow output

## 7. Webhook Delivery Flow

```mermaid
sequenceDiagram
    participant E as Event Source
    participant A as API
    participant Q as Queue
    participant W as Webhook Worker
    participant H as External Webhook

    E->>A: Event occurs
    A->>Q: Enqueue webhook delivery
    Q->>W: Dequeue webhook job
    W->>W: Sign payload
    W->>H: POST webhook
    H-->>W: 200 OK
    W->>D: Mark as delivered
    Note over W,H: On failure
    H-->>W: 500 Error
    W->>Q: Retry with backoff
```

### Flow Details

1. Event occurs in the system (message created, conversation updated, etc.)
2. Webhook delivery job is enqueued
3. Worker picks up job and signs payload with webhook secret
4. Worker POSTs to external webhook URL
5. On success, delivery is marked complete
6. On failure, retry with exponential backoff (max 3 retries)

## 8. Background Job Processing

```mermaid
sequenceDiagram
    participant A as API
    participant Q as Task Queue
    participant W as Workers
    participant D as Database
    participant E as External APIs

    A->>Q: Enqueue job (email, analytics, cleanup)
    Q->>W: Distribute to workers
    loop Job processing
        W->>D: Read job data
        W->>E: Call external API
        E-->>W: Response
        W->>D: Update job status
    end
    W->>Q: Mark complete
```

### Flow Details

1. API enqueues background jobs (emails, analytics, cleanup)
2. Task queue distributes jobs to available workers
3. Workers process jobs independently
4. Job status is updated in database
5. Completed jobs are archived or deleted

## 9. Monitoring Data Flow

```mermaid
sequenceDiagram
    participant A as Application
    participant M as Metrics Exporter
    participant P as Prometheus
    participant G as Grafana
    participant J as Jaeger

    A->>M: Emit metrics (counters, histograms, gauges)
    M->>P: Scrape metrics
    P->>G: Query metrics
    G->>G: Render dashboards

    A->>J: Emit traces
    J->>G: Query traces
    G->>G: Render trace view
```

### Flow Details

1. Application instruments code with metrics and traces
2. Prometheus scrapes metrics endpoint periodically
3. Grafana queries Prometheus for dashboard rendering
4. Jaeger collects distributed traces
5. Grafana queries Jaeger for trace visualization

## 10. Error Handling Flow

```mermaid
graph TD
    A[Request] --> B{Valid?}
    B -->|No| C[400 Bad Request]
    B -->|Yes| D{Authenticated?}
    D -->|No| E[401 Unauthorized]
    D -->|Yes| F{Authorized?}
    F -->|No| G[403 Forbidden]
    F -->|Yes| H{Found?}
    H -->|No| I[404 Not Found]
    H -->|Yes| J{Rate Limited?}
    J -->|Yes| K[429 Too Many Requests]
    J -->|No| L[Process Request]
    L --> M{Success?}
    M -->|No| N[500 Internal Error]
    M -->|Yes| O[200 OK]
```

### Flow Details

1. Request enters the system
2. Validation layer checks request format
3. Authentication layer verifies JWT
4. Authorization layer checks permissions
5. Resource existence is verified
6. Rate limiting is applied
7. Request is processed
8. Response is returned or error is thrown
