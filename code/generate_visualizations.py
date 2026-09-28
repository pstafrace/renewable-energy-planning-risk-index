import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
import seaborn as sns
from re_pri_engine import REPRI_Engine
from scenario_simulator import ScenarioSimulator
import shutil
import os

sns.set_theme(style="whitegrid")

OUTPUT_DIR = "../figures/"

# 1. Phase 1: Empirical Friction Bar Chart
def generate_phase1_chart(fdata):
    base_refusal = fdata['baseline']['refusal_rate'] * 100
    overlays = fdata['overlays']
    
    labels = ['State Baseline']
    rates = [base_refusal]
    colors = ['#1f77b4'] # Blue for baseline
    
    for ov, data in overlays.items():
        if data['count'] > 0:
            labels.append(f"{ov} Overlay")
            rates.append(data['refusal_rate'] * 100)
            colors.append('#d62728' if data['refusal_rate'] > base_refusal else '#ffcc00')
            
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(labels, rates, color=colors)
    ax.set_title("Phase 1: Empirical Refusal Rates by Spatial Constraint", fontsize=14, fontweight='bold')
    ax.set_ylabel("Refusal Probability (%)")
    ax.set_ylim(0, max(rates) + 15)
    
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
                
    plt.tight_layout()
    plt.savefig('phase1_friction_chart.png', dpi=300)
    shutil.copy('phase1_friction_chart.png', os.path.join(OUTPUT_DIR, 'phase1_friction_chart.png'))
    plt.close()

# 2. Phase 2: Monte Carlo Risk Distribution (Intersecting KDE plots) 
def generate_phase2_chart(engine):
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # We define multiple distinct constraint scenarios for the Monte Carlo to run permutations against
    scenarios = {
        'Baseline Model (Empty Land)': [],
        'Bushfire Management (BMO)': ['BMO'],
        'Environmental Significance (ESO)': ['ESO'],
        'Significant Landscape (SLO)': ['SLO'],
        'Heritage Topology (HO)': ['HO']
    }
    
    colors = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#d62728']
    
    for (label, overlays), color in zip(scenarios.items(), colors):
        res = engine.simulate_project(overlays=overlays, clauses=['52.32'], num_iterations=10000)
        dist = res * 100 # percentage permittability
        
        # Plot overlapping Kernel Density Estimates
        sns.kdeplot(dist, fill=True, alpha=0.35, label=label, color=color, ax=ax, linewidth=2)
        # Mark the topological mean
        mean_val = np.mean(dist)
        ax.axvline(mean_val, color=color, linestyle='dashed', alpha=0.8, linewidth=1.5)
    
    ax.set_title("Phase 2: Monte Carlo Topological Variance by Overlay", fontsize=15, fontweight='bold', pad=15)
    ax.set_xlabel("Predicted Likelihood of Approval (%)", fontsize=12)
    ax.set_ylabel("Probability Density (Frequency of Output)", fontsize=12)
    ax.legend(title='Spatial Constraints:', loc='upper right', frameon=True)
    
    plt.tight_layout()
    plt.savefig('phase2_monte_carlo.png', dpi=300)
    shutil.copy('phase2_monte_carlo.png', os.path.join(OUTPUT_DIR, 'phase2_monte_carlo.png'))
    plt.close()

# 3. Phase 3: OWA Regulatory vs Developer Perspectives
def generate_phase3_chart(engine):
    sim = ScenarioSimulator(engine)
    
    # Low Friction
    low_res = engine.simulate_project([], ['52.32'])
    low_mean = low_res.mean()
    low_dev = sim.OWA_score(low_res, "developer_optimistic")
    low_reg = sim.OWA_score(low_res, "regulator_pessimistic")
    
    # High Friction
    high_res = engine.simulate_project(['HO', 'SLO'], ['52.32'])
    high_mean = high_res.mean()
    high_dev = sim.OWA_score(high_res, "developer_optimistic")
    high_reg = sim.OWA_score(high_res, "regulator_pessimistic")
    
    labels = ['Low Friction Baseline', 'High Friction (HO & SLO)']
    
    dev_scores = [low_dev*100, high_dev*100]
    mean_scores = [low_mean*100, high_mean*100]
    reg_scores = [low_reg*100, high_reg*100]
    
    x = np.arange(len(labels))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    rects1 = ax.bar(x - width, dev_scores, width, label='Optimistic Developer Perspective', color='#2ca02c')
    rects2 = ax.bar(x, mean_scores, width, label='Actuarial Baseline (Mean)', color='#7f7f7f')
    rects3 = ax.bar(x + width, reg_scores, width, label='Pessimistic Regulator Perspective', color='#d62728')
    
    ax.set_title('Phase 3: OWA Risk Interpretation by Stakeholder Viewpoint', fontsize=14, fontweight='bold')
    ax.set_ylabel('Permittability Likelihood (%)')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(loc='upper right')
    
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), 
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)
                        
    autolabel(rects1)
    autolabel(rects2)
    autolabel(rects3)

    plt.tight_layout()
    plt.savefig('phase3_owa_scenarios.png', dpi=300)
    shutil.copy('phase3_owa_scenarios.png', os.path.join(OUTPUT_DIR, 'phase3_owa_scenarios.png'))
    plt.close()

def main():
    print("Loading empirical data...")
    with open('friction_coefficients.json', 'r') as f:
        fdata = json.load(f)
        
    print("Initializing RE-PRI Engine...")
    engine = REPRI_Engine('friction_coefficients.json')
    
    try:
        print("Generating Phase 1 Chart...")
        generate_phase1_chart(fdata)
        
        print("Generating Phase 2 Chart...")
        generate_phase2_chart(engine)
        
        print("Generating Phase 3 Chart...")
        generate_phase3_chart(engine)
        
        print("Successfully generated all visualizations.")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
