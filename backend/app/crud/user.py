from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from typing import Optional

async def get_user_by_sleeper_id(db: AsyncSession, sleeper_user_id: str) -> Optional[User]:
    """Get user by Sleeper user ID"""
    result = await db.execute(
        select(User).where(User.sleeper_user_id == sleeper_user_id)
    )
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by internal ID"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()

async def create_user(
    db: AsyncSession,
    sleeper_user_id: str,
    sleeper_username: str,
    display_name: str,
    avatar: Optional[str] = None
) -> User:
    """Create new user"""
    user = User(
        sleeper_user_id=sleeper_user_id,
        sleeper_username=sleeper_username,
        display_name=display_name,
        avatar=avatar
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def update_user_preferences(
    db: AsyncSession,
    user_id: str,
    preferences: dict
) -> Optional[User]:
    """Update user preferences"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.preferences = preferences
        await db.commit()
        await db.refresh(user)
    return user

async def set_autonomous_mode(
    db: AsyncSession,
    user_id: str,
    enabled: bool
) -> Optional[User]:
    """Enable/disable autonomous mode"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.autonomous_mode = enabled
        await db.commit()
        await db.refresh(user)
    return user
