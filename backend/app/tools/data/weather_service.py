"""
Weather Service for NFL Games
Fetches weather forecasts for game day conditions
"""

import httpx
import logging
import os
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# OpenWeatherMap API (requires free API key)
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE = "https://api.openweathermap.org/data/2.5"

# Stadium locations (latitude, longitude, is_dome)
STADIUM_LOCATIONS = {
    "ARI": (33.5276, -112.2626, True),  # State Farm Stadium (retractable roof, usually closed)
    "ATL": (33.7553, -84.4006, True),  # Mercedes-Benz Stadium (retractable roof)
    "BAL": (39.2780, -76.6227, False),  # M&T Bank Stadium
    "BUF": (42.7738, -78.7870, False),  # Highmark Stadium
    "CAR": (35.2258, -80.8528, False),  # Bank of America Stadium
    "CHI": (41.8623, -87.6167, False),  # Soldier Field
    "CIN": (39.0954, -84.5160, False),  # Paycor Stadium
    "CLE": (41.5061, -81.6995, False),  # Cleveland Browns Stadium
    "DAL": (32.7473, -97.0945, True),  # AT&T Stadium (retractable roof)
    "DEN": (39.7439, -105.0201, False),  # Empower Field at Mile High
    "DET": (42.3400, -83.0456, True),  # Ford Field
    "GB": (44.5013, -88.0622, False),  # Lambeau Field
    "HOU": (29.6847, -95.4107, True),  # NRG Stadium (retractable roof)
    "IND": (39.7601, -86.1639, True),  # Lucas Oil Stadium (retractable roof)
    "JAX": (30.3240, -81.6373, False),  # TIAA Bank Field
    "KC": (39.0489, -94.4839, False),  # Arrowhead Stadium
    "LAC": (34.0139, -118.2880, False),  # SoFi Stadium (actually has a roof but open-air)
    "LAR": (34.0139, -118.2880, False),  # SoFi Stadium
    "LV": (36.0909, -115.1833, True),  # Allegiant Stadium
    "MIA": (25.9580, -80.2389, False),  # Hard Rock Stadium (open-air)
    "MIN": (44.9738, -93.2577, True),  # U.S. Bank Stadium
    "NE": (42.0909, -71.2643, False),  # Gillette Stadium
    "NO": (29.9511, -90.0812, True),  # Caesars Superdome
    "NYG": (40.8128, -74.0742, False),  # MetLife Stadium
    "NYJ": (40.8128, -74.0742, False),  # MetLife Stadium
    "PHI": (39.9008, -75.1675, False),  # Lincoln Financial Field
    "PIT": (40.4468, -80.0158, False),  # Acrisure Stadium
    "SF": (37.4032, -121.9698, False),  # Levi's Stadium
    "SEA": (47.5952, -122.3316, False),  # Lumen Field
    "TB": (27.9759, -82.5033, False),  # Raymond James Stadium
    "TEN": (36.1665, -86.7713, False),  # Nissan Stadium
    "WAS": (38.9076, -76.8645, False),  # FedExField
}

# Team abbreviation normalization
TEAM_MAPPINGS = {
    "WSH": "WAS",
    "LA": "LAR",
}


class WeatherService:
    """Service for fetching game day weather forecasts"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self._weather_cache: Dict[str, Any] = {}

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    def _normalize_team_abbr(self, team: str) -> str:
        """Normalize team abbreviation to standard format"""
        team_upper = team.upper()
        return TEAM_MAPPINGS.get(team_upper, team_upper)

    def is_dome_stadium(self, team: str) -> bool:
        """
        Check if a team plays in a dome or retractable roof stadium

        Args:
            team: Team abbreviation

        Returns:
            True if dome/enclosed stadium
        """
        team = self._normalize_team_abbr(team)
        location = STADIUM_LOCATIONS.get(team)

        if not location:
            return False

        return location[2]  # is_dome flag

    async def _fetch_openweather_forecast(self, lat: float, lon: float, game_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Fetch weather forecast from OpenWeatherMap API

        Args:
            lat: Latitude
            lon: Longitude
            game_time: Game date/time

        Returns:
            Weather data dict or None
        """
        if not OPENWEATHER_API_KEY:
            logger.warning("OpenWeatherMap API key not set, weather data unavailable")
            return None

        try:
            # Use 5-day forecast API
            url = f"{OPENWEATHER_BASE}/forecast"
            params = {
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHER_API_KEY,
                "units": "imperial",  # Fahrenheit
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Find forecast closest to game time
            forecasts = data.get("list", [])

            if not forecasts:
                return None

            closest_forecast = None
            min_time_diff = timedelta(days=365)

            for forecast in forecasts:
                forecast_time = datetime.fromtimestamp(forecast.get("dt", 0))
                time_diff = abs(forecast_time - game_time)

                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest_forecast = forecast

            if not closest_forecast:
                return forecasts[0]  # Fallback to first forecast

            return closest_forecast

        except Exception as e:
            logger.error(f"Error fetching OpenWeatherMap data: {e}")
            return None

    async def get_game_weather(
        self, team: str, week: int, game_time: Optional[datetime] = None, season: int = 2025
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather forecast for a team's game

        Args:
            team: Team abbreviation
            week: Week number
            game_time: Optional game time (if not provided, uses Sunday 1pm EST as default)
            season: Season year

        Returns:
            Weather data dict with temp, wind, precipitation, description
        """
        team = self._normalize_team_abbr(team)

        # Check if dome stadium
        if self.is_dome_stadium(team):
            return {
                "team": team,
                "week": week,
                "is_dome": True,
                "temperature": 72,  # Indoor temp
                "wind_speed": 0,
                "precipitation": 0.0,
                "conditions": "Indoor - Climate Controlled",
                "weather_impact": "none",
            }

        # Get stadium location
        location = STADIUM_LOCATIONS.get(team)

        if not location:
            logger.warning(f"No stadium location for team {team}")
            return None

        lat, lon, _ = location

        # Use provided game time or default to Sunday 1pm EST
        if not game_time:
            # Estimate game time (Week 1 starts around Sept 8)
            start_date = datetime(season, 9, 8, 13, 0)  # Sunday 1pm
            game_time = start_date + timedelta(weeks=week - 1)

        # Check cache
        cache_key = f"{team}_{week}_{season}"
        if cache_key in self._weather_cache:
            return self._weather_cache[cache_key]

        # Fetch forecast
        forecast = await self._fetch_openweather_forecast(lat, lon, game_time)

        if not forecast:
            # Return neutral default weather if API unavailable
            return {
                "team": team,
                "week": week,
                "is_dome": False,
                "temperature": 65,
                "wind_speed": 5,
                "precipitation": 0.0,
                "conditions": "Weather data unavailable",
                "weather_impact": "unknown",
            }

        # Parse forecast data
        main = forecast.get("main", {})
        wind = forecast.get("wind", {})
        weather = forecast.get("weather", [{}])[0]
        rain = forecast.get("rain", {}).get("3h", 0.0)  # 3-hour precipitation
        snow = forecast.get("snow", {}).get("3h", 0.0)

        temp = int(main.get("temp", 65))
        wind_speed = int(wind.get("speed", 0))
        precipitation = rain + snow
        conditions = weather.get("description", "Clear").title()

        # Assess weather impact
        weather_impact = self._assess_weather_impact(temp, wind_speed, precipitation)

        weather_data = {
            "team": team,
            "week": week,
            "is_dome": False,
            "temperature": temp,
            "wind_speed": wind_speed,
            "precipitation": round(precipitation, 2),
            "conditions": conditions,
            "weather_impact": weather_impact,
            "game_time": game_time.isoformat() if game_time else None,
        }

        # Cache result
        self._weather_cache[cache_key] = weather_data

        return weather_data

    def _assess_weather_impact(self, temp: int, wind_speed: int, precipitation: float) -> str:
        """
        Assess the impact of weather on game play

        Args:
            temp: Temperature in Fahrenheit
            wind_speed: Wind speed in mph
            precipitation: Precipitation in inches

        Returns:
            Impact level: "none", "low", "moderate", "high", "severe"
        """
        impact_score = 0

        # Temperature impact
        if temp < 20 or temp > 95:
            impact_score += 3
        elif temp < 32 or temp > 85:
            impact_score += 2
        elif temp < 40 or temp > 80:
            impact_score += 1

        # Wind impact
        if wind_speed > 25:
            impact_score += 3
        elif wind_speed > 15:
            impact_score += 2
        elif wind_speed > 10:
            impact_score += 1

        # Precipitation impact
        if precipitation > 0.5:
            impact_score += 3
        elif precipitation > 0.2:
            impact_score += 2
        elif precipitation > 0.0:
            impact_score += 1

        # Determine overall impact
        if impact_score == 0:
            return "none"
        elif impact_score <= 2:
            return "low"
        elif impact_score <= 4:
            return "moderate"
        elif impact_score <= 6:
            return "high"
        else:
            return "severe"

    def is_weather_concerning(self, temp: int, wind_speed: int, precipitation: float) -> bool:
        """
        Check if weather conditions are concerning for fantasy purposes

        Args:
            temp: Temperature in Fahrenheit
            wind_speed: Wind speed in mph
            precipitation: Precipitation in inches

        Returns:
            True if weather is concerning
        """
        impact = self._assess_weather_impact(temp, wind_speed, precipitation)
        return impact in ["high", "severe"]


# Global instance
weather_service = WeatherService()
