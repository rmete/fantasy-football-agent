"""
NFL Schedule Tool
Fetches NFL schedules from ESPN API (via Schedule Service)
"""
from typing import Dict, Any, Optional
import logging
from app.tools.data.schedule_service import schedule_service

logger = logging.getLogger(__name__)


class NFLScheduleTool:
    """Tool for fetching NFL schedules and matchups using real data"""

    def __init__(self):
        self.schedule_service = schedule_service

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
            week: NFL week number (1-18)
            season: NFL season year

        Returns:
            Opponent team abbreviation or None if on bye or not found
        """
        logger.info(f"Fetching opponent for {team_abbr} in week {week}")

        try:
            opponent = await self.schedule_service.get_team_opponent(team_abbr, week, season)

            if opponent:
                logger.info(f"{team_abbr} plays {opponent} in week {week}")
            else:
                logger.info(f"{team_abbr} is on bye in week {week}")

            return opponent

        except Exception as e:
            logger.error(f"Error fetching opponent for {team_abbr}: {e}")
            return None

    async def is_home_game(
        self,
        team_abbr: str,
        week: int,
        season: int = 2025
    ) -> bool:
        """
        Check if a team is playing at home in a given week

        Args:
            team_abbr: Team abbreviation
            week: NFL week number
            season: NFL season year

        Returns:
            True if home game, False if away or bye
        """
        try:
            return await self.schedule_service.is_home_game(team_abbr, week, season)
        except Exception as e:
            logger.error(f"Error checking home game for {team_abbr}: {e}")
            return False

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
        logger.info(f"Fetching full schedule for {team_abbr}")

        try:
            schedule = await self.schedule_service.get_team_schedule(team_abbr, season)
            return schedule

        except Exception as e:
            logger.error(f"Error fetching schedule for {team_abbr}: {e}")
            return {}

    async def get_current_week(self, season: int = 2025) -> int:
        """
        Get the current NFL week

        Args:
            season: NFL season year

        Returns:
            Current week number (1-18)
        """
        try:
            return await self.schedule_service.get_current_week(season)
        except Exception as e:
            logger.error(f"Error fetching current week: {e}")
            return 1

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
