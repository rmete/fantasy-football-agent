"""
Browser Automation API Endpoints
Provides REST API for browser session management and screenshots
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
import logging

from app.tools.browser.playwright_manager import playwright_manager
from app.tools.browser.screenshot_storage import screenshot_storage
from app.services.credential_service import credential_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/browser", tags=["browser"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class StartSessionRequest(BaseModel):
    user_id: str = "default"


class StartSessionResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    message: str
    error: Optional[str] = None


class SessionStatusResponse(BaseModel):
    success: bool
    session_id: str
    user_id: Optional[str] = None
    created_at: Optional[str] = None
    last_activity: Optional[str] = None
    is_active: bool
    age_minutes: Optional[float] = None


class SaveCredentialsRequest(BaseModel):
    user_id: str = "default"
    email: str
    password: str
    use_sso: bool = False


class CredentialsResponse(BaseModel):
    success: bool
    message: str
    use_sso: Optional[bool] = None
    email: Optional[str] = None
    has_password: Optional[bool] = None
    error: Optional[str] = None


# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/start-session", response_model=StartSessionResponse)
async def start_browser_session(request: StartSessionRequest):
    """
    Start a new browser session for automation

    Creates a persistent browser context with user profile
    """
    try:
        session_id = str(uuid.uuid4())
        logger.info(f"Starting browser session for user {request.user_id}")

        # Ensure Playwright is started
        await playwright_manager.start()

        # Create session
        session = await playwright_manager.create_session(session_id, request.user_id)

        return StartSessionResponse(
            success=True,
            session_id=session_id,
            message=f"Browser session started successfully"
        )

    except Exception as e:
        logger.error(f"Failed to start browser session: {e}", exc_info=True)
        return StartSessionResponse(
            success=False,
            message="Failed to start browser session",
            error=str(e)
        )


@router.post("/stop-session/{session_id}")
async def stop_browser_session(session_id: str):
    """
    Stop and cleanup a browser session
    """
    try:
        logger.info(f"Stopping browser session {session_id}")

        await playwright_manager.close_session(session_id)

        return {
            "success": True,
            "message": f"Session {session_id} stopped successfully"
        }

    except Exception as e:
        logger.error(f"Failed to stop session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Get status of a browser session
    """
    try:
        info = playwright_manager.get_session_info(session_id)

        if not info:
            return SessionStatusResponse(
                success=False,
                session_id=session_id,
                is_active=False
            )

        return SessionStatusResponse(
            success=True,
            session_id=info["session_id"],
            user_id=info["user_id"],
            created_at=info["created_at"],
            last_activity=info["last_activity"],
            is_active=info["is_active"],
            age_minutes=info["age_minutes"]
        )

    except Exception as e:
        logger.error(f"Error getting session status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def list_sessions():
    """
    List all active browser sessions
    """
    try:
        active_count = playwright_manager.get_active_session_count()

        sessions = []
        for session_id in playwright_manager.sessions.keys():
            info = playwright_manager.get_session_info(session_id)
            if info:
                sessions.append(info)

        return {
            "success": True,
            "active_count": active_count,
            "sessions": sessions
        }

    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup-expired")
async def cleanup_expired_sessions(timeout_minutes: int = 30):
    """
    Cleanup expired browser sessions
    """
    try:
        count = await playwright_manager.cleanup_expired_sessions(timeout_minutes)

        return {
            "success": True,
            "message": f"Cleaned up {count} expired sessions",
            "count": count
        }

    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CREDENTIAL MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/credentials", response_model=CredentialsResponse)
async def save_credentials(request: SaveCredentialsRequest):
    """
    Save Sleeper credentials to OS keychain
    """
    try:
        result = credential_service.save_credentials(
            user_id=request.user_id,
            email=request.email,
            password=request.password,
            use_sso=request.use_sso
        )

        if result["success"]:
            return CredentialsResponse(
                success=True,
                message=result["message"],
                use_sso=request.use_sso,
                email=request.email
            )
        else:
            return CredentialsResponse(
                success=False,
                message="Failed to save credentials",
                error=result.get("error")
            )

    except Exception as e:
        logger.error(f"Error saving credentials: {e}", exc_info=True)
        return CredentialsResponse(
            success=False,
            message="Failed to save credentials",
            error=str(e)
        )


@router.get("/credentials/{user_id}", response_model=CredentialsResponse)
async def get_credentials(user_id: str):
    """
    Check if credentials exist for a user (doesn't return actual credentials)
    """
    try:
        test_result = credential_service.test_credentials(user_id)

        if test_result["success"]:
            return CredentialsResponse(
                success=True,
                message=test_result["message"],
                email=test_result.get("email"),
                use_sso=test_result.get("use_sso"),
                has_password=test_result.get("has_password")
            )
        else:
            return CredentialsResponse(
                success=False,
                message=test_result.get("message", "No credentials found"),
                error=test_result.get("error")
            )

    except Exception as e:
        logger.error(f"Error checking credentials: {e}", exc_info=True)
        return CredentialsResponse(
            success=False,
            message="Error checking credentials",
            error=str(e)
        )


@router.delete("/credentials/{user_id}")
async def delete_credentials(user_id: str):
    """
    Delete stored credentials for a user
    """
    try:
        result = credential_service.delete_credentials(user_id)

        return result

    except Exception as e:
        logger.error(f"Error deleting credentials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/credentials/test/{user_id}")
async def test_credentials(user_id: str):
    """
    Test if stored credentials are valid
    """
    try:
        result = credential_service.test_credentials(user_id)
        return result

    except Exception as e:
        logger.error(f"Error testing credentials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SCREENSHOT ENDPOINTS
# ============================================================================

@router.get("/screenshots/{thread_id}")
async def get_thread_screenshots(thread_id: str):
    """
    Get all screenshots for a specific thread/conversation
    """
    try:
        screenshots = screenshot_storage.get_thread_screenshots(thread_id)

        return {
            "success": True,
            "thread_id": thread_id,
            "count": len(screenshots),
            "screenshots": screenshots
        }

    except Exception as e:
        logger.error(f"Error getting screenshots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/screenshots/{thread_id}")
async def delete_thread_screenshots(thread_id: str):
    """
    Delete all screenshots for a specific thread
    """
    try:
        count = screenshot_storage.delete_thread_screenshots(thread_id)

        return {
            "success": True,
            "message": f"Deleted {count} screenshots",
            "count": count
        }

    except Exception as e:
        logger.error(f"Error deleting screenshots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screenshots/cleanup")
async def cleanup_old_screenshots(days: int = 7):
    """
    Delete screenshots older than specified days
    """
    try:
        count = screenshot_storage.cleanup_old_screenshots(days)

        return {
            "success": True,
            "message": f"Deleted {count} old screenshots",
            "count": count,
            "days": days
        }

    except Exception as e:
        logger.error(f"Error during screenshot cleanup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screenshots/stats")
async def get_screenshot_stats():
    """
    Get screenshot storage statistics
    """
    try:
        stats = screenshot_storage.get_storage_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting screenshot stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def browser_health():
    """
    Check browser automation system health
    """
    try:
        browser_running = playwright_manager.browser is not None
        active_sessions = playwright_manager.get_active_session_count()

        return {
            "status": "healthy",
            "browser_running": browser_running,
            "active_sessions": active_sessions,
            "screenshot_stats": screenshot_storage.get_storage_stats()
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }
