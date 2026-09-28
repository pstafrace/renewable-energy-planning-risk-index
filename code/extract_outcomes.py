import csv
import re
import os

input_file = 'renewable_energy_cases_victoria.csv'
temp_file = 'temp.csv'

outcome_patterns = [
    r'(?i)no permit granted',
    r'(?i)(?<!no )permit granted',
    r'(?i)application dismissed',
    r'(?i)application granted',
    r'(?i)declaration refused',
    r'(?i)amend permit application',
    r'(?i)amend vcat application',
    r'(?i)appeal dismissed',
    r'(?i)appeal allowed'
]

with open(input_file, mode='r', encoding='utf-8') as infile, \
     open(temp_file, mode='w', encoding='utf-8', newline='') as outfile:
    
    reader = csv.DictReader(infile)
    fieldnames = reader.fieldnames
    if 'outcome' not in fieldnames:
        fieldnames = fieldnames + ['outcome']
    
    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
    writer.writeheader()
    
    for row in reader:
        summary = row.get('summary_text', '')
        outcomes = []
        for pattern in outcome_patterns:
            matches = re.findall(pattern, summary)
            if matches:
                 # Standardize capitalization based on the pattern
                 standard_outcome = pattern.replace('(?i)', '').replace('(?<!no )', '').capitalize()
                 if standard_outcome not in outcomes:
                     outcomes.append(standard_outcome)
        
        row['outcome'] = ', '.join(outcomes)
        writer.writerow(row)

os.replace(temp_file, input_file)
print("Successfully extracted outcomes to new column.")
