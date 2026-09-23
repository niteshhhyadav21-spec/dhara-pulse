import re
import csv

INPUT_FILE = "gsi_raw.txt"
OUTPUT_FILE = "gsi_clean_v2.csv"

records = []

STATES = [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Puducherry",
    "Chandigarh",
    "Andaman and Nicobar Islands",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Lakshadweep"
]

with open(INPUT_FILE, "r", encoding="utf-8") as file:

    for line in file:

        line = line.strip()

        if not line:
            continue

        if line.startswith("====="):
            continue

        record_match = re.match(
            r"^(\d+)\s+(.+)$",
            line
        )

        if not record_match:
            continue

        serial_number = record_match.group(1)
        record_text = record_match.group(2)

        slide_match = re.match(
            r"([A-Z]{2}/[A-Z0-9]+/[A-Z0-9]+/\d{4}/\d+)\s+(.+)",
            record_text
        )

        if not slide_match:
            continue

        slide_number = slide_match.group(1)
        remaining = slide_match.group(2)

        # Find latitude and longitude
        # Latitude: approximately 6 to 38 degrees
        # Longitude: approximately 68 to 98 degrees
        coordinate_match = re.search(
            r"\b((?:[6-9]|[12]\d|3[0-8])(?:\.\d+)?)\s+"
            r"((?:6[89]|[7-9]\d|9[0-8])(?:\.\d+)?)\b",
            remaining
        )

        if not coordinate_match:
            continue

        latitude = float(coordinate_match.group(1))
        longitude = float(coordinate_match.group(2))

        # Find state
        state = ""

        for state_name in STATES:

            if re.search(
                r"\b" + re.escape(state_name) + r"\b",
                remaining,
                re.IGNORECASE
            ):
                state = state_name
                break

        if not state:
            continue

        # Find text before coordinates
        before_coordinates = remaining[
            :coordinate_match.start()
        ].strip()

        # Find where the state ends
        state_match = re.search(
            r"\b" + re.escape(state) + r"\b",
            before_coordinates,
            re.IGNORECASE
        )

        if not state_match:
            continue

        after_state = before_coordinates[
            state_match.end():
        ].strip()

        # First two words are used as a temporary district estimate
        district_words = after_state.split()

        if len(district_words) >= 2:
            district = " ".join(district_words[:2])
        elif len(district_words) == 1:
            district = district_words[0]
        else:
            district = ""

        # Text after coordinates
        after_coordinates = remaining[
            coordinate_match.end():
        ].strip()

        material = ""
        movement_type = ""
        history = ""

        movement_patterns = [
            "Debris Slide",
            "Rock Slide",
            "Earth Slide",
            "Soil Slide",
            "Debris Flow",
            "Rock Fall",
            "Debris Fall",
            "Earth Fall"
        ]

        for pattern in movement_patterns:

            if pattern.lower() in after_coordinates.lower():

                parts = re.split(
                    re.escape(pattern),
                    after_coordinates,
                    maxsplit=1,
                    flags=re.IGNORECASE
                )

                material = pattern.split()[0]
                movement_type = pattern.split()[1]

                if len(parts) > 1:
                    history = parts[1].strip()

                break

        records.append({
            "serial_number": serial_number,
            "slide_number": slide_number,
            "state": state,
            "district": district,
            "latitude": latitude,
            "longitude": longitude,
            "material": material,
            "movement_type": movement_type,
            "history": history
        })


print("Records found:", len(records))

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    fieldnames = [
        "serial_number",
        "slide_number",
        "state",
        "district",
        "latitude",
        "longitude",
        "material",
        "movement_type",
        "history"
    ]

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(records)

print("Clean data saved to:", OUTPUT_FILE)