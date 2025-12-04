import os
import sys
import django
import requests
from dotenv import load_dotenv
from django.utils import timezone
import time

# -----------------------------
# Django environment setup
# -----------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import FollowUp

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")  # e.g. mg.mockmapr.com
REPLY_TO_EMAIL = "mockmaproutreach@gmail.com"
MAILGUN_URL = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"

# -----------------------------
# Config
# -----------------------------
BATCH_SIZE = 10       # max emails to send per run
DELAY_BETWEEN_EMAILS = 10  # seconds pause between sends

# -----------------------------
# Send follow-up email (Mailgun)
# -----------------------------
def send_followup_email(fu: FollowUp):
    data = {
        "from": f"MockMapr <no-reply@{MAILGUN_DOMAIN}>",
        "to": fu.lead.email,
        "subject": fu.email_subject,
        "text": fu.email_body,
        "html": fu.email_body,
        "h:Reply-To": REPLY_TO_EMAIL,
        "o:tracking": "yes",
        "o:tracking-clicks": "yes",
        "o:tracking-opens": "yes",
        "o:tracking-domain": "email.mg.mockmaproutreach.com",
        "o:tracking-protocol": "https",
    }

    try:
        response = requests.post(
            MAILGUN_URL,
            auth=("api", MAILGUN_API_KEY),
            data=data
        )
        response.raise_for_status()
        message_id = response.json().get("id")
        print(f"✅ Sent follow-up to {fu.lead.email} → {message_id}")
        return message_id
    except Exception as e:
        print(f"❌ ERROR sending follow-up to {fu.lead.email}: {e}")
        return None

# -----------------------------
# Process follow-ups in batches
# -----------------------------
def process_followups(batch_size=BATCH_SIZE):
    followups = FollowUp.objects.filter(
        ready_for_followup=True,
        status__in=['draft', 'ready']
    ).order_by('followup_number')[:batch_size]

    if not followups.exists():
        print("[INFO] No follow-ups to send.")
        return

    print(f"[INFO] Sending {followups.count()} follow-ups in this batch...")

    for fu in followups:
        msg_id = send_followup_email(fu)
        if not msg_id:
            print(f"⚠️ Skipping update for FollowUp {fu.id}, send failed.")
            continue

        fu.message_id = msg_id
        fu.status = "sent"
        fu.sent_at = timezone.now()
        fu.save()
        time.sleep(DELAY_BETWEEN_EMAILS)

    print("[INFO] Batch complete.")

# -----------------------------
# Run script
# -----------------------------
if __name__ == "__main__":
    print("[INFO] Sending queued follow-ups...")
    process_followups()
    print("[INFO] Finished.")
