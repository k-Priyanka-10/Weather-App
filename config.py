"""
Configuration and settings manager for the Weather Forecast Application.
"""

import json
import os
from typing import Any, Dict, List

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG: Dict[str, Any] = {
    "unit": "metric",  # "metric" (°C, km/h, mm) or "imperial" (°F, mph, in)
    "theme": "dark",   # "dark" or "light"
    "default_city": "London",
    "last_location": {
        "name": "London",
        "country": "United Kingdom",
        "admin1": "England",
        "latitude": 51.5085,
        "longitude": -0.1257,
        "timezone": "Europe/London",
        "country_code": "GB"
    },
    "favorites": [
        {"name": "London", "country": "United Kingdom", "admin1": "England", "latitude": 51.5085, "longitude": -0.1257},
        {"name": "New York", "country": "United States", "admin1": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"name": "Tokyo", "country": "Japan", "admin1": "Tokyo", "latitude": 35.6895, "longitude": 139.6917},
        {"name": "Paris", "country": "France", "admin1": "Île-de-France", "latitude": 48.8566, "longitude": 2.3522},
        {"name": "Sydney", "country": "Australia", "admin1": "New South Wales", "latitude": -33.8688, "longitude": 151.2093}
    ],
    "auto_refresh_minutes": 30,  # 0 to disable
    "api_provider": "open-meteo",  # "open-meteo" or "openweathermap"
    "openweathermap_api_key": "",
    "cache_ttl_minutes": 20
}


class ConfigManager:
    def __init__(self, file_path: str = CONFIG_FILE):
        self.file_path = file_path
        self._data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception as e:
                print(f"[Config] Error loading config: {e}. Using defaults.")
        else:
            self.save()

    def save(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    @property
    def unit(self) -> str:
        return self._data.get("unit", "metric")

    @unit.setter
    def unit(self, val: str) -> None:
        self.set("unit", val)

    @property
    def theme(self) -> str:
        return self._data.get("theme", "dark")

    @theme.setter
    def theme(self, val: str) -> None:
        self.set("theme", val)

    @property
    def favorites(self) -> List[Dict[str, Any]]:
        return self._data.get("favorites", [])

    def add_favorite(self, loc_dict: Dict[str, Any]) -> bool:
        favs = self.favorites
        # Check if already in favorites by name & country
        for f in favs:
            if (f.get("name") == loc_dict.get("name") and 
                f.get("country") == loc_dict.get("country")):
                return False
        favs.append(loc_dict)
        self.set("favorites", favs)
        return True

    def remove_favorite(self, name: str, country: str = "") -> bool:
        favs = self.favorites
        initial_len = len(favs)
        favs = [
            f for f in favs 
            if not (f.get("name") == name and (not country or f.get("country") == country))
        ]
        if len(favs) != initial_len:
            self.set("favorites", favs)
            return True
        return False

    def is_favorite(self, name: str, country: str = "") -> bool:
        for f in self.favorites:
            if f.get("name") == name:
                if not country or f.get("country") == country:
                    return True
        return False


# Global config singleton
config = ConfigManager()
