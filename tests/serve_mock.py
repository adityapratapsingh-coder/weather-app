"""
Launches the FastAPI app with the Open-Meteo calls replaced by fake data, so the
Playwright end-to-end tests render deterministically without any network access.
Used automatically by the test suite; you can also run it manually:  python tests/serve_mock.py 8123
"""
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import weather          # noqa: E402
import main             # noqa: E402
import _fixtures        # noqa: E402
import uvicorn          # noqa: E402

weather.get_weather_by_city = lambda city: _fixtures.make_weather(city)
weather.get_weather_by_coords = lambda lat, lon: _fixtures.make_weather("Lucknow", lat, lon)
weather.get_heatmap = lambda: list(_fixtures.FAKE_HEATMAP)
weather.geocode_city = lambda name: dict(_fixtures.FAKE_GEO, name=name)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="error")
