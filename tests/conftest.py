"""Fixtures for the Weather App test suite."""
import sys
import time
import socket
import subprocess
import pathlib

import pytest
from fastapi.testclient import TestClient

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import main          # noqa: E402
import weather       # noqa: E402
import _fixtures     # noqa: E402

MOCK_PORT = 8123
MOCK_URL = f"http://127.0.0.1:{MOCK_PORT}"


def _port_open(host, port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


# ---- in-process API tests: patch the Open-Meteo layer with fakes ----
@pytest.fixture(autouse=True)
def mock_upstream(monkeypatch):
    monkeypatch.setattr(weather, "get_weather_by_city", lambda c: _fixtures.make_weather(c))
    monkeypatch.setattr(weather, "get_weather_by_coords", lambda lat, lon: _fixtures.make_weather("Lucknow", lat, lon))
    monkeypatch.setattr(weather, "get_heatmap", lambda: list(_fixtures.FAKE_HEATMAP))
    monkeypatch.setattr(weather, "geocode_city", lambda name: dict(_fixtures.FAKE_GEO, name=name))


@pytest.fixture
def client():
    return TestClient(main.app)


# ---- end-to-end tests: run a mock-data server for the browser ----
@pytest.fixture(scope="session")
def base_url():
    proc = None
    if not _port_open("127.0.0.1", MOCK_PORT):
        proc = subprocess.Popen([sys.executable, str(HERE / "serve_mock.py"), str(MOCK_PORT)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(40):
            if _port_open("127.0.0.1", MOCK_PORT):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Mock server did not start in time.")
    yield MOCK_URL
    if proc:
        proc.terminate()
        proc.wait(timeout=10)


# grant a fake geolocation so the app loads instantly in E2E tests
@pytest.fixture
def browser_context_args(browser_context_args):
    return {**browser_context_args,
            "geolocation": {"latitude": 26.85, "longitude": 80.95},
            "permissions": ["geolocation"]}
