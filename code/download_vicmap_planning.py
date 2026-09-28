#!/usr/bin/env python3
"""
RE-PRI Model: Vicmap Planning Overlays & Zones Downloader
=========================================================
Primary:   ArcGIS Feature Server (Vicmap Planning REST API)
           https://services-ap1.arcgis.com/P744lA0wf4LlBZ84/ArcGIS/rest/services/Vicmap_Planning/FeatureServer
Fallback:  OGC WFS (GeoServer)
           https://opendata.maps.vic.gov.au/geoserver/wfs

Data:      plan_overlay  — Planning Scheme Overlay Polygon (Heritage, Bushfire, Flood, etc.)
           plan_zone     — Planning Scheme Zone Polygon (Residential, Industrial, Rural, etc.)

License:   Creative Commons Attribution 4.0 International
Publisher: Department of Transport and Planning, Victoria
Catalog:   https://discover.data.vic.gov.au/dataset/vicmap-planning-planning-scheme-overlay-polygon
           https://discover.data.vic.gov.au/dataset/vicmap-planning-planning-scheme-zone-polygon
Last update: 9 April 2026 (updated weekly)

Usage:
    python3 download_vicmap_planning.py

Output:
    geospatial data/PLANOVERLAY.geojson
    geospatial data/PLANZONE.geojson
    geospatial data/vicmap_planning_metadata.json
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
from datetime import datetime, timezone

ssl._create_default_https_context = ssl._create_unverified_context

# ── Configuration ─────────────────────────────────────────────────────────────

OUTPUT_DIR = "geospatial data"

# Primary: ArcGIS Feature Server (Vicmap Planning REST API — Data.Vic catalog ID: vicmap-planning-api)
ARCGIS_BASE = (
    "https://services-ap1.arcgis.com/P744lA0wf4LlBZ84"
    "/ArcGIS/rest/services/Vicmap_Planning/FeatureServer"
)

# Fallback: OGC WFS (GeoServer)
WFS_BASE = "https://opendata.maps.vic.gov.au/geoserver/wfs"

# ArcGIS layer IDs (discovered from FeatureServer metadata)
ARCGIS_LAYERS = {
    "plan_overlay": {
        "keyword":     "overlay",          
        "description": "Vicmap Planning – Planning Scheme Overlay Polygon",
        "output_base": "PLANOVERLAY",
    },
    "plan_zone": {
        "keyword":     "zone",
        "description": "Vicmap Planning – Planning Scheme Zone Polygon",
        "output_base": "PLANZONE",
    },
}

# WFS layer names (fallback)
WFS_LAYERS = {
    "plan_overlay": {
        "typename":    "open-data-platform:plan_overlay",
        "description": "Vicmap Planning – Planning Scheme Overlay Polygon",
        "output_base": "PLANOVERLAY",
    },
    "plan_zone": {
        "typename":    "open-data-platform:plan_zone",
        "description": "Vicmap Planning – Planning Scheme Zone Polygon",
        "output_base": "PLANZONE",
    },
}

PAGE_SIZE = 2000        
WFS_PAGE_SIZE = 1000    

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 RE-PRI-Model/1.0 VicPlanningResearch"
    ),
    "Accept": "application/json, text/plain, */*",
}

def fetch(url, timeout=180):
    req = urllib.request.Request(url, headers=HEADERS)
    last_err = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return raw.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 503, 502):
                wait = 5 * attempt
                print(f"    HTTP {e.code} — waiting {wait}s before retry {attempt}/3 ...", flush=True)
                time.sleep(wait)
            else:
                raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            print(f"    Network error: {e} — retry {attempt}/3 ...", flush=True)
            time.sleep(3)
    raise last_err

def progress(current, total, width=40):
    filled = int(width * current / max(total, 1))
    bar = "█" * filled + "░" * (width - filled)
    pct = 100 * current / max(total, 1)
    print(f"\r  [{bar}] {pct:5.1f}%  {current:,}/{total:,} features", end="", flush=True)

def get_arcgis_layers(base_url):
    url = f"{base_url}?f=json"
    data = fetch(url, timeout=30)
    if isinstance(data, str):
        raise ValueError(f"Expected JSON from FeatureServer, got: {data[:200]}")
    layers = data.get("layers", [])
    print(f"  FeatureServer has {len(layers)} layer(s):")
    for l in layers:
        print(f"    ID {l['id']}: {l['name']}")
    return layers

def get_arcgis_count(base_url, layer_id):
    params = {
        "where": "1=1", "returnCountOnly": "true", "f": "json",
        "geometryType": "esriGeometryEnvelope",
        "geometry": "142.0,-37.0,143.0,-36.2",
        "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"
    }
    url = f"{base_url}/{layer_id}/query?{urllib.parse.urlencode(params)}"
    data = fetch(url, timeout=30)
    return data.get("count", 0)

def download_arcgis_layer(base_url, layer_id, layer_name, output_path):
    print(f"  Using ArcGIS Feature Server (layer {layer_id}: {layer_name})")
    total = get_arcgis_count(base_url, layer_id)
    print(f"  Feature count: {total:,}")

    features = []
    offset = 0
    page = 1

    while True:
        params = {
            "where": "1=1", "outFields": "*", "returnGeometry": "true",
            "geometryPrecision": "6", "outSR": "4326", "f": "geojson",
            "resultOffset": str(offset), "resultRecordCount": str(PAGE_SIZE),
            "geometryType": "esriGeometryEnvelope",
            "geometry": "142.0,-37.0,143.0,-36.2",
            "inSR": "4326", "spatialRel": "esriSpatialRelIntersects"
        }
        url = f"{base_url}/{layer_id}/query?{urllib.parse.urlencode(params)}"

        try:
            data = fetch(url, timeout=180)
        except Exception as e:
            print(f"\n    Page {page} error: {e}")
            break

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                print(f"\n    Unexpected response format on page {page}")
                break

        batch = data.get("features", [])
        if not batch:
            break

        features.extend(batch)
        progress(len(features), total)

        exceeded = data.get("exceededTransferLimit", False)
        if not exceeded and len(batch) < PAGE_SIZE:
            break

        offset += PAGE_SIZE
        page += 1
        time.sleep(0.3)

    print() 

    if not features:
        print("  WARNING: No features downloaded.")
        return None

    fc = {
        "type": "FeatureCollection",
        "name": os.path.splitext(os.path.basename(output_path))[0],
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }

    print(f"  Writing {len(features):,} features → {output_path} ...", end=" ", flush=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    mb = os.path.getsize(output_path) / 1_048_576
    print(f"done ({mb:.1f} MB)")
    return output_path

def wfs_url(typename, start=0, count=WFS_PAGE_SIZE):
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": typename, "outputFormat": "application/json",
        "startIndex": str(start), "count": str(count), "srsName": "EPSG:4326",
    }
    return WFS_BASE + "?" + urllib.parse.urlencode(params)

def wfs_hit_count(typename):
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": typename, "resultType": "hits", "outputFormat": "application/json",
    }
    try:
        data = fetch(WFS_BASE + "?" + urllib.parse.urlencode(params), timeout=30)
        return data.get("totalFeatures") or data.get("numberMatched")
    except Exception:
        return None

def download_wfs_layer(typename, output_path, description):
    print(f"  Using WFS fallback ({typename})")
    total = wfs_hit_count(typename)
    print(f"  Feature count: {f'{total:,}' if total else 'unknown'}")

    features, page, start, crs = [], 1, 0, None

    while True:
        url = wfs_url(typename, start=start, count=WFS_PAGE_SIZE)
        print(f"  Page {page}: [{start}–{start + WFS_PAGE_SIZE - 1}] ...", end=" ", flush=True)
        try:
            data = fetch(url, timeout=180)
        except urllib.error.HTTPError as e:
            print(f"HTTP {e.code} {e.reason} — stopping.")
            break
        except Exception as e:
            print(f"Error: {e} — stopping.")
            break

        batch = data.get("features", [])
        print(f"{len(batch)} features")
        if not batch:
            break
        if page == 1:
            crs = data.get("crs")
        features.extend(batch)
        if len(batch) < WFS_PAGE_SIZE:
            break
        start += WFS_PAGE_SIZE
        page += 1
        time.sleep(0.4)

    if not features:
        print("  WARNING: 0 features downloaded.")
        return None

    fc = {
        "type": "FeatureCollection",
        "name": os.path.splitext(os.path.basename(output_path))[0],
        "crs": crs or {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    print(f"  Writing {len(features):,} features → {output_path} ...", end=" ", flush=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(fc, f)
    mb = os.path.getsize(output_path) / 1_048_576
    print(f"done ({mb:.1f} MB)")
    return output_path

def download_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nOutput directory: {OUTPUT_DIR}\n")

    arcgis_available = False
    arcgis_layer_map = {}

    print("Probing ArcGIS Feature Server ...")
    try:
        layers = get_arcgis_layers(ARCGIS_BASE)
        arcgis_available = True
        for key, cfg in ARCGIS_LAYERS.items():
            kw = cfg["keyword"].lower()
            for l in layers:
                if kw in l["name"].lower():
                    arcgis_layer_map[key] = {"id": l["id"], "name": l["name"]}
                    break
        print(f"  ArcGIS Feature Server reachable. Matched layers: {arcgis_layer_map}")
    except Exception as e:
        print(f"  ArcGIS Feature Server unavailable: {e}")
        print("  Will fall back to WFS.")

    wfs_available = False
    if not arcgis_available or len(arcgis_layer_map) < len(ARCGIS_LAYERS):
        print("\nProbing WFS endpoint ...")
        caps_url = f"{WFS_BASE}?service=WFS&version=2.0.0&request=GetCapabilities"
        try:
            req = urllib.request.Request(caps_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as r:
                snippet = r.read(200).decode("utf-8", errors="replace")
            wfs_available = True
            print(f"  WFS endpoint reachable. Response: {snippet[:80]}...")
        except Exception as e:
            print(f"  WFS endpoint unavailable: {e}")

    downloaded = {}

    for key, cfg in ARCGIS_LAYERS.items():
        out_path = os.path.join(OUTPUT_DIR, cfg["output_base"] + ".geojson")
        print(f"\n{'='*60}")
        print(f"Downloading: {cfg['description']}")
        print(f"Output:      {out_path}")

        result = None
        if arcgis_available and key in arcgis_layer_map:
            lyr = arcgis_layer_map[key]
            try:
                result = download_arcgis_layer(ARCGIS_BASE, lyr["id"], lyr["name"], out_path)
            except Exception as e:
                print(f"  ArcGIS download failed: {e}")
                print("  Falling back to WFS ...")

        if result is None and wfs_available:
            wfs_cfg = WFS_LAYERS.get(key)
            if wfs_cfg:
                try:
                    result = download_wfs_layer(wfs_cfg["typename"], out_path, cfg["description"])
                except Exception as e:
                    print(f"  WFS download also failed: {e}")

        if result is None:
            print(f"\n  FAILED: Could not download {key} from any source.")
        else:
            downloaded[key] = result

    return downloaded

def save_metadata(downloaded):
    meta = {
        "title": "Vicmap Planning – Spatial Data Download",
        "files": {
            k: {
                "path": v,
                "size_mb": round(os.path.getsize(v) / 1_048_576, 2),
            }
            for k, v in downloaded.items()
        }
    }
    path = os.path.join(OUTPUT_DIR, "vicmap_planning_metadata.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return path

def main():
    downloaded = download_all()
    if downloaded: save_metadata(downloaded)

if __name__ == "__main__":
    main()
