# 🧪 QA Test Suite — Weather App (Skyline)

Automated tests using **pytest** (FastAPI TestClient) for API/functional testing and
**Playwright (Python)** for end-to-end UI testing.

The live Open-Meteo API is **mocked**, so the tests are deterministic and run fully
offline — they don't depend on the network or on the day's actual weather.

## What's covered

**API / functional** — `tests/test_api.py`
- Home page, PWA manifest and service worker are served correctly
- `/api/weather` returns a full payload (temperature, humidity, pressure, UV, forecast, AQI)
- Empty city → 400, unknown city → 404, upstream failure → 502
- `/api/weather/coords` and `/api/heatmap` work
- `/api/population/countries` returns the world total, live-counter data and a
  correctly sorted country list (local data)
- `/api/city` returns population; empty → 400, unknown → 404

**End-to-end UI (Playwright)** — `tests/test_e2e.py`
- Page loads with all tabs (Today / 15-Day / Map / Population)
- Current weather renders (city, temperature, condition)
- City search updates the displayed city
- °C ↔ °F unit toggle works
- Light-mode theme toggle works
- Population tab shows the live counter and the country list

## Setup

```bash
# from the project root
pip install -r requirements-test.txt
playwright install chromium        # one-time: download the browser
```

## Run the tests

```bash
pytest
```

The end-to-end tests automatically start a mock-data server (port 8123) with the
Open-Meteo calls stubbed, so nothing external is required. The API tests run fully
in-process via FastAPI's TestClient.

## Structure
```
tests/
├── conftest.py          # fixtures: TestClient, mock server, geolocation
├── _fixtures.py         # shared fake weather data
├── serve_mock.py        # FastAPI server with Open-Meteo mocked (for E2E)
├── test_api.py          # API / functional tests (TestClient)
└── test_e2e.py          # Playwright end-to-end UI tests
pytest.ini
requirements-test.txt
```

## Sample run
```
tests/test_api.py::test_weather_by_city_returns_full_payload PASSED
tests/test_api.py::test_population_countries_local_data PASSED
tests/test_e2e.py::test_current_weather_renders[chromium] PASSED
tests/test_e2e.py::test_population_tab_shows_counter_and_countries[chromium] PASSED
...
============================== 19 passed ==============================
```
