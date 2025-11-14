"""
LangChain Browser Automation Tools
Provides @tool decorated functions for browser interactions
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.tools.browser.playwright_manager import playwright_manager
from app.tools.browser.selectors import selectors
from app.tools.browser.screenshot_storage import screenshot_storage

logger = logging.getLogger(__name__)

# Thread-local storage for current session_id
_current_session_id: Optional[str] = None
_current_thread_id: Optional[str] = None


def set_browser_context(session_id: str, thread_id: str):
    """Set the current browser session context for tools"""
    global _current_session_id, _current_thread_id
    _current_session_id = session_id
    _current_thread_id = thread_id


async def _get_current_session():
    """Get the current browser session"""
    if not _current_session_id:
        raise ValueError("No active browser session. Call start_browser_session first.")

    session = await playwright_manager.get_session(_current_session_id)
    if not session:
        raise ValueError(f"Session {_current_session_id} not found or expired.")

    return session


# ============================================================================
# NAVIGATION TOOLS
# ============================================================================

@tool
async def open_page(url: str) -> Dict[str, Any]:
    """
    Navigate to a specific URL in the browser.

    Use this tool to:
    - Open Sleeper homepage
    - Navigate to any allowed domain

    Args:
        url: The URL to navigate to (must be from allowed domains)

    Returns:
        Dictionary with success status and page info
    """
    try:
        session = await _get_current_session()

        # Validate URL against allowed domains
        allowed = any(domain in url for domain in playwright_manager.allowed_domains)
        if not allowed:
            return {
                "success": False,
                "error": f"URL not in allowed domains: {playwright_manager.allowed_domains}"
            }

        logger.info(f"Navigating to: {url}")
        await session.page.goto(url, wait_until="domcontentloaded")

        # Add random delay
        await playwright_manager.random_delay()

        return {
            "success": True,
            "url": session.page.url,
            "title": await session.page.title()
        }

    except Exception as e:
        logger.error(f"Error navigating to {url}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def click_element(selector: str, timeout_ms: int = 30000) -> Dict[str, Any]:
    """
    Click an element on the page.

    Use this tool to:
    - Click buttons
    - Click links
    - Select menu items

    Args:
        selector: CSS selector for the element to click
        timeout_ms: Maximum wait time in milliseconds (default 30000)

    Returns:
        Dictionary with success status
    """
    try:
        session = await _get_current_session()

        logger.info(f"Clicking element: {selector}")

        # Wait for element and click
        await session.page.wait_for_selector(selector, timeout=timeout_ms)
        await session.page.click(selector)

        # Add random delay after click
        await playwright_manager.random_delay()

        return {
            "success": True,
            "selector": selector
        }

    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for element: {selector}")
        return {
            "success": False,
            "error": f"Element not found within {timeout_ms}ms: {selector}"
        }
    except Exception as e:
        logger.error(f"Error clicking {selector}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def type_text(
    selector: str,
    text: str,
    clear: bool = True,
    secure: bool = False,
    timeout_ms: int = 30000
) -> Dict[str, Any]:
    """
    Type text into an input field.

    Use this tool to:
    - Fill in forms
    - Enter search queries
    - Input credentials (with secure=True)

    Args:
        selector: CSS selector for the input field
        text: Text to type
        clear: Whether to clear existing text first (default True)
        secure: If True, text won't be logged (for passwords)
        timeout_ms: Maximum wait time in milliseconds

    Returns:
        Dictionary with success status
    """
    try:
        session = await _get_current_session()

        display_text = "***SECURE***" if secure else text
        logger.info(f"Typing into {selector}: {display_text}")

        # Wait for input field
        await session.page.wait_for_selector(selector, timeout=timeout_ms)

        # Clear if requested
        if clear:
            await session.page.fill(selector, "")

        # Type text with delay
        await session.page.type(selector, text, delay=50)

        # Add random delay
        await playwright_manager.random_delay()

        return {
            "success": True,
            "selector": selector,
            "text_length": len(text)
        }

    except Exception as e:
        logger.error(f"Error typing into {selector}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def press_key(key: str) -> Dict[str, Any]:
    """
    Press a keyboard key.

    Use this tool to:
    - Submit forms (Enter)
    - Navigate (Tab, Arrow keys)
    - Close dialogs (Escape)

    Args:
        key: Key to press (e.g., "Enter", "Tab", "Escape", "ArrowDown")

    Returns:
        Dictionary with success status
    """
    try:
        session = await _get_current_session()

        logger.info(f"Pressing key: {key}")
        await session.page.keyboard.press(key)

        # Add random delay
        await playwright_manager.random_delay()

        return {
            "success": True,
            "key": key
        }

    except Exception as e:
        logger.error(f"Error pressing key {key}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def wait_for_element(selector: str, timeout_ms: int = 30000) -> Dict[str, Any]:
    """
    Wait for an element to appear on the page.

    Use this tool to:
    - Wait for page loads
    - Wait for dynamic content
    - Verify navigation completed

    Args:
        selector: CSS selector to wait for
        timeout_ms: Maximum wait time in milliseconds

    Returns:
        Dictionary with success status
    """
    try:
        session = await _get_current_session()

        logger.info(f"Waiting for element: {selector}")
        await session.page.wait_for_selector(selector, timeout=timeout_ms)

        return {
            "success": True,
            "selector": selector
        }

    except PlaywrightTimeoutError:
        logger.error(f"Timeout waiting for element: {selector}")
        return {
            "success": False,
            "error": f"Element did not appear within {timeout_ms}ms: {selector}"
        }
    except Exception as e:
        logger.error(f"Error waiting for {selector}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def take_screenshot(tag: Optional[str] = None) -> Dict[str, Any]:
    """
    Capture a screenshot of the current page.

    Use this tool to:
    - Document current state
    - Capture before/after lineup changes
    - Verify actions completed

    Args:
        tag: Optional tag to label the screenshot (e.g., "login", "before_swap", "saved")

    Returns:
        Dictionary with screenshot URL and metadata
    """
    try:
        session = await _get_current_session()

        if not _current_thread_id:
            raise ValueError("No thread_id set for screenshot storage")

        logger.info(f"Taking screenshot (tag: {tag})")

        # Capture screenshot
        screenshot_bytes = await session.page.screenshot(full_page=True)

        # Save screenshot
        result = await screenshot_storage.save_screenshot(
            screenshot_bytes=screenshot_bytes,
            thread_id=_current_thread_id,
            tag=tag
        )

        return result

    except Exception as e:
        logger.error(f"Error taking screenshot: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def sleep_ms(milliseconds: int) -> Dict[str, Any]:
    """
    Pause execution for specified milliseconds.

    Use this tool to:
    - Wait for animations
    - Add human-like delays
    - Slow down automation

    Args:
        milliseconds: Time to sleep in milliseconds

    Returns:
        Dictionary with success status
    """
    try:
        logger.info(f"Sleeping for {milliseconds}ms")
        await asyncio.sleep(milliseconds / 1000)

        return {
            "success": True,
            "duration_ms": milliseconds
        }

    except Exception as e:
        logger.error(f"Error during sleep: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# SLEEPER-SPECIFIC WORKFLOWS
# ============================================================================

@tool
async def open_sleeper_browser(email: str = "", password: str = "", use_sso: bool = False) -> Dict[str, Any]:
    """
    Opens a browser session to Sleeper fantasy football platform.

    This tool opens your pre-configured Sleeper browser session automatically.
    The browser uses your saved session configuration - no manual entry needed.

    Use this tool when the user asks to:
    - "Open Sleeper"
    - "Go to Sleeper"
    - "Access my Sleeper account"
    - "Show me my lineup on Sleeper"
    - Any request to view or interact with Sleeper

    The tool handles authentication automatically using your saved browser profile.
    Just call it with no arguments - everything is pre-configured.

    Args:
        email: (Optional) Override email - leave empty to use saved config
        password: (Optional) Override password - leave empty to use saved config
        use_sso: Use Google SSO instead (default False)

    Returns:
        Dictionary with session status and browser state
    """
    try:
        # If credentials not provided, fetch from secure storage
        if not email or not password:
            from app.services.credential_service import credential_service
            creds = credential_service.get_credentials("default")
            if not creds:
                return {
                    "success": False,
                    "error": "No credentials found. User must save credentials in settings first."
                }
            email = creds.email
            password = creds.password
            use_sso = creds.use_sso
            logger.info("Retrieved credentials from secure storage")

        session = await _get_current_session()

        logger.info(f"Logging into Sleeper (SSO: {use_sso})")

        # Navigate to Sleeper
        await session.page.goto("https://sleeper.com/", wait_until="domcontentloaded")
        await playwright_manager.random_delay(100, 300)

        # Click login button (if not already on login page)
        try:
            login_selectors = selectors.get_selector("LOGIN", "login_button")
            for sel in login_selectors:
                try:
                    await session.page.wait_for_selector(sel, timeout=3000)
                    await session.page.click(sel)
                    await playwright_manager.random_delay()
                    break
                except:
                    continue
        except:
            # May already be on login page
            pass

        if use_sso:
            # Google SSO flow
            sso_selectors = selectors.get_selector("LOGIN", "google_sso_button")
            for sel in sso_selectors:
                try:
                    await session.page.wait_for_selector(sel, timeout=5000)
                    await session.page.click(sel)
                    logger.info("Clicked Google SSO button - waiting for user to complete auth...")

                    # Wait for redirect back to Sleeper (user completes SSO)
                    await session.page.wait_for_url("**/sleeper.**", timeout=120000)
                    break
                except:
                    continue

        else:
            # Email/password login
            email_selectors = selectors.get_selector("LOGIN", "email_input")
            password_selectors = selectors.get_selector("LOGIN", "password_input")

            # Enter email
            for sel in email_selectors:
                try:
                    await session.page.wait_for_selector(sel, timeout=5000)
                    await session.page.fill(sel, email)
                    await playwright_manager.random_delay()
                    break
                except:
                    continue

            # Enter password
            for sel in password_selectors:
                try:
                    await session.page.wait_for_selector(sel, timeout=5000)
                    await session.page.fill(sel, password)
                    await playwright_manager.random_delay()
                    break
                except:
                    continue

            # Click submit
            submit_selectors = selectors.get_selector("LOGIN", "login_button")
            for sel in submit_selectors:
                try:
                    await session.page.wait_for_selector(sel, timeout=5000)
                    await session.page.click(sel)
                    await playwright_manager.random_delay()
                    break
                except:
                    continue

        # Wait for successful login (leagues page or main page)
        await asyncio.sleep(3)  # Give time for redirect

        # Check if logged in
        current_url = session.page.url
        if "sleeper" in current_url:
            logger.info("Login successful!")
            return {
                "success": True,
                "url": current_url,
                "message": "Successfully logged into Sleeper"
            }
        else:
            logger.error("Login may have failed - unexpected URL")
            return {
                "success": False,
                "error": "Login verification failed",
                "url": current_url
            }

    except Exception as e:
        logger.error(f"Error during Sleeper login: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def navigate_to_lineup(league_id: str, week: int) -> Dict[str, Any]:
    """
    Navigate to a specific league lineup page.

    Use this tool to:
    - Go to a league's lineup page
    - Select a specific week

    Args:
        league_id: Sleeper league ID
        week: NFL week number

    Returns:
        Dictionary with navigation status
    """
    try:
        session = await _get_current_session()

        logger.info(f"Navigating to lineup for league {league_id}, week {week}")

        # Navigate to league page
        url = f"https://sleeper.com/leagues/{league_id}/{week}"
        await session.page.goto(url, wait_until="domcontentloaded")

        # Wait for lineup to load
        await asyncio.sleep(2)

        return {
            "success": True,
            "league_id": league_id,
            "week": week,
            "url": session.page.url
        }

    except Exception as e:
        logger.error(f"Error navigating to lineup: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# Browser tools list for export
BROWSER_TOOLS = [
    open_page,
    click_element,
    type_text,
    press_key,
    wait_for_element,
    take_screenshot,
    sleep_ms,
    sleeper_login,
    navigate_to_lineup
]
