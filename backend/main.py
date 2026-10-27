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

WEATHER_CACHE_SECONDS = 600      # 10 minutes
ELEVATION_CACHE_SECONDS = 86400  # 24 hours
DEFAULT_COOLDOWN_SECONDS = 300   # 5 minutes default cooldown on HTTP 429

# Global tracking of provider rate limits
rate_limit_until = 0.0

@app.get("/api/weather")
def weather(
    lat: float = 26.14,
    lon: float = 91.74
):
    global rate_limit_until

    # Normalize cache key
    cache_key = f"{round(lat, 2)},{round(lon, 2)}"
    current_time = time.time()

    with weather_lock:
        # 1. Try serving from cache first
        if cache_key in weather_cache:
            cached_entry = weather_cache[cache_key]
            # If fresh, return it
            if current_time - cached_entry["timestamp"] < WEATHER_CACHE_SECONDS:
                result = cached_entry["data"].copy()
                result["cached"] = True
                result["live"] = False
                result["available"] = True
                return result

        # 2. Check if we are currently rate-limited
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

            return {
                "latitude": lat,
                "longitude": lon,
                "available": False,
                "live": False,
                "source": "Rate limited (HTTP 429)",
                "message": "Provider rate limit active. Cached data unavailable."
            }

        # 3. Request fresh data (Only if not rate-limited and cache expired/missing)
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,visibility,wind_speed_10m,wind_gusts_10m"
            "&hourly=precipitation&past_hours=24&forecast_hours=1&timezone=auto"
        )

        try:
            response = http_session.get(url, timeout=10)

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                cooldown = int(retry_after) if retry_after and retry_after.isdigit() else DEFAULT_COOLDOWN_SECONDS
                rate_limit_until = current_time + cooldown
                raise requests.exceptions.HTTPError("429 Too Many Requests")

            response.raise_for_status()
            data = response.json()

            current = data["current"]
            hourly = data.get("hourly", {})
            rainfall_values = hourly.get("precipitation", [])
            rainfall_24h = round(sum(v for v in rainfall_values if v is not None), 2)

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

            weather_cache[cache_key] = {"timestamp": current_time, "data": result}
            return result

        except Exception as error:
            # If we fail, try serving stale cache even if older than normal TTL
            if cache_key in weather_cache:
                cached_entry = weather_cache[cache_key]
                result = cached_entry["data"].copy()
                result["live"] = False
                result["cached"] = True
                result["stale"] = True
                result["available"] = True
                result["source"] = "Open-Meteo (error fallback)"
                return result

            return {
                "latitude": lat,
                "longitude": lon,
                "available": False,
                "live": False,
                "source": "Weather API unavailable",
                "message": str(error)
            }
