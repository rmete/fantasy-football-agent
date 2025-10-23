from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.schemas.sleeper import (
    SleeperUser,
    SleeperLeague,
    LeagueResponse,
    UserLeaguesResponse,
    SleeperRoster,
    SleeperMatchup
)
from app.tools.sleeper_client import sleeper_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sleeper", tags=["sleeper"])

@router.get("/user/{username}", response_model=SleeperUser)
async def get_user(username: str):
    """Get Sleeper user by username"""
    user_data = await sleeper_client.get_user(username)
    if not user_data:
        raise HTTPException(status_code=404, detail=f"User {username} not found")
    return user_data

@router.get("/user/{username}/leagues", response_model=UserLeaguesResponse)
async def get_user_leagues(
    username: str,
    sport: str = Query("nfl", description="Sport type"),
    season: str = Query("2025", description="Season year")
):
    """Get all leagues for a user"""
    # First get user
    user_data = await sleeper_client.get_user(username)
    if not user_data:
        raise HTTPException(status_code=404, detail=f"User {username} not found")

    # Then get leagues
    leagues = await sleeper_client.get_user_leagues(user_data["user_id"], sport, season)

    return {
        "user": user_data,
        "leagues": leagues
    }

@router.get("/league/{league_id}", response_model=LeagueResponse)
async def get_league_details(league_id: str):
    """Get complete league details including rosters and users"""
    league = await sleeper_client.get_league(league_id)
    if not league:
        raise HTTPException(status_code=404, detail=f"League {league_id} not found")

    # Fetch rosters and users in parallel
    rosters = await sleeper_client.get_league_rosters(league_id)
    users = await sleeper_client.get_league_users(league_id)

    # Add league_id to rosters
    for roster in rosters:
        roster["league_id"] = league_id

    return {
        "league": league,
        "rosters": rosters,
        "users": users
    }

@router.get("/league/{league_id}/rosters", response_model=List[SleeperRoster])
async def get_league_rosters(league_id: str):
    """Get all rosters in a league"""
    rosters = await sleeper_client.get_league_rosters(league_id)
    if not rosters:
        raise HTTPException(status_code=404, detail=f"No rosters found for league {league_id}")

    # Add league_id to each roster
    for roster in rosters:
        roster["league_id"] = league_id

    return rosters

@router.get("/league/{league_id}/matchups/{week}", response_model=List[SleeperMatchup])
async def get_league_matchups(league_id: str, week: int):
    """Get matchups for a specific week"""
    if week < 1 or week > 18:
        raise HTTPException(status_code=400, detail="Week must be between 1 and 18")

    matchups = await sleeper_client.get_league_matchups(league_id, week)
    if not matchups:
        raise HTTPException(status_code=404, detail=f"No matchups found for week {week}")
    return matchups

@router.get("/players")
async def get_all_players():
    """Get all NFL players (large response, ~50MB)"""
    players = await sleeper_client.get_players()
    if not players:
        raise HTTPException(status_code=500, detail="Failed to fetch players")
    return players

@router.get("/players/trending/{add_drop}")
async def get_trending_players(
    add_drop: str,
    sport: str = Query("nfl", description="Sport type")
):
    """Get trending players (adds or drops)"""
    if add_drop not in ["add", "drop"]:
        raise HTTPException(status_code=400, detail="add_drop must be 'add' or 'drop'")

    trending = await sleeper_client.get_trending_players(sport, add_drop)
    return trending
