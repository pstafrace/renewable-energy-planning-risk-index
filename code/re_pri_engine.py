import json
import numpy as np

# Spatial-to-Argument Deterministic NLP Mapper
# Maps a map boundary overlay back to its fundamental legal framework argument.
OVERLAY_ARGUMENT_MAP = {
    'HO': ['heritage'],
    'SLO': ['visual_amenity'],
    'ESO': ['flora_fauna'],
    'VPO': ['flora_fauna'],
    'BMO': ['fire_risk']
}

CLAUSE_ARGUMENT_MAP = {
    '52.32': ['visual_amenity', 'noise_impact'], # Wind facility naturally triggers visual & noise argument contexts
    '13.10': ['fire_risk'] 
}

class REPRI_Engine:
    def __init__(self, friction_json_path):
        # We implicitly intercept old system routing to instantly deploy the causal ML pipeline
        if 'ml_' not in friction_json_path:
            friction_json_path = 'ml_friction_coefficients.json'
            
        with open(friction_json_path, 'r') as f:
            self.data = json.load(f)
            
        bias = self.data['baseline_metadata']['intercept_bias']
        # Convert baseline Log-Odds bias into probability approximation (Sigmoid)
        self.base_risk = 1.0 / (1.0 + np.exp(-bias))
        
        self.ml_weights = self.data['nlp_friction_coefficients']
        
        # Expert priors (AHP derived). 
        self.ahp_weights = {
            'visual_amenity': 0.6,
            'noise_impact': 0.3,
            'flora_fauna': 0.7,
            'heritage': 0.8,
            'traffic': 0.4,
            'fire_risk': 0.8
        }
        
    def simulate_project(self, overlays, clauses, num_iterations=10000):
        """
        Runs a Monte Carlo simulation (n=num_iterations).
        Returns a numpy array of permittability scores (0.0 to 1.0).
        """
        results = []
        for _ in range(num_iterations):
            # 1. Base regulatory friction: Sample from normal distribution
            risk = np.random.normal(self.base_risk, 0.05)
            
            # Aggregate all triggered ML arguments based on spatial layout mapped to the footprint
            triggered_args = set()
            for o in overlays:
                if o in OVERLAY_ARGUMENT_MAP:
                    triggered_args.update(OVERLAY_ARGUMENT_MAP[o])
            for c in clauses:
                if c in CLAUSE_ARGUMENT_MAP:
                    triggered_args.update(CLAUSE_ARGUMENT_MAP[c])
            
            # 2. Add Causal Friction deduced from the Logistic Regression
            for arg in triggered_args:
                ml_coefficient = self.ml_weights.get(arg, 0.0)
                ahp = self.ahp_weights.get(arg, 0.5)
                
                # Combine Scikit-Learn logic natively alongside our AHP expert priors
                combined_weight = (ml_coefficient * 0.8) + (ahp * 0.2)
                
                # Add to cumulative risk using a triangular distribution to model variance
                added_friction = np.random.triangular(0, combined_weight * 0.5, combined_weight)
                risk += added_friction
                
            # Clamp risk to be between 0 and 1
            risk = max(0.0, min(1.0, risk))
            
            # Permittability is the inverse of risk
            permittability = 1.0 - risk
            results.append(permittability)
            
        return np.array(results)

if __name__ == "__main__":
    np.random.seed(42) # For reproducible testing
    engine = REPRI_Engine('ml_friction_coefficients.json')
    
    # Test High-Risk Project
    high_risk_overlays = ['HO', 'SLO']
    high_risk_clauses = ['52.32']
    high_scores = engine.simulate_project(high_risk_overlays, high_risk_clauses)
    
    print("--- HIGH RISK PROJECT (Heritage & Landscape Driven) ---")
    print(f"Overlays: {high_risk_overlays}, Clauses: {high_risk_clauses}")
    print(f"Mean Permittability: {np.mean(high_scores):.2%}")
    print(f"95% CI: [{np.percentile(high_scores, 2.5):.2%}, {np.percentile(high_scores, 97.5):.2%}]\n")
    
    # Test Low-Risk Project
    low_risk_overlays = ['BMO']
    low_risk_clauses = ['52.32']
    low_scores = engine.simulate_project(low_risk_overlays, low_risk_clauses)
    
    print("--- LOW RISK PROJECT (Fire Driven) ---")
    print(f"Overlays: {low_risk_overlays}, Clauses: {low_risk_clauses}")
    print(f"Mean Permittability: {np.mean(low_scores):.2%}")
    print(f"95% CI: [{np.percentile(low_scores, 2.5):.2%}, {np.percentile(low_scores, 97.5):.2%}]\n")
