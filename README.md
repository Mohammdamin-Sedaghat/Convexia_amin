## Amins Convexia CRO Submission

# CRO Reliability Pipeline

This repository contains a pipeline to build a unified reliability dataset for the top Contract Research Organizations (CROs) based on public FDA enforcement data and clinical trial performance metadata.

---

## Table of Contents

1. [Overview](#overview)
2. [Repository Structure](#repository-structure)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Data Sources](#data-sources)
6. [Methodology](#methodology)

   * [1. Target List Extraction](#1-target-list-extraction)
   * [2. Name Standardization](#2-name-standardization)
   * [3. Regulatory Data Ingestion & Cleaning](#3-regulatory-data-ingestion--cleaning)
   * [4. Dataset Merging](#4-dataset-merging)
   * [5. Final Schema & Export](#5-final-schema--export)
   * [6. Trial-Level Performance Data](#6-trial-level-performance-data)
7. [Final Unified Schema](#final-unified-schema)
8. [Evaluation](#evaluation)
9. [Limitations & Future Work](#limitations--future-work)

---

## Overview

I build a foundational dataset to quantify operational reliability of 20 major global CROs over the past five years (with the ability to expand). The pipeline:

* Scrapes and structures FDA enforcement data (Form 483s, Warning Letters, inspection citations)
* Loads clinical trial metrics (e.g., completion delays, dropout rates) from ClinicalTrials.gov
* Normalizes company names and flags
* Merges all sources into a single, standardized table (`unified_schema.csv`)

This output can poIr scoring models, dashboards, and downstream analysis.

---

## Repository Structure

```
├── data/
│   ├── targets.csv
│   ├── inspection_details_since2019.csv
│   ├── Inspection_Citation_Details.csv
│   ├── Published_483s.csv
│   ├── warning-letters.csv
│   ├── clinicalTrials_summary.csv
├── extract_targets.py       # Scraper for initial CRO list
├── Convexia-Amin.ipynb       # Main pipeline notebook
├── requirements.txt
├── overlaps.json
└── README.md
```

---

## Prerequisites

* Python 3.9+
* Dependencies listed in `requirements.txt`:

  * pandas
  * rapidfuzz
  * matplotlib - for evaluating findings
  * (There are other ones mentioned but those are for jupyter nootebook)

---

## Installation

1. Clone the repo:

   ```bash
   git clone https://github.com/your-username/cro-reliability-pipeline.git
   cd cro-reliability-pipeline
   ```
2. Install packages:

   ```bash
   pip install -r requirements.txt
   ```
3. Ensure the `data/` directory contains all CSV and JSON files as described above.

---

## Data Sources

1. **Target CRO List**: Top 50 CROs, scraped from a recent industry article; pared down to top 20 for this project (`extract_targets.py` can generate `data/targets.csv`).
2. **FDA Inspection Dashboard**: Inspection and violation data from FDA’s BIMO program. Source: [https://datadashboard.fda.gov/oii/cd/inspections.htm](https://datadashboard.fda.gov/oii/cd/inspections.htm)
3. **FDA Warning Letters**: Official warning letters. Source: [https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters)
4. **FDA Form 483s**: Published 483 notices from the same dashboard.
5. **ClinicalTrials.gov (AACT)**: Trial-level performance metadata (dropout rates, completion delays). Download via [https://aact.ctti-clinicaltrials.org/downloads](https://aact.ctti-clinicaltrials.org/downloads)

Each source link and rationale is documented in the methodology below.

---

## Methodology

### 1. Target List Extraction

* **Purpose**: Define the set of CROs to benchmark.
* **Process**: Scrape top CRO names and FEI numbers with `extract_targets.extract(n)` (skip by default, `data/targets.csv` provided).

### 2. Name Standardization

* **Purpose**: Resolve alternate or legacy CRO names (e.g., Quintiles → IQVIA).
* **Data**: `overlaps.json` maps `non_standardized` names to `cro_name_standardized`.
* **Approach**:

  1. Lowercase company name column.
  2. Use `rapidfuzz.process.extractOne` with `token_sort_ratio` and threshold 90.
  3. Drop unmatched records.
  4. Map matches to standardized names.

### 3. Regulatory Data Ingestion & Cleaning

For each of the three enforcement sources:

1. **Inspection Details** (`inspection_details_since2019.csv`)
2. **Inspection Citation Details** (`Inspection_Citation_Details.csv`)
3. **Published 483s** (`Published_483s.csv`)
4. **Warning Letters** (`warning-letters.csv`)

Steps:

* Load CSV into pandas.
* Standardize CRO names (see step 2).

### 4. Dataset Merging

1. **Merge** inspection details + citation details on `Inspection ID` (left join).
2. **Merge** result + published 483s on `(FEI Number, date_of_inspection)` (outer join).
3. **Merge** result + warning letters on `cro_name_standardized` (outer join).
4. **Clean** duplicate columns by filling nulls and dropping old suffixes.
5. **Rename** final columns to snake\_case and logical field names.
6. Filter or flag records:

    * `has_483` → `form_483_flag`
    * `has_warning` → `warning_letter_flag`
7. Drop irrelevant columns (location details, duplicates).

### 5. Final Schema & Export

* Add source column: `source = "FDA_DASHBOARD"`.
* Reorder columns for readability.
* Export to `data/regulatory_data_merged.csv`.

### 6. Trial-Level Performance Data

* Load `data/clinicalTrials_summary.csv` (prepared from AACT SQL dump). -- For more details look bellow.
* Standardize `cro_involved` to `cro_name_standardized`.
* Merge with `targets` to focus on top CROs.
* Concatenate with regulatory data to form `unified_schema`.
* Export to `data/unified_schema.csv`.


### AACT SQL Dump. 
* This file was loaded into a local postgreSQL and it's data was extracted through the following command:
```sql

\copy ( 
SELECT
    study.nct_id                              AS trial_identifier,
	sp.name                    AS cro_involved,
        dw.total_withdrawals::float               AS withdrawals,
    study.enrollment::float                   AS enrolled,

	study.start_date,

	CASE
		WHEN study.primary_completion_date_type = 'ACTUAL'
		THEN primary_completion_date
		WHEN study.completion_date_type = 'ACTUAL'
		THEN completion_date
		ELSE NULL
	END                                       AS completion_date,

	CASE
		WHEN study.primary_completion_date_type = 'ESTIMATED'
		THEN primary_completion_date
		WHEN study.completion_date_type = 'ESTIMATED'
		THEN completion_date
		ELSE NULL
	END                                       AS estimated_completion_date,
	
    CASE
      WHEN study.enrollment > 0
      THEN dw.total_withdrawals::float / study.enrollment::float
      ELSE NULL
    END                                       AS dropout_rate,
    f.country                               AS country,
    f.city                                  AS city
  FROM studies AS study


  LEFT JOIN sponsors AS sp
    ON study.nct_id = sp.nct_id
   AND sp.lead_or_collaborator = 'collaborator'


  LEFT JOIN (
    SELECT
      nct_id,
      SUM(count) AS total_withdrawals
    FROM drop_withdrawals
    WHERE period LIKE '%Overall%'
    GROUP BY nct_id
  ) AS dw
    ON study.nct_id = dw.nct_id


  LEFT JOIN facilities AS f
    ON study.nct_id = f.nct_id


  WHERE sp.name is NOT NULL
) TO 'C:/Users/mamin/Downloads/test/trials_summary.csv'
WITH CSV HEADER;

```

---

## Final Unified Schema

['fei_number', 'cro_name_standardized', 'inspection_id',
       'date_of_inspection', 'type_of_issue', 'classification',
       'act/cfr_number', 'short_description', 'publish_date', 'form_483_flag',
       'warning_letter_flag', 'download', 'source', 'record_id',
       'specialization', 'notable_client', 'trial_identifier', 'withdrawals',
       'enrolled', 'start_date', 'completion_date',
       'estimated_completion_date', 'dropout_rate', 'country', 'city']

| Column                      | Description                                          |
| --------------------------- | ---------------------------------------------------- |
| fei\_number                 | FDA FEI identifier for the CRO                       |
| cro\_name\_standardized     | Standardized CRO name                                |
| inspection\_id              | Unique inspection record ID                          |
| date\_of\_inspection        | Inspection or trial record date                      |
| type\_of\_issue             | Issue category (e.g., data integrity, deviation)     |
| classification              | Severity classification                              |
| act/cfr\_number             | Regulatory reference number                          |
| short\_description          | Brief description of violation or performance metric |
| publish\_date               | Date of warning letter or 483 publication            |
| form\_483\_flag             | 1 if a Form 483 was issued, else 0                   |
| warning\_letter\_flag       | 1 if a warning letter exists, else 0                 |
| download                    | Link to source document (if available)               |
| source                      | Data source identifier (e.g., FDA\_DASHBOARD, AACT)  |
| record\_id                  | Unique record identifier across all sources          |
| specialization              | CRO's area(s) of specialization                      |
| notable\_client             | Example notable clients under CRO's service          |
| trial\_identifier           | Clinical trial identifier (e.g., NCT number)         |
| withdrawals                 | Number of participant withdrawals in trial           |
| enrolled                    | Number of participants enrolled                      |
| start\_date                 | Trial start date                                     |
| completion\_date            | Actual trial completion date                         |
| estimated\_completion\_date | Estimated trial completion date                      |
| dropout\_rate               | Calculated dropout rate                              |
| country                     | Country where trial was conducted                    |
| city                        | City where trial was conducted                       |

---

## Evaluation
  * Evaluation is done by the end of the .ipynb file and a summary is provided as a seprate file.

## Limitations & Future Work

* **Citeline Data**: TrialTrove / SiteTrove integration required subscription to platform.
* **Automation**: Can be scheduled or containerized for continuous updates.
