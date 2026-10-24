"""
Data models for the Weather Forecast Application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class LocationData:
    name: str
    country: str = ""
    admin1: str = ""  # State / Province
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = "auto"
    country_code: str = ""

    @property
    def display_name(self) -> str:
        parts = [self.name]
        if self.admin1 and self.admin1 != self.name:
            parts.append(self.admin1)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts)

    @property
    def short_display(self) -> str:
        if self.country:
            return f"{self.name}, {self.country}"
        return self.name


@dataclass
class CurrentWeather:
    temperature: float
    feels_like: float
    temp_min: float
    temp_max: float
    humidity: int
    wind_speed: float
    wind_direction: int
    pressure: float
    uv_index: float
    visibility: float
    weather_code: int
    condition_text: str
    icon_name: str
    is_day: bool = True
    sunrise: str = "--:--"
    sunset: str = "--:--"
    precipitation: float = 0.0
    wind_gusts: float = 0.0
    dew_point: Optional[float] = None


@dataclass
class HourlyForecast:
    time_str: str  # e.g., "14:00" or "2 PM"
    datetime_val: datetime
    temperature: float
    feels_like: float
    weather_code: int
    condition_text: str
    icon_name: str
    precipitation_prob: int  # percentage 0-100
    precipitation_amount: float  # mm or in
    wind_speed: float
    is_day: bool = True


@dataclass
class DailyForecast:
    date_str: str  # e.g., "2026-10-24"
    day_name: str  # e.g., "Saturday" or "Today"
    temp_min: float
    temp_max: float
    weather_code: int
    condition_text: str
    icon_name: str
    precipitation_sum: float
    precipitation_prob_max: int
    uv_index_max: float
    wind_speed_max: float
    sunrise: str = ""
    sunset: str = ""


@dataclass
class WeatherReport:
    location: LocationData
    current: CurrentWeather
    hourly: List[HourlyForecast] = field(default_factory=list)
    daily: List[DailyForecast] = field(default_factory=list)
    fetch_time: datetime = field(default_factory=datetime.now)
    provider: str = "Open-Meteo"
    unit_system: str = "metric"  # "metric" (°C, km/h) or "imperial" (°F, mph)
    is_cached: bool = False
