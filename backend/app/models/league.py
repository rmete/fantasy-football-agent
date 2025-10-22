from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class League(Base):
    __tablename__ = "leagues"

    id = Column(String, primary_key=True)  # Sleeper league_id
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    season = Column(String, nullable=False)
    sport = Column(String, default="nfl")
    status = Column(String)  # pre_draft, drafting, in_season, complete
    total_rosters = Column(Integer)

    # League settings
    roster_positions = Column(JSON)
    scoring_settings = Column(JSON)
    settings = Column(JSON)

    # Cache timestamps
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="leagues")
    rosters = relationship("Roster", back_populates="league", cascade="all, delete-orphan")
    agent_decisions = relationship("AgentDecision", back_populates="league", cascade="all, delete-orphan")

class Roster(Base):
    __tablename__ = "rosters"

    id = Column(String, primary_key=True)  # Composite: league_id:roster_id
    league_id = Column(String, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    roster_id = Column(Integer, nullable=False)
    owner_id = Column(String, nullable=False)  # Sleeper user_id

    # Roster data
    players = Column(JSON)  # List of player IDs
    starters = Column(JSON)  # List of starter IDs
    reserve = Column(JSON)
    taxi = Column(JSON)

    # Standings
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    fpts = Column(Float, default=0.0)

    # Settings
    settings = Column(JSON)

    # Timestamps
    last_synced = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    league = relationship("League", back_populates="rosters")
