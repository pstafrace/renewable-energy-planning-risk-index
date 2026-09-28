import os
import re
import csv
import json
import time
from docx import Document
from google import genai

try:
    client = genai.Client()
except Exception as e:
    print(f"Error initializing Gemini Client: {e}")
    exit(1)

def chunk_cases_from_docx(filepath):
    doc = Document(filepath)
    cases = []
    current_case_text = []
    
    # We notice some headers in LexisNexis might be split. We'll look for 'CaseBase | ['
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
        
        # New case delimiter
        if re.search(r'^CaseBase\s*\|\s*\[', text):
            if current_case_text:
                cases.append("\n".join(current_case_text))
            current_case_text = [text]
        else:
            current_case_text.append(text)
            
    if current_case_text:
        cases.append("\n".join(current_case_text))
        
    return cases

PROMPT = """
You are a legal data extraction assistant. I will provide you with the full text of a Victorian planning or environmental law case.
Your task is to extract the following information and return it strictly as a JSON object (no markdown, no backticks, just raw JSON).

{
  "lodgement_date": "YYYY-MM-DD or null if not found",
  "decision_date": "YYYY-MM-DD or null if not found",
  "planning_delay_days": integer or null,
  "spatial_overlays": ["BMO", "ESO", "SLO", etc] or [],
  "regulatory_clauses": ["Clause 52.32", etc] or [],
  "outcome": "Permit granted / Refused / Amended / Application dismissed / etc"
}

Case Text:
"""

def extract_case_data(case_text):
    # Truncate to first 40,000 characters to save time/tokens if the case is massive
    truncated_text = case_text[:40000]
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=PROMPT + truncated_text,
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Extraction error: {e}")
        return None

def main():
    files = ['full_text_batch_1.docx', 'full_text_batch_2.docx']
    all_cases = []
    for f in files:
        if os.path.exists(f):
            print(f"Chunking {f}...")
            cases = chunk_cases_from_docx(f)
            # Remove the very first chunk if it's just introductory index text (it won't have 'CaseBase | [')
            if cases and not re.search(r'^CaseBase\s*\|\s*\[', cases[0]):
                cases = cases[1:]
            all_cases.extend(cases)
            print(f"Found {len(cases)} cases in {f}")
            
    print(f"Total cases to process: {len(all_cases)}")
    
    extracted_data = []
    # Process just the first 5 cases as a Prototype
    for i, case_text in enumerate(all_cases[:5]):
        print(f"Processing case {i+1}...")
        data = extract_case_data(case_text)
        if data is not None:
            # Attempt to grab the case name from the first few lines
            lines = case_text.split('\n')
            case_name = "Unknown Case"
            # In Lexis exported docs, the line *before* the 'CaseBase | [' usually isn't there because we split ON 'CaseBase |'
            # Let's just find the first UPPERCASE line or line containing ' v '
            for line in lines[:10]:
                if ' v ' in line.lower() or (line.isupper() and len(line) > 10):
                    case_name = line
                    break
                    
            data['case_name'] = case_name
            extracted_data.append(data)
            
        time.sleep(2) # basic rate limit prevention
        
    print("\nExtraction Prototype Results:")
    print(json.dumps(extracted_data, indent=2))
    
    if extracted_data:
        keys = extracted_data[0].keys()
        with open('ai_extracted_preview.csv', 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(extracted_data)
        print("Saved preview to ai_extracted_preview.csv")

if __name__ == "__main__":
    main()
