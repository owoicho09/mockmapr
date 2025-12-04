import os
import sys
import csv
import django

# -----------------------------
# Django Setup
# -----------------------------
print("🔧 Setting up Django environment...")
sys.stdout.reconfigure(encoding='utf-8')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import Lead

# -----------------------------
# CSV File
# -----------------------------
CSV_FILE_PATH = "csv-json/mockmapleads/Cold Email Leads/mockmapr_dallas_FINAL_personalized.csv"  # Update path accordingly

# -----------------------------
# Import function
# -----------------------------
def import_leads_from_csv():
    print("[INFO] Starting import from CSV...")

    added_count = 0
    skipped_count = 0

    with open(CSV_FILE_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        print(f"[INFO] CSV columns detected: {reader.fieldnames}")

        for row_num, row in enumerate(reader, start=1):
            email = row.get("Email", "").strip()
            first_name = row.get("FirstName", "").strip()
            last_name = row.get("LastName", "").strip()
            phone = row.get("Phone", "").strip()
            business_name = row.get("BusinessName", "").strip()
            website = row.get("Website", "").strip()
            location = row.get("Location", "").strip()
            verification_status = row.get("VerificationStatus", "").strip()
            description = row.get("proof_evidence_snippet", "").strip()
            keywords = row.get("project_type", "").strip()

            # Skip rows with no email
            if not email:
                print(f"[WARN] Row {row_num} skipped: missing email")
                skipped_count += 1
                continue

            # Prevent duplicates
            if Lead.objects.filter(email=email).exists():
                print(f"[SKIP] Row {row_num}: Lead already exists: {email}")
                skipped_count += 1
                continue

            # Build lead name
            full_name = f"{first_name} {last_name}".strip() or business_name or "Unknown"

            # Create Lead
            lead = Lead.objects.create(
                name=full_name,
                company_name=business_name or "Unknown",
                email=email,
                phone=phone,
                website=website,
                address=location,
                description=description,
                keywords=keywords,
                source="csv",
                email_verified=True if verification_status.lower() == "valid" else False,
                phone_verified=bool(phone),
            )
            added_count += 1
            print(f"[ADDED] Row {row_num}: {lead.name} | {lead.email}")

    print(f"[INFO] Import completed. Added: {added_count}, Skipped: {skipped_count}")


# -----------------------------
# Run script
# -----------------------------
if __name__ == "__main__":
    import_leads_from_csv()
