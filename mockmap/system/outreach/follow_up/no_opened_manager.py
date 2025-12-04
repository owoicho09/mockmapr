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
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

# -----------------------------
# Imports
# -----------------------------
from mockmap.models import OutreachTracking, FollowUp, Template
from openai import OpenAI

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# -----------------------------
# CONFIG
# -----------------------------
NO_OPEN_HOURS = 32     # after 32 hours no open → follow-up generator
MAX_GPT_RETRIES = 3


# -----------------------------
# GPT EMAIL GENERATION
# -----------------------------
def build_email_prompt(lead, template_content: str) -> str:
    system_prompt = """
You are an expert B2B copywriter and outreach assistant specialized in MockMapr, a company that creates high-quality product mockups, visuals, and graphic assets for brands, print shops, print-on-demand services, apparel lines, and creative agencies.

Key Rules:

1. MockMapr Context:
   - Core Offerings: product mockups (apparel, merch, posters, packaging), e-commerce visuals, and custom design assets.
   - ICP: businesses selling physical products, print shops, POD services, creative agencies.
   - Value Proposition: save time, improve visual consistency, boost conversions, make workflows easier.
   - Position MockMapr as a problem-solver, not a service seller.

2. Personalization:
   - Adapt the template to the lead’s Name, Company, Title, Website, and Description.
   - Include a relevant insight whenever possible (product, visuals, brand detail).
   - Use informal company names for natural phrasing.

3. Tone & Style:
   - Casual, friendly, human.
   - Short and digestible: 2–3 sentences, under 65 words.
   - Natural phrasing; avoid over-formality or corporate jargon.
   - Use spintax if the template contains it for variation.

4. Behavior:
   - Lead **has NOT opened the previous email** (e.g., after 32 hours).
   - Assume they missed the earlier email; use a friendly nudge.
   - Focus on reinforcing value or curiosity.
   - End with a soft, low-pressure CTA.

5. Content Guidelines:
   - Subject: lowercase, 1–4 words, curiosity-driven.
   - Body: short sentences, clear value, subtle nudge.
   - Keep emails readable with line breaks where needed.

"""

    user_prompt = f"""
You’re writing a follow-up email to a prospect who has NOT opened the previous first email even after 32 hours.

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

email body here
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


def generate_email(lead, template_content: str, max_retries: int = MAX_GPT_RETRIES):
    prompt = build_email_prompt(lead, template_content)

    for attempt in range(max_retries):
        try:
            print(f"[INFO] Generating NO-OPEN email for {lead.email} attempt {attempt+1}")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.85,
                max_tokens=220
            )

            raw = response.choices[0].message.content
            subject, body = parse_email_response(raw)

            if subject and body:
                return subject, body

            print(f"[WARN] Empty GPT result for {lead.email}")

        except Exception as e:
            print(f"[ERROR] GPT error for {lead.email}: {e}")
            time.sleep(1)

    return None, None


# -----------------------------
# Get template (rotate)
# -----------------------------
def get_rotated_template(last_template_type=None) -> Optional[Template]:
    templates = list(Template.objects.filter(template_type="no-opened-follow_up", is_active=True))

    if not templates:
        print("[WARN] No follow-up templates found.")
        return None

    if last_template_type:
        filtered = [t for t in templates if t.template_type != last_template_type]
        templates = filtered or templates

    choice = random.choice(templates)
    print(f"[INFO] Using template: {choice.name}")
    return choice


# -----------------------------
# FETCH LEADS WITH NO OPEN AFTER 32 HOURS
# -----------------------------
def fetch_no_open_leads():
    now = timezone.now()
    threshold = now - timedelta(hours=NO_OPEN_HOURS)

    leads = OutreachTracking.objects.filter(
        event='delivered',      # delivered means we know mailgun accepted
        opened_at__isnull=True,
        timestamp__lte=threshold
    )

    print(f"[INFO] Found {leads.count()} no-opened leads.")
    return leads


# -----------------------------
# CREATE FOLLOW-UPS
# -----------------------------
def create_no_opened_followups():
    no_opened = fetch_no_open_leads()
    if not no_opened.exists():
        print("[INFO] No follow-ups needed right now.")
        return

    for ot in no_opened:
        lead = ot.lead

        # Avoid duplicate follow-ups
        if FollowUp.objects.filter(parent_email=ot).exists():
            print(f"[SKIP] Follow-up already exists for {lead.email}")
            continue

        last_follow = FollowUp.objects.filter(lead=lead).order_by('-created_at').first()
        last_template_type = last_follow.template_type if last_follow else None

        template = get_rotated_template(last_template_type)
        if not template:
            continue

        subject, body = generate_email(lead, template.content)
        if not subject or not body:
            print(f"[WARN] GPT failed for {lead.email}, skipping")
            continue

        followup = FollowUp.objects.create(
            lead=lead,
            parent_email=ot,
            followup_number=(last_follow.followup_number + 1) if last_follow else 1,
            template_type=template.template_type,
            email_subject=subject,
            email_body=body,
            ready_for_followup=True,
            status="ready"
        )

        print(f"[SUCCESS] Created NO-OPEN follow-up #{followup.followup_number} → {lead.email}")


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    print("[INFO] Starting NO-OPEN follow-up generation...")
    create_no_opened_followups()
    print("[INFO] Done.")
