# ⛅ SkyCast Weather Forecast Application

A modern, responsive desktop weather application built with **Python**, **Tkinter**, and **Weather APIs** (Open-Meteo and OpenWeatherMap). SkyCast delivers real-time weather observations, a 24-hour hourly forecast ribbon, a 7-day extended forecast with visual temperature range bars, global city search with autocomplete, one-click IP geolocation, and full offline caching.

---

## ✨ Key Features

- **Real-Time Weather Conditions**:
  - Live temperature with one-click **Metric (°C)** and **Imperial (°F)** switching.
  - "Feels like" apparent temperature, plus today's High & Low ranges.
  - Dynamic weather condition descriptions mapped to WMO standards.
  - High-resolution, vector-styled weather icons generated dynamically using Pillow.

- **Comprehensive Weather Metrics (6 Modern Cards)**:
  - 💧 **Humidity**: Relative humidity percentage & dew point.
  - 💨 **Wind Speed & Direction**: Wind speed in km/h or mph, 16-point cardinal compass direction (e.g. NW, ESE), and degree bearing.
  - ☀️ **UV Index**: Live UV index with safety rating ("Low", "Moderate", "High", "Very High", "Extreme") and color indicators.
  - ⏲️ **Air Pressure**: Surface atmospheric pressure in hPa with barometric stability status.
  - 👁️ **Visibility**: Viewing distance in km.
  - 🌅 **Sunrise & Sunset**: Daily solar transit times for your exact location.

- **24-Hour Hourly Forecast Ribbon**:
  - Horizontally scrollable timeline showing upcoming temperatures, weather condition icons, and precipitation probability percentages (`💧 %`).

- **7-Day Extended Daily Forecast**:
  - Daily outlook displaying day name ("Today", "Tomorrow", "Saturday"...), weather icon, condition text, maximum precipitation probability, and comparative visual min/max temperature gradient bars.

- **Global City Search & Autocomplete**:
  - Instant city search with debounced autocomplete suggestions for cities, towns, and regions worldwide powered by Open-Meteo Geocoding.
  - 📍 **One-Click IP Geolocation**: Automatically detects your current location and loads local weather instantly.

- **Favorites Management**:
  - Save your favorite cities with the ⭐ button.
  - Fast one-click switching between saved favorite locations from the header menu.

- **Modern Dark & Light Themes**:
  - Beautiful deep slate dark mode (`#0f172a`) and crisp light mode (`#f1f5f9`).
  - Seamless live theme toggling without restarting the application.

- **Robust Threaded Architecture & Offline Caching**:
  - All network calls (weather fetching, search autocomplete, geolocation) execute on background threads (`threading.Thread`), keeping the Tkinter UI fluid and responsive without freezing.
  - Automatic local cache (`cache.json`) persists previous forecasts, enabling instant startup and fallback when working offline.

- **High-DPI Scaling on Windows**:
  - High-DPI awareness enabled via Windows shell scaling (`ctypes.windll.shcore.SetProcessDpiAwareness`) for crisp typography and graphics on 1080p, 2K, and 4K displays.

---

## 🛠️ Technologies Used

| Technology | Purpose |
| :--- | :--- |
| **Python 3.10+** | Core programming language |
| **Tkinter & TTK** | Graphical User Interface (GUI), canvas graphics, and event loop |
| **Pillow (PIL)** | Dynamic antialiased weather icon generation and image rendering |
| **Requests** | Non-blocking HTTP communication with REST APIs |
| **Open-Meteo API** | Free, open global weather forecast and geocoding (no API key required) |
| **OpenWeatherMap API** | Optional secondary provider support via in-app Settings |

---

## 📁 Project Structure

```text
d:\python\
├── main.py                 # Application entry point & High-DPI configuration
├── gui.py                  # Tkinter user interface, frames, events, & rendering
├── weather_service.py      # Weather API client, geocoding, IP detection, & caching
├── models.py               # Data models (LocationData, CurrentWeather, Hourly, Daily)
├── config.py               # Configuration manager (theme, units, favorites, intervals)
├── icon_generator.py       # Vector-style weather icon generator using Pillow
├── config.json             # Persisted user preferences and favorite cities
├── cache.json              # Local offline weather cache
├── requirements.txt        # Python dependency manifest
├── run.bat                 # Convenient Windows batch launcher
├── tests/
│   ├── test_weather.py     # Unit tests for models, config, icons, & helpers
│   ├── test_integration.py # Live API integration tests
│   └── test_gui_headless.py# Headless GUI smoke & lifecycle tests
└── assets/
    └── icons/              # Generated high-resolution weather icons
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10, 3.11, 3.12, or 3.13 installed.
- Required packages: `requests` and `pillow` (already installed or installable via pip).

### Installation

1. Navigate to the project directory:
   ```bash
   cd d:\python
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

You can launch the application in either of the following ways:

#### Option 1: Double-click or run the batch launcher
```cmd
run.bat
```

#### Option 2: Run directly with Python
```cmd
python main.py
```
*(Or `py -3.12 main.py`)*

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Enter` | Submit city search |
| `F5` | Refresh weather data |
| `Ctrl + T` | Toggle between Dark and Light mode |
| `Ctrl + U` | Toggle units between Celsius (°C) and Fahrenheit (°F) |
| `Ctrl + L` | Auto-detect current location via IP |
| `Ctrl + F` | Focus the city search box |

---

## ⚙️ Configuration & API Settings

SkyCast works completely out of the box with **zero configuration required**, using the free, rate-limit-friendly **Open-Meteo API**.

If you wish to use **OpenWeatherMap**:
1. Click the **⚙️ Settings** icon in the top right.
2. Select **OpenWeatherMap**.
3. Paste your OpenWeatherMap API key into the input field.
4. Click **Save Settings**.

You can also adjust the background auto-refresh interval:
- `0 (Manual only)`
- `15 minutes`
- `30 minutes` *(default)*
- `60 minutes`

---

## 🧪 Running the Test Suite

Run the automated test suite to verify models, config management, icon generation, and GUI lifecycle:

```bash
# Run all unit tests
python -m unittest discover -s tests

# Run specific test modules
python -m unittest tests/test_weather.py
python -m unittest tests/test_gui_headless.py
python -m unittest tests/test_integration.py
```

---

## 📄 License
This project is open-source and free to use for personal and educational purposes.
