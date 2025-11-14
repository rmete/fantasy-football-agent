"""
Settings API endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
import os

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    """Settings update request"""
    anthropic_model: Optional[str] = None
    llm_provider: Optional[str] = None
    sleeper_username: Optional[str] = None


class SettingsResponse(BaseModel):
    """Current settings response"""
    llm_provider: str
    anthropic_model: str
    sleeper_username: Optional[str]
    available_anthropic_models: list[str]
    available_providers: list[str]


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """Get current settings"""
    return SettingsResponse(
        llm_provider=settings.LLM_PROVIDER,
        anthropic_model=settings.ANTHROPIC_MODEL,
        sleeper_username=settings.SLEEPER_USERNAME,
        available_anthropic_models=[
            "claude-sonnet-4-5-20250929",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ],
        available_providers=["anthropic", "openai", "gemini"]
    )


@router.post("", response_model=SettingsResponse)
async def update_settings(update: SettingsUpdate):
    """
    Update settings (runtime only - does not persist to .env)

    To persist settings, update your .env file with:
    - ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
    - LLM_PROVIDER=anthropic
    - SLEEPER_USERNAME=your_username
    """
    # Update runtime settings
    if update.anthropic_model:
        valid_models = [
            "claude-sonnet-4-5-20250929",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022"
        ]
        if update.anthropic_model not in valid_models:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model. Must be one of: {valid_models}"
            )
        settings.ANTHROPIC_MODEL = update.anthropic_model

    if update.llm_provider:
        valid_providers = ["anthropic", "openai", "gemini"]
        if update.llm_provider not in valid_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider. Must be one of: {valid_providers}"
            )
        settings.LLM_PROVIDER = update.llm_provider

    if update.sleeper_username:
        settings.SLEEPER_USERNAME = update.sleeper_username

    return await get_settings()

