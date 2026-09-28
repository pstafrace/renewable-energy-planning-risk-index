import csv
import re
from docx import Document

input_file = 'austlii_export.docx'
output_file = 'renewable_energy_cases_victoria.csv'

doc = Document(input_file)
cases_data = []

current_case = {}
for p in doc.paragraphs:
    text = p.text.strip()
    if not text: continue
    
    # Look for a citation pattern like [YYYY] VCAT NNN or [YYYY] VSC NNN
    if re.search(r'\[20\d{2}\] (VCAT|VSC) \d+', text) and 'v' in text.lower():
        # Save previous case if it exists
        if current_case and 'case_name' in current_case:
            cases_data.append(current_case)
            
        current_case = {
            'case_name': text,
            'url': '', # We might not have URLs in a raw export, but we can try to reconstruct or leave empty
            'summary_text': ''
        }
        
        # Super basic URL reconstruction attempt based on case name
        # e.g. "Smith v Jones [2024] VCAT 123" -> https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/vic/VCAT/2024/123.html
        match = re.search(r'\[(20\d{2})\] (VCAT|VSC) (\d+)', text)
        if match:
            year, court, num = match.groups()
            current_case['url'] = f"https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/vic/{court}/{year}/{num}.html"
            
    elif current_case:
        # Append to summary text
        current_case['summary_text'] += text + " "

# Add the final case
if current_case and 'case_name' in current_case:
    cases_data.append(current_case)

print(f"Extracted {len(cases_data)} cases from the document.")

if len(cases_data) > 0:
    existing_cases = []
    try:
        with open(output_file, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            for row in reader:
                existing_cases.append(row)
    except FileNotFoundError:
        fieldnames = ['case_name', 'url', 'summary_text', 'outcome']

    # Combine and save
    with open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
        if 'outcome' not in fieldnames:
            fieldnames.append('outcome')
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing_cases)
        
        for case in cases_data:
            if 'outcome' not in case:
                case['outcome'] = ''
            writer.writerow(case)
            
    print(f"Appended extracted cases to CSV.")
else:
    print("Could not extract any cases. The document structure might be different.")
    
    # Print the first few paragraphs to see what we're working with
    print("\n--- Document Preview ---")
    for p in doc.paragraphs[:10]:
        print(p.text)
