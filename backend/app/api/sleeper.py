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
from app.tools.projections import projection_tool
from app.core.config import settings
from app.utils.bye_weeks import is_team_on_bye
import logging
import httpx

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

@router.get("/projections/{player_id}")
async def get_player_projection(
    player_id: str,
    week: Optional[int] = Query(None, description="Week number (default: current week)"),
    scoring_format: str = Query("PPR", description="Scoring format: PPR, HALF_PPR, or STD"),
    season: Optional[int] = Query(None, description="Season year (default: current season)")
):
    """Get projection for a specific player"""
    try:
        # Get player info first to get name and position
        players = await sleeper_client.get_players()
        player = players.get(player_id)

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        player_name = player.get("full_name") or f"{player.get('first_name')} {player.get('last_name')}"
        position = player.get("position")

        if not position:
            raise HTTPException(status_code=400, detail=f"Player {player_name} has no position")

        # Get projection
        projection = await projection_tool.get_player_projection(
            player_name=player_name,
            position=position,
            week=week,
            scoring_format=scoring_format,
            season=season
        )

        # Add player_id to response
        projection["player_id"] = player_id

        return projection
    except Exception as e:
        logger.error(f"Error fetching projection for player {player_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projections/batch")
async def get_batch_projections(
    player_ids: List[str],
    week: Optional[int] = Query(None, description="Week number (default: current week)"),
    scoring_format: str = Query("PPR", description="Scoring format: PPR, HALF_PPR, or STD"),
    season: Optional[int] = Query(None, description="Season year (default: current season)")
):
    """Get projections for multiple players at once"""
    try:
        # Get NFL state for current week
        async with httpx.AsyncClient() as client:
            state_resp = await client.get("https://api.sleeper.app/v1/state/nfl")
            nfl_state = state_resp.json()
        current_week = week if week is not None else int(nfl_state.get("week", 1))

        players = await sleeper_client.get_players()
        projections = []

        for player_id in player_ids:
            player = players.get(player_id)
            if not player:
                logger.warning(f"Player {player_id} not found in catalog")
                # Still add a placeholder so frontend knows this player exists
                projections.append({
                    "player_id": player_id,
                    "player": player_id,
                    "position": "Unknown",
                    "team": None,
                    "projected_points": None,
                    "floor": None,
                    "ceiling": None,
                    "confidence": "none",
                    "is_on_bye": False,
                    "injury_status": None,
                    "injury_body_part": None,
                    "note": "Player not found in catalog"
                })
                continue

            player_name = player.get("full_name") or f"{player.get('first_name')} {player.get('last_name')}"
            position = player.get("position")
            team = player.get("team")
            injury_status = player.get("injury_status")
            injury_body_part = player.get("injury_body_part")

            # Check if player is on bye
            is_on_bye = is_team_on_bye(team, current_week) if team else False

            if not position:
                logger.warning(f"Player {player_name} ({player_id}) has no position")
                projections.append({
                    "player_id": player_id,
                    "player": player_name,
                    "position": "Unknown",
                    "team": team,
                    "projected_points": None,
                    "floor": None,
                    "ceiling": None,
                    "confidence": "none",
                    "is_on_bye": is_on_bye,
                    "injury_status": injury_status,
                    "injury_body_part": injury_body_part,
                    "note": "No position data"
                })
                continue

            try:
                projection = await projection_tool.get_player_projection(
                    player_name=player_name,
                    position=position,
                    week=week,
                    scoring_format=scoring_format,
                    season=season
                )
                # Add player_id and status info
                projection["player_id"] = player_id
                projection["is_on_bye"] = is_on_bye
                projection["injury_status"] = injury_status
                projection["injury_body_part"] = injury_body_part
                projections.append(projection)
            except Exception as e:
                logger.error(f"Error fetching projection for {player_name} ({player_id}): {e}")
                # Add the player with null projection so UI can show it
                projections.append({
                    "player_id": player_id,
                    "player": player_name,
                    "position": position,
                    "team": team,
                    "projected_points": None,
                    "floor": None,
                    "ceiling": None,
                    "confidence": "none",
                    "is_on_bye": is_on_bye,
                    "injury_status": injury_status,
                    "injury_body_part": injury_body_part,
                    "note": f"Error: {str(e)[:50]}"
                })
                continue

        return {"projections": projections}
    except Exception as e:
        logger.error(f"Error in batch projections: {e}")
        raise HTTPException(status_code=500, detail=str(e))
