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

**`.env` file** (required):
```bash
# Anthropic API
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/fantasy_football
REDIS_URL=redis://redis:6379/0

# Sleeper
SLEEPER_USERNAME=your_username

# Optional
LLM_PROVIDER=anthropic  # or openai, gemini
```

### Deployment Commands

```bash
# Build and start all services
docker-compose up -d

# Rebuild after code changes
docker-compose build backend frontend
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

---

## ⚡ Backend Architecture (FastAPI)

### Why FastAPI?

FastAPI is a modern, high-performance Python web framework chosen for several key reasons:

#### 1. **Async/Await Support (Performance)**
```python
# FastAPI natively supports async operations
@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    async for chunk in chat_agent.stream_response(request.message):
        yield chunk
```

**Benefits**:
- **Non-blocking I/O**: While waiting for Anthropic API responses, the server can handle other requests
- **Concurrent requests**: Handle 100+ simultaneous users without blocking
- **Streaming responses**: Real-time AI responses streamed to frontend
- **Efficient resource usage**: Lower memory footprint than traditional sync frameworks

#### 2. **Automatic API Documentation**
FastAPI auto-generates interactive API docs:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

**Example**:
```python
@router.post("/agents/sit-start", response_model=SitStartResponse)
async def analyze_sit_start(request: SitStartRequest):
    """
    Analyze sit/start decisions for your lineup.

    - **league_id**: Your Sleeper league ID
    - **roster_id**: Your roster ID
    - **week**: NFL week number (1-18)
    """
    # FastAPI automatically validates request and generates docs
```

#### 3. **Type Safety & Validation (Pydantic)**
```python
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    league_id: str
    roster_id: int = Field(..., gt=0)
    week: Optional[int] = Field(None, ge=1, le=18)
    model: str = "claude-sonnet-4-5-20250929"
    temperature: float = Field(0.7, ge=0.0, le=2.0)
```

**Benefits**:
- **Automatic validation**: Invalid requests rejected before reaching your code
- **Type hints**: IDE autocomplete and type checking
- **Clear errors**: Detailed validation error messages
- **Data serialization**: Automatic JSON conversion

#### 4. **Built-in Dependency Injection**
```python
from fastapi import Depends

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/conversations")
async def get_conversations(db: Session = Depends(get_db)):
    # db automatically injected and cleaned up
    return db.query(Conversation).all()
```

#### 5. **WebSocket & Streaming Support**
```python
@router.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    async def event_generator():
        async for event in chat_agent.stream_response(request.message):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Use Cases**:
- Real-time AI responses (typewriter effect)
- Live status updates during analysis
- Progressive data loading

### Backend Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/
│   │   ├── config.py          # Settings & environment variables
│   │   └── database.py        # PostgreSQL connection
│   ├── api/
│   │   ├── agents.py          # AI agent endpoints
│   │   ├── sleeper.py         # Sleeper API proxy
│   │   ├── conversations.py   # Chat history endpoints
│   │   └── settings.py        # App settings endpoints
│   ├── agents/
│   │   ├── chat_agent.py      # Main conversational agent
│   │   ├── sit_start_agent.py # Lineup optimization
│   │   ├── trade_agent.py     # Trade analysis
│   │   ├── waiver_agent.py    # Waiver recommendations
│   │   ├── llm_client.py      # Anthropic API wrapper
│   │   └── state.py           # LangGraph state definitions
│   ├── tools/
│   │   ├── sleeper_client.py  # Sleeper API integration
│   │   ├── projection_tool.py # Player projections
│   │   ├── injury_tool.py     # Injury reports
│   │   ├── matchup_analyzer.py # Matchup analysis
│   │   ├── web_search_tool.py # Web search (Tavily)
│   │   └── reddit_tool.py     # Reddit sentiment
│   ├── models/
│   │   └── conversation.py    # SQLAlchemy models
│   └── utils/
│       ├── bye_weeks.py       # NFL bye week data
│       └── cache.py           # Redis caching utilities
└── requirements.txt
```

### Key Backend Endpoints

#### 1. **Chat Streaming** (`POST /api/v1/agents/chat/stream`)
```python
Request:
{
  "message": "Should I start Josh Allen or Patrick Mahomes?",
  "league_id": "123456789",
  "roster_id": 1,
  "week": 11,
  "thread_id": "uuid-here",  # For conversation continuity
  "model": "claude-sonnet-4-5-20250929",
  "temperature": 0.7
}

Response (Server-Sent Events):
data: {"type": "status", "message": "Analyzing your roster..."}
data: {"type": "status", "message": "Checking player matchups..."}
data: {"type": "content", "content": "Based on the matchups..."}
data: {"type": "done", "thread_id": "uuid-here"}
```

#### 2. **Sit/Start Analysis** (`POST /api/v1/agents/sit-start`)
```python
Request:
{
  "league_id": "123456789",
  "roster_id": 1,
  "week": 11
}

Response:
{
  "total_analyzed": 15,
  "bye_week_players": [
    {
      "player_name": "Jonathan Taylor",
      "team": "IND",
      "is_on_bye": true,
      "recommendation": "SIT",
      "confidence": 100
    }
  ],
  "substitution_suggestions": [
    {
      "player_to_sit": {
        "player_name": "Jonathan Taylor",
        "position": "RB",
        "reason": "BYE WEEK"
      },
      "suggested_replacement": {
        "player_name": "James Conner",
        "position": "RB",
        "projected_points": 14.5
      },
      "priority": "CRITICAL"
    }
  ],
  "start_recommendations": [...],
  "sit_recommendations": [...]
}
```

#### 3. **Trade Analysis** (`POST /api/v1/agents/trade-analysis`)
```python
Request:
{
  "league_id": "123456789",
  "roster_id": 1,
  "my_players": ["player_id_1", "player_id_2"],
  "their_players": ["player_id_3"]
}

Response:
{
  "recommendation": "ACCEPT",
  "confidence": 85,
  "analysis": "This trade improves your RB depth...",
  "value_comparison": {
    "you_give": 42.5,
    "you_get": 48.2,
    "net_gain": 5.7
  }
}
```

#### 4. **Sleeper Data Proxy** (`GET /api/v1/sleeper/*`)
- `GET /sleeper/user/{username}` - User info
- `GET /sleeper/user/{username}/leagues` - User's leagues
- `GET /sleeper/league/{league_id}` - League details
- `GET /sleeper/league/{league_id}/rosters` - All rosters
- `GET /sleeper/players` - All NFL players (cached)

### FastAPI vs Alternatives

| Feature | FastAPI | Flask | Django |
|---------|---------|-------|--------|
| **Async Support** | ✅ Native | ⚠️ Limited | ⚠️ Limited |
| **Performance** | ⚡ Very Fast | 🐌 Slower | 🐌 Slower |
| **Auto Docs** | ✅ Built-in | ❌ Manual | ⚠️ DRF only |
| **Type Safety** | ✅ Pydantic | ❌ No | ⚠️ Partial |
| **Learning Curve** | 📈 Moderate | 📉 Easy | 📈 Steep |
| **Streaming** | ✅ Native | ⚠️ Manual | ⚠️ Manual |
| **Best For** | APIs, AI apps | Simple apps | Full websites |

### Performance Characteristics

**Benchmarks** (requests/second):
- FastAPI: ~20,000 req/s
- Flask: ~3,000 req/s
- Django: ~2,000 req/s

**Why it matters for this app**:
- Multiple concurrent AI agent calls
- Real-time streaming responses
- External API calls (Sleeper, Anthropic, Tavily)
- Database queries
- Redis caching

FastAPI's async nature means while waiting for Anthropic's API response (1-3 seconds), the server can:
- Process other user requests
- Fetch data from Sleeper API
- Query the database
- Update Redis cache

---

## 🔧 Tool Integration Layer

### External APIs & Services

#### 1. **Sleeper API**
- **Purpose**: Fantasy league data
- **Endpoints Used**:
  - User leagues and rosters
  - Player database
  - Matchup information
- **Caching**: 1 hour (players), 5 minutes (leagues)

#### 2. **Anthropic API (Claude)**
- **Purpose**: AI agent intelligence
- **Models Available**:
  - Claude Sonnet 4.5 (latest, most intelligent)
  - Claude 3.5 Sonnet (balanced)
  - Claude 3.5 Haiku (fast, efficient)
- **Rate Limits**: Handled with exponential backoff

#### 3. **Tavily Search API**
- **Purpose**: Real-time web search for player news
- **Use Cases**:
  - Injury updates
  - Breaking news
  - Expert analysis
  - Matchup insights

#### 4. **Reddit API (PRAW)**
- **Purpose**: Community sentiment analysis
- **Subreddits**: r/fantasyfootball
- **Metrics**: Positive/negative mentions, trending players

#### 5. **FantasyPros API** (Optional)
- **Purpose**: Expert consensus rankings
- **Data**: Weekly projections, rankings

---

## 🔐 Security & Best Practices

### API Key Management
- All keys stored in `.env` (never committed)
- Docker secrets for production
- Environment variable validation on startup

### Rate Limiting
- Redis-based rate limiting
- Per-user request throttling
- Exponential backoff for external APIs

### Data Privacy
- User conversations isolated by user_id
- No PII stored
- Conversation deletion supported

### Error Handling
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

---

## 📈 Scalability Considerations

### Current Architecture
- **Single server**: Good for 100-1000 users
- **Vertical scaling**: Increase container resources
- **Caching**: Redis reduces external API calls

### Future Enhancements
- **Horizontal scaling**: Multiple backend containers
- **Load balancer**: Nginx/Traefik
- **Message queue**: Celery for background tasks
- **CDN**: Static asset delivery
- **Database replication**: Read replicas for queries

---

## 🚀 Development Workflow

### Local Development
```bash
# Start services
docker-compose up -d

# Watch logs
docker-compose logs -f backend frontend

# Run tests
docker-compose exec backend pytest

# Access containers
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Hot Reload
- **Frontend**: Next.js dev server auto-reloads
- **Backend**: Uvicorn watches for file changes

### Debugging
- **Frontend**: Chrome DevTools, React DevTools
- **Backend**: Python debugger, FastAPI debug mode
- **Database**: pgAdmin or psql client

---

## 📚 Key Technologies Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 | React framework with SSR |
| **State** | Redux Toolkit | Global state management |
| **Data Fetching** | TanStack Query | Server state & caching |
| **UI** | Tailwind + Radix | Styling & components |
| **Backend** | FastAPI | Async Python web framework |
| **AI** | LangGraph | Agent orchestration |
| **LLM** | Anthropic Claude | AI intelligence |
| **Database** | PostgreSQL | Persistent storage |
| **Cache** | Redis | High-speed caching |
| **Container** | Docker | Deployment & isolation |
| **API Docs** | Swagger/OpenAPI | Auto-generated docs |

---

## 🎓 Learning Resources

- **FastAPI**: https://fastapi.tiangolo.com/
- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **Next.js**: https://nextjs.org/docs
- **Anthropic**: https://docs.anthropic.com/
- **Sleeper API**: https://docs.sleeper.com/


