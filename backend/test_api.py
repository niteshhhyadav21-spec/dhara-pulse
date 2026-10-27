import pytest
from fastapi.testclient import TestClient
from main import app, weather_cache, elevation_cache, rate_limit_until

client = TestClient(app)

def test_weather_success_caching(monkeypatch):
    weather_cache.clear()

    class MockSuccess:
        status_code = 200
        def json(self):
            return {
                "current": {
                    "temperature_2m": 20.0, "relative_humidity_2m": 50, "precipitation": 0.0,
                    "rain": 0.0, "weather_code": 0, "visibility": 10000, "wind_speed_10m": 5.0, "wind_gusts_10m": 10.0
                },
                "hourly": {"precipitation": [0.0]}
            }
        def raise_for_status(self): pass

    monkeypatch.setattr("main.http_session.get", lambda url, timeout: MockSuccess())

    # First call (Fresh)
    res1 = client.get("/api/weather?lat=26.1&lon=91.7")
    assert res1.status_code == 200
    assert res1.json()["available"] is True
    assert res1.json()["live"] is True

    # Second call (Cached)
    res2 = client.get("/api/weather?lat=26.1&lon=91.7")
    assert res2.status_code == 200
    assert res2.json()["cached"] is True
    assert res2.json()["live"] is False

def test_weather_429_cooldown(monkeypatch):
    weather_cache.clear()
    monkeypatch.setattr("main.rate_limit_until", 0.0)

    call_count = {"n": 0}
    class Mock429:
        status_code = 429
        headers = {"Retry-After": "60"}
        def raise_for_status(self): pass

    def fake_get(url, timeout):
        call_count["n"] += 1
        return Mock429()

    monkeypatch.setattr("main.http_session.get", fake_get)

    # Call 1: Triggers 429
    res1 = client.get("/api/weather?lat=26.1&lon=91.7")
    assert res1.status_code == 200
    assert res1.json()["available"] is False
    assert call_count["n"] == 1

    # Call 2: Should not call upstream due to cooldown
    res2 = client.get("/api/weather?lat=26.1&lon=91.7")
    assert call_count["n"] == 1
    assert res2.json()["available"] is False

def test_weather_malformed_response(monkeypatch):
    weather_cache.clear()
    monkeypatch.setattr("main.rate_limit_until", 0.0)

    class MockMalformed:
        status_code = 200
        def json(self):
            return {"bad_key": True}
        def raise_for_status(self): pass

    monkeypatch.setattr("main.http_session.get", lambda url, timeout: MockMalformed())

    res = client.get("/api/weather?lat=26.1&lon=91.7")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False
    assert "Weather API unavailable" in data["source"]
