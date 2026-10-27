import pytest
from fastapi.testclient import TestClient
from main import app, weather_cache, elevation_cache, rate_limit_until

client = TestClient(app)

def test_weather_caching_and_availability(monkeypatch):
    weather_cache.clear()
    elevation_cache.clear()

    # Mock requests.Session.get to return a successful Open-Meteo response
    class MockResponse:
        status_code = 200
        headers = {}
        def json(self):
            return {
                "current": {
                    "temperature_2m": 25.5,
                    "relative_humidity_2m": 80,
                    "precipitation": 1.2,
                    "rain": 1.2,
                    "weather_code": 61,
                    "visibility": 8000,
                    "wind_speed_10m": 12.0,
                    "wind_gusts_10m": 22.0
                },
                "hourly": {
                    "precipitation": [0.0, 5.0, 10.0]
                }
            }
        def raise_for_status(self):
            pass

    monkeypatch.setattr("main.http_session.get", lambda url, timeout: MockResponse())

    # First request (Live)
    response1 = client.get("/api/weather?lat=26.14&lon=91.74")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["available"] is True
    assert data1["live"] is True
    assert data1["cached"] is False
    assert data1["temperature"] == 25.5
    assert data1["rainfall_24h"] == 15.0

    # Second request (Cached)
    response2 = client.get("/api/weather?lat=26.14&lon=91.74")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["available"] is True
    assert data2["live"] is False
    assert data2["cached"] is True

def test_weather_rate_limit_429(monkeypatch):
    weather_cache.clear()

    class Mock429Response:
        status_code = 429
        headers = {"Retry-After": "30"}
        def json(self):
            return {}
        def raise_for_status(self):
            pass

    monkeypatch.setattr("main.http_session.get", lambda url, timeout: Mock429Response())

    # Request encountering 429 without cache should return unavailable with rate limit message
    response = client.get("/api/weather?lat=27.00&lon=92.00")
    assert response.status_code == 200
    data = response.json()
    assert data["available"] is False
    assert "Rate limited" in data["source"]

def test_terrain_caching():
    elevation_cache.clear()

    res1 = client.get("/api/terrain?lat=26.0&lon=91.0")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["cached"] is False

    res2 = client.get("/api/terrain?lat=26.0&lon=91.0")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["cached"] is True
    assert data1["slope"] == data2["slope"]

def test_weather_rate_limit_cooldown_prevents_repeated_calls(monkeypatch):
    """During an HTTP 429 cooldown, no upstream request should be made."""
    weather_cache.clear()
    monkeypatch.setattr("main.rate_limit_until", 0.0)

    call_count = {"count": 0}

    class Mock429Response:
        status_code = 429
        headers = {"Retry-After": "60"}
        def json(self):
            return {}
        def raise_for_status(self):
            pass

    def fake_get(url, timeout):
        call_count["count"] += 1
        return Mock429Response()

    monkeypatch.setattr("main.http_session.get", fake_get)

    # First request triggers the 429 and starts the cooldown
    response1 = client.get("/api/weather?lat=27.00&lon=92.00")
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["available"] is False
    assert call_count["count"] == 1

    # Subsequent requests during the cooldown must NOT call upstream
    response2 = client.get("/api/weather?lat=27.00&lon=92.00")
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["available"] is False
    assert call_count["count"] == 1  # no additional upstream calls
