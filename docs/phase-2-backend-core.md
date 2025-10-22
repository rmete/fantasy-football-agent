# Phase 2: Backend Core & Sleeper API Integration

**Goal**: Build FastAPI REST endpoints and integrate with Sleeper API

**Estimated Time**: 6-8 hours

**Dependencies**: Phase 1 (Project Foundation)

## Overview

This phase creates the core backend functionality, focusing on:
- Sleeper API client for fetching fantasy football data
- REST API endpoints for frontend consumption
- Pydantic schemas for data validation
- Error handling and logging
- Caching with Redis

## Tasks Breakdown

### Task 2.1: Sleeper API Client

#### backend/app/tools/sleeper_client.py

```python
import httpx
from typing import Optional, List, Dict, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class SleeperClient:
    """Client for interacting with Sleeper API"""

    def __init__(self):
        self.base_url = settings.SLEEPER_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        try:
            response = await self.client.get(f"{self.base_url}/user/{username}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching user {username}: {e}")
            return None

    async def get_user_leagues(self, user_id: str, sport: str = "nfl", season: str = "2024") -> List[Dict[str, Any]]:
        """Get all leagues for a user in a given season"""
        try:
            response = await self.client.get(
                f"{self.base_url}/user/{user_id}/leagues/{sport}/{season}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching leagues for user {user_id}: {e}")
            return []

    async def get_league(self, league_id: str) -> Optional[Dict[str, Any]]:
        """Get league details"""
        try:
            response = await self.client.get(f"{self.base_url}/league/{league_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching league {league_id}: {e}")
            return None

    async def get_league_rosters(self, league_id: str) -> List[Dict[str, Any]]:
        """Get all rosters in a league"""
        try:
            response = await self.client.get(f"{self.base_url}/league/{league_id}/rosters")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching rosters for league {league_id}: {e}")
            return []

    async def get_league_users(self, league_id: str) -> List[Dict[str, Any]]:
        """Get all users in a league"""
        try:
            response = await self.client.get(f"{self.base_url}/league/{league_id}/users")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching users for league {league_id}: {e}")
            return []

    async def get_league_matchups(self, league_id: str, week: int) -> List[Dict[str, Any]]:
        """Get matchups for a specific week"""
        try:
            response = await self.client.get(
                f"{self.base_url}/league/{league_id}/matchups/{week}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching matchups for league {league_id}, week {week}: {e}")
            return []

    async def get_players(self) -> Dict[str, Any]:
        """Get all NFL players (cached, updates daily)"""
        try:
            response = await self.client.get(f"{self.base_url}/players/nfl")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching players: {e}")
            return {}

    async def get_trending_players(self, sport: str = "nfl", add_drop: str = "add") -> List[Dict[str, Any]]:
        """Get trending players (adds or drops)"""
        try:
            response = await self.client.get(
                f"{self.base_url}/players/{sport}/trending/{add_drop}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error fetching trending players: {e}")
            return []

# Singleton instance
sleeper_client = SleeperClient()
```

### Task 2.2: Pydantic Schemas

#### backend/app/schemas/sleeper.py

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SleeperUser(BaseModel):
    user_id: str
    username: str
    display_name: str
    avatar: Optional[str] = None

class SleeperLeague(BaseModel):
    league_id: str
    name: str
    season: str
    sport: str
    status: str
    total_rosters: int
    roster_positions: List[str]
    scoring_settings: Dict[str, Any]
    settings: Dict[str, Any]

class SleeperRoster(BaseModel):
    roster_id: int
    owner_id: str
    league_id: str
    players: List[str]  # List of player IDs
    starters: List[str]  # List of starter player IDs
    reserve: Optional[List[str]] = None
    taxi: Optional[List[str]] = None
    settings: Dict[str, Any]

    # Standings info
    wins: int = 0
    losses: int = 0
    ties: int = 0
    fpts: float = 0.0  # Fantasy points for season

class SleeperPlayer(BaseModel):
    player_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    position: Optional[str] = None
    team: Optional[str] = None
    age: Optional[int] = None
    injury_status: Optional[str] = None
    number: Optional[int] = None
    depth_chart_order: Optional[int] = None
    search_rank: Optional[int] = None
    fantasy_positions: Optional[List[str]] = None

class SleeperMatchup(BaseModel):
    roster_id: int
    matchup_id: int
    points: float
    starters: List[str]
    players: List[str]
    custom_points: Optional[float] = None

class LeagueResponse(BaseModel):
    """Response model for league endpoint"""
    league: SleeperLeague
    rosters: List[SleeperRoster]
    users: List[SleeperUser]

class UserLeaguesResponse(BaseModel):
    """Response model for user leagues endpoint"""
    user: SleeperUser
    leagues: List[SleeperLeague]
```

### Task 2.3: API Routes

#### backend/app/api/sleeper.py

```python
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.schemas.sleeper import (
    SleeperUser,
    SleeperLeague,
    LeagueResponse,
    UserLeaguesResponse,
    SleeperRoster,
    SleeperMatchup
)
from app.tools.sleeper_client import sleeper_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sleeper", tags=["sleeper"])

@router.get("/user/{username}", response_model=SleeperUser)
async def get_user(username: str):
    """Get Sleeper user by username"""
    user_data = await sleeper_client.get_user(username)
    if not user_data:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    return user_data

@router.get("/user/{username}/leagues", response_model=UserLeaguesResponse)
async def get_user_leagues(
    username: str,
    sport: str = Query("nfl", description="Sport type"),
    season: str = Query("2024", description="Season year")
):
    """Get all leagues for a user"""
    # First get user
    user_data = await sleeper_client.get_user(username)
    if not user_data:
        raise HTTPException(status_code=404, detail=f"User {username} not found")

    # Then get leagues
    leagues = await sleeper_client.get_user_leagues(user_data["user_id"], sport, season)

    return {
        "user": user_data,
        "leagues": leagues
    }

@router.get("/league/{league_id}", response_model=LeagueResponse)
async def get_league_details(league_id: str):
    """Get complete league details including rosters and users"""
    league = await sleeper_client.get_league(league_id)
    if not league:
        raise HTTPException(status_code=404, detail=f"League {league_id} not found")

    # Fetch rosters and users in parallel
    rosters = await sleeper_client.get_league_rosters(league_id)
    users = await sleeper_client.get_league_users(league_id)

    return {
        "league": league,
        "rosters": rosters,
        "users": users
    }

@router.get("/league/{league_id}/rosters", response_model=List[SleeperRoster])
async def get_league_rosters(league_id: str):
    """Get all rosters in a league"""
    rosters = await sleeper_client.get_league_rosters(league_id)
    if not rosters:
        raise HTTPException(status_code=404, detail=f"No rosters found for league {league_id}")
    return rosters

@router.get("/league/{league_id}/matchups/{week}", response_model=List[SleeperMatchup])
async def get_league_matchups(league_id: str, week: int):
    """Get matchups for a specific week"""
    if week < 1 or week > 18:
        raise HTTPException(status_code=400, detail="Week must be between 1 and 18")

    matchups = await sleeper_client.get_league_matchups(league_id, week)
    if not matchups:
        raise HTTPException(status_code=404, detail=f"No matchups found for week {week}")
    return matchups

@router.get("/players")
async def get_all_players():
    """Get all NFL players (large response, ~50MB)"""
    players = await sleeper_client.get_players()
    if not players:
        raise HTTPException(status_code=500, detail="Failed to fetch players")
    return players

@router.get("/players/trending/{add_drop}")
async def get_trending_players(
    add_drop: str,
    sport: str = Query("nfl", description="Sport type")
):
    """Get trending players (adds or drops)"""
    if add_drop not in ["add", "drop"]:
        raise HTTPException(status_code=400, detail="add_drop must be 'add' or 'drop'")

    trending = await sleeper_client.get_trending_players(sport, add_drop)
    return trending
```

### Task 2.4: Update main.py with Routes

#### backend/main.py (updated)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import sleeper
from app.tools.sleeper_client import sleeper_client
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Fantasy Football AI Manager API")
    yield
    # Shutdown
    logger.info("Shutting down API")
    await sleeper_client.close()

app = FastAPI(
    title="Fantasy Football AI Manager API",
    description="AI-powered fantasy football team management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sleeper.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Fantasy Football AI Manager API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Task 2.5: Redis Caching Layer

#### backend/app/core/redis_client.py

```python
import redis.asyncio as redis
from app.core.config import settings
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    async def close(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
        return None

    async def set(self, key: str, value: Any, expire: int = 3600):
        """Set value in cache with expiration (default 1 hour)"""
        if not self.redis:
            return False

        try:
            await self.redis.setex(
                key,
                expire,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

# Singleton instance
redis_cache = RedisCache()
```

Update `main.py` lifespan to connect Redis:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Fantasy Football AI Manager API")
    await redis_cache.connect()
    yield
    # Shutdown
    logger.info("Shutting down API")
    await sleeper_client.close()
    await redis_cache.close()
```

### Task 2.6: Add Caching to Sleeper Client

Update `sleeper_client.py` to use Redis caching:

```python
from app.core.redis_client import redis_cache

# In SleeperClient class, add caching to expensive calls:

async def get_players(self) -> Dict[str, Any]:
    """Get all NFL players (cached for 24 hours)"""
    cache_key = "sleeper:players:nfl"

    # Try cache first
    cached = await redis_cache.get(cache_key)
    if cached:
        logger.info("Returning cached players data")
        return cached

    try:
        response = await self.client.get(f"{self.base_url}/players/nfl")
        response.raise_for_status()
        data = response.json()

        # Cache for 24 hours
        await redis_cache.set(cache_key, data, expire=86400)
        return data
    except httpx.HTTPError as e:
        logger.error(f"Error fetching players: {e}")
        return {}
```

## Testing

### Manual API Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test getting user
curl http://localhost:8000/api/v1/sleeper/user/YOUR_SLEEPER_USERNAME

# Test getting user leagues
curl http://localhost:8000/api/v1/sleeper/user/YOUR_SLEEPER_USERNAME/leagues

# Test getting league details
curl http://localhost:8000/api/v1/sleeper/league/LEAGUE_ID

# Test API docs
# Visit http://localhost:8000/docs
```

### Create Test Script

#### backend/tests/test_sleeper.py

```python
import asyncio
from app.tools.sleeper_client import sleeper_client
from app.core.config import settings

async def test_sleeper_integration():
    """Test Sleeper API integration"""

    if not settings.SLEEPER_USERNAME:
        print("ERROR: SLEEPER_USERNAME not set in .env")
        return

    print(f"Testing Sleeper API with username: {settings.SLEEPER_USERNAME}")

    # Test 1: Get user
    print("\n1. Testing get_user...")
    user = await sleeper_client.get_user(settings.SLEEPER_USERNAME)
    if user:
        print(f"✓ User found: {user['display_name']} (ID: {user['user_id']})")
    else:
        print("✗ Failed to get user")
        return

    # Test 2: Get leagues
    print("\n2. Testing get_user_leagues...")
    leagues = await sleeper_client.get_user_leagues(user['user_id'], "nfl", "2024")
    if leagues:
        print(f"✓ Found {len(leagues)} leagues")
        for league in leagues[:3]:  # Show first 3
            print(f"  - {league['name']} ({league['total_rosters']} teams)")
    else:
        print("✗ No leagues found")
        return

    # Test 3: Get league details
    if leagues:
        league_id = leagues[0]['league_id']
        print(f"\n3. Testing get_league_rosters for {leagues[0]['name']}...")
        rosters = await sleeper_client.get_league_rosters(league_id)
        if rosters:
            print(f"✓ Found {len(rosters)} rosters")
        else:
            print("✗ Failed to get rosters")

    # Test 4: Get players (cached)
    print("\n4. Testing get_players (this may take a moment)...")
    players = await sleeper_client.get_players()
    if players:
        print(f"✓ Loaded {len(players)} players")
        # Show a sample player
        sample_id = list(players.keys())[0]
        sample = players[sample_id]
        print(f"  Sample: {sample.get('full_name', 'Unknown')} - {sample.get('position', 'N/A')}")
    else:
        print("✗ Failed to get players")

    await sleeper_client.close()
    print("\n✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_sleeper_integration())
```

Run test:
```bash
docker exec -it fantasy-backend python tests/test_sleeper.py
```

## Success Criteria

After completing Phase 2, you should have:

1. ✅ Working Sleeper API client with all core methods
2. ✅ REST endpoints accessible at `/api/v1/sleeper/*`
3. ✅ Interactive API docs at http://localhost:8000/docs
4. ✅ Ability to fetch user, leagues, rosters, and players
5. ✅ Redis caching working for expensive API calls
6. ✅ Proper error handling and logging
7. ✅ Pydantic schemas validating data

## Verification

```bash
# Visit API docs and test each endpoint
open http://localhost:8000/docs

# Run test script
docker exec -it fantasy-backend python tests/test_sleeper.py

# Check Redis cache
docker exec -it fantasy-redis redis-cli KEYS "sleeper:*"
```

## Next Steps

Proceed to **[Phase 3: Database & Models](./phase-3-database.md)** to set up data persistence.

## Resources

- [Sleeper API Documentation](https://docs.sleeper.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
