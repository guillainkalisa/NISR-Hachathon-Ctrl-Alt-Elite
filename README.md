**Who's Missing? Social protection targeting in Rwanda**  
**NISR Big Data Hackathon 2026, Track 2: Financial Inclusion & Poverty Reduction**  
Social protection only reduces poverty if it reaches poor households. Using NISR's EICV household survey, this tool  
   
 measures, district by district, how many poor households receive **no** support (exclusion error) and how many  
   
 recipients are **not** poor (inclusion error). It also shows where extra budget would reach the most poor households.  
- **Live app:** *add deployed link*  
- **Demo video:** *add link*  
*📋* ***Team:*** *see* [*PROGRESS.md for current status, terminal commands and next steps.*](PROGRESS.md "PROGRESS.md")  
**What it does**  
  
|  |  |  |  
| - | - | - |  
| **Page** |  **For** |  **What it shows** |  
| **Map** |  LODA, MINALOC, partners |  Districts shaded by exclusion error, poor households missed, poverty, coverage or inclusion error, by EICV round |  
| **District profile** |  District planners |  Key rates with 95% CIs, change across rounds, who the excluded poor are |  
| **Budget simulator** |  Policy & budget |  Extra slots allocated like today vs. by need, and how many more poor households need-based allocation reaches |  
| **Household checker** |  Social-protection officers |  Proxy-means-test model: estimated probability a household is poor from about 15 observable traits, with the traits that drove each result |  
  
   
**How to use it**  
1. **Map (home page).** Pick a measure in the *Indicator* menu: survey measures such as poor households receiving  
   
 no support, or satellite measures such as people living under night-time light. Darker districts are worse off  
   
 (for coverage and light, darker means less). Hover over a district for its value, or read the top-10 list and  
   
 full table under the map. Click a district to open its profile.  
2. **District profile.** Headline rates with 95% confidence intervals, who the poor households being missed are  
   
 (female-headed, elderly head, disability, young children and so on), and monthly night-time lights since the  
   
 survey. Gaps in the lights chart are months too cloudy to measure.  
3. **Budget simulator.** Move the slider to add support places (1–50% of today's recipients). The page compares  
   
 sharing them out the way places are shared today with sharing them by need, and shows how many more poor  
   
 households the need-based option reaches.  
4. **Household checker.** Enter a household's observable traits (roof, floor, electricity, livestock, head of  
   
 household and so on). It returns the estimated probability that the household is poor, and the traits that  
   
 pushed the estimate up or down. It is a screening aid for officers, not an eligibility decision.  
5. **Method & data.** Definitions, model accuracy and data sources.  
**Alignment with national priorities**  
*Fill in: quote the relevant NST2 (2024–2029) poverty and social-protection targets and Vision 2050 pillar.*  
**Repository layout**  
```  
pipeline/            Data pipeline (plain Python, independent of Django)  
   features.py          Canonical household schema + model features  
   inspect_eicv.py      List variables in raw EICV files  
   prepare_eicv.py      Raw EICV -> canonical household table  
   rounds/eicv7.py      EICV7 file names, variables and recodes (from the NISR data dictionary)  
   survey.py            Design-based estimators (weights, strata, clusters)  
   build_indicators.py  District indicators -> data/processed/indicators.csv  
   train_pmt.py         Poverty model -> models/pmt.joblib + metrics  
   export_trees.py      Model as plain numpy arrays (models/pmt.npz), used by the website  
   satellite.py         Night-time lights + population per district via Google Earth Engine  
   demo_data.py         Synthetic data for development only  
 dashboard/           Django app (map, district, simulator, checker, about)  
 data/geo/            District boundaries (geoBoundaries, CC BY 4.0)  
 data/metadata/       EICV7 data dictionary (DDI JSON/XML) + flat variable list  
 data/processed/      Published aggregates (safe to commit)  
 data/raw, interim/   Microdata - git-ignored, never committed  
   
```  
**Running locally**  
```  
python -m venv .venv && source .venv/bin/activate  
 pip install -r requirements.txt  
   
 # Option A: synthetic demo data  
 python -m pipeline.demo_data  
 python -m pipeline.build_indicators --source data/demo --demo  
 python -m pipeline.train_pmt --source data/demo --round EICV7 --demo  
   
 # Option B: real EICV7 (put the Stata files in data/raw/EICV7/)  
 python -m pipeline.prepare_eicv --round EICV7           # mapping in pipeline/rounds/eicv7.py  
 python -m pipeline.build_indicators  
 python -m pipeline.train_pmt --round EICV7  
   
 # Satellite indicators (needs a Google Earth Engine project; EE_PROJECT=<id> in .env, then `earthengine authenticate`)  
 python -m pipeline.satellite snapshot          # EICV7 fieldwork period, for analysis  
 python -m pipeline.satellite monthly           # last 24 months, re-run monthly to refresh  
   
 python manage.py migrate  
 python manage.py load_indicators  
 python manage.py load_satellite  
 python manage.py runserver  
 python manage.py test dashboard  
   
```  
**Deployment (PythonAnywhere)**  
1. **Bash console** (Consoles → Bash):  
2.   
```  
git clone https://github.com/guillainkalisa/NISR-Hachathon-Ctrl-Alt-Elite.git  
 cd NISR-Hachathon-Ctrl-Alt-Elite  
 mkvirtualenv --python=python3.12 nisr  
 pip install --no-cache-dir -r requirements-web.txt  
 export DJANGO_DEBUG=0 DJANGO_SECRET_KEY=build-only  
 python manage.py collectstatic --noinput  
 python manage.py migrate  
 python manage.py load_indicators  
 python manage.py load_satellite  
   
```  
3. **Web tab** → Add a new web app → *Manual configuration* → Python 3.12. Then set:  
  - Source code: `/home/<username>/NISR-Hachathon-Ctrl-Alt-Elite`  
  - Virtualenv: `/home/<username>/.virtualenvs/nisr`  
  - Static files: URL `/static/` → directory `/home/<username>/NISR-Hachathon-Ctrl-Alt-Elite/staticfiles`  
4. **WSGI configuration file** (link on the Web tab): replace its contents with  
5.   
```  
import os, sys  
 path = "/home/<username>/NISR-Hachathon-Ctrl-Alt-Elite"  
 if path not in sys.path:  
     sys.path.insert(0, path)  
 os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"  
 os.environ["DJANGO_DEBUG"] = "0"  
 os.environ["DJANGO_SECRET_KEY"] = "<long random string>"  
 os.environ["DJANGO_ALLOWED_HOSTS"] = "<username>.pythonanywhere.com"  
 os.environ["DJANGO_CSRF_TRUSTED_ORIGINS"] = "https://<username>.pythonanywhere.com"  
 from django.core.wsgi import get_wsgi_application  
 application = get_wsgi_application()  
   
```  
6. Click **Reload** and open `https://<username>.pythonanywhere.com`.  
To update after a new push: `git pull`, re-run `collectstatic`/`migrate`/`load_*` if static files or data changed, then **Reload**.  
   
 Generate the secret key with `python -c "import secrets; print(secrets.token_urlsafe(50))"` and never commit it.  
**Deployment (Render)**  
- Build command: `./build.sh`  
- Start command: `gunicorn config.wsgi`  
- Environment: `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY=<random>`, `DJANGO_ALLOWED_HOSTS=<your-app>.onrender.com`,  
 `DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-app>.onrender.com`  
Only `data/processed/indicators.csv` and `models/` are deployed. No household microdata.  
**Methodology**  
See the in-app **Method & data** page. In short: survey-weighted ratios with Taylor-linearised standard errors over  
   
 EICV strata and clusters. Districts with under 30 sampled poor households are flagged. The model is a gradient-boosted  
   
 classifier, evaluated on survey clusters it never saw, against current targeting at an equal number of beneficiaries.  
**Data**  
The data the app uses is in [`data/`;](data/ "data/") [`data/README.md` describes every file.](data/README.md "data/README.md")  
  
|  |  |  |  
| - | - | - |  
| **Data** |  **Source & link** |  **In this repo?** |  
| EICV7 household survey 2023/24, cross-sectional sample (15,054 households) |  NISR Microdata Catalog: [https://microdatabk.statistics.gov.rw/index.php/catalog/119](https://microdatabk.statistics.gov.rw/index.php/catalog/119 "https://microdatabk.statistics.gov.rw/index.php/catalog/119") |  **District results only** (`data/processed/indicators.csv`). The raw microdata (about 1.5 GB) is licensed by NISR to approved users and must not be redistributed; request access at the link above |  
| EICV7 data dictionary |  Same catalog page (DDI metadata) |  Yes, `data/metadata/` |  
| Night-time lights: NOAA VIIRS DNB monthly, cloud-screened (`NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG`) |  [https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMSLCFG](https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMSLCFG "https://developers.google.com/earth-engine/datasets/catalog/NOAA_VIIRS_DNB_MONTHLY_V1_VCMSLCFG") |  Yes, district results in `data/processed/satellite_*.csv` |  
| Population: WorldPop 100 m, 2024 (`WorldPop/GP/100m/R2025A/v1/pop`) |  [https://www.worldpop.org via Google Earth Engine](https://www.worldpop.org "https://www.worldpop.org") |  Yes, inside `satellite_districts.csv` |  
| District boundaries (ADM2), CC BY 4.0 |  geoBoundaries: [https://www.geoboundaries.org](https://www.geoboundaries.org "https://www.geoboundaries.org") |  Yes, `data/geo/rwa_districts.geojson` |  
  
   
To rebuild everything from the raw data, put the EICV7 Stata files in `data/raw/EICV7/` and follow *Running locally*, option B.  
**Demo video**  
[`demo/`: 3-minute screen recording of the app](demo/ "demo/")  
**Team, originality & AI use**  
**Ctrl Alt Elite**, Year 3 students at the University of Rwanda: Hakiza Divine, KALISA Guillain and Niyogakiza Japhet.  
   
 Proof of eligibility for all three members is in [`eligibility/`.  
   
 This is our original work for this hackathon. AI tool use is disclosed in  
   
 ](eligibility/ "eligibility/")[AI_USAGE.md.](AI_USAGE.md "AI_USAGE.md")  
