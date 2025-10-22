from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.league import League, Roster
from typing import List, Optional
from datetime import datetime

async def get_or_create_league(
    db: AsyncSession,
    league_id: str,
    user_id: str,
    league_data: dict
) -> League:
    """Get existing league or create new one"""
    result = await db.execute(select(League).where(League.id == league_id))
    league = result.scalar_one_or_none()

    if not league:
        league = League(
            id=league_id,
            user_id=user_id,
            name=league_data["name"],
            season=league_data["season"],
            sport=league_data["sport"],
            status=league_data["status"],
            total_rosters=league_data["total_rosters"],
            roster_positions=league_data.get("roster_positions"),
            scoring_settings=league_data.get("scoring_settings"),
            settings=league_data.get("settings"),
        )
        db.add(league)
        await db.commit()
        await db.refresh(league)
    else:
        # Update existing league
        league.name = league_data["name"]
        league.status = league_data["status"]
        league.total_rosters = league_data["total_rosters"]
        league.roster_positions = league_data.get("roster_positions")
        league.scoring_settings = league_data.get("scoring_settings")
        league.settings = league_data.get("settings")
        league.last_synced = datetime.utcnow()
        await db.commit()
        await db.refresh(league)

    return league

async def get_user_leagues(db: AsyncSession, user_id: str) -> List[League]:
    """Get all leagues for a user"""
    result = await db.execute(
        select(League).where(League.user_id == user_id)
    )
    return result.scalars().all()

async def get_league(db: AsyncSession, league_id: str) -> Optional[League]:
    """Get league by ID"""
    result = await db.execute(select(League).where(League.id == league_id))
    return result.scalar_one_or_none()

async def upsert_roster(
    db: AsyncSession,
    league_id: str,
    roster_data: dict
) -> Roster:
    """Insert or update roster"""
    roster_id = roster_data["roster_id"]
    composite_id = f"{league_id}:{roster_id}"

    result = await db.execute(select(Roster).where(Roster.id == composite_id))
    roster = result.scalar_one_or_none()

    if not roster:
        roster = Roster(
            id=composite_id,
            league_id=league_id,
            roster_id=roster_id,
            owner_id=roster_data["owner_id"],
            players=roster_data.get("players", []),
            starters=roster_data.get("starters", []),
            reserve=roster_data.get("reserve"),
            taxi=roster_data.get("taxi"),
            wins=roster_data.get("wins", 0),
            losses=roster_data.get("losses", 0),
            ties=roster_data.get("ties", 0),
            fpts=roster_data.get("fpts", 0.0),
            settings=roster_data.get("settings", {}),
        )
        db.add(roster)
    else:
        # Update existing
        roster.players = roster_data.get("players", [])
        roster.starters = roster_data.get("starters", [])
        roster.reserve = roster_data.get("reserve")
        roster.taxi = roster_data.get("taxi")
        roster.wins = roster_data.get("wins", 0)
        roster.losses = roster_data.get("losses", 0)
        roster.ties = roster_data.get("ties", 0)
        roster.fpts = roster_data.get("fpts", 0.0)
        roster.settings = roster_data.get("settings", {})
        roster.last_synced = datetime.utcnow()

    await db.commit()
    await db.refresh(roster)
    return roster

async def get_league_rosters(db: AsyncSession, league_id: str) -> List[Roster]:
    """Get all rosters for a league"""
    result = await db.execute(
        select(Roster).where(Roster.league_id == league_id)
    )
    return result.scalars().all()
