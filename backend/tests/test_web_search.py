"""
Comprehensive tests for web search functionality - NO MOCKS
Tests both Tavily and DuckDuckGo search implementations
"""
import asyncio
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tools.web_search import WebSearchTool
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_duckduckgo_search():
    """Test DuckDuckGo search directly (no Tavily)"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: DuckDuckGo Direct Search")
    logger.info("="*60)

    tool = WebSearchTool()

    # Force DuckDuckGo by calling _duckduckgo_search directly
    query = "Patrick Mahomes NFL fantasy football week 8 2025"

    try:
        results = await tool._duckduckgo_search(query, max_results=3)

        assert isinstance(results, list), "Results should be a list"
        assert len(results) > 0, "DuckDuckGo should return at least one result"
        assert len(results) <= 3, "Should not exceed max_results"

        logger.info(f"✓ DuckDuckGo returned {len(results)} results")

        for idx, result in enumerate(results, 1):
            logger.info(f"\nResult {idx}:")
            logger.info(f"  Title: {result.get('title', 'N/A')}")
            logger.info(f"  URL: {result.get('url', 'N/A')}")
            logger.info(f"  Content: {result.get('content', 'N/A')[:100]}...")
            logger.info(f"  Score: {result.get('score', 'N/A')}")

            # Validate structure
            assert 'title' in result, "Result must have title"
            assert 'url' in result, "Result must have url"
            assert 'content' in result, "Result must have content"
            assert 'score' in result, "Result must have score"

            # Validate data types
            assert isinstance(result['title'], str), "Title must be string"
            assert isinstance(result['url'], str), "URL must be string"
            assert isinstance(result['content'], str), "Content must be string"
            assert isinstance(result['score'], (int, float)), "Score must be numeric"

            # Validate non-empty
            assert len(result['title']) > 0, "Title should not be empty"
            assert len(result['url']) > 0, "URL should not be empty"
            assert result['url'].startswith('http'), "URL should be valid HTTP(S) URL"

        logger.info("\n✓ DuckDuckGo search test PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ DuckDuckGo search test FAILED: {e}")
        raise


async def test_tavily_search_if_available():
    """Test Tavily search if API key is configured"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Tavily Search (if API key available)")
    logger.info("="*60)

    tool = WebSearchTool()

    if not settings.TAVILY_API_KEY:
        logger.info("⊘ Skipping Tavily test - no API key configured")
        logger.info("  Set TAVILY_API_KEY in .env to test Tavily")
        return True

    try:
        results = await tool.search_player_news("Patrick Mahomes", max_results=3)

        assert isinstance(results, list), "Results should be a list"
        assert len(results) > 0, "Should return at least one result"

        logger.info(f"✓ Tavily returned {len(results)} results")

        for idx, result in enumerate(results, 1):
            logger.info(f"\nResult {idx}:")
            logger.info(f"  Title: {result.get('title', 'N/A')}")
            logger.info(f"  URL: {result.get('url', 'N/A')}")
            logger.info(f"  Content: {result.get('content', 'N/A')[:100]}...")
            logger.info(f"  Score: {result.get('score', 'N/A')}")

            # Validate structure
            assert 'title' in result
            assert 'url' in result
            assert 'content' in result
            assert 'score' in result

        logger.info("\n✓ Tavily search test PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Tavily search test FAILED: {e}")
        raise


async def test_fallback_behavior():
    """Test that Tavily failures fallback to DuckDuckGo"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Fallback Behavior (Tavily → DuckDuckGo)")
    logger.info("="*60)

    tool = WebSearchTool()
    original_key = tool.tavily_api_key

    try:
        # Temporarily disable Tavily to force fallback
        tool.tavily_api_key = None

        results = await tool.search_player_news("Josh Allen", max_results=3)

        assert isinstance(results, list), "Fallback should return a list"
        assert len(results) > 0, "Fallback should return results"

        logger.info(f"✓ Fallback returned {len(results)} results via DuckDuckGo")

        for idx, result in enumerate(results[:2], 1):
            logger.info(f"\nFallback Result {idx}:")
            logger.info(f"  Title: {result.get('title', 'N/A')}")
            logger.info(f"  URL: {result.get('url', 'N/A')}")

        logger.info("\n✓ Fallback behavior test PASSED")
        return True

    finally:
        # Restore original API key
        tool.tavily_api_key = original_key


async def test_general_search():
    """Test the general_search method used by chat agent"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: General Search (Chat Agent Method)")
    logger.info("="*60)

    tool = WebSearchTool()

    try:
        # Test with a general fantasy football question
        query = "best fantasy football waiver wire pickups week 8 2025"
        results = await tool.general_search(query, max_results=5)

        assert isinstance(results, list), "Results should be a list"
        assert len(results) > 0, "Should return at least one result"
        assert len(results) <= 5, "Should respect max_results"

        logger.info(f"✓ General search returned {len(results)} results")

        for idx, result in enumerate(results[:3], 1):
            logger.info(f"\nResult {idx}:")
            logger.info(f"  Title: {result.get('title', 'N/A')}")
            logger.info(f"  URL: {result.get('url', 'N/A')}")
            logger.info(f"  Content: {result.get('content', 'N/A')[:100]}...")

            # Validate structure
            assert 'title' in result
            assert 'url' in result
            assert 'content' in result

        logger.info("\n✓ General search test PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ General search test FAILED: {e}")
        raise


async def test_matchup_search():
    """Test matchup analysis search"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Matchup Analysis Search")
    logger.info("="*60)

    tool = WebSearchTool()

    try:
        results = await tool.search_matchup_analysis("Chiefs", "Raiders", week=8)

        assert isinstance(results, list), "Results should be a list"
        # Results might be empty if no API key, that's okay

        if len(results) > 0:
            logger.info(f"✓ Matchup search returned {len(results)} results")

            for idx, result in enumerate(results[:2], 1):
                logger.info(f"\nResult {idx}:")
                logger.info(f"  Title: {result.get('title', 'N/A')}")
                logger.info(f"  URL: {result.get('url', 'N/A')}")
        else:
            logger.info("⊘ Matchup search returned no results (may need Tavily API key)")

        logger.info("\n✓ Matchup search test PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Matchup search test FAILED: {e}")
        raise


async def test_player_news_search():
    """Test player-specific news search"""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Player News Search")
    logger.info("="*60)

    tool = WebSearchTool()

    try:
        # Test with multiple players
        players = ["Lamar Jackson", "Christian McCaffrey", "Travis Kelce"]

        for player in players:
            logger.info(f"\nSearching news for: {player}")
            results = await tool.search_player_news(player, additional_context="injury update", max_results=2)

            assert isinstance(results, list), f"Results for {player} should be a list"
            assert len(results) > 0, f"Should return results for {player}"

            logger.info(f"  ✓ Found {len(results)} articles for {player}")

            if results:
                logger.info(f"  Top article: {results[0].get('title', 'N/A')}")

        logger.info("\n✓ Player news search test PASSED")
        return True

    except Exception as e:
        logger.error(f"✗ Player news search test FAILED: {e}")
        raise


async def main():
    """Run all web search tests"""
    logger.info("\n" + "="*70)
    logger.info("COMPREHENSIVE WEB SEARCH TESTS - NO MOCKS")
    logger.info("="*70)
    logger.info(f"Tavily API Key configured: {bool(settings.TAVILY_API_KEY)}")
    logger.info("="*70)

    tests = [
        ("DuckDuckGo Direct Search", test_duckduckgo_search),
        ("Tavily Search", test_tavily_search_if_available),
        ("Fallback Behavior", test_fallback_behavior),
        ("General Search", test_general_search),
        ("Matchup Search", test_matchup_search),
        ("Player News Search", test_player_news_search),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            await test_func()
            results.append((test_name, "PASSED"))
        except Exception as e:
            logger.error(f"Test '{test_name}' failed with error: {e}")
            results.append((test_name, f"FAILED: {str(e)}"))

    # Print summary
    logger.info("\n" + "="*70)
    logger.info("TEST SUMMARY")
    logger.info("="*70)

    passed = 0
    failed = 0

    for test_name, result in results:
        status = "✓" if result == "PASSED" else "✗"
        logger.info(f"{status} {test_name}: {result}")
        if result == "PASSED":
            passed += 1
        else:
            failed += 1

    logger.info("="*70)
    logger.info(f"Total: {len(results)} tests | Passed: {passed} | Failed: {failed}")
    logger.info("="*70)

    if failed > 0:
        sys.exit(1)
    else:
        logger.info("\n🎉 ALL TESTS PASSED! 🎉\n")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
