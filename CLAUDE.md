# CLAUDE.md

University project (TECNUN, Project B): Inside Airbnb Euskadi data modelled in PostgreSQL 18,
loaded with a Python ETL, analysed in SQL and shown in a Streamlit app.
Team: Aitor Marcalain, Iker Elias. Step-by-step guide (Spanish): `docs/PASOS.md`.

## Course rules (graded - never break them)

- **All analysis happens in SQL.** Python may read files, clean formats and pass rows to charts.
  It must NOT filter, join, group, aggregate, pivot, merge or compute results. pandas is only a
  container of the rows a query returned (`pd.DataFrame(rows, columns=cols)`), nothing else.
- **SQL is written by hand.** psycopg2 with `%(name)s` parameters. No ORM, no SQL built by
  string concatenation or f-strings with user values. A literal `%` inside a parameterised
  query must be written `%%`.
- **The ETL (`scripts/etl.py`) runs in ONE transaction**: commit at the end, rollback on any
  error. The `--simulate-error` rollback demo must keep working.
- **Missing values stay NULL.** Never invent or impute a value. Every cleaning rule is counted
  in `stats` and listed in `RULES` (written to `docs/cleaning_report.md`).
- **The schema is created by `sql/schema.sql` first; the load only inserts rows.**
- **The app must never crash on bad input**: every query call is wrapped in try/except and
  shows `st.error`. Inputs are constrained widgets (selectbox, slider, number_input with
  bounds). Keep these try/except blocks.
- **Raw data is never committed** (`data/`, `*.csv` are git-ignored). Never edit `.env`.
- Each query in `sql/queries/qNN_*.sql` keeps its header (`-- id/author/title/question/why/
  techniques/params`); `scripts/query_lib.py` parses it.

## Conventions

- Python 3.14, standard library + psycopg2, python-dotenv, streamlit, plotly, pandas.
- Comments and docstrings in Spanish (the team learns from them); query headers and app UI in
  English (they go into the English report).
- No emojis anywhere (code, UI, docs). Formal, sober UI.
- Chart colors: fixed categorical palette, each province always the same color; single-hue
  ramp for magnitudes; one axis per chart.
- Git: commits authored by the user only. Never add `Co-Authored-By` or any AI attribution.

## Commands

```bash
python scripts/run_all.py        # full pipeline: DB, download, staging, profiling, schema, ETL, queries
python scripts/etl.py --simulate-error   # rollback demo (needs empty tables: run create_schema.py first)
python scripts/run_queries.py    # regenerate docs/queries_results.md
streamlit run app/app.py
```
