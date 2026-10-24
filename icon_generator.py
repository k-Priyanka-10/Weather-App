"""
Weather icon generation and cache system using Pillow (PIL).
Generates modern, crisp, vector-styled weather icons dynamically
without requiring external image files or network downloads.
"""

import math
import os
from typing import Dict, Tuple
from PIL import Image, ImageDraw, ImageTk

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")
os.makedirs(ASSETS_DIR, exist_ok=True)

# In-memory Tkinter PhotoImage cache to prevent garbage collection
_photo_cache: Dict[str, ImageTk.PhotoImage] = {}
_pil_cache: Dict[str, Image.Image] = {}


def _draw_sun(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill: Tuple[int, int, int, int] = (255, 193, 7, 255), ray_color: Tuple[int, int, int, int] = (255, 179, 0, 230), rays: int = 8):
    # Draw sun center
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    # Draw rays
    ray_len = r * 0.55
    ray_start = r * 1.25
    for i in range(rays):
        angle = i * (2 * math.pi / rays)
        x1 = cx + math.cos(angle) * ray_start
        y1 = cy + math.sin(angle) * ray_start
        x2 = cx + math.cos(angle) * (ray_start + ray_len)
        y2 = cy + math.sin(angle) * (ray_start + ray_len)
        draw.line([x1, y1, x2, y2], fill=ray_color, width=max(2, int(r * 0.25)))


def _draw_moon(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill: Tuple[int, int, int, int] = (255, 235, 118, 255)):
    # Draw crescent moon
    base_mask = Image.new("L", (int(r * 4), int(r * 4)), 0)
    m_draw = ImageDraw.Draw(base_mask)
    mcx, mcy = r * 2, r * 2
    m_draw.ellipse([mcx - r, mcy - r, mcx + r, mcy + r], fill=255)
    # Cutout
    cutout_offset = r * 0.45
    m_draw.ellipse([mcx - r * 0.9 + cutout_offset, mcy - r + cutout_offset * 0.2, mcx + r * 0.9 + cutout_offset, mcy + r + cutout_offset * 0.2], fill=0)

    # Paste onto main image
    crop_size = int(r * 2.5)
    left = int(mcx - r * 1.25)
    top = int(mcy - r * 1.25)
    cropped_mask = base_mask.crop((left, top, left + crop_size, top + crop_size))
    moon_img = Image.new("RGBA", (crop_size, crop_size), fill)
    moon_img.putalpha(cropped_mask)
    return moon_img


def _draw_cloud(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float, fill: Tuple[int, int, int, int] = (220, 230, 242, 255)):
    # Cloud composed of multiple overlapping circles and rounded bottom
    r = scale
    draw.ellipse([cx - r * 1.4, cy - r * 0.4, cx - r * 0.4, cy + r * 0.6], fill=fill)
    draw.ellipse([cx - r * 0.7, cy - r * 0.9, cx + r * 0.7, cy + r * 0.5], fill=fill)
    draw.ellipse([cx + r * 0.2, cy - r * 0.5, cx + r * 1.4, cy + r * 0.6], fill=fill)
    draw.rounded_rectangle([cx - r * 1.2, cy, cx + r * 1.2, cy + r * 0.6], radius=int(r * 0.3), fill=fill)


def generate_base_icon(name: str, size: int = 256) -> Image.Image:
    """Generate high-resolution 256x256 RGBA image for given weather icon."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = size / 2

    if name == "clear_day":
        _draw_sun(draw, center, center, size * 0.26)

    elif name == "clear_night":
        moon = _draw_moon(draw, center, center, size * 0.28, fill=(255, 235, 130, 255))
        img.paste(moon, (int(center - moon.width / 2), int(center - moon.height / 2)), moon)
        # Add 2 tiny twinkling stars
        draw.ellipse([size * 0.72, size * 0.25, size * 0.76, size * 0.29], fill=(255, 255, 255, 220))
        draw.ellipse([size * 0.25, size * 0.65, size * 0.28, size * 0.68], fill=(255, 255, 255, 180))

    elif name == "partly_cloudy_day":
        # Sun in upper left/behind
        _draw_sun(draw, size * 0.38, size * 0.38, size * 0.18, rays=6)
        # Cloud in foreground
        _draw_cloud(draw, size * 0.56, size * 0.60, size * 0.24, fill=(235, 240, 248, 250))

    elif name == "partly_cloudy_night":
        moon = _draw_moon(draw, center, center, size * 0.22, fill=(255, 235, 130, 255))
        img.paste(moon, (int(size * 0.25), int(size * 0.20)), moon)
        _draw_cloud(draw, size * 0.56, size * 0.60, size * 0.24, fill=(210, 220, 235, 250))

    elif name == "cloudy" or name == "overcast":
        # Back darker cloud
        _draw_cloud(draw, size * 0.42, size * 0.44, size * 0.22, fill=(160, 175, 195, 240))
        # Front cloud
        _draw_cloud(draw, size * 0.54, size * 0.58, size * 0.25, fill=(225, 235, 245, 255))

    elif name == "fog":
        # Layered horizontal mist bars
        for y, w, alpha in [(0.34, 0.65, 180), (0.45, 0.8, 240), (0.56, 0.75, 220), (0.67, 0.6, 170)]:
            x1 = center - (size * w) / 2
            x2 = center + (size * w) / 2
            draw.rounded_rectangle([x1, size * y, x2, size * y + size * 0.05], radius=int(size * 0.025), fill=(200, 215, 230, alpha))

    elif name in ("rain_light", "drizzle"):
        _draw_cloud(draw, center, size * 0.42, size * 0.24, fill=(185, 200, 218, 255))
        # Rain streaks
        rain_color = (78, 168, 255, 220)
        for rx, ry in [(0.38, 0.68), (0.50, 0.74), (0.62, 0.68)]:
            draw.line([size * rx, size * ry, size * (rx - 0.04), size * (ry + 0.12)], fill=rain_color, width=int(size * 0.025))

    elif name == "rain":
        _draw_cloud(draw, center, size * 0.40, size * 0.25, fill=(140, 160, 185, 255))
        rain_color = (64, 150, 255, 240)
        for rx, ry in [(0.34, 0.66), (0.46, 0.72), (0.58, 0.66), (0.70, 0.72)]:
            draw.line([size * rx, size * ry, size * (rx - 0.05), size * (ry + 0.14)], fill=rain_color, width=int(size * 0.03))

    elif name in ("rain_heavy", "heavy_rain"):
        _draw_cloud(draw, center, size * 0.38, size * 0.26, fill=(100, 120, 145, 255))
        rain_color = (40, 130, 240, 255)
        for rx, ry in [(0.30, 0.65), (0.42, 0.72), (0.54, 0.65), (0.66, 0.72), (0.78, 0.66)]:
            draw.line([size * rx, size * ry, size * (rx - 0.06), size * (ry + 0.16)], fill=rain_color, width=int(size * 0.035))

    elif name == "thunderstorm":
        # Dark storm cloud
        _draw_cloud(draw, center, size * 0.38, size * 0.26, fill=(75, 88, 108, 255))
        # Lightning bolt
        lightning_points = [
            (size * 0.54, size * 0.55),
            (size * 0.44, size * 0.72),
            (size * 0.52, size * 0.72),
            (size * 0.46, size * 0.92),
            (size * 0.62, size * 0.68),
            (size * 0.53, size * 0.68),
        ]
        draw.polygon(lightning_points, fill=(255, 214, 0, 255))
        # Small rain drops
        rain_color = (90, 175, 255, 200)
        for rx, ry in [(0.32, 0.72), (0.72, 0.72)]:
            draw.line([size * rx, size * ry, size * (rx - 0.04), size * (ry + 0.12)], fill=rain_color, width=int(size * 0.025))

    elif name == "snow":
        _draw_cloud(draw, center, size * 0.40, size * 0.25, fill=(185, 205, 225, 255))
        # Snowflakes (asterisks / circles)
        snow_color = (255, 255, 255, 240)
        for sx, sy in [(0.36, 0.70), (0.50, 0.76), (0.64, 0.70), (0.44, 0.85), (0.58, 0.85)]:
            cx2, cy2 = size * sx, size * sy
            sr = size * 0.03
            draw.ellipse([cx2 - sr, cy2 - sr, cx2 + sr, cy2 + sr], fill=snow_color)

    elif name == "wind":
        # Stylized breeze lines
        wind_color = (130, 180, 220, 240)
        for wy, wl in [(0.38, 0.7), (0.50, 0.85), (0.62, 0.6)]:
            x1 = center - (size * wl) / 2
            x2 = center + (size * wl) / 2
            draw.line([x1, size * wy, x2 - size * 0.08, size * wy], fill=wind_color, width=int(size * 0.04))
            # Swirl tip
            draw.arc([x2 - size * 0.14, size * (wy - 0.08), x2, size * wy], start=180, end=360, fill=wind_color, width=int(size * 0.04))

    # Metric Icons
    elif name == "temp":
        # Thermometer
        draw.rounded_rectangle([size * 0.44, size * 0.20, size * 0.56, size * 0.65], radius=int(size * 0.06), outline=(255, 110, 110, 255), width=int(size * 0.04))
        draw.ellipse([size * 0.38, size * 0.58, size * 0.62, size * 0.82], fill=(255, 82, 82, 255))
        draw.rounded_rectangle([size * 0.47, size * 0.35, size * 0.53, size * 0.68], radius=int(size * 0.03), fill=(255, 82, 82, 255))

    elif name == "humidity":
        # Water droplet
        drop_points = [
            (size * 0.50, size * 0.20),
            (size * 0.70, size * 0.55),
            (size * 0.65, size * 0.78),
            (size * 0.50, size * 0.84),
            (size * 0.35, size * 0.78),
            (size * 0.30, size * 0.55),
        ]
        draw.polygon(drop_points, fill=(66, 165, 245, 240))
        draw.ellipse([size * 0.33, size * 0.52, size * 0.67, size * 0.82], fill=(66, 165, 245, 240))

    elif name == "pressure":
        # Barometer dial
        draw.ellipse([size * 0.22, size * 0.22, size * 0.78, size * 0.78], outline=(170, 190, 210, 240), width=int(size * 0.045))
        # Center pin
        draw.ellipse([size * 0.46, size * 0.46, size * 0.54, size * 0.54], fill=(255, 152, 0, 255))
        # Needle
        draw.line([size * 0.50, size * 0.50, size * 0.68, size * 0.34], fill=(255, 152, 0, 255), width=int(size * 0.04))

    elif name == "uv":
        # Sun with rays & UV text
        _draw_sun(draw, center, center, size * 0.24, fill=(255, 160, 0, 255), ray_color=(255, 180, 50, 220), rays=8)

    elif name == "visibility":
        # Eye icon
        draw.ellipse([size * 0.20, size * 0.32, size * 0.80, size * 0.68], outline=(144, 202, 249, 240), width=int(size * 0.04))
        draw.ellipse([size * 0.40, size * 0.40, size * 0.60, size * 0.60], fill=(144, 202, 249, 255))
        draw.ellipse([size * 0.46, size * 0.46, size * 0.54, size * 0.54], fill=(255, 255, 255, 255))

    elif name == "sunrise":
        # Sun rising over horizon
        draw.line([size * 0.15, size * 0.65, size * 0.85, size * 0.65], fill=(255, 183, 77, 240), width=int(size * 0.04))
        draw.chord([size * 0.32, size * 0.38, size * 0.68, size * 0.74], start=180, end=360, fill=(255, 152, 0, 255))
        # Up arrow
        draw.line([size * 0.50, size * 0.34, size * 0.50, size * 0.20], fill=(255, 213, 79, 255), width=int(size * 0.035))
        draw.line([size * 0.44, size * 0.25, size * 0.50, size * 0.19], fill=(255, 213, 79, 255), width=int(size * 0.035))
        draw.line([size * 0.56, size * 0.25, size * 0.50, size * 0.19], fill=(255, 213, 79, 255), width=int(size * 0.035))

    elif name == "sunset":
        # Sun setting below horizon
        draw.line([size * 0.15, size * 0.65, size * 0.85, size * 0.65], fill=(244, 81, 30, 240), width=int(size * 0.04))
        draw.chord([size * 0.32, size * 0.38, size * 0.68, size * 0.74], start=180, end=360, fill=(255, 87, 34, 255))
        # Down arrow
        draw.line([size * 0.50, size * 0.20, size * 0.50, size * 0.34], fill=(255, 112, 67, 255), width=int(size * 0.035))
        draw.line([size * 0.44, size * 0.29, size * 0.50, size * 0.35], fill=(255, 112, 67, 255), width=int(size * 0.035))
        draw.line([size * 0.56, size * 0.29, size * 0.50, size * 0.35], fill=(255, 112, 67, 255), width=int(size * 0.035))

    elif name == "location":
        # Map Pin
        draw.ellipse([size * 0.35, size * 0.22, size * 0.65, size * 0.52], fill=(239, 83, 80, 255))
        draw.ellipse([size * 0.44, size * 0.31, size * 0.56, size * 0.43], fill=(255, 255, 255, 255))
        pin_bottom = [
            (size * 0.36, size * 0.42),
            (size * 0.64, size * 0.42),
            (size * 0.50, size * 0.78),
        ]
        draw.polygon(pin_bottom, fill=(239, 83, 80, 255))

    elif name == "search":
        # Magnifying glass
        draw.ellipse([size * 0.25, size * 0.25, size * 0.62, size * 0.62], outline=(200, 220, 240, 240), width=int(size * 0.06))
        draw.line([size * 0.55, size * 0.55, size * 0.78, size * 0.78], fill=(200, 220, 240, 240), width=int(size * 0.07))

    elif name == "star_filled":
        # Star filled (favorite)
        points = []
        for i in range(10):
            r = size * 0.34 if i % 2 == 0 else size * 0.16
            ang = i * (math.pi / 5) - math.pi / 2
            points.append((center + math.cos(ang) * r, center + math.sin(ang) * r))
        draw.polygon(points, fill=(255, 193, 7, 255))

    elif name == "star_outline":
        # Star outline
        points = []
        for i in range(10):
            r = size * 0.34 if i % 2 == 0 else size * 0.16
            ang = i * (math.pi / 5) - math.pi / 2
            points.append((center + math.cos(ang) * r, center + math.sin(ang) * r))
        draw.polygon(points, outline=(180, 190, 205, 255), fill=(0, 0, 0, 0), width=int(size * 0.04))

    else:
        # Default fallback cloud
        _draw_cloud(draw, center, center, size * 0.26, fill=(200, 215, 235, 240))

    return img


def get_pil_icon(name: str, size: Tuple[int, int] = (48, 48)) -> Image.Image:
    """Return a resized PIL Image for the given icon name."""
    cache_key = f"{name}_{size[0]}x{size[1]}"
    if cache_key in _pil_cache:
        return _pil_cache[cache_key]

    base = generate_base_icon(name, size=256)
    resized = base.resize(size, Image.Resampling.LANCZOS)
    _pil_cache[cache_key] = resized
    return resized


def get_tk_icon(name: str, size: Tuple[int, int] = (48, 48)) -> ImageTk.PhotoImage:
    """Return a cached Tkinter PhotoImage for the given icon name."""
    cache_key = f"{name}_{size[0]}x{size[1]}"
    if cache_key in _photo_cache:
        return _photo_cache[cache_key]

    pil_img = get_pil_icon(name, size)
    tk_img = ImageTk.PhotoImage(pil_img)
    _photo_cache[cache_key] = tk_img
    return tk_img


def pregenerate_all_icons():
    """Pregenerate and save common icons to disk."""
    common_icons = [
        "clear_day", "clear_night", "partly_cloudy_day", "partly_cloudy_night",
        "cloudy", "fog", "rain_light", "rain", "rain_heavy", "thunderstorm",
        "snow", "wind", "temp", "humidity", "pressure", "uv", "visibility",
        "sunrise", "sunset", "location", "search", "star_filled", "star_outline"
    ]
    for icon_name in common_icons:
        file_path = os.path.join(ASSETS_DIR, f"{icon_name}.png")
        if not os.path.exists(file_path):
            img = generate_base_icon(icon_name, 128)
            img.save(file_path, "PNG")


# Pre-cache common icons
try:
    pregenerate_all_icons()
except Exception as e:
    print(f"[IconGenerator] Note: {e}")
