from openai import OpenAI
import time
import os
from .prompts import generate_initial_prompt, generate_continuation_prompt
import re
import json

# Initialize OpenAI client with API key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MAX_ROWS = 25

def call_openai(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content
        except Exception as e:
            if "APIConnectionError" in str(type(e)):
                print(f"⚠️ Connection error: {e}. Retrying in 5s...")
                time.sleep(5)
            else:
                print(f"❌ Unexpected error: {e}")
                raise
    raise Exception("❌ Failed after multiple retries.")

def extract_json_from_gpt_response(response_text):
    try:
        # Try loading directly if it's a clean list
        if response_text.strip().startswith('['):
            return json.loads(response_text)

        # Try to extract a JSON block inside markdown or text
        match = re.search(r'```json\s*(\[.*?\])\s*```', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))

        # Try to find a fallback list of dicts
        match = re.search(r'(\[\s*{.*?}\s*\])', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(1))

        print("⚠️ JSON not found in response")
        return []
    except Exception as e:
        print("⚠️ JSON parsing error:", e)
        return []


def generate_all_records(drawing_text):
    all_records = []
    seen_names = set()
    iteration = 0

    while True:
        if iteration == 0:
            prompt = generate_initial_prompt(drawing_text, max_rows=MAX_ROWS)
        else:
            prompt = generate_continuation_prompt(drawing_text, list(seen_names), max_rows=MAX_ROWS)

        print(f"\n📤 Calling GPT for batch {iteration + 1}...")
        try:
            response = call_openai(prompt)
        except Exception as e:
            print(f"❌ Error during GPT call: {e}")
            break

        raw_text = response
        print("📥 Raw GPT response:")
        print(raw_text)

        # Try parsing using the existing extraction function
        records = extract_json_from_gpt_response(raw_text)
        if not records:
            print("❌ Failed to parse GPT output.")
            break

        # Validate and filter
        valid_batch = [r for r in records if isinstance(r, dict) and "Name" in r]
        new_names = [r["Name"] for r in valid_batch if r["Name"] not in seen_names]

        if not new_names:
            print("✅ No new valid records. Finishing.")
            break

        seen_names.update(new_names)
        all_records.extend(valid_batch)
        print(f"✅ Added {len(new_names)} new records.")
        iteration += 1

    return all_records 