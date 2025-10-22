# Phase 4: Agent Tools

**Goal**: Build individual tools that LangGraph agents will use to gather data and make decisions

**Estimated Time**: 8-10 hours

**Dependencies**: Phase 1, 2, 3

## Overview

This phase creates the specialized tools that AI agents will use:
- Web search for player news
- Reddit sentiment analysis
- Twitter/X scraping for breaking news
- Projection aggregation from multiple sources
- Injury monitoring
- Matchup analysis
- Sentiment scoring

## Tasks Breakdown

### Task 4.1: Web Search Tool (Tavily/SerpAPI)

#### backend/app/tools/web_search.py

```python
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
            return []

    async def _fallback_search(self, player_name: str, context: str) -> List[Dict[str, Any]]:
        """Fallback search using DuckDuckGo (no API key required)"""
        # Implement a simple web scraper or use an alternative free API
        # For now, return empty list
        logger.info("Fallback search not implemented")
        return []

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
```

### Task 4.2: Reddit Sentiment Tool

#### backend/app/tools/reddit_scraper.py

```python
import praw
from typing import List, Dict, Any, Optional
from app.core.config import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RedditSentimentTool:
    """Tool for analyzing player sentiment on Reddit"""

    def __init__(self):
        self.reddit = None
        self._initialize_reddit()

    def _initialize_reddit(self):
        """Initialize Reddit API client"""
        if not all([settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET]):
            logger.warning("Reddit API credentials not set")
            return

        try:
            self.reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=settings.REDDIT_USER_AGENT or "FantasyFootballAI/1.0"
            )
            logger.info("Reddit client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")

    async def get_player_sentiment(
        self,
        player_name: str,
        subreddit: str = "fantasyfootball",
        limit: int = 50,
        time_filter: str = "week"
    ) -> Dict[str, Any]:
        """
        Analyze Reddit sentiment for a player

        Returns:
            {
                "player": str,
                "total_mentions": int,
                "positive_mentions": int,
                "negative_mentions": int,
                "neutral_mentions": int,
                "sentiment_score": float,  # -1 to 1
                "top_comments": List[str],
                "keywords": List[str]
            }
        """

        if not self.reddit:
            return self._empty_sentiment(player_name)

        try:
            subreddit_obj = self.reddit.subreddit(subreddit)

            # Search for player mentions
            search_query = player_name
            posts = subreddit_obj.search(
                search_query,
                time_filter=time_filter,
                limit=limit
            )

            comments_data = []
            for post in posts:
                # Get top comments from each post
                post.comments.replace_more(limit=0)
                for comment in post.comments.list()[:10]:
                    if player_name.lower() in comment.body.lower():
                        comments_data.append({
                            "text": comment.body,
                            "score": comment.score,
                            "created": datetime.fromtimestamp(comment.created_utc)
                        })

            # Analyze sentiment (simple keyword-based for now)
            sentiment = self._analyze_sentiment(comments_data, player_name)

            return sentiment

        except Exception as e:
            logger.error(f"Reddit sentiment error: {e}")
            return self._empty_sentiment(player_name)

    def _analyze_sentiment(self, comments: List[Dict], player_name: str) -> Dict[str, Any]:
        """Analyze sentiment from comments"""

        positive_keywords = [
            "great", "excellent", "good", "love", "best", "amazing", "strong",
            "boom", "smash", "rb1", "wr1", "league winner", "breakout", "start"
        ]
        negative_keywords = [
            "bad", "terrible", "worst", "hate", "bust", "avoid", "drop",
            "sit", "bench", "injured", "out", "questionable", "sell"
        ]

        positive = 0
        negative = 0
        neutral = 0

        top_comments = []

        for comment in comments:
            text_lower = comment["text"].lower()

            pos_count = sum(1 for word in positive_keywords if word in text_lower)
            neg_count = sum(1 for word in negative_keywords if word in text_lower)

            if pos_count > neg_count:
                positive += 1
            elif neg_count > pos_count:
                negative += 1
            else:
                neutral += 1

            # Save high-scoring comments
            if comment["score"] > 5:
                top_comments.append({
                    "text": comment["text"][:200],
                    "score": comment["score"]
                })

        total = positive + negative + neutral
        sentiment_score = 0.0
        if total > 0:
            sentiment_score = (positive - negative) / total

        # Sort comments by score
        top_comments = sorted(top_comments, key=lambda x: x["score"], reverse=True)[:5]

        return {
            "player": player_name,
            "total_mentions": total,
            "positive_mentions": positive,
            "negative_mentions": negative,
            "neutral_mentions": neutral,
            "sentiment_score": round(sentiment_score, 2),
            "top_comments": [c["text"] for c in top_comments],
            "confidence": "high" if total > 10 else "medium" if total > 5 else "low"
        }

    def _empty_sentiment(self, player_name: str) -> Dict[str, Any]:
        """Return empty sentiment data"""
        return {
            "player": player_name,
            "total_mentions": 0,
            "positive_mentions": 0,
            "negative_mentions": 0,
            "neutral_mentions": 0,
            "sentiment_score": 0.0,
            "top_comments": [],
            "confidence": "none"
        }

reddit_tool = RedditSentimentTool()
```

### Task 4.3: Projection Aggregator Tool

#### backend/app/tools/projections.py

```python
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class ProjectionTool:
    """Tool for aggregating player projections from multiple sources"""

    async def get_player_projection(
        self,
        player_name: str,
        position: str,
        week: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated projection for a player

        Returns:
            {
                "player": str,
                "position": str,
                "week": int,
                "projected_points": float,
                "floor": float,
                "ceiling": float,
                "confidence": str,
                "sources": List[Dict]
            }
        """

        # For MVP, we'll use a mock projection system
        # In production, scrape FantasyPros, ESPN, Yahoo, etc.

        projection_data = await self._fetch_mock_projection(player_name, position, week)

        return projection_data

    async def _fetch_mock_projection(
        self,
        player_name: str,
        position: str,
        week: Optional[int]
    ) -> Dict[str, Any]:
        """
        Mock projection data
        In production, implement scraping from:
        - FantasyPros consensus
        - ESPN projections
        - Yahoo projections
        - NFL.com projections
        """

        # This would be replaced with actual scraping logic
        base_projections = {
            "QB": {"points": 18.5, "floor": 12.0, "ceiling": 28.0},
            "RB": {"points": 12.3, "floor": 6.0, "ceiling": 20.0},
            "WR": {"points": 11.8, "floor": 5.0, "ceiling": 22.0},
            "TE": {"points": 8.2, "floor": 3.0, "ceiling": 15.0},
        }

        proj = base_projections.get(position, {"points": 10.0, "floor": 5.0, "ceiling": 15.0})

        return {
            "player": player_name,
            "position": position,
            "week": week or "current",
            "projected_points": proj["points"],
            "floor": proj["floor"],
            "ceiling": proj["ceiling"],
            "confidence": "medium",
            "sources": [
                {"name": "Mock Projection", "points": proj["points"]}
            ],
            "note": "Using mock data - implement real scrapers in production"
        }

    async def get_weekly_rankings(
        self,
        position: str,
        week: int,
        scoring_format: str = "PPR"
    ) -> List[Dict[str, Any]]:
        """Get top players at a position for the week"""

        # Mock implementation
        # In production, scrape FantasyPros weekly rankings

        return []

projection_tool = ProjectionTool()
```

### Task 4.4: Injury Monitor Tool

#### backend/app/tools/injury_monitor.py

```python
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
        injury_status: Optional[str],
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
        injury_status: Optional[str],
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
```

### Task 4.5: Matchup Analyzer Tool

#### backend/app/tools/matchup_analyzer.py

```python
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class MatchupAnalyzerTool:
    """Tool for analyzing player matchups and opponent strength"""

    def __init__(self):
        # In production, load historical defense rankings, Vegas lines, etc.
        self.defense_rankings = {}

    async def analyze_player_matchup(
        self,
        player_name: str,
        player_team: str,
        opponent_team: str,
        position: str,
        week: int
    ) -> Dict[str, Any]:
        """
        Analyze a player's matchup

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
                "recommendation": str
            }
        """

        # Mock implementation
        # In production:
        # - Fetch defense rankings vs position
        # - Get Vegas lines and totals
        # - Check weather conditions
        # - Analyze historical matchups

        matchup_rating = self._calculate_matchup_rating(
            opponent_team,
            position
        )

        return {
            "player": player_name,
            "player_team": player_team,
            "opponent": opponent_team,
            "position": position,
            "week": week,
            "matchup_rating": matchup_rating,
            "defense_rank_vs_position": 15,  # Mock
            "points_allowed_avg": 18.5,  # Mock
            "home_away": "Home",
            "recommendation": self._generate_matchup_recommendation(matchup_rating)
        }

    def _calculate_matchup_rating(
        self,
        opponent: str,
        position: str
    ) -> float:
        """Calculate matchup favorability (0-10)"""

        # Mock implementation
        # In production, use actual defense rankings and stats

        # Default to neutral matchup
        return 5.5

    def _generate_matchup_recommendation(self, rating: float) -> str:
        """Generate recommendation based on matchup rating"""

        if rating >= 8:
            return "Excellent matchup - Start with confidence"
        elif rating >= 6:
            return "Favorable matchup - Good start option"
        elif rating >= 4:
            return "Neutral matchup - Moderate expectations"
        elif rating >= 2:
            return "Difficult matchup - Consider alternatives"
        else:
            return "Very tough matchup - Avoid if possible"

    async def analyze_team_matchups(
        self,
        roster_players: List[Dict[str, Any]],
        week: int
    ) -> List[Dict[str, Any]]:
        """Analyze matchups for entire roster"""

        matchups = []

        for player in roster_players:
            if player.get("opponent"):
                analysis = await self.analyze_player_matchup(
                    player["name"],
                    player["team"],
                    player["opponent"],
                    player["position"],
                    week
                )
                matchups.append(analysis)

        return matchups

matchup_analyzer = MatchupAnalyzerTool()
```

### Task 4.6: Tools Registry

#### backend/app/tools/__init__.py

```python
from app.tools.sleeper_client import sleeper_client
from app.tools.web_search import web_search_tool
from app.tools.reddit_scraper import reddit_tool
from app.tools.projections import projection_tool
from app.tools.injury_monitor import injury_tool
from app.tools.matchup_analyzer import matchup_analyzer

__all__ = [
    "sleeper_client",
    "web_search_tool",
    "reddit_tool",
    "projection_tool",
    "injury_tool",
    "matchup_analyzer",
]
```

## Testing Tools

#### backend/tests/test_tools.py

```python
import asyncio
from app.tools import (
    sleeper_client,
    web_search_tool,
    reddit_tool,
    projection_tool,
    injury_tool,
    matchup_analyzer
)

async def test_all_tools():
    """Test all agent tools"""

    print("🧪 Testing Agent Tools\n")

    # Test 1: Web Search
    print("1. Testing Web Search Tool...")
    news = await web_search_tool.search_player_news("Patrick Mahomes")
    print(f"   Found {len(news)} news articles")

    # Test 2: Reddit Sentiment
    print("\n2. Testing Reddit Sentiment Tool...")
    sentiment = await reddit_tool.get_player_sentiment("Christian McCaffrey")
    print(f"   Sentiment Score: {sentiment['sentiment_score']}")
    print(f"   Total Mentions: {sentiment['total_mentions']}")

    # Test 3: Projections
    print("\n3. Testing Projection Tool...")
    projection = await projection_tool.get_player_projection(
        "Josh Allen", "QB", week=1
    )
    print(f"   Projected Points: {projection['projected_points']}")

    # Test 4: Injury Monitor
    print("\n4. Testing Injury Monitor...")
    injury = await injury_tool.check_player_injury_status(
        "4881", "Justin Jefferson"
    )
    print(f"   Status: {injury['injury_status']}")
    print(f"   Recommendation: {injury['recommendation']}")

    # Test 5: Matchup Analyzer
    print("\n5. Testing Matchup Analyzer...")
    matchup = await matchup_analyzer.analyze_player_matchup(
        "Tyreek Hill", "MIA", "BUF", "WR", 1
    )
    print(f"   Matchup Rating: {matchup['matchup_rating']}/10")
    print(f"   Recommendation: {matchup['recommendation']}")

    await sleeper_client.close()
    print("\n✅ All tools tested!")

if __name__ == "__main__":
    asyncio.run(test_all_tools())
```

Run tests:
```bash
docker exec -it fantasy-backend python tests/test_tools.py
```

## Success Criteria

After Phase 4:

1. ✅ All tools can be imported without errors
2. ✅ Web search returns relevant news articles
3. ✅ Reddit tool can analyze sentiment (even if mocked)
4. ✅ Projection tool returns structured data
5. ✅ Injury monitor identifies injured players
6. ✅ Matchup analyzer rates matchups
7. ✅ All tools have proper error handling

## Next Steps

Proceed to **[Phase 5: LangGraph Agents](./phase-5-langgraph-agents.md)** to implement the AI orchestration layer.

## Resources

- [Tavily API Documentation](https://docs.tavily.com/)
- [PRAW Documentation](https://praw.readthedocs.io/)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
