# Conversation History & State Persistence Implementation Plan

## Overview
Implement persistent conversation history using PostgreSQL and LangGraph checkpointing, with Redis caching for performance optimization.

## Architecture Goals

### PostgreSQL - Long-Term Storage
1. **Conversation History**: Store all user/assistant messages permanently
2. **LangGraph Checkpoints**: Enable pause/resume, state recovery, multi-turn reasoning
3. **User Context**: Track league settings, preferences, past recommendations

### Redis - Performance Cache
1. **Sleeper API Responses**: Cache player data, rosters, matchups (1-hour TTL)
2. **Computed Projections**: Cache expensive calculations (30-min TTL)
3. **Defense Stats**: Cache defensive rankings (daily TTL)
4. **Rate Limiting**: Track API usage per user (future)

### UI/UX Improvements
1. **Conversation List**: Show past conversations in sidebar
2. **Thread Continuity**: Maintain conversation context across sessions
3. **Resume Capability**: Pick up where you left off
4. **Search History**: Find past advice/recommendations

---

## Database Schema Design

### Table: `conversations`
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    league_id VARCHAR(255),
    thread_id VARCHAR(255) UNIQUE NOT NULL,  -- For LangGraph checkpointing
    title VARCHAR(500),  -- Auto-generated from first message
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB  -- Store week, roster_id, tags, etc.
);

CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_thread_id ON conversations(thread_id);
CREATE INDEX idx_conversations_created_at ON conversations(created_at DESC);
```

**Design Decisions:**
- `thread_id`: Unique identifier for LangGraph checkpoint retrieval
- `title`: Generated from first user message (e.g., "Week 10 lineup advice")
- `metadata`: Flexible JSONB for league context, roster_id, week number

### Table: `messages`
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tool_calls JSONB,  -- Store [{name: "search_web", args: {...}, result: {...}}]
    created_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB  -- Store model, tokens, latency, errors
);

CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
```

**Design Decisions:**
- `tool_calls`: Store complete tool execution history for debugging/analytics
- `metadata`: Track performance metrics (tokens used, response time, model version)
- Cascade delete: Deleting conversation removes all messages

### LangGraph Checkpoint Tables (Auto-Created)
```sql
-- Created automatically by AsyncPostgresSaver.setup()
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    value JSONB,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

**What LangGraph Stores:**
- Complete `ChatAgentState` at each node execution
- All messages, tool outputs, roster data, status updates
- Enables `get_state()`, `update_state()`, time-travel debugging

---

## Implementation Phases

### Phase 1: Database Setup (Backend)

#### 1.1 Install Dependencies
```bash
pip install langgraph-checkpoint-postgres alembic sqlalchemy[asyncio] asyncpg
```

#### 1.2 Create SQLAlchemy Models
**File**: `backend/app/models/conversation.py`
- Define `Conversation` and `Message` models
- Add relationships
- Include JSONB fields for metadata

#### 1.3 Create Alembic Migration
```bash
cd backend
alembic revision --autogenerate -m "Add conversation and message tables"
alembic upgrade head
```

#### 1.4 Set Up LangGraph Checkpointer
**File**: `backend/app/agents/langgraph_chat_agent.py`
- Import `AsyncPostgresSaver`
- Initialize checkpointer in `__init__` or startup
- Pass to `workflow.compile(checkpointer=checkpointer)`
- Run `await checkpointer.setup()` to create tables

**Key Code:**
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

class LangGraphChatAgent:
    def __init__(self):
        self.checkpointer = None
        self.graph = None

    async def initialize(self):
        """Call this on app startup"""
        self.checkpointer = await AsyncPostgresSaver.from_conn_string(
            settings.DATABASE_URL
        )
        await self.checkpointer.setup()  # Creates checkpoint tables
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(ChatAgentState)
        # ... add nodes ...
        return workflow.compile(checkpointer=self.checkpointer)
```

---

### Phase 2: Backend API Implementation

#### 2.1 Create Conversation Service Layer
**File**: `backend/app/services/conversation_service.py`

**Functions to implement:**
```python
async def create_conversation(db: AsyncSession, user_id: str, league_id: str, thread_id: str) -> Conversation
async def get_conversation_by_thread_id(db: AsyncSession, thread_id: str) -> Optional[Conversation]
async def get_user_conversations(db: AsyncSession, user_id: str, limit: int = 50) -> List[Conversation]
async def save_message(db: AsyncSession, conversation_id: UUID, role: str, content: str, tool_calls: List = None) -> Message
async def get_conversation_messages(db: AsyncSession, conversation_id: UUID) -> List[Message]
async def update_conversation_title(db: AsyncSession, conversation_id: UUID, title: str)
async def delete_conversation(db: AsyncSession, conversation_id: UUID)
```

**Why a service layer:**
- Separates database logic from API endpoints
- Reusable across multiple endpoints
- Easier to test and maintain
- Handles transaction management

#### 2.2 Update Chat Stream Endpoint
**File**: `backend/app/api/agents.py`

**Changes:**
1. Accept `thread_id` in request (generate if not provided)
2. Get or create conversation record
3. Save user message before streaming
4. Collect assistant response during streaming
5. Save assistant message after streaming
6. Auto-generate conversation title from first message

**Request Schema Update:**
```python
class ChatRequest(BaseModel):
    message: str
    league_id: str
    roster_id: int
    week: int
    thread_id: Optional[str] = None  # NEW
    user_id: Optional[str] = "default"  # NEW - will come from auth later
```

**Response includes:**
```json
{
    "type": "metadata",
    "thread_id": "uuid-here",
    "conversation_id": "uuid-here"
}
```

#### 2.3 Create Conversation History Endpoints
**File**: `backend/app/api/conversations.py` (NEW)

**Endpoints:**
```python
@router.get("/conversations")
async def list_conversations(
    user_id: str = "default",
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> List[ConversationResponse]:
    """Get user's conversation history, ordered by most recent"""

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> ConversationDetailResponse:
    """Get full conversation with all messages"""

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all messages"""

@router.get("/conversations/{thread_id}/state")
async def get_conversation_state(
    thread_id: str,
    agent: LangGraphChatAgent = Depends(get_agent)
) -> Dict:
    """Get LangGraph checkpoint state for debugging"""
```

**Response Schemas:**
```python
class ConversationResponse(BaseModel):
    id: UUID
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_preview: str  # First 100 chars

class ConversationDetailResponse(BaseModel):
    id: UUID
    thread_id: str
    title: str
    created_at: datetime
    messages: List[MessageResponse]

class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    tool_calls: Optional[List[Dict]]
    created_at: datetime
```

#### 2.4 Integrate Checkpointing in Agent
**File**: `backend/app/agents/langgraph_chat_agent.py`

**Key Changes:**
```python
async def chat_stream(
    self,
    user_message: str,
    thread_id: str,  # REQUIRED now
    league_id: str,
    roster_id: int,
    week: int,
    conversation_history: Optional[List] = None  # Can be removed - checkpointer handles this
):
    """Stream chat response with checkpointing"""

    # Configuration for checkpointing
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": ""  # Optional namespace
        }
    }

    # Check if conversation exists in checkpointer
    state = await self.graph.aget_state(config)

    # If no prior state, initialize fresh
    if not state.values.get("messages"):
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "user_id": "default",
            "league_id": league_id,
            "roster_id": roster_id,
            "week": week,
            # ... rest of state
        }
    else:
        # Append to existing conversation
        initial_state = state.values
        initial_state["messages"].append(HumanMessage(content=user_message))

    # Stream with checkpointing enabled
    async for event in self.graph.astream(initial_state, config=config):
        yield event
```

**Benefits:**
- No need to pass `conversation_history` - checkpointer retrieves it
- Automatic state persistence at each node
- Can resume mid-execution if request fails

---

### Phase 3: Redis Caching Strategy

#### 3.1 Enhanced Redis Service
**File**: `backend/app/services/redis_cache_service.py` (NEW)

**Caching Strategy:**
```python
class CacheKeyBuilder:
    """Centralized cache key management"""

    @staticmethod
    def sleeper_players(league_id: str) -> str:
        return f"sleeper:players:{league_id}"

    @staticmethod
    def sleeper_roster(league_id: str, roster_id: int, week: int) -> str:
        return f"sleeper:roster:{league_id}:{roster_id}:{week}"

    @staticmethod
    def player_projection(player_id: str, week: int) -> str:
        return f"projection:{player_id}:{week}"

    @staticmethod
    def defense_stats(week: int) -> str:
        return f"defense:stats:{week}"

    @staticmethod
    def matchup_analysis(player_id: str, week: int) -> str:
        return f"matchup:{player_id}:{week}"

class CacheTTL:
    """Time-to-live constants"""
    SLEEPER_PLAYERS = 3600  # 1 hour
    SLEEPER_ROSTER = 1800   # 30 min
    PLAYER_PROJECTION = 1800  # 30 min
    DEFENSE_STATS = 86400   # 24 hours
    MATCHUP_ANALYSIS = 1800  # 30 min
```

#### 3.2 Cache Wrapper Decorator
```python
from functools import wraps

def cache_result(key_builder, ttl: int):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            cache_key = key_builder(*args, **kwargs)

            # Try cache first
            cached = await redis_client.get(cache_key)
            if cached:
                logger.info(f"Cache HIT: {cache_key}")
                return cached

            # Execute function
            logger.info(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            await redis_client.set(cache_key, result, expire=ttl)
            return result

        return wrapper
    return decorator
```

#### 3.3 Apply Caching to Tools
**File**: `backend/app/agents/tools.py`

**Example:**
```python
@cache_result(
    lambda player_id, week: CacheKeyBuilder.player_projection(player_id, week),
    CacheTTL.PLAYER_PROJECTION
)
async def get_player_projection(player_id: str, week: int) -> Dict:
    """Fetch player projection with caching"""
    # Expensive computation here
    projection = await compute_projection(player_id, week)
    return projection

@cache_result(
    lambda league_id: CacheKeyBuilder.sleeper_players(league_id),
    CacheTTL.SLEEPER_PLAYERS
)
async def fetch_sleeper_players(league_id: str) -> Dict:
    """Fetch Sleeper players with caching"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{SLEEPER_API}/players/nfl")
        return response.json()
```

#### 3.4 Cache Invalidation Strategy
**File**: `backend/app/services/cache_invalidation.py` (NEW)

**When to invalidate:**
- User makes roster change → Clear roster cache
- New injury report → Clear affected player projections
- Week changes → Clear all week-specific caches

```python
async def invalidate_roster_cache(league_id: str, roster_id: int):
    """Clear roster cache after changes"""
    pattern = f"sleeper:roster:{league_id}:{roster_id}:*"
    await redis_client.delete_pattern(pattern)

async def invalidate_player_cache(player_id: str):
    """Clear all caches for a player"""
    patterns = [
        f"projection:{player_id}:*",
        f"matchup:{player_id}:*"
    ]
    for pattern in patterns:
        await redis_client.delete_pattern(pattern)
```

---

### Phase 4: Frontend Implementation

#### 4.1 Update API Client
**File**: `frontend/src/services/api.ts` (or similar)

**Changes:**
```typescript
interface ChatRequest {
    message: string;
    league_id: string;
    roster_id: number;
    week: number;
    thread_id?: string;  // NEW
    user_id?: string;    // NEW
}

interface ChatStreamEvent {
    type: 'status' | 'response' | 'metadata';
    message?: string;
    thread_id?: string;
    conversation_id?: string;
}

// NEW: Conversation history API
export async function getConversations(): Promise<Conversation[]> {
    const response = await fetch('/api/conversations');
    return response.json();
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
    const response = await fetch(`/api/conversations/${conversationId}`);
    return response.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
    await fetch(`/api/conversations/${conversationId}`, { method: 'DELETE' });
}
```

#### 4.2 Add Conversation Context
**File**: `frontend/src/contexts/ConversationContext.tsx` (NEW)

```typescript
interface ConversationContextType {
    currentThreadId: string | null;
    conversations: Conversation[];
    loadConversations: () => Promise<void>;
    selectConversation: (threadId: string) => void;
    startNewConversation: () => void;
    deleteConversation: (conversationId: string) => Promise<void>;
}

export const ConversationProvider: React.FC = ({ children }) => {
    const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
    const [conversations, setConversations] = useState<Conversation[]>([]);

    const loadConversations = async () => {
        const data = await getConversations();
        setConversations(data);
    };

    const startNewConversation = () => {
        setCurrentThreadId(null);  // Will generate new thread_id on first message
    };

    // ... implement other functions

    return (
        <ConversationContext.Provider value={{ ... }}>
            {children}
        </ConversationContext.Provider>
    );
};
```

#### 4.3 Create Conversation Sidebar
**File**: `frontend/src/components/ConversationSidebar.tsx` (NEW)

**Features:**
- List of past conversations
- "New Conversation" button
- Search/filter conversations
- Delete conversation (with confirmation)
- Show conversation title + preview + date

**Layout:**
```
┌─────────────────────────┐
│ [+ New Conversation]    │
├─────────────────────────┤
│ 🔍 Search...            │
├─────────────────────────┤
│ Today                   │
│ ├─ Week 10 lineup ⭐    │ ← Selected
│ └─ Trade analysis       │
├─────────────────────────┤
│ Yesterday               │
│ ├─ Waiver wire help     │
│ └─ Start/sit advice     │
├─────────────────────────┤
│ This Week               │
│ └─ Week 9 recap         │
└─────────────────────────┘
```

#### 4.4 Update Chat Component
**File**: `frontend/src/components/Chat.tsx` (or main chat component)

**Changes:**
1. Use `currentThreadId` from context
2. On first message in new conversation, capture returned `thread_id`
3. Display conversation title at top
4. Show loading state when loading historical conversation
5. Remove client-side `conversation_history` state (backend handles via checkpointing)

**Simplified Flow:**
```typescript
const { currentThreadId, selectConversation } = useConversation();
const [messages, setMessages] = useState<Message[]>([]);

const sendMessage = async (message: string) => {
    const eventSource = await chatStream({
        message,
        league_id: selectedLeague,
        roster_id: selectedRoster,
        week: currentWeek,
        thread_id: currentThreadId  // Will be null for new conversations
    });

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === 'metadata') {
            // First message response - save thread_id
            if (!currentThreadId) {
                selectConversation(data.thread_id);
            }
        }
        // ... handle other event types
    };
};

// Load historical conversation
useEffect(() => {
    if (currentThreadId) {
        loadConversationHistory(currentThreadId);
    }
}, [currentThreadId]);
```

#### 4.5 Add Conversation Header
**Component**: Show conversation title with edit/delete actions
```tsx
<div className="conversation-header">
    <h2>{conversation?.title || "New Conversation"}</h2>
    <div className="actions">
        <button onClick={handleRename}>Rename</button>
        <button onClick={handleDelete}>Delete</button>
    </div>
</div>
```

---

### Phase 5: Testing & Validation

#### 5.1 Backend Tests
**File**: `backend/tests/test_conversation_service.py`

**Test Cases:**
- Create conversation
- Save messages
- Retrieve conversation history
- Delete conversation (cascades to messages)
- Generate conversation title
- Handle duplicate thread_id

#### 5.2 Integration Tests
**File**: `backend/tests/test_chat_persistence.py`

**Test Cases:**
- Send message → verify saved to DB
- Start new conversation → verify new thread_id
- Continue existing conversation → verify thread_id preserved
- Checkpoint state recovery → send message, crash, resume
- Redis cache hit/miss behavior

#### 5.3 Frontend Tests
**Test Cases:**
- Load conversation list
- Select conversation → loads messages
- Start new conversation → generates thread_id
- Delete conversation → removes from list
- Search conversations

#### 5.4 Manual Testing Checklist
```
[ ] Send first message in new conversation → Creates conversation record
[ ] Send follow-up message → Appends to same conversation
[ ] Refresh page → Can resume conversation from history
[ ] Delete conversation → Removes from UI and DB
[ ] Cache behavior → Second request for same data is faster
[ ] Multiple conversations → Can switch between them
[ ] Conversation titles → Auto-generated from first message
[ ] Error handling → Graceful failure if DB is down
```

---

## Redis Caching Matrix

| Data Source | Cache Key Pattern | TTL | Invalidation Trigger |
|-------------|-------------------|-----|----------------------|
| Sleeper Players | `sleeper:players:{league_id}` | 1 hour | Manual/cron |
| Sleeper Roster | `sleeper:roster:{league_id}:{roster_id}:{week}` | 30 min | Roster change |
| Player Projection | `projection:{player_id}:{week}` | 30 min | New data ingestion |
| Defense Stats | `defense:stats:{week}` | 24 hours | Weekly update |
| Matchup Analysis | `matchup:{player_id}:{week}` | 30 min | Injury/status change |

---

## Migration Strategy

### Backward Compatibility
1. Keep existing `/chat/stream` endpoint working without `thread_id` (auto-generate)
2. Frontend can gradually adopt conversation history UI
3. Existing users won't see past conversations (started before persistence)

### Rollout Plan
1. **Phase 1**: Deploy backend with conversation persistence (no UI changes yet)
2. **Phase 2**: Add conversation sidebar to UI (optional feature)
3. **Phase 3**: Make conversation history default experience
4. **Phase 4**: Add advanced features (search, export, sharing)

---

## Performance Considerations

### Database Optimization
- Index on `(user_id, created_at DESC)` for conversation list queries
- Partition messages table by month for large-scale deployments
- Use connection pooling (already configured in database.py)

### Redis Optimization
- Set max memory policy: `maxmemory-policy allkeys-lru`
- Monitor cache hit rate: `INFO stats` → `keyspace_hits / (keyspace_hits + keyspace_misses)`
- Use pipeline for bulk operations

### LangGraph Checkpointing
- Checkpoints can grow large → consider retention policy (delete checkpoints >30 days old)
- Monitor checkpoint table size
- Use `checkpoint_ns` to organize by feature if needed

---

## Security Considerations

### Current State (Pre-Auth)
- `user_id = "default"` for all users
- No authentication required
- Conversations accessible to anyone with thread_id

### Future (With Auth)
- Add user authentication (JWT, OAuth, etc.)
- Verify conversation ownership before access
- Add row-level security in PostgreSQL
- Encrypt sensitive metadata

### API Endpoint Protection
```python
@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),  # Future
    db: AsyncSession = Depends(get_db)
):
    # Only return user's own conversations
    return await conversation_service.get_user_conversations(db, current_user.id)
```

---

## Monitoring & Observability

### Metrics to Track
1. **Conversation Stats**
   - Average messages per conversation
   - Conversation duration
   - Active conversations per day

2. **Cache Performance**
   - Redis hit rate
   - Average cache retrieval time
   - Most frequently cached keys

3. **Database Performance**
   - Query latency
   - Connection pool usage
   - Checkpoint table size growth

### Logging Strategy
```python
logger.info("Conversation created", extra={
    "conversation_id": str(conversation.id),
    "thread_id": conversation.thread_id,
    "user_id": user_id
})

logger.info("Cache hit", extra={
    "cache_key": cache_key,
    "ttl_remaining": ttl
})
```

---

## Error Handling

### Database Failures
```python
try:
    conversation = await create_conversation(db, ...)
except IntegrityError:
    # Duplicate thread_id - retrieve existing
    conversation = await get_conversation_by_thread_id(db, thread_id)
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=503, detail="Database unavailable")
```

### Redis Failures
```python
try:
    cached = await redis_client.get(cache_key)
except RedisError:
    logger.warning(f"Redis unavailable, bypassing cache")
    cached = None  # Fallback to database/API
```

### Checkpoint Failures
```python
try:
    state = await graph.aget_state(config)
except CheckpointError:
    logger.error("Failed to retrieve checkpoint, starting fresh")
    state = None
    # Initialize new conversation state
```

---

## Future Enhancements

### Phase 2 Features
1. **Conversation Branching**: Fork a conversation at any point
2. **Export Conversations**: Download as PDF/JSON
3. **Share Conversations**: Generate shareable links
4. **Conversation Tags**: Organize by topic (trades, lineup, waivers)
5. **Search**: Full-text search across all conversations

### Phase 3 Features
1. **Multi-League Context**: Switch between leagues mid-conversation
2. **Voice Input**: Speak questions instead of typing
3. **Scheduled Advice**: "Remind me every Tuesday to check waivers"
4. **Conversation Analytics**: "You followed 80% of my start/sit advice"

---

## Success Metrics

### Technical Metrics
- [ ] All conversations persisted to database (100% success rate)
- [ ] Cache hit rate >80% for Sleeper API calls
- [ ] Average response time <2s with caching
- [ ] Zero data loss on server restart (checkpoint recovery)
- [ ] Database query latency <100ms for conversation retrieval

### User Experience Metrics
- [ ] Users can resume conversations across sessions
- [ ] Conversation history loads in <500ms
- [ ] No duplicate conversations created
- [ ] Historical conversations display correctly
- [ ] Delete conversation removes all data

---

## File Structure After Implementation

```
backend/
├── app/
│   ├── models/
│   │   ├── __init__.py
│   │   └── conversation.py          # NEW: SQLAlchemy models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── conversation_service.py  # NEW: Conversation CRUD
│   │   ├── redis_cache_service.py   # NEW: Enhanced caching
│   │   └── cache_invalidation.py    # NEW: Cache management
│   ├── api/
│   │   ├── agents.py                # MODIFIED: Add thread_id support
│   │   └── conversations.py         # NEW: Conversation endpoints
│   ├── agents/
│   │   ├── langgraph_chat_agent.py  # MODIFIED: Add checkpointing
│   │   ├── state.py                 # Existing
│   │   └── tools.py                 # MODIFIED: Add caching decorators
│   └── core/
│       ├── database.py              # Existing
│       └── redis_client.py          # Existing
├── alembic/
│   └── versions/
│       └── xxxx_add_conversation_tables.py  # NEW: Migration
└── tests/
    ├── test_conversation_service.py  # NEW
    └── test_chat_persistence.py      # NEW

frontend/
├── src/
│   ├── components/
│   │   ├── ConversationSidebar.tsx   # NEW
│   │   ├── ConversationHeader.tsx    # NEW
│   │   └── Chat.tsx                  # MODIFIED
│   ├── contexts/
│   │   └── ConversationContext.tsx   # NEW
│   ├── services/
│   │   └── api.ts                    # MODIFIED: Add conversation APIs
│   └── types/
│       └── conversation.ts           # NEW: TypeScript types
```

---

## Estimated Implementation Time

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Database Setup | Models, migrations, checkpointer | 4-6 hours |
| Phase 2: Backend API | Service layer, endpoints, integration | 6-8 hours |
| Phase 3: Redis Caching | Enhanced caching, decorators | 3-4 hours |
| Phase 4: Frontend | Sidebar, context, API client | 6-8 hours |
| Phase 5: Testing | Unit tests, integration tests | 4-6 hours |
| **Total** | | **23-32 hours** |

---

## Next Steps

1. Review this implementation plan
2. Approve architecture decisions
3. Begin Phase 1: Database Setup
4. Iterate on each phase with testing
5. Deploy incrementally to production
