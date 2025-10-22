"""
Test API endpoints using httpx

Run from backend directory:
    python tests/test_api.py
"""

import asyncio
import httpx
from app.core.config import settings

API_BASE = "http://localhost:8000"

async def test_api_endpoints():
    """Test API endpoints"""

    print("\n🧪 Testing API Endpoints\n")
    print("=" * 60)

    if not settings.SLEEPER_USERNAME:
        print("❌ ERROR: SLEEPER_USERNAME not set in .env")
        return

    async with httpx.AsyncClient() as client:

        # Test 1: Health check
        print("1. Testing /health endpoint...")
        try:
            response = await client.get(f"{API_BASE}/health")
            if response.status_code == 200:
                print(f"   ✓ Health check passed: {response.json()}")
            else:
                print(f"   ✗ Health check failed: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            print("\n   Make sure the backend is running:")
            print("   docker-compose up -d backend")
            return

        # Test 2: Get user
        print("\n2. Testing /api/v1/sleeper/user/{username}...")
        try:
            response = await client.get(
                f"{API_BASE}/api/v1/sleeper/user/{settings.SLEEPER_USERNAME}"
            )
            if response.status_code == 200:
                user = response.json()
                print(f"   ✓ User: {user['display_name']}")
            else:
                print(f"   ✗ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

        # Test 3: Get user leagues
        print("\n3. Testing /api/v1/sleeper/user/{username}/leagues...")
        try:
            response = await client.get(
                f"{API_BASE}/api/v1/sleeper/user/{settings.SLEEPER_USERNAME}/leagues"
            )
            if response.status_code == 200:
                data = response.json()
                leagues = data['leagues']
                print(f"   ✓ Found {len(leagues)} leagues")
                if leagues:
                    league_id = leagues[0]['league_id']
                    league_name = leagues[0]['name']
                    print(f"      First league: {league_name}")

                    # Test 4: Get league details
                    print(f"\n4. Testing /api/v1/sleeper/league/{league_id}...")
                    response = await client.get(
                        f"{API_BASE}/api/v1/sleeper/league/{league_id}"
                    )
                    if response.status_code == 200:
                        league_data = response.json()
                        print(f"   ✓ League details retrieved")
                        print(f"      Rosters: {len(league_data['rosters'])}")
                        print(f"      Users: {len(league_data['users'])}")
                    else:
                        print(f"   ✗ Failed: {response.status_code}")

            else:
                print(f"   ✗ Failed: {response.status_code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ API endpoint tests completed!\n")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
