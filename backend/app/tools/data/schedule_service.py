"""
NFL Schedule Service
Fetches and caches NFL schedules from ESPN API
"""

import httpx
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_SCOREBOARD_ENDPOINT = f"{ESPN_API_BASE}/scoreboard"

# Team abbreviation normalization
TEAM_MAPPINGS = {
    "WSH": "WAS",
    "LA": "LAR",
}


class NFLScheduleService:
    """Service for fetching and caching NFL schedules"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._schedule_cache: Dict[int, Dict[str, Dict[int, Any]]] = {}  # season -> team -> week -> game_info
        self._current_week_cache: Optional[int] = None
        self._cache_timestamp: Optional[datetime] = None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    def _normalize_team_abbr(self, team: str) -> str:
        """Normalize team abbreviation to standard format"""
        team_upper = team.upper()
        return TEAM_MAPPINGS.get(team_upper, team_upper)

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid (less than 1 hour old)"""
        if not self._cache_timestamp:
            return False
        return (datetime.now() - self._cache_timestamp) < timedelta(hours=1)

    async def get_current_week(self, season: int = 2025) -> int:
        """
        Get the current NFL week

        Args:
            season: Season year

        Returns:
            Current week number (1-18)
        """
        if self._current_week_cache and self._is_cache_valid():
            return self._current_week_cache

        try:
            response = await self.client.get(ESPN_SCOREBOARD_ENDPOINT)
            response.raise_for_status()
            data = response.json()

            week = data.get("week", {}).get("number", 1)
            self._current_week_cache = int(week)
            return self._current_week_cache

        except Exception as e:
            logger.error(f"Error fetching current week: {e}")
            # Fallback to estimated week based on date
            now = datetime.now()
            if now.month < 9:
                return 1
            elif now.month > 12:
                return 18
            else:
                days_since_sept = (now - datetime(now.year, 9, 1)).days
                week = min(18, max(1, (days_since_sept // 7) + 1))
                return week

    async def _fetch_week_schedule(self, season: int, week: int) -> Dict[str, Any]:
        """
        Fetch schedule for a specific week

        Args:
            season: Season year
            week: Week number (1-18)

        Returns:
            Dict of games for that week
        """
        try:
            # ESPN API uses a date-based query, we need to estimate the date for the week
            # Week 1 typically starts in early September
            year = season
            # Rough estimate: Week 1 starts around Sept 8
            start_date = datetime(year, 9, 8)
            week_date = start_date + timedelta(weeks=week - 1)

            # Format as YYYYMMDD
            date_str = week_date.strftime("%Y%m%d")

            # Fetch games for this date range (get the whole week)
            params = {"dates": date_str, "seasontype": "2", "week": str(week)}
            response = await self.client.get(ESPN_SCOREBOARD_ENDPOINT, params=params)
            response.raise_for_status()
            data = response.json()

            games = data.get("events", [])
            week_schedule = {}

            for game in games:
                try:
                    competitions = game.get("competitions", [{}])[0]
                    competitors = competitions.get("competitors", [])

                    if len(competitors) < 2:
                        continue

                    # Determine home and away teams
                    home_team = None
                    away_team = None

                    for competitor in competitors:
                        team_abbr = competitor.get("team", {}).get("abbreviation", "")
                        team_abbr = self._normalize_team_abbr(team_abbr)
                        is_home = competitor.get("homeAway") == "home"

                        if is_home:
                            home_team = team_abbr
                        else:
                            away_team = team_abbr

                    if not home_team or not away_team:
                        continue

                    # Get game time
                    game_date_str = game.get("date")
                    game_time = None
                    if game_date_str:
                        try:
                            game_time = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                        except:
                            pass

                    # Store game info for both teams
                    game_info_home = {
                        "week": week,
                        "opponent": away_team,
                        "is_home": True,
                        "game_time": game_time,
                    }

                    game_info_away = {
                        "week": week,
                        "opponent": home_team,
                        "is_home": False,
                        "game_time": game_time,
                    }

                    week_schedule[home_team] = game_info_home
                    week_schedule[away_team] = game_info_away

                except Exception as e:
                    logger.warning(f"Error parsing game data: {e}")
                    continue

            return week_schedule

        except Exception as e:
            logger.error(f"Error fetching week {week} schedule: {e}")
            return {}

    async def get_full_schedule(self, season: int = 2025) -> Dict[str, Dict[int, Any]]:
        """
        Get the full season schedule for all teams

        Args:
            season: Season year

        Returns:
            Dict mapping team abbreviation to dict of week -> game info
        """
        if season in self._schedule_cache and self._is_cache_valid():
            return self._schedule_cache[season]

        try:
            full_schedule: Dict[str, Dict[int, Any]] = defaultdict(dict)

            # Fetch schedule for all 18 weeks
            for week in range(1, 19):
                week_schedule = await self._fetch_week_schedule(season, week)

                for team, game_info in week_schedule.items():
                    full_schedule[team][week] = game_info

            # Convert defaultdict to regular dict
            self._schedule_cache[season] = dict(full_schedule)
            self._cache_timestamp = datetime.now()

            logger.info(f"Cached schedule for {len(full_schedule)} teams")
            return self._schedule_cache[season]

        except Exception as e:
            logger.error(f"Error fetching full schedule: {e}")
            return {}

    async def get_team_opponent(self, team: str, week: int, season: int = 2025) -> Optional[str]:
        """
        Get the opponent for a team in a specific week

        Args:
            team: Team abbreviation
            week: Week number (1-18)
            season: Season year

        Returns:
            Opponent team abbreviation or None if on bye or not found
        """
        team = self._normalize_team_abbr(team)

        try:
            # Check cache first
            if season in self._schedule_cache and self._is_cache_valid():
                schedule = self._schedule_cache[season]
                if team in schedule and week in schedule[team]:
                    return schedule[team][week].get("opponent")

            # Fetch specific week if not in cache
            week_schedule = await self._fetch_week_schedule(season, week)

            if team in week_schedule:
                return week_schedule[team].get("opponent")

            # No game found - likely on bye
            return None

        except Exception as e:
            logger.error(f"Error getting opponent for {team} in week {week}: {e}")
            return None

    async def is_home_game(self, team: str, week: int, season: int = 2025) -> bool:
        """
        Check if a team is playing at home in a specific week

        Args:
            team: Team abbreviation
            week: Week number (1-18)
            season: Season year

        Returns:
            True if home game, False if away or bye
        """
        team = self._normalize_team_abbr(team)

        try:
            # Check cache first
            if season in self._schedule_cache and self._is_cache_valid():
                schedule = self._schedule_cache[season]
                if team in schedule and week in schedule[team]:
                    return schedule[team][week].get("is_home", False)

            # Fetch specific week if not in cache
            week_schedule = await self._fetch_week_schedule(season, week)

            if team in week_schedule:
                return week_schedule[team].get("is_home", False)

            return False

        except Exception as e:
            logger.error(f"Error checking home game for {team} in week {week}: {e}")
            return False

    async def get_game_time(self, team: str, week: int, season: int = 2025) -> Optional[datetime]:
        """
        Get the game time for a team in a specific week

        Args:
            team: Team abbreviation
            week: Week number (1-18)
            season: Season year

        Returns:
            Game time as datetime or None if not found
        """
        team = self._normalize_team_abbr(team)

        try:
            # Check cache first
            if season in self._schedule_cache and self._is_cache_valid():
                schedule = self._schedule_cache[season]
                if team in schedule and week in schedule[team]:
                    return schedule[team][week].get("game_time")

            # Fetch specific week if not in cache
            week_schedule = await self._fetch_week_schedule(season, week)

            if team in week_schedule:
                return week_schedule[team].get("game_time")

            return None

        except Exception as e:
            logger.error(f"Error getting game time for {team} in week {week}: {e}")
            return None

    async def get_team_schedule(self, team: str, season: int = 2025) -> Dict[int, str]:
        """
        Get the full season schedule for a specific team

        Args:
            team: Team abbreviation
            season: Season year

        Returns:
            Dict mapping week number to opponent abbreviation
        """
        team = self._normalize_team_abbr(team)
        full_schedule = await self.get_full_schedule(season)

        if team not in full_schedule:
            return {}

        # Return simplified dict of week -> opponent
        return {week: info.get("opponent") for week, info in full_schedule[team].items() if info.get("opponent")}


# Global instance
schedule_service = NFLScheduleService()
