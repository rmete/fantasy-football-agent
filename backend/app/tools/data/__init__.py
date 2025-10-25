"""
Data fetchers for NFL statistics and schedules
"""

from .nfl_stats_api import nfl_stats_api, NFLStatsAPI
from .schedule_service import schedule_service, NFLScheduleService
from .vegas_lines import vegas_lines_api, VegasLinesAPI
from .weather_service import weather_service, WeatherService

__all__ = [
    "nfl_stats_api",
    "NFLStatsAPI",
    "schedule_service",
    "NFLScheduleService",
    "vegas_lines_api",
    "VegasLinesAPI",
    "weather_service",
    "WeatherService",
]
