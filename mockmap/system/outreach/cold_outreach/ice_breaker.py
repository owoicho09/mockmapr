import time
import re, os, sys, random
from typing import Optional, Tuple
from django.db import transaction
from openai import OpenAI
from dotenv import load_dotenv
import django

# ---------------------------
# Django setup
# ---------------------------
print("[SETUP] Configuring Django environment...")
sys.stdout.reconfigure(encoding='utf-8')
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import Lead, OutreachTemplate, OutreachSequence, Template

# ---------------------------
# Load environment
# ---------------------------
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=openai_api_key)

# ---------------------------
# GPT EMAIL GENERATION
# ---------------------------
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
   - Include a specific, relevant insight whenever possible (product, visuals, brand detail).
   - Use informal company names if applicable for natural phrasing.

3. Tone & Style:
   - Casual, friendly, and human-like.
   - Short and digestible: 3 sentences max, under 70 words.
   - Natural phrasing; avoid over-formality or corporate jargon.
   - Use spintax if the template contains it for variation.

4. Content Guidelines:
   - Subject: lowercase, curiosity-driven, ≤30 characters.
   - Body: structure as compliment → problem → hint solution.
   - End with a soft, low-friction CTA, e.g., “want a quick peek?”.
   - Keep emails readable with line breaks where needed.

5. Behavior:
   - Treat each email as a **first-touch cold outreach** unless otherwise specified.
   - Focus on delivering clear value and personalized insight without selling the service directly.

"""

    user_prompt = f"""
You’re a copywriter writing short, friendly cold emails that feel like one person reaching out to another.

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
        body = re.sub(r"(?i)^body:\s*", "", "\n".join(lines[1:])) if len(lines) > 1 else ""
        return subject.strip(), body.strip()
    except:
        return None, None

def generate_personalized_email(lead, template_content: str, max_retries: int = 3):
    prompt = build_email_prompt(lead, template_content)
    for attempt in range(max_retries):
        try:
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
        except Exception as e:
            print(f"GPT error for {lead.email}, attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
    return None, None

# ---------------------------
# TEMPLATE ROTATION LOGIC
# ---------------------------
def get_rotated_template(last_used_template_id=None) -> Template:
    """
    Returns a template in a dynamic rotation.
    Avoids picking the same template consecutively if possible.
    """
    templates = list(Template.objects.all())
    if not templates:
        return None
    # Remove last used template from options if possible
    if last_used_template_id and len(templates) > 1:
        templates = [t for t in templates if t.id != last_used_template_id]
    return random.choice(templates)

# ---------------------------
# MAIN SEQUENCE BUILDER
# ---------------------------
def generate_first_sequences():
    leads = Lead.objects.filter(email_verified=True, email_sent=False, icp_match=True)
    if not leads.exists():
        print("No leads ready.")
        return

    print(f"Starting GPT generation for {leads.count()} leads...")

    last_used_template_id = None

    for lead in leads:
        if OutreachSequence.objects.filter(lead=lead, step=1).exists():
            print(f"Skipping {lead.email} — step 1 already exists.")
            continue

        template = get_rotated_template(last_used_template_id)
        if not template:
            print("❌ No templates found in DB. Skipped.")
            continue

        subject, body = generate_personalized_email(lead, template.content)
        if not subject or not body:
            print(f"❌ GPT failed for {lead.email}. Skipped.")
            continue

        OutreachSequence.objects.create(
            lead=lead,
            step=1,
            template=None,              # optional, can leave null
            template_used=template,     # assign the template used
            email_subject=subject,
            email_body=body,
            status="pending",
        )

        last_used_template_id = template.id  # remember for rotation
        print(f"✔ Created GPT email for {lead.email} using template '{template.name}'")

    print("\n🔥 Done — GPT sequences generated.")

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    generate_first_sequences()
