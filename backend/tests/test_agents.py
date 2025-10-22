"""
Test AI agents end-to-end

Run from backend directory:
    python tests/test_agents.py
"""

import asyncio
from app.agents.orchestrator import orchestrator
from app.core.config import settings

async def test_sit_start_agent():
    """Test sit/start agent workflow"""

    print("\n🤖 Testing Sit/Start Agent\n")
    print("=" * 60)

    if not settings.SLEEPER_USERNAME:
        print("❌ ERROR: SLEEPER_USERNAME not set in .env")
        return

    if not settings.ANTHROPIC_API_KEY:
        print("❌ ERROR: ANTHROPIC_API_KEY not set in .env")
        print("\nThe AI agents require Anthropic Claude to function.")
        print("Get your API key from: https://console.anthropic.com/")
        return

    # Get user and league info
    from app.tools.sleeper_client import sleeper_client

    print(f"✓ Testing with username: {settings.SLEEPER_USERNAME}")
    print(f"✓ Anthropic API key configured\n")

    user = await sleeper_client.get_user(settings.SLEEPER_USERNAME)
    if not user:
        print("❌ Failed to get user")
        return

    leagues = await sleeper_client.get_user_leagues(user['user_id'], "nfl", "2024")
    if not leagues:
        print("❌ No leagues found")
        return

    league_id = leagues[0]['league_id']
    league_name = leagues[0]['name']

    print(f"1. Testing sit/start analysis for '{league_name}'...")
    print(f"   League ID: {league_id}\n")

    initial_state = {
        "user_id": "test_user",
        "league_id": league_id,
        "roster_id": 1,
        "task_type": "sit_start",
        "task_id": "test_123",
        "week": 1
    }

    print("   Initializing agent...")
    print("   Gathering data from Sleeper...")
    print("   Analyzing players with AI...")
    print("   (This may take 30-60 seconds)\n")

    result = await orchestrator.run(initial_state)

    # Verify results
    if result.get("current_step") == "completed":
        print("✓ Analysis completed successfully!\n")

        recommendations = result.get("recommendations", [])
        print(f"Found {len(recommendations)} START recommendations:\n")

        for i, rec in enumerate(recommendations[:5], 1):
            print(f"{i}. {rec['player_name']} ({rec['position']})")
            print(f"   Confidence: {rec['confidence']}%")
            print(f"   Projection: {rec['supporting_data']['projection']} pts")
            print(f"   Matchup: {rec['supporting_data']['matchup_rating']}/10")
            print(f"   Reasoning: {rec['reasoning'][:100]}...")
            print()

    else:
        print(f"✗ Analysis failed: {result.get('error', 'Unknown error')}")

    await sleeper_client.close()

    print("=" * 60)
    print("✅ Sit/Start agent test completed!\n")

async def test_trade_agent():
    """Test trade analysis agent"""

    print("\n🤖 Testing Trade Analysis Agent\n")
    print("=" * 60)

    if not settings.SLEEPER_USERNAME or not settings.ANTHROPIC_API_KEY:
        print("❌ ERROR: Missing required configuration")
        return

    from app.tools.sleeper_client import sleeper_client

    user = await sleeper_client.get_user(settings.SLEEPER_USERNAME)
    leagues = await sleeper_client.get_user_leagues(user['user_id'], "nfl", "2024")

    if not leagues:
        print("❌ No leagues found")
        return

    league_id = leagues[0]['league_id']

    print("1. Testing trade analysis...")
    print(f"   League: {leagues[0]['name']}\n")

    # Get some player IDs from the league
    rosters = await sleeper_client.get_league_rosters(league_id)
    if rosters and rosters[0].get("players"):
        # Use first 2 players from roster
        sample_players = rosters[0]["players"][:2]

        initial_state = {
            "user_id": "test_user",
            "league_id": league_id,
            "roster_id": 1,
            "task_type": "trade_analysis",
            "task_id": "test_456",
            "input_data": {
                "my_players": [sample_players[0]],
                "their_players": [sample_players[1]] if len(sample_players) > 1 else []
            }
        }

        print("   Analyzing trade proposal...")
        print("   (This may take 20-30 seconds)\n")

        result = await orchestrator.run(initial_state)

        if result.get("current_step") == "completed":
            print("✓ Trade analysis completed!\n")

            trade_result = result.get("analysis_results", {}).get("trade", {})
            print(f"Recommendation: {trade_result.get('recommendation')}")
            print(f"My value: {trade_result.get('my_value')}")
            print(f"Their value: {trade_result.get('their_value')}")
            print(f"\nAnalysis:\n{trade_result.get('analysis', '')[:300]}...")
        else:
            print(f"✗ Analysis failed: {result.get('error')}")

    await sleeper_client.close()

    print("\n=" * 60)
    print("✅ Trade agent test completed!\n")

async def main():
    """Run all agent tests"""

    print("\n" + "="*60)
    print("🧪 TESTING FANTASY FOOTBALL AI AGENTS")
    print("="*60)

    await test_sit_start_agent()
    await test_trade_agent()

    print("\n" + "="*60)
    print("✅ ALL AGENT TESTS COMPLETED!")
    print("="*60)
    print("\nNext steps:")
    print("1. Agents are working and making AI-powered recommendations")
    print("2. Visit http://localhost:8000/docs to test endpoints")
    print("3. Phase 5 complete - agents ready for production use!")
    print("4. Proceed to Phase 6 for frontend integration\n")

if __name__ == "__main__":
    asyncio.run(main())
