import sys, os
import django
from django.utils import timezone

# ---------------------------
print("[SETUP] Configuring Django environment...")
sys.stdout.reconfigure(encoding='utf-8')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# ---------------------------
from mockmap.system.outreach.follow_up.follow_up2.follow_up_manager2 import create_second_followups
from mockmap.system.outreach.follow_up.follow_up2.no_opened_manager2 import create_no_open_followups2
from mockmap.system.outreach.follow_up.follow_up2.follow_up2 import process_followups
from mockmap.models import FollowUp

BATCH_SIZE = 10

def run_followup_sequence2():
    print("[INFO] Starting FOLLOW-UP sequence at", timezone.now())

    # Opened-but-no-reply
    print("[INFO] Creating opened-but-no-reply follow-ups...")
    create_second_followups()
    print("[INFO] Done.")

    # No-open leads
    print("[INFO] Creating no-open follow-ups...")
    create_no_open_followups2()
    print("[INFO] Done.")

    # -----------------------------
    # 2️⃣ Send pending follow-ups in batches
    # -----------------------------
    pending_count = FollowUp.objects.filter(
        ready_for_followup=True,
        followup_number=2,
    ).count()

    if pending_count == 0:
        print("[INFO] No pending follow-up emails to send.")
    else:
        print(f"[INFO] Sending follow-ups in batches (max {BATCH_SIZE} per run)...")
        process_followups(batch_size=BATCH_SIZE)

    print("[INFO] FOLLOW-UP sequence completed at", timezone.now())


if __name__ == "__main__":
    run_followup_sequence2()
