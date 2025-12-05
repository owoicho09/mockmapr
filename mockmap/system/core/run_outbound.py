import sys
import os
import django
from django.utils import timezone
import time

# ---------------------------
# Django setup
# ---------------------------
print("[SETUP] Configuring Django environment...")
sys.stdout.reconfigure(encoding='utf-8')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# ---------------------------
# Imports of sequences
# ---------------------------
from mockmap.system.core.first_sequence import run_first_touch_sequence
from mockmap.system.core.first_follow_up import run_followup_sequence
from mockmap.system.core.second_follow_up import run_followup_sequence2
from mockmap.system.core.send_update import send_emails

# ---------------------------
# Main orchestrator
# ---------------------------
def run_outbound():
    print(f"[INFO] Starting OUTBOUND sequence at {timezone.now()}")

    # -----------------------------
    # 1️⃣ First Touch Sequence
    # -----------------------------
    try:
        print("[INFO] Running FIRST TOUCH sequence...")
        run_first_touch_sequence()
        print("[INFO] FIRST TOUCH sequence completed.")
    except Exception as e:
        print(f"[ERROR] FIRST TOUCH sequence failed: {e}")

    time.sleep(5)  # small buffer between sequences

    # -----------------------------
    # 2️⃣ First Follow-Up Sequence
    # -----------------------------
    try:
        print("[INFO] Running FIRST FOLLOW-UP sequence...")
        run_followup_sequence()
        print("[INFO] FIRST FOLLOW-UP sequence completed.")
    except Exception as e:
        print(f"[ERROR] FIRST FOLLOW-UP sequence failed: {e}")

    time.sleep(5)

    # -----------------------------
    # 3️⃣ Second Follow-Up Sequence
    # -----------------------------
    try:
        print("[INFO] Running SECOND FOLLOW-UP sequence...")
        run_followup_sequence2()
        print("[INFO] SECOND FOLLOW-UP sequence completed.")
    except Exception as e:
        print(f"[ERROR] SECOND FOLLOW-UP sequence failed: {e}")

    print(f"[INFO] OUTBOUND sequence finished at {timezone.now()}")

# ---------------------------
# Entry point
if __name__ == "__main__":
    # Run the main outbound function
    run_outbound()

    # Email notification
    recipient_list = ['michaelogaje033@gmail.com']
    subject = "MockMapr Outbound System Update"
    message = f"""
Hello Team,

The MockMapr outbound system has completed its latest run successfully.

Next scheduled run: in 2 hours.

Best regards,
MockMapr Bot
"""
    send_emails(subject, message, recipient_list)
