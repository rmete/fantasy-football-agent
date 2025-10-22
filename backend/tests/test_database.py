"""
Test database operations

Run from backend directory:
    python tests/test_database.py
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import engine, AsyncSessionLocal, init_db, Base
from app.models import User, League, Roster
from app.crud.user import create_user, get_user_by_sleeper_id
from app.crud.league import get_or_create_league, upsert_roster

async def test_database():
    """Test database connectivity and basic CRUD"""

    print("\n🧪 Testing Database Operations\n")
    print("=" * 60)

    # Initialize database (create tables)
    print("1. Initializing database...")
    await init_db()
    print("   ✓ Database initialized")

    # Create test user
    print("\n2. Testing user creation...")
    async with AsyncSessionLocal() as session:
        # Check if user already exists
        existing = await get_user_by_sleeper_id(session, "test123")
        if existing:
            print(f"   ℹ User already exists: {existing.display_name}")
            test_user = existing
        else:
            test_user = await create_user(
                session,
                sleeper_user_id="test123",
                sleeper_username="testuser",
                display_name="Test User"
            )
            print(f"   ✓ Created user: {test_user.display_name}")

    # Retrieve user
    print("\n3. Testing user retrieval...")
    async with AsyncSessionLocal() as session:
        retrieved = await get_user_by_sleeper_id(session, "test123")
        if retrieved:
            print(f"   ✓ Retrieved user: {retrieved.display_name}")
            print(f"      - ID: {retrieved.id}")
            print(f"      - Sleeper ID: {retrieved.sleeper_user_id}")
            print(f"      - Username: {retrieved.sleeper_username}")
        else:
            print("   ✗ Failed to retrieve user")
            return

    # Create test league
    print("\n4. Testing league creation...")
    async with AsyncSessionLocal() as session:
        league_data = {
            "name": "Test League",
            "season": "2024",
            "sport": "nfl",
            "status": "in_season",
            "total_rosters": 12,
            "roster_positions": ["QB", "RB", "RB", "WR", "WR", "TE", "FLEX", "K", "DEF", "BN", "BN"],
            "scoring_settings": {"pass_td": 4, "rec": 1},
            "settings": {"waiver_type": 1}
        }

        league = await get_or_create_league(
            session,
            league_id="test_league_123",
            user_id=retrieved.id,
            league_data=league_data
        )
        print(f"   ✓ Created league: {league.name}")
        print(f"      - ID: {league.id}")
        print(f"      - Season: {league.season}")
        print(f"      - Status: {league.status}")

    # Create test roster
    print("\n5. Testing roster creation...")
    async with AsyncSessionLocal() as session:
        roster_data = {
            "roster_id": 1,
            "owner_id": "test123",
            "players": ["player1", "player2", "player3"],
            "starters": ["player1", "player2"],
            "wins": 5,
            "losses": 3,
            "ties": 0,
            "fpts": 1234.5,
            "settings": {}
        }

        roster = await upsert_roster(
            session,
            league_id="test_league_123",
            roster_data=roster_data
        )
        print(f"   ✓ Created roster #{roster.roster_id}")
        print(f"      - Players: {len(roster.players)}")
        print(f"      - Starters: {len(roster.starters)}")
        print(f"      - Record: {roster.wins}-{roster.losses}-{roster.ties}")

    # Test querying with relationships
    print("\n6. Testing relationships...")
    async with AsyncSessionLocal() as session:
        # Eagerly load the leagues relationship
        result = await session.execute(
            select(User)
            .options(selectinload(User.leagues))
            .where(User.sleeper_user_id == "test123")
        )
        user = result.scalar_one_or_none()
        if user and user.leagues:
            print(f"   ✓ User has {len(user.leagues)} league(s)")
            for league in user.leagues:
                print(f"      - {league.name} ({league.season})")

    print("\n" + "=" * 60)
    print("✅ All database tests passed!\n")
    print("Next steps:")
    print("1. Database schema is ready")
    print("2. CRUD operations are working")
    print("3. Proceed to Phase 4 for agent tools\n")

if __name__ == "__main__":
    asyncio.run(test_database())
