# 🌍 Skyline — Weather & Climate Dashboard (PWA)

A modern, premium, responsive weather app built with **FastAPI** + **vanilla JS**.
Live conditions, hourly + 15-day forecast, an interactive temperature map with rain radar,
air quality, a world-population explorer, a smart assistant, animated weather effects, and
full **PWA** support — all with **no API keys**.

## Features

**Current weather**
- Temperature, condition + icon, feels-like, humidity, wind + **direction (compass)**,
  pressure, visibility, cloud cover, **dew point**, UV index, AQI
- **Sunrise / sunset**, **moon phase**, city population, **coordinates**, **time zone**
- **Live local date & time** (ticking clock) for the place you're viewing
- **Weather alerts** (heatwave, storm, heavy rain, poor air)
- **✨ Smart assistant** — what to wear, umbrella advice, UV protection, activity & health tips

**Forecast & charts**
- Next-24-hours strip + **hourly temperature graph**
- **15-day forecast** + **daily high/low graph**

**Map**
- Interactive map, **coloured temperature dots** (spot heatwaves by colour), click-anywhere weather
- **Rain radar overlay** toggle (RainViewer), marker for the viewed city

**Population**
- **Live ticking world population counter**, ranked & searchable countries, per-city lookup

**Personalisation & UX**
- **°C / °F**, **Light / Vivid theme**, favourites + recent searches (remove), all saved locally
- **Voice search**, **GPS location**, **auto-refresh** every 5 min, **offline cache**, **retry** on errors
- **Animated weather effects** (rain, snow, drifting clouds, lightning, night stars)
- **Installable PWA** with offline app shell (manifest + service worker)
- Glassmorphism UI, dynamic weather backgrounds, smooth animations, responsive, accessible

## Tech Stack
- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, JavaScript · Chart.js + Leaflet (bundled, no CDN)
- **Data (all free, no key):** Open-Meteo (weather, air quality, geocoding), RainViewer (radar),
  OpenStreetMap (map), bundled country dataset for population

> Uses **Open-Meteo** (no API key / signup) instead of OpenWeatherMap/WeatherAPI which require keys.

## Project Structure
```
weather-app/
├── main.py               # FastAPI app + endpoints + PWA routes
├── weather.py            # forecast, hourly, AQI, UV, sun/moon, dew point, alerts, heatmap
├── population.py         # population API (local dataset + live-counter params)
├── population_data.py    # bundled country populations + world-counter base/growth
├── manifest.webmanifest  # PWA manifest
├── sw.js                 # service worker (offline shell)
├── templates/index.html
├── static/
│   ├── style.css · app.js
│   ├── icons/            # PWA icons (192, 512)
│   └── vendor/           # Chart.js + Leaflet
├── requirements.txt
└── README.md
```

## Setup & Run
```bash
python -m venv venv
venv\Scripts\activate              # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python -m uvicorn main:app --reload
```
Open **http://127.0.0.1:8000/** (hard-refresh with Ctrl+Shift+R the first time).
API docs: **http://127.0.0.1:8000/docs**. To install as an app, use the browser's "Install" option.

> Needs internet for live weather, radar and map tiles — but **no API keys**.

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` · `/manifest.webmanifest` · `/sw.js` | App shell + PWA |
| GET | `/api/weather?city=` / `/api/weather/coords?lat=&lon=` | Full weather payload |
| GET | `/api/heatmap` | City temperatures for the map |
| GET | `/api/population/countries` | World total + live-counter params + countries |
| GET | `/api/city?name=` | Geocoded city info incl. population |

## Notes
- Country populations are a bundled 2024 snapshot; the world counter ticks from a 2024 base using an annual growth rate.
- Skipped by design: account login / cloud sync, and paid map layers (satellite/temperature/wind).
