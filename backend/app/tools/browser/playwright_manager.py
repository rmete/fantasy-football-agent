"""
Playwright Browser Session Manager
Manages browser contexts, sessions, and lifecycle
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from app.core.config import settings

logger = logging.getLogger(__name__)


class BrowserSession:
    """Represents an active browser session"""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        context: BrowserContext,
        page: Page
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.context = context
        self.page = page
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.is_active = True

    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if session has expired"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)

    async def close(self):
        """Close the session"""
        try:
            if self.page and not self.page.is_closed():
                await self.page.close()
            if self.context:
                await self.context.close()
            self.is_active = False
            logger.info(f"Session {self.session_id} closed")
        except Exception as e:
            logger.error(f"Error closing session {self.session_id}: {e}")


class PlaywrightManager:
    """
    Singleton manager for Playwright browser sessions
    Manages browser lifecycle, persistent contexts, and session tracking
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.playwright: Optional[Playwright] = None
            self.browser: Optional[Browser] = None
            self.sessions: Dict[str, BrowserSession] = {}
            self._lock = asyncio.Lock()
            self._initialized = True

            # Configuration
            self.headless = True  # Headless for Docker
            self.slow_mo = 500  # Slow down for better screenshots
            self.timeout = 30000  # 30 seconds default timeout

            # Domain allowlist for safety
            self.allowed_domains = [
                "sleeper.app",
                "sleeper.com",
                "accounts.google.com",
                "accounts.google.co.uk"
            ]

            logger.info("PlaywrightManager initialized")

    async def start(self):
        """Start Playwright and browser"""
        async with self._lock:
            if self.playwright and self.browser:
                logger.info("Playwright already started")
                return

            try:
                logger.info("Starting Playwright...")
                self.playwright = await async_playwright().start()

                # Launch browser with configuration
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',  # For CORS during dev
                    ]
                )

                logger.info(f"Playwright browser started (headless={self.headless})")
            except Exception as e:
                logger.error(f"Failed to start Playwright: {e}", exc_info=True)
                raise

    async def stop(self):
        """Stop Playwright and close all sessions"""
        async with self._lock:
            try:
                # Close all sessions
                for session in list(self.sessions.values()):
                    await session.close()
                self.sessions.clear()

                # Close browser
                if self.browser:
                    await self.browser.close()
                    self.browser = None

                # Stop playwright
                if self.playwright:
                    await self.playwright.stop()
                    self.playwright = None

                logger.info("Playwright stopped")
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}", exc_info=True)

    def _get_profile_path(self, user_id: str) -> Path:
        """Get persistent profile path for user"""
        base_path = Path(settings.BASE_DIR if hasattr(settings, 'BASE_DIR') else ".") / "data" / "browser_profiles"
        profile_path = base_path / f"user_{user_id}"
        profile_path.mkdir(parents=True, exist_ok=True)
        return profile_path

    async def create_session(self, session_id: str, user_id: str) -> BrowserSession:
        """Create a new browser session with persistent context"""

        if not self.playwright:
            await self.start()

        try:
            # Get user-specific profile path
            profile_path = self._get_profile_path(user_id)

            logger.info(f"Creating session {session_id} for user {user_id}")
            logger.info(f"Profile path: {profile_path}")

            # Create persistent context (combines browser launch + persistent storage)
            context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=self.headless,
                slow_mo=self.slow_mo,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9"
                },
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                ]
            )

            # Set default timeout
            context.set_default_timeout(self.timeout)

            # Create page
            page = await context.new_page()

            # Add route blocking for better safety (block ads, trackers)
            await page.route("**/*", lambda route: (
                route.abort() if any(blocked in route.request.url for blocked in [
                    'doubleclick.net',
                    'analytics.google.com',
                    'googletagmanager.com',
                    'facebook.com/tr',
                    'hotjar.com'
                ]) else route.continue_()
            ))

            # Create session object
            session = BrowserSession(
                session_id=session_id,
                user_id=user_id,
                context=context,
                page=page
            )

            # Store session
            self.sessions[session_id] = session

            logger.info(f"Session {session_id} created successfully")
            return session

        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}", exc_info=True)
            raise

    async def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get an existing session"""
        session = self.sessions.get(session_id)
        if session and session.is_active:
            session.update_activity()
            return session
        return None

    async def close_session(self, session_id: str):
        """Close a specific session"""
        session = self.sessions.get(session_id)
        if session:
            await session.close()
            del self.sessions[session_id]
            logger.info(f"Session {session_id} closed and removed")

    async def cleanup_expired_sessions(self, timeout_minutes: int = 30):
        """Clean up expired sessions"""
        expired = []
        for session_id, session in self.sessions.items():
            if session.is_expired(timeout_minutes):
                expired.append(session_id)

        for session_id in expired:
            await self.close_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")

        return len(expired)

    def get_active_session_count(self) -> int:
        """Get count of active sessions"""
        return sum(1 for s in self.sessions.values() if s.is_active)

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        session = self.sessions.get(session_id)
        if session:
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "is_active": session.is_active,
                "age_minutes": (datetime.now() - session.created_at).total_seconds() / 60
            }
        return None

    async def random_delay(self, min_ms: int = 50, max_ms: int = 150):
        """Add random human-like delay"""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)


# Singleton instance
playwright_manager = PlaywrightManager()
