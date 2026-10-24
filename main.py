"""
Main entry point for the SkyCast Weather Forecast Application.
"""

import os
import sys
import tkinter as tk

# Enable high DPI awareness on Windows for crisp fonts and graphics
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from gui import WeatherApp
from icon_generator import pregenerate_all_icons


def main():
    print("=" * 60)
    print(" SkyCast Weather Forecast Application")
    print(" Technologies: Python, Tkinter, Open-Meteo API, PIL")
    print("=" * 60)

    try:
        pregenerate_all_icons()
    except Exception as e:
        print(f"Icon initialization note: {e}")

    app = WeatherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
