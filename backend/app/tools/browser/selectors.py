"""
Centralized Sleeper UI Selectors
Keeps all CSS/XPath selectors in one place for easy maintenance
"""
from typing import Dict, List, Union


class SleeperSelectors:
    """
    Centralized selector registry for Sleeper fantasy football platform
    Supports multiple selector strategies for resilience
    """

    # ============================================================================
    # LOGIN & AUTHENTICATION
    # ============================================================================

    LOGIN = {
        "email_input": [
            "input[type='email']",
            "input[name='email']",
            "#email"
        ],
        "password_input": [
            "input[type='password']",
            "input[name='password']",
            "#password"
        ],
        "login_button": [
            "button:has-text('Log In')",
            "button:has-text('Sign In')",
            "button[type='submit']"
        ],
        "google_sso_button": [
            "button:has-text('Continue with Google')",
            "button:has-text('Google')"
        ],
        "continue_button": [
            "button:has-text('Continue')"
        ]
    }

    # ============================================================================
    # NAVIGATION & HEADER
    # ============================================================================

    NAVIGATION = {
        "leagues_menu": [
            "a:has-text('Leagues')",
            "nav a[href*='leagues']",
            "text=Leagues"
        ],
        "my_team": [
            "a:has-text('My Team')",
            "text=My Team"
        ],
        "lineup": [
            "a:has-text('Lineup')",
            "text=Lineup"
        ],
        "user_menu": [
            "button[aria-label='User menu']",
            ".user-menu-button"
        ]
    }

    # ============================================================================
    # LEAGUE SELECTION
    # ============================================================================

    LEAGUE = {
        "league_card": [
            ".league-card",
            "[data-testid='league-card']"
        ],
        "league_name": [
            ".league-name",
            "h3"
        ],
        "league_link": [
            "a[href*='/leagues/']"
        ]
    }

    # ============================================================================
    # LINEUP / ROSTER PAGE
    # ============================================================================

    LINEUP = {
        # Lineup container
        "lineup_container": [
            "[data-testid='lineup']",
            ".lineup-container",
            "#lineup"
        ],

        # Edit mode
        "edit_lineup_button": [
            "button:has-text('Edit Lineup')",
            "button:has-text('Edit')"
        ],
        "save_lineup_button": [
            "button:has-text('Save')",
            "button:has-text('Save Lineup')"
        ],
        "cancel_button": [
            "button:has-text('Cancel')"
        ],

        # Week selector
        "week_selector": [
            "select[name='week']",
            ".week-selector select"
        ],
        "week_option": "option[value='{week}']",

        # Player slots
        "starter_slot": [
            ".starter-slot",
            "[data-testid='starter-slot']"
        ],
        "bench_slot": [
            ".bench-slot",
            "[data-testid='bench-slot']"
        ],
        "player_slot": [
            ".player-slot",
            "[data-testid='player-slot']"
        ],

        # Player cards
        "player_card": [
            ".player-card",
            "[data-testid='player-card']"
        ],
        "player_name": [
            ".player-name",
            "[data-testid='player-name']"
        ],
        "player_position": [
            ".player-position",
            ".position-label"
        ],
        "player_team": [
            ".player-team",
            ".team-abbr"
        ],

        # Drag and drop (if applicable)
        "draggable_player": [
            "[draggable='true']",
            ".draggable-player"
        ],
        "drop_zone": [
            ".drop-zone",
            "[data-droppable='true']"
        ],

        # Confirmation
        "confirm_changes_button": [
            "button:has-text('Confirm')",
            "button:has-text('Yes')"
        ]
    }

    # ============================================================================
    # COMMON UI ELEMENTS
    # ============================================================================

    COMMON = {
        "loading_spinner": [
            ".loading",
            ".spinner",
            "[data-testid='loading']"
        ],
        "error_message": [
            ".error-message",
            ".alert-error",
            "[role='alert']"
        ],
        "success_message": [
            ".success-message",
            ".alert-success"
        ],
        "modal": [
            ".modal",
            "[role='dialog']"
        ],
        "modal_close": [
            "button[aria-label='Close']",
            ".modal-close"
        ]
    }

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    @staticmethod
    def get_selector(category: str, key: str, fallback: bool = True) -> Union[str, List[str]]:
        """
        Get selector(s) for a specific element

        Args:
            category: Selector category (LOGIN, NAVIGATION, LINEUP, etc.)
            key: Specific element key
            fallback: If True, return list of fallback selectors

        Returns:
            Single selector string or list of fallback selectors
        """
        category_map = {
            "LOGIN": SleeperSelectors.LOGIN,
            "NAVIGATION": SleeperSelectors.NAVIGATION,
            "LEAGUE": SleeperSelectors.LEAGUE,
            "LINEUP": SleeperSelectors.LINEUP,
            "COMMON": SleeperSelectors.COMMON
        }

        selectors = category_map.get(category, {}).get(key, [])

        if not selectors:
            raise ValueError(f"No selector found for {category}.{key}")

        if fallback:
            return selectors if isinstance(selectors, list) else [selectors]
        else:
            return selectors[0] if isinstance(selectors, list) else selectors

    @staticmethod
    def format_selector(selector_template: str, **kwargs) -> str:
        """
        Format a selector template with variables

        Example:
            format_selector("option[value='{week}']", week=10)
            Returns: "option[value='10']"
        """
        return selector_template.format(**kwargs)

    @staticmethod
    def player_by_name(player_name: str) -> str:
        """
        Generate selector for a player by name

        Args:
            player_name: Full player name

        Returns:
            CSS selector for player card containing the name
        """
        return f"[data-testid='player-card']:has-text('{player_name}')"

    @staticmethod
    def slot_by_position(position: str) -> str:
        """
        Generate selector for a roster slot by position

        Args:
            position: Position code (QB, RB, WR, TE, FLEX, etc.)

        Returns:
            CSS selector for slot
        """
        return f"[data-testid='roster-slot'][data-position='{position}']"


# Create singleton instance for easy import
selectors = SleeperSelectors()
