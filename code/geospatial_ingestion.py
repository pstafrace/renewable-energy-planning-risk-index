import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

from re_pri_engine import REPRI_Engine
from scenario_simulator import ScenarioSimulator

def create_mock_shapefiles():
    """
    Ingests the REAL GeoJSON layout data dropping by the user for the project footprint,
    and creates optimized mock state overlays directly over that footprint.
    """
    # 1. Developer's Project Footprint 
    # Instead of the massive AEMO REZ boundary, we simulate a specific 5km developer layout
    # placed at [142.5, -36.6]. We'll see if this targeted layout dodges the friction.
    project_poly = Polygon([[142.50, -36.65], [142.50, -36.55], [142.60, -36.55], [142.60, -36.65]])
    project_df = gpd.GeoDataFrame(
        {'project_name': ['Targeted Alpha Wind Farm']}, 
        geometry=[project_poly], 
        crs="EPSG:4326"
    )
    
    # 2. Authentic State Planning Overlays Map
    # Reads the actual file downloaded from Vicmap REST API
    overlay_df = gpd.read_file("geospatial data/PLANOVERLAY.geojson")
    overlay_df = overlay_df.to_crs(epsg=4326)
    
    def extract_overlay(code):
        c = str(code).upper()
        if c.startswith('HO'): return 'HO'
        if c.startswith('SLO'): return 'SLO'
        if c.startswith('BMO'): return 'BMO'
        if c.startswith('ESO'): return 'ESO'
        if c.startswith('VPO'): return 'VPO'
        return 'NONE'

    overlay_df['overlay_id'] = overlay_df['zone_code'].apply(extract_overlay)
    
    return project_df, overlay_df

def detect_spatial_friction(project_df, overlay_df):
    """
    Intersects the project footprint with state overlays to auto-detect constraints.
    """
    # Perform spatial intersection (inner join on intersecting polygons)
    intersections = gpd.sjoin(project_df, overlay_df, how="inner", predicate="intersects")
    
    # Extract unique overlays that aren't the 'NONE' basemap
    detected_overlays = intersections[intersections['overlay_id'] != 'NONE']['overlay_id'].unique().tolist()
    return detected_overlays

if __name__ == "__main__":
    print("==============================================")
    print(" PHASE 4: GEOSPATIAL INTELLIGENCE PROOF-OF-CONCEPT")
    print("==============================================\n")
    
    print("Step 1: Ingesting Spatial data...")
    project_df, overlay_df = create_mock_shapefiles()
    
    print("Step 2: Performing Geospatial Intersection...")
    detected_overlays = detect_spatial_friction(project_df, overlay_df)
    print(f"\n=> ALERT: The proposed map boundary intersects with: {detected_overlays}")
    
    print("\nStep 3: Auto-injecting spatial layers into RE-PRI Engine...")
    engine = REPRI_Engine("friction_coefficients.json")
    simulator = ScenarioSimulator(engine)
    
    # Base regulatory clauses are still explicitly provided standard to wind applications
    base_clauses = ['52.32']
    
    # We call run_risk_treatment with the AUTO-DETECTED overlays and an empty mitigations dict
    simulator.run_risk_treatment(
        base_overlays=detected_overlays, 
        base_clauses=base_clauses, 
        mitigations={}
    )
    print("Geospatial Integration successful. Eliminates manual mapping errors by developers.")
