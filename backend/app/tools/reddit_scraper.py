import asyncpraw
from typing import List, Dict, Any, Optional
from app.core.config import settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RedditSentimentTool:
    """Tool for analyzing player sentiment on Reddit"""

    def __init__(self):
        self.reddit = None
        self._reddit_config = {
            "client_id": settings.REDDIT_CLIENT_ID,
            "client_secret": settings.REDDIT_CLIENT_SECRET,
            "user_agent": settings.REDDIT_USER_AGENT or "FantasyFootballAI/1.0"
        }

    async def _get_reddit_client(self):
        """Get or create async Reddit client"""
        if not all([settings.REDDIT_CLIENT_ID, settings.REDDIT_CLIENT_SECRET]):
            logger.warning("Reddit API credentials not set")
            return None

        try:
            reddit = asyncpraw.Reddit(**self._reddit_config)
            logger.info("Async Reddit client initialized")
            return reddit
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            return None

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
                "confidence": str
            }
        """

        reddit = await self._get_reddit_client()
        if not reddit:
            return self._empty_sentiment(player_name)

        try:
            subreddit_obj = await reddit.subreddit(subreddit)

            # Search for player mentions
            search_query = player_name
            posts = subreddit_obj.search(
                search_query,
                time_filter=time_filter,
                limit=limit
            )

            comments_data = []
            async for post in posts:
                # Get top comments from each post
                await post.comments.replace_more(limit=0)
                comments_list = post.comments.list()
                if comments_list:  # Check if list is not None
                    for comment in comments_list[:10]:
                        if hasattr(comment, 'body') and player_name.lower() in comment.body.lower():
                            comments_data.append({
                                "text": comment.body,
                                "score": comment.score,
                                "created": datetime.fromtimestamp(comment.created_utc)
                            })

            # Analyze sentiment (simple keyword-based for now)
            sentiment = self._analyze_sentiment(comments_data, player_name)

            # Close the Reddit session
            await reddit.close()

            return sentiment

        except Exception as e:
            logger.error(f"Reddit sentiment error: {e}")
            if reddit:
                await reddit.close()
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
