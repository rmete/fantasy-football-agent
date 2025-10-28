# Implementation Prompt: Conversation History & State Persistence

## Objective
Implement persistent conversation history using PostgreSQL for long-term storage, LangGraph checkpointing for state management, and Redis for performance optimization. Update the UI to display conversation history and enable users to resume past conversations.

---

## Prerequisites

Before starting, verify the following:
- [ ] PostgreSQL database is running and accessible
- [ ] Redis is running and accessible
- [ ] Current codebase is at `/Users/rileymete/Desktop/Projects/fantasy-football-agent`
- [ ] Backend virtual environment is activated
- [ ] All existing tests are passing
- [ ] Git branch created: `git checkout -b feature/conversation-persistence`

---

## PHASE 1: DATABASE SETUP

### Task 1.1: Install Required Dependencies

**What to do:**
1. Navigate to the backend directory
2. Install the LangGraph PostgreSQL checkpointer and ensure all database dependencies are present
3. Verify installation

**Commands:**
```bash
cd backend
source venv/bin/activate  # or your virtualenv activation command
pip install langgraph-checkpoint-postgres
pip install alembic sqlalchemy[asyncio] asyncpg  # Likely already installed
pip freeze > requirements.txt
```

**Verification:**
```bash
python -c "from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver; print('Success')"
```

**Expected outcome:** No import errors, "Success" printed

---

### Task 1.2: Create SQLAlchemy Models for Conversations

**What to do:**
Create a new file `backend/app/models/conversation.py` with SQLAlchemy models for `Conversation` and `Message` tables.

**File to create:** `backend/app/models/conversation.py`

**Code to write:**
```python
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Conversation(Base):
    """Represents a conversation thread between user and agent"""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    league_id = Column(String(255), nullable=True)
    thread_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    metadata = Column(JSONB, nullable=True, default={})

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, thread_id={self.thread_id}, title={self.title})>"


class Message(Base):
    """Represents a single message in a conversation"""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(JSONB, nullable=True)
    metadata = Column(JSONB, nullable=True, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Add constraint for role
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="check_message_role"),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"
```

**Update:** `backend/app/models/__init__.py`

Add these imports:
```python
from app.models.conversation import Conversation, Message

__all__ = ["Conversation", "Message"]
```

**Verification:**
```bash
python -c "from app.models.conversation import Conversation, Message; print('Models imported successfully')"
```

---

### Task 1.3: Create Alembic Migration

**What to do:**
Generate an Alembic migration to create the `conversations` and `messages` tables.

**Prerequisites:**
- Alembic is already configured in the project
- Check if `backend/alembic.ini` and `backend/alembic/` exist

**Commands:**
```bash
cd backend

# Check current migration status
alembic current

# Generate migration
alembic revision --autogenerate -m "Add conversations and messages tables"

# Review the generated migration file in backend/alembic/versions/
# Look for the latest file with timestamp prefix

# Apply migration
alembic upgrade head
```

**Verification:**
Connect to PostgreSQL and verify tables exist:
```bash
# If using psql
psql -d your_database_name -c "\dt conversations"
psql -d your_database_name -c "\dt messages"
```

Or using Python:
```python
from app.core.database import engine
from sqlalchemy import inspect

async def check_tables():
    async with engine.begin() as conn:
        inspector = inspect(conn)
        tables = await inspector.get_table_names()
        print("conversations" in tables, "messages" in tables)
```

**Expected outcome:** Both tables exist with proper columns and indexes

---

### Task 1.4: Set Up LangGraph PostgreSQL Checkpointer

**What to do:**
Modify `backend/app/agents/langgraph_chat_agent.py` to initialize and use the PostgreSQL checkpointer.

**File to modify:** `backend/app/agents/langgraph_chat_agent.py`

**Step 1: Add imports**
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
```

**Step 2: Modify the class constructor**

Find the `__init__` method and update it:
```python
class LangGraphChatAgent:
    def __init__(self):
        self.llm = None
        self.graph = None
        self.checkpointer = None  # NEW

    async def initialize(self):
        """Initialize async components - call this on app startup"""
        logger.info("Initializing LangGraph chat agent with PostgreSQL checkpointing...")

        # Initialize checkpointer
        self.checkpointer = AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL)
        await self.checkpointer.setup()  # Creates checkpoint tables
        logger.info("Checkpointer initialized and tables created")

        # Build graph with checkpointer
        self.graph = self._build_graph()
        logger.info("LangGraph agent initialized successfully")
```

**Step 3: Modify `_build_graph` method**

Find the `_build_graph` method and update the final return statement:
```python
def _build_graph(self) -> StateGraph:
    """Build the LangGraph agent workflow"""
    workflow = StateGraph(ChatAgentState)

    # Add nodes
    workflow.add_node("fetch_context", self._fetch_context_node)
    workflow.add_node("agent", self._agent_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))

    # Set entry point
    workflow.set_entry_point("fetch_context")

    # Add edges
    workflow.add_edge("fetch_context", "agent")
    workflow.add_conditional_edges(
        "agent",
        self._should_continue,
        {
            "continue": "tools",
            "end": END
        }
    )
    workflow.add_edge("tools", "agent")

    # Compile with checkpointer - MODIFIED
    return workflow.compile(checkpointer=self.checkpointer)
```

**Step 4: Update app startup**

Find where `LangGraphChatAgent` is instantiated (likely in `backend/app/main.py` or `backend/app/api/agents.py`) and ensure `initialize()` is called.

**File to check:** `backend/app/main.py`

Add startup event:
```python
from contextlib import asynccontextmanager
from app.agents.langgraph_chat_agent import LangGraphChatAgent

# Global agent instance
chat_agent = LangGraphChatAgent()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await chat_agent.initialize()
    yield
    # Shutdown
    if chat_agent.checkpointer:
        await chat_agent.checkpointer.conn.close()

app = FastAPI(lifespan=lifespan)
```

**Verification:**
```bash
# Start the backend server
cd backend
python -m uvicorn app.main:app --reload

# Check logs for:
# "Checkpointer initialized and tables created"
# "LangGraph agent initialized successfully"

# Verify checkpoint tables exist
psql -d your_database_name -c "\dt checkpoint*"
# Should see: checkpoints, checkpoint_writes
```

---

## PHASE 2: BACKEND SERVICE LAYER

### Task 2.1: Create Conversation Service

**What to do:**
Create a service layer to handle all conversation-related database operations.

**File to create:** `backend/app/services/conversation_service.py`

**Code to write:**
```python
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
import logging

logger = logging.getLogger(__name__)


async def create_conversation(
    db: AsyncSession,
    user_id: str,
    league_id: str,
    thread_id: str,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Conversation:
    """Create a new conversation"""
    conversation = Conversation(
        user_id=user_id,
        league_id=league_id,
        thread_id=thread_id,
        title=title or "New Conversation",
        metadata=metadata or {}
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    logger.info(f"Created conversation {conversation.id} with thread_id {thread_id}")
    return conversation


async def get_conversation_by_thread_id(
    db: AsyncSession,
    thread_id: str
) -> Optional[Conversation]:
    """Get conversation by thread_id"""
    result = await db.execute(
        select(Conversation).where(Conversation.thread_id == thread_id)
    )
    return result.scalar_one_or_none()


async def get_conversation_by_id(
    db: AsyncSession,
    conversation_id: UUID
) -> Optional[Conversation]:
    """Get conversation by ID with messages"""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def get_user_conversations(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Conversation]:
    """Get user's conversations, ordered by most recent"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def save_message(
    db: AsyncSession,
    conversation_id: UUID,
    role: str,
    content: str,
    tool_calls: Optional[List[Dict]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Message:
    """Save a message to a conversation"""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        metadata=metadata or {}
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    logger.info(f"Saved {role} message to conversation {conversation_id}")
    return message


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: UUID
) -> List[Message]:
    """Get all messages for a conversation"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


async def update_conversation_title(
    db: AsyncSession,
    conversation_id: UUID,
    title: str
) -> Optional[Conversation]:
    """Update conversation title"""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.title = title
        await db.commit()
        await db.refresh(conversation)
        logger.info(f"Updated conversation {conversation_id} title to: {title}")
    return conversation


async def delete_conversation(
    db: AsyncSession,
    conversation_id: UUID
) -> bool:
    """Delete a conversation (cascades to messages)"""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        await db.delete(conversation)
        await db.commit()
        logger.info(f"Deleted conversation {conversation_id}")
        return True
    return False


async def get_conversation_count(
    db: AsyncSession,
    user_id: str
) -> int:
    """Get total conversation count for a user"""
    result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    )
    return result.scalar() or 0


def generate_conversation_title(first_message: str, max_length: int = 50) -> str:
    """Generate a conversation title from the first message"""
    # Clean up the message
    title = first_message.strip()

    # Remove common prefixes
    prefixes = ["help me", "can you", "i need", "what should", "who should"]
    for prefix in prefixes:
        if title.lower().startswith(prefix):
            title = title[len(prefix):].strip()

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    # Truncate if too long
    if len(title) > max_length:
        title = title[:max_length].rsplit(' ', 1)[0] + "..."

    return title or "New Conversation"
```

**Verification:**
```bash
python -c "from app.services.conversation_service import create_conversation; print('Service imported successfully')"
```

---

### Task 2.2: Update Chat Stream Endpoint with Persistence

**What to do:**
Modify the chat stream endpoint to save conversations and messages to the database, and use LangGraph checkpointing with thread_id.

**File to modify:** `backend/app/api/agents.py`

**Step 1: Update imports**
```python
from uuid import uuid4
from app.models.conversation import Conversation, Message
from app.services import conversation_service
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
```

**Step 2: Update ChatRequest schema**
```python
from pydantic import BaseModel, Field
from typing import Optional, List

class ChatRequest(BaseModel):
    message: str
    league_id: str
    roster_id: int
    week: int
    thread_id: Optional[str] = None  # NEW
    user_id: Optional[str] = "default"  # NEW - will come from auth later
```

**Step 3: Modify the chat_stream endpoint**

Find the `/chat/stream` endpoint and replace it with:

```python
@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """Stream chat responses with conversation persistence"""

    # Generate thread_id if not provided
    thread_id = request.thread_id or str(uuid4())
    is_new_conversation = request.thread_id is None

    # Get or create conversation
    conversation = await conversation_service.get_conversation_by_thread_id(db, thread_id)

    if not conversation:
        # Create new conversation
        conversation = await conversation_service.create_conversation(
            db=db,
            user_id=request.user_id,
            league_id=request.league_id,
            thread_id=thread_id,
            title=conversation_service.generate_conversation_title(request.message),
            metadata={
                "roster_id": request.roster_id,
                "week": request.week
            }
        )

    # Save user message
    await conversation_service.save_message(
        db=db,
        conversation_id=conversation.id,
        role="user",
        content=request.message,
        metadata={
            "league_id": request.league_id,
            "roster_id": request.roster_id,
            "week": request.week
        }
    )

    async def event_generator():
        """Generate SSE events"""
        # Send metadata first (includes thread_id for frontend)
        metadata_event = {
            "type": "metadata",
            "thread_id": thread_id,
            "conversation_id": str(conversation.id),
            "is_new_conversation": is_new_conversation
        }
        yield f"data: {json.dumps(metadata_event)}\n\n"

        # Stream agent response
        agent = LangGraphChatAgent()  # Or get from dependency
        full_response = ""
        tool_calls_used = []

        try:
            async for event in agent.chat_stream(
                user_message=request.message,
                thread_id=thread_id,  # Pass thread_id for checkpointing
                league_id=request.league_id,
                roster_id=request.roster_id,
                week=request.week,
                conversation_history=[]  # Not needed anymore - checkpointer handles it
            ):
                # Forward event to frontend
                yield f"data: {json.dumps(event)}\n\n"

                # Collect response and tool calls
                if event.get("type") == "response":
                    full_response += event.get("message", "")
                if event.get("type") == "status" and "Using tools:" in event.get("message", ""):
                    # Extract tool names
                    tools_str = event["message"].replace("Using tools:", "").strip("...")
                    tool_calls_used.extend([t.strip() for t in tools_str.split(",")])

        except Exception as e:
            logger.error(f"Error during chat stream: {e}")
            error_event = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
            full_response = f"Error: {str(e)}"

        # Save assistant message
        if full_response:
            await conversation_service.save_message(
                db=db,
                conversation_id=conversation.id,
                role="assistant",
                content=full_response,
                tool_calls=tool_calls_used if tool_calls_used else None,
                metadata={
                    "model": "claude-3-5-haiku",
                    "tools_used": tool_calls_used
                }
            )

        # Send completion event
        done_event = {"type": "done"}
        yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Verification:**
- Start backend server
- Send a test request to `/chat/stream`
- Check database: `SELECT * FROM conversations;`
- Check database: `SELECT * FROM messages;`
- Should see conversation and messages saved

---

### Task 2.3: Update LangGraph Agent to Use Checkpointing

**What to do:**
Modify the `chat_stream` method in `langgraph_chat_agent.py` to properly use checkpointing with thread_id.

**File to modify:** `backend/app/agents/langgraph_chat_agent.py`

**Find the `chat_stream` method and replace it:**

```python
async def chat_stream(
    self,
    user_message: str,
    thread_id: str,  # REQUIRED
    league_id: str,
    roster_id: int,
    week: int,
    conversation_history: Optional[List] = None  # Deprecated - keeping for backward compatibility
):
    """
    Stream chat response with LangGraph checkpointing.

    Args:
        user_message: The user's message
        thread_id: Unique conversation thread identifier
        league_id: Sleeper league ID
        roster_id: User's roster ID
        week: Current NFL week
        conversation_history: Deprecated - checkpointer handles history
    """

    # Configuration for checkpointing
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": ""  # Optional namespace for organizing checkpoints
        }
    }

    # Get existing state from checkpointer (if any)
    try:
        state_snapshot = await self.graph.aget_state(config)
        has_existing_state = bool(state_snapshot.values)
    except Exception as e:
        logger.warning(f"Could not retrieve checkpoint state: {e}")
        has_existing_state = False

    # Initialize or update state
    if has_existing_state:
        logger.info(f"Resuming conversation with thread_id: {thread_id}")
        # Append new message to existing state
        current_state = state_snapshot.values
        current_state["messages"].append(HumanMessage(content=user_message))

        # Update context (league/roster might have changed)
        current_state["league_id"] = league_id
        current_state["roster_id"] = roster_id
        current_state["week"] = week

        initial_state = current_state
    else:
        logger.info(f"Starting new conversation with thread_id: {thread_id}")
        # Create fresh state
        initial_state: ChatAgentState = {
            "messages": [HumanMessage(content=user_message)],
            "user_id": "default",  # TODO: Get from auth
            "league_id": league_id,
            "roster_id": roster_id,
            "week": week,
            "next_agent": None,
            "current_agent": "chat",
            "roster_data": None,
            "players_data": None,
            "tool_outputs": {},
            "status_message": None,
            "final_response": None,
            "needs_approval": False,
            "pending_action": None
        }

    # Yield initial status
    yield {"type": "status", "message": "Fetching your roster data..."}

    # Stream graph execution with checkpointing
    try:
        async for event in self.graph.astream(initial_state, config=config):
            # Extract and yield status/response events
            if isinstance(event, dict):
                for node_name, node_state in event.items():
                    # Status updates
                    if "status_message" in node_state and node_state["status_message"]:
                        yield {"type": "status", "message": node_state["status_message"]}

                    # Tool execution status
                    if "messages" in node_state and len(node_state["messages"]) > 0:
                        last_msg = node_state["messages"][-1]
                        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                            tool_names = [tc["name"] for tc in last_msg.tool_calls]
                            yield {"type": "status", "message": f"Using tools: {', '.join(tool_names)}..."}

                    # Final response
                    if "final_response" in node_state and node_state["final_response"]:
                        yield {"type": "response", "message": node_state["final_response"]}

        # Get final state after execution
        final_state = await self.graph.aget_state(config)
        logger.info(f"Conversation state saved to checkpoint: {thread_id}")

    except Exception as e:
        logger.error(f"Error during graph execution: {e}")
        yield {"type": "error", "message": f"An error occurred: {str(e)}"}
```

**Verification:**
- Send first message with no thread_id → Creates new checkpoint
- Send second message with same thread_id → Resumes from checkpoint
- Check PostgreSQL: `SELECT * FROM checkpoints WHERE thread_id = 'your-thread-id';`
- Should see checkpoint data

---

## PHASE 3: CONVERSATION HISTORY API ENDPOINTS

### Task 3.1: Create Conversation API Router

**What to do:**
Create new API endpoints for managing conversations (list, get, delete).

**File to create:** `backend/app/api/conversations.py`

**Code to write:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

from app.core.database import get_db
from app.services import conversation_service
from app.models.conversation import Conversation, Message

router = APIRouter(prefix="/conversations", tags=["conversations"])


# Response Schemas
class MessageResponse(BaseModel):
    id: UUID
    role: str
    content: str
    tool_calls: Optional[List[dict]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    id: UUID
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_preview: str

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    id: UUID
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    league_id: Optional[str]
    metadata: dict
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


# Endpoints
@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    user_id: str = "default",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get user's conversation history, ordered by most recent"""
    conversations = await conversation_service.get_user_conversations(
        db, user_id, limit, offset
    )

    # Build summaries with message count and preview
    summaries = []
    for conv in conversations:
        messages = await conversation_service.get_conversation_messages(db, conv.id)

        # Get last message for preview
        last_message = messages[-1].content if messages else "No messages"
        preview = last_message[:100] + "..." if len(last_message) > 100 else last_message

        summaries.append(
            ConversationSummary(
                id=conv.id,
                thread_id=conv.thread_id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(messages),
                last_message_preview=preview
            )
        )

    return summaries


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get full conversation with all messages"""
    conversation = await conversation_service.get_conversation_by_id(db, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    messages = await conversation_service.get_conversation_messages(db, conversation_id)

    return ConversationDetail(
        id=conversation.id,
        thread_id=conversation.thread_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        league_id=conversation.league_id,
        metadata=conversation.metadata or {},
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    success = await conversation_service.delete_conversation(db, conversation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    return None


@router.patch("/{conversation_id}/title")
async def update_title(
    conversation_id: UUID,
    title: str,
    db: AsyncSession = Depends(get_db)
):
    """Update conversation title"""
    conversation = await conversation_service.update_conversation_title(
        db, conversation_id, title
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    return {"success": True, "title": conversation.title}
```

**Step 2: Register router in main app**

**File to modify:** `backend/app/main.py`

Add import:
```python
from app.api import conversations
```

Register router:
```python
app.include_router(conversations.router, prefix="/api")
```

**Verification:**
```bash
# Start server and test endpoints
curl http://localhost:8000/api/conversations
curl http://localhost:8000/api/conversations/{conversation_id}
```

---

## PHASE 4: REDIS CACHING ENHANCEMENTS

### Task 4.1: Create Redis Cache Service

**What to do:**
Create an enhanced Redis caching service with decorators and key management.

**File to create:** `backend/app/services/redis_cache_service.py`

**Code to write:**
```python
from functools import wraps
from typing import Any, Callable, Optional
import logging
import json

from app.core.redis_client import RedisClient

logger = logging.getLogger(__name__)


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
    """Time-to-live constants (in seconds)"""
    SLEEPER_PLAYERS = 3600  # 1 hour
    SLEEPER_ROSTER = 1800   # 30 minutes
    PLAYER_PROJECTION = 1800  # 30 minutes
    DEFENSE_STATS = 86400   # 24 hours
    MATCHUP_ANALYSIS = 1800  # 30 minutes


def cache_result(key_func: Callable, ttl: int):
    """
    Decorator to cache function results in Redis.

    Args:
        key_func: Function that takes the same args as decorated function and returns cache key
        ttl: Time-to-live in seconds

    Example:
        @cache_result(lambda player_id, week: f"projection:{player_id}:{week}", 1800)
        async def get_projection(player_id: str, week: int):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            redis = RedisClient()

            # Build cache key from function arguments
            try:
                cache_key = key_func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Failed to build cache key: {e}")
                # If key building fails, skip caching
                return await func(*args, **kwargs)

            # Try to get from cache
            try:
                cached = await redis.get(cache_key)
                if cached is not None:
                    logger.info(f"Cache HIT: {cache_key}")
                    return cached
            except Exception as e:
                logger.warning(f"Redis get failed for {cache_key}: {e}")

            # Cache miss - execute function
            logger.info(f"Cache MISS: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                await redis.set(cache_key, result, expire=ttl)
                logger.debug(f"Cached result for {cache_key} (TTL: {ttl}s)")
            except Exception as e:
                logger.warning(f"Redis set failed for {cache_key}: {e}")

            return result

        return wrapper
    return decorator


async def invalidate_roster_cache(league_id: str, roster_id: int):
    """Clear roster cache after changes"""
    redis = RedisClient()
    pattern = f"sleeper:roster:{league_id}:{roster_id}:*"

    try:
        # Note: This requires redis-py with pattern deletion support
        # For production, consider using SCAN + DEL
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.info(f"Invalidated {len(keys)} roster cache entries")
    except Exception as e:
        logger.error(f"Failed to invalidate roster cache: {e}")


async def invalidate_player_cache(player_id: str):
    """Clear all caches for a player"""
    redis = RedisClient()
    patterns = [
        f"projection:{player_id}:*",
        f"matchup:{player_id}:*"
    ]

    try:
        for pattern in patterns:
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for pattern {pattern}")
    except Exception as e:
        logger.error(f"Failed to invalidate player cache: {e}")
```

**Verification:**
```bash
python -c "from app.services.redis_cache_service import cache_result, CacheKeyBuilder; print('Cache service imported')"
```

---

### Task 4.2: Apply Caching to Tools

**What to do:**
Add caching decorators to expensive tool operations.

**File to modify:** `backend/app/agents/tools.py`

**Find tool functions and add caching:**

Example for `get_player_projection`:
```python
from app.services.redis_cache_service import cache_result, CacheKeyBuilder, CacheTTL

@cache_result(
    lambda player_id, week: CacheKeyBuilder.player_projection(player_id, week),
    CacheTTL.PLAYER_PROJECTION
)
async def get_player_projection(player_id: str, week: int) -> Dict:
    """Fetch player projection with caching"""
    # Existing implementation
    ...
```

**Apply to these tools:**
- `get_player_projection` → Use PLAYER_PROJECTION TTL
- `analyze_defense_vs_position` → Use DEFENSE_STATS TTL
- `get_player_news` → Use short TTL (15 minutes)
- Any Sleeper API calls → Use SLEEPER_* TTLs

**Verification:**
- Call a tool twice with same arguments
- Check logs for "Cache HIT" on second call
- Use Redis CLI: `redis-cli KEYS "*"`

---

## PHASE 5: FRONTEND IMPLEMENTATION

### Task 5.1: Update API Client Types

**What to do:**
Add TypeScript types for conversation endpoints.

**File to modify:** `frontend/src/services/api.ts` (or wherever API client is)

**Add types:**
```typescript
export interface Conversation {
    id: string;
    thread_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    message_count: number;
    last_message_preview: string;
}

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    tool_calls?: any[];
    created_at: string;
}

export interface ConversationDetail {
    id: string;
    thread_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    league_id?: string;
    metadata: Record<string, any>;
    messages: Message[];
}

export interface ChatRequest {
    message: string;
    league_id: string;
    roster_id: number;
    week: number;
    thread_id?: string;
    user_id?: string;
}

export interface ChatStreamEvent {
    type: 'status' | 'response' | 'metadata' | 'error' | 'done';
    message?: string;
    thread_id?: string;
    conversation_id?: string;
    is_new_conversation?: boolean;
}
```

**Add API functions:**
```typescript
export async function getConversations(): Promise<Conversation[]> {
    const response = await fetch('/api/conversations', {
        headers: { 'Content-Type': 'application/json' }
    });
    if (!response.ok) throw new Error('Failed to fetch conversations');
    return response.json();
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
    const response = await fetch(`/api/conversations/${conversationId}`);
    if (!response.ok) throw new Error('Failed to fetch conversation');
    return response.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
    const response = await fetch(`/api/conversations/${conversationId}`, {
        method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete conversation');
}

export async function updateConversationTitle(
    conversationId: string,
    title: string
): Promise<void> {
    const response = await fetch(`/api/conversations/${conversationId}/title`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title })
    });
    if (!response.ok) throw new Error('Failed to update title');
}
```

---

### Task 5.2: Create Conversation Context

**What to do:**
Create React context to manage conversation state across the app.

**File to create:** `frontend/src/contexts/ConversationContext.tsx`

**Code to write:**
```typescript
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Conversation, ConversationDetail, getConversations, getConversation, deleteConversation as apiDeleteConversation } from '../services/api';

interface ConversationContextType {
    currentThreadId: string | null;
    conversations: Conversation[];
    currentConversation: ConversationDetail | null;
    loading: boolean;
    loadConversations: () => Promise<void>;
    selectConversation: (threadId: string) => Promise<void>;
    startNewConversation: () => void;
    deleteConversation: (conversationId: string) => Promise<void>;
    setCurrentThreadId: (threadId: string) => void;
}

const ConversationContext = createContext<ConversationContextType | undefined>(undefined);

export const ConversationProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [currentConversation, setCurrentConversation] = useState<ConversationDetail | null>(null);
    const [loading, setLoading] = useState(false);

    const loadConversations = async () => {
        setLoading(true);
        try {
            const data = await getConversations();
            setConversations(data);
        } catch (error) {
            console.error('Failed to load conversations:', error);
        } finally {
            setLoading(false);
        }
    };

    const selectConversation = async (threadId: string) => {
        setCurrentThreadId(threadId);

        // Find conversation in list
        const conv = conversations.find(c => c.thread_id === threadId);
        if (conv) {
            // Load full conversation detail
            try {
                const detail = await getConversation(conv.id);
                setCurrentConversation(detail);
            } catch (error) {
                console.error('Failed to load conversation detail:', error);
            }
        }
    };

    const startNewConversation = () => {
        setCurrentThreadId(null);
        setCurrentConversation(null);
    };

    const deleteConversation = async (conversationId: string) => {
        try {
            await apiDeleteConversation(conversationId);
            // Remove from local state
            setConversations(prev => prev.filter(c => c.id !== conversationId));
            // If currently viewing, clear it
            if (currentConversation?.id === conversationId) {
                startNewConversation();
            }
        } catch (error) {
            console.error('Failed to delete conversation:', error);
            throw error;
        }
    };

    // Load conversations on mount
    useEffect(() => {
        loadConversations();
    }, []);

    return (
        <ConversationContext.Provider
            value={{
                currentThreadId,
                conversations,
                currentConversation,
                loading,
                loadConversations,
                selectConversation,
                startNewConversation,
                deleteConversation,
                setCurrentThreadId
            }}
        >
            {children}
        </ConversationContext.Provider>
    );
};

export const useConversation = () => {
    const context = useContext(ConversationContext);
    if (!context) {
        throw new Error('useConversation must be used within ConversationProvider');
    }
    return context;
};
```

---

### Task 5.3: Create Conversation Sidebar Component

**What to do:**
Create a sidebar component to display conversation history.

**File to create:** `frontend/src/components/ConversationSidebar.tsx`

**Code to write:**
```typescript
import React, { useState } from 'react';
import { useConversation } from '../contexts/ConversationContext';
import { formatDistanceToNow } from 'date-fns';

export const ConversationSidebar: React.FC = () => {
    const {
        conversations,
        currentThreadId,
        selectConversation,
        startNewConversation,
        deleteConversation,
        loading
    } = useConversation();

    const [searchQuery, setSearchQuery] = useState('');
    const [deletingId, setDeletingId] = useState<string | null>(null);

    const handleDelete = async (e: React.MouseEvent, conversationId: string) => {
        e.stopPropagation();

        if (!window.confirm('Are you sure you want to delete this conversation?')) {
            return;
        }

        setDeletingId(conversationId);
        try {
            await deleteConversation(conversationId);
        } catch (error) {
            alert('Failed to delete conversation');
        } finally {
            setDeletingId(null);
        }
    };

    // Filter conversations by search query
    const filteredConversations = conversations.filter(conv =>
        conv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conv.last_message_preview.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Group by date
    const groupedConversations = filteredConversations.reduce((groups, conv) => {
        const date = new Date(conv.created_at);
        const now = new Date();
        const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

        let group = 'Older';
        if (diffDays === 0) group = 'Today';
        else if (diffDays === 1) group = 'Yesterday';
        else if (diffDays <= 7) group = 'This Week';
        else if (diffDays <= 30) group = 'This Month';

        if (!groups[group]) groups[group] = [];
        groups[group].push(conv);
        return groups;
    }, {} as Record<string, typeof conversations>);

    return (
        <div className="conversation-sidebar">
            {/* Header */}
            <div className="sidebar-header">
                <button
                    className="new-conversation-btn"
                    onClick={startNewConversation}
                >
                    + New Conversation
                </button>
            </div>

            {/* Search */}
            <div className="search-box">
                <input
                    type="text"
                    placeholder="Search conversations..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {/* Conversation List */}
            <div className="conversation-list">
                {loading ? (
                    <div className="loading">Loading conversations...</div>
                ) : (
                    Object.entries(groupedConversations).map(([group, convs]) => (
                        <div key={group} className="conversation-group">
                            <div className="group-label">{group}</div>
                            {convs.map(conv => (
                                <div
                                    key={conv.id}
                                    className={`conversation-item ${
                                        conv.thread_id === currentThreadId ? 'active' : ''
                                    }`}
                                    onClick={() => selectConversation(conv.thread_id)}
                                >
                                    <div className="conversation-title">{conv.title}</div>
                                    <div className="conversation-preview">
                                        {conv.last_message_preview}
                                    </div>
                                    <div className="conversation-meta">
                                        <span className="message-count">
                                            {conv.message_count} messages
                                        </span>
                                        <span className="timestamp">
                                            {formatDistanceToNow(new Date(conv.updated_at), {
                                                addSuffix: true
                                            })}
                                        </span>
                                    </div>
                                    <button
                                        className="delete-btn"
                                        onClick={(e) => handleDelete(e, conv.id)}
                                        disabled={deletingId === conv.id}
                                    >
                                        {deletingId === conv.id ? '...' : '×'}
                                    </button>
                                </div>
                            ))}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
```

**Add basic styles** (adjust to your styling approach):

**File to create:** `frontend/src/components/ConversationSidebar.css`

```css
.conversation-sidebar {
    width: 300px;
    height: 100vh;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    background: #f9f9f9;
}

.sidebar-header {
    padding: 16px;
    border-bottom: 1px solid #e0e0e0;
}

.new-conversation-btn {
    width: 100%;
    padding: 12px;
    background: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
}

.new-conversation-btn:hover {
    background: #0056b3;
}

.search-box {
    padding: 12px 16px;
    border-bottom: 1px solid #e0e0e0;
}

.search-box input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.conversation-list {
    flex: 1;
    overflow-y: auto;
}

.conversation-group {
    margin-bottom: 16px;
}

.group-label {
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
}

.conversation-item {
    padding: 12px 16px;
    border-bottom: 1px solid #e0e0e0;
    cursor: pointer;
    position: relative;
    transition: background 0.2s;
}

.conversation-item:hover {
    background: #f0f0f0;
}

.conversation-item.active {
    background: #e3f2fd;
    border-left: 3px solid #007bff;
}

.conversation-title {
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 4px;
    color: #333;
}

.conversation-preview {
    font-size: 12px;
    color: #666;
    margin-bottom: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.conversation-meta {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #999;
}

.delete-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    background: transparent;
    border: none;
    font-size: 20px;
    color: #999;
    cursor: pointer;
    width: 24px;
    height: 24px;
    display: none;
}

.conversation-item:hover .delete-btn {
    display: block;
}

.delete-btn:hover {
    color: #ff4444;
}

.loading {
    padding: 24px;
    text-align: center;
    color: #999;
}
```

---

### Task 5.4: Update Chat Component

**What to do:**
Modify the main chat component to use conversation context and handle thread_id.

**File to modify:** `frontend/src/components/Chat.tsx` (or main chat component)

**Key changes:**

1. **Import conversation context:**
```typescript
import { useConversation } from '../contexts/ConversationContext';
```

2. **Use context in component:**
```typescript
const { currentThreadId, setCurrentThreadId, loadConversations } = useConversation();
```

3. **Update sendMessage to include thread_id:**
```typescript
const sendMessage = async (message: string) => {
    // Build request with thread_id
    const request: ChatRequest = {
        message,
        league_id: selectedLeague,
        roster_id: selectedRoster,
        week: currentWeek,
        thread_id: currentThreadId || undefined,  // Use current or undefined for new
        user_id: 'default'
    };

    // Send to API
    const eventSource = await chatStream(request);

    eventSource.onmessage = (event) => {
        const data: ChatStreamEvent = JSON.parse(event.data);

        // Handle metadata event (includes thread_id)
        if (data.type === 'metadata' && data.thread_id) {
            if (!currentThreadId) {
                // First message in new conversation - save thread_id
                setCurrentThreadId(data.thread_id);
            }
            // Reload conversation list to show new conversation
            loadConversations();
        }

        // Handle other events...
    };
};
```

4. **Load historical messages when selecting conversation:**
```typescript
const { currentConversation } = useConversation();

useEffect(() => {
    if (currentConversation) {
        // Load messages from conversation
        const historicalMessages = currentConversation.messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.created_at
        }));
        setMessages(historicalMessages);
    } else {
        // New conversation
        setMessages([]);
    }
}, [currentConversation]);
```

---

### Task 5.5: Update Main App Layout

**What to do:**
Integrate the conversation sidebar into your main app layout.

**File to modify:** `frontend/src/App.tsx` (or main layout component)

**Wrap app with ConversationProvider:**
```typescript
import { ConversationProvider } from './contexts/ConversationContext';
import { ConversationSidebar } from './components/ConversationSidebar';

function App() {
    return (
        <ConversationProvider>
            <div className="app-container">
                <ConversationSidebar />
                <div className="main-content">
                    {/* Your existing chat component */}
                    <Chat />
                </div>
            </div>
        </ConversationProvider>
    );
}
```

**Add layout styles:**
```css
.app-container {
    display: flex;
    height: 100vh;
}

.main-content {
    flex: 1;
    overflow: hidden;
}
```

---

## PHASE 6: TESTING & VALIDATION

### Task 6.1: Manual Testing Checklist

Execute these tests and verify each works correctly:

**Backend Tests:**
```bash
# 1. Database persistence
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Who should I start this week?",
    "league_id": "test_league",
    "roster_id": 1,
    "week": 10
  }'

# Verify: Check database for conversation and message
psql -d your_db -c "SELECT * FROM conversations;"
psql -d your_db -c "SELECT * FROM messages;"

# 2. Conversation retrieval
curl http://localhost:8000/api/conversations

# 3. Continue existing conversation (use thread_id from step 1)
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What about my RB2?",
    "league_id": "test_league",
    "roster_id": 1,
    "week": 10,
    "thread_id": "THREAD_ID_FROM_STEP_1"
  }'

# Verify: Same conversation has 2 messages now

# 4. Redis caching
# Call a tool twice, check logs for "Cache HIT"
redis-cli KEYS "*"

# 5. LangGraph checkpointing
psql -d your_db -c "SELECT * FROM checkpoints;"
```

**Frontend Tests:**
1. [ ] Open app → See conversation sidebar
2. [ ] Click "New Conversation" → Clears chat
3. [ ] Send first message → Creates new conversation in sidebar
4. [ ] Send follow-up message → Appends to same conversation
5. [ ] Click different conversation → Loads that conversation's messages
6. [ ] Delete conversation → Removes from sidebar
7. [ ] Search conversations → Filters correctly
8. [ ] Refresh page → Selected conversation persists (if you add localStorage)

---

### Task 6.2: Write Unit Tests (Optional but Recommended)

**File to create:** `backend/tests/test_conversation_service.py`

```python
import pytest
from uuid import uuid4
from app.services import conversation_service

@pytest.mark.asyncio
async def test_create_conversation(db_session):
    conv = await conversation_service.create_conversation(
        db_session,
        user_id="test_user",
        league_id="test_league",
        thread_id=str(uuid4()),
        title="Test Conversation"
    )
    assert conv.id is not None
    assert conv.title == "Test Conversation"

@pytest.mark.asyncio
async def test_save_and_retrieve_messages(db_session):
    # Create conversation
    conv = await conversation_service.create_conversation(
        db_session, "user1", "league1", str(uuid4())
    )

    # Save message
    msg = await conversation_service.save_message(
        db_session, conv.id, "user", "Hello!"
    )
    assert msg.content == "Hello!"

    # Retrieve messages
    messages = await conversation_service.get_conversation_messages(db_session, conv.id)
    assert len(messages) == 1
    assert messages[0].content == "Hello!"

# Add more tests...
```

---

## PHASE 7: DEPLOYMENT & CLEANUP

### Task 7.1: Update Requirements and Documentation

**Update requirements.txt:**
```bash
cd backend
pip freeze > requirements.txt
```

**Verify key dependencies are included:**
- langgraph-checkpoint-postgres
- sqlalchemy
- asyncpg
- alembic
- redis

---

### Task 7.2: Environment Variables

**Ensure these are set in `.env`:**
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fantasy_football
REDIS_URL=redis://localhost:6379
```

---

### Task 7.3: Create Database Backup

**Before deploying:**
```bash
pg_dump -U your_user -d your_database > backup_before_migration.sql
```

---

### Task 7.4: Run Migrations in Production

**When deploying:**
```bash
cd backend
alembic upgrade head
```

---

### Task 7.5: Monitor After Deployment

**Check these metrics:**
1. Database query latency (should be <100ms for conversation queries)
2. Redis cache hit rate (aim for >80%)
3. Checkpoint table size growth
4. Frontend load times

**Logging to monitor:**
```bash
# Backend logs
tail -f backend/logs/app.log | grep -E "conversation|checkpoint|cache"

# Database connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='your_db';"

# Redis stats
redis-cli INFO stats | grep keyspace
```

---

## SUCCESS CRITERIA

After implementing all phases, verify these work:

- [ ] New conversations automatically saved to database
- [ ] Messages persisted with proper timestamps and metadata
- [ ] Conversation history displayed in sidebar
- [ ] Selecting past conversation loads all messages
- [ ] Thread continuity maintained across page refreshes
- [ ] LangGraph state recoverable from checkpoints
- [ ] Redis caching reduces API call latency
- [ ] Delete conversation removes all data (cascade)
- [ ] Search functionality filters conversations
- [ ] No errors in browser console or backend logs

---

## TROUBLESHOOTING

### Common Issues:

**1. Alembic migration fails:**
- Check database connection string
- Ensure PostgreSQL is running
- Verify models are imported in `__init__.py`

**2. Checkpointer not saving:**
- Verify `await checkpointer.setup()` was called
- Check PostgreSQL permissions
- Look for errors in logs during `graph.compile()`

**3. Frontend not showing conversations:**
- Check network tab for API errors
- Verify backend is returning data: `curl http://localhost:8000/api/conversations`
- Check ConversationProvider is wrapping app

**4. Redis caching not working:**
- Verify Redis is running: `redis-cli PING`
- Check connection string in settings
- Look for Redis errors in logs

**5. Thread_id not persisting:**
- Check that metadata event is being sent from backend
- Verify frontend is capturing thread_id from event
- Ensure `setCurrentThreadId` is being called

---

## ROLLBACK PLAN

If issues occur:

**1. Rollback database migration:**
```bash
alembic downgrade -1
```

**2. Restore database from backup:**
```bash
psql -U your_user -d your_database < backup_before_migration.sql
```

**3. Revert code:**
```bash
git revert HEAD
git push
```

---

## NEXT STEPS AFTER COMPLETION

Once this is working:

1. **Add authentication** - Replace "default" user_id with real users
2. **Implement conversation sharing** - Generate shareable links
3. **Add export functionality** - Download conversations as PDF/JSON
4. **Conversation analytics** - Track which advice users follow
5. **Advanced search** - Full-text search across all messages
6. **Conversation tags** - Organize by topic (lineup, trades, waivers)

---

## ESTIMATED TIMELINE

- Phase 1: Database Setup - **4-6 hours**
- Phase 2: Backend Service - **6-8 hours**
- Phase 3: API Endpoints - **2-3 hours**
- Phase 4: Redis Caching - **3-4 hours**
- Phase 5: Frontend - **6-8 hours**
- Phase 6: Testing - **4-6 hours**
- Phase 7: Deployment - **2-3 hours**

**Total: 27-38 hours** (can be split across multiple days)

---

## QUESTIONS OR ISSUES?

If you encounter problems during implementation:

1. Check the error logs (backend and frontend)
2. Verify database and Redis are running
3. Review this prompt for missed steps
4. Test each phase independently before moving to next
5. Use `git commit` after each working phase (for easy rollback)

Good luck with implementation!
