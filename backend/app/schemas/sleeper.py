from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SleeperUser(BaseModel):
    user_id: str
    username: str
    display_name: str
    avatar: Optional[str] = None

class SleeperLeague(BaseModel):
    league_id: str
    name: str
    season: str
    sport: str
    status: str
    total_rosters: int
    roster_positions: List[str]
    scoring_settings: Dict[str, Any]
    settings: Dict[str, Any]

class SleeperRoster(BaseModel):
    roster_id: int
    owner_id: str
    league_id: str = Field(default="")
    players: List[str]  # List of player IDs
    starters: List[str]  # List of starter player IDs
    reserve: Optional[List[str]] = None
    taxi: Optional[List[str]] = None
    settings: Dict[str, Any] = Field(default_factory=dict)

    # Standings info
    wins: int = 0
    losses: int = 0
    ties: int = 0
    fpts: float = 0.0  # Fantasy points for season

class SleeperPlayer(BaseModel):
    player_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    position: Optional[str] = None
    team: Optional[str] = None
    age: Optional[int] = None
    injury_status: Optional[str] = None
    number: Optional[int] = None
    depth_chart_order: Optional[int] = None
    search_rank: Optional[int] = None
    fantasy_positions: Optional[List[str]] = None

class SleeperMatchup(BaseModel):
    roster_id: int
    matchup_id: int
    points: float
    starters: List[str]
    players: List[str]
    custom_points: Optional[float] = None

class LeagueResponse(BaseModel):
    """Response model for league endpoint"""
    league: SleeperLeague
    rosters: List[SleeperRoster]
    users: List[SleeperUser]

class UserLeaguesResponse(BaseModel):
    """Response model for user leagues endpoint"""
    user: SleeperUser
    leagues: List[SleeperLeague]
