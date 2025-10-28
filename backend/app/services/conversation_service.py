"""
Conversation Service - Handles all conversation-related database operations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message
import logging

logger = logging.getLogger(__name__)


async def create_conversation(
    db: AsyncSession,
    user_id: str,
    league_id: str,
    thread_id: str,
    title: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> Conversation:
    """Create a new conversation"""
    conversation = Conversation(
        user_id=user_id,
        league_id=league_id,
        thread_id=thread_id,
        title=title or "New Conversation",
        extra_data=extra_data or {}
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    logger.info(f"Created conversation {conversation.id} with thread_id {thread_id}")
    return conversation


async def get_conversation_by_thread_id(
    db: AsyncSession,
    thread_id: str
) -> Optional[Conversation]:
    """Get conversation by thread_id"""
    result = await db.execute(
        select(Conversation).where(Conversation.thread_id == thread_id)
    )
    return result.scalar_one_or_none()


async def get_conversation_by_id(
    db: AsyncSession,
    conversation_id: str
) -> Optional[Conversation]:
    """Get conversation by ID with messages"""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def get_user_conversations(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> List[Conversation]:
    """Get user's conversations, ordered by most recent"""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    tool_calls: Optional[List[Dict]] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> Message:
    """Save a message to a conversation"""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
        extra_data=extra_data or {}
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    logger.info(f"Saved {role} message to conversation {conversation_id}")
    return message


async def get_conversation_messages(
    db: AsyncSession,
    conversation_id: str
) -> List[Message]:
    """Get all messages for a conversation"""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def update_conversation_title(
    db: AsyncSession,
    conversation_id: str,
    title: str
) -> Optional[Conversation]:
    """Update conversation title"""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.title = title
        await db.commit()
        await db.refresh(conversation)
        logger.info(f"Updated conversation {conversation_id} title to: {title}")
    return conversation


async def delete_conversation(
    db: AsyncSession,
    conversation_id: str
) -> bool:
    """Delete a conversation (cascades to messages)"""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        await db.delete(conversation)
        await db.commit()
        logger.info(f"Deleted conversation {conversation_id}")
        return True
    return False


async def get_conversation_count(
    db: AsyncSession,
    user_id: str
) -> int:
    """Get total conversation count for a user"""
    result = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    )
    return result.scalar() or 0


def generate_conversation_title(first_message: str, max_length: int = 50) -> str:
    """Generate a conversation title from the first message"""
    # Clean up the message
    title = first_message.strip()

    # Remove common prefixes
    prefixes = ["help me", "can you", "i need", "what should", "who should", "please"]
    for prefix in prefixes:
        if title.lower().startswith(prefix):
            title = title[len(prefix):].strip()

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    # Truncate if too long
    if len(title) > max_length:
        title = title[:max_length].rsplit(' ', 1)[0] + "..."

    return title or "New Conversation"
