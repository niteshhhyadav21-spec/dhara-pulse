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
            if current_time - cached_entry["timestamp"] < WEATHER_CACHE_SECONDS:
                result = cached_entry["data"].copy()
                result["cached"] = True
                result["live"] = False
                result["available"] = True
                return result

        # 2. Check if Open-Meteo is currently rate-limited
        is_rate_limited = current_time < rate_limit_until

        # 3. Try Open-Meteo if not rate limited
        primary_success = False
        data = None
        error_message = None

        if not is_rate_limited:
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
                    is_rate_limited = True
                    raise requests.exceptions.HTTPError("429 Too Many Requests")

                response.raise_for_status()
                data = response.json()
                primary_success = True
            except Exception as err:
                error_message = str(err)

        # 4. Fallback Provider: wttr.in (Public, zero-config, free tier suitable for light/fallback usage)
        if not primary_success:
            fallback_url = f"https://wttr.in/{lat},{lon}?format=j1"
            try:
                # wttr.in can be slow; keep short timeout
                fb_response = http_session.get(fallback_url, timeout=5)
                fb_response.raise_for_status()
                fb_data = fb_response.json()
                current_cond = fb_data["current_condition"][0]

                # Normalize wttr.in to match Open-Meteo response structure expected by frontend
                temp_c = float(current_cond["temp_C"])
                humidity = int(current_cond["humidity"])
                precip_mm = float(current_cond.get("precipMM", 0.0))
                visibility_m = float(current_cond.get("visibility", 10)) * 1000.0
                wind_kmh = float(current_cond.get("windspeedKmph", 0.0))

                result = {
                    "latitude": lat,
                    "longitude": lon,
                    "temperature": temp_c,
                    "humidity": humidity,
                    "precipitation": precip_mm,
                    "rain": precip_mm,
                    "weather_code": 0,
                    "visibility": visibility_m,
                    "wind_speed": wind_kmh,
                    "wind_gusts": wind_kmh * 1.2,
                    "rainfall_24h": precip_mm * 3, # estimated daily accumulation from current
                    "source": "wttr.in (fallback)",
                    "live": True,
                    "cached": False,
                    "stale": False,
                    "available": True,
                    "observation_time": current_time
                }

                weather_cache[cache_key] = {"timestamp": current_time, "data": result}
                return result

            except Exception as fb_err:
                # Fallback also failed; try stale cache
                if cache_key in weather_cache:
                    cached_entry = weather_cache[cache_key]
                    result = cached_entry["data"].copy()
                    result["live"] = False
                    result["cached"] = True
                    result["stale"] = True
                    result["available"] = True
                    result["source"] = f"Stale cache (Primary & Fallback error: {error_message or fb_err})"
                    return result

                return {
                    "latitude": lat,
                    "longitude": lon,
                    "available": False,
                    "live": False,
                    "source": "Rate limited / Weather API unavailable",
                    "message": error_message or str(fb_err)
                }

        # Process primary Open-Meteo success
        try:
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

        except Exception as parse_err:
            if cache_key in weather_cache:
                cached_entry = weather_cache[cache_key]
                result = cached_entry["data"].copy()
                result["live"] = False
                result["cached"] = True
                result["stale"] = True
                result["available"] = True
                result["source"] = "Open-Meteo (parse error fallback)"
                return result

            return {
                "latitude": lat,
                "longitude": lon,
                "available": False,
                "live": False,
                "source": "Weather API parse error",
                "message": str(parse_err)
            }

@app.get("/api/terrain")
def terrain(lat: float, lon: float):
    cache_key = f"{round(lat, 3)},{round(lon, 3)}"
    current_time = time.time()

    if cache_key in elevation_cache:
        entry = elevation_cache[cache_key]
        if current_time - entry["timestamp"] < ELEVATION_CACHE_SECONDS:
            return {"slope": entry["slope"], "cached": True}

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
