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
print("[SETUP] Configuring Django environment...")
sys.stdout.reconfigure(encoding='utf-8')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import Lead  # Django model

# ----------------------------
# Load environment variables
# ----------------------------
print("[SETUP] Loading environment variables...")
load_dotenv()
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
if not APOLLO_API_KEY:
    raise ValueError("Apollo API key not found in .env")
print(f"[SETUP] Apollo API Key found: {'Yes' if APOLLO_API_KEY else 'No'}")

# ----------------------------
# ICP Filters for MockMapr
# ----------------------------
print("[SETUP] Defining ICP filters for MockMapr...")
ICP_FILTERS = {
    "person_titles": [
        "Head of Design",
        "Creative Designer",
        "Print Designer"
    ],
    "include_similar_titles": False,  # Strict match only
    "person_seniorities": ["owner", "founder", "c_suite", "director", "head", "manager"],
    "person_locations": [
        "United States","Germany", "France", "UK", "Netherlands", "Belgium", "Spain", "Italy", "Sweden", "Norway", "Denmark", "Poland"
    ],
    "contact_email_status": ["verified", "likely to engage"],
    "organization_num_employees_ranges": ["1,100"],  # small/medium studios and print shops

    "q_keywords": "design services, signage, design, print, product design, branding, mockup generation, poster design, brand design, logo design, graphic design",

    "per_page": 20
}

API_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"

# ----------------------------
# Helper function to fetch a page
# ----------------------------
def fetch_apollo_page(page_number):
    print(f"[FETCH] Fetching Apollo page {page_number}...")
    payload = ICP_FILTERS.copy()
    payload["page"] = page_number
    print(f"[PAYLOAD] Sending payload: {payload}")

    try:
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "x-api-key": APOLLO_API_KEY
            },
            json=payload,
            timeout=30
        )
        print(f"[RESPONSE] Status Code: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        print(f"[RESPONSE] JSON received: {data}")
        people = data.get("people", [])
        print(f"[INFO] Number of leads returned: {len(people)}")
        return people
    except requests.RequestException as e:
        print(f"[ERROR] API request failed on page {page_number}: {e}")
        return []

# ----------------------------
# Helper function to create or update lead
# ----------------------------
def upsert_lead(person):
    if not person.get("has_email", False):
        print(f"[SKIP] Lead skipped because no email: {person}")
        return

    apollo_id = person.get("id")
    first_name = person.get("first_name", "")
    last_name = person.get("last_name") or person.get("last_name_obfuscated") or ""
    full_name = f"{first_name} {last_name}".strip()
    company_name = person.get("organization", {}).get("name", "")
    title = person.get("title", "")
    email_verified = person.get("email_status") == "verified"
    phone = person.get("phone_number")
    address = person.get("current_employment", {}).get("location")
    website = person.get("current_employment", {}).get("website")

    print(f"[UPSERT] Saving lead: {full_name} | {company_name} | Title: {title} | Apollo ID: {apollo_id}")

    try:
        lead, created = Lead.objects.update_or_create(
            apollo_id=apollo_id,
            defaults={
                "name": full_name,
                "company_name": company_name,
                "title": title,
                "email_verified": email_verified,
                "phone": phone,
                "address": address,
                "website": website,
                "source": "apollo"
            }
        )
        if created:
            print(f"[NEW LEAD] Created: {full_name} | {company_name} | Apollo ID: {apollo_id}")
        else:
            print(f"[UPDATED LEAD] Updated: {full_name} | {company_name} | Apollo ID: {apollo_id}")
    except IntegrityError as e:
        print(f"[DB ERROR] Could not save lead {full_name} ({apollo_id}): {e}")

# ----------------------------
# Main Scraper Function
# ----------------------------
def run_apollo_scraper(max_pages=10, delay=2):
    print("[START] Apollo MockMapr ICP Scraper Running...")
    for page in range(1, max_pages + 1):
        print(f"\n[PAGE] Starting page {page}...")
        people = fetch_apollo_page(page)
        if not people:
            print("[INFO] No more leads returned. Stopping scraper.")
            break

        for idx, person in enumerate(people, 1):
            print(f"\n[PROCESS] Lead {idx} on Page {page}")
            upsert_lead(person)

        print(f"[INFO] Finished processing page {page}. Sleeping {delay} sec...")
        time.sleep(delay)

    print("\n[END] Apollo MockMapr ICP Scraper Finished.")

# ----------------------------
# Run the scraper
# ----------------------------
if __name__ == "__main__":
    run_apollo_scraper(max_pages=10, delay=2)  # Adjust max_pages & delay as needed
