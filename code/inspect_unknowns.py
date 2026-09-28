import pandas as pd
from docx import Document

df = pd.read_csv('longitudinal_analysis_dataset.csv')
unknown_cases = df[df['outcome'] == 'Unknown']['case_name'].tolist()

def extract_improved():
    files = ['full_text_batch_1.docx', 'full_text_batch_2.docx']
    cases = []
    
    for filepath in files:
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
            
    # Print the last 800 chars of the first 3 unknown cases
    count = 0
    for title, text in cases:
        # Match case name (approximate due to truncation)
        if any(uc[:50] in title for uc in unknown_cases):
            print(f"\n--- {title[:100]} ---")
            print(text[-800:])
            count += 1
            if count >= 3:
                break

extract_improved()
