# Project progress & handover notes

Read this first when picking the project up again. It says what is built, how to run it from the terminal, and what is still to do.
Update the **Status** and **Next steps** sections whenever something changes.

_Last updated: 2026-10-28_

---

## 1. The project in one paragraph

**Who's Missing?** is our entry to the NISR Big Data Hackathon 2026, **Track 2: Financial Inclusion & Poverty Reduction**.
It uses NISR's EICV7 household survey to measure, for each of Rwanda's 30 districts, how many poor households receive **no**
social protection (VUP or NSDS), called *exclusion error*, and how many recipients are **not** poor, called *inclusion error*.
It adds satellite night-time lights to show conditions between surveys. It also includes a budget simulator and a household
poverty checker for social-protection officers.

Judging: 5 criteria × 20 pts (problem & NST2 relevance, data & methodology, tech innovation, usability, impact).
Deliverables: **public GitHub repo + deployed app + documentation**. AI use must be disclosed (see `AI_USAGE.md`).

---

## 2. Status

| Part | Status | Notes |
|---|---|---|
| Django app (map, district page, simulator, checker, about) | ✅ Done | Runs on **real EICV7 data** (since 2026-10-28) |
| Survey statistics (weights, strata, clusters, 95% CIs) | ✅ Done | `pipeline/survey.py` |
| EICV7 variable mapping | ✅ Done, **validated** | Reproduces the official 27.4% poverty and 5.4% extreme poverty exactly |
| Poverty prediction model + explanations | ✅ Done, **real data** | AUC 0.795 on unseen clusters; at equal budget reaches 29.7% of poor vs 13.8% today |
| Satellite layer (night-time lights, population) | ✅ Done, **real data** | Google Earth Engine, cloud-screened |
| Budget simulator | ✅ Done, real data | |
| Tests | ✅ 7 passing | `python manage.py test dashboard` |
| **EICV7 microdata** | ✅ **Received** | Cross-section zip in `~/Downloads`; 7 files extracted to `data/raw/EICV7/` (git-ignored). A separate VUP-sample zip is unused so far |
| Priority alerts page | ❌ To do | Last missing piece for the "Tech innovation" criterion |
| Validation vs published NISR district poverty rates | ❌ To do | Needs `EICV7_Tables_MainIndicatorReport.xlsx` (public) |
| Deployment (Render) | ❌ To do | `build.sh` is ready |
| GitHub repo | ✅ Done | https://github.com/guillainkalisa/NISR-Hachathon-Ctrl-Alt-Elite (branch `main`) |
| Team names, NST2 targets, deadline in README | ❌ To do | Placeholders marked `_Fill in_` |

---

## 3. Running it from the terminal

Every command is run from the project folder with the virtual environment active:

```bash
cd ~/Desktop/Class_Assigns/NISR
source .venv/bin/activate          # prompt now starts with (.venv)
```

### Start the website
```bash
python manage.py runserver 8800
```
Open **http://127.0.0.1:8800**. Stop with `Ctrl + C`.
> If the page looks out of date, it is the browser cache. Use a different port (e.g. `runserver 8900`) or hard-refresh with `Ctrl + Shift + R`.

### Everyday Django commands
| Command | What it does |
|---|---|
| `python manage.py runserver 8800` | Start the site |
| `python manage.py test dashboard` | Run all tests (should print `OK`) |
| `python manage.py migrate` | Create or update database tables (after model changes, or on a new machine) |
| `python manage.py makemigrations dashboard` | Generate a migration after editing `dashboard/models.py` |
| `python manage.py load_indicators` | Load `data/processed/indicators.csv` into the database |
| `python manage.py load_satellite` | Load `data/processed/satellite_*.csv` into the database |
| `python manage.py createsuperuser` | Create a login for the admin at `/admin/` |
| `python manage.py shell` | Python shell with Django loaded |

### Setting up on a new machine (e.g. teammate's laptop)
```bash
git clone <repo-url> && cd <repo>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_indicators
python manage.py load_satellite
python manage.py runserver 8800
```
This is enough to run the site. Re-running the pipelines below needs the data or Earth Engine access.

---

## 4. Data pipelines (run before the website shows new numbers)

The pipeline is plain Python in `pipeline/` and is separate from Django. It writes CSV files to `data/processed/` and the
model to `models/`. The `load_*` commands then copy those into the Django database.

```
raw data ──> pipeline/*.py ──> data/processed/*.csv, models/ ──> manage.py load_* ──> website
```

### A. Demo data (what the site shows now)
```bash
python -m pipeline.demo_data
python -m pipeline.build_indicators --source data/demo --demo
python -m pipeline.train_pmt --source data/demo --round EICV7 --demo
python manage.py load_indicators
```

### B. Real EICV7 data (as soon as the files arrive)
1. Put the Stata files in `data/raw/EICV7/`. These 7 are needed:
   `CS_EICV7_poverty_file`, `CS_S01_S5_S7_Household`, `CS_S0_S1_S2_S3_S4_S6A_S6B_S6C_Person`,
   `CS_S9D1_Direct_Support`, `CS_S9D2_Classic_Public_Work`, `CS_S9D3_Expanded_Public_Work`, `CS_S9D4_NSDS` (all `.dta`).
2. Run:
   ```bash
   python -m pipeline.prepare_eicv --round EICV7
   python -m pipeline.build_indicators
   python -m pipeline.train_pmt --round EICV7
   python manage.py load_indicators
   ```
3. **Check:** `prepare_eicv` prints national poverty, extreme poverty and VUP coverage. They must match the
   *EICV7 Main Indicator Report*. If they don't, the mapping in `pipeline/rounds/eicv7.py` needs fixing.
4. The demo banner disappears automatically once real data is loaded.

### C. Satellite data (Google Earth Engine)
Needs `EE_PROJECT=project-fd2909ee-d2a1-48ef-abd` in `.env` (already there) and a one-time `earthengine authenticate`.
```bash
python -m pipeline.satellite snapshot          # Oct 2023 – Oct 2024, matches EICV7 fieldwork
python -m pipeline.satellite monthly           # last 24 months; re-run monthly to refresh
python manage.py load_satellite
```

---

## 5. Where things are

```
config/                     Django settings and root URLs
dashboard/                  The Django app
  models.py                   District, Indicator, SatelliteSnapshot, NightlightMonth
  views.py                    One function per page
  urls.py                     /  /district/<name>/  /simulator/  /checker/  /about/
  templates/dashboard/        HTML pages (base.html = shared header/footer)
  static/dashboard/           style.css (colours, light/dark mode), map.js (the map)
  services/simulator.py       Budget allocation logic
  services/pmt.py             Loads the model, scores a household, explains the result
  management/commands/        load_indicators, load_satellite
  tests.py                    Automated tests
pipeline/                   Data processing (no Django)
  features.py                 Column names shared by everything, plus the model's input fields
  rounds/eicv7.py             EICV7 file names, variables and answer codes
  prepare_eicv.py             Raw EICV -> one clean household table
  survey.py                   Weighted estimates and confidence intervals
  build_indicators.py         District indicators -> data/processed/indicators.csv
  train_pmt.py                Poverty model -> models/pmt.joblib
  satellite.py                Earth Engine -> data/processed/satellite_*.csv
  demo_data.py                Synthetic households (development only)
data/
  raw/, interim/              Household microdata. NEVER committed (git-ignored)
  processed/                  District-level results. Safe to publish
  geo/                        District boundaries (geoBoundaries)
  metadata/                   EICV7 data dictionary + flat variable list (eicv7_variables.csv)
models/                     Trained model + its accuracy figures
```

---

## 6. Decisions made, and why

- **Track 2, the targeting-gap idea.** NISR's own survey is the core data, it ties directly to NST2, and it gives a clear user (LODA, MINALOC, districts).
- **Support = VUP (any component) + NSDS.** Ubudehe category is not in the public microdata, and the survey shows health insurance but not whether Mutuelle was subsidised.
- **Poverty status from `pov_jan`**, which is coded **0 / 100** (not 0 / 1).
- **"Any VUP" = Direct Support or classic or expanded public works.** Each S9D file has a column `s9d1q1` labelled "VUP, any component", but it only covers that file's own component, so it is not used.
- **Exclusion error counts all poor households, not only those eligible.** VUP and NSDS target only some poor households (no labour capacity, pregnant mothers, etc.), so part of the 85% gap is by design. Explain this on the Method page and in the pitch.
- **Strata = `strata_id`** (district-based, as in the EICV7 sampling design).
- **Household checker features:** observable traits only (housing, assets, head of household). Land area is not in the public files, so it was dropped.
- **Satellite via API, not downloads.** Earth Engine does the processing and returns only 30 numbers per district. The website reads saved results, so it stays fast and does not depend on Google during judging.
- **Two satellite time frames.** A survey-period snapshot (for analysis) is kept separate from monthly updates (for alerts).
- **Cloudy months are flagged, not used.** Rainy-season clouds made districts look falsely dark. Pixels with fewer than 2 clear nights are dropped, and district-months with under half the area visible are marked unreliable (135 of 720).
- **WorldPop 2024 (R2025A)** replaced the deprecated 2020 dataset. Its total (12.1M) is below the 2022 Census (13.2M), but we only use shares, so this does not matter.
- **Privacy.** Only district aggregates and the model are committed or deployed. Microdata stays in the git-ignored `data/raw/` and `data/interim/`.

---

## 7. Next steps (in order)

1. ~~Get EICV7 microdata~~ Done 2026-10-28. Only one survey round is loaded, so the trend chart has one point; add EICV5/EICV6 for trends.
2. **Validate night-time lights against official district poverty.** Download the public `EICV7_Tables_MainIndicatorReport.xlsx`.
3. **Build the priority alerts page:** districts with high exclusion plus a worsening trend or a satellite signal, each with a downloadable district brief.
4. **Optional:** sector-level (416 sectors) poverty estimates combining EICV7 with satellite data.
5. **Polish:** fill in the README placeholders (team, NST2 targets), update `AI_USAGE.md`, review the design.
6. **Publish:** create the GitHub repo, commit, deploy on Render (`build.sh`, start command `gunicorn config.wsgi`).
7. **Record a 2–3 minute demo video.**

## 8. Open questions

- Submission **deadline**?
- Team names and universities for the README?
