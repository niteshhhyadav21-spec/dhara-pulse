import pdfplumber

PDF_FILE = "landslide_report.pdf"

with pdfplumber.open(PDF_FILE) as pdf:

    page = pdf.pages[0]

    print("Reading page 1...")

    table = page.extract_table()

    if table:

        print("\nTABLE FOUND!\n")

        for row in table[:10]:
            print(row)

    else:

        print("No table found on page 1.")