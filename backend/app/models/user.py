from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sleeper_user_id = Column(String, unique=True, nullable=False, index=True)
    sleeper_username = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    avatar = Column(String, nullable=True)

    # Preferences
    preferences = Column(JSON, default={})
    autonomous_mode = Column(Boolean, default=False)
    notification_settings = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    leagues = relationship("League", back_populates="user", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="user", cascade="all, delete-orphan")
