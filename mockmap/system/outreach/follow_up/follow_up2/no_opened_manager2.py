import os
import sys
import django
import random
import re
import time
from datetime import timedelta
from typing import Tuple, Optional
from dotenv import load_dotenv
from django.utils import timezone

# -----------------------------
# Django setup
# -----------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../../../"))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# -----------------------------
# Imports
# -----------------------------
from mockmap.models import FollowUp, Template
from openai import OpenAI

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# -----------------------------
# Config
# -----------------------------
NO_OPEN_HOURS = 32  # hours after first follow-up sent, if not opened
SCHEDULE_DELAY_HOURS = 16
MAX_GPT_RETRIES = 3

# -----------------------------
# GPT EMAIL GENERATION
# -----------------------------
def build_email_prompt(lead, template_content: str) -> str:
    system_prompt = """
You are an expert B2B outreach assistant specialized in MockMapr, a company that creates high-quality product mockups, visuals, and graphic assets for brands, print shops, print-on-demand services, apparel lines, and creative agencies.

Key Rules:

1. MockMapr Context:
   - Core Offerings: product mockups (apparel, merch, posters, packaging), e-commerce visuals, and custom design assets.
   - ICP: businesses selling physical products, print shops, POD services, creative agencies.
   - Value Proposition: save time, improve visual consistency, boost conversions, make workflows easier.
   - Position MockMapr as a problem-solver, not a service seller.

2. Personalization:
   - Adapt the template to the lead’s Name, Company, Title, Website, and Description.
   - Include a specific, relevant insight whenever possible (product, visuals, brand detail).
   - Use informal company names if applicable for natural phrasing.

3. Tone & Style:
   - Professional but approachable; slightly casual when appropriate.
   - Short, digestible emails (ideally 4–6 lines, with line breaks).
   - Natural, human-like; avoid over-formality and jargon.
   - Use spintax if the template contains it for variations in greetings or closings.

4. Behavior:
   - Assume the lead did NOT open the first follow-up email.
   - Do NOT reference previous emails.
   - Focus on delivering clear value and a low-friction CTA.
   - Keep emails under ~120 words unless template specifies otherwise.

"""

    user_prompt = f"""
You’re writing a follow-up email to a prospect who did NOT open our first follow-up email after {NO_OPEN_HOURS} hours.

Template Reference:
{template_content}

Lead:
- Name: {lead.name}
- Company: {lead.company_name}
- Website: {lead.website}
- Title: {lead.title}
- Description: {lead.description}

Output Format:

subject line

body text here
"""
    prompt = system_prompt + user_prompt
    return prompt

def parse_email_response(raw_output: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        lines = [l.strip() for l in raw_output.splitlines() if l.strip()]
        if not lines:
            return None, None
        subject = re.sub(r"(?i)^subject:\s*", "", lines[0])
        body = "\n".join(lines[1:]) if len(lines) > 1 else ""
        return subject.strip(), body.strip()
    except Exception as e:
        print(f"[ERROR] Failed parsing GPT output: {e}")
        return None, None

def generate_personalized_email(lead, template_content: str, max_retries: int = MAX_GPT_RETRIES):
    prompt = build_email_prompt(lead, template_content)
    for attempt in range(max_retries):
        try:
            print(f"[INFO] Generating NO-OPEN follow-up for {lead.email}, attempt {attempt+1}")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=250
            )
            raw = response.choices[0].message.content
            subject, body = parse_email_response(raw)
            if subject and body:
                return subject, body
            print(f"[WARN] Empty subject/body for {lead.email}")
        except Exception as e:
            print(f"[ERROR] GPT error for {lead.email}, attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return None, None

# -----------------------------
# TEMPLATE ROTATION
# -----------------------------
def get_rotated_template(last_template_type=None) -> Optional[Template]:
    templates = list(Template.objects.filter(template_type="no_open_followup", is_active=True))
    if not templates:
        print("[WARN] No active NO-OPEN follow-up templates found.")
        return None
    if last_template_type:
        templates = [t for t in templates if t.template_type != last_template_type] or templates
    chosen = random.choice(templates)
    print(f"[INFO] Using template: {chosen.name} (ID: {chosen.id})")
    return chosen

# -----------------------------
# Fetch leads who did NOT open first follow-up
# -----------------------------
def fetch_no_open_first_followups():
    threshold = timezone.now() - timedelta(hours=NO_OPEN_HOURS)
    followups = FollowUp.objects.filter(
        followup_number=1,
        opened=False,
        sent_at__lte=threshold
    )
    print(f"[INFO] Found {followups.count()} first follow-ups NOT opened")
    return followups

# -----------------------------
# CREATE NO-OPEN FOLLOW-UPS
# -----------------------------
def create_no_open_followups2():
    first_followups = fetch_no_open_first_followups()
    if not first_followups.exists():
        print("[INFO] No leads to create NO-OPEN follow-ups for.")
        return

    for first in first_followups:
        lead = first.lead
        last_template_type = first.template_type

        template = get_rotated_template(last_template_type)
        if not template:
            continue

        subject, body = generate_personalized_email(lead, template.content)
        if not subject or not body:
            print(f"[WARN] Skipping lead {lead.id} (GPT failure)")
            continue

        followup = FollowUp.objects.create(
            lead=lead,
            parent_email=first.parent_email,  # OutreachTracking instance
            followup_number=2,
            template=template,
            template_type=template.template_type,
            email_subject=subject,
            email_body=body,
            ready_for_followup=True,
            status="ready",
            scheduled_at=timezone.now() + timedelta(hours=SCHEDULE_DELAY_HOURS)
        )

        print(f"[SUCCESS] NO-OPEN follow-up created for {lead.email}")

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    print("[INFO] Starting NO-OPEN follow-up generation...")
    create_no_open_followups2()
    print("[INFO] Done.")
