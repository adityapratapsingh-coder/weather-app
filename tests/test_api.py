"""
API / functional tests using FastAPI's TestClient.
The Open-Meteo layer is mocked (see conftest), so these run offline and are deterministic.
"""
import weather


def test_home_page_loads(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Skyline" in r.text


def test_manifest_served(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert "application/manifest+json" in r.headers["content-type"]
    assert "Skyline" in r.text


def test_service_worker_served(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]


def test_weather_by_city_returns_full_payload(client):
    r = client.get("/api/weather", params={"city": "Lucknow"})
    assert r.status_code == 200
    data = r.json()
    assert data["location"]["name"] == "Lucknow"
    for field in ("temperature", "feels_like", "humidity", "wind_speed", "pressure", "uv_index"):
        assert field in data["current"]
    assert len(data["forecast"]) >= 7
    assert data["aqi"]["value"] == 78


def test_weather_empty_city_returns_400(client):
    r = client.get("/api/weather", params={"city": "  "})
    assert r.status_code == 400


def test_weather_unknown_city_returns_404(client, monkeypatch):
    monkeypatch.setattr(weather, "get_weather_by_city", lambda c: None)
    r = client.get("/api/weather", params={"city": "zzzzzz"})
    assert r.status_code == 404


def test_weather_service_failure_returns_502(client, monkeypatch):
    def boom(_):
        raise RuntimeError("network down")
    monkeypatch.setattr(weather, "get_weather_by_city", boom)
    r = client.get("/api/weather", params={"city": "Lucknow"})
    assert r.status_code == 502


def test_weather_by_coords(client):
    r = client.get("/api/weather/coords", params={"lat": 26.85, "lon": 80.95})
    assert r.status_code == 200
    assert "temperature" in r.json()["current"]


def test_heatmap_returns_cities(client):
    r = client.get("/api/heatmap")
    assert r.status_code == 200
    cities = r.json()["cities"]
    assert len(cities) >= 3
    assert all("temp" in c and "lat" in c for c in cities)


def test_population_countries_local_data(client):
    r = client.get("/api/population/countries")
    assert r.status_code == 200
    data = r.json()
    assert data["world_total"] > 8_000_000_000
    assert "world_live" in data and data["world_live"]["per_second"] > 0
    countries = data["countries"]
    assert len(countries) > 50
    # list must be sorted by population, descending
    pops = [c["population"] for c in countries]
    assert pops == sorted(pops, reverse=True)
    assert countries[0]["name"] in ("India", "China")


def test_city_lookup_returns_population(client):
    r = client.get("/api/city", params={"name": "Lucknow"})
    assert r.status_code == 200
    assert r.json()["population"] == 2902920


def test_city_empty_returns_400(client):
    r = client.get("/api/city", params={"name": ""})
    assert r.status_code == 400


def test_city_unknown_returns_404(client, monkeypatch):
    monkeypatch.setattr(weather, "geocode_city", lambda name: None)
    r = client.get("/api/city", params={"name": "zzzzzz"})
    assert r.status_code == 404
