# Data

| Folder / file | What it is | Source |
|---|---|---|
| `processed/indicators.csv` | One row per district (30) for EICV7: households, poor households, support recipients, poor households missed, poverty rate, coverage, exclusion and inclusion error with 95% CIs, sample sizes, and the profile of excluded households (JSON) | Computed by `pipeline/build_indicators.py` from EICV7 |
| `processed/satellite_districts.csv` | Per district, averaged over EICV7 fieldwork (Oct 2023 – Oct 2024): WorldPop population, mean night-time light, population-weighted light, share of people living under light | Computed by `pipeline/satellite.py` in Google Earth Engine |
| `processed/satellite_monthly.csv` | Per district and month (last 24 months): mean night-time light, share of the district clear of cloud, reliability flag | `pipeline/satellite.py monthly` |
| `geo/rwa_districts.geojson` | Rwanda district (ADM2) boundaries | geoBoundaries, https://www.geoboundaries.org (CC BY 4.0) |
| `metadata/RWA-NISR-EICV7-2023-2024-v01.json`, `.xml` | Official EICV7 data dictionary (DDI) | NISR Microdata Catalog, https://microdatabk.statistics.gov.rw/index.php/catalog/119 |
| `metadata/eicv7_variables.csv` | Flat list of every EICV7 variable and its label, made from the dictionary | `pipeline/inspect_eicv.py` |
| `raw/`, `interim/` | **Empty in this repository.** Locally they hold the EICV7 microdata and the cleaned household table | See below |

## Why the EICV7 microdata is not included

The household-level EICV7 files (about 1.5 GB) are distributed by NISR only to registered users who accept its
terms of use, which do not allow redistribution, and they describe individual households. Request access at
https://microdatabk.statistics.gov.rw/index.php/catalog/119, then place these files from the *Cross-Sectional Sample*
in `raw/EICV7/`:

```
CS_EICV7_poverty_file.dta
CS_S01_S5_S7_Household.dta
CS_S0_S1_S2_S3_S4_S6A_S6B_S6C_Person.dta
CS_S9D1_Direct_Support.dta
CS_S9D2_Classic_Public_Work.dta
CS_S9D3_Expanded_Public_Work.dta
CS_S9D4_NSDS.dta
```

and run `python -m pipeline.prepare_eicv --round EICV7` (see the main README). Git ignores these folders, so the files
cannot be committed by mistake.
