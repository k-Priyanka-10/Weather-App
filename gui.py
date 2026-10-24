"""
Modern Graphical User Interface (GUI) for the Weather Forecast Application using Tkinter.
Supports Dark/Light theme, hourly/daily forecasts, search autocomplete, favorites,
offline mode, and threaded asynchronous data fetching.
"""

from datetime import datetime
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional

from config import config
from icon_generator import get_tk_icon
from models import DailyForecast, HourlyForecast, LocationData, WeatherReport
from weather_service import WeatherService, degrees_to_cardinal, get_uv_description

# Color Palettes
THEMES = {
    "dark": {
        "bg_root": "#0f172a",         # Deep slate navy
        "bg_surface": "#1e293b",      # Slate surface
        "bg_card": "#243247",         # Elevated card
        "bg_card_hover": "#2e3f59",   # Card hover
        "bg_input": "#182234",        # Input background
        "border": "#334155",          # Border line
        "text_primary": "#f8fafc",    # Pure white / light
        "text_secondary": "#94a3b8",  # Muted slate
        "text_dim": "#64748b",        # Darker muted
        "accent": "#38bdf8",          # Sky cyan
        "accent_hover": "#0284c7",    # Darker sky cyan
        "accent_text": "#0369a1",     # Accent contrast
        "success": "#22c55e",         # Green
        "warning": "#f59e0b",         # Amber
        "danger": "#ef4444",          # Red
        "badge_bg": "#1e3a5f",        # Blue-ish badge
        "temp_bar_bg": "#334155",
        "temp_bar_fg": "#38bdf8"
    },
    "light": {
        "bg_root": "#f1f5f9",         # Clean light slate
        "bg_surface": "#ffffff",      # Pure white surface
        "bg_card": "#f8fafc",         # Elevated card
        "bg_card_hover": "#f1f5f9",   # Card hover
        "bg_input": "#ffffff",        # Input background
        "border": "#e2e8f0",          # Border line
        "text_primary": "#0f172a",    # Dark slate
        "text_secondary": "#64748b",  # Medium slate
        "text_dim": "#94a3b8",        # Light slate
        "accent": "#0284c7",          # Sky blue
        "accent_hover": "#0369a1",    # Darker blue
        "accent_text": "#ffffff",     # Contrast
        "success": "#16a34a",         # Green
        "warning": "#d97706",         # Amber
        "danger": "#dc2626",          # Red
        "badge_bg": "#e0f2fe",        # Light sky badge
        "temp_bar_bg": "#e2e8f0",
        "temp_bar_fg": "#0284c7"
    }
}


class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SkyCast • Weather Forecast")
        self.geometry("980x760")
        self.minsize(860, 680)

        # Application state
        self.current_theme = config.theme
        self.colors = THEMES[self.current_theme]
        self.weather_service = WeatherService()
        self.current_report: Optional[WeatherReport] = None
        self.current_location: Optional[LocationData] = None
        self.is_loading = False
        self._auto_refresh_timer = None
        self._search_debounce_timer = None

        # Try to restore last location
        last_loc_dict = config.get("last_location")
        if last_loc_dict:
            self.current_location = LocationData(**last_loc_dict)
        else:
            self.current_location = LocationData(
                name="London", country="United Kingdom", admin1="England",
                latitude=51.5085, longitude=-0.1257, timezone="Europe/London"
            )

        # Window styling
        self.configure(bg=self.colors["bg_root"])
        self._setup_styles()

        # Build UI Structure
        self._build_header()
        self._build_scrollable_main()
        self._build_status_bar()

        # Key bindings
        self.bind("<F5>", lambda e: self.refresh_weather())
        self.bind("<Control-t>", lambda e: self.toggle_theme())
        self.bind("<Control-u>", lambda e: self.toggle_units())
        self.bind("<Control-l>", lambda e: self.detect_location())
        self.bind("<Control-f>", lambda e: self.search_entry.focus_set())

        # Start loading weather on startup
        self.refresh_weather()
        self._schedule_auto_refresh()

    def _setup_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

    def _apply_theme(self):
        self.colors = THEMES[self.current_theme]
        self.configure(bg=self.colors["bg_root"])
        self.header_frame.configure(bg=self.colors["bg_surface"])
        self.search_entry.configure(
            bg=self.colors["bg_input"],
            fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"]
        )
        self.canvas.configure(bg=self.colors["bg_root"])
        self.scroll_content.configure(bg=self.colors["bg_root"])
        self.status_bar.configure(bg=self.colors["bg_surface"])
        self.status_label.configure(bg=self.colors["bg_surface"], fg=self.colors["text_secondary"])
        self.provider_label.configure(bg=self.colors["bg_surface"], fg=self.colors["text_dim"])

        # Update theme toggle button text
        theme_icon = "☀️ Light" if self.current_theme == "dark" else "🌙 Dark"
        self.theme_btn.config(text=theme_icon)

        # Redraw content if we have current report
        if self.current_report:
            self._render_report(self.current_report)

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        config.theme = self.current_theme
        self._apply_theme()

    def toggle_units(self):
        new_unit = "imperial" if config.unit == "metric" else "metric"
        config.unit = new_unit
        self.unit_btn.config(text="°F" if new_unit == "imperial" else "°C")
        self.refresh_weather()

    # -------------------------------------------------------------
    # UI Component Builders
    # -------------------------------------------------------------
    def _build_header(self):
        self.header_frame = tk.Frame(self, bg=self.colors["bg_surface"], height=64, padx=16, pady=10)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)

        # Brand / Logo
        brand_frame = tk.Frame(self.header_frame, bg=self.colors["bg_surface"])
        brand_frame.pack(side=tk.LEFT, padx=(4, 16))

        brand_icon = tk.Label(brand_frame, text="⛅", font=("Segoe UI Emoji", 20), bg=self.colors["bg_surface"])
        brand_icon.pack(side=tk.LEFT, padx=(0, 6))

        brand_title = tk.Label(brand_frame, text="SkyCast", font=("Segoe UI", 16, "bold"),
                               bg=self.colors["bg_surface"], fg=self.colors["accent"])
        brand_title.pack(side=tk.LEFT)

        # Search Bar Container
        search_box = tk.Frame(self.header_frame, bg=self.colors["border"], padx=1, pady=1)
        search_box.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        search_inner = tk.Frame(search_box, bg=self.colors["bg_input"], padx=6, pady=2)
        search_inner.pack(fill=tk.BOTH, expand=True)

        search_icon = tk.Label(search_inner, text="🔍", font=("Segoe UI", 11), bg=self.colors["bg_input"], fg=self.colors["text_dim"])
        search_icon.pack(side=tk.LEFT, padx=(4, 6))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_inner,
            textvariable=self.search_var,
            font=("Segoe UI", 12),
            bg=self.colors["bg_input"],
            fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"],
            relief=tk.FLAT,
            bd=0
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=4)
        self.search_entry.bind("<Return>", lambda e: self._on_search_submit())
        self.search_entry.bind("<KeyRelease>", self._on_search_key_release)

        # Autocomplete dropdown listbox (hidden initially)
        self.suggestion_window = None

        search_btn = tk.Button(
            search_inner,
            text="Search",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["accent"],
            fg="#ffffff",
            activebackground=self.colors["accent_hover"],
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            cursor="hand2",
            command=self._on_search_submit
        )
        search_btn.pack(side=tk.RIGHT, padx=2)

        # Quick Actions Frame
        actions_frame = tk.Frame(self.header_frame, bg=self.colors["bg_surface"])
        actions_frame.pack(side=tk.RIGHT)

        # Location Button (IP Geolocation)
        self.loc_btn = tk.Button(
            actions_frame,
            text="📍 Locate",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["bg_card_hover"],
            activeforeground=self.colors["text_primary"],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.detect_location
        )
        self.loc_btn.pack(side=tk.LEFT, padx=4)

        # Favorites Menu Button
        self.fav_btn = tk.Menubutton(
            actions_frame,
            text="⭐ Favorites",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["bg_card_hover"],
            activeforeground=self.colors["text_primary"],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2"
        )
        self.fav_menu = tk.Menu(self.fav_btn, tearoff=0, font=("Segoe UI", 10))
        self.fav_btn["menu"] = self.fav_menu
        self._refresh_favorites_menu()
        self.fav_btn.pack(side=tk.LEFT, padx=4)

        # Units Toggle Button (°C / °F)
        unit_text = "°F" if config.unit == "imperial" else "°C"
        self.unit_btn = tk.Button(
            actions_frame,
            text=unit_text,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["accent"],
            activebackground=self.colors["bg_card_hover"],
            activeforeground=self.colors["accent"],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.toggle_units
        )
        self.unit_btn.pack(side=tk.LEFT, padx=4)

        # Theme Toggle
        theme_icon = "☀️ Light" if self.current_theme == "dark" else "🌙 Dark"
        self.theme_btn = tk.Button(
            actions_frame,
            text=theme_icon,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["bg_card_hover"],
            activeforeground=self.colors["text_primary"],
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.toggle_theme
        )
        self.theme_btn.pack(side=tk.LEFT, padx=4)

        # Refresh Button
        self.refresh_btn = tk.Button(
            actions_frame,
            text="🔄",
            font=("Segoe UI Emoji", 11),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["bg_card_hover"],
            activeforeground=self.colors["text_primary"],
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self.refresh_weather
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=4)

        # Settings Button
        self.settings_btn = tk.Button(
            actions_frame,
            text="⚙️",
            font=("Segoe UI Emoji", 11),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["bg_card_hover"],
            activeforeground=self.colors["text_primary"],
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=4,
            cursor="hand2",
            command=self._open_settings_dialog
        )
        self.settings_btn.pack(side=tk.LEFT, padx=(4, 0))

    def _build_scrollable_main(self):
        # Container frame for canvas & scrollbar
        main_container = tk.Frame(self, bg=self.colors["bg_root"])
        main_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(main_container, bg=self.colors["bg_root"], highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(main_container, orient=tk.VERTICAL, command=self.canvas.yview)

        self.scroll_content = tk.Frame(self.canvas, bg=self.colors["bg_root"])
        self.scroll_content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Keep content frame width synced with canvas width
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.bind_all("<MouseWheel>", _on_mousewheel)

    def _build_status_bar(self):
        self.status_bar = tk.Frame(self, bg=self.colors["bg_surface"], height=28, padx=16, pady=4)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = tk.Label(
            self.status_bar,
            text="Ready",
            font=("Segoe UI", 9),
            bg=self.colors["bg_surface"],
            fg=self.colors["text_secondary"]
        )
        self.status_label.pack(side=tk.LEFT)

        self.provider_label = tk.Label(
            self.status_bar,
            text="Powered by Open-Meteo",
            font=("Segoe UI", 9),
            bg=self.colors["bg_surface"],
            fg=self.colors["text_dim"]
        )
        self.provider_label.pack(side=tk.RIGHT)

    # -------------------------------------------------------------
    # Weather Rendering & UI Sections
    # -------------------------------------------------------------
    def _render_report(self, report: WeatherReport):
        # Clear previous widgets in scroll_content
        for widget in self.scroll_content.winfo_children():
            widget.destroy()

        content = tk.Frame(self.scroll_content, bg=self.colors["bg_root"], padx=20, pady=16)
        content.pack(fill=tk.BOTH, expand=True)

        # 1. Hero Weather Card
        self._render_hero_card(content, report)

        # 2. Detailed 6-Metric Grid
        self._render_metrics_grid(content, report)

        # 3. 24-Hour Forecast Ribbon
        self._render_hourly_ribbon(content, report)

        # 4. 7-Day Extended Forecast List
        self._render_daily_forecast(content, report)

        # Update status bar
        unit_sym = "°C" if report.unit_system == "metric" else "°F"
        cache_notice = " [Offline Cached Data]" if report.is_cached else ""
        self.status_label.config(
            text=f"Updated at {report.fetch_time.strftime('%I:%M %p')}{cache_notice} • {report.location.name} ({report.current.temperature}{unit_sym})",
            fg=self.colors["warning"] if report.is_cached else self.colors["text_secondary"]
        )
        self.provider_label.config(text=f"Provider: {report.provider}")

    def _render_hero_card(self, parent: tk.Frame, report: WeatherReport):
        card = tk.Frame(parent, bg=self.colors["bg_card"], padx=24, pady=20)
        card.pack(fill=tk.X, pady=(0, 16))

        # Top line: Location & Favorite Button
        top_row = tk.Frame(card, bg=self.colors["bg_card"])
        top_row.pack(fill=tk.X)

        loc_text = f"{report.location.name}, {report.location.country}"
        if report.location.admin1 and report.location.admin1 != report.location.name:
            loc_text = f"{report.location.name}, {report.location.admin1}, {report.location.country}"

        title_lbl = tk.Label(
            top_row,
            text=loc_text,
            font=("Segoe UI", 20, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"]
        )
        title_lbl.pack(side=tk.LEFT)

        # Favorite star toggle button
        is_fav = config.is_favorite(report.location.name, report.location.country)
        fav_icon_name = "star_filled" if is_fav else "star_outline"
        fav_star_img = get_tk_icon(fav_icon_name, (22, 22))

        fav_btn = tk.Button(
            top_row,
            image=fav_star_img,
            bg=self.colors["bg_card"],
            activebackground=self.colors["bg_card_hover"],
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=lambda: self._toggle_favorite(report.location)
        )
        fav_btn.image = fav_star_img
        fav_btn.pack(side=tk.LEFT, padx=12)

        # Date & time pill
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        date_lbl = tk.Label(
            top_row,
            text=date_str,
            font=("Segoe UI", 11),
            bg=self.colors["bg_card"],
            fg=self.colors["text_secondary"]
        )
        date_lbl.pack(side=tk.RIGHT)

        # Middle row: Large Icon + Giant Temp + Condition
        mid_row = tk.Frame(card, bg=self.colors["bg_card"], pady=8)
        mid_row.pack(fill=tk.X)

        # Weather icon (large 96x96)
        weather_icon_img = get_tk_icon(report.current.icon_name, (96, 96))
        icon_lbl = tk.Label(mid_row, image=weather_icon_img, bg=self.colors["bg_card"])
        icon_lbl.image = weather_icon_img
        icon_lbl.pack(side=tk.LEFT, padx=(0, 20))

        # Temperature
        unit_sym = "°C" if report.unit_system == "metric" else "°F"
        temp_val_str = f"{int(round(report.current.temperature))}{unit_sym}"
        temp_lbl = tk.Label(
            mid_row,
            text=temp_val_str,
            font=("Segoe UI", 48, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"]
        )
        temp_lbl.pack(side=tk.LEFT, padx=(0, 24))

        # Condition & High/Low column
        cond_col = tk.Frame(mid_row, bg=self.colors["bg_card"])
        cond_col.pack(side=tk.LEFT, fill=tk.Y, pady=4)

        cond_lbl = tk.Label(
            cond_col,
            text=report.current.condition_text,
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["accent"]
        )
        cond_lbl.pack(anchor="w")

        feels_lbl = tk.Label(
            cond_col,
            text=f"Feels like {int(round(report.current.feels_like))}{unit_sym}",
            font=("Segoe UI", 11),
            bg=self.colors["bg_card"],
            fg=self.colors["text_secondary"]
        )
        feels_lbl.pack(anchor="w", pady=(2, 0))

        range_lbl = tk.Label(
            cond_col,
            text=f"High: {int(round(report.current.temp_max))}{unit_sym}  •  Low: {int(round(report.current.temp_min))}{unit_sym}",
            font=("Segoe UI", 10),
            bg=self.colors["bg_card"],
            fg=self.colors["text_dim"]
        )
        range_lbl.pack(anchor="w", pady=(2, 0))

    def _render_metrics_grid(self, parent: tk.Frame, report: WeatherReport):
        grid_frame = tk.Frame(parent, bg=self.colors["bg_root"])
        grid_frame.pack(fill=tk.X, pady=(0, 16))

        for col_idx in range(3):
            grid_frame.columnconfigure(col_idx, weight=1, uniform="metric_col")

        speed_unit = "km/h" if report.unit_system == "metric" else "mph"
        cardinal_wind = degrees_to_cardinal(report.current.wind_direction)
        uv_desc, uv_color = get_uv_description(report.current.uv_index)

        metrics = [
            ("humidity", "HUMIDITY", f"{report.current.humidity}%", "Dew point nominal"),
            ("wind", "WIND SPEED", f"{report.current.wind_speed} {speed_unit}", f"Direction: {cardinal_wind} ({report.current.wind_direction}°)"),
            ("uv", "UV INDEX", f"{report.current.uv_index}", uv_desc),
            ("pressure", "AIR PRESSURE", f"{int(report.current.pressure)} hPa", "Barometric steady"),
            ("visibility", "VISIBILITY", f"{report.current.visibility} km", "Clear viewing range"),
            ("sunrise", "SUNRISE & SUNSET", f"🌅 {report.current.sunrise}", f"🌇 {report.current.sunset}")
        ]

        for i, (icon_name, title, main_val, sub_val) in enumerate(metrics):
            row = i // 3
            col = i % 3

            card = tk.Frame(grid_frame, bg=self.colors["bg_card"], padx=16, pady=12)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")

            # Header of card
            hdr_frame = tk.Frame(card, bg=self.colors["bg_card"])
            hdr_frame.pack(fill=tk.X)

            icon_img = get_tk_icon(icon_name, (20, 20))
            ic_lbl = tk.Label(hdr_frame, image=icon_img, bg=self.colors["bg_card"])
            ic_lbl.image = icon_img
            ic_lbl.pack(side=tk.LEFT, padx=(0, 6))

            t_lbl = tk.Label(hdr_frame, text=title, font=("Segoe UI", 9, "bold"),
                             bg=self.colors["bg_card"], fg=self.colors["text_dim"])
            t_lbl.pack(side=tk.LEFT)

            # Main value
            val_lbl = tk.Label(card, text=main_val, font=("Segoe UI", 16, "bold"),
                               bg=self.colors["bg_card"], fg=self.colors["text_primary"])
            val_lbl.pack(anchor="w", pady=(6, 2))

            # Sub value
            sub_fg = uv_color if title == "UV INDEX" else self.colors["text_secondary"]
            sub_lbl = tk.Label(card, text=sub_val, font=("Segoe UI", 9),
                               bg=self.colors["bg_card"], fg=sub_fg)
            sub_lbl.pack(anchor="w")

    def _render_hourly_ribbon(self, parent: tk.Frame, report: WeatherReport):
        container = tk.Frame(parent, bg=self.colors["bg_card"], padx=16, pady=14)
        container.pack(fill=tk.X, pady=(0, 16))

        # Title
        hdr = tk.Label(
            container,
            text="⏱️  24-Hour Forecast",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"]
        )
        hdr.pack(anchor="w", pady=(0, 10))

        # Scrollable horizontal frame
        h_canvas = tk.Canvas(container, bg=self.colors["bg_card"], height=130, highlightthickness=0, bd=0)
        h_scroll = ttk.Scrollbar(container, orient=tk.HORIZONTAL, command=h_canvas.xview)
        ribbon_frame = tk.Frame(h_canvas, bg=self.colors["bg_card"])

        ribbon_frame.bind(
            "<Configure>",
            lambda e: h_canvas.configure(scrollregion=h_canvas.bbox("all"))
        )
        h_canvas.create_window((0, 0), window=ribbon_frame, anchor="nw")
        h_canvas.configure(xscrollcommand=h_scroll.set)

        h_canvas.pack(fill=tk.X, expand=True)
        h_scroll.pack(fill=tk.X, pady=(4, 0))

        unit_sym = "°"
        for hour in report.hourly:
            h_card = tk.Frame(ribbon_frame, bg=self.colors["bg_surface"], padx=10, pady=8, width=74)
            h_card.pack(side=tk.LEFT, padx=4)

            # Time label
            time_lbl = tk.Label(h_card, text=hour.time_str, font=("Segoe UI", 9, "bold"),
                                bg=self.colors["bg_surface"], fg=self.colors["text_secondary"])
            time_lbl.pack()

            # Weather icon
            ic_img = get_tk_icon(hour.icon_name, (28, 28))
            ic_lbl = tk.Label(h_card, image=ic_img, bg=self.colors["bg_surface"])
            ic_lbl.image = ic_img
            ic_lbl.pack(pady=4)

            # Temp
            t_lbl = tk.Label(h_card, text=f"{int(round(hour.temperature))}{unit_sym}",
                             font=("Segoe UI", 11, "bold"),
                             bg=self.colors["bg_surface"], fg=self.colors["text_primary"])
            t_lbl.pack()

            # Precip chance
            p_text = f"💧 {hour.precipitation_prob}%" if hour.precipitation_prob > 0 else "—"
            p_lbl = tk.Label(h_card, text=p_text, font=("Segoe UI", 8),
                             bg=self.colors["bg_surface"],
                             fg=self.colors["accent"] if hour.precipitation_prob > 20 else self.colors["text_dim"])
            p_lbl.pack()

    def _render_daily_forecast(self, parent: tk.Frame, report: WeatherReport):
        container = tk.Frame(parent, bg=self.colors["bg_card"], padx=16, pady=14)
        container.pack(fill=tk.X, pady=(0, 8))

        # Title
        hdr = tk.Label(
            container,
            text="📅  7-Day Extended Forecast",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"]
        )
        hdr.pack(anchor="w", pady=(0, 10))

        # Find global min & max to render comparative temperature bars
        all_mins = [d.temp_min for d in report.daily]
        all_maxs = [d.temp_max for d in report.daily]
        global_min = min(all_mins) if all_mins else 0
        global_max = max(all_maxs) if all_maxs else 40
        temp_range = max(1.0, global_max - global_min)

        unit_sym = "°"
        for day in report.daily:
            row_frame = tk.Frame(container, bg=self.colors["bg_card"], pady=6)
            row_frame.pack(fill=tk.X)

            # Day name (e.g. Today, Tomorrow, Friday)
            day_lbl = tk.Label(
                row_frame,
                text=day.day_name,
                font=("Segoe UI", 10, "bold"),
                width=11,
                anchor="w",
                bg=self.colors["bg_card"],
                fg=self.colors["text_primary"]
            )
            day_lbl.pack(side=tk.LEFT)

            # Weather icon (24x24)
            ic_img = get_tk_icon(day.icon_name, (24, 24))
            ic_lbl = tk.Label(row_frame, image=ic_img, bg=self.colors["bg_card"])
            ic_lbl.image = ic_img
            ic_lbl.pack(side=tk.LEFT, padx=(4, 10))

            # Condition text
            cond_lbl = tk.Label(
                row_frame,
                text=day.condition_text,
                font=("Segoe UI", 10),
                width=18,
                anchor="w",
                bg=self.colors["bg_card"],
                fg=self.colors["text_secondary"]
            )
            cond_lbl.pack(side=tk.LEFT)

            # Precipitation Chance
            precip_lbl = tk.Label(
                row_frame,
                text=f"💧 {day.precipitation_prob_max}%" if day.precipitation_prob_max > 0 else "—",
                font=("Segoe UI", 9),
                width=8,
                anchor="w",
                bg=self.colors["bg_card"],
                fg=self.colors["accent"] if day.precipitation_prob_max > 25 else self.colors["text_dim"]
            )
            precip_lbl.pack(side=tk.LEFT, padx=(4, 12))

            # Temp min
            min_lbl = tk.Label(
                row_frame,
                text=f"{int(round(day.temp_min))}{unit_sym}",
                font=("Segoe UI", 10),
                width=4,
                anchor="e",
                bg=self.colors["bg_card"],
                fg=self.colors["text_secondary"]
            )
            min_lbl.pack(side=tk.LEFT)

            # Temperature visual range bar
            bar_canvas = tk.Canvas(row_frame, width=120, height=8, bg=self.colors["temp_bar_bg"], highlightthickness=0, bd=0)
            bar_canvas.pack(side=tk.LEFT, padx=10)

            # Compute normalized offsets
            start_x = max(0, int(((day.temp_min - global_min) / temp_range) * 120))
            end_x = min(120, int(((day.temp_max - global_min) / temp_range) * 120))
            if end_x - start_x < 6:
                end_x = start_x + 6

            bar_canvas.create_rectangle(start_x, 1, end_x, 7, fill=self.colors["temp_bar_fg"], outline="")

            # Temp max
            max_lbl = tk.Label(
                row_frame,
                text=f"{int(round(day.temp_max))}{unit_sym}",
                font=("Segoe UI", 10, "bold"),
                width=4,
                anchor="w",
                bg=self.colors["bg_card"],
                fg=self.colors["text_primary"]
            )
            max_lbl.pack(side=tk.LEFT)

    # -------------------------------------------------------------
    # Async Fetching & Event Handlers
    # -------------------------------------------------------------
    def refresh_weather(self):
        """Fetch weather asynchronously in a daemon thread."""
        if not self.current_location or self.is_loading:
            return

        self.is_loading = True
        self.status_label.config(text=f"Fetching weather for {self.current_location.name}...", fg=self.colors["accent"])
        self.refresh_btn.config(state=tk.DISABLED)

        unit = config.unit
        provider = config.get("api_provider", "open-meteo")
        api_key = config.get("openweathermap_api_key", "")
        loc = self.current_location

        def _worker():
            try:
                report = self.weather_service.get_weather(
                    location=loc,
                    unit=unit,
                    provider=provider,
                    api_key=api_key
                )
                self.after(0, lambda: self._on_weather_success(report))
            except Exception as err:
                self.after(0, lambda: self._on_weather_error(str(err)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_weather_success(self, report: WeatherReport):
        self.is_loading = False
        self.refresh_btn.config(state=tk.NORMAL)
        self.current_report = report
        self.current_location = report.location

        # Save as last location
        config.set("last_location", {
            "name": report.location.name,
            "country": report.location.country,
            "admin1": report.location.admin1,
            "latitude": report.location.latitude,
            "longitude": report.location.longitude,
            "timezone": report.location.timezone,
            "country_code": report.location.country_code
        })

        self._render_report(report)
        self._refresh_favorites_menu()

    def _on_weather_error(self, err_msg: str):
        self.is_loading = False
        self.refresh_btn.config(state=tk.NORMAL)
        self.status_label.config(text=f"Error: {err_msg}", fg=self.colors["danger"])
        messagebox.showerror("Weather Fetch Error", f"Unable to fetch weather data:\n\n{err_msg}\n\nPlease check your internet connection or city name.")

    def detect_location(self):
        """Auto-detect user's location via IP geolocation."""
        self.status_label.config(text="Detecting your current location...", fg=self.colors["accent"])
        self.loc_btn.config(state=tk.DISABLED)

        def _worker():
            loc = self.weather_service.detect_current_location()
            if loc:
                self.after(0, lambda: self._on_location_detected(loc))
            else:
                self.after(0, self._on_location_detect_failed)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_location_detected(self, loc: LocationData):
        self.loc_btn.config(state=tk.NORMAL)
        self.current_location = loc
        self.refresh_weather()

    def _on_location_detect_failed(self):
        self.loc_btn.config(state=tk.NORMAL)
        self.status_label.config(text="Could not detect location. Please search manually.", fg=self.colors["warning"])
        messagebox.showwarning("Location Detection", "Could not automatically determine your location. Please type your city in the search bar.")

    # -------------------------------------------------------------
    # Search & Autocomplete
    # -------------------------------------------------------------
    def _on_search_key_release(self, event):
        # Ignore navigation keys
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return

        query = self.search_var.get().strip()
        if len(query) < 2:
            self._close_suggestions()
            return

        # Debounce typing
        if self._search_debounce_timer:
            self.after_cancel(self._search_debounce_timer)
        self._search_debounce_timer = self.after(350, lambda: self._trigger_autocomplete(query))

    def _trigger_autocomplete(self, query: str):
        def _worker():
            results = self.weather_service.search_cities(query, count=6)
            self.after(0, lambda: self._show_suggestions(results))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_suggestions(self, results: List[LocationData]):
        if not results:
            self._close_suggestions()
            return

        if not self.suggestion_window or not tk.Toplevel.winfo_exists(self.suggestion_window):
            self.suggestion_window = tk.Toplevel(self)
            self.suggestion_window.wm_overrideredirect(True)
            self.suggestion_window.wm_attributes("-topmost", True)

        # Position right under search bar
        x = self.search_entry.winfo_rootx()
        y = self.search_entry.winfo_rooty() + self.search_entry.winfo_height() + 4
        w = max(340, self.search_entry.winfo_width())
        self.suggestion_window.geometry(f"{w}x{min(200, len(results) * 32 + 8)}+{x}+{y}")

        # Clear existing children
        for widget in self.suggestion_window.winfo_children():
            widget.destroy()

        s_frame = tk.Frame(self.suggestion_window, bg=self.colors["bg_surface"], bd=1, relief=tk.SOLID)
        s_frame.pack(fill=tk.BOTH, expand=True)

        for loc in results:
            disp_name = loc.display_name
            btn = tk.Button(
                s_frame,
                text=f"📍 {disp_name}",
                font=("Segoe UI", 10),
                anchor="w",
                bg=self.colors["bg_surface"],
                fg=self.colors["text_primary"],
                activebackground=self.colors["bg_card"],
                activeforeground=self.colors["accent"],
                relief=tk.FLAT,
                bd=0,
                padx=8,
                pady=4,
                cursor="hand2",
                command=lambda l=loc: self._select_location(l)
            )
            btn.pack(fill=tk.X)

    def _close_suggestions(self):
        if self.suggestion_window and tk.Toplevel.winfo_exists(self.suggestion_window):
            self.suggestion_window.destroy()
            self.suggestion_window = None

    def _select_location(self, loc: LocationData):
        self._close_suggestions()
        self.search_var.set(loc.short_display)
        self.current_location = loc
        self.refresh_weather()

    def _on_search_submit(self):
        self._close_suggestions()
        query = self.search_var.get().strip()
        if not query:
            return

        self.status_label.config(text=f"Searching for '{query}'...", fg=self.colors["accent"])

        def _worker():
            results = self.weather_service.search_cities(query, count=1)
            if results:
                self.after(0, lambda: self._select_location(results[0]))
            else:
                self.after(0, lambda: self._on_search_not_found(query))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_search_not_found(self, query: str):
        self.status_label.config(text=f"City '{query}' not found.", fg=self.colors["warning"])
        messagebox.showinfo("City Not Found", f"Could not find any city matching '{query}'.\nPlease check the spelling and try again.")

    # -------------------------------------------------------------
    # Favorites Management
    # -------------------------------------------------------------
    def _toggle_favorite(self, loc: LocationData):
        if config.is_favorite(loc.name, loc.country):
            config.remove_favorite(loc.name, loc.country)
        else:
            config.add_favorite({
                "name": loc.name,
                "country": loc.country,
                "admin1": loc.admin1,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timezone": loc.timezone,
                "country_code": loc.country_code
            })

        self._refresh_favorites_menu()
        if self.current_report:
            self._render_report(self.current_report)

    def _refresh_favorites_menu(self):
        self.fav_menu.delete(0, tk.END)
        favs = config.favorites

        if not favs:
            self.fav_menu.add_command(label="No favorites yet", state=tk.DISABLED)
            return

        for f in favs:
            disp = f.get("name", "")
            if f.get("country"):
                disp += f", {f.get('country')}"

            loc = LocationData(
                name=f.get("name", ""),
                country=f.get("country", ""),
                admin1=f.get("admin1", ""),
                latitude=f.get("latitude", 0.0),
                longitude=f.get("longitude", 0.0),
                timezone=f.get("timezone", "auto")
            )
            self.fav_menu.add_command(
                label=f"⭐ {disp}",
                command=lambda l=loc: self._select_location(l)
            )

    # -------------------------------------------------------------
    # Auto-Refresh & Settings Dialog
    # -------------------------------------------------------------
    def _schedule_auto_refresh(self):
        mins = config.get("auto_refresh_minutes", 30)
        if mins > 0:
            ms = mins * 60 * 1000
            self._auto_refresh_timer = self.after(ms, self._on_auto_refresh_trigger)

    def _on_auto_refresh_trigger(self):
        self.refresh_weather()
        self._schedule_auto_refresh()

    def _open_settings_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Settings")
        dlg.geometry("440x360")
        dlg.resizable(False, False)
        dlg.configure(bg=self.colors["bg_surface"])
        dlg.transient(self)
        dlg.grab_set()

        # Title
        t_lbl = tk.Label(dlg, text="⚙️ Weather App Settings", font=("Segoe UI", 14, "bold"),
                         bg=self.colors["bg_surface"], fg=self.colors["text_primary"])
        t_lbl.pack(pady=(16, 12))

        form = tk.Frame(dlg, bg=self.colors["bg_surface"], padx=24)
        form.pack(fill=tk.BOTH, expand=True)

        # Provider selection
        tk.Label(form, text="Weather API Provider:", font=("Segoe UI", 10, "bold"),
                 bg=self.colors["bg_surface"], fg=self.colors["text_secondary"]).pack(anchor="w", pady=(8, 2))

        provider_var = tk.StringVar(value=config.get("api_provider", "open-meteo"))
        prov_frame = tk.Frame(form, bg=self.colors["bg_surface"])
        prov_frame.pack(anchor="w")

        tk.Radiobutton(prov_frame, text="Open-Meteo (Free, No Key Needed)", variable=provider_var, value="open-meteo",
                       bg=self.colors["bg_surface"], fg=self.colors["text_primary"], selectcolor=self.colors["bg_card"]).pack(side=tk.LEFT)
        tk.Radiobutton(prov_frame, text="OpenWeatherMap", variable=provider_var, value="openweathermap",
                       bg=self.colors["bg_surface"], fg=self.colors["text_primary"], selectcolor=self.colors["bg_card"]).pack(side=tk.LEFT, padx=12)

        # OpenWeatherMap Key entry
        tk.Label(form, text="OpenWeatherMap API Key (optional):", font=("Segoe UI", 10, "bold"),
                 bg=self.colors["bg_surface"], fg=self.colors["text_secondary"]).pack(anchor="w", pady=(12, 2))

        key_var = tk.StringVar(value=config.get("openweathermap_api_key", ""))
        key_entry = tk.Entry(form, textvariable=key_var, font=("Segoe UI", 10), bg=self.colors["bg_input"],
                             fg=self.colors["text_primary"], relief=tk.SOLID, bd=1)
        key_entry.pack(fill=tk.X, ipady=3)

        # Auto refresh interval
        tk.Label(form, text="Auto-Refresh Interval:", font=("Segoe UI", 10, "bold"),
                 bg=self.colors["bg_surface"], fg=self.colors["text_secondary"]).pack(anchor="w", pady=(12, 2))

        refresh_var = tk.IntVar(value=config.get("auto_refresh_minutes", 30))
        refresh_combo = ttk.Combobox(form, values=["0 (Manual only)", "15 minutes", "30 minutes", "60 minutes"], state="readonly")
        current_idx = {0: 0, 15: 1, 30: 2, 60: 3}.get(refresh_var.get(), 2)
        refresh_combo.current(current_idx)
        refresh_combo.pack(fill=tk.X)

        # Buttons
        btn_frame = tk.Frame(dlg, bg=self.colors["bg_surface"], pady=16)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        def _save():
            config.set("api_provider", provider_var.get())
            config.set("openweathermap_api_key", key_var.get().strip())
            interval_map = {0: 0, 1: 15, 2: 30, 3: 60}
            config.set("auto_refresh_minutes", interval_map[refresh_combo.current()])
            dlg.destroy()
            self.refresh_weather()

        save_btn = tk.Button(btn_frame, text="Save Settings", font=("Segoe UI", 10, "bold"),
                             bg=self.colors["accent"], fg="#ffffff", padx=16, pady=6, relief=tk.FLAT,
                             cursor="hand2", command=_save)
        save_btn.pack(side=tk.RIGHT, padx=24)

        cancel_btn = tk.Button(btn_frame, text="Cancel", font=("Segoe UI", 10),
                               bg=self.colors["bg_card"], fg=self.colors["text_primary"], padx=14, pady=6,
                               relief=tk.FLAT, cursor="hand2", command=dlg.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=4)
