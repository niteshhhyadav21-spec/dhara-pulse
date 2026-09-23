import pdfplumber
import csv

PDF_FILE = "landslide_report.pdf"
OUTPUT_FILE = "gsi_clean_final.csv"

headers = [
    "serial_number",
    "slide_number",
    "state",
    "district",
    "slide_name",
    "nh_sh_location",
    "latitude",
    "longitude",
    "material",
    "movement_type",
    "history"
]

records = []

with pdfplumber.open(PDF_FILE) as pdf:

    print("Total pages:", len(pdf.pages))

    for page_number, page in enumerate(pdf.pages, start=1):

        print(f"Reading page {page_number}/{len(pdf.pages)}")

        table = page.extract_table()

        if not table:
            continue

        for row in table:

            if not row:
                continue

            # Skip header row
            if row[0] == "Sl.No.":
                continue

            # Make sure row has enough columns
            if len(row) < 11:
                continue

            records.append({
                "serial_number": row[0],
                "slide_number": row[1],
                "state": row[2],
                "district": row[3],
                "slide_name": row[4],
                "nh_sh_location": row[5],
                "latitude": row[6],
                "longitude": row[7],
                "material": row[8],
                "movement_type": row[9],
                "history": row[10]
            })


print()
print("Total records found:", len(records))


with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=headers
    )

    writer.writeheader()
    writer.writerows(records)


print("Clean GSI data saved to:", OUTPUT_FILE)