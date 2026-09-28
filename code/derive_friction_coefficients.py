import csv
import json
from collections import defaultdict

def analyze_friction_coefficients(csv_path, output_json="friction_coefficients.json"):
    total_cases = 0
    refusals = 0
    delays = []
    
    # Track stats by overlay and by clause
    # structure: { key: {'count': 0, 'refusals': 0, 'delays': []} }
    overlay_stats = defaultdict(lambda: {'count': 0, 'refusals': 0, 'delays': []})
    clause_stats = defaultdict(lambda: {'count': 0, 'refusals': 0, 'delays': []})
    
    # We will treat "Permit refused", "Application refused", "Appeal dismissed" etc. as negative outcomes (refusals).
    negative_outcomes = ['refused', 'dismissed', 'set aside', 'no permit']
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_cases += 1
            
            outcome = row.get('outcome', '').lower()
            is_refusal = any(neg in outcome for neg in negative_outcomes)
            delay_str = row.get('planning_delay_days')
            delay_val = int(delay_str) if (delay_str and delay_str.strip()) else None
            
            if is_refusal:
                refusals += 1
            if delay_val is not None:
                delays.append(delay_val)
                
            # Process Overlays
            overlays = [o.strip() for o in row.get('spatial_overlays', '').split('|') if o.strip()]
            for o in overlays:
                overlay_stats[o]['count'] += 1
                if is_refusal:
                    overlay_stats[o]['refusals'] += 1
                if delay_val is not None:
                    overlay_stats[o]['delays'].append(delay_val)
                    
            # Process Clauses
            clauses = [c.strip() for c in row.get('regulatory_clauses', '').split('|') if c.strip()]
            for c in clauses:
                clause_stats[c]['count'] += 1
                if is_refusal:
                    clause_stats[c]['refusals'] += 1
                if delay_val is not None:
                    clause_stats[c]['delays'].append(delay_val)

    # Compile Results
    results = {
        'baseline': {
            'total_cases': total_cases,
            'refusal_rate': (refusals / total_cases) if total_cases > 0 else 0.0,
            'avg_delay_days': sum(delays)/len(delays) if delays else 0.0
        },
        'overlays': {},
        'clauses': {}
    }
    
    for key, stats in overlay_stats.items():
        results['overlays'][key] = {
            'count': stats['count'],
            'refusal_rate': (stats['refusals'] / stats['count']),
            'avg_delay_days': sum(stats['delays'])/len(stats['delays']) if stats['delays'] else None
        }

    for key, stats in clause_stats.items():
        # Only keep clauses that occur more than a few times to avoid noise
        if stats['count'] > 2:
            results['clauses'][key] = {
                'count': stats['count'],
                'refusal_rate': (stats['refusals'] / stats['count']),
                'avg_delay_days': sum(stats['delays'])/len(stats['delays']) if stats['delays'] else None
            }

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
        
    print(f"Analysis complete. Base refusal rate: {results['baseline']['refusal_rate']:.1%}")
    print(f"Extracted patterns for {len(results['overlays'])} overlays and {len(results['clauses'])} common clauses.")
    print(f"Results saved to {output_json}")

if __name__ == '__main__':
    # Using the dataset created by extract_v3.py
    analyze_friction_coefficients('longitudinal_analysis_dataset.csv')
