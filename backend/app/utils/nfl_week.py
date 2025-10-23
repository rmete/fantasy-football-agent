"""
Utility to determine the current NFL week
"""
from datetime import datetime, timezone
from typing import Optional

# NFL 2025 Season Start Date (approximately Week 1 Thursday Night Football)
# Update this each season
NFL_SEASON_START = datetime(2025, 9, 4, tzinfo=timezone.utc)  # First Thursday of September 2025

# NFL Regular Season is 18 weeks
REGULAR_SEASON_WEEKS = 18

def get_current_nfl_week() -> int:
    """
    Calculate the current NFL week based on the current date

    Returns:
        int: Current NFL week (1-18), defaults to 1 if before season starts
    """
    now = datetime.now(timezone.utc)

    # If before season starts, return week 1
    if now < NFL_SEASON_START:
        return 1

    # Calculate weeks since season started
    days_since_start = (now - NFL_SEASON_START).days
    weeks_since_start = (days_since_start // 7) + 1

    # Cap at 18 weeks (regular season)
    # After week 18, could be playoffs - still use week 18 for regular season purposes
    current_week = min(weeks_since_start, REGULAR_SEASON_WEEKS)

    return int(current_week)

def get_nfl_week_info() -> dict:
    """
    Get detailed information about the current NFL week

    Returns:
        dict: Information about current week, season status, etc.
    """
    current_week = get_current_nfl_week()
    now = datetime.now(timezone.utc)

    is_preseason = now < NFL_SEASON_START
    is_regular_season = NFL_SEASON_START <= now

    days_until_season = (NFL_SEASON_START - now).days if is_preseason else 0

    return {
        "current_week": current_week,
        "season_year": 2025,
        "is_preseason": is_preseason,
        "is_regular_season": is_regular_season,
        "days_until_season": days_until_season,
        "season_start_date": NFL_SEASON_START.isoformat(),
    }

def validate_week(week: Optional[int] = None) -> int:
    """
    Validate and return a week number, using current week if None

    Args:
        week: Optional week number to validate

    Returns:
        int: Valid week number (1-18)
    """
    if week is None:
        return get_current_nfl_week()

    # Ensure week is within valid range
    return max(1, min(week, REGULAR_SEASON_WEEKS))
