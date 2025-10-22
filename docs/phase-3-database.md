# Phase 3: Database & Models

**Goal**: Set up PostgreSQL database with SQLAlchemy ORM and create data models

**Estimated Time**: 4-6 hours

**Dependencies**: Phase 1 (Project Foundation), Phase 2 (Backend Core)

## Overview

This phase establishes persistent data storage for:
- User accounts and preferences
- League and roster data (cached from Sleeper)
- Player statistics and trends
- AI agent decisions and recommendations
- Historical analysis data

## Tasks Breakdown

### Task 3.1: Database Connection Setup

#### backend/app/core/database.py

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()

async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
```

### Task 3.2: SQLAlchemy Models

#### backend/app/models/user.py

```python
from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sleeper_user_id = Column(String, unique=True, nullable=False, index=True)
    sleeper_username = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    avatar = Column(String, nullable=True)

    # Preferences
    preferences = Column(JSON, default={})
    autonomous_mode = Column(Boolean, default=False)
    notification_settings = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    leagues = relationship("League", back_populates="user", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="user", cascade="all, delete-orphan")
```

#### backend/app/models/league.py

```python
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class League(Base):
    __tablename__ = "leagues"

    id = Column(String, primary_key=True)  # Sleeper league_id
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    season = Column(String, nullable=False)
    sport = Column(String, default="nfl")
    status = Column(String)  # pre_draft, drafting, in_season, complete
    total_rosters = Column(Integer)

    # League settings
    roster_positions = Column(JSON)
    scoring_settings = Column(JSON)
    settings = Column(JSON)

    # Cache timestamps
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="leagues")
    rosters = relationship("Roster", back_populates="league", cascade="all, delete-orphan")
    agent_decisions = relationship("AgentDecision", back_populates="league", cascade="all, delete-orphan")

class Roster(Base):
    __tablename__ = "rosters"

    id = Column(String, primary_key=True)  # Composite: league_id:roster_id
    league_id = Column(String, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    roster_id = Column(Integer, nullable=False)
    owner_id = Column(String, nullable=False)  # Sleeper user_id

    # Roster data
    players = Column(JSON)  # List of player IDs
    starters = Column(JSON)  # List of starter IDs
    reserve = Column(JSON)
    taxi = Column(JSON)

    # Standings
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    fpts = Column(Float, default=0.0)

    # Settings
    settings = Column(JSON)

    # Timestamps
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    league = relationship("League", back_populates="rosters")
```

#### backend/app/models/player.py

```python
from sqlalchemy import Column, String, Integer, DateTime, Float, JSON, Index
from datetime import datetime
from app.core.database import Base

class Player(Base):
    """Cached player data from Sleeper"""
    __tablename__ = "players"

    player_id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    full_name = Column(String, index=True)
    position = Column(String, index=True)
    team = Column(String, index=True)
    age = Column(Integer)
    injury_status = Column(String, index=True)
    number = Column(Integer)
    depth_chart_order = Column(Integer)
    search_rank = Column(Integer)

    # Fantasy data
    fantasy_positions = Column(JSON)
    player_data = Column(JSON)  # Full Sleeper player object

    # Timestamps
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_player_position_team', 'position', 'team'),
    )

class PlayerStats(Base):
    """Weekly player statistics"""
    __tablename__ = "player_stats"

    id = Column(String, primary_key=True)  # Composite: player_id:season:week
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False, index=True)
    season = Column(String, nullable=False)
    week = Column(Integer, nullable=False)

    # Stats
    stats = Column(JSON)  # Raw stats from Sleeper
    fantasy_points = Column(Float)
    projected_points = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_stats_player_season_week', 'player_id', 'season', 'week'),
    )
```

#### backend/app/models/agent.py

```python
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import uuid
import enum

class AgentTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentTaskType(str, enum.Enum):
    SIT_START = "sit_start"
    TRADE_ANALYSIS = "trade_analysis"
    WAIVER_WIRE = "waiver_wire"
    LINEUP_OPTIMIZATION = "lineup_optimization"
    INJURY_MONITORING = "injury_monitoring"
    OPPONENT_ANALYSIS = "opponent_analysis"

class AgentTask(Base):
    """Track agent tasks and their execution"""
    __tablename__ = "agent_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    league_id = Column(String, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=True)

    task_type = Column(SQLEnum(AgentTaskType), nullable=False)
    status = Column(SQLEnum(AgentTaskStatus), default=AgentTaskStatus.PENDING)

    # Task details
    input_data = Column(JSON)  # Parameters for the task
    result = Column(JSON)  # Agent's output
    error_message = Column(Text, nullable=True)

    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="agent_tasks")

class AgentDecision(Base):
    """Store AI-generated decisions and recommendations"""
    __tablename__ = "agent_decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    league_id = Column(String, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String, ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False)

    decision_type = Column(SQLEnum(AgentTaskType), nullable=False)
    week = Column(Integer, nullable=True)
    season = Column(String, nullable=True)

    # Decision details
    recommendation = Column(JSON)  # The actual recommendation
    reasoning = Column(Text)  # AI's explanation
    confidence_score = Column(Integer)  # 0-100

    # User action
    user_approved = Column(Boolean, nullable=True)
    user_action_taken = Column(JSON, nullable=True)
    executed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    league = relationship("League", back_populates="agent_decisions")
```

### Task 3.3: Import All Models

#### backend/app/models/__init__.py

```python
from app.models.user import User
from app.models.league import League, Roster
from app.models.player import Player, PlayerStats
from app.models.agent import AgentTask, AgentDecision, AgentTaskStatus, AgentTaskType

__all__ = [
    "User",
    "League",
    "Roster",
    "Player",
    "PlayerStats",
    "AgentTask",
    "AgentDecision",
    "AgentTaskStatus",
    "AgentTaskType",
]
```

### Task 3.4: Alembic Setup for Migrations

#### Setup Alembic

```bash
cd backend
docker exec -it fantasy-backend pip install alembic
docker exec -it fantasy-backend alembic init alembic
```

#### alembic.ini (update sqlalchemy.url)

```ini
# Line ~63, comment out or remove
# sqlalchemy.url = driver://user:pass@localhost/dbname

# We'll use env.py to get URL from settings
```

#### alembic/env.py

```python
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio

# Import your app configuration
from app.core.config import settings
from app.core.database import Base

# Import all models so Alembic can detect them
from app.models import *

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with our settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    """Run migrations in 'online' mode for async engine."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

#### Create Initial Migration

```bash
# Generate migration
docker exec -it fantasy-backend alembic revision --autogenerate -m "Initial migration"

# Apply migration
docker exec -it fantasy-backend alembic upgrade head
```

### Task 3.5: Database Initialization in App Startup

Update `backend/main.py`:

```python
from app.core.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Fantasy Football AI Manager API")
    await init_db()  # Initialize database
    await redis_cache.connect()
    yield
    # Shutdown
    logger.info("Shutting down API")
    await sleeper_client.close()
    await redis_cache.close()
```

### Task 3.6: CRUD Operations

#### backend/app/crud/user.py

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from typing import Optional

async def get_user_by_sleeper_id(db: AsyncSession, sleeper_user_id: str) -> Optional[User]:
    """Get user by Sleeper user ID"""
    result = await db.execute(
        select(User).where(User.sleeper_user_id == sleeper_user_id)
    )
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, sleeper_user_id: str, sleeper_username: str, display_name: str, avatar: Optional[str] = None) -> User:
    """Create new user"""
    user = User(
        sleeper_user_id=sleeper_user_id,
        sleeper_username=sleeper_username,
        display_name=display_name,
        avatar=avatar
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def update_user_preferences(db: AsyncSession, user_id: str, preferences: dict) -> Optional[User]:
    """Update user preferences"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.preferences = preferences
        await db.commit()
        await db.refresh(user)
    return user
```

#### backend/app/crud/league.py

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.league import League, Roster
from typing import List, Optional

async def get_or_create_league(db: AsyncSession, league_id: str, user_id: str, league_data: dict) -> League:
    """Get existing league or create new one"""
    result = await db.execute(select(League).where(League.id == league_id))
    league = result.scalar_one_or_none()

    if not league:
        league = League(
            id=league_id,
            user_id=user_id,
            name=league_data["name"],
            season=league_data["season"],
            sport=league_data["sport"],
            status=league_data["status"],
            total_rosters=league_data["total_rosters"],
            roster_positions=league_data.get("roster_positions"),
            scoring_settings=league_data.get("scoring_settings"),
            settings=league_data.get("settings"),
        )
        db.add(league)
        await db.commit()
        await db.refresh(league)

    return league

async def get_user_leagues(db: AsyncSession, user_id: str) -> List[League]:
    """Get all leagues for a user"""
    result = await db.execute(
        select(League).where(League.user_id == user_id)
    )
    return result.scalars().all()
```

## Testing

### Test Database Connection

```python
# backend/tests/test_database.py
import asyncio
from app.core.database import engine, AsyncSessionLocal, init_db
from app.models.user import User
from app.crud.user import create_user, get_user_by_sleeper_id

async def test_database():
    """Test database connectivity and basic CRUD"""

    # Initialize database
    await init_db()
    print("✓ Database initialized")

    # Create test user
    async with AsyncSessionLocal() as session:
        test_user = await create_user(
            session,
            sleeper_user_id="test123",
            sleeper_username="testuser",
            display_name="Test User"
        )
        print(f"✓ Created user: {test_user.display_name}")

        # Retrieve user
        retrieved = await get_user_by_sleeper_id(session, "test123")
        print(f"✓ Retrieved user: {retrieved.display_name}")

        assert retrieved.sleeper_user_id == "test123"

    print("✅ Database tests passed!")

if __name__ == "__main__":
    asyncio.run(test_database())
```

Run test:
```bash
docker exec -it fantasy-backend python tests/test_database.py
```

## Success Criteria

After completing Phase 3:

1. ✅ PostgreSQL database accessible with pgvector extension
2. ✅ All SQLAlchemy models created and imported
3. ✅ Alembic migrations set up and working
4. ✅ Database tables created successfully
5. ✅ CRUD operations working for User and League
6. ✅ Database connection pooling configured
7. ✅ Can query database from Python

## Verification

```bash
# Check if tables were created
docker exec -it fantasy-postgres psql -U postgres -d fantasy_football -c "\dt"

# Should see tables: users, leagues, rosters, players, player_stats, agent_tasks, agent_decisions

# Check migrations
docker exec -it fantasy-backend alembic current

# Test CRUD operations
docker exec -it fantasy-backend python tests/test_database.py
```

## Next Steps

Proceed to **[Phase 4: Agent Tools](./phase-4-agent-tools.md)** to build the tools that agents will use.

## Resources

- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
