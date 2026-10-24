"""
Live integration test for Open-Meteo API fetching and geocoding.
Gracefully skips if running in an offline environment or sandbox without internet access.
"""

import socket
import unittest
from models import LocationData
from weather_service import WeatherService


def is_online() -> bool:
    try:
        # Check if DNS resolution works
        socket.gethostbyname("api.open-meteo.com")
        return True
    except OSError:
        return False


@unittest.skipUnless(is_online(), "Network connectivity required for live integration test")
class TestLiveWeatherIntegration(unittest.TestCase):
    def setUp(self):
        self.service = WeatherService(timeout=10)

    def test_search_and_fetch_weather(self):
        # 1. Search city
        results = self.service.search_cities("Tokyo", count=1)
        self.assertGreater(len(results), 0)
        tokyo = results[0]
        self.assertEqual(tokyo.name, "Tokyo")

        # 2. Fetch weather for Tokyo
        report = self.service.get_weather(tokyo, unit="metric")
        self.assertIsNotNone(report)
        self.assertEqual(report.location.name, "Tokyo")
        self.assertIsNotNone(report.current.temperature)
        self.assertGreater(len(report.hourly), 0)
        self.assertGreater(len(report.daily), 0)
        print(f"[Live Test] Tokyo Temp: {report.current.temperature}°C, Condition: {report.current.condition_text}")
        print(f"[Live Test] Hourly count: {len(report.hourly)}, Daily count: {len(report.daily)}")


if __name__ == "__main__":
    unittest.main()
