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
            if text.startswith('CaseBase') and '|' in text:
                if current_case:
                    if len(current_case) > 0:
                        current_case.pop()
                    cases.append((current_title, "\n".join(current_case)))
                current_title = paragraphs[i-1] if i > 0 else "Unknown Title"
                current_case = [text]
            else:
                current_case.append(text)
                
        if current_case:
            cases.append((current_title, "\n".join(current_case)))
            
    extracted_data = []
    for title, text in cases:
        data = {
            "case_name": title[:200],
            "decision_date": None,
            "lodgement_date": None,
            "planning_delay_days": None,
            "spatial_overlays": [],
            "regulatory_clauses": [],
            "outcome": "Unknown"
        }
        
        head_text = text[:1500]
        
        # Date
        date_match = re.search(r'(?:Judgment Date|Decision Date|Date)\s*:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})', head_text, re.IGNORECASE)
        if date_match:
            data['decision_date'] = date_match.group(1)
        else:
            dates = re.findall(r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+20\d{2})', head_text, re.IGNORECASE)
            if dates:
                data['decision_date'] = dates[-1]
                
        # Lodgement
        lodge_match = re.search(r'(?:lodged|filed|made)[^.]{0,30}on\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})', text, re.IGNORECASE)
        if lodge_match:
            data['lodgement_date'] = lodge_match.group(1)
            
        # Overlays
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
        
        # Clauses
        clauses = set(re.findall(r'(?i)\b(?:Clause|cl)\s+(\d{2}\.\d{2}[A-Za-z]*)\b', text))
        data['regulatory_clauses'] = " | ".join(sorted(list(clauses)))
        
        # Outcomes V3
        outcomes = [
            "Permit granted", "Permit refused", "No permit granted", "Decision set aside", 
            "Appeal allowed", "Appeal dismissed", "Application dismissed", "Application refused",
            "Declaration refused", "Declaration made", "Application granted", "Direction made", 
            "Order made", "Orders made", "Leave to appeal refused", "Leave to appeal granted",
            "Summons dismissed", "Proceeding dismissed", "Injunction granted", "Injunction refused",
            "Costs ordered", "Costs to follow the event", "Determination affirmed", "Determination quashed",
            "Orders accordingly"
        ]
        
        # Attempt specific headers
        held_match = re.search(r'(?i)\bHeld\s*[:-]\s*([^.—\n]+)', head_text)
        # Attempt NLP on the doc tail
        tail_term = text[-8000:]
        verb_match = re.search(r'(?i)\b(permit|application|appeal|proceeding|leave)[^.]{0,30}\b(granted|dismissed|refused|allowed|set\s+aside)', tail_term)
        
        if held_match and len(held_match.group(1)) > 5:
            data['outcome'] = held_match.group(1).strip()
        elif verb_match:
            data['outcome'] = f"{verb_match.group(1).capitalize()} {verb_match.group(2).lower()}"
        else:
            # Fallback scan over entire text
            for out in outcomes:
                if out.lower() in text.lower():
                    data['outcome'] = out
                    break
        
        # Filter noise
        is_planning = bool(
            re.search(r'(?i)\b(?:planning scheme|permit|vcat|tribunal|council|shire)\b', text) or 
            len(overlays_found) > 0 or 
            len(clauses) > 0
        )
        if is_planning and len(text) > 1500:
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
                if d['planning_delay_days'] < 0 or d['planning_delay_days'] > 5000:
                    d['planning_delay_days'] = None
        except:
            d['planning_delay_days'] = None

    if extracted_data:
        keys = extracted_data[0].keys()
        with open('longitudinal_analysis_dataset.csv', 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, keys)
            dict_writer.writeheader()
            dict_writer.writerows(extracted_data)
        print(f"Extraction V3 complete. Saved {len(extracted_data)} refined cases.")

if __name__ == "__main__":
    extract_improved()
