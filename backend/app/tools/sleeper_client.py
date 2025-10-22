import httpx
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.redis_client import redis_cache
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
