import time
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

    res1 = client.get("/api/weather?lat=26.1&lon=91.7")
    assert res1.status_code == 200
    assert res1.json()["available"] is True
    assert res1.json()["live"] is True
    assert res1.json()["source"] == "Open-Meteo"

def test_weather_fallback_provider(monkeypatch):
    weather_cache.clear()
    monkeypatch.setattr("main.rate_limit_until", time.time() + 300) # Force primary rate limited

    class MockWttr:
        status_code = 200
        def json(self):
            return {
                "current_condition": [{
                    "temp_C": "28", "humidity": "65", "precipMM": "1.5",
                    "visibility": "10", "windspeedKmph": "15"
                }]
            }
        def raise_for_status(self): pass

    monkeypatch.setattr("main.http_session.get", lambda url, timeout: MockWttr())

    res = client.get("/api/weather?lat=26.1&lon=91.7")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is True
    assert data["source"] == "wttr.in (fallback)"
    assert data["temperature"] == 28.0

def test_weather_all_providers_fail(monkeypatch):
    weather_cache.clear()
    monkeypatch.setattr("main.rate_limit_until", time.time() + 300)

    class MockFail:
        status_code = 500
        def raise_for_status(self):
            raise Exception("Server Error")

    monkeypatch.setattr("main.http_session.get", lambda url, timeout: MockFail())

    res = client.get("/api/weather?lat=26.1&lon=91.7")
    assert res.status_code == 200
    data = res.json()
    assert data["available"] is False
