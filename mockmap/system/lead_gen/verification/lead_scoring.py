import os
import sys
import django
import json
import re
from dotenv import load_dotenv
from openai import OpenAI

# --------------------------------------
# Django setup
# --------------------------------------
print("🔧 Setting up Django environment...")
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../../.."))
sys.path.insert(0, APP_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from mockmap.models import Lead

# --------------------------------------
# Load env + GPT client
# --------------------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --------------------------------------
# Config
# --------------------------------------
BATCH_SIZE = 7  # change to 10/20/etc

ICP_CRITERIA = """
You are an expert B2B lead evaluator for MockMapr, a company that creates high-quality product mockups, visuals, and graphic assets for brands, print shops, print-on-demand services, apparel lines, and creative agencies.

Task:
Score leads to determine if they match MockMapr’s Ideal Customer Profile (ICP) **before outreach**.

Ideal ICP matches include:

1. Businesses selling physical products that require mockups:
   - Examples: apparel,signage, merchandise, posters, prints, packaging, custom products, Etsy stores, Shopify brands.

2. Creative or branding agencies producing designs for clients:
   - Examples: design studios, marketing agencies, brand identity firms, signage.

3. Print shops or print-on-demand services:
   - Examples: local print shops, POD companies, screen printers, DTG printers, custom merch printers.

Non-matches include:
- Pure software companies, SaaS, or services unrelated to product visuals or mockups.
- Companies that do not produce posters,mockup, prints, packaging, custom products or sell physical products, or do not need design assets.

Instructions:
- Evaluate each lead individually.
- Use the lead’s business description, title, or website to inform your decision.
- Provide a concise reason explaining the score.
- Only return **JSON**, formatted EXACTLY like this:

[
  {"id": 123, "icp_match": true, "reason": "They run a print shop"},
  {"id": 124, "icp_match": false, "reason": "They sell software only"}
]

- Do NOT include any extra text or commentary outside the JSON.
"""


# --------------------------------------
# Extract JSON safely
# --------------------------------------
def extract_json(text):
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in response")
    return match.group(0)

# --------------------------------------
# Process one batch
# --------------------------------------
def score_batch():
    leads = list(Lead.objects.filter(scored=False)[:BATCH_SIZE])

    if not leads:
        print("⭕ No unscored leads left.")
        return False

    print(f"📦 Scoring batch of {len(leads)} leads")

    payload = []
    for lead in leads:
        payload.append({
            "id": lead.id,
            "name": lead.name,
            "title": lead.title or "",
            "company_name": lead.company_name or "",
            "email": lead.email,
            "website": lead.website or "",
            "keywords": lead.keywords or "",
            "description": lead.description or "",
        })

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0,
            messages=[
                {"role": "system", "content": ICP_CRITERIA},
                {"role": "user", "content": json.dumps(payload)}
            ]
        )
    except Exception as e:
        print(f"❌ GPT API error: {e}")
        return False

    raw = response.choices[0].message.content
    print("📩 Raw GPT response:", raw)

    try:
        json_text = extract_json(raw)
        result = json.loads(json_text)
    except Exception as e:
        print("❌ Failed to parse JSON:", e)
        print("RAW:", raw)
        return False

    # Update DB
    for item in result:
        try:
            lead = Lead.objects.get(id=item["id"])
            lead.icp_match = item["icp_match"]
            lead.icp_reason = item.get("reason", "")
            lead.scored = True
            lead.save()
            print(f"✔ Updated lead {lead.id} | Match={lead.icp_match}")
        except Lead.DoesNotExist:
            print(f"⚠ Lead ID not found: {item['id']}")

    print("🎯 Batch done.\n")
    return True

# --------------------------------------
# MAIN LOOP
# --------------------------------------
if __name__ == "__main__":
    print("🚀 Starting scoring engine...\n")

    batches = 0
    while score_batch():
        batches += 1
        print(f"🔁 Completed batch #{batches}")

    print(f"\n🎉 Finished scoring! Total batches: {batches}")
