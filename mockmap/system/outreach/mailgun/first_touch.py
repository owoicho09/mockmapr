import os
import sys
import django
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
from django.utils import timezone

# -----------------------------
# Setup Django environment
# -----------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import OutreachSequence, OutreachTracking

# -----------------------------
# Load environment
# -----------------------------
load_dotenv()
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")  # e.g., mg.mockmapr.com
REPLY_TO_EMAIL = "mockmaproutreach@gmail.com"
MAILGUN_BASE_URL = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"

# -----------------------------
# Config
# -----------------------------
BATCH_SIZE = 10
PAUSE_BETWEEN_EMAILS = 5  # seconds

# -----------------------------
# Mailgun send function
# -----------------------------
def send_email(outreach: OutreachSequence):
    data = {
        "from": f"MockMapr <no-reply@{MAILGUN_DOMAIN}>",
        "to": outreach.lead.email,
        "subject": outreach.email_subject,
        "text": outreach.email_body,
        "html": outreach.email_body,
        "h:Reply-To": REPLY_TO_EMAIL,
        "o:tracking": "yes",
        "o:tracking-clicks": "yes",
        "o:tracking-opens": "yes",
        "o:tracking-domain": "email.mg.mockmaproutreach.com",
        "o:tracking-protocol": "https",
    }
    try:
        response = requests.post(
            MAILGUN_BASE_URL,
            auth=("api", MAILGUN_API_KEY),
            data=data
        )
        response.raise_for_status()
        result = response.json()
        return result.get("id")
    except Exception as e:
        print(f"❌ Failed to send email to {outreach.lead.email}: {e}")
        return None

# -----------------------------
# Process pending OutreachSequence in batches
# -----------------------------
def process_pending_emails():
    pending_sequences = OutreachSequence.objects.filter(status="pending")[:BATCH_SIZE]
    if not pending_sequences.exists():
        print("[INFO] No pending emails to send.")
        return

    print(f"[INFO] Sending {len(pending_sequences)} emails in this batch...")

    for outreach in pending_sequences:
        message_id = send_email(outreach)
        if message_id:
            outreach.status = "sent"
            outreach.sent_at = timezone.now()
            outreach.save()

            # Create tracking record
            OutreachTracking.objects.create(
                lead=outreach.lead,
                sequence=outreach,
                message_id=message_id,
                event="delivered",
            )
            print(f"✔ Email sent to {outreach.lead.email} | message_id: {message_id}")
        else:
            outreach.status = "failed"
            outreach.save()

        time.sleep(PAUSE_BETWEEN_EMAILS)

    print(f"[INFO] Batch completed. {len(pending_sequences)} emails processed.")

# -----------------------------
# Run script
# -----------------------------
if __name__ == "__main__":
    process_pending_emails()
