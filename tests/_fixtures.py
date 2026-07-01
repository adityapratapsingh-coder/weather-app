"""Shared fake weather data so tests never depend on the live Open-Meteo API."""


def make_weather(name="Lucknow", lat=26.85, lon=80.95):
    return {
        "location": {"name": name, "region": "Uttar Pradesh, India", "country": "India",
                     "latitude": lat, "longitude": lon, "population": 2902920},
        "utc_offset_seconds": 19800, "timezone": "Asia/Kolkata",
        "current": {
            "temperature": 31, "feels_like": 34, "humidity": 55, "wind_speed": 12,
            "wind_dir": 225, "wind_compass": "SW", "dew_point": 20, "pressure": 1006,
            "cloud_cover": 40, "visibility_km": 9.0, "uv_index": 6.5, "uv_label": "High",
            "is_day": True, "description": "Partly cloudy", "emoji": "\u26c5", "theme": "cloudy",
            "local_time": "2026-07-01T12:00", "sunrise": "2026-07-01T05:28", "sunset": "2026-07-01T19:05",
        },
        "moon": {"name": "Waxing crescent", "emoji": "\U0001f312", "illumination": 30},
        "hourly": [{"time": f"2026-07-01T{h:02d}:00", "temp": 30 + h % 3, "emoji": "\u26c5",
                    "humidity": 55, "rain_chance": 10} for h in range(12, 24)],
        "forecast": [{"date": f"2026-07-0{d}", "max": 34, "min": 26, "description": "Partly cloudy",
                      "emoji": "\u26c5", "rain_chance": 20, "uv_max": 7} for d in range(1, 10)],
        "aqi": {"value": 78, "label": "Moderate", "color": "#ffcc00", "pm2_5": 25, "pm10": 45},
        "alerts": [],
    }


FAKE_WEATHER = make_weather()
FAKE_GEO = {"name": "Lucknow", "region": "Uttar Pradesh, India", "country": "India",
            "latitude": 26.85, "longitude": 80.95, "population": 2902920}
FAKE_HEATMAP = [
    {"name": "London", "lat": 51.51, "lon": -0.13, "temp": 18},
    {"name": "Tokyo", "lat": 35.68, "lon": 139.69, "temp": 29},
    {"name": "New York", "lat": 40.71, "lon": -74.01, "temp": 24},
]
