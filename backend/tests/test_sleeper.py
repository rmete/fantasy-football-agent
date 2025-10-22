import asyncio
from app.tools.sleeper_client import sleeper_client
from app.core.config import settings

async def test_sleeper_integration():
    """Test Sleeper API integration"""

    print("\n🧪 Testing Sleeper API Integration\n")
    print("=" * 60)

    if not settings.SLEEPER_USERNAME:
        print("❌ ERROR: SLEEPER_USERNAME not set in .env")
        print("\nPlease set your Sleeper username in the .env file:")
        print("SLEEPER_USERNAME=your_username")
        return

    print(f"✓ Testing with username: {settings.SLEEPER_USERNAME}\n")

    # Test 1: Get user
    print("1. Testing get_user...")
    user = await sleeper_client.get_user(settings.SLEEPER_USERNAME)
    if user:
        print(f"   ✓ User found: {user['display_name']} (ID: {user['user_id']})")
    else:
        print("   ✗ Failed to get user")
        await sleeper_client.close()
        return

    # Test 2: Get leagues
    print("\n2. Testing get_user_leagues...")
    leagues = await sleeper_client.get_user_leagues(user['user_id'], "nfl", "2024")
    if leagues:
        print(f"   ✓ Found {len(leagues)} leagues")
        for i, league in enumerate(leagues[:3], 1):
            print(f"   {i}. {league['name']} ({league['total_rosters']} teams)")
    else:
        print("   ✗ No leagues found")
        await sleeper_client.close()
        return

    # Test 3: Get league details
    if leagues:
        league_id = leagues[0]['league_id']
        print(f"\n3. Testing get_league for '{leagues[0]['name']}'...")
        league = await sleeper_client.get_league(league_id)
        if league:
            print(f"   ✓ League details retrieved")
            print(f"      Season: {league['season']}")
            print(f"      Status: {league['status']}")
        else:
            print("   ✗ Failed to get league details")

    # Test 4: Get rosters
    if leagues:
        league_id = leagues[0]['league_id']
        print(f"\n4. Testing get_league_rosters...")
        rosters = await sleeper_client.get_league_rosters(league_id)
        if rosters:
            print(f"   ✓ Found {len(rosters)} rosters")
            # Show sample roster
            if rosters:
                sample = rosters[0]
                print(f"      Sample roster #{sample['roster_id']}:")
                print(f"      - Players: {len(sample.get('players', []))}")
                print(f"      - Starters: {len(sample.get('starters', []))}")
                print(f"      - Record: {sample.get('wins', 0)}-{sample.get('losses', 0)}-{sample.get('ties', 0)}")
        else:
            print("   ✗ Failed to get rosters")

    # Test 5: Get players (cached)
    print("\n5. Testing get_players (this may take a moment)...")
    players = await sleeper_client.get_players()
    if players:
        print(f"   ✓ Loaded {len(players)} players")
        # Show a sample player
        sample_id = list(players.keys())[0]
        sample = players[sample_id]
        print(f"      Sample: {sample.get('full_name', 'Unknown')} - {sample.get('position', 'N/A')} - {sample.get('team', 'FA')}")
    else:
        print("   ✗ Failed to get players")

    # Test 6: Get trending players
    print("\n6. Testing get_trending_players...")
    trending = await sleeper_client.get_trending_players("nfl", "add")
    if trending:
        print(f"   ✓ Found {len(trending)} trending adds")
        for i, player in enumerate(trending[:3], 1):
            player_id = player.get('player_id')
            count = player.get('count', 0)
            if player_id and player_id in players:
                name = players[player_id].get('full_name', 'Unknown')
                print(f"   {i}. {name} ({count} adds)")
    else:
        print("   ⚠ No trending players (may be off-season)")

    await sleeper_client.close()

    print("\n" + "=" * 60)
    print("✅ All Sleeper API tests completed!\n")
    print("Next steps:")
    print("1. Visit http://localhost:8000/docs to see the API endpoints")
    print("2. Test endpoints in the interactive API docs")
    print("3. Proceed to Phase 3 for database integration\n")

if __name__ == "__main__":
    asyncio.run(test_sleeper_integration())
