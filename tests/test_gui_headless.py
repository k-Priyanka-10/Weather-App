"""
Headless smoke test for Tkinter WeatherApp initialization and shutdown.
"""

import unittest
from gui import WeatherApp


class TestWeatherAppGUI(unittest.TestCase):
    def test_app_lifecycle(self):
        app = WeatherApp()
        # Verify initial state
        self.assertIsNotNone(app.current_location)
        self.assertIsNotNone(app.colors)
        self.assertIn("bg_root", app.colors)
        # Update once to process layout
        app.update_idletasks()
        app.update()
        # Cleanly destroy
        app.destroy()


if __name__ == "__main__":
    unittest.main()
