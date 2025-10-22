from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum as SQLEnum, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import uuid
import enum

class AgentTaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentTaskType(str, enum.Enum):
    SIT_START = "sit_start"
    TRADE_ANALYSIS = "trade_analysis"
    WAIVER_WIRE = "waiver_wire"
    LINEUP_OPTIMIZATION = "lineup_optimization"
    INJURY_MONITORING = "injury_monitoring"
    OPPONENT_ANALYSIS = "opponent_analysis"

class AgentTask(Base):
    """Track agent tasks and their execution"""
    __tablename__ = "agent_tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    league_id = Column(String, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=True)

    task_type = Column(SQLEnum(AgentTaskType), nullable=False)
    status = Column(SQLEnum(AgentTaskStatus), default=AgentTaskStatus.PENDING)

    # Task details
    input_data = Column(JSON)  # Parameters for the task
    result = Column(JSON)  # Agent's output
    error_message = Column(Text, nullable=True)

    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="agent_tasks")

class AgentDecision(Base):
    """Store AI-generated decisions and recommendations"""
    __tablename__ = "agent_decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    league_id = Column(String, ForeignKey("leagues.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(String, ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False)

    decision_type = Column(SQLEnum(AgentTaskType), nullable=False)
    week = Column(Integer, nullable=True)
    season = Column(String, nullable=True)

    # Decision details
    recommendation = Column(JSON)  # The actual recommendation
    reasoning = Column(Text)  # AI's explanation
    confidence_score = Column(Integer)  # 0-100

    # User action
    user_approved = Column(Boolean, nullable=True)
    user_action_taken = Column(JSON, nullable=True)
    executed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    league = relationship("League", back_populates="agent_decisions")
