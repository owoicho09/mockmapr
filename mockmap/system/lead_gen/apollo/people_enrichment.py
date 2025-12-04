import os
import sys
import django
import requests
import time
from dotenv import load_dotenv
from django.db import IntegrityError

# ----------------------------
# Setup Django environment
# ----------------------------
sys.stdout.reconfigure(encoding='utf-8')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import Lead

# ----------------------------
# Load environment variables
# ----------------------------
load_dotenv()
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
if not APOLLO_API_KEY:
    raise ValueError("Apollo API key not found in .env")

# ----------------------------
# Constants
# ----------------------------
BULK_ENRICH_URL = "https://api.apollo.io/api/v1/people/bulk_match"
BATCH_SIZE = 10  # max 10 IDs per bulk call
DELAY = 2        # seconds between requests

# ----------------------------
# Helper function: enrich batch
# ----------------------------
def enrich_batch(leads):
    ids_payload = [{"id": lead.apollo_id} for lead in leads]
    payload = {"details": ids_payload}
    print(f"[ENRICH] Sending bulk enrichment payload: {payload}")

    try:
        response = requests.post(
            BULK_ENRICH_URL + "?reveal_personal_emails=false&reveal_phone_number=false",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "x-api-key": APOLLO_API_KEY
            },
            json=payload,
            timeout=30
        )
        print(f"[RESPONSE] Status code: {response.status_code}")
        data = response.json()
        print(f"[RESPONSE] JSON: {data}")
        return data.get("matches", [])
    except requests.RequestException as e:
        print(f"[ERROR] Bulk enrichment failed: {e}")
        return []

# ----------------------------
# Main enrichment function
# ----------------------------
def run_enrichment():
    print("[START] Apollo Enrichment Script Running...")

    # Fetch leads needing enrichment
    leads_to_enrich = list(Lead.objects.filter(email_verified=False, apollo_id__isnull=False))
    total_leads = len(leads_to_enrich)
    print(f"[INFO] Found {total_leads} leads to enrich")

    # Process in batches
    for i in range(0, total_leads, BATCH_SIZE):
        batch = leads_to_enrich[i:i + BATCH_SIZE]
        print(f"[BATCH] Processing leads {i+1} to {i+len(batch)}")

        enriched_people = enrich_batch(batch)
        print(f"[INFO] Received {len(enriched_people)} enriched records")

        for person in enriched_people:
            apollo_id = person.get("id")
            first_name = person.get("first_name") or ""
            last_name = person.get("last_name") or ""
            full_name = f"{first_name} {last_name}".strip()
            linkedin_url = person.get("linkedin_url") or ""
            email = person.get("email") or ""

            org = person.get("organization", {}) or {}

            website = org.get("website", "") or ""

            keywords = ", ".join(person.get("organization", {}).get("keywords", [])) if person.get("organization") else ""
            title = person.get("title") or ""

            try:
                lead = Lead.objects.get(apollo_id=apollo_id)
                lead.name = full_name
                lead.first_name = first_name
                lead.last_name = last_name
                lead.title = title
                lead.keywords = keywords
                lead.linkedin_url = linkedin_url
                lead.website = website
                lead.email = email
                lead.email_verified = True
                lead.save()
                print(f"[UPDATED] Lead {full_name} ({apollo_id}) updated with email: {email}, keywords & LinkedIn")
            except Lead.DoesNotExist:
                print(f"[SKIP] Lead with Apollo ID {apollo_id} not found in DB")
            except IntegrityError as e:
                print(f"[DB ERROR] Could not update lead {full_name}: {e}")

        print(f"[BATCH] Sleeping for {DELAY} seconds before next batch")
        time.sleep(DELAY)

    print("[END] Apollo Enrichment Script Finished.")

# ----------------------------
# Run the enrichment
# ----------------------------
if __name__ == "__main__":
    run_enrichment()
