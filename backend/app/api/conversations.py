"""
Conversations API - Endpoints for managing conversation history
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


# Response Schemas
class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    tool_calls: Optional[List] = None  # Can be list of strings or dicts
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationSummary(BaseModel):
    id: str
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    last_message_preview: str

    class Config:
        from_attributes = True


class ConversationDetail(BaseModel):
    id: str
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    league_id: Optional[str]
    extra_data: dict
    messages: List[MessageResponse]

    class Config:
        from_attributes = True


class UpdateTitleRequest(BaseModel):
    title: str


# Endpoints
@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    user_id: str = "default",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get user's conversation history, ordered by most recent"""
    conversations = await conversation_service.get_user_conversations(
        db, user_id, limit, offset
    )

    # Build summaries with message count and preview
    summaries = []
    for conv in conversations:
        messages = await conversation_service.get_conversation_messages(db, conv.id)

        # Get last message for preview
        last_message = messages[-1].content if messages else "No messages"
        preview = last_message[:100] + "..." if len(last_message) > 100 else last_message

        summaries.append(
            ConversationSummary(
                id=conv.id,
                thread_id=conv.thread_id,
                title=conv.title,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=len(messages),
                last_message_preview=preview
            )
        )

    return summaries


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get full conversation with all messages"""
    conversation = await conversation_service.get_conversation_by_id(db, conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    messages = await conversation_service.get_conversation_messages(db, conversation_id)

    return ConversationDetail(
        id=conversation.id,
        thread_id=conversation.thread_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        league_id=conversation.league_id,
        extra_data=conversation.extra_data or {},
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tool_calls=msg.tool_calls,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and all its messages"""
    success = await conversation_service.delete_conversation(db, conversation_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    return None


@router.patch("/{conversation_id}/title")
async def update_title(
    conversation_id: str,
    request: UpdateTitleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update conversation title"""
    conversation = await conversation_service.update_conversation_title(
        db, conversation_id, request.title
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found"
        )

    return {"success": True, "title": conversation.title}


@router.get("/stats/count")
async def get_conversation_count(
    user_id: str = "default",
    db: AsyncSession = Depends(get_db)
):
    """Get total conversation count for a user"""
    count = await conversation_service.get_conversation_count(db, user_id)
    return {"user_id": user_id, "count": count}
