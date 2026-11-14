# AI adoption report 

The brief requires one row per task where AI was adopted. **Fill in the last column with what
the team actually did to check each item.** Ideas are given in _italics_.

| Task | Tool | What the AI produced | How the team checked it |
|---|---|---|---|
| Dataset source and licence | Claude Code (Claude Opus 5.5) | Located the Inside Airbnb Euskadi download URLs and the CC BY 4.0 licence | _Opened insideairbnb.com/get-the-data and data-policies and confirmed both_ |
| Download script | Claude Code | `scripts/download_data.py` | _Compared file sizes / row counts with the manually downloaded files_ |
| Profiling queries | Claude Code | `sql/profiling/*.sql` (row counts, nulls, keys, ranges, anomalies) | _Re-checked several numbers by hand in pgAdmin, e.g. `SELECT COUNT(*), COUNT(DISTINCT id) FROM staging.reviews`_ |
| ER / relational model draft | Claude Code | `docs/modelo.md`, Mermaid ER draft | _Discussed each decision; redrew ER in course notation_ |
| DDL | Claude Code | `sql/schema.sql` | _Verified constraints in pgAdmin with `sql/verify_constraints.sql`, tried statements that must fail_ |
| ETL and cleaning rules | Claude Code | `scripts/etl.py` | _Ran the rollback demo; compared table row counts with staging counts; spot-checked repaired names (Álava, Guipúzcoa)_ |
| SQL queries Q01–Q12 (first versions) | Claude Code | All 12 queries | _For each query: manual count on a small sample (e.g. one municipality) and compare_ |
| Streamlit app | Claude Code | `app/app.py` | _Tried every filter, invalid/extreme values and SQL-injection strings_ |
| Documentation | Claude Code | `docs/PASOS.md`, this table | _Read and corrected by the team_ |
