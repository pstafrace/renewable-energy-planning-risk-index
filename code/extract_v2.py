import os
import re
import csv
from docx import Document

def extract_improved():
    files = ['full_text_batch_1.docx', 'full_text_batch_2.docx']
    cases = []
    
    for filepath in files:
        if not os.path.exists(filepath):
            continue
            
        doc = Document(filepath)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        
        current_title = "Unknown"
        current_case = []
        
        for i, text in enumerate(paragraphs):
            # A new case in LexisNexis exports usually starts with 'CaseBase | '
            if text.startswith('CaseBase') and '|' in text:
                if current_case:
                    # The title of the NEXT case was mistakenly added to the END of current_case
                    # Let's pop it off
                    if len(current_case) > 0:
                        current_case.pop()
                    cases.append((current_title, "\n".join(current_case)))
                    
                current_title = paragraphs[i-1] if i > 0 else "Unknown Title"
                current_case = [text]
            else:
                current_case.append(text)
                
        if current_case:
            cases.append((current_title, "\n".join(current_case)))
            
    # Now that we have cleanly chunked cases (Title, FullText), let's extract data
    
    extracted_data = []
    for title, text in cases:
        data = {
            "case_name": title[:200], # limit length just in case
            "decision_date": None,
            "lodgement_date": None,
            "planning_delay_days": None,
            "spatial_overlays": [],
            "regulatory_clauses": [],
            "outcome": "Unknown"
        }
        
        # 1. Decision Date
        # Look in the first 1500 characters for the judgment date pattern
        head_text = text[:1500]
        # Sometimes it says "Judgment Date: 12 August 2021"
        date_match = re.search(r'(?:Judgment Date|Decision Date|Date)\s*:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})', head_text, re.IGNORECASE)
        if date_match:
            data['decision_date'] = date_match.group(1)
        else:
            # Fallback: find standard dates in the header and take the last one
            dates = re.findall(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})', head_text, re.IGNORECASE)
            if dates:
                data['decision_date'] = dates[-1]
                
        # 2. Lodgement Date
        # VCAT decisions sometimes mention when the application was lodged.
        # e.g., "application was lodged on 14 May 2018" or "dated 14 May 2018"
        # We search the whole text, prioritizing "lodged"
        lodge_match = re.search(r'(?:lodged|filed|made)[^.]{0,30}on\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})', text, re.IGNORECASE)
        if lodge_match:
            data['lodgement_date'] = lodge_match.group(1)
            
        # 3. Spatial Overlays
        overlays_found = set()
        overlay_map = {
            r'\bBMO\b|Bushfire Management Overlay': 'BMO',
            r'\bESO\b|Environmental Significance Overlay': 'ESO',
            r'\bSLO\b|Significant Landscape Overlay': 'SLO',
            r'\bVPO\b|Vegetation Protection Overlay': 'VPO',
            r'\bHO\b|Heritage Overlay': 'HO',
            r'\bLSIO\b|Land Subject to Inundation Overlay': 'LSIO',
            r'\bPAO\b|Public Acquisition Overlay': 'PAO',
            r'\bEAO\b|Environmental Audit Overlay': 'EAO'
        }
        for pattern, code in overlay_map.items():
            if re.search(pattern, text, re.IGNORECASE):
                overlays_found.add(code)
        data['spatial_overlays'] = " | ".join(sorted(list(overlays_found)))
        
        # 4. Regulatory Clauses
        # Look for "Clause 52.32" or "cl 52.32"
        clauses = set(re.findall(r'(?i)\b(?:Clause|cl)\s+(\d{2}\.\d{2}[A-Za-z]*)\b', text))
        data['regulatory_clauses'] = " | ".join(sorted(list(clauses)))
        
        # 5. Outcome
        
        # 1. Look for explicit outcome in catchwords (often formatted as "— Appeal dismissed —")
        catchword_match = re.search(r'(?i)—\s*(Permit granted|Permit refused|Appeal allowed|Appeal dismissed|Application dismissed|Application granted|Proceeding dismissed)\s*—', head_text)
        
        # 2. Look for "Held:" which indicates the outcome in CaseBase
        held_match = re.search(r'(?i)\bHeld\s*[:-]\s*([^.—]+)', head_text)
        
        # 3. Look for "Orders:" near the end of the text (ignoring footnotes at the very end by searching a larger tail)
        tail_text = text[-12000:]
        order_match = re.search(r'(?i)^(?:Orders|Order)\s*[:-]\s*([^.\n]+)', tail_text, re.MULTILINE)
        
        # 4. Look for flexible verb phrases anywhere in the document, prioritizing the tail
        verb_match = re.search(r'(?i)\b(permit|application|appeal|proceeding|summons|action)\s+(?:is|was|shall\s+be|must\s+be|will\s+be|hereby\s+)?(granted|dismissed|refused|allowed|set\s+aside)', tail_text)
        
        if catchword_match:
            data['outcome'] = catchword_match.group(1).strip().capitalize()
        elif held_match and len(held_match.group(1)) > 5:
            data['outcome'] = held_match.group(1).strip().capitalize()
        elif order_match and len(order_match.group(1)) > 5:
            data['outcome'] = order_match.group(1).strip().capitalize()
        elif verb_match:
            data['outcome'] = f"{verb_match.group(1).capitalize()} {verb_match.group(2).lower()}"
        else:
            data['outcome'] = "Unknown"
        
        # Filter: Is this actually a planning case?
        # A planning case will usually mention "permit", "planning scheme", "council", "vcat", or "tribunal"
        # Or it has actual overlays.
        is_planning = bool(
            re.search(r'(?i)\b(?:planning scheme|permit|vcat|tribunal|council|shire)\b', text) or 
            len(overlays_found) > 0 or 
            len(clauses) > 0
        )
        
        if is_planning and len(text) > 1500: # drop tiny fragments
            extracted_data.append(data)
            
    # Calculate delays
    from datetime import datetime
    for d in extracted_data:
        try:
            if d['decision_date'] and d['lodgement_date']:
                fmt = "%d %B %Y"
                date1 = datetime.strptime(d['lodgement_date'], fmt)
                date2 = datetime.strptime(d['decision_date'], fmt)
                d['planning_delay_days'] = (date2 - date1).days
                # Sanity check: if delay is massively negative or completely absurd, null it out
                if d['planning_delay_days'] < 0 or d['planning_delay_days'] > 5000:
                    d['planning_delay_days'] = None
        except:
            d['planning_delay_days'] = None

    # Write output
    if extracted_data:
        keys = extracted_data[0].keys()
        with open('longitudinal_analysis_dataset.csv', 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(extracted_data)
        print(f"Extraction V2 complete. Saved {len(extracted_data)} refined cases.")

if __name__ == "__main__":
    extract_improved()
