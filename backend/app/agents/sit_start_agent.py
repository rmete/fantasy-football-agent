from typing import Dict, Any, List
from app.agents.state import AgentState
from app.agents.config import SYSTEM_PROMPTS, AGENT_MODELS
from app.agents.llm_client import llm_client
from app.tools import (
    sleeper_client,
    web_search_tool,
    reddit_tool,
    projection_tool,
    injury_tool,
    matchup_analyzer
)
from app.utils.bye_weeks import is_team_on_bye, get_team_bye_week
import logging

logger = logging.getLogger(__name__)

class SitStartAgent:
    """Agent for making sit/start decisions"""

    def __init__(self):
        self.model = AGENT_MODELS["sit_start"]
        self.system_prompt = SYSTEM_PROMPTS["sit_start"]

    async def analyze_player(
        self,
        player_id: str,
        player_name: str,
        position: str,
        opponent: str,
        week: int,
        players_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Comprehensive player analysis"""

        logger.info(f"Analyzing {player_name} for week {week}")

        # Gather data from multiple sources in parallel
        player_info = players_data.get(player_id, {})
        player_team = player_info.get("team", "")

        # 0. Check if player is on bye week
        is_on_bye = is_team_on_bye(player_team, week) if player_team else False
        bye_week = get_team_bye_week(player_team) if player_team else None

        # If on bye, return immediate recommendation to sit
        if is_on_bye:
            logger.info(f"{player_name} is on BYE week {week}")
            return {
                "player_id": player_id,
                "player_name": player_name,
                "position": position,
                "team": player_team,
                "opponent": "BYE",
                "week": week,
                "is_on_bye": True,
                "bye_week": bye_week,
                "recommendation": "SIT",
                "confidence": 100,
                "reasoning": f"{player_name} is on a BYE week. You must substitute them out of your lineup.",
                "supporting_data": {
                    "projection": 0,
                    "matchup_rating": 0,
                    "injury_status": "BYE",
                    "sentiment_score": 0
                }
            }

        # 1. Check injury status
        injury_status = await injury_tool.check_player_injury_status(
            player_id, player_name
        )

        # 2. Get matchup analysis
        matchup = await matchup_analyzer.analyze_player_matchup(
            player_name,
            player_team,
            opponent,
            position,
            week
        )

        # 3. Get projections
        projection = await projection_tool.get_player_projection(
            player_name, position, week
        )

        # 4. Search recent news
        news = await web_search_tool.search_player_news(
            player_name,
            additional_context=f"week {week} fantasy outlook"
        )

        # 5. Get community sentiment
        sentiment = await reddit_tool.get_player_sentiment(player_name)

        # Compile all data
        analysis_data = {
            "player_id": player_id,
            "player_name": player_name,
            "position": position,
            "team": player_team,
            "opponent": opponent,
            "week": week,
            "is_on_bye": False,
            "bye_week": bye_week,
            "injury_status": injury_status,
            "matchup": matchup,
            "projection": projection,
            "recent_news": news[:3],
            "sentiment": sentiment
        }

        # Use Claude to synthesize analysis
        decision = await self._make_decision(analysis_data)

        return decision

    async def _make_decision(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use Claude to make final sit/start decision"""

        # Prepare context for Claude
        context = f"""
Analyze this fantasy football player for sit/start decision:

Player: {analysis_data['player_name']} ({analysis_data['position']})
Team: {analysis_data['team']} vs {analysis_data['opponent']}
Week: {analysis_data['week']}

Injury Status: {analysis_data['injury_status']['injury_status']}
Injury Recommendation: {analysis_data['injury_status']['recommendation']}

Matchup Rating: {analysis_data['matchup']['matchup_rating']}/10
Matchup Recommendation: {analysis_data['matchup']['recommendation']}

Projection: {analysis_data['projection']['projected_points']} points
Floor/Ceiling: {analysis_data['projection']['floor']} - {analysis_data['projection']['ceiling']}

Reddit Sentiment: {analysis_data['sentiment']['sentiment_score']} ({analysis_data['sentiment']['confidence']})
Positive/Negative: {analysis_data['sentiment']['positive_mentions']}/{analysis_data['sentiment']['negative_mentions']}

Recent News:
{chr(10).join([f"- {n['title']}" for n in analysis_data['recent_news']])}

Based on all this data, provide:
1. START or SIT recommendation
2. Confidence score (0-100)
3. Brief reasoning (2-3 sentences)
4. Key factors influencing decision
"""

        try:
            recommendation_text = llm_client.create_message(
                model=self.model,
                system=self.system_prompt,
                messages=[
                    {"role": "user", "content": context}
                ],
                max_tokens=1000
            )

            # Parse response
            decision = self._parse_recommendation(
                recommendation_text,
                analysis_data
            )

            return decision

        except Exception as e:
            logger.error(f"Error making decision: {e}")
            return {
                "player": analysis_data['player_name'],
                "recommendation": "SIT",
                "confidence": 50,
                "reasoning": f"Error occurred during analysis: {str(e)}",
                "error": str(e)
            }

    def _parse_recommendation(
        self,
        text: str,
        analysis_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Claude's response into structured format"""

        # Simple parsing
        recommendation = "START" if "START" in text.upper() else "SIT"

        # Extract confidence (look for numbers)
        confidence = 75  # Default
        for line in text.split('\n'):
            if 'confidence' in line.lower():
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    confidence = int(numbers[0])
                    break

        return {
            "player_id": analysis_data['player_id'],
            "player_name": analysis_data['player_name'],
            "position": analysis_data['position'],
            "week": analysis_data['week'],
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": text,
            "supporting_data": {
                "projection": analysis_data['projection']['projected_points'],
                "matchup_rating": analysis_data['matchup']['matchup_rating'],
                "injury_status": analysis_data['injury_status']['injury_status'],
                "sentiment_score": analysis_data['sentiment']['sentiment_score']
            }
        }

    async def analyze_lineup_decision(
        self,
        state: AgentState
    ) -> Dict[str, Any]:
        """Analyze multiple players for lineup decisions"""

        roster_data = state["roster_data"]
        players_data = state["players_data"]
        week = state.get("week", 1)

        starters = roster_data.get("starters", [])
        bench = roster_data.get("players", [])

        # Remove starters from bench list
        bench = [p for p in bench if p not in starters]

        # Analyze all players
        all_analyses = []
        bye_week_starters = []
        bench_analyses = []

        # Analyze starters first
        for player_id in starters:
            player_info = players_data.get(player_id, {})
            if not player_info:
                continue

            analysis = await self.analyze_player(
                player_id,
                player_info.get("full_name", "Unknown"),
                player_info.get("position", ""),
                player_info.get("opponent", ""),
                week,
                players_data
            )
            all_analyses.append(analysis)

            # Track bye week players
            if analysis.get("is_on_bye"):
                bye_week_starters.append(analysis)

        # Analyze bench players
        for player_id in bench[:10]:  # Analyze more bench players to find substitutes
            player_info = players_data.get(player_id, {})
            if not player_info:
                continue

            analysis = await self.analyze_player(
                player_id,
                player_info.get("full_name", "Unknown"),
                player_info.get("position", ""),
                player_info.get("opponent", ""),
                week,
                players_data
            )
            all_analyses.append(analysis)
            bench_analyses.append(analysis)

        # Generate substitution suggestions for bye week players
        substitution_suggestions = []
        for bye_player in bye_week_starters:
            # Find bench players at same position who are not on bye
            position = bye_player["position"]
            available_subs = [
                b for b in bench_analyses
                if b["position"] == position
                and not b.get("is_on_bye", False)
                and b["recommendation"] == "START"
            ]

            # Sort by projected points
            available_subs.sort(
                key=lambda x: x["supporting_data"].get("projection", 0),
                reverse=True
            )

            best_sub = available_subs[0] if available_subs else None

            substitution_suggestions.append({
                "player_to_sit": {
                    "player_id": bye_player["player_id"],
                    "player_name": bye_player["player_name"],
                    "position": bye_player["position"],
                    "reason": "BYE WEEK"
                },
                "suggested_replacement": {
                    "player_id": best_sub["player_id"] if best_sub else None,
                    "player_name": best_sub["player_name"] if best_sub else "No available substitute",
                    "position": best_sub["position"] if best_sub else position,
                    "projected_points": best_sub["supporting_data"].get("projection", 0) if best_sub else 0
                } if best_sub else None,
                "priority": "CRITICAL",
                "confidence": 100
            })

        # Sort by confidence and recommendation
        start_recommendations = [
            a for a in all_analyses if a["recommendation"] == "START" and not a.get("is_on_bye")
        ]
        sit_recommendations = [
            a for a in all_analyses if a["recommendation"] == "SIT" or a.get("is_on_bye")
        ]

        return {
            "total_analyzed": len(all_analyses),
            "bye_week_players": bye_week_starters,
            "substitution_suggestions": substitution_suggestions,
            "start_recommendations": sorted(
                start_recommendations,
                key=lambda x: x["confidence"],
                reverse=True
            ),
            "sit_recommendations": sorted(
                sit_recommendations,
                key=lambda x: x["confidence"],
                reverse=True
            ),
            "all_analyses": all_analyses
        }

sit_start_agent = SitStartAgent()
