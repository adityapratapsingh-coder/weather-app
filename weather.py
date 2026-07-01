"""
Weather data layer (OpenWeatherMap).

  Geocoding:     https://api.openweathermap.org/geo/1.0/direct
  Current:       https://api.openweathermap.org/data/2.5/weather
  5d/3h Forecast:https://api.openweathermap.org/data/2.5/forecast
  Air Pollution: https://api.openweathermap.org/data/2.5/air_pollution

The API key is read from the OWM_API_KEY environment variable (never hard-coded).
Moon phase is computed locally.
"""
import os
import math
import datetime
import requests

OWM_API_KEY = os.environ.get("OWM_API_KEY", "")

GEOCODE_URL = "https://api.openweathermap.org/geo/1.0/direct"
REVERSE_URL = "https://api.openweathermap.org/geo/1.0/reverse"
CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
AIR_QUALITY_URL = "https://api.openweathermap.org/data/2.5/air_pollution"

FORECAST_DAYS = 6

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


import time

_CACHE = {}          # simple in-memory cache: key -> (expiry_ts, data)
_CACHE_TTL = 600     # seconds (10 minutes)


def _get_json(url, params, retries=4):
    # serve from cache if fresh (fewer API calls => far less likely to be rate-limited)
    key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    hit = _CACHE.get(key)
    if hit and hit[0] > time.time():
        return hit[1]

    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=20,
                                    headers={"User-Agent": "WeatherApp/3.0"})
            # Open-Meteo throttles shared/cloud IPs with 429 (and sometimes 5xx) — back off and retry
            if response.status_code == 429 or response.status_code >= 500:
                wait = float(response.headers.get("Retry-After", 0)) or (1.5 * (attempt + 1))
                last_error = requests.HTTPError(f"{response.status_code} from {url}")
                time.sleep(min(wait, 6))
                continue
            response.raise_for_status()
            data = response.json()
            _CACHE[key] = (time.time() + _CACHE_TTL, data)
            return data
        except requests.RequestException as e:
            last_error = e
            time.sleep(1.5 * (attempt + 1))

    # everything failed — fall back to stale cache if we have any, else raise
    if hit:
        return hit[1]
    raise last_error if last_error else RuntimeError("request failed")


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


# ── OpenWeatherMap helpers ───────────────────────────────────────────────

def _owm_to_wmo(owm_id):
    """Map an OpenWeatherMap condition id to the WMO code used by describe()/theme_for()."""
    if owm_id == 800: return 0
    if owm_id == 801: return 1
    if owm_id == 802: return 2
    if owm_id in (803, 804): return 3
    if 200 <= owm_id < 300: return 95            # thunderstorm
    if 300 <= owm_id < 400: return 53            # drizzle
    if owm_id in (500,): return 61
    if owm_id in (501,): return 63
    if owm_id in (502, 503, 504): return 65
    if owm_id in (511,): return 66
    if owm_id in (520, 521): return 80
    if owm_id in (522, 531): return 82
    if owm_id in (600, 615, 620): return 71
    if owm_id in (601, 616, 621): return 73
    if owm_id in (602, 622): return 75
    if owm_id in (611, 612, 613): return 85
    if 700 <= owm_id < 800: return 45            # mist/fog/haze/etc.
    return 3


def _dew_point(temp_c, rh):
    if temp_c is None or rh is None or rh <= 0:
        return None
    a, b = 17.27, 237.7
    g = (a * temp_c) / (b + temp_c) + math.log(rh / 100.0)
    return round((b * g) / (a - g))


def _pm25_to_aqi(pm):
    """Convert a PM2.5 concentration (µg/m³) to the US AQI number."""
    if pm is None:
        return None
    bp = [(0.0, 12.0, 0, 50), (12.1, 35.4, 51, 100), (35.5, 55.4, 101, 150),
          (55.5, 150.4, 151, 200), (150.5, 250.4, 201, 300),
          (250.5, 350.4, 301, 400), (350.5, 500.4, 401, 500)]
    for lo, hi, alo, ahi in bp:
        if lo <= pm <= hi:
            return round((ahi - alo) / (hi - lo) * (pm - lo) + alo)
    return 500 if pm > 500.4 else None


def _local_iso(epoch, offset):
    """UTC epoch seconds + timezone offset -> 'YYYY-MM-DDTHH:MM' local string."""
    if epoch is None:
        return None
    dt = datetime.datetime.utcfromtimestamp(epoch + (offset or 0))
    return dt.strftime("%Y-%m-%dT%H:%M")


def _require_key():
    if not OWM_API_KEY:
        raise RuntimeError("OWM_API_KEY environment variable is not set")


# ── Data fetching ────────────────────────────────────────────────────────

def geocode_city(city):
    _require_key()
    data = _get_json(GEOCODE_URL, {"q": city, "limit": 1, "appid": OWM_API_KEY})
    if not data:
        return None
    r = data[0]
    region = ", ".join(p for p in [r.get("state"), r.get("country")] if p)
    return {"name": r.get("name", city), "region": region, "country": r.get("country", ""),
            "latitude": r["lat"], "longitude": r["lon"], "population": None}


def _reverse_name(lat, lon):
    try:
        data = _get_json(REVERSE_URL, {"lat": lat, "lon": lon, "limit": 1, "appid": OWM_API_KEY})
        if data:
            r = data[0]
            region = ", ".join(p for p in [r.get("state"), r.get("country")] if p)
            return {"name": r.get("name", "Selected location"), "region": region,
                    "country": r.get("country", ""), "latitude": lat, "longitude": lon, "population": None}
    except Exception:
        pass
    return {"name": "Selected location", "region": "", "country": "",
            "latitude": lat, "longitude": lon, "population": None}


def _fetch_current(lat, lon):
    return _get_json(CURRENT_URL, {"lat": lat, "lon": lon, "units": "metric", "appid": OWM_API_KEY})


def _fetch_forecast(lat, lon):
    return _get_json(FORECAST_URL, {"lat": lat, "lon": lon, "units": "metric", "appid": OWM_API_KEY})


def _fetch_air_quality(lat, lon):
    try:
        data = _get_json(AIR_QUALITY_URL, {"lat": lat, "lon": lon, "appid": OWM_API_KEY})
        entry = (data.get("list") or [{}])[0]
        comp = entry.get("components", {})
        pm25 = comp.get("pm2_5")
        value = _pm25_to_aqi(pm25)
        label, color = aqi_category(value)
        return {"value": value, "label": label, "color": color,
                "pm2_5": pm25, "pm10": comp.get("pm10")}
    except Exception:
        return None


def _hourly_next_24(forecast_list, offset):
    rows = []
    for item in forecast_list[:8]:            # 8 x 3h = 24h
        wid = (item.get("weather") or [{}])[0].get("id", 800)
        _, emoji = describe(_owm_to_wmo(wid))
        rows.append({"time": _local_iso(item["dt"], offset),
                     "temp": round(item["main"]["temp"]), "emoji": emoji,
                     "humidity": item["main"].get("humidity"),
                     "rain_chance": round(item.get("pop", 0) * 100)})
    return rows


def _daily_from_forecast(forecast_list, offset):
    days = {}
    order = []
    for item in forecast_list:
        local = datetime.datetime.utcfromtimestamp(item["dt"] + (offset or 0))
        key = local.strftime("%Y-%m-%d")
        if key not in days:
            days[key] = {"min": [], "max": [], "pop": [], "noon": None, "noon_gap": 99}
            order.append(key)
        d = days[key]
        d["min"].append(item["main"]["temp_min"])
        d["max"].append(item["main"]["temp_max"])
        d["pop"].append(item.get("pop", 0))
        gap = abs(local.hour - 12)
        if gap < d["noon_gap"]:
            d["noon_gap"] = gap
            d["noon"] = (item.get("weather") or [{}])[0].get("id", 800)
    out = []
    for key in order[:FORECAST_DAYS]:
        d = days[key]
        wmo = _owm_to_wmo(d["noon"])
        desc, emoji = describe(wmo)
        out.append({"date": key, "max": round(max(d["max"])), "min": round(min(d["min"])),
                    "description": desc, "emoji": emoji,
                    "rain_chance": round(max(d["pop"]) * 100), "uv_max": None})
    return out


def _alerts(temp, code, aqi):
    out = []
    if temp is not None and temp >= 40:
        out.append({"level": "severe", "text": f"Heatwave advisory \u2014 {temp}\u00b0C. Stay hydrated and avoid the midday sun."})
    if temp is not None and temp <= -5:
        out.append({"level": "severe", "text": f"Extreme cold \u2014 {temp}\u00b0C. Dress in warm layers."})
    if code in (95, 96, 99):
        out.append({"level": "warning", "text": "Thunderstorm in the area. Seek shelter if outdoors."})
    if code in (65, 82):
        out.append({"level": "warning", "text": "Heavy rain expected. Watch for local flooding."})
    if code in (75, 86):
        out.append({"level": "warning", "text": "Heavy snowfall expected."})
    if aqi and aqi.get("value") is not None and aqi["value"] > 150:
        out.append({"level": "warning", "text": f"Poor air quality (AQI {aqi['value']}). Limit outdoor activity."})
    return out


def _build_payload(location, current, forecast, aqi):
    offset = current.get("timezone", 0)
    w = (current.get("weather") or [{}])[0]
    owm_id = w.get("id", 800)
    code = _owm_to_wmo(owm_id)
    icon = w.get("icon", "01d")
    is_day = icon.endswith("d")
    desc, emoji = describe(code)
    if not is_day and code in (0, 1):
        emoji = "\U0001f319"

    main = current.get("main", {})
    wind = current.get("wind", {})
    temp = round(main.get("temp")) if main.get("temp") is not None else None
    humidity = main.get("humidity")
    vis_m = current.get("visibility")
    flist = forecast.get("list", [])

    return {
        "location": location,
        "utc_offset_seconds": offset,
        "timezone": "",
        "current": {
            "temperature": temp,
            "feels_like": round(main.get("feels_like")) if main.get("feels_like") is not None else temp,
            "humidity": humidity,
            "wind_speed": round(wind.get("speed", 0) * 3.6),      # m/s -> km/h
            "wind_dir": wind.get("deg"), "wind_compass": compass(wind.get("deg")),
            "dew_point": _dew_point(main.get("temp"), humidity),
            "pressure": main.get("pressure"),
            "cloud_cover": (current.get("clouds") or {}).get("all"),
            "visibility_km": round(vis_m / 1000, 1) if vis_m is not None else None,
            "uv_index": None, "uv_label": uv_category(None),
            "is_day": is_day, "description": desc, "emoji": emoji, "theme": theme_for(code, is_day),
            "local_time": _local_iso(current.get("dt"), offset),
            "sunrise": _local_iso((current.get("sys") or {}).get("sunrise"), offset),
            "sunset": _local_iso((current.get("sys") or {}).get("sunset"), offset),
        },
        "moon": moon_phase(),
        "hourly": _hourly_next_24(flist, offset),
        "forecast": _daily_from_forecast(flist, offset),
        "aqi": aqi,
        "alerts": _alerts(temp, code, aqi),
    }


def get_weather_by_city(city):
    location = geocode_city(city)
    if location is None:
        return None
    current = _fetch_current(location["latitude"], location["longitude"])
    forecast = _fetch_forecast(location["latitude"], location["longitude"])
    aqi = _fetch_air_quality(location["latitude"], location["longitude"])
    return _build_payload(location, current, forecast, aqi)


def get_weather_by_coords(latitude, longitude):
    _require_key()
    current = _fetch_current(latitude, longitude)
    forecast = _fetch_forecast(latitude, longitude)
    aqi = _fetch_air_quality(latitude, longitude)
    location = _reverse_name(latitude, longitude)
    if current.get("name"):
        location["name"] = current["name"]
    return _build_payload(location, current, forecast, aqi)


def get_heatmap():
    _require_key()
    cities = []
    for name, lat, lon in HEATMAP_CITIES:
        try:
            cur = _fetch_current(lat, lon)
            temp = cur.get("main", {}).get("temp")
            cities.append({"name": name, "lat": lat, "lon": lon,
                           "temp": round(temp) if temp is not None else None})
        except Exception:
            cities.append({"name": name, "lat": lat, "lon": lon, "temp": None})
    return cities
