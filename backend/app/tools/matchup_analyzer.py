"""
Comprehensive Matchup Analyzer Tool
Analyzes player matchups using real data sources (no mocking)
"""
from typing import Dict, Any, List, Optional
import logging
from app.tools.data.nfl_stats_api import nfl_stats_api
from app.tools.data.schedule_service import schedule_service
from app.tools.data.vegas_lines import vegas_lines_api
from app.tools.data.weather_service import weather_service
from app.tools.web_search import web_search_tool

logger = logging.getLogger(__name__)


class MatchupAnalyzerTool:
    """
    Comprehensive tool for analyzing player matchups using real data

    Data Sources:
    - NFL Stats API (ESPN) for defensive rankings and stats
    - Schedule Service for opponent and home/away determination
    - Vegas Lines API for spreads and over/under
    - Weather Service for game day conditions
    - Web Search for qualitative analysis
    """

    def __init__(self):
        self.nfl_stats = nfl_stats_api
        self.schedule = schedule_service
        self.vegas = vegas_lines_api
        self.weather = weather_service

    async def analyze_player_matchup(
        self,
        player_name: str,
        player_team: str,
        opponent_team: str,
        position: str,
        week: int,
        season: int = 2025
    ) -> Dict[str, Any]:
        """
        Analyze a player's matchup using real data sources

        Args:
            player_name: Player's name
            player_team: Player's team abbreviation
            opponent_team: Opponent team abbreviation
            position: Position (QB, RB, WR, TE)
            week: Week number (1-18)
            season: Season year

        Returns:
            {
                "player": str,
                "opponent": str,
                "matchup_rating": float,  # 0-10 scale
                "defense_rank_vs_position": int,
                "points_allowed_avg": float,
                "home_away": str,
                "weather": Optional[Dict],
                "vegas_total": Optional[float],
                "vegas_spread": Optional[float],
                "recommendation": str,
                "insights": str
            }
        """
        logger.info(f"Analyzing matchup: {player_name} ({player_team}) vs {opponent_team}, Week {week}")

        # Fetch all data in parallel
        try:
            # Get defensive stats
            defensive_stats = await self.nfl_stats.get_defensive_stats(opponent_team, season, week)

            # Get home/away status
            is_home = await self.schedule.is_home_game(player_team, week, season)

            # Get Vegas lines
            vegas_total = await self.vegas.get_over_under(player_team, opponent_team, week, season)
            vegas_spread = await self.vegas.get_game_spread(player_team, opponent_team, week, season)

            # Get weather (for home team's stadium)
            game_time = await self.schedule.get_game_time(player_team, week, season)
            weather_data = await self.weather.get_game_weather(
                player_team if is_home else opponent_team,
                week,
                game_time,
                season
            )

            # Extract defensive metrics
            defense_rank = 16  # Default to league average
            points_allowed = 18.0  # Default average

            if defensive_stats:
                defense_rank = defensive_stats.get("rank_vs_position", {}).get(position, 16)
                points_allowed = defensive_stats.get("points_allowed_avg", {}).get(position, 18.0)

            # Calculate comprehensive matchup rating
            matchup_rating = await self._calculate_matchup_rating(
                defense_rank=defense_rank,
                points_allowed=points_allowed,
                is_home=is_home,
                vegas_total=vegas_total,
                weather=weather_data,
                position=position
            )

            # Get qualitative insights via web search
            insights = await self._get_web_insights(player_name, opponent_team, position, week)

            return {
                "player": player_name,
                "player_team": player_team,
                "opponent": opponent_team,
                "position": position,
                "week": week,
                "season": season,
                "matchup_rating": round(matchup_rating, 2),
                "defense_rank_vs_position": defense_rank,
                "points_allowed_avg": round(points_allowed, 2),
                "home_away": "Home" if is_home else "Away",
                "is_home": is_home,
                "weather": weather_data,
                "vegas_total": vegas_total,
                "vegas_spread": vegas_spread,
                "recommendation": self._generate_matchup_recommendation(matchup_rating),
                "insights": insights,
            }

        except Exception as e:
            logger.error(f"Error analyzing matchup for {player_name}: {e}")
            return {
                "player": player_name,
                "player_team": player_team,
                "opponent": opponent_team,
                "position": position,
                "week": week,
                "error": str(e),
                "matchup_rating": 5.0,
                "recommendation": "Unable to analyze matchup - data unavailable"
            }

    async def _calculate_matchup_rating(
        self,
        defense_rank: int,
        points_allowed: float,
        is_home: bool,
        vegas_total: Optional[float],
        weather: Optional[Dict[str, Any]],
        position: str
    ) -> float:
        """
        Calculate matchup favorability rating (0-10 scale)

        Factors:
        - Defense rank vs position (40% weight)
        - Points allowed to position (30% weight)
        - Home/away (10% weight)
        - Vegas total (10% weight)
        - Weather conditions (10% weight)
        """
        rating = 5.0  # Start at neutral

        # Defense rank factor (40% weight)
        # Rank 1 (best) = low rating, Rank 32 (worst) = high rating
        defense_score = ((32 - defense_rank) / 32) * 4.0  # 0-4 points
        rating += defense_score

        # Points allowed factor (30% weight)
        # Higher points allowed = better matchup
        position_avg_map = {"QB": 18.0, "RB": 15.0, "WR": 20.0, "TE": 10.0}
        league_avg = position_avg_map.get(position, 15.0)

        if points_allowed > league_avg + 3:
            rating += 1.5  # Great matchup
        elif points_allowed > league_avg:
            rating += 0.8  # Good matchup
        elif points_allowed < league_avg - 3:
            rating -= 1.5  # Tough matchup
        elif points_allowed < league_avg:
            rating -= 0.8  # Below average matchup

        # Home/away factor (10% weight)
        if is_home:
            rating += 0.5
        else:
            rating -= 0.3

        # Vegas total factor (10% weight)
        if vegas_total:
            if vegas_total >= 50:
                rating += 0.5  # High-scoring game expected
            elif vegas_total >= 45:
                rating += 0.2
            elif vegas_total <= 38:
                rating -= 0.5  # Low-scoring game
            elif vegas_total <= 42:
                rating -= 0.2

        # Weather factor (10% weight)
        if weather:
            weather_impact = weather.get("weather_impact", "none")
            if weather_impact == "severe":
                rating -= 1.0
            elif weather_impact == "high":
                rating -= 0.6
            elif weather_impact == "moderate":
                rating -= 0.3

        # Clamp rating to 0-10 range
        return max(0.0, min(10.0, rating))

    async def _get_web_insights(
        self,
        player_name: str,
        opponent: str,
        position: str,
        week: int
    ) -> str:
        """
        Get qualitative insights from web search
        """
        try:
            query = f"{player_name} vs {opponent} week {week} 2025 fantasy matchup analysis"
            results = await web_search_tool.general_search(query, max_results=2)

            if results:
                # Combine top snippets
                insights = []
                for result in results[:2]:
                    content = result.get("content", "")
                    if content:
                        insights.append(content[:150])

                return " | ".join(insights) if insights else "No additional insights available"

            return "No additional insights available"

        except Exception as e:
            logger.warning(f"Error fetching web insights: {e}")
            return "Unable to fetch additional insights"

    def _generate_matchup_recommendation(self, rating: float) -> str:
        """Generate recommendation based on matchup rating"""

        if rating >= 8:
            return "Excellent matchup - Start with confidence"
        elif rating >= 6.5:
            return "Favorable matchup - Good start option"
        elif rating >= 5:
            return "Above average matchup - Solid play"
        elif rating >= 4:
            return "Neutral matchup - Moderate expectations"
        elif rating >= 2.5:
            return "Difficult matchup - Consider alternatives"
        else:
            return "Very tough matchup - Avoid if possible"

    async def analyze_defense_vs_position(
        self,
        defense_team: str,
        position: str,
        week: int,
        season: int = 2025
    ) -> Dict[str, Any]:
        """
        Analyze how a defense performs against a specific position

        Args:
            defense_team: Defense team abbreviation
            position: Position (QB, RB, WR, TE)
            week: Week number
            season: Season year

        Returns:
            Defense vs position analysis
        """
        try:
            defensive_stats = await self.nfl_stats.get_defensive_stats(defense_team, season, week)

            if not defensive_stats:
                return {
                    "defense_team": defense_team,
                    "position": position,
                    "week": week,
                    "error": "Unable to fetch defensive stats"
                }

            defense_rank = defensive_stats.get("rank_vs_position", {}).get(position, 16)
            points_allowed = defensive_stats.get("points_allowed_avg", {}).get(position, 18.0)

            # Determine recommendation
            if defense_rank <= 10:
                recommendation = "unfavorable"
            elif defense_rank >= 23:
                recommendation = "favorable"
            else:
                recommendation = "neutral"

            return {
                "defense_team": defense_team,
                "position": position,
                "week": week,
                "season": season,
                "defense_rank": defense_rank,
                "points_allowed_avg": round(points_allowed, 2),
                "recommendation": recommendation,
            }

        except Exception as e:
            logger.error(f"Error analyzing defense vs position: {e}")
            return {
                "defense_team": defense_team,
                "position": position,
                "error": str(e)
            }

    async def analyze_team_matchups(
        self,
        roster_players: List[Dict[str, Any]],
        week: int,
        season: int = 2025
    ) -> List[Dict[str, Any]]:
        """
        Analyze matchups for entire roster

        Args:
            roster_players: List of player dicts with name, team, position
            week: Week number
            season: Season year

        Returns:
            List of matchup analyses
        """
        matchups = []

        for player in roster_players:
            opponent = player.get("opponent")
            if not opponent:
                # Try to fetch opponent from schedule
                opponent = await self.schedule.get_team_opponent(
                    player.get("team"),
                    week,
                    season
                )

            if opponent:
                try:
                    analysis = await self.analyze_player_matchup(
                        player.get("name", "Unknown"),
                        player.get("team", ""),
                        opponent,
                        player.get("position", ""),
                        week,
                        season
                    )
                    matchups.append(analysis)
                except Exception as e:
                    logger.error(f"Error analyzing matchup for {player.get('name')}: {e}")
                    continue

        return matchups


# Singleton instance
matchup_analyzer = MatchupAnalyzerTool()
