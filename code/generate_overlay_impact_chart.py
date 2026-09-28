import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import shutil
import os
from re_pri_engine import REPRI_Engine

sns.set_theme(style="whitegrid")

OUTPUT_DIR = "../figures/"

def generate_overlay_impact_chart():
    # Intialize the RE-PRI framework utilizing our new Scikit-Learn Logistic Regression backend
    engine = REPRI_Engine('ml_friction_coefficients.json')
    
    # Establish generic benchmark
    base_scores = engine.simulate_project([], ['52.32'], num_iterations=10000)
    base_mean = np.mean(base_scores) * 100
    
    overlays = ['BMO', 'ESO', 'VPO', 'SLO', 'HO']
    overlay_names = {
        'BMO': 'Bushfire Management Overlay (BMO)\n[Arg: Fire Risk]',
        'ESO': 'Environmental Significance Overlay (ESO)\n[Arg: Flora/Fauna]',
        'VPO': 'Vegetation Protection Overlay (VPO)\n[Arg: Flora/Fauna]',
        'SLO': 'Significant Landscape Overlay (SLO)\n[Arg: Visual Amenity]',
        'HO':  'Heritage Overlay (HO)\n[Arg: Heritage]'
    }
    
    results = {}
    for o in overlays:
        scores = engine.simulate_project([o], ['52.32'], num_iterations=10000)
        results[o] = np.mean(scores) * 100
        
    labels = ['Baseline (Clause 52.32 Only)'] + [overlay_names[o] for o in overlays]
    values = [base_mean] + [results[o] for o in overlays]
    
    # Sort values descending (Most likely to be approved at top)
    sorted_pairs = sorted(zip(labels, values), key=lambda x: x[1], reverse=False)
    sorted_labels = [p[0] for p in sorted_pairs]
    sorted_values = [p[1] for p in sorted_pairs]
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Color severity
    colors = []
    for label, val in zip(sorted_labels, sorted_values):
        if 'Baseline' in label:
            colors.append('#1f77b4') # Blue
        elif val > 30:
            colors.append('#2ca02c') # Green (Low structural friction)
        elif val > 15:
            colors.append('#ff7f0e') # Orange (Medium friction)
        else:
            colors.append('#d62728') # Red (Severe algorithmic friction)
            
    bars = ax.barh(sorted_labels, sorted_values, color=colors)
    
    ax.set_title("Causal Impact of Specific Planning Overlays on Permittability", fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel("Mathematical Likelihood of Tribunal Approval (%)", fontsize=12)
    ax.set_xlim(0, max(sorted_values) + 15) # Provide padding for the text
    
    # Append percent readouts
    for bar in bars:
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                f'{bar.get_width():.1f}%', va='center', fontweight='bold', fontsize=11)
                
    plt.tight_layout()
    plt.savefig('overlay_impact_chart.png', dpi=300)
    shutil.copy('overlay_impact_chart.png', os.path.join(OUTPUT_DIR, 'overlay_impact_chart.png'))
    print("Overlay impact chart generated securely.")

if __name__ == "__main__":
    generate_overlay_impact_chart()
