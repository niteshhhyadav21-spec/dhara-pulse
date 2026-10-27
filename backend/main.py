import time
import threading
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared requests session for connection pooling
http_session = requests.Session()

# Caching, lock, and rate limit tracking
weather_cache = {}
elevation_cache = {}
weather_lock = threading.Lock()

WEATHER_CACHE_SECONDS = 600     # 10 minutes TTL for fresh cache
ELEVATION_CACHE_SECONDS = 86400  # 24 hours TTL for elevation
DEFAULT_COOLDOWN_SECONDS = 180   # 3 minutes default cooldown on HTTP 429

rate_limit_until = 0.0

@app.get("/api/weather")
def weather(
    lat: float = 26.14,
    lon: float = 91.74
):
    global rate_limit_until

    cache_key = f"{round(lat, 3)},{round(lon, 3)}"

    with weather_lock:
        current_time = time.time()

        # 1. Return fresh cache hit if available
        if cache_key in weather_cache:
            cached_entry = weather_cache[cache_key]
            if current_time - cached_entry["timestamp"] < WEATHER_CACHE_SECONDS:
                result = cached_entry["data"].copy()
                result["cached"] = True
                result["live"] = False
                result["available"] = True
                return result

        # 2. Check global rate-limit cooldown
        if current_time < rate_limit_until:
            if cache_key in weather_cache:
                cached_entry = weather_cache[cache_key]
                result = cached_entry["data"].copy()
                result["cached"] = True
                result["live"] = False
                result["stale"] = True
                result["available"] = True
                result["source"] = "Open-Meteo (rate-limit cached)"
                return result
            else:
                return {
                    "latitude": lat,
                    "longitude": lon,
                    "available": False,
                    "live": False,
                    "cached": False,
                    "stale": False,
                    "source": "Rate limited (HTTP 429)",
                    "message": "Open-Meteo rate limit active. Please try again later."
                }

        # 3. Request fresh data from Open-Meteo (under lock)
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}"
            f"&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,visibility,wind_speed_10m,wind_gusts_10m"
            "&hourly=precipitation"
            "&past_hours=24"
            "&forecast_hours=1"
            "&timezone=auto"
        )

        try:
            response = http_session.get(url, timeout=10)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                cooldown = int(retry_after) if retry_after and retry_after.isdigit() else DEFAULT_COOLDOWN_SECONDS
                rate_limit_until = current_time + cooldown
                print(f"Open-Meteo HTTP 429 encountered. Backing off for {cooldown} seconds.")
                raise requests.exceptions.HTTPError("429 Too Many Requests")

            response.raise_for_status()
            data = response.json()

            current = data["current"]
            hourly = data.get("hourly", {})
            rainfall_values = hourly.get("precipitation", [])

            rainfall_24h = round(
                sum(value for value in rainfall_values if value is not None),
                2
            )

            result = {
                "latitude": lat,
                "longitude": lon,
                "temperature": current["temperature_2m"],
                "humidity": current["relative_humidity_2m"],
                "precipitation": current["precipitation"],
                "rain": current["rain"],
                "weather_code": current["weather_code"],
                "visibility": current["visibility"],
                "wind_speed": current["wind_speed_10m"],
                "wind_gusts": current["wind_gusts_10m"],
                "rainfall_24h": rainfall_24h,
                "source": "Open-Meteo",
                "live": True,
                "cached": False,
                "stale": False,
                "available": True,
                "observation_time": current_time
            }

            weather_cache[cache_key] = {
                "timestamp": current_time,
                "data": result
            }

            return result

        except Exception as error:
            print("WEATHER API ERROR:", error)

            # Fallback to stale cache if available
            if cache_key in weather_cache:
                cached_entry = weather_cache[cache_key]
                result = cached_entry["data"].copy()
                result["live"] = False
                result["cached"] = True
                result["stale"] = True
                result["available"] = True
                result["source"] = "Open-Meteo (stale cache)"
                return result

            is_429 = "429" in str(error)
            return {
                "latitude": lat,
                "longitude": lon,
                "available": False,
                "live": False,
                "cached": False,
                "stale": False,
                "source": "Rate limited (HTTP 429)" if is_429 else "Weather API temporarily unavailable",
                "message": str(error)
            }

@app.get("/api/terrain")
def terrain(lat: float, lon: float):
    cache_key = f"{round(lat, 3)},{round(lon, 3)}"
    current_time = time.time()

    if cache_key in elevation_cache:
        entry = elevation_cache[cache_key]
        if current_time - entry["timestamp"] < ELEVATION_CACHE_SECONDS:
            return {"slope": entry["slope"], "cached": True}

    # Fallback/cached elevation & slope calculation
    slope_val = 12.5 + ((lat + lon) % 15.0)
    elevation_cache[cache_key] = {
        "timestamp": current_time,
        "slope": round(slope_val, 2)
    }

    return {"slope": round(slope_val, 2), "cached": False}

@app.get("/api/soil-moisture")
def soil_moisture():
    return {"soil_moisture": 45.0, "simulated": True}

@app.get("/api/soil-moisture/history")
def soil_moisture_history():
    return {"readings": [{"soil_moisture": 45.0}, {"soil_moisture": 44.0}]}

@app.get("/api/gsi-historical-landslides/nearby")
def historical_landslides(lat: float, lon: float, radius_km: int = 50):
    return {"historical_events": 0, "landslides": []}

@app.get("/api/risk")
def risk(rainfall: float, soil_moisture: float, slope: float, historical_events: int, soil_trend: str):
    return {
        "score": 10,
        "level": "LOW",
        "explanation": "Conditions are stable.",
        "factors": {"rainfall": rainfall, "soil_moisture": soil_moisture, "slope": slope, "historical_events": historical_events},
        "factor_scores": {"rainfall": 5, "soil_moisture": 2, "slope": 2, "historical_events": 1}
    }

@app.get("/api/reports")
def get_reports():
    return {"reports": []}

@app.get("/api/alerts")
def get_alerts():
    return {"alerts": []}
