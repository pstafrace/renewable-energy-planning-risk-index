import numpy as np
from re_pri_engine import REPRI_Engine

class ScenarioSimulator:
    def __init__(self, engine: REPRI_Engine):
        self.engine = engine

    def OWA_score(self, scores_array, scenario):
        """
        Applies Ordered Weighted Averaging proxy via percentiles 
        and risk-tolerance algorithms.
        """
        # Sort scores from lowest permittability to highest
        ordered_scores = np.sort(scores_array)
        
        if scenario == 'developer_optimistic':
            # Optimistic OWA: The developer believes they can mitigate average risks.
            # We skew the weight towards the higher end of the permittability distribution.
            # Using the 75th percentile as a proxy for the Optimistic score
            return np.percentile(ordered_scores, 75)
            
        elif scenario == 'regulator_pessimistic':
            # Pessimistic OWA: The regulator treats any friction as highly restrictive.
            # Skew weight towards the lower end.
            # Using the 25th percentile
            return np.percentile(ordered_scores, 25)
            
        else: # baseline mean
            return np.mean(ordered_scores)

    def run_risk_treatment(self, base_overlays, base_clauses, mitigations):
        """
        Risk Treatment Simulation for a site.
        mitigations: dict specifying overlays/clauses to 'remove' due to layout redesign
        e.g. {'remove_overlays': ['SLO']}
        """
        print(f"--- Base Baseline Configuration ---")
        base_scores = self.engine.simulate_project(base_overlays, base_clauses)
        base_opt = self.OWA_score(base_scores, 'developer_optimistic')
        base_pess = self.OWA_score(base_scores, 'regulator_pessimistic')
        
        print(f"Overlays: {base_overlays} | Clauses: {base_clauses}")
        print(f"Mean Permittability: {np.mean(base_scores):.2%}")
        print(f"Developer OWA (Optimistic) : {base_opt:.2%}")
        print(f"Regulator OWA (Pessimistic): {base_pess:.2%}")
        print(f"Permittability Gap: {abs(base_opt - base_pess):.2%}\n")
        
        # Apply mitigations
        treated_overlays = [o for o in base_overlays if o not in mitigations.get('remove_overlays', [])]
        treated_clauses = [c for c in base_clauses if c not in mitigations.get('remove_clauses', [])]
        
        print(f"--- Treated Configuration (Post-Design Mitigation) ---")
        treated_scores = self.engine.simulate_project(treated_overlays, treated_clauses)
        treated_opt = self.OWA_score(treated_scores, 'developer_optimistic')
        treated_pess = self.OWA_score(treated_scores, 'regulator_pessimistic')
        
        print(f"Overlays: {treated_overlays} | Clauses: {treated_clauses}")
        print(f"Mean Permittability: {np.mean(treated_scores):.2%}")
        print(f"Developer OWA (Optimistic) : {treated_opt:.2%}")
        print(f"Regulator OWA (Pessimistic): {treated_pess:.2%}")
        print(f"Permittability Gap: {abs(treated_opt - treated_pess):.2%}")
        
        # Return improvement
        improvement = np.mean(treated_scores) - np.mean(base_scores)
        print(f"\nNet Permittability Improvement: +{improvement:.2%}")
        return improvement

if __name__ == "__main__":
    engine = REPRI_Engine('friction_coefficients.json')
    simulator = ScenarioSimulator(engine)
    
    # Original Site: Has an SLO and BMO
    # Mitigation: Redesign turbine layout to push 500m back, dropping out of the SLO boundary.
    original_overlays = ['SLO', 'BMO']
    original_clauses = ['52.32']
    
    mitigations = {
        'remove_overlays': ['SLO']
    }
    
    simulator.run_risk_treatment(original_overlays, original_clauses, mitigations)
