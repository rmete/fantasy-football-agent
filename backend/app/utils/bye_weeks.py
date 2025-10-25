"""
NFL Bye Week Schedule
Updated for 2025 season
"""

from typing import Optional, Set

# 2025 NFL Bye Week Schedule
# Source: NFL official schedule
BYE_WEEKS_2025 = {
    5: {"DET", "LAR", "PHI", "TEN"},
    6: {"KC", "LAC", "MIA", "MIN"},
    7: {"CHI", "DAL"},
    9: {"CLE", "GB", "LV", "PIT", "SF", "SEA"},
    10: {"ARI", "CAR", "NYG", "TB"},
    11: {"ATL", "BUF", "CIN", "JAX", "NO", "NYJ"},
    12: {"BAL", "DEN", "HOU", "IND", "NE", "WAS"},
    14: {},  # No byes in week 14
}

# Weeks with no byes
NO_BYE_WEEKS = {1, 2, 3, 4, 8, 13, 15, 16, 17, 18}


def get_teams_on_bye(week: int) -> Set[str]:
    """
    Get the set of teams on bye for a given week

    Args:
        week: NFL week number (1-18)

    Returns:
        Set of team abbreviations on bye that week
    """
    return BYE_WEEKS_2025.get(week, set())


def is_team_on_bye(team: str, week: int) -> bool:
    """
    Check if a team is on bye for a given week

    Args:
        team: Team abbreviation (e.g., "KC", "SF")
        week: NFL week number (1-18)

    Returns:
        True if team is on bye, False otherwise
    """
    if not team:
        return False

    bye_teams = get_teams_on_bye(week)
    return team.upper() in bye_teams


def get_team_bye_week(team: str) -> Optional[int]:
    """
    Get the bye week for a specific team

    Args:
        team: Team abbreviation (e.g., "KC", "SF")

    Returns:
        Bye week number or None if not found
    """
    if not team:
        return None

    team_upper = team.upper()
    for week, teams in BYE_WEEKS_2025.items():
        if team_upper in teams:
            return week

    return None
