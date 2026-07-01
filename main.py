"""
Weather + Climate dashboard — FastAPI backend.

Endpoints:
  GET /                              -> the web page
  GET /api/weather?city=London       -> weather (current, hourly, 15-day, AQI) by city
  GET /api/weather/coords?lat=&lon=   -> same, by coordinates (geolocation / map clicks)
  GET /api/heatmap                    -> current temps for major cities (map overlay)
  GET /api/population/countries       -> world total + per-country population
  GET /api/city?name=London           -> geocoded city info incl. population

Run:  uvicorn main:app --reload
"""
import pathlib

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

import weather
import population

BASE_DIR = pathlib.Path(__file__).parent

app = FastAPI(title="Weather + Climate Dashboard", version="2.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

SERVICE_ERROR = {"error": "Could not reach the weather service. Check your internet connection."}


@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/manifest.webmanifest")
def manifest():
    return Response((BASE_DIR / "manifest.webmanifest").read_text(encoding="utf-8"),
                    media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return Response((BASE_DIR / "sw.js").read_text(encoding="utf-8"),
                    media_type="application/javascript")


@app.get("/api/weather")
def api_weather_by_city(city: str):
    city = (city or "").strip()
    if not city:
        return JSONResponse({"error": "Enter a city name to search."}, status_code=400)
    try:
        data = weather.get_weather_by_city(city)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"error": SERVICE_ERROR["error"], "debug": f"{type(e).__name__}: {e}"},
            status_code=502,
        )
    if data is None:
        return JSONResponse({"error": f"No match for \u201c{city}\u201d. Try a different spelling."}, status_code=404)
    return data


@app.get("/api/weather/coords")
def api_weather_by_coords(lat: float, lon: float):
    try:
        return weather.get_weather_by_coords(lat, lon)
    except Exception:
        return JSONResponse(SERVICE_ERROR, status_code=502)


@app.get("/api/heatmap")
def api_heatmap():
    try:
        return {"cities": weather.get_heatmap()}
    except Exception:
        return JSONResponse(SERVICE_ERROR, status_code=502)


@app.get("/api/population/countries")
def api_population_countries():
    try:
        return population.get_countries()
    except Exception:
        return JSONResponse({"error": "Could not reach the population service."}, status_code=502)


@app.get("/api/city")
def api_city(name: str):
    name = (name or "").strip()
    if not name:
        return JSONResponse({"error": "Enter a city name."}, status_code=400)
    try:
        loc = weather.geocode_city(name)
    except Exception:
        return JSONResponse(SERVICE_ERROR, status_code=502)
    if loc is None:
        return JSONResponse({"error": f"No match for \u201c{name}\u201d."}, status_code=404)
    return loc
