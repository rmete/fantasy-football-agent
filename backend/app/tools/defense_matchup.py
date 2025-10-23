"""
Defense vs Position Matchup Analysis Tool
Analyzes how defenses perform against specific positions using web search
"""
from typing import Dict, Any, Optional
from app.tools.web_search import web_search_tool
from app.utils.nfl_week import get_current_nfl_week
import logging

logger = logging.getLogger(__name__)


class DefenseMatchupAnalyzer:
    """Analyzes defensive matchups against specific positions"""

    async def analyze_defense_vs_position(
        self,
        defense_team: str,
        position: str,
        week: Optional[int] = None,
        year: int = 2025
    ) -> Dict[str, Any]:
        """
        Analyze how a defense performs against a specific position

        Args:
            defense_team: The defensive team (e.g., "Falcons", "Giants")
            position: The position (e.g., "RB", "WR", "QB", "TE")
            week: Current NFL week (defaults to current week)
            year: NFL season year (defaults to 2025)

        Returns:
            Dictionary with matchup analysis including rating and insights
        """
        week = week or get_current_nfl_week()

        # Build specific query based on position
        position_queries = {
            "RB": f"How are the {defense_team} defense against the run {year} week {week}",
            "WR": f"How are the {defense_team} defense against wide receivers {year} week {week}",
            "QB": f"How is the {defense_team} defense against the pass {year} week {week}",
            "TE": f"How are the {defense_team} defense against tight ends {year} week {week}",
        }

        # Get position-specific query or default
        if position in position_queries:
            query = position_queries[position]
        else:
            query = f"{defense_team} defense vs {position} fantasy football {year} week {week}"

        logger.info(f"Analyzing matchup: {query}")

        try:
            # Search the web for defense vs position analysis
            search_results = await web_search_tool.general_search(query, max_results=3)

            # Also search for general defense rankings
            rankings_query = f"{defense_team} defense rankings against {position} {year}"
            rankings_results = await web_search_tool.general_search(rankings_query, max_results=2)

            # Combine results
            all_results = search_results + rankings_results

            # Extract key insights
            analysis = {
                "defense_team": defense_team,
                "position": position,
                "week": week,
                "year": year,
                "query": query,
                "search_results": all_results,
                "insights": self._extract_insights(all_results, defense_team, position),
                "recommendation": self._generate_recommendation(all_results, defense_team, position)
            }

            logger.info(f"Matchup analysis complete: {defense_team} vs {position}")
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing defense matchup: {e}")
            return {
                "defense_team": defense_team,
                "position": position,
                "week": week,
                "year": year,
                "error": str(e),
                "search_results": [],
                "insights": "Unable to fetch matchup data",
                "recommendation": "neutral"
            }

    def _extract_insights(
        self,
        search_results: list,
        defense_team: str,
        position: str
    ) -> str:
        """Extract key insights from search results"""

        if not search_results:
            return f"No data available for {defense_team} vs {position}"

        # Combine top snippets
        insights = []
        for result in search_results[:3]:
            content = result.get("content", "")
            if content:
                insights.append(content[:200])

        combined = " | ".join(insights)
        return combined if combined else f"Limited data for {defense_team} vs {position}"

    def _generate_recommendation(
        self,
        search_results: list,
        defense_team: str,
        position: str
    ) -> str:
        """
        Generate a recommendation based on search results
        Returns: "favorable", "neutral", "unfavorable"
        """

        if not search_results:
            return "neutral"

        # Simple keyword-based analysis
        positive_keywords = ["weak", "vulnerable", "allows", "gives up", "favorable", "exploit"]
        negative_keywords = ["strong", "tough", "stingy", "shutdown", "elite", "difficult"]

        positive_count = 0
        negative_count = 0

        for result in search_results[:3]:
            content = (result.get("content", "") + " " + result.get("title", "")).lower()

            for keyword in positive_keywords:
                if keyword in content:
                    positive_count += 1

            for keyword in negative_keywords:
                if keyword in content:
                    negative_count += 1

        # Determine recommendation
        if positive_count > negative_count:
            return "favorable"
        elif negative_count > positive_count:
            return "unfavorable"
        else:
            return "neutral"

    async def analyze_player_matchup(
        self,
        player_name: str,
        player_team: str,
        player_position: str,
        opponent_team: str,
        week: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analyze a specific player's matchup against an opponent defense

        Args:
            player_name: Name of the player
            player_team: Player's team
            player_position: Player's position (QB, RB, WR, TE)
            opponent_team: Opposing team
            week: Current week

        Returns:
            Detailed matchup analysis
        """
        week = week or get_current_nfl_week()

        logger.info(f"Analyzing player matchup: {player_name} ({player_position}) vs {opponent_team}")

        # Get defense vs position analysis
        defense_analysis = await self.analyze_defense_vs_position(
            opponent_team,
            player_position,
            week
        )

        # Get player-specific matchup info
        player_query = f"{player_name} vs {opponent_team} week {week} 2025 fantasy outlook"
        player_results = await web_search_tool.general_search(player_query, max_results=2)

        return {
            "player_name": player_name,
            "player_team": player_team,
            "player_position": player_position,
            "opponent_team": opponent_team,
            "week": week,
            "defense_vs_position": defense_analysis,
            "player_specific_results": player_results,
            "overall_recommendation": defense_analysis.get("recommendation", "neutral"),
            "summary": self._create_matchup_summary(
                player_name,
                player_position,
                opponent_team,
                defense_analysis,
                player_results
            )
        }

    def _create_matchup_summary(
        self,
        player_name: str,
        position: str,
        opponent: str,
        defense_analysis: Dict[str, Any],
        player_results: list
    ) -> str:
        """Create a human-readable matchup summary"""

        recommendation = defense_analysis.get("recommendation", "neutral")

        if recommendation == "favorable":
            sentiment = "favorable"
        elif recommendation == "unfavorable":
            sentiment = "challenging"
        else:
            sentiment = "neutral"

        summary = f"{player_name} ({position}) faces a {sentiment} matchup against {opponent}. "

        insights = defense_analysis.get("insights", "")
        if insights:
            summary += f"{insights[:150]}..."

        return summary


# Singleton instance
defense_matchup_analyzer = DefenseMatchupAnalyzer()
