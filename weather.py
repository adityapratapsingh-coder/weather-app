"""
Weather data layer (Open-Meteo — free, no API key).

  Geocoding:    https://geocoding-api.open-meteo.com/v1/search
  Forecast:     https://api.open-meteo.com/v1/forecast
  Air Quality:  https://air-quality-api.open-meteo.com/v1/air-quality

Moon phase is computed locally. HTTP uses Python's standard library only.
"""
import json
import math
import datetime
import requests

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

FORECAST_DAYS = 15

WEATHER_CODES = {
    0: ("Clear sky", "\u2600\ufe0f"), 1: ("Mainly clear", "\U0001f324\ufe0f"), 2: ("Partly cloudy", "\u26c5"),
    3: ("Overcast", "\u2601\ufe0f"), 45: ("Fog", "\U0001f32b\ufe0f"), 48: ("Rime fog", "\U0001f32b\ufe0f"),
    51: ("Light drizzle", "\U0001f326\ufe0f"), 53: ("Drizzle", "\U0001f326\ufe0f"), 55: ("Heavy drizzle", "\U0001f326\ufe0f"),
    56: ("Freezing drizzle", "\U0001f327\ufe0f"), 57: ("Freezing drizzle", "\U0001f327\ufe0f"),
    61: ("Light rain", "\U0001f327\ufe0f"), 63: ("Rain", "\U0001f327\ufe0f"), 65: ("Heavy rain", "\U0001f327\ufe0f"),
    66: ("Freezing rain", "\U0001f327\ufe0f"), 67: ("Freezing rain", "\U0001f327\ufe0f"),
    71: ("Light snow", "\U0001f328\ufe0f"), 73: ("Snow", "\U0001f328\ufe0f"), 75: ("Heavy snow", "\u2744\ufe0f"),
    77: ("Snow grains", "\U0001f328\ufe0f"), 80: ("Light showers", "\U0001f326\ufe0f"), 81: ("Showers", "\U0001f327\ufe0f"),
    82: ("Violent showers", "\u26c8\ufe0f"), 85: ("Snow showers", "\U0001f328\ufe0f"), 86: ("Heavy snow showers", "\u2744\ufe0f"),
    95: ("Thunderstorm", "\u26c8\ufe0f"), 96: ("Thunderstorm + hail", "\u26c8\ufe0f"), 99: ("Severe thunderstorm", "\u26c8\ufe0f"),
}

MOON_PHASES = [
    ("New moon", "\U0001f311"), ("Waxing crescent", "\U0001f312"), ("First quarter", "\U0001f313"),
    ("Waxing gibbous", "\U0001f314"), ("Full moon", "\U0001f315"), ("Waning gibbous", "\U0001f316"),
    ("Last quarter", "\U0001f317"), ("Waning crescent", "\U0001f318"),
]

HEATMAP_CITIES = [
    ("New York", 40.71, -74.01), ("London", 51.51, -0.13), ("Tokyo", 35.68, 139.69),
    ("New Delhi", 28.61, 77.21), ("Mumbai", 19.08, 72.88), ("Beijing", 39.90, 116.41),
    ("Shanghai", 31.23, 121.47), ("Moscow", 55.76, 37.62), ("Paris", 48.85, 2.35),
    ("Berlin", 52.52, 13.40), ("Cairo", 30.04, 31.24), ("Lagos", 6.52, 3.38),
    ("Sydney", -33.87, 151.21), ("Sao Paulo", -23.55, -46.63), ("Mexico City", 19.43, -99.13),
    ("Los Angeles", 34.05, -118.24), ("Dubai", 25.20, 55.27), ("Singapore", 1.35, 103.82),
    ("Bangkok", 13.76, 100.50), ("Istanbul", 41.01, 28.98), ("Toronto", 43.65, -79.38),
    ("Johannesburg", -26.20, 28.05), ("Nairobi", -1.29, 36.82), ("Jakarta", -6.21, 106.85),
    ("Lucknow", 26.85, 80.95), ("Riyadh", 24.71, 46.68), ("Tehran", 35.69, 51.39),
    ("Karachi", 24.86, 67.01), ("Buenos Aires", -34.60, -58.38), ("Madrid", 40.42, -3.70),
]


def _get_json(url, params):
    response = requests.get(url, params=params, timeout=15,
                            headers={"User-Agent": "WeatherApp/3.0"})
    response.raise_for_status()
    return response.json()


def describe(code):
    return WEATHER_CODES.get(code, ("Unknown", "\u2753"))


def theme_for(code, is_day):
    if code in (95, 96, 99): return "storm"
    if code in (45, 48): return "fog"
    if code in (71, 73, 75, 77, 85, 86): return "snow"
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82): return "rain"
    if code in (2, 3): return "cloudy"
    return "clear-day" if is_day else "clear-night"


def aqi_category(value):
    if value is None: return ("Unknown", "#9aa0a6")
    if value <= 50: return ("Good", "#4cd964")
    if value <= 100: return ("Moderate", "#ffcc00")
    if value <= 150: return ("Unhealthy (sensitive)", "#ff9500")
    if value <= 200: return ("Unhealthy", "#ff3b30")
    if value <= 300: return ("Very unhealthy", "#af52de")
    return ("Hazardous", "#8e1a1a")


def uv_category(value):
    if value is None: return "Unknown"
    if value < 3: return "Low"
    if value < 6: return "Moderate"
    if value < 8: return "High"
    if value < 11: return "Very high"
    return "Extreme"


def compass(deg):
    if deg is None: return ""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int(round(deg / 45.0)) % 8]


def moon_phase(date=None):
    date = date or datetime.datetime.utcnow()
    ref = datetime.datetime(2000, 1, 6, 18, 14)  # a known new moon
    days = (date - ref).total_seconds() / 86400.0
    phase = (days / 29.53058867) % 1.0
    index = int(round(phase * 8)) % 8
    name, emoji = MOON_PHASES[index]
    return {"name": name, "emoji": emoji, "illumination": round(abs(0.5 - phase) * -200 + 100)}


def geocode_city(city):
    data = _get_json(GEOCODE_URL, {"name": city, "count": 1, "language": "en", "format": "json"})
    results = data.get("results")
    if not results: return None
    r = results[0]
    region = ", ".join(p for p in [r.get("admin1"), r.get("country")] if p)
    return {"name": r["name"], "region": region, "country": r.get("country", ""),
            "latitude": r["latitude"], "longitude": r["longitude"], "population": r.get("population")}


def _fetch_forecast(latitude, longitude):
    return _get_json(FORECAST_URL, {
        "latitude": latitude, "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,"
                   "wind_speed_10m,wind_direction_10m,surface_pressure,cloud_cover,dew_point_2m",
        "hourly": "temperature_2m,weather_code,relative_humidity_2m,precipitation_probability,visibility,uv_index",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
                 "uv_index_max,sunrise,sunset",
        "timezone": "auto", "forecast_days": FORECAST_DAYS,
    })


def _fetch_air_quality(latitude, longitude):
    try:
        data = _get_json(AIR_QUALITY_URL, {"latitude": latitude, "longitude": longitude,
                                           "current": "us_aqi,pm2_5,pm10", "timezone": "auto"})
        cur = data.get("current", {})
        value = cur.get("us_aqi")
        label, color = aqi_category(value)
        return {"value": value, "label": label, "color": color,
                "pm2_5": cur.get("pm2_5"), "pm10": cur.get("pm10")}
    except Exception:
        return None


def _current_hour_index(times, current_time):
    current_hour = current_time[:13] + ":00"
    for i, t in enumerate(times):
        if t >= current_hour:
            return i
    return 0


def _hourly_next_24(hourly, start):
    times = hourly["time"]
    rows = []
    for i in range(start, min(start + 24, len(times))):
        _, emoji = describe(hourly["weather_code"][i])
        rows.append({"time": times[i], "temp": round(hourly["temperature_2m"][i]), "emoji": emoji,
                     "humidity": hourly["relative_humidity_2m"][i],
                     "rain_chance": hourly["precipitation_probability"][i]})
    return rows


def _alerts(temp, code, aqi):
    out = []
    if temp is not None and temp >= 40:
        out.append({"level": "severe", "text": f"Heatwave advisory — {temp}\u00b0C. Stay hydrated and avoid the midday sun."})
    if temp is not None and temp <= -5:
        out.append({"level": "severe", "text": f"Extreme cold — {temp}\u00b0C. Dress in warm layers."})
    if code in (95, 96, 99):
        out.append({"level": "warning", "text": "Thunderstorm in the area. Seek shelter if outdoors."})
    if code in (65, 82):
        out.append({"level": "warning", "text": "Heavy rain expected. Watch for local flooding."})
    if code in (75, 86):
        out.append({"level": "warning", "text": "Heavy snowfall expected."})
    if aqi and aqi.get("value") is not None and aqi["value"] > 150:
        out.append({"level": "warning", "text": f"Poor air quality (AQI {aqi['value']}). Limit outdoor activity."})
    return out


def _build_payload(location, data, aqi):
    current = data["current"]
    code = current["weather_code"]
    is_day = bool(current["is_day"])
    desc, emoji = describe(code)
    if not is_day and code in (0, 1):
        emoji = "\U0001f319"

    hourly = data["hourly"]
    idx = _current_hour_index(hourly["time"], current["time"])
    visibility_m = hourly["visibility"][idx] if hourly.get("visibility") else None
    uv_now = hourly["uv_index"][idx] if hourly.get("uv_index") else None

    daily = data["daily"]
    forecast = []
    for i in range(len(daily["time"])):
        d_desc, d_emoji = describe(daily["weather_code"][i])
        forecast.append({"date": daily["time"][i], "max": round(daily["temperature_2m_max"][i]),
                         "min": round(daily["temperature_2m_min"][i]), "description": d_desc,
                         "emoji": d_emoji, "rain_chance": daily["precipitation_probability_max"][i],
                         "uv_max": daily["uv_index_max"][i]})

    sunrise = daily["sunrise"][0] if daily.get("sunrise") else None
    sunset = daily["sunset"][0] if daily.get("sunset") else None

    return {
        "location": location,
        "utc_offset_seconds": data.get("utc_offset_seconds", 0),
        "timezone": data.get("timezone", ""),
        "current": {
            "temperature": round(current["temperature_2m"]), "feels_like": round(current["apparent_temperature"]),
            "humidity": current["relative_humidity_2m"], "wind_speed": round(current["wind_speed_10m"]),
            "wind_dir": current.get("wind_direction_10m"), "wind_compass": compass(current.get("wind_direction_10m")),
            "dew_point": round(current["dew_point_2m"]) if current.get("dew_point_2m") is not None else None,
            "pressure": round(current["surface_pressure"]) if current.get("surface_pressure") is not None else None,
            "cloud_cover": current.get("cloud_cover"),
            "visibility_km": round(visibility_m / 1000, 1) if visibility_m is not None else None,
            "uv_index": round(uv_now, 1) if uv_now is not None else None,
            "uv_label": uv_category(uv_now),
            "is_day": is_day, "description": desc, "emoji": emoji, "theme": theme_for(code, is_day),
            "local_time": current["time"], "sunrise": sunrise, "sunset": sunset,
        },
        "moon": moon_phase(),
        "hourly": _hourly_next_24(hourly, idx),
        "forecast": forecast,
        "aqi": aqi,
        "alerts": _alerts(round(current["temperature_2m"]), code, aqi),
    }


def get_weather_by_city(city):
    location = geocode_city(city)
    if location is None:
        return None
    data = _fetch_forecast(location["latitude"], location["longitude"])
    aqi = _fetch_air_quality(location["latitude"], location["longitude"])
    return _build_payload(location, data, aqi)


def get_weather_by_coords(latitude, longitude):
    data = _fetch_forecast(latitude, longitude)
    aqi = _fetch_air_quality(latitude, longitude)
    location = {"name": "Selected location", "region": "", "country": "",
                "latitude": latitude, "longitude": longitude, "population": None}
    return _build_payload(location, data, aqi)


def get_heatmap():
    lats = [c[1] for c in HEATMAP_CITIES]
    lons = [c[2] for c in HEATMAP_CITIES]
    data = _get_json(FORECAST_URL, {"latitude": ",".join(str(x) for x in lats),
                                    "longitude": ",".join(str(x) for x in lons),
                                    "current": "temperature_2m,weather_code", "timezone": "auto"})
    items = data if isinstance(data, list) else [data]
    cities = []
    for (name, lat, lon), entry in zip(HEATMAP_CITIES, items):
        cur = entry.get("current", {})
        temp = cur.get("temperature_2m")
        cities.append({"name": name, "lat": lat, "lon": lon,
                       "temp": round(temp) if temp is not None else None})
    return cities
