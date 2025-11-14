# Fantasy Football AI Manager - Architecture Documentation

## 🏗️ System Overview

The Fantasy Football AI Manager is a full-stack application that uses AI agents to provide intelligent fantasy football insights, lineup optimization, trade analysis, and player recommendations. The system leverages Claude AI models through Anthropic's API to deliver contextual, data-driven advice.

---

## 📊 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    (Next.js 14 Frontend)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    FastAPI Backend                               │
│                  (Python 3.11 + LangGraph)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AI Agent Orchestration Layer                 │  │
│  │  • Chat Agent      • Sit/Start Agent                      │  │
│  │  • Trade Agent     • Waiver Agent                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Tool Integration Layer                  │  │
│  │  • Sleeper API     • Projection Tools                     │  │
│  │  • Web Search      • Reddit Sentiment                     │  │
│  │  • Injury Reports  • Matchup Analysis                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬──────────────────────┬──────────────────────────────┘
             │                      │
    ┌────────▼────────┐    ┌───────▼────────┐
    │   PostgreSQL    │    │     Redis      │
    │   (Persistent)  │    │    (Cache)     │
    └─────────────────┘    └────────────────┘
             │
    ┌────────▼────────┐
    │  Anthropic API  │
    │  (Claude AI)    │
    └─────────────────┘
```

---

## 🎯 Agent Orchestration

### LangGraph-Based Multi-Agent System

The application uses **LangGraph** to orchestrate multiple specialized AI agents that work together to provide comprehensive fantasy football insights.

#### Agent Types

1. **Chat Agent** (`chat_agent.py`)
   - **Purpose**: Main conversational interface
   - **Capabilities**: 
     - Natural language understanding
     - Context-aware responses
     - Tool delegation to specialized agents
     - Conversation history management
   - **Model**: Claude Sonnet 4.5 (configurable)

2. **Sit/Start Agent** (`sit_start_agent.py`)
   - **Purpose**: Lineup optimization and player recommendations
   - **Capabilities**:
     - Player matchup analysis
     - Injury status checking
     - **Bye week detection** (NEW!)
     - **Automatic substitution suggestions** (NEW!)
     - Projection-based recommendations
   - **Data Sources**: Sleeper API, injury reports, projections, Reddit sentiment

3. **Trade Analysis Agent** (`trade_agent.py`)
   - **Purpose**: Evaluate trade proposals
   - **Capabilities**:
     - Multi-player trade evaluation
     - Roster impact analysis
     - Value comparison
     - Long-term vs short-term analysis

4. **Waiver Wire Agent** (`waiver_agent.py`)
   - **Purpose**: Identify waiver wire opportunities
   - **Capabilities**:
     - Available player analysis
     - Roster need identification
     - Breakout player detection
     - Drop candidate suggestions

#### Agent Communication Flow

```
User Query
    │
    ▼
Chat Agent (Router)
    │
    ├──► Sit/Start Agent ──► Tools (Sleeper, Projections, Injuries)
    │                              │
    │                              ▼
    │                         Matchup Analyzer
    │                              │
    │                              ▼
    │                         Bye Week Checker
    │                              │
    │                              ▼
    │                         Substitution Engine
    │
    ├──► Trade Agent ──────► Tools (Player Stats, Projections)
    │
    └──► Waiver Agent ─────► Tools (Available Players, Trends)
```

### State Management

Each agent maintains state through LangGraph's `AgentState`:

```python
class AgentState(TypedDict):
    messages: List[BaseMessage]
    roster_data: Dict[str, Any]
    players_data: Dict[str, Any]
    league_data: Dict[str, Any]
    week: int
    analysis_results: Dict[str, Any]
```

---

## 🎨 Frontend Architecture

### Technology Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **State Management**: Redux Toolkit
- **Data Fetching**: TanStack Query (React Query)
- **UI Components**: Radix UI + Tailwind CSS
- **Markdown Rendering**: react-markdown + remark-gfm

### Key Features

#### 1. **Real-time Chat Interface**
- Streaming responses from AI agents
- Typewriter effect for status updates
- Markdown-formatted responses with:
  - Headers, lists, tables
  - Code blocks
  - Bold/italic text
  - Links and blockquotes

#### 2. **Conversation Management**
- Persistent conversation history
- Thread-based organization
- Conversation sidebar with search
- Title auto-generation

#### 3. **League Integration**
- Sleeper API integration
- Real-time roster data
- Player projections
- Matchup information

#### 4. **Settings Management**
- Model selection (Claude Sonnet 4.5, 3.5 Sonnet, 3.5 Haiku)
- Temperature control
- Provider selection (Anthropic, OpenAI, Gemini)
- Sleeper username configuration

### Component Structure

```
frontend/
├── app/
│   ├── page.tsx                    # Home page
│   ├── settings/page.tsx           # Settings page
│   └── league/[leagueId]/
│       ├── page.tsx                # League overview
│       └── lineup/page.tsx         # Lineup analyzer
├── components/
│   ├── chat-interface.tsx          # Main chat UI
│   ├── chat-fullscreen-modal.tsx   # Fullscreen chat
│   ├── markdown-renderer.tsx       # Markdown formatting
│   ├── conversation-sidebar.tsx    # Conversation history
│   └── ui/                         # Reusable UI components
├── store/
│   └── slices/
│       ├── conversationSlice.ts    # Conversation state
│       └── settingsSlice.ts        # App settings
└── lib/
    └── api-client.ts               # API communication
```

---

## 🗄️ Database Architecture

### PostgreSQL (Primary Database)

**Purpose**: Persistent storage for conversations and user data

#### Schema

```sql
-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    league_id VARCHAR(255),
    roster_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
```

#### Key Features
- **Conversation persistence**: All chat history stored
- **User isolation**: Conversations scoped by user_id
- **Cascade deletes**: Messages deleted when conversation is deleted
- **Optimized queries**: Indexes on frequently queried columns

### Redis (Cache Layer)

**Purpose**: High-speed caching for frequently accessed data

#### Use Cases
1. **Player Data Cache**
   - TTL: 1 hour
   - Key pattern: `players:all`
   - Reduces Sleeper API calls

2. **League Data Cache**
   - TTL: 5 minutes
   - Key pattern: `league:{league_id}`
   - Fresh data for active leagues

3. **Projection Cache**
   - TTL: 1 hour
   - Key pattern: `projection:{player_id}:{week}`
   - Expensive calculations cached

4. **Session Data**
   - TTL: 24 hours
   - Key pattern: `session:{user_id}`
   - User preferences and state

---

## 🐳 Docker Architecture

### Multi-Container Setup

The application runs as 4 interconnected Docker containers:

```yaml
services:
  frontend:
    - Next.js development server
    - Port: 3000
    - Hot reload enabled
    
  backend:
    - FastAPI + Uvicorn
    - Port: 8000
    - Depends on: postgres, redis
    
  postgres:
    - PostgreSQL 15
    - Port: 5432
    - Volume: postgres_data
    
  redis:
    - Redis 7-alpine
    - Port: 6379
    - Volume: redis_data
```

### Container Communication

```
┌─────────────┐
│  Frontend   │ ──HTTP──► Backend (http://backend:8000)
│  (Next.js)  │
└─────────────┘
       │
       │ (User Access)
       ▼
   localhost:3000

┌─────────────┐
│   Backend   │ ──SQL──► PostgreSQL (postgres:5432)
│  (FastAPI)  │ ──TCP──► Redis (redis:6379)
└─────────────┘
       │
       │ (API Access)
       ▼
   localhost:8000
```

### Volume Management

**Persistent Volumes**:
- `postgres_data`: Database files
- `redis_data`: Redis persistence (optional)

**Benefits**:
- Data survives container restarts
- Easy backup and restore
- Development/production parity

### Environment Configuration


