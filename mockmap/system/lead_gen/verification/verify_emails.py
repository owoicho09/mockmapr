import os
import sys
import django
import time
import neverbounce_sdk

# -----------------------------
# Setup Django environment
# -----------------------------
print("🔧 Setting up Django environment...")
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import Lead

# -----------------------------
# NeverBounce SDK setup
# -----------------------------
NEVERBOUNCE_API_KEY = os.getenv("NEVERBOUNCE_API_KEY")
print(f"🔑 Using NeverBounce API key: {'SET' if NEVERBOUNCE_API_KEY else 'NOT SET'}")

client = neverbounce_sdk.client(api_key=NEVERBOUNCE_API_KEY)

# -----------------------------
# Batch processing function
# -----------------------------
BATCH_SIZE = 20
PAUSE_BETWEEN_EMAILS = 2  # seconds between verifications to avoid rate limits


def verify_leads():
    print("[INFO] Starting email verification process...")

    # Fetch leads that are not yet verified and have an email
    pending_leads = Lead.objects.filter(email__isnull=False, email_verified=False)
    total = pending_leads.count()
    print(f"[INFO] Found {total} leads to verify")

    offset = 0
    while offset < total:
        batch = pending_leads[offset:offset + BATCH_SIZE]
        print(f"[INFO] Processing batch {offset // BATCH_SIZE + 1} | {len(batch)} leads")

        for lead in batch:
            print(f"[INFO] Verifying lead: {lead.name} | {lead.email}")
            try:
                verification = client.single_check(
                    email=lead.email,
                    address_info=True,
                    credits_info=True,
                    timeout=10
                )
                result = verification.get("result")
                print(f"[INFO] Verification result for {lead.email}: {result}")

                if result == "valid":
                    lead.email_verified = True
                    lead.save()
                    print(f"✅ Lead email verified: {lead.email}")
                else:
                    print(f"⚠️ Lead email not verified ({result}): {lead.email}")

            except Exception as e:
                print(f"[ERROR] Failed to verify {lead.email}: {e}")

            time.sleep(PAUSE_BETWEEN_EMAILS)

        offset += BATCH_SIZE
        print(f"[INFO] Completed batch {offset // BATCH_SIZE}. Moving to next batch...\n")

    print("[INFO] Email verification process completed.")


# -----------------------------
# Run script
# -----------------------------
if __name__ == "__main__":
    verify_leads()
