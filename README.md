# Airbnb Euskadi: relational database on real data

TECNUN · Information Technology · Project B
**Team:** Aitor Marcalain, Iker Elias

The project takes the **Inside Airbnb** data for the Basque Country (scrape of 25 September 2026,
licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)) and turns it into a normalised
PostgreSQL database. A Python script loads it in a single transaction, 13 hand-written SQL
queries analyse it, and a Streamlit app shows the results.

## Quick start

```bash
pip install -r requirements.txt
copy .env.example .env          # set PGPASSWORD
python scripts/run_all.py       # create DB, download, profile, schema, ETL, queries
python -m streamlit run app/app.py
```

## Repository layout

| Path | Content |
|---|---|
| `scripts/download_data.py` | downloads the raw files (data is **not** committed) |
| `scripts/load_staging.py` | raw CSV into the `staging` schema (all TEXT) for profiling in SQL |
| `sql/profiling/` | data-profiling queries, results in [`docs/profiling_results.md`](docs/profiling_results.md) |
| `sql/schema.sql` | physical schema: 11 tables, PK/FK/UNIQUE/CHECK/NOT NULL constraints, indexes |
| `scripts/etl.py` | ETL in one transaction (`--simulate-error` runs the rollback demonstration), rules in [`docs/cleaning_report.md`](docs/cleaning_report.md) |
| `sql/verify_constraints.sql` | constraint verification after the load |
| `sql/index_demo.sql` | timings with and without indexes |
| `sql/queries/` | 13 analytical queries, results in [`docs/queries_results.md`](docs/queries_results.md) |
| `app/app.py` | Streamlit application |
| [`docs/design.md`](docs/design.md) | ER diagram, relational model, justified design decisions |
| [`docs/ai_adoption.md`](docs/ai_adoption.md), [`docs/effort_log.md`](docs/effort_log.md) | AI adoption report, effort log |

## Data source

Inside Airbnb, *Euskadi, Spain*, 25 September 2026: https://insideairbnb.com/get-the-data/
Licensed under CC BY 4.0. Data © Inside Airbnb, sourced from publicly available Airbnb listings.
