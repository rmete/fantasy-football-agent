"""
NFL Stats API Client
Fetches real NFL statistics from ESPN and other public sources
"""

import httpx
import logging
from typing import Dict, Optional, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ESPN API endpoints
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_TEAMS_ENDPOINT = f"{ESPN_API_BASE}/teams"
ESPN_SCOREBOARD_ENDPOINT = f"{ESPN_API_BASE}/scoreboard"

# Team abbreviation mappings (ESPN to standard)
TEAM_MAPPINGS = {
    "WSH": "WAS",
    "LA": "LAR",
}


class NFLStatsAPI:
    """Client for fetching NFL statistics from public APIs"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._team_cache: Dict[str, Any] = {}
        self._defensive_stats_cache: Dict[str, Any] = {}

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    def _normalize_team_abbr(self, team: str) -> str:
        """Normalize team abbreviation to standard format"""
        team_upper = team.upper()
        return TEAM_MAPPINGS.get(team_upper, team_upper)

    async def get_all_teams(self) -> Dict[str, Any]:
        """
        Get all NFL teams with basic info

        Returns:
            Dict mapping team abbreviation to team data
        """
        if self._team_cache:
            return self._team_cache

        try:
            response = await self.client.get(ESPN_TEAMS_ENDPOINT)
            response.raise_for_status()
            data = response.json()

            teams_data = {}
            if "sports" in data and len(data["sports"]) > 0:
                leagues = data["sports"][0].get("leagues", [])
                if leagues:
                    teams = leagues[0].get("teams", [])
                    for team_obj in teams:
                        team = team_obj.get("team", {})
                        abbr = team.get("abbreviation", "")
                        if abbr:
                            teams_data[abbr] = {
                                "id": team.get("id"),
                                "name": team.get("displayName"),
                                "abbreviation": abbr,
                                "location": team.get("location"),
                                "nickname": team.get("name"),
                                "logo": team.get("logos", [{}])[0].get("href") if team.get("logos") else None,
                            }

            self._team_cache = teams_data
            logger.info(f"Fetched {len(teams_data)} NFL teams")
            return teams_data

        except Exception as e:
            logger.error(f"Error fetching NFL teams: {e}")
            return {}

    async def get_team_stats(self, team_abbr: str, season: int = 2025) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive stats for a team

        Args:
            team_abbr: Team abbreviation (e.g., "KC", "SF")
            season: Season year

        Returns:
            Team stats dictionary or None if not found
        """
        team_abbr = self._normalize_team_abbr(team_abbr)

        try:
            teams = await self.get_all_teams()
            team_info = teams.get(team_abbr)

            if not team_info:
                logger.warning(f"Team {team_abbr} not found")
                return None

            team_id = team_info["id"]

            # Fetch team details including statistics
            url = f"{ESPN_TEAMS_ENDPOINT}/{team_id}"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()

            team_data = data.get("team", {})

            # Extract record
            record = team_data.get("record", {})
            record_items = record.get("items", [{}])[0] if record.get("items") else {}
            stats = record_items.get("stats", [])

            # Parse stats
            wins = losses = ties = 0
            for stat in stats:
                if stat.get("name") == "wins":
                    wins = int(stat.get("value", 0))
                elif stat.get("name") == "losses":
                    losses = int(stat.get("value", 0))
                elif stat.get("name") == "ties":
                    ties = int(stat.get("value", 0))

            return {
                "team": team_abbr,
                "name": team_info["name"],
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "record": f"{wins}-{losses}-{ties}" if ties > 0 else f"{wins}-{losses}",
            }

        except Exception as e:
            logger.error(f"Error fetching stats for team {team_abbr}: {e}")
            return None

    async def get_defensive_stats(self, team: str, season: int = 2025, week: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get defensive statistics for a team

        Args:
            team: Team abbreviation
            season: Season year
            week: Optional week number

        Returns:
            Defensive stats including rankings and points allowed by position
        """
        team = self._normalize_team_abbr(team)
        cache_key = f"{team}_{season}_{week or 'season'}"

        if cache_key in self._defensive_stats_cache:
            return self._defensive_stats_cache[cache_key]

        try:
            # For now, we'll use a combination of team stats and scoreboard data
            # In a production system, you'd want to integrate with a more comprehensive stats API
            team_stats = await self.get_team_stats(team, season)

            if not team_stats:
                return None

            # Calculate defensive ranking based on record (simplified)
            # In production, this should use actual defensive stats (yards allowed, points allowed, etc.)
            wins = team_stats["wins"]
            losses = team_stats["losses"]

            # Simple ranking calculation (better records = better defense assumption)
            # This is a placeholder - real implementation would fetch actual defensive rankings
            win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.5

            # Estimate defensive rank (1-32, lower is better)
            estimated_rank = int(32 - (win_pct * 31))

            defensive_stats = {
                "team": team,
                "season": season,
                "week": week,
                "overall_rank": estimated_rank,
                "rank_vs_position": {
                    "QB": estimated_rank,
                    "RB": estimated_rank,
                    "WR": estimated_rank,
                    "TE": estimated_rank,
                },
                "points_allowed_avg": {
                    "QB": 18.0 + (estimated_rank - 16) * 0.3,  # Varies based on rank
                    "RB": 15.0 + (estimated_rank - 16) * 0.25,
                    "WR": 20.0 + (estimated_rank - 16) * 0.35,
                    "TE": 10.0 + (estimated_rank - 16) * 0.2,
                },
            }

            self._defensive_stats_cache[cache_key] = defensive_stats
            return defensive_stats

        except Exception as e:
            logger.error(f"Error fetching defensive stats for {team}: {e}")
            return None

    async def get_defense_rankings(self, season: int = 2025, week: Optional[int] = None) -> Dict[str, int]:
        """
        Get defensive rankings for all teams

        Args:
            season: Season year
            week: Optional week number

        Returns:
            Dict mapping team abbreviation to defensive rank (1-32)
        """
        try:
            teams = await self.get_all_teams()
            rankings = {}

            for team_abbr in teams.keys():
                stats = await self.get_defensive_stats(team_abbr, season, week)
                if stats:
                    rankings[team_abbr] = stats["overall_rank"]

            return rankings

        except Exception as e:
            logger.error(f"Error fetching defense rankings: {e}")
            return {}

    async def get_points_allowed_by_position(
        self, team: str, position: str, season: int = 2025, week: Optional[int] = None
    ) -> Optional[float]:
        """
        Get average points allowed to a position by a defense

        Args:
            team: Team abbreviation
            position: Position (QB, RB, WR, TE)
            season: Season year
            week: Optional week number

        Returns:
            Average fantasy points allowed to position
        """
        defensive_stats = await self.get_defensive_stats(team, season, week)

        if not defensive_stats:
            return None

        return defensive_stats["points_allowed_avg"].get(position)

    async def get_current_week(self) -> int:
        """
        Get the current NFL week

        Returns:
            Current week number (1-18)
        """
        try:
            response = await self.client.get(ESPN_SCOREBOARD_ENDPOINT)
            response.raise_for_status()
            data = response.json()

            # Extract week from scoreboard
            week = data.get("week", {}).get("number", 1)
            return int(week)

        except Exception as e:
            logger.error(f"Error fetching current week: {e}")
            # Fallback to estimated week based on date
            now = datetime.now()
            if now.month < 9:  # Before September
                return 1
            elif now.month > 12:  # After December
                return 18
            else:
                # Rough estimate
                days_since_sept = (now - datetime(now.year, 9, 1)).days
                week = min(18, max(1, (days_since_sept // 7) + 1))
                return week


# Global instance
nfl_stats_api = NFLStatsAPI()
