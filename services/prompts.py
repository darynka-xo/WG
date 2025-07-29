def generate_initial_prompt(drawing_text, max_rows=25):
    return f"""
You are an AI agent helping to extract part data from a technical drawing. The drawing defines a **base part number** and **variation rules** (e.g., material, dash size, finish, etc.) in notes and tables.

Your goal is to:
- Extract the **logic of part number construction**
- Generate **structured records** for each valid part (up to {max_rows} in this batch)
- Each record must match the format of this sample:

Example output record (JSON object):
{{
  "Name": "HL79D6",
  "Base Part Number 1": "HL79",
  "Part Series": "HL",
  "Sales Description": "HI-LOK® COLLAR, 2024-T6 ALUMINUM ALLOY",
  "Part Material Detail": "2024 aluminum alloy per QQ-A-430 or QQ-A-225/6",
  "Part Finish 1": "Anodize per MIL-A-8625",
  "Lube Type": "Cetyl alcohol or Solid film lube",
  "Self-Locking": "Yes"
  ...
}}

You must return a JSON(as a Python list of dictionaries) array of up to {max_rows} part records, based on the text below. Include only the fields specified in the NetSuite template (Name, Thread, Material, Finish, etc). Use best guesses if something is implicit. Output ONLY the list, no explanation, no markdown. 

Drawing text:
\"\"\"
{drawing_text}
\"\"\"
Your output must start with `[{{` and end with `}}]`.
"""


def generate_continuation_prompt(text, existing_names, max_rows=25):
    excluded = ", ".join(existing_names[-50:])  # последние 50 имён, чтобы не перегружать
    return f"""
You are an assistant extracting structured data about aerospace fasteners from engineering drawings.

Below is the content of the drawing:
{text[:10000]}

Already extracted part names (exclude these): {excluded}

Now, generate the next {max_rows} part records in JSON format, matching the schema below.

Schema example (each part must match):
[
  {{
    "Name": "HL79-6",
    "Base Part Number 1": "HL79",
    "Part Series": "HL",
    "Sales Description": "HI-LOK® COLLAR, 2024-T6 ALUMINUM ALLOY",
    "Part Material Detail": "2024 aluminum alloy per QQ-A-430 or QQ-A-225/6",
    "Part Finish 1": "Anodize per MIL-A-8625, dye color red, and cetyl alcohol lube per Hi-Shear Spec. 305",
    "Lube Type": "Cetyl alcohol",
    "Self-Locking": "Yes",
    "Thread": "10-32UNJF-3B"
  }},
  ...
]

Do not repeat existing records. Output only the JSON array, without explanations.
"""
