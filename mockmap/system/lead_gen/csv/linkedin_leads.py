import os
import sys
import csv
import django
from django.db import transaction

# -----------------------------
# Django Setup
# -----------------------------
sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import Lead

# -----------------------------
# CSV path
# -----------------------------
CSV_FILE_PATH = os.path.join(
    APP_ROOT,
    "csv-json",
    "mockmapleads",
    "Cold Email Leads",
    "Sales Navigator Data 30,000.xlsx - Sales-Nav-Wholesale-Clean.csv"
)

BATCH_SIZE = 10


def clean_field(value):
    """Strip whitespace and quotes."""
    if value:
        value = str(value).strip().strip('"').strip("'")
        print(f"[DEBUG] Cleaned field: {value}")
        return value
    return ""


def import_salesnav_leads():
    print("[INFO] Import starting...")
    total_added = 0
    total_skipped = 0
    row_number = 0
    batch = []

    with open(CSV_FILE_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            row_number += 1
            print(f"\n[INFO] Processing row {row_number}: {row}")

            # Skip completely empty rows
            if not any(row):
                print(f"[WARN] Row {row_number} skipped: empty row")
                total_skipped += 1
                continue

            # Ensure row has at least 9 columns
            while len(row) < 9:
                row.append("")
                print(f"[DEBUG] Row {row_number} padded with empty field: {row}")

            try:
                email = clean_field(row[0])
                first_name = clean_field(row[1])
                last_name = clean_field(row[2])
                linkedin_url = clean_field(row[3])
                title = clean_field(row[4])
                company_name = clean_field(row[5])
                website = clean_field(row[6])
                phone = clean_field(row[7])
                address = clean_field(row[8])

                if not email:
                    print(f"[WARN] Row {row_number} skipped: missing email")
                    total_skipped += 1
                    continue

                # Check for duplicates
                duplicate_email = Lead.objects.filter(email=email).exists()
                duplicate_linkedin = linkedin_url and Lead.objects.filter(linkedin_url=linkedin_url).exists()
                if duplicate_email or duplicate_linkedin:
                    print(f"[SKIP] Row {row_number} duplicate found. Email: {duplicate_email}, LinkedIn: {duplicate_linkedin}")
                    total_skipped += 1
                    continue

                lead = Lead(
                    name=f"{first_name} {last_name}".strip(),
                    company_name=company_name,
                    email=email,
                    linkedin_url=linkedin_url,
                    title=title,
                    website=website,
                    phone=phone,
                    address=address,
                    source="csv",
                    rating=None,
                    reviews_count=None,
                    email_verified=False,
                    phone_verified=False,
                )

                batch.append(lead)
                print(f"[DEBUG] Row {row_number} added to batch. Batch size: {len(batch)}")

                # Bulk save in batches
                if len(batch) >= BATCH_SIZE:
                    with transaction.atomic():
                        Lead.objects.bulk_create(batch)
                        total_added += len(batch)
                        print(f"[INFO] Batch saved at row {row_number}. {len(batch)} leads added.")
                        batch = []

            except Exception as e:
                print(f"[ERROR] Row {row_number} failed: {e}")
                total_skipped += 1

        # Save any remaining leads
        if batch:
            with transaction.atomic():
                Lead.objects.bulk_create(batch)
                total_added += len(batch)
                print(f"[INFO] Final batch saved. {len(batch)} leads added.")

    print(f"\n[INFO] Import complete. Total rows processed: {row_number}")
    print(f"[INFO] Total added: {total_added}, total skipped: {total_skipped}")


if __name__ == "__main__":
    import_salesnav_leads()
