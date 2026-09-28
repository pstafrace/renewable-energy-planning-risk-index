import os
import re
import csv
from docx import Document

def chunk_cases_from_docx(filepath):
    doc = Document(filepath)
    cases = []
    current_case_text = []
    
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

def extract_case_data(case_text):
    data = {
        "case_name": "Unknown",
        "citation": "Unknown",
        "decision_date": None,
        "lodgement_date": None,
        "planning_delay_days": None,
        "spatial_overlays": [],
        "regulatory_clauses": [],
        "outcome": "Unknown"
    }
    
    lines = case_text.split('\n')
    
    # 1. Extract Case Name & Citation
    # usually line 0 is CaseBase | [2024] VSCA 201 | BC2024...
    # But wait, we split ON CaseBase, so the case name is usually in the first few lines
    for i, line in enumerate(lines[:10]):
        if 'CaseBase' in line:
            parts = line.split('|')
            if len(parts) > 1:
                data['citation'] = parts[1].strip()
        elif ' v ' in line.lower() or (line.isupper() and len(line) > 10 and data['case_name'] == 'Unknown'):
            data['case_name'] = line.strip()
            
    # 2. Extract Decision Date
    # Look for standard date patterns in the first 20 lines (e.g. "13 September 2024")
    head_text = "\n".join(lines[:20])
    date_matches = re.findall(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})', head_text, re.IGNORECASE)
    if date_matches:
        data['decision_date'] = date_matches[-1] # Usually the last date in the header is the judgment date

    # 3. Extract Lodgement Date
    lodgement_matches = re.findall(r'(?:lodged|lodged on|filed on)\s*(?:the\s*)?(\d{1,2}\s+[A-Za-z]+\s+20\d{2}|\d{1,2}/\d{1,2}/\d{2,4})', case_text, re.IGNORECASE)
    if lodgement_matches:
        data['lodgement_date'] = lodgement_matches[0]
        
    # 4. Extract Overlays
    overlays_found = set()
    overlay_keywords = {
        "BMO": r'\b(?:BMO|Bushfire Management Overlay)\b',
        "ESO": r'\b(?:ESO|Environmental Significance Overlay)\b',
        "SLO": r'\b(?:SLO|Significant Landscape Overlay)\b',
        "VPO": r'\b(?:VPO|Vegetation Protection Overlay)\b',
        "HO": r'\b(?:HO|Heritage Overlay)\b',
        "LSIO": r'\b(?:LSIO|Land Subject to Inundation Overlay)\b'
    }
    for code, pattern in overlay_keywords.items():
        if re.search(pattern, case_text, re.IGNORECASE):
            overlays_found.add(code)
    data['spatial_overlays'] = " | ".join(sorted(list(overlays_found)))
    
    # 5. Extract Clauses
    clauses_found = set(re.findall(r'(?i)Clause\s+(\d{2}\.\d{2}[A-Za-z]*)', case_text))
    # Also look for 52.32 explicitly if written as "cl 52.32"
    clauses_found.update(re.findall(r'(?i)cl\s+(\d{2}\.\d{2}[A-Za-z]*)', case_text))
    data['regulatory_clauses'] = " | ".join(sorted(list(clauses_found)))
    
    # 6. Extract Outcome
    outcomes = ["Permit granted", "Application dismissed", "Declaration refused", "No permit granted", "Appeal allowed", "Application granted"]
    for outcome in outcomes:
        if outcome.lower() in case_text.lower()[-5000:]: # usually at the end
            data['outcome'] = outcome
            break
            
    return data

def main():
    files = ['full_text_batch_1.docx', 'full_text_batch_2.docx']
    all_cases = []
    
    for f in files:
        if os.path.exists(f):
            print(f"Chunking {f}...")
            cases = chunk_cases_from_docx(f)
            
            # Remove purely index intro blocks
            if cases and not re.search(r'^CaseBase\s*\|\s*\[', cases[0]):
                cases = cases[1:]
                
            all_cases.extend(cases)
            print(f"Found {len(cases)} case blocks in {f}")
            
    print(f"\nTotal potential cases to process: {len(all_cases)}")
    
    extracted_data = []
    for i, case_text in enumerate(all_cases):
        data = extract_case_data(case_text)
        # Filter out extremely short erroneous blocks
        if len(case_text) > 1000:
            extracted_data.append(data)
            
    # Filter for ONLY true planning appeals (drop purely commercial v commercial)
    # We look for "Minister" or "Council" or "Shire" in the case name
    filtered_data = []
    for idx, d in enumerate(extracted_data):
        cname = d['case_name'].lower()
        if 'minister' in cname or 'council' in cname or 'shire' in cname or 'city' in cname or len(d['spatial_overlays']) > 0 or len(d['regulatory_clauses']) > 0:
            filtered_data.append(d)
        
    print(f"\nSuccessfully extracted {len(filtered_data)} highly relevant planning cases (filtered from noise).")
    
    if filtered_data:
        keys = filtered_data[0].keys()
        output_file = 'longitudinal_analysis_dataset.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(filtered_data)
        print(f"Saved robust longitudinal dataset to {output_file}")

if __name__ == "__main__":
    main()
