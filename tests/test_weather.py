"""
Automated unit and integration tests for the Weather Forecast Application.
"""

from datetime import datetime
import os
import unittest

from config import ConfigManager
from icon_generator import generate_base_icon, get_pil_icon
from models import CurrentWeather, DailyForecast, HourlyForecast, LocationData, WeatherReport
from weather_service import WeatherService, degrees_to_cardinal, get_condition_info, get_uv_description


class TestWeatherModels(unittest.TestCase):
    def test_location_display(self):
        loc = LocationData(name="London", country="United Kingdom", admin1="England")
        self.assertEqual(loc.short_display, "London, United Kingdom")
        self.assertEqual(loc.display_name, "London, England, United Kingdom")

    def test_current_weather(self):
        curr = CurrentWeather(
            temperature=22.5,
            feels_like=21.0,
            temp_min=18.0,
            temp_max=24.0,
            humidity=60,
            wind_speed=15.0,
            wind_direction=180,
            pressure=1012.0,
            uv_index=4.5,
            visibility=10.0,
            weather_code=1,
            condition_text="Mainly Clear",
            icon_name="clear_day"
        )
        self.assertEqual(curr.temperature, 22.5)
        self.assertEqual(curr.condition_text, "Mainly Clear")


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_cfg_path = os.path.join(os.path.dirname(__file__), "test_config.json")
        self.cfg = ConfigManager(file_path=self.test_cfg_path)

    def tearDown(self):
        if os.path.exists(self.test_cfg_path):
            os.remove(self.test_cfg_path)

    def test_unit_and_theme_toggle(self):
        self.cfg.unit = "imperial"
        self.assertEqual(self.cfg.unit, "imperial")
        self.cfg.unit = "metric"
        self.assertEqual(self.cfg.unit, "metric")

        self.cfg.theme = "light"
        self.assertEqual(self.cfg.theme, "light")

    def test_favorite_operations(self):
        city = {"name": "TestCity", "country": "TestCountry", "latitude": 10.0, "longitude": 20.0}
        self.assertTrue(self.cfg.add_favorite(city))
        self.assertTrue(self.cfg.is_favorite("TestCity", "TestCountry"))
        # Duplicate should return False
        self.assertFalse(self.cfg.add_favorite(city))
        # Remove
        self.assertTrue(self.cfg.remove_favorite("TestCity", "TestCountry"))
        self.assertFalse(self.cfg.is_favorite("TestCity", "TestCountry"))


class TestIconGenerator(unittest.TestCase):
    def test_generate_all_icons(self):
        icons = [
            "clear_day", "clear_night", "partly_cloudy_day", "partly_cloudy_night",
            "cloudy", "fog", "rain_light", "rain", "rain_heavy", "thunderstorm",
            "snow", "wind", "temp", "humidity", "pressure", "uv", "visibility",
            "sunrise", "sunset", "location", "search", "star_filled", "star_outline"
        ]
        for icon in icons:
            img = generate_base_icon(icon, size=64)
            self.assertEqual(img.size, (64, 64))
            self.assertEqual(img.mode, "RGBA")

    def test_get_pil_icon_resizing(self):
        img = get_pil_icon("clear_day", (32, 32))
        self.assertEqual(img.size, (32, 32))


class TestWeatherServiceHelpers(unittest.TestCase):
    def test_cardinal_directions(self):
        self.assertEqual(degrees_to_cardinal(0), "N")
        self.assertEqual(degrees_to_cardinal(90), "E")
        self.assertEqual(degrees_to_cardinal(180), "S")
        self.assertEqual(degrees_to_cardinal(270), "W")
        self.assertEqual(degrees_to_cardinal(315), "NW")

    def test_wmo_code_interpretation(self):
        cond, icon = get_condition_info(0, is_day=True)
        self.assertEqual(cond, "Clear Sky")
        self.assertEqual(icon, "clear_day")

        cond, icon = get_condition_info(0, is_day=False)
        self.assertEqual(icon, "clear_night")

        cond, icon = get_condition_info(95, is_day=True)
        self.assertEqual(cond, "Thunderstorm")
        self.assertEqual(icon, "thunderstorm")

    def test_uv_description(self):
        desc, color = get_uv_description(1.5)
        self.assertEqual(desc, "Low")
        desc, color = get_uv_description(4.2)
        self.assertEqual(desc, "Moderate")
        desc, color = get_uv_description(7.0)
        self.assertEqual(desc, "High")
        desc, color = get_uv_description(9.5)
        self.assertEqual(desc, "Very High")
        desc, color = get_uv_description(12.0)
        self.assertEqual(desc, "Extreme")


if __name__ == "__main__":
    unittest.main()
