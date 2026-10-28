# Who's Missing? Social protection targeting in Rwanda

**NISR Big Data Hackathon 2026, Track 2: Financial Inclusion & Poverty Reduction**

Social protection only reduces poverty if it reaches poor households. Using NISR's EICV household survey, this tool
measures, district by district, how many poor households receive **no** support (exclusion error) and how many
recipients are **not** poor (inclusion error). It also shows where extra budget would reach the most poor households.

- **Live app:** _add deployed link_
- **Demo video:** _add link_

> 📋 **Team:** see [PROGRESS.md](PROGRESS.md) for current status, terminal commands and next steps.

## What it does

| Page | For | What it shows |
|---|---|---|
| **Map** | LODA, MINALOC, partners | Districts shaded by exclusion error, poor households missed, poverty, coverage or inclusion error, by EICV round |
| **District profile** | District planners | Key rates with 95% CIs, change across rounds, who the excluded poor are |
| **Budget simulator** | Policy & budget | Extra slots allocated like today vs. by need, and how many more poor households need-based allocation reaches |
| **Household checker** | Social-protection officers | Proxy-means-test model: estimated probability a household is poor from about 15 observable traits, with the traits that drove each result |

## Alignment with national priorities
_Fill in: quote the relevant NST2 (2024–2029) poverty and social-protection targets and Vision 2050 pillar._

## Repository layout

```
pipeline/            Data pipeline (plain Python, independent of Django)
  features.py          Canonical household schema + model features
  inspect_eicv.py      List variables in raw EICV files
  prepare_eicv.py      Raw EICV -> canonical household table
  rounds/eicv7.py      EICV7 file names, variables and recodes (from the NISR data dictionary)
  survey.py            Design-based estimators (weights, strata, clusters)
  build_indicators.py  District indicators -> data/processed/indicators.csv
  train_pmt.py         Poverty model -> models/pmt.joblib + metrics
  satellite.py         Night-time lights + population per district via Google Earth Engine
  demo_data.py         Synthetic data for development only
dashboard/           Django app (map, district, simulator, checker, about)
data/geo/            District boundaries (geoBoundaries, CC BY 4.0)
data/metadata/       EICV7 data dictionary (DDI JSON/XML) + flat variable list
data/processed/      Published aggregates (safe to commit)
data/raw, interim/   Microdata - git-ignored, never committed
```

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Option A: synthetic demo data
python -m pipeline.demo_data
python -m pipeline.build_indicators --source data/demo --demo
python -m pipeline.train_pmt --source data/demo --round EICV7 --demo

# Option B: real EICV7 (put the Stata files in data/raw/EICV7/)
python -m pipeline.prepare_eicv --round EICV7           # mapping in pipeline/rounds/eicv7.py
python -m pipeline.build_indicators
python -m pipeline.train_pmt --round EICV7

# Satellite indicators (needs a Google Earth Engine project; EE_PROJECT=<id> in .env, then `earthengine authenticate`)
python -m pipeline.satellite snapshot          # EICV7 fieldwork period, for analysis
python -m pipeline.satellite monthly           # last 24 months, re-run monthly to refresh

python manage.py migrate
python manage.py load_indicators
python manage.py load_satellite
python manage.py runserver
python manage.py test dashboard
```

## Deployment (Render)
- Build command: `./build.sh`
- Start command: `gunicorn config.wsgi`
- Environment: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=<random>`, `DJANGO_ALLOWED_HOSTS=<your-app>.onrender.com`,
  `DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-app>.onrender.com`

Only `data/processed/indicators.csv` and `models/` are deployed. No household microdata.

## Methodology
See the in-app **Method & data** page. In short: survey-weighted ratios with Taylor-linearised standard errors over
EICV strata and clusters. Districts with under 30 sampled poor households are flagged. The model is a gradient-boosted
classifier, evaluated on survey clusters it never saw, against current targeting at an equal number of beneficiaries.

## Data sources
- National Institute of Statistics of Rwanda: EICV7 (Integrated Household Living Conditions Survey, 2023/24), cross-sectional sample
- NOAA VIIRS Day/Night Band monthly composites (VCMSLCFG), via Google Earth Engine
- WorldPop 100 m population 2024 (R2025A), via Google Earth Engine
- geoBoundaries: Rwanda ADM2 boundaries, CC BY 4.0

## Team, originality & AI use
_Team names and universities._ This is our original work for this hackathon. AI tool use is disclosed in
[AI_USAGE.md](AI_USAGE.md).
