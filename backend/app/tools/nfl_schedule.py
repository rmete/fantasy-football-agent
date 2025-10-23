"""
NFL Schedule Tool
Fetches NFL schedules to determine team matchups
"""
from typing import Dict, Any, Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class NFLScheduleTool:
    """Tool for fetching NFL schedules and matchups"""

    def __init__(self):
        # Sleeper API endpoint for NFL state (includes week info)
        self.sleeper_base = "https://api.sleeper.app/v1"

    async def get_team_opponent(
        self,
        team_abbr: str,
        week: int,
        season: int = 2025
    ) -> Optional[str]:
        """
        Get the opponent for a specific team in a given week

        Args:
            team_abbr: Team abbreviation (e.g., "KC", "SF", "BAL")
            week: NFL week number
            season: NFL season year

        Returns:
            Opponent team abbreviation or None if not found
        """
        logger.info(f"Fetching opponent for {team_abbr} in week {week}")

        # For now, we'll use web search to find the matchup
        # In production, you'd use an NFL API or maintain a schedule database
        from app.tools.web_search import web_search_tool

        try:
            query = f"{team_abbr} NFL week {week} {season} opponent schedule"
            results = await web_search_tool.general_search(query, max_results=2)

            # Try to extract opponent from results
            opponent = self._extract_opponent_from_results(results, team_abbr)

            if opponent:
                logger.info(f"{team_abbr} plays {opponent} in week {week}")
                return opponent
            else:
                logger.warning(f"Could not determine opponent for {team_abbr} in week {week}")
                return None

        except Exception as e:
            logger.error(f"Error fetching opponent: {e}")
            return None

    def _extract_opponent_from_results(
        self,
        results: list,
        team: str
    ) -> Optional[str]:
        """
        Extract opponent team from search results

        This is a simple implementation - in production you'd want more robust parsing
        """
        # Common team abbreviations
        nfl_teams = [
            "KC", "SF", "BAL", "BUF", "CIN", "CLE", "DAL", "DEN", "DET", "GB",
            "HOU", "IND", "JAX", "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO",
            "NYG", "NYJ", "PHI", "PIT", "SEA", "TB", "TEN", "WAS", "ARI", "ATL",
            "CAR", "CHI"
        ]

        for result in results:
            content = (result.get("title", "") + " " + result.get("content", "")).upper()

            # Look for "vs" or "@" patterns
            for opp in nfl_teams:
                if opp == team.upper():
                    continue

                # Check for common matchup patterns
                patterns = [
                    f"{team.upper()} VS {opp}",
                    f"{team.upper()} @ {opp}",
                    f"{opp} VS {team.upper()}",
                    f"{opp} @ {team.upper()}",
                    f"{team.upper()}-{opp}",
                    f"{opp}-{team.upper()}"
                ]

                for pattern in patterns:
                    if pattern in content:
                        return opp

        return None

    async def get_team_schedule(
        self,
        team_abbr: str,
        season: int = 2025
    ) -> Dict[int, str]:
        """
        Get full season schedule for a team

        Args:
            team_abbr: Team abbreviation
            season: NFL season year

        Returns:
            Dictionary mapping week numbers to opponent abbreviations
        """
        # This would ideally call an NFL schedule API
        # For now, return empty dict - we'll fetch matchups on-demand
        logger.info(f"Schedule lookup for {team_abbr} - using on-demand fetching")
        return {}

    def get_team_full_name(self, team_abbr: str) -> str:
        """Convert team abbreviation to full name"""
        team_map = {
            "ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills",
            "CAR": "Panthers", "CHI": "Bears", "CIN": "Bengals", "CLE": "Browns",
            "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers",
            "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars", "KC": "Chiefs",
            "LAC": "Chargers", "LAR": "Rams", "LV": "Raiders", "MIA": "Dolphins",
            "MIN": "Vikings", "NE": "Patriots", "NO": "Saints", "NYG": "Giants",
            "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers", "SEA": "Seahawks",
            "SF": "49ers", "TB": "Buccaneers", "TEN": "Titans", "WAS": "Commanders"
        }
        return team_map.get(team_abbr.upper(), team_abbr)


# Singleton instance
nfl_schedule_tool = NFLScheduleTool()
