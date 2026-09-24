from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import time
from sqlalchemy import create_engine, text

import csv
import re
from pathlib import Path



weather_cache = {}
WEATHER_CACHE_SECONDS = 300

terrain_cache = {}
TERRAIN_CACHE_SECONDS = 300
# ================= DATABASE =================

DATABASE_URL = "sqlite:///./dhara_pulse.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

with engine.begin() as connection:

    # Historical landslide database
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS historical_landslides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            year INTEGER,
            state TEXT,
            district TEXT,
            source TEXT
        )
    """))

        # GSI Historical Landslide Database
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS gsi_historical_landslides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT,
            slide_number TEXT,
            state TEXT,
            district TEXT,
            slide_name TEXT,
            nh_sh_location TEXT,
            latitude REAL,
            longitude REAL,
            material TEXT,
            movement_type TEXT,
            history TEXT,
            year INTEGER
        )
    """))

    # Load GSI CSV data if the table is empty
    gsi_count = connection.execute(
        text("SELECT COUNT(*) FROM gsi_historical_landslides")
    ).scalar()

    if gsi_count == 0:
        gsi_file = Path(__file__).resolve().parent / "gsi_clean_final.csv"

        if gsi_file.exists():
            gsi_records = []

            with open(gsi_file, "r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)

                for row in reader:
                    try:
                        latitude = float(row["latitude"])
                        longitude = float(row["longitude"])
                    except (ValueError, TypeError, KeyError):
                        continue

                    slide_number = (row.get("slide_number") or "").strip()

                    year = None
                    year_match = re.search(r"/(20\d{2})/", slide_number)

                    if year_match:
                        year = int(year_match.group(1))

                    gsi_records.append({
                        "serial_number": (row.get("serial_number") or "").strip(),
                        "slide_number": slide_number,
                        "state": (row.get("state") or "").strip(),
                        "district": (row.get("district") or "").strip(),
                        "slide_name": (row.get("slide_name") or "").strip(),
                        "nh_sh_location": (row.get("nh_sh_location") or "").strip(),
                        "latitude": latitude,
                        "longitude": longitude,
                        "material": (row.get("material") or "").strip(),
                        "movement_type": (row.get("movement_type") or "").strip(),
                        "history": (row.get("history") or "").strip(),
                        "year": year
                    })

            if gsi_records:
                connection.execute(
                    text("""
                        INSERT INTO gsi_historical_landslides (
                            serial_number,
                            slide_number,
                            state,
                            district,
                            slide_name,
                            nh_sh_location,
                            latitude,
                            longitude,
                            material,
                            movement_type,
                            history,
                            year
                        )
                        VALUES (
                            :serial_number,
                            :slide_number,
                            :state,
                            :district,
                            :slide_name,
                            :nh_sh_location,
                            :latitude,
                            :longitude,
                            :material,
                            :movement_type,
                            :history,
                            :year
                        )
                    """),
                    gsi_records
                )

                print(f"GSI records loaded: {len(gsi_records)}")
            else:
                print(f"GSI CSV not found: {gsi_file}")

    # Citizen hazard reports
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS hazard_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hazard_type TEXT NOT NULL,
            description TEXT,
            latitude REAL,
            longitude REAL,
            status TEXT DEFAULT 'NEW'
        )
    """))

    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS risk_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            risk_level TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))

    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS soil_moisture_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            soil_moisture REAL NOT NULL,
            latitude REAL,
            longitude REAL,
            source TEXT DEFAULT 'IoT Sensor Network',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))



# ================= APP =================

app = FastAPI(title="Dhara Pulse API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= ADD HISTORICAL LANDSLIDE =================

@app.post("/api/historical-landslides")
def add_historical_landslide(data: dict):

    with engine.begin() as connection:

        connection.execute(
            text("""
                INSERT INTO historical_landslides
                (
                    latitude,
                    longitude,
                    year,
                    state,
                    district,
                    source
                )
                VALUES
                (
                    :latitude,
                    :longitude,
                    :year,
                    :state,
                    :district,
                    :source
                )
            """),
            {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "year": data.get("year"),
                "state": data.get("state"),
                "district": data.get("district"),
                "source": data.get("source", "Dhara Pulse")
            }
        )

    return {
        "success": True,
        "message": "Historical landslide added successfully"
    }

# ================= GET HISTORICAL LANDSLIDES =================

@app.get("/api/gsi-historical-landslides")
def get_gsi_historical_landslides():

    with engine.connect() as connection:

        rows = connection.execute(
            text("""
                SELECT
                    id,
                    serial_number,
                    slide_number,
                    state,
                    district,
                    slide_name,
                    nh_sh_location,
                    latitude,
                    longitude,
                    material,
                    movement_type,
                    history,
                    year
                FROM gsi_historical_landslides
                ORDER BY year DESC
            """)
        ).mappings().all()

    return {
        "success": True,
        "count": len(rows),
        "source": "GSI Landslide Inventory",
        "landslides": [dict(row) for row in rows]
    }

# ================= DELETE TEST LANDSLIDES =================

@app.delete("/api/historical-landslides/test-data")
def delete_test_landslides():

    with engine.begin() as connection:

        result = connection.execute(
            text("""
                DELETE FROM historical_landslides
                WHERE source = 'TEST DATA'
            """)
        )

    return {
        "success": True,
        "deleted": result.rowcount,
        "message": "Test historical landslides deleted"
    }

# ================= NEARBY HISTORICAL LANDSLIDES =================

@app.get("/api/gsi-historical-landslides/nearby")
def get_nearby_gsi_landslides(
    lat: float = 26.14,
    lon: float = 91.74,
    radius_km: float = 50
):

    with engine.connect() as connection:

        rows = connection.execute(
            text("""
                SELECT
                    id,
                    serial_number,
                    slide_number,
                    state,
                    district,
                    slide_name,
                    nh_sh_location,
                    latitude,
                    longitude,
                    material,
                    movement_type,
                    history,
                    year
                FROM gsi_historical_landslides
            """)
        ).mappings().all()

    import math

    nearby = []

    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    for row in rows:

        lat2 = math.radians(row["latitude"])
        lon2 = math.radians(row["longitude"])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            +
            math.cos(lat1)
            * math.cos(lat2)
            * math.sin(dlon / 2) ** 2
        )

        distance_km = (
            6371
            * 2
            * math.atan2(
                math.sqrt(a),
                math.sqrt(1 - a)
            )
        )

        if distance_km <= radius_km:

            nearby.append({
                "id": row["id"],
                "serial_number": row["serial_number"],
                "slide_number": row["slide_number"],
                "state": row["state"],
                "district": row["district"],
                "slide_name": row["slide_name"],
                "nh_sh_location": row["nh_sh_location"],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "material": row["material"],
                "movement_type": row["movement_type"],
                "history": row["history"],
                "year": row["year"],
                "distance_km": round(distance_km, 2)
            })

    return {
        "success": True,
        "latitude": lat,
        "longitude": lon,
        "radius_km": radius_km,
        "historical_events": len(nearby),
        "source": "GSI Landslide Inventory",
        "landslides": nearby
    }

# ================= HOME =================

@app.get("/")
def home():
    return {
        "status": "Dhara Pulse backend is running"
    }
# ================= ALERTS =================


@app.post("/api/alerts")
def create_alert(
    risk_level: str,
    risk_score: int,
    latitude: float,
    longitude: float,
    message: str = ""
):
    with engine.begin() as connection:
        result = connection.execute(
            text("""
                INSERT INTO risk_alerts
                (risk_level, risk_score, latitude, longitude, message)
                VALUES
                (:risk_level, :risk_score, :latitude, :longitude, :message)
            """),
            {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "latitude": latitude,
                "longitude": longitude,
                "message": message
            }
        )

        alert_id = result.lastrowid

    return {
        "success": True,
        "alert_id": alert_id,
        "message": "Risk alert saved successfully"
    }



@app.get("/api/alerts")
def get_alerts(limit: int = 20):

    with engine.begin() as connection:
        rows = connection.execute(
            text("""
                SELECT
                    id,
                    risk_level,
                    risk_score,
                    latitude,
                    longitude,
                    message,
                    created_at
                FROM risk_alerts
                ORDER BY id DESC
                LIMIT :limit
            """),
            {"limit": limit}
        ).mappings().all()

    return {
        "alerts": [dict(row) for row in rows]
    }
# ================= REAL WEATHER =================

import time
import requests

weather_cache = {}
WEATHER_CACHE_SECONDS = 300  # 5 minutes


@app.get("/api/weather")
def weather(
    lat: float = 26.14,
    lon: float = 91.74
):

    cache_key = f"{round(lat, 3)},{round(lon, 3)}"
    current_time = time.time()

    # -----------------------------
    # 1. RETURN CACHE IF AVAILABLE
    # -----------------------------
    if cache_key in weather_cache:

        cached_data = weather_cache[cache_key]

        if current_time - cached_data["timestamp"] < WEATHER_CACHE_SECONDS:

            result = cached_data["data"].copy()
            result["cached"] = True
            result["live"] = True

            return result

    # -----------------------------
    # 2. REQUEST FRESH DATA
    # -----------------------------
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}"
        f"&longitude={lon}"
        "&current=temperature_2m,"
        "relative_humidity_2m,"
        "precipitation,"
        "rain"
        "&hourly=precipitation"
        "&past_hours=24"
        "&forecast_hours=1"
        "&timezone=auto"
    )

    try:

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        current = data["current"]
        hourly = data["hourly"]

        rainfall_values = hourly.get("precipitation", [])

        rainfall_24h = round(
            sum(
                value for value in rainfall_values
                if value is not None
            ),
            2
        )

        result = {
            "latitude": lat,
            "longitude": lon,
            "temperature": current["temperature_2m"],
            "humidity": current["relative_humidity_2m"],
            "precipitation": current["precipitation"],
            "rain": current["rain"],
            "rainfall_24h": rainfall_24h,
            "source": "Open-Meteo",
            "live": True,
            "cached": False
        }

        # -----------------------------
        # 3. SAVE TO CACHE
        # -----------------------------
        weather_cache[cache_key] = {
            "timestamp": current_time,
            "data": result
        }

        return result

    except Exception as error:

        print("WEATHER API ERROR:", error)

        # -----------------------------
        # 4. USE OLD CACHE IF AVAILABLE
        # -----------------------------
        if cache_key in weather_cache:

            result = weather_cache[cache_key]["data"].copy()

            result["live"] = False
            result["cached"] = True
            result["source"] = "Open-Meteo (cached)"

            return result

        # -----------------------------
        # 5. NO DATA AVAILABLE
        # -----------------------------
        return {
            "latitude": lat,
            "longitude": lon,
            "temperature": 0,
            "humidity": 0,
            "precipitation": 0,
            "rain": 0,
            "rainfall_24h": 0,
            "source": "Weather API temporarily unavailable",
            "live": False,
            "cached": False
        }

# ================= TERRAIN / SLOPE =================
# ================= TERRAIN / SLOPE =================

@app.get("/api/terrain")
def terrain(
    lat: float = 26.14,
    lon: float = 91.74
):

    # Round coordinates to avoid unnecessary API requests
    cache_key = (
        round(lat, 2),
        round(lon, 2)
    )

    # Check cache
    cached = terrain_cache.get(cache_key)

    if cached:
        age = time.time() - cached["timestamp"]

        if age < TERRAIN_CACHE_SECONDS:
            print("TERRAIN CACHE HIT:", cache_key)

            result = cached["data"].copy()
            result["cached"] = True

            return result

    print("TERRAIN API REQUEST:", cache_key)

    # Five points around selected location
    offset = 0.001

    points = {
        "center": (lat, lon),
        "north": (lat + offset, lon),
        "south": (lat - offset, lon),
        "east": (lat, lon + offset),
        "west": (lat, lon - offset)
    }

    latitude_values = ",".join(
        str(point[0])
        for point in points.values()
    )

    longitude_values = ",".join(
        str(point[1])
        for point in points.values()
    )

    url = (
        "https://api.open-meteo.com/v1/elevation"
        f"?latitude={latitude_values}"
        f"&longitude={longitude_values}"
    )

    try:

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        elevations = data["elevation"]

        center_elevation = elevations[0]
        north_elevation = elevations[1]
        south_elevation = elevations[2]
        east_elevation = elevations[3]
        west_elevation = elevations[4]

        import math

        # Approximate distance for prototype
        distance_m = 111.0

        north_slope = math.degrees(
            math.atan(
                abs(north_elevation - center_elevation)
                / distance_m
            )
        )

        south_slope = math.degrees(
            math.atan(
                abs(south_elevation - center_elevation)
                / distance_m
            )
        )

        east_slope = math.degrees(
            math.atan(
                abs(east_elevation - center_elevation)
                / distance_m
            )
        )

        west_slope = math.degrees(
            math.atan(
                abs(west_elevation - center_elevation)
                / distance_m
            )
        )

        slope = round(
            max(
                north_slope,
                south_slope,
                east_slope,
                west_slope
            ),
            2
        )

        result = {
            "latitude": lat,
            "longitude": lon,
            "elevation": center_elevation,
            "slope": slope,
            "unit": "degrees",
            "source": "Open-Meteo Elevation API",
            "live": True,
            "cached": False,
            "prototype": True
        }

        # Save result in cache
        terrain_cache[cache_key] = {
            "timestamp": time.time(),
            "data": result
        }

        return result

    except Exception as error:

        print("TERRAIN API ERROR:", error)

        # Use previous cached data if available
        if cached:

            fallback = cached["data"].copy()

            fallback["cached"] = True
            fallback["live"] = False
            fallback["source"] = "Open-Meteo Elevation API (cached)"

            return fallback

        # No cached data
        return {
            "latitude": lat,
            "longitude": lon,
            "elevation": 0,
            "slope": 0,
            "unit": "degrees",
            "source": "Terrain API temporarily unavailable",
            "live": False,
            "cached": False,
            "prototype": True
        }


# ================= RISK ENGINE =================

# ================= RISK ENGINE =================

@app.get("/api/risk")
def calculate_risk(
    rainfall: float = 0,
    soil_moisture: float = 50,
    slope: float = 30,
    historical_events: int = 0,
    soil_trend: str = "STABLE"
):
    """
    Dhara Pulse prototype risk engine.

    IMPORTANT:
    This is a prototype explainable risk model.
    It is NOT an official GSI warning threshold
    or scientifically validated prediction model.
    """

    # -------------------------------------------------
    # 1. RAINFALL COMPONENT
    # Maximum contribution = 35 points
    # -------------------------------------------------

    rainfall_score = min(
        max(rainfall, 0) / 30 * 35,
        35
    )

    # -------------------------------------------------
    # 2. SOIL MOISTURE COMPONENT
    # Maximum contribution = 25 points
    # -------------------------------------------------

    soil_score = min(
        max(soil_moisture - 40, 0) / 50 * 25,
        25
    )

    # -------------------------------------------------
    # 3. SLOPE COMPONENT
    # Maximum contribution = 25 points
    # -------------------------------------------------

    slope_score = min(
        max(slope, 0) / 30 * 25,
        25
    )

    # -------------------------------------------------
    # 4. HISTORICAL LANDSLIDE COMPONENT
    # Maximum contribution = 15 points
    # -------------------------------------------------

    history_score = min(
        max(historical_events, 0) * 1.5,
        15
    )

    # -------------------------------------------------
# 5. SOIL MOISTURE TREND
# -------------------------------------------------

    trend_score = 0

    if soil_trend == "RISING":
        trend_score = 5
    elif soil_trend == "FALLING":
        trend_score = -2



    # -------------------------------------------------
    # 5. SOIL MOISTURE TREND
    # -------------------------------------------------

    trend_score = 0

    if soil_trend == "RISING":
        trend_score = 5

    elif soil_trend == "FALLING":
        trend_score = -2

    trend_score = max(min(trend_score, 5), -2)
    # -------------------------------------------------
    # TOTAL RISK SCORE
    # -------------------------------------------------

    score = round(
    rainfall_score
    + soil_score
    + slope_score
    + history_score
    + trend_score
)

    score = min(max(score, 0), 100)

    # -------------------------------------------------
    # RISK LEVEL
    # -------------------------------------------------

    if score >= 80:
        level = "CRITICAL"

    elif score >= 60:
        level = "HIGH"

    elif score >= 35:
        level = "MODERATE"

    else:
        level = "LOW"

    # -------------------------------------------------
    # FIND IMPORTANT CONTRIBUTING FACTORS
    # -------------------------------------------------

    factor_scores = {
        "rainfall": round(rainfall_score, 1),
        "soil_moisture": round(soil_score, 1),
        "slope": round(slope_score, 1),
        "historical_events": round(history_score, 1)
    }

    sorted_factors = sorted(
        factor_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    factor_names = {
        "rainfall": "recent rainfall",
        "soil_moisture": "elevated soil moisture",
        "slope": "terrain slope",
        "historical_events": "historical landslide activity"
    }

    main_factors = [
        factor_names[name]
        for name, value in sorted_factors
        if value > 0
    ][:3]

    # -------------------------------------------------
    # EXPLANATION
    # -------------------------------------------------

    if main_factors:

        explanation = (
            "Risk assessment is mainly influenced by "
            + ", ".join(main_factors)
            + "."
        )

    else:

        explanation = (
            "No significant risk factors were detected "
            "by the prototype model."
        )

    # -------------------------------------------------
    # RESPONSE
    # -------------------------------------------------

    return {
        "score": score,
        "level": level,

        "factors": {
            "rainfall": rainfall,
            "soil_moisture": soil_moisture,
            "slope": slope,
            "historical_events": historical_events
        },

        "factor_scores": factor_scores,

        "weights": {
            "rainfall": 35,
            "soil_moisture": 25,
            "slope": 25,
            "historical_events": 15
        },

        "main_factors": main_factors,

        "explanation": explanation,

        "prototype": True
    }


# ================= CREATE REPORT =================

@app.post("/api/reports")
def create_report(report: dict):

    with engine.begin() as connection:

        connection.execute(
            text("""
                INSERT INTO hazard_reports
                (
                    hazard_type,
                    description,
                    latitude,
                    longitude,
                    status
                )
                VALUES
                (
                    :hazard_type,
                    :description,
                    :latitude,
                    :longitude,
                    :status
                )
            """),
            {
                "hazard_type": report.get(
                    "hazard_type",
                    "UNKNOWN"
                ),
                "description": report.get(
                    "description",
                    ""
                ),
                "latitude": report.get("latitude"),
                "longitude": report.get("longitude"),
                "status": "NEW"
            }
        )

    return {
        "success": True,
        "message": "Hazard report saved to database"
    }


# ================= GET REPORTS =================

@app.get("/api/reports")
def get_reports():

    with engine.connect() as connection:

        rows = connection.execute(
            text("""
                SELECT
                    id,
                    hazard_type,
                    description,
                    latitude,
                    longitude,
                    status
                FROM hazard_reports
                ORDER BY id DESC
            """)
        ).mappings().all()

    return {
        "success": True,
        "count": len(rows),
        "reports": [dict(row) for row in rows]
    }

@app.patch("/api/reports/{report_id}/status")
def update_report_status(report_id: int, status: str):

    allowed_statuses = ["NEW", "VERIFIED", "REJECTED"]

    if status not in allowed_statuses:
        return {
            "success": False,
            "message": "Invalid status"
        }

    with engine.begin() as conn:

        result = conn.execute(
            text("""
                UPDATE hazard_reports
                SET status = :status
                WHERE id = :report_id
            """),
            {
                "status": status,
                "report_id": report_id
            }
        )

        if result.rowcount == 0:
            return {
                "success": False,
                "message": "Report not found"
            }

    return {
        "success": True,
        "report_id": report_id,
        "status": status
    }

# ================= DATABASE TEST =================

@app.get("/api/database-test")
def database_test():

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "success": True,
        "message": "Dhara Pulse database is connected"
    }

import random
from datetime import datetime

@app.get("/api/soil-moisture")
def soil_moisture():

    # Simulated IoT sensor reading
    moisture = round(random.uniform(55, 85), 1)

    timestamp = datetime.now().isoformat()

    # Save sensor reading to database
    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO soil_moisture_readings
                (soil_moisture, latitude, longitude, source, created_at)
                VALUES (:moisture, :latitude, :longitude, :source, :timestamp)
            """),
            {
                "moisture": moisture,
                "latitude": 26.14,
                "longitude": 91.74,
                "source": "IoT Sensor Network",
                "timestamp": timestamp
            }
        )

    return {
        "soil_moisture": moisture,
        "unit": "%",
        "source": "IoT Sensor Network",
        "live": True,
        "prototype": True,
        "timestamp": timestamp
    }
@app.get("/api/soil-moisture/history")
def soil_moisture_history():
    with engine.connect() as connection:
        result = connection.execute(text("""
            SELECT
                id,
                soil_moisture,
                latitude,
                longitude,
                source,
                created_at
            FROM soil_moisture_readings
            ORDER BY id DESC
            LIMIT 10
        """))

        rows = [dict(row._mapping) for row in result]

    return {
        "count": len(rows),
        "readings": rows
    }