from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import uuid


class Conversation(Base):
    """Represents a conversation thread between user and agent"""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    league_id = Column(String, nullable=True)
    thread_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Extra data (stores week, roster_id, tags, etc.)
    extra_data = Column(JSONB, default={})

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, thread_id={self.thread_id}, title={self.title})>"


class Message(Base):
    """Represents a single message in a conversation"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)

    # Store tool execution history for debugging/analytics
    tool_calls = Column(JSONB, nullable=True)

    # Store performance metrics (tokens, latency, model version, etc.)
    extra_data = Column(JSONB, default={})

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Add constraint for role
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="check_message_role"),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"
