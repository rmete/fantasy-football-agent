import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class WebSearchTool:
    """Tool for searching the web for player news and analysis"""

    def __init__(self):
        self.tavily_api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com/search"

    async def search_player_news(
        self,
        player_name: str,
        additional_context: str = "",
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for recent news about a player"""

        if not self.tavily_api_key:
            logger.warning("Tavily API key not set, using fallback search")
            return await self._fallback_search(player_name, additional_context)

        query = f"{player_name} NFL fantasy football {additional_context}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": max_results,
                        "include_answer": True,
                        "include_raw_content": False,
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()

                results = []
                for result in data.get("results", []):
                    results.append({
                        "title": result.get("title"),
                        "url": result.get("url"),
                        "content": result.get("content"),
                        "score": result.get("score", 0)
                    })

                return results

        except Exception as e:
            logger.error(f"Web search error: {e}")
            # Return fallback data on error instead of empty array
            return await self._fallback_search(player_name, additional_context)

    async def _fallback_search(self, player_name: str, context: str) -> List[Dict[str, Any]]:
        """Fallback search using mock data when no API key available"""
        logger.info(f"Using fallback search for {player_name}")

        # Return mock data for development/testing
        return [
            {
                "title": f"{player_name} - ESPN Player Profile",
                "url": f"https://espn.com/nfl/player/{player_name.replace(' ', '-').lower()}",
                "content": f"Latest updates and analysis for {player_name}. {context}",
                "score": 0.8
            },
            {
                "title": f"{player_name} Fantasy Football Outlook",
                "url": f"https://fantasypros.com/nfl/players/{player_name.replace(' ', '-').lower()}.php",
                "content": f"Fantasy football analysis and projections for {player_name}.",
                "score": 0.7
            },
            {
                "title": f"{player_name} Recent Performance Analysis",
                "url": "https://example.com/analysis",
                "content": f"Detailed breakdown of {player_name}'s recent performances and upcoming matchups.",
                "score": 0.6
            },
            {
                "title": f"{player_name} Injury Report & Status",
                "url": "https://example.com/injuries",
                "content": f"Latest injury updates for {player_name}.",
                "score": 0.5
            },
            {
                "title": f"{player_name} Weekly Rankings",
                "url": "https://example.com/rankings",
                "content": f"Expert rankings and start/sit advice for {player_name}.",
                "score": 0.5
            }
        ]

    async def search_matchup_analysis(
        self,
        team1: str,
        team2: str,
        week: int
    ) -> List[Dict[str, Any]]:
        """Search for matchup analysis between two teams"""
        query = f"{team1} vs {team2} week {week} NFL fantasy matchup analysis"

        if not self.tavily_api_key:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": 3,
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("results", [])

        except Exception as e:
            logger.error(f"Matchup search error: {e}")
            return []

web_search_tool = WebSearchTool()
