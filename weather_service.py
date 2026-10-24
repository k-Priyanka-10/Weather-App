"""
Weather service handling data retrieval from Open-Meteo and OpenWeatherMap,
geocoding, IP geolocation, caching, and unit conversions.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests

from models import CurrentWeather, DailyForecast, HourlyForecast, LocationData, WeatherReport

CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache.json")


# WMO Weather interpretation codes (WW)
WMO_CODES: Dict[int, Tuple[str, str, str]] = {
    # code: (description, day_icon, night_icon)
    0: ("Clear Sky", "clear_day", "clear_night"),
    1: ("Mainly Clear", "clear_day", "clear_night"),
    2: ("Partly Cloudy", "partly_cloudy_day", "partly_cloudy_night"),
    3: ("Overcast", "cloudy", "cloudy"),
    45: ("Foggy", "fog", "fog"),
    48: ("Depositing Rime Fog", "fog", "fog"),
    51: ("Light Drizzle", "rain_light", "rain_light"),
    53: ("Moderate Drizzle", "rain_light", "rain_light"),
    55: ("Dense Drizzle", "rain_light", "rain_light"),
    56: ("Light Freezing Drizzle", "rain_light", "rain_light"),
    57: ("Dense Freezing Drizzle", "rain_light", "rain_light"),
    61: ("Slight Rain", "rain_light", "rain_light"),
    63: ("Moderate Rain", "rain", "rain"),
    65: ("Heavy Rain", "rain_heavy", "rain_heavy"),
    66: ("Light Freezing Rain", "rain", "rain"),
    67: ("Heavy Freezing Rain", "rain_heavy", "rain_heavy"),
    71: ("Slight Snow", "snow", "snow"),
    73: ("Moderate Snow", "snow", "snow"),
    75: ("Heavy Snow", "snow", "snow"),
    77: ("Snow Grains", "snow", "snow"),
    80: ("Slight Rain Showers", "rain_light", "rain_light"),
    81: ("Moderate Rain Showers", "rain", "rain"),
    82: ("Violent Rain Showers", "rain_heavy", "rain_heavy"),
    85: ("Slight Snow Showers", "snow", "snow"),
    86: ("Heavy Snow Showers", "snow", "snow"),
    95: ("Thunderstorm", "thunderstorm", "thunderstorm"),
    96: ("Thunderstorm with Slight Hail", "thunderstorm", "thunderstorm"),
    99: ("Thunderstorm with Heavy Hail", "thunderstorm", "thunderstorm"),
}


def get_condition_info(code: int, is_day: bool = True) -> Tuple[str, str]:
    """Returns (condition_text, icon_name) for a given WMO weather code."""
    if code in WMO_CODES:
        desc, day_icon, night_icon = WMO_CODES[code]
        return desc, day_icon if is_day else night_icon
    return "Unknown", "cloudy"


def degrees_to_cardinal(deg: float) -> str:
    """Convert wind direction in degrees to compass cardinal direction."""
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    val = int((deg / 22.5) + 0.5)
    return directions[val % 16]


def get_uv_description(uv: float) -> Tuple[str, str]:
    """Returns (UV rating text, hex color) for a UV index."""
    if uv < 3:
        return "Low", "#4CAF50"
    elif uv < 6:
        return "Moderate", "#FBC02D"
    elif uv < 8:
        return "High", "#FB8C00"
    elif uv < 11:
        return "Very High", "#E53935"
    else:
        return "Extreme", "#8E24AA"


class WeatherService:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AntigravityWeatherApp/2.0"})
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, default=str, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WeatherService] Cache save error: {e}")

    def detect_current_location(self) -> Optional[LocationData]:
        """Auto-detect location using IP geolocation."""
        services = [
            ("http://ip-api.com/json/", lambda d: LocationData(
                name=d.get("city", "Unknown City"),
                country=d.get("country", ""),
                admin1=d.get("regionName", ""),
                latitude=float(d.get("lat", 0.0)),
                longitude=float(d.get("lon", 0.0)),
                timezone=d.get("timezone", "auto"),
                country_code=d.get("countryCode", "")
            )),
            ("https://ipapi.co/json/", lambda d: LocationData(
                name=d.get("city", "Unknown City"),
                country=d.get("country_name", ""),
                admin1=d.get("region", ""),
                latitude=float(d.get("latitude", 0.0)),
                longitude=float(d.get("longitude", 0.0)),
                timezone=d.get("timezone", "auto"),
                country_code=d.get("country_code", "")
            ))
        ]

        for url, parser in services:
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    loc = parser(data)
                    if loc.latitude != 0.0 and loc.longitude != 0.0:
                        return loc
            except Exception as e:
                print(f"[WeatherService] Geolocation error ({url}): {e}")

        return None

    def search_cities(self, query: str, count: int = 6) -> List[LocationData]:
        """Search cities worldwide via Open-Meteo Geocoding API."""
        query = query.strip()
        if not query or len(query) < 2:
            return []

        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": query,
            "count": count,
            "language": "en",
            "format": "json"
        }

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("results", []):
                    loc = LocationData(
                        name=item.get("name", ""),
                        country=item.get("country", ""),
                        admin1=item.get("admin1", ""),
                        latitude=item.get("latitude", 0.0),
                        longitude=item.get("longitude", 0.0),
                        timezone=item.get("timezone", "auto"),
                        country_code=item.get("country_code", "")
                    )
                    results.append(loc)
                return results
        except Exception as e:
            print(f"[WeatherService] Search error for '{query}': {e}")

        return []

    def get_weather(self, location: LocationData, unit: str = "metric", provider: str = "open-meteo", api_key: str = "") -> WeatherReport:
        """Fetch current, hourly, and daily weather forecast."""
        cache_key = f"{location.latitude:.3f}_{location.longitude:.3f}_{unit}"

        # Try API fetch
        try:
            if provider == "openweathermap" and api_key.strip():
                return self._fetch_openweathermap(location, unit, api_key)
            else:
                report = self._fetch_open_meteo(location, unit)
                # Save to cache
                self._cache[cache_key] = {
                    "timestamp": datetime.now().isoformat(),
                    "location": {
                        "name": location.name, "country": location.country,
                        "admin1": location.admin1, "latitude": location.latitude,
                        "longitude": location.longitude, "timezone": location.timezone,
                        "country_code": location.country_code
                    },
                    "current": report.current.__dict__,
                    "hourly": [h.__dict__ for h in report.hourly],
                    "daily": [d.__dict__ for d in report.daily],
                    "provider": report.provider,
                    "unit": unit
                }
                self._save_cache()
                return report
        except Exception as net_err:
            print(f"[WeatherService] Network error: {net_err}. Trying cache...")
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
            raise ConnectionError(f"Unable to fetch weather data: {net_err}")

    def _fetch_open_meteo(self, location: LocationData, unit: str = "metric") -> WeatherReport:
        """Fetch weather data from Open-Meteo."""
        temp_unit = "celsius" if unit == "metric" else "fahrenheit"
        wind_unit = "kmh" if unit == "metric" else "mph"
        precip_unit = "mm" if unit == "metric" else "inch"

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,precipitation,weather_code,wind_speed_10m,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,sunrise,sunset,uv_index_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "timezone": location.timezone if location.timezone and location.timezone != "auto" else "auto",
            "temperature_unit": temp_unit,
            "wind_speed_unit": wind_unit,
            "precipitation_unit": precip_unit
        }

        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        curr_raw = data.get("current", {})
        daily_raw = data.get("daily", {})
        hourly_raw = data.get("hourly", {})

        is_day = bool(curr_raw.get("is_day", 1))
        weather_code = int(curr_raw.get("weather_code", 0))
        cond_text, icon_name = get_condition_info(weather_code, is_day)

        # Extract sunrise & sunset for today
        sunrises = daily_raw.get("sunrise", [])
        sunsets = daily_raw.get("sunset", [])
        sunrise_today = sunrises[0].split("T")[-1][:5] if sunrises else "--:--"
        sunset_today = sunsets[0].split("T")[-1][:5] if sunsets else "--:--"

        # Today's high and low
        temp_max_arr = daily_raw.get("temperature_2m_max", [])
        temp_min_arr = daily_raw.get("temperature_2m_min", [])
        uv_arr = daily_raw.get("uv_index_max", [])

        temp_max_today = temp_max_arr[0] if temp_max_arr else curr_raw.get("temperature_2m", 0.0)
        temp_min_today = temp_min_arr[0] if temp_min_arr else curr_raw.get("temperature_2m", 0.0)
        uv_today = uv_arr[0] if uv_arr else 0.0

        current = CurrentWeather(
            temperature=round(curr_raw.get("temperature_2m", 0.0), 1),
            feels_like=round(curr_raw.get("apparent_temperature", 0.0), 1),
            temp_min=round(temp_min_today, 1),
            temp_max=round(temp_max_today, 1),
            humidity=int(curr_raw.get("relative_humidity_2m", 0)),
            wind_speed=round(curr_raw.get("wind_speed_10m", 0.0), 1),
            wind_direction=int(curr_raw.get("wind_direction_10m", 0)),
            pressure=round(curr_raw.get("surface_pressure", 1013.25), 1),
            uv_index=round(uv_today, 1),
            visibility=10.0 if unit == "metric" else 6.2,  # Standard nominal visibility
            weather_code=weather_code,
            condition_text=cond_text,
            icon_name=icon_name,
            is_day=is_day,
            sunrise=sunrise_today,
            sunset=sunset_today,
            precipitation=round(curr_raw.get("precipitation", 0.0), 2),
            wind_gusts=round(curr_raw.get("wind_gusts_10m", 0.0), 1)
        )

        # Parse next 24 hours
        hourly_list: List[HourlyForecast] = []
        h_times = hourly_raw.get("time", [])
        h_temps = hourly_raw.get("temperature_2m", [])
        h_feels = hourly_raw.get("apparent_temperature", [])
        h_codes = hourly_raw.get("weather_code", [])
        h_pops = hourly_raw.get("precipitation_probability", [])
        h_precips = hourly_raw.get("precipitation", [])
        h_winds = hourly_raw.get("wind_speed_10m", [])
        h_days = hourly_raw.get("is_day", [])

        # Find current hour index
        current_iso_hour = datetime.now().strftime("%Y-%m-%dT%H:00")
        start_idx = 0
        for i, t_str in enumerate(h_times):
            if t_str >= current_iso_hour:
                start_idx = i
                break

        for i in range(start_idx, min(start_idx + 24, len(h_times))):
            t_str = h_times[i]
            dt = datetime.fromisoformat(t_str)
            time_display = dt.strftime("%I %p").lstrip("0") if i > start_idx else "Now"
            h_code = int(h_codes[i]) if i < len(h_codes) else 0
            h_day = bool(h_days[i]) if i < len(h_days) else True
            h_cond, h_icon = get_condition_info(h_code, h_day)

            hourly_list.append(HourlyForecast(
                time_str=time_display,
                datetime_val=dt,
                temperature=round(h_temps[i], 1) if i < len(h_temps) else 0.0,
                feels_like=round(h_feels[i], 1) if i < len(h_feels) else 0.0,
                weather_code=h_code,
                condition_text=h_cond,
                icon_name=h_icon,
                precipitation_prob=int(h_pops[i]) if i < len(h_pops) and h_pops[i] is not None else 0,
                precipitation_amount=round(h_precips[i], 2) if i < len(h_precips) and h_precips[i] is not None else 0.0,
                wind_speed=round(h_winds[i], 1) if i < len(h_winds) else 0.0,
                is_day=h_day
            ))

        # Parse 7-day forecast
        daily_list: List[DailyForecast] = []
        d_times = daily_raw.get("time", [])
        d_codes = daily_raw.get("weather_code", [])
        d_maxs = daily_raw.get("temperature_2m_max", [])
        d_mins = daily_raw.get("temperature_2m_min", [])
        d_precip_sums = daily_raw.get("precipitation_sum", [])
        d_pops = daily_raw.get("precipitation_probability_max", [])
        d_uvs = daily_raw.get("uv_index_max", [])
        d_winds = daily_raw.get("wind_speed_10m_max", [])

        for i in range(min(7, len(d_times))):
            date_str = d_times[i]
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            if i == 0:
                day_name = "Today"
            elif i == 1:
                day_name = "Tomorrow"
            else:
                day_name = dt.strftime("%A")

            d_code = int(d_codes[i]) if i < len(d_codes) else 0
            d_cond, d_icon = get_condition_info(d_code, is_day=True)

            daily_list.append(DailyForecast(
                date_str=date_str,
                day_name=day_name,
                temp_min=round(d_mins[i], 1) if i < len(d_mins) else 0.0,
                temp_max=round(d_maxs[i], 1) if i < len(d_maxs) else 0.0,
                weather_code=d_code,
                condition_text=d_cond,
                icon_name=d_icon,
                precipitation_sum=round(d_precip_sums[i], 2) if i < len(d_precip_sums) else 0.0,
                precipitation_prob_max=int(d_pops[i]) if i < len(d_pops) and d_pops[i] is not None else 0,
                uv_index_max=round(d_uvs[i], 1) if i < len(d_uvs) else 0.0,
                wind_speed_max=round(d_winds[i], 1) if i < len(d_winds) else 0.0,
                sunrise=sunrises[i].split("T")[-1][:5] if i < len(sunrises) else "",
                sunset=sunsets[i].split("T")[-1][:5] if i < len(sunsets) else ""
            ))

        return WeatherReport(
            location=location,
            current=current,
            hourly=hourly_list,
            daily=daily_list,
            fetch_time=datetime.now(),
            provider="Open-Meteo",
            unit_system=unit,
            is_cached=False
        )

    def _fetch_openweathermap(self, location: LocationData, unit: str, api_key: str) -> WeatherReport:
        """Fetch current weather via OpenWeatherMap API."""
        owm_unit = "metric" if unit == "metric" else "imperial"
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": location.latitude,
            "lon": location.longitude,
            "units": owm_unit,
            "appid": api_key
        }
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        # Parse OpenWeatherMap response
        main = data.get("main", {})
        weather_arr = data.get("weather", [{}])
        weather_0 = weather_arr[0] if weather_arr else {}
        wind = data.get("wind", {})
        sys = data.get("sys", {})

        icon_code = weather_0.get("icon", "01d")
        is_day = icon_code.endswith("d")
        cond_text = weather_0.get("main", "Clear")

        icon_map = {
            "01d": "clear_day", "01n": "clear_night",
            "02d": "partly_cloudy_day", "02n": "partly_cloudy_night",
            "03d": "cloudy", "03n": "cloudy",
            "04d": "cloudy", "04n": "cloudy",
            "09d": "rain_light", "09n": "rain_light",
            "10d": "rain", "10n": "rain",
            "11d": "thunderstorm", "11n": "thunderstorm",
            "13d": "snow", "13n": "snow",
            "50d": "fog", "50n": "fog",
        }
        icon_name = icon_map.get(icon_code, "partly_cloudy_day" if is_day else "partly_cloudy_night")

        sunrise_ts = sys.get("sunrise", 0)
        sunset_ts = sys.get("sunset", 0)
        sunrise_str = datetime.fromtimestamp(sunrise_ts).strftime("%H:%M") if sunrise_ts else "--:--"
        sunset_str = datetime.fromtimestamp(sunset_ts).strftime("%H:%M") if sunset_ts else "--:--"

        current = CurrentWeather(
            temperature=round(main.get("temp", 0.0), 1),
            feels_like=round(main.get("feels_like", 0.0), 1),
            temp_min=round(main.get("temp_min", 0.0), 1),
            temp_max=round(main.get("temp_max", 0.0), 1),
            humidity=int(main.get("humidity", 0)),
            wind_speed=round(wind.get("speed", 0.0), 1),
            wind_direction=int(wind.get("deg", 0)),
            pressure=round(main.get("pressure", 1013), 1),
            uv_index=0.0,
            visibility=round(data.get("visibility", 10000) / 1000.0, 1),
            weather_code=0,
            condition_text=cond_text,
            icon_name=icon_name,
            is_day=is_day,
            sunrise=sunrise_str,
            sunset=sunset_str
        )

        # For hourly and daily, also enrich with Open-Meteo so the charts are complete
        om_report = self._fetch_open_meteo(location, unit)
        return WeatherReport(
            location=location,
            current=current,
            hourly=om_report.hourly,
            daily=om_report.daily,
            fetch_time=datetime.now(),
            provider="OpenWeatherMap",
            unit_system=unit,
            is_cached=False
        )

    def _get_from_cache(self, cache_key: str) -> Optional[WeatherReport]:
        """Retrieve weather report from local cache if available."""
        if cache_key in self._cache:
            c = self._cache[cache_key]
            try:
                loc_dict = c.get("location", {})
                loc = LocationData(
                    name=loc_dict.get("name", "Unknown"),
                    country=loc_dict.get("country", ""),
                    admin1=loc_dict.get("admin1", ""),
                    latitude=loc_dict.get("latitude", 0.0),
                    longitude=loc_dict.get("longitude", 0.0),
                    timezone=loc_dict.get("timezone", "auto"),
                    country_code=loc_dict.get("country_code", "")
                )
                curr_dict = c.get("current", {})
                current = CurrentWeather(**curr_dict)

                hourly = [
                    HourlyForecast(
                        time_str=h["time_str"],
                        datetime_val=datetime.fromisoformat(h["datetime_val"]) if isinstance(h["datetime_val"], str) else h["datetime_val"],
                        temperature=h["temperature"],
                        feels_like=h["feels_like"],
                        weather_code=h["weather_code"],
                        condition_text=h["condition_text"],
                        icon_name=h["icon_name"],
                        precipitation_prob=h["precipitation_prob"],
                        precipitation_amount=h["precipitation_amount"],
                        wind_speed=h["wind_speed"],
                        is_day=h.get("is_day", True)
                    )
                    for h in c.get("hourly", [])
                ]

                daily = [DailyForecast(**d) for d in c.get("daily", [])]

                return WeatherReport(
                    location=loc,
                    current=current,
                    hourly=hourly,
                    daily=daily,
                    fetch_time=datetime.fromisoformat(c.get("timestamp", datetime.now().isoformat())),
                    provider=c.get("provider", "Open-Meteo"),
                    unit_system=c.get("unit", "metric"),
                    is_cached=True
                )
            except Exception as e:
                print(f"[WeatherService] Cache reconstruction error: {e}")
        return None
