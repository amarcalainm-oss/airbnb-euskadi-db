# AI adoption report

The team used Claude Code (Claude Opus 5.5) as a coding assistant. Every artefact it produced was
reviewed, executed and checked by the team as described below.

| Task | Tool | What the AI produced | How the team checked it |
|---|---|---|---|
| Dataset source and licence | Claude Code | Download URLs of the Euskadi snapshot and the CC BY 4.0 licence | Opened the Inside Airbnb data and policy pages and confirmed the snapshot date and the licence. |
| Download script | Claude Code | `scripts/download_data.py` | Checked that the row counts of the downloaded files (6,248 listings, 2,280,744 calendar days, 432,956 reviews) match the staging tables and the loaded tables. |
| Profiling queries | Claude Code | `sql/profiling/*.sql` | Re-ran key results by hand in pgAdmin, e.g. `COUNT(*)` against `COUNT(DISTINCT id)` on reviews (432,956 vs. 419,594), and inspected a repeated review id directly. |
| ER and relational model | Claude Code | First draft of the model, the ER diagram and the design decisions | Checked every cardinality and exception against a profiling result (one province per municipality, repeated reviews always on listings of the same host) and discussed each decision as a team. |
| DDL | Claude Code | `sql/schema.sql` | Ran `sql/verify_constraints.sql` in pgAdmin after the load (all constraints validated) and ran one statement per constraint type that must fail; all five were rejected. |
| ETL and cleaning rules | Claude Code | `scripts/etl.py` | Ran the rollback demonstration (all eleven tables at 0 rows), compared loaded and staging row counts, and spot-checked repaired names (Álava, Guipúzcoa) and converted prices against the raw CSV. |
| SQL queries Q01-Q13 | Claude Code | First versions of the thirteen queries | Each author checked their queries on a small sample (one municipality or one host) against a manual count, confirmed that Q09 leaves prices unchanged after `ROLLBACK`, and added a tie-breaker to Q12 so its order is deterministic. |
| Streamlit application | Claude Code | `app/app.py` | Tried every filter, extreme slider values and SQL-injection strings as parameters (no rows, no crash). Reviewing the screenshots revealed an empty chart (Q08), which was fixed and checked again. |
| Report | Claude Code | First draft of the report | Compared every figure in the text with the generated results files and the database; read and corrected by both members. |
