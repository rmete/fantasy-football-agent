"""
Vegas Lines API Client
Fetches betting lines and odds from public sources
"""

import httpx
import logging
import os
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
ESPN_SCOREBOARD_ENDPOINT = f"{ESPN_API_BASE}/scoreboard"

# The Odds API (optional, requires API key)
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Team abbreviation normalization
TEAM_MAPPINGS = {
    "WSH": "WAS",
    "LA": "LAR",
}


class VegasLinesAPI:
    """Client for fetching betting lines and odds"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._odds_cache: Dict[str, Any] = {}  # Cache odds by game key
        self._cache_timestamp: Optional[datetime] = None

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    def _normalize_team_abbr(self, team: str) -> str:
        """Normalize team abbreviation to standard format"""
        team_upper = team.upper()
        return TEAM_MAPPINGS.get(team_upper, team_upper)

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid (less than 12 hours old)"""
        if not self._cache_timestamp:
            return False
        return (datetime.now() - self._cache_timestamp) < timedelta(hours=12)

    async def _fetch_espn_odds(self, week: int, season: int = 2025) -> Dict[str, Any]:
        """
        Fetch odds from ESPN API for a specific week

        Args:
            week: Week number (1-18)
            season: Season year

        Returns:
            Dict mapping game key to odds data
        """
        cache_key = f"espn_{season}_{week}"

        if cache_key in self._odds_cache and self._is_cache_valid():
            return self._odds_cache[cache_key]

        try:
            # Estimate date for the week
            year = season
            start_date = datetime(year, 9, 8)
            week_date = start_date + timedelta(weeks=week - 1)
            date_str = week_date.strftime("%Y%m%d")

            params = {"dates": date_str, "seasontype": "2", "week": str(week)}
            response = await self.client.get(ESPN_SCOREBOARD_ENDPOINT, params=params)
            response.raise_for_status()
            data = response.json()

            games = data.get("events", [])
            odds_data = {}

            for game in games:
                try:
                    competitions = game.get("competitions", [{}])[0]
                    competitors = competitions.get("competitors", [])

                    if len(competitors) < 2:
                        continue

                    # Get team abbreviations
                    teams = []
                    for competitor in competitors:
                        team_abbr = competitor.get("team", {}).get("abbreviation", "")
                        team_abbr = self._normalize_team_abbr(team_abbr)
                        teams.append(team_abbr)

                    if len(teams) != 2:
                        continue

                    home_team = teams[0] if competitors[0].get("homeAway") == "home" else teams[1]
                    away_team = teams[1] if competitors[0].get("homeAway") == "home" else teams[0]

                    # Extract odds information
                    odds_info = competitions.get("odds", [])

                    spread = None
                    over_under = None
                    home_moneyline = None
                    away_moneyline = None

                    if odds_info:
                        odds = odds_info[0]

                        # Spread (negative means favorite)
                        spread_value = odds.get("spread")
                        if spread_value is not None:
                            spread = float(spread_value)

                        # Over/Under
                        ou_value = odds.get("overUnder")
                        if ou_value is not None:
                            over_under = float(ou_value)

                        # Moneylines
                        home_ml = odds.get("homeTeamOdds", {}).get("moneyLine")
                        away_ml = odds.get("awayTeamOdds", {}).get("moneyLine")

                        if home_ml:
                            home_moneyline = int(home_ml)
                        if away_ml:
                            away_moneyline = int(away_ml)

                    # Store odds for both teams
                    game_key = f"{home_team}_vs_{away_team}_week_{week}"

                    odds_data[game_key] = {
                        "home_team": home_team,
                        "away_team": away_team,
                        "week": week,
                        "spread": spread,
                        "over_under": over_under,
                        "home_moneyline": home_moneyline,
                        "away_moneyline": away_moneyline,
                    }

                except Exception as e:
                    logger.warning(f"Error parsing odds for game: {e}")
                    continue

            self._odds_cache[cache_key] = odds_data
            self._cache_timestamp = datetime.now()

            logger.info(f"Fetched odds for {len(odds_data)} games in week {week}")
            return odds_data

        except Exception as e:
            logger.error(f"Error fetching ESPN odds: {e}")
            return {}

    def _find_game(self, odds_data: Dict[str, Any], team1: str, team2: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find game in odds data by team(s)

        Args:
            odds_data: Odds data dict
            team1: First team abbreviation
            team2: Optional second team abbreviation

        Returns:
            Game odds data or None
        """
        team1 = self._normalize_team_abbr(team1)
        if team2:
            team2 = self._normalize_team_abbr(team2)

        for game_key, game_data in odds_data.items():
            home = game_data.get("home_team")
            away = game_data.get("away_team")

            # Check if team1 is in the game
            if team1 not in [home, away]:
                continue

            # If team2 specified, check if both teams match
            if team2 and team2 not in [home, away]:
                continue

            return game_data

        return None

    async def get_game_spread(self, team1: str, team2: str, week: int, season: int = 2025) -> Optional[float]:
        """
        Get the point spread for a game

        Args:
            team1: First team abbreviation
            team2: Second team abbreviation
            week: Week number (1-18)
            season: Season year

        Returns:
            Point spread or None if not available
        """
        try:
            odds_data = await self._fetch_espn_odds(week, season)
            game = self._find_game(odds_data, team1, team2)

            if game:
                return game.get("spread")

            return None

        except Exception as e:
            logger.error(f"Error getting spread for {team1} vs {team2}: {e}")
            return None

    async def get_over_under(self, team1: str, team2: str, week: int, season: int = 2025) -> Optional[float]:
        """
        Get the over/under total for a game

        Args:
            team1: First team abbreviation
            team2: Second team abbreviation
            week: Week number (1-18)
            season: Season year

        Returns:
            Over/under total or None if not available
        """
        try:
            odds_data = await self._fetch_espn_odds(week, season)
            game = self._find_game(odds_data, team1, team2)

            if game:
                return game.get("over_under")

            return None

        except Exception as e:
            logger.error(f"Error getting over/under for {team1} vs {team2}: {e}")
            return None

    async def get_moneyline(self, team: str, week: int, season: int = 2025) -> Optional[int]:
        """
        Get the moneyline for a team

        Args:
            team: Team abbreviation
            week: Week number (1-18)
            season: Season year

        Returns:
            Moneyline odds or None if not available
        """
        try:
            team = self._normalize_team_abbr(team)
            odds_data = await self._fetch_espn_odds(week, season)
            game = self._find_game(odds_data, team)

            if not game:
                return None

            # Determine if team is home or away
            if game.get("home_team") == team:
                return game.get("home_moneyline")
            else:
                return game.get("away_moneyline")

        except Exception as e:
            logger.error(f"Error getting moneyline for {team}: {e}")
            return None

    async def get_game_odds(self, team1: str, team2: str, week: int, season: int = 2025) -> Optional[Dict[str, Any]]:
        """
        Get all odds for a game (spread, over/under, moneylines)

        Args:
            team1: First team abbreviation
            team2: Second team abbreviation
            week: Week number (1-18)
            season: Season year

        Returns:
            Dict with all odds data or None if not available
        """
        try:
            odds_data = await self._fetch_espn_odds(week, season)
            game = self._find_game(odds_data, team1, team2)

            return game

        except Exception as e:
            logger.error(f"Error getting game odds for {team1} vs {team2}: {e}")
            return None

    async def get_week_odds(self, week: int, season: int = 2025) -> Dict[str, Any]:
        """
        Get all odds for a specific week

        Args:
            week: Week number (1-18)
            season: Season year

        Returns:
            Dict of all games and their odds
        """
        return await self._fetch_espn_odds(week, season)


# Global instance
vegas_lines_api = VegasLinesAPI()
