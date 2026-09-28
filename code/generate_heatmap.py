import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
import json
import matplotlib.pyplot as plt
import contextily as ctx
from re_pri_engine import REPRI_Engine

def generate_grid_polygons(xmin, ymin, xmax, ymax, spacing):
    """Generates a regular polygon grid across the bounding box bounding box."""
    polys = []
    x = xmin
    while x < xmax:
        y = ymin
        while y < ymax:
            polys.append(Polygon([(x, y), (x+spacing, y), (x+spacing, y+spacing), (x, y+spacing)]))
            y += spacing
        x += spacing
    return polys

def main():
    # Initialize Core Engine
    engine = REPRI_Engine('friction_coefficients.json')
    
    print("Loading Vicmap Geospatial Overlays...")
    overlays_df = gpd.read_file("geospatial data/PLANOVERLAY.geojson")
    overlays_df = overlays_df.to_crs(epsg=4326)
    
    def extract_overlay(code):
        c = str(code).upper()
        if c.startswith('HO'): return 'HO'
        if c.startswith('SLO'): return 'SLO'
        if c.startswith('BMO'): return 'BMO'
        if c.startswith('ESO'): return 'ESO'
        if c.startswith('VPO'): return 'VPO'
        return 'NONE'
    
    overlays_df['overlay_id'] = overlays_df['zone_code'].apply(extract_overlay)
    valid_overlays = overlays_df[overlays_df['overlay_id'] != 'NONE']
    
    print("Generating Vector Intersect Grid (2km resolution)...")
    # Coordinates tightly framing the Western Victoria REZ test area
    xmin, xmax = 142.1, 142.9
    ymin, ymax = -37.0, -36.2
    spacing = 0.02 # Approx 2km chunks
    grid_polys = generate_grid_polygons(xmin, ymin, xmax, ymax, spacing)
    
    grid_df = gpd.GeoDataFrame({'geometry': grid_polys}, crs="EPSG:4326")
    print(f"Grid populated with {len(grid_df)} distinct land parcels.")
    
    print("Processing computational intersections across grid...")
    scores = []
    combo_cache = {} # Use dynamic programming to speed up MC iterations
    
    for idx, cell in grid_df.iterrows():
        cell_geom = cell['geometry']
        intersects = valid_overlays[valid_overlays.intersects(cell_geom)]
        obs = list(set(intersects['overlay_id'].tolist()))
        
        cache_key = tuple(sorted(obs))
        if cache_key not in combo_cache:
            res = engine.simulate_project(overlays=list(cache_key), clauses=['52.32'], num_iterations=3000)
            combo_cache[cache_key] = res.mean()
                
        scores.append(combo_cache[cache_key] * 100) # Output as %
    
    grid_df['permittability'] = scores
    
    print("Rendering High-Resolution Viability Heatmap with Urban Context...")
    fig, ax = plt.subplots(1, 1, figsize=(14, 12))
    
    # We use a Red-Yellow-Green (RdYlGn) colormap. Green = Highly Permittable, Red = Toxic
    # Alpha down to 0.5 so we can read the town names
    grid_df.plot(column='permittability', ax=ax, cmap='RdYlGn', legend=True, alpha=0.55,
                 edgecolor='none', linewidth=0,
                 legend_kwds={'label': "RE-PRI Likelihood of Approval (%)"})
    
    # Optional context borders (very light)
    valid_overlays.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.3, alpha=0.2)
    
    # Add beautiful context map with town names underneath!
    ctx.add_basemap(ax, crs=grid_df.crs.to_string(), source=ctx.providers.CartoDB.Positron)
    
    ax.set_title("RE-PRI: Development Permittability Heatmap (Western VIC REZ Model)", fontsize=16, pad=15)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    
    out_file = "permittability_heatmap.png"
    plt.savefig(out_file, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"=========================================")
    print(f"SUCCESS! Heatmap saved locally to: {out_file}")
    print(f"=========================================")

if __name__ == "__main__":
    main()
