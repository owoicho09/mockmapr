import os
import sys
import django
import requests
import time
import random
from datetime import datetime
from dotenv import load_dotenv
from django.utils import timezone

# -----------------------------
# Setup Django environment
# -----------------------------
print("🔧 Setting up Django environment...")
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import OutreachSequence, OutreachTracking

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
MAILGUN_API_KEY = os.getenv("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.getenv("MAILGUN_DOMAIN")
REPLY_TO_EMAIL = "mockmaproutreach@gmail.com"
MAILGUN_BASE_URL = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"

print(f"🔑 Mailgun Domain: {MAILGUN_DOMAIN}")
print(f"🔑 Mailgun API Key: {'SET' if MAILGUN_API_KEY else 'NOT SET'}")

# -----------------------------
# Config
# -----------------------------
BATCH_SIZE = 5
PAUSE_BETWEEN_EMAILS = 5  # seconds
WARMUP_EMAILS = [
    "michaelogaje033@gmail.com",
    "kennkiyoshi@gmail.com",
    "owi.09.12.02@gmail.com",
    "unitorial111@gmail.com",
    "009.012.k2@gmail.com",
    "u15529464@gmail.com",
    "owoiichoo@gmail.com",
    "genesissystems011@gmail.com",
    "kacheofficiall@gmail.com",
    "michael.m1904722@st.futminna.edu.ng",
    "anthonyogaje44@gmail.com",
]

# -----------------------------
# Mailgun send function
# -----------------------------
def send_email(to_email: str, subject: str, body: str):
    """
    Sends a single email via Mailgun
    """
    data = {
        "from": f"MockMapr <no-reply@{MAILGUN_DOMAIN}>",
        "to": to_email,
        "subject": subject,
        "text": body,
        "html": body,
        "h:Reply-To": REPLY_TO_EMAIL,
        "o:tracking": "yes",
        "o:tracking-clicks": "yes",
        "o:tracking-opens": "yes",
        "o:tracking-domain": f"email.mg.{MAILGUN_DOMAIN}",
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
        print(f"✔ Mailgun response: {result}")
        return result.get("id")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        return None

# -----------------------------
# Process pending emails
# -----------------------------
def process_pending_emails():
    pending_sequences = list(OutreachSequence.objects.filter(status="pending")[:BATCH_SIZE])

    if not pending_sequences:
        print("[INFO] No pending emails to send.")
        return

    print(f"[INFO] Sending {len(pending_sequences)} emails in this batch...")

    # Keep track of sent sequences to pick for warmup
    sent_sequences = []

    # Send emails to real leads
    for outreach in pending_sequences:
        print(f"[INFO] Processing lead: {outreach.lead.email} | {outreach.lead.name}")
        message_id = send_email(outreach.lead.email, outreach.email_subject, outreach.email_body)

        if message_id:
            # Update outreach status
            outreach.status = "sent"
            outreach.sent_at = timezone.now()
            outreach.save()

            # Track real lead
            OutreachTracking.objects.create(
                lead=outreach.lead,
                sequence=outreach,
                message_id=message_id,
                event="delivered",
            )
            outreach.lead.email_sent = True
            outreach.lead.save()
            print(f"✔ Email sent to real lead: {outreach.lead.email}")
            sent_sequences.append(outreach)
        else:
            outreach.status = "failed"
            outreach.save()
            print(f"❌ Email FAILED for {outreach.lead.email}")

        time.sleep(PAUSE_BETWEEN_EMAILS)

    # -----------------------------
    # Send one warmup email per batch
    # -----------------------------
    if sent_sequences:
        warmup_sequence = random.choice(sent_sequences)
        warmup_email = random.choice(WARMUP_EMAILS)
        print(f"[INFO] Sending warmup email to {warmup_email} using subject from {warmup_sequence.lead.email}")

        message_id = send_email(warmup_email, warmup_sequence.email_subject, warmup_sequence.email_body)

        if message_id:
            OutreachTracking.objects.create(
                lead=None,  # Shadow tracking
                sequence=warmup_sequence,
                message_id=message_id,
                event="delivered",
            )
            print(f"✔ Warmup email sent to {warmup_email}")
        else:
            print(f"❌ Warmup email FAILED for {warmup_email}")

    print("[INFO] Batch completed.")

# -----------------------------
# Run script
# -----------------------------
if __name__ == "__main__":
    process_pending_emails()
