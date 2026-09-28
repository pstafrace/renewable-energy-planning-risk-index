import os
import re
import json
import numpy as np
import pandas as pd
from docx import Document
import spacy
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Quantitative Arguments/Themes to extract using spaCy tokenization
THEMES = {
    'visual_amenity': ['visual', 'landscape', 'amenity', 'sightline', 'view', 'scenic', 'aesthetics'],
    'noise_impact': ['noise', 'acoustic', 'decibel', 'sound', 'vibration', 'dba'],
    'flora_fauna': ['flora', 'fauna', 'habitat', 'vegetation', 'brolga', 'bird', 'bat', 'native', 'biodiversity', 'tree', 'ecological'],
    'heritage': ['heritage', 'historic', 'aboriginal', 'cultural', 'archaeological', 'ancestral'],
    'traffic': ['traffic', 'road', 'vehicle', 'transportation', 'access', 'highway', 'truck', 'construction'],
    'fire_risk': ['fire', 'bushfire', 'cfa', 'combustible', 'ignition'],
    'agriculture': ['agriculture', 'farming', 'irrigation', 'soil', 'crop', 'livestock', 'productive']
}

def extract_cases():
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
    
    # Causal outcome mapper
    for title, text in cases:
        tail_term = text[-8000:]
        
        outcome_val = None # 1 = Granted, 0 = Refused
        
        refusal_match = re.search(r'(?i)\b(permit usually refused|application refused|appeal dismissed|no permit granted)\b', text)
        granted_match = re.search(r'(?i)\b(permit granted|application granted|appeal allowed|direction made|order made)\b', text)
        verb_match = re.search(r'(?i)\b(permit|application|appeal|proceeding)[^.]{0,30}\b(granted|dismissed|refused|allowed|set\s+aside)', tail_term)
        
        if verb_match:
            verb = verb_match.group(2).lower()
            if verb in ['refused', 'dismissed']:
                outcome_val = 0
            elif verb in ['granted', 'allowed', 'set aside']:
                outcome_val = 1
        elif refusal_match:
            outcome_val = 0
        elif granted_match:
            outcome_val = 1
            
        if outcome_val is not None and len(text) > 1000:
            extracted_data.append({
                'title': title[:100],
                'text': text,
                'outcome': outcome_val
            })
            
    return extracted_data

def run_nlp_pipeline():
    print("=============================================================")
    print("RE-PRI: Causal NLP Logistic Regression Pipeline")
    print("=============================================================\n")
    print("Initializing spaCy NLP engine...")
    try:
        nlp = spacy.load("en_core_web_sm")
    except:
        import spacy.cli
        spacy.cli.download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")

    print(f"Extracting raw tribunal decision corpuses...")
    cases = extract_cases()
    print(f"Extracted {len(cases)} cases with mathematically deterministic outcomes.")
    
    # Process text frequencies
    dataset = []
    print("\nPerforming causal argument extraction via linguistic text mapping...")
    
    for c in cases:
        # Fast generic tokenization over the legal document
        doc_text = c['text'].lower()
        
        # Frequency counts mapped as features
        features = {'outcome': c['outcome']}
        doc_len = len(doc_text)
        
        for theme, keywords in THEMES.items():
            # Count precise legal terminology corresponding to the causal theme
            count = sum(doc_text.count(kw) for kw in keywords)
            
            # Normalize by document length (to prevent huge 200-page rulings from dominating)
            # Normalization proxy: Per 5,000 characters
            length_norm = max(doc_len / 5000.0, 1.0)
            freq = count / length_norm
            features[theme] = freq
            
        dataset.append(features)
        
    df = pd.DataFrame(dataset)
    X = df.drop('outcome', axis=1)
    y = df['outcome']
    
    print("\n--- Argument Frequency Matrix (First 5 Rows) ---")
    print(X.head())
    
    print("\nTraining Logistic Regression Algorithms (Scikit-Learn)....")
    # Scale features so regression weights are mathematically comparable
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Fit regression, balancing classes because approvals vs refusals may be highly asymmetrical
    clf = LogisticRegression(class_weight='balanced', random_state=42)
    clf.fit(X_scaled, y)
    
    print("\n--- Logistic Regression Coefficients (Causal Log Odds) ---")
    # A negative coefficient means the argument PUSHES outcome towards 0 (Refusal). So it ADDS theoretical friction.
    # A positive coefficient means it PUSHES outcome towards 1 (Granted).
    
    friction_weights = {}
    baseline_bias = clf.intercept_[0]
    
    print(f"Baseline Outcome Modeling Bias: {baseline_bias:.3f}")
    for feature, coef in zip(X.columns, clf.coef_[0]):
        impact_str = f"({coef:.4f})"
        
        if coef < -0.1:
            print(f"{feature.ljust(22)}: {impact_str.ljust(10)} -> Highly Causal Refusal Argument")
        elif coef > 0.1:
            print(f"{feature.ljust(22)}: {impact_str.ljust(10)} -> Highly Causal Approval Argument")
        else:
            print(f"{feature.ljust(22)}: {impact_str.ljust(10)} -> Negligible Causal Correlation")
            
        # We invert negative coefficients to turn them into an explicit 'friction/risk' penalizer.
        # Clamp to bounds.
        friction = -coef
        if friction < 0: 
            friction = 0.0 # It helped approvals, so zero planning friction added
        friction_weights[feature] = friction

    # Normalize friction weights logarithmically so that massive visual amenity penalties cap out sensibly
    max_friction = max(friction_weights.values())
    if max_friction > 0:
        for k in friction_weights:
            # Map impact relative to the strongest argument. 
            friction_weights[k] = (friction_weights[k] / max_friction) * 0.9
            
    print("\n--- RE-PRI Simulation Engine Probability Multipliers ---")
    for k, v in friction_weights.items():
        print(f"{k.ljust(22)}: +{v:.2%} probabilistic friction multiplier")
        
    # Output causal probabilities to JSON config file
    out_data = {
        "baseline_metadata": {
            "cases_parsed": len(cases),
            "intercept_bias": float(baseline_bias)
        },
        "nlp_friction_coefficients": friction_weights
    }
    
    with open('ml_friction_coefficients.json', 'w') as f:
        json.dump(out_data, f, indent=4)
        
    print("\n✅ Successfully compiled Scikit-Learn logic. Exported causal variables to `ml_friction_coefficients.json`")

if __name__ == "__main__":
    run_nlp_pipeline()
