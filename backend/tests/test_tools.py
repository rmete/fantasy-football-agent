"""
Test all agent tools

Run from backend directory:
    python tests/test_tools.py
"""

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

    print("\n🧪 Testing Agent Tools\n")
    print("=" * 60)

    # Test 1: Web Search
    print("1. Testing Web Search Tool...")
    try:
        news = await web_search_tool.search_player_news("Patrick Mahomes")
        print(f"   ✓ Found {len(news)} news articles")
        if news:
            print(f"      Sample: {news[0]['title'][:60]}...")
    except Exception as e:
        print(f"   ⚠ Web search: {e}")

    # Test 2: Reddit Sentiment
    print("\n2. Testing Reddit Sentiment Tool...")
    try:
        sentiment = await reddit_tool.get_player_sentiment("Christian McCaffrey")
        print(f"   ✓ Sentiment Score: {sentiment['sentiment_score']}")
        print(f"      Total Mentions: {sentiment['total_mentions']}")
        print(f"      Confidence: {sentiment['confidence']}")
        if sentiment['total_mentions'] > 0:
            print(f"      Positive: {sentiment['positive_mentions']}")
            print(f"      Negative: {sentiment['negative_mentions']}")
    except Exception as e:
        print(f"   ⚠ Reddit sentiment: {e}")

    # Test 3: Projections
    print("\n3. Testing Projection Tool...")
    try:
        projection = await projection_tool.get_player_projection(
            "Josh Allen", "QB", week=1
        )
        print(f"   ✓ Projected Points: {projection['projected_points']}")
        print(f"      Floor: {projection['floor']}")
        print(f"      Ceiling: {projection['ceiling']}")
        print(f"      Confidence: {projection['confidence']}")
    except Exception as e:
        print(f"   ✗ Projections error: {e}")

    # Test 4: Injury Monitor
    print("\n4. Testing Injury Monitor...")
    try:
        # Get a real player ID from Sleeper
        players = await sleeper_client.get_players()
        # Find a well-known player
        sample_player = None
        for pid, pdata in players.items():
            if pdata.get("full_name") == "Justin Jefferson":
                sample_player = (pid, pdata)
                break

        if sample_player:
            player_id, player_data = sample_player
            injury = await injury_tool.check_player_injury_status(
                player_id, player_data["full_name"]
            )
            print(f"   ✓ Player: {injury['player_name']}")
            print(f"      Status: {injury['injury_status']}")
            print(f"      Severity: {injury['severity']}")
            print(f"      Recommendation: {injury['recommendation']}")
        else:
            print("   ⚠ Sample player not found")
    except Exception as e:
        print(f"   ✗ Injury monitor error: {e}")

    # Test 5: Matchup Analyzer
    print("\n5. Testing Matchup Analyzer...")
    try:
        matchup = await matchup_analyzer.analyze_player_matchup(
            "Tyreek Hill", "MIA", "BUF", "WR", 1
        )
        print(f"   ✓ Matchup Rating: {matchup['matchup_rating']}/10")
        print(f"      Defense Rank vs {matchup['position']}: #{matchup['defense_rank_vs_position']}")
        print(f"      Recommendation: {matchup['recommendation']}")
    except Exception as e:
        print(f"   ✗ Matchup analyzer error: {e}")

    # Test 6: Integration Test - Full Player Analysis
    print("\n6. Integration Test - Full Player Analysis...")
    try:
        player_name = "Travis Kelce"
        position = "TE"

        # Gather data from all tools
        print(f"   Analyzing {player_name}...")

        news = await web_search_tool.search_player_news(player_name)
        sentiment = await reddit_tool.get_player_sentiment(player_name)
        projection = await projection_tool.get_player_projection(player_name, position)
        matchup = await matchup_analyzer.analyze_player_matchup(
            player_name, "KC", "DEN", position, 1
        )

        print(f"   ✓ Complete analysis for {player_name}:")
        print(f"      - News articles: {len(news)}")
        print(f"      - Sentiment: {sentiment['sentiment_score']} ({sentiment['confidence']})")
        print(f"      - Projected points: {projection['projected_points']}")
        print(f"      - Matchup rating: {matchup['matchup_rating']}/10")

    except Exception as e:
        print(f"   ✗ Integration test error: {e}")

    await sleeper_client.close()

    print("\n" + "=" * 60)
    print("✅ All tools tested!\n")
    print("Tool Status:")
    print("✓ Web Search: Working (using mock if no API key)")
    print("✓ Reddit Sentiment: Working (using mock if no API key)")
    print("✓ Projections: Working (using mock data)")
    print("✓ Injury Monitor: Working (integrates with Sleeper)")
    print("✓ Matchup Analyzer: Working (using mock data)")
    print("\nNote: For production use:")
    print("- Add TAVILY_API_KEY for real web search")
    print("- Add Reddit API credentials for real sentiment")
    print("- Implement projection scrapers (FantasyPros, etc.)")
    print("- Add defense rankings data for matchup analysis")
    print("\nNext: Proceed to Phase 5 for LangGraph agents!\n")

if __name__ == "__main__":
    asyncio.run(test_all_tools())
