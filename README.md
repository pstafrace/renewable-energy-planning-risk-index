# Renewable Energy Planning Risk Index (RE-PRI)

**A probabilistic model for feasibility assessment and risk mitigation in the Australian energy transition**

Capstone project for ARCH1411, Master of Urban Planning and Environment, RMIT University (2026). Patrick Stafrace.

RE-PRI estimates the likelihood that a renewable energy project in Victoria will face planning refusal or delay. It combines:

1. **Regulatory friction coding.** Victorian planning and VCAT decisions (sourced from AustLII) are scraped and coded to derive empirical refusal rates by planning overlay and clause.
2. **NLP causal coefficients.** spaCy-based extraction of the arguments raised in each decision (visual amenity, noise, flora and fauna, heritage, fire risk and so on) feeds a logistic model of friction.
3. **Hybrid weighting and Monte Carlo simulation.** NLP coefficients are blended with AHP expert priors, then simulated (n = 10,000) under developer and regulator scenarios using ordered weighted averaging (OWA).
4. **Spatial application.** Vicmap Planning zones and overlays are intersected with AEMO Renewable Energy Zone boundaries to map permittability across Western Victoria.

The full write-up is in [`report/`](report/RE-PRI_Final_Report_Stafrace.pdf).

## Repository layout

```
code/      Python scripts plus the CSV and JSON files they read and write
figures/   Output charts and the permittability heatmap
report/    Final project report (PDF)
```

Key scripts in `code/`:

| Script | Purpose |
| --- | --- |
| `scrape_cases.py`, `parse_word_export.py` | Collect Victorian planning cases from AustLII |
| `extract_v3.py`, `extract_regex_cases.py`, `extract_ai_cases.py` | Extract structured fields from case text |
| `derive_friction_coefficients.py` | Phase 1: empirical friction coefficients |
| `nlp_extraction_engine.py` | Phase 2: NLP causal coefficients |
| `re_pri_engine.py` | Core RE-PRI engine (hybrid NLP and AHP weighting) |
| `scenario_simulator.py` | Phase 3: Monte Carlo and OWA scenarios |
| `download_vicmap_planning.py`, `geospatial_ingestion.py` | Vicmap Planning data download and spatial join |
| `generate_*.py` | Charts and heatmap |

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cd code
python scenario_simulator.py
```

Run scripts from inside `code/`. `extract_ai_cases.py` uses the Gemini API and reads its key from the `GEMINI_API_KEY` environment variable.

## Data not included

Large raw inputs aren't in the repo (GitHub has a 100 MB file limit):

- Vicmap Planning zones and overlays. Run `download_vicmap_planning.py`, which saves them to `code/geospatial data/`
- AustLII full-text case exports (`full_text_batch_1.docx`, `full_text_batch_2.docx`)
- AEMO indicative REZ boundaries (2024 GIS data), the 2025 Inputs, Assumptions and Scenarios workbook, and NEM Generation Information
- Australian solar GHI/DNI poster maps
