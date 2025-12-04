import sys,os
import django

# ---------------------------
print("[SETUP] Configuring Django environment...")
sys.stdout.reconfigure(encoding='utf-8')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()


from mockmap.system.outreach.mailgun.first_touch import process_pending_emails
from mockmap.system.outreach.cold_outreach.ice_breaker import generate_first_sequences

from mockmap.models import OutreachSequence, Lead
from django.utils import timezone

BATCH_SIZE = 10

def run_first_touch_sequence():
    print("[INFO] Starting FIRST TOUCH sequence at", timezone.now())

    # -----------------------------
    # 1️⃣ Generate first-touch email content only for leads without content
    # -----------------------------
    leads_to_generate = Lead.objects.filter(
        email_verified=True,
        email_sent=False,
        icp_match=True
    ).exclude(
        outreachsequence__step=1
    )

    if leads_to_generate.exists():
        print(f"[INFO] Generating email content for {leads_to_generate.count()} leads...")
        generate_first_sequences()
    else:
        print("[INFO] All leads already have first-touch content. Skipping GPT generation.")

    # -----------------------------
    # 2️⃣ Send pending emails in batches
    # -----------------------------
    pending_count = OutreachSequence.objects.filter(status="pending").count()
    if pending_count == 0:
        print("[INFO] No pending emails to send.")
    else:
        print(f"[INFO] Sending emails in batches (max {BATCH_SIZE} per run)...")
        process_pending_emails()

    print("[INFO] FIRST TOUCH sequence completed at", timezone.now())


if __name__ == "__main__":
    run_first_touch_sequence()
