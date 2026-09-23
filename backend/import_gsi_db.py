import csv
import sqlite3
import re

CSV_FILE = "gsi_clean_final.csv"
DATABASE_FILE = "dhara_pulse.db"


# Connect to database
connection = sqlite3.connect(DATABASE_FILE)

cursor = connection.cursor()


# Create GSI historical landslide table
cursor.execute("""
CREATE TABLE IF NOT EXISTS gsi_historical_landslides (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    serial_number INTEGER,

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
""")


# Clear previous GSI import
cursor.execute("""
DELETE FROM gsi_historical_landslides
""")


records = []


with open(
    CSV_FILE,
    "r",
    encoding="utf-8"
) as file:

    reader = csv.DictReader(file)

    for row in reader:

        try:

            latitude = float(row["latitude"])
            longitude = float(row["longitude"])

        except (ValueError, TypeError):

            continue


        # Extract year from slide number
        year = None

        slide_number = row["slide_number"]

        year_match = re.search(
            r"/(\d{4})/",
            slide_number
        )

        if year_match:

            year = int(year_match.group(1))


        records.append((
            int(row["serial_number"]),
            slide_number,
            row["state"],
            row["district"],
            row["slide_name"],
            row["nh_sh_location"],
            latitude,
            longitude,
            row["material"],
            row["movement_type"],
            row["history"],
            year
        ))


# Insert all records
cursor.executemany("""
INSERT INTO gsi_historical_landslides
(
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
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", records)


connection.commit()


# Check total records
cursor.execute("""
SELECT COUNT(*)
FROM gsi_historical_landslides
""")

total = cursor.fetchone()[0]


print()
print("================================")
print("GSI DATABASE IMPORT COMPLETE")
print("================================")
print("Records imported:", total)
print("Database:", DATABASE_FILE)
print("Table: gsi_historical_landslides")


connection.close()