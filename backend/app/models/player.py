from sqlalchemy import Column, String, Integer, DateTime, Float, JSON, Index, ForeignKey
from datetime import datetime
from app.core.database import Base

class Player(Base):
    """Cached player data from Sleeper"""
    __tablename__ = "players"

    player_id = Column(String, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    full_name = Column(String, index=True)
    position = Column(String, index=True)
    team = Column(String, index=True)
    age = Column(Integer)
    injury_status = Column(String, index=True)
    number = Column(Integer)
    depth_chart_order = Column(Integer)
    search_rank = Column(Integer)

    # Fantasy data
    fantasy_positions = Column(JSON)
    player_data = Column(JSON)  # Full Sleeper player object

    # Timestamps
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_player_position_team', 'position', 'team'),
    )

class PlayerStats(Base):
    """Weekly player statistics"""
    __tablename__ = "player_stats"

    id = Column(String, primary_key=True)  # Composite: player_id:season:week
    player_id = Column(String, ForeignKey("players.player_id"), nullable=False, index=True)
    season = Column(String, nullable=False)
    week = Column(Integer, nullable=False)

    # Stats
    stats = Column(JSON)  # Raw stats from Sleeper
    fantasy_points = Column(Float)
    projected_points = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_stats_player_season_week', 'player_id', 'season', 'week'),
    )
