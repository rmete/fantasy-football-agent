from typing import List, Dict, Any
from app.tools.sleeper_client import sleeper_client
from app.tools.web_search import web_search_tool
import logging

logger = logging.getLogger(__name__)

class InjuryMonitorTool:
    """Tool for monitoring player injuries and status changes"""

    async def check_player_injury_status(
        self,
        player_id: str,
        player_name: str
    ) -> Dict[str, Any]:
        """
        Check injury status for a player

        Returns:
            {
                "player_id": str,
                "player_name": str,
                "injury_status": str,  # None, Questionable, Doubtful, Out, IR
                "injury_body_part": str,
                "practice_status": List[str],  # ["DNP", "Limited", "Full"]
                "expected_return": str,
                "severity": str,  # low, medium, high
                "recommendation": str
            }
        """

        # Get injury status from Sleeper
        players_data = await sleeper_client.get_players()
        player_info = players_data.get(player_id, {})

        injury_status = player_info.get("injury_status")
        injury_body_part = player_info.get("injury_body_part")

        # Search for recent injury news
        news = await web_search_tool.search_player_news(
            player_name,
            additional_context="injury status update"
        )

        # Analyze severity
        severity = self._assess_injury_severity(injury_status, news)

        # Generate recommendation
        recommendation = self._generate_injury_recommendation(
            injury_status,
            severity,
            news
        )

        return {
            "player_id": player_id,
            "player_name": player_name,
            "injury_status": injury_status or "Healthy",
            "injury_body_part": injury_body_part,
            "practice_status": [],  # Would need to scrape practice reports
            "severity": severity,
            "recent_news": [n["title"] for n in news[:3]],
            "recommendation": recommendation
        }

    def _assess_injury_severity(
        self,
        injury_status: str | None,
        news: List[Dict]
    ) -> str:
        """Assess injury severity based on status and news"""

        if not injury_status:
            return "none"

        status_severity = {
            "IR": "high",
            "Out": "high",
            "Doubtful": "medium",
            "Questionable": "low",
            "PUP": "high",
        }

        return status_severity.get(injury_status, "low")

    def _generate_injury_recommendation(
        self,
        injury_status: str | None,
        severity: str,
        news: List[Dict]
    ) -> str:
        """Generate recommendation based on injury"""

        if severity == "high":
            return "Consider replacement. Player unlikely to play or severely limited."
        elif severity == "medium":
            return "Monitor closely. Have backup plan ready."
        elif severity == "low":
            return "Likely to play but monitor practice reports."
        else:
            return "No injury concerns."

    async def monitor_roster_injuries(
        self,
        player_ids: List[str],
        players_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check injury status for entire roster"""

        injuries = []

        for player_id in player_ids:
            player_info = players_data.get(player_id, {})
            injury_status = player_info.get("injury_status")

            if injury_status:
                injuries.append({
                    "player_id": player_id,
                    "player_name": player_info.get("full_name", "Unknown"),
                    "position": player_info.get("position"),
                    "injury_status": injury_status,
                    "injury_body_part": player_info.get("injury_body_part")
                })

        return injuries

injury_tool = InjuryMonitorTool()
