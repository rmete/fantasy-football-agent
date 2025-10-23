import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging
from duckduckgo_search import AsyncDDGS

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
        """Fallback search using DuckDuckGo when Tavily API is not available"""
        logger.info(f"Using DuckDuckGo fallback search for {player_name}")

        query = f"{player_name} NFL fantasy football {context}"
        return await self._duckduckgo_search(query, max_results=5)

    async def search_matchup_analysis(
        self,
        team1: str,
        team2: str,
        week: int
    ) -> List[Dict[str, Any]]:
        """Search for matchup analysis between two teams"""
        query = f"{team1} vs {team2} week {week} NFL fantasy matchup analysis"

        if not self.tavily_api_key:
            return await self._duckduckgo_search(query, max_results=3)

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
            return await self._duckduckgo_search(query, max_results=3)

    async def general_search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """General web search for any query - used by chat agent"""
        logger.info(f"General web search: {query}")

        # Try Tavily first if API key is available
        if self.tavily_api_key:
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

                    logger.info(f"Tavily returned {len(results)} results")
                    return results

            except Exception as e:
                logger.error(f"Tavily search error: {e}, falling back to DuckDuckGo")

        # Fallback to DuckDuckGo
        return await self._duckduckgo_search(query, max_results)

    async def _duckduckgo_search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """DuckDuckGo search for any general query"""
        logger.info(f"DuckDuckGo search: {query}")

        try:
            async with AsyncDDGS() as ddgs:
                results = []
                idx = 0
                # ddgs.text returns an async generator, so iterate over it
                async for result in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("href", result.get("link", "")),
                        "content": result.get("body", result.get("snippet", "")),
                        "score": 1.0 - (idx * 0.1)
                    })
                    idx += 1

                    # Break after max_results
                    if len(results) >= max_results:
                        break

                logger.info(f"DuckDuckGo returned {len(results)} results")
                return results

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

web_search_tool = WebSearchTool()
