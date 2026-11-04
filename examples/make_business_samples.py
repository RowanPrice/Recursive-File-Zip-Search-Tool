"""Make a folder of fake business files to test the search tool with.

Run it like this:

    python examples/make_business_samples.py

It creates a folder called business_samples next to this script, filled
with small pretend files: invoices, scans, spreadsheets, reports and a
few more. Every name matches at least one category in
examples/categories.json. It also packs most of them into a ZIP, so you
can see the tool finding matches inside ZIPs too.

Then search the folder:

    python main.py examples/business_samples

The results land in results.csv. Nothing here is real data; delete the
folder whenever you like and run this script again to remake it.
"""

from pathlib import Path
from zipfile import ZipFile

# The folder this script lives in, so it works from anywhere.
HERE = Path(__file__).resolve().parent
OUT = HERE / "business_samples"

# One pretend file per business category, plus a couple that match two
# categories and two that match only the general ones.
FILES = [
    "INV-2026-001.pdf",          # invoices (and documents)
    "invoice_acme_ltd.pdf",      # invoices (and documents)
    "brain_scan.dcm",            # scans
    "prototype_part.stl",        # scans
    "site_photo.jpg",            # scans (and images)
    "sales_data.xlsx",           # spreadsheets
    "staff_list.csv",            # spreadsheets
    "quarterly_report.pdf",      # reports (and documents)
    "report.pdf",                # reports (and documents)
    "contract_acme.pdf",         # contracts (and documents)
    "supplier_agreement.docx",   # contracts (and documents)
    "receipt_march.pdf",         # receipts (and documents)
    "pitch_deck.pptx",           # presentations
    "notes.txt",                 # documents only
    "photo.png",                 # images only
]

# The files that also go into the ZIP.
ZIP_FILES = [
    "INV-2026-001.pdf",
    "invoice_acme_ltd.pdf",
    "brain_scan.dcm",
    "prototype_part.stl",
    "site_photo.jpg",
    "sales_data.xlsx",
    "staff_list.csv",
    "quarterly_report.pdf",
    "contract_acme.pdf",
    "receipt_march.pdf",
    "pitch_deck.pptx",
]

TEXT = "Sample file for testing the zip search tool. Not real data.\n"


def main():
    """Write the sample files and pack some of them into a ZIP."""
    OUT.mkdir(exist_ok=True)
    for name in FILES:
        (OUT / name).write_text(TEXT, encoding="utf-8")

    zip_path = OUT / "business_samples.zip"
    with ZipFile(zip_path, "w") as bundle:
        for name in ZIP_FILES:
            bundle.write(OUT / name, arcname=name)

    print("Created {} files plus business_samples.zip in {}".format(
        len(FILES), OUT))
    print('Now try: python main.py "{}"'.format(OUT))


if __name__ == "__main__":
    main()
