"""
Carga las consultas de sql/queries/*.sql y las ejecuta con parámetros.

Lo usan tanto scripts/run_queries.py (para el informe) como la app de
Streamlit. Así cada consulta está escrita UNA sola vez, a mano, en su .sql.

Seguridad (inyección SQL): los valores del usuario NUNCA se pegan dentro del
texto SQL. Se pasan aparte a cursor.execute(sql, params) y psycopg2 los
escapa correctamente (%(nombre)s en el .sql).
"""
import json
import re
from pathlib import Path

QUERIES_DIR = Path(__file__).resolve().parent.parent / "sql" / "queries"
META_RE = re.compile(r"^-- (\w+): (.*)$")


def load_queries() -> dict[str, dict]:
    """Devuelve {'Q01': {id, author, title, question, why, techniques, params, sql | steps, file}}."""
    out = {}
    for path in sorted(QUERIES_DIR.glob("q*.sql")):
        text = path.read_text(encoding="utf-8")
        meta, body = {}, []
        for line in text.splitlines():
            m = META_RE.match(line)
            if m and not body and m.group(1) != "@step":
                meta[m.group(1)] = m.group(2).strip()
            else:
                body.append(line)
        q = {**meta, "file": path.name, "params": json.loads(meta.get("params", "{}"))}
        sql = "\n".join(body).strip()
        if meta.get("type") == "transaction":
            parts = re.split(r"^-- @step (\w+)$", sql, flags=re.M)
            q["steps"] = {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}
        q["sql"] = sql
        out[q["id"]] = q
    return out


def run_query(conn, q: dict, params: dict | None = None):
    """Ejecuta una consulta de lectura. Devuelve (nombres_columnas, filas)."""
    p = {**q["params"], **(params or {})}
    with conn.cursor() as cur:
        cur.execute(q["sql"], p)
        cols = [d.name for d in cur.description]
        rows = cur.fetchall()
    conn.rollback()  # cierra la transacción de lectura
    return cols, rows


def run_transaction_query(conn, q: dict, params: dict | None = None, commit: bool = False):
    """Q09: before -> UPDATE -> after dentro de UNA transacción.
    Por defecto termina con ROLLBACK, así la base de datos no cambia."""
    p = {**q["params"], **(params or {})}
    steps = q["steps"]
    try:
        with conn.cursor() as cur:
            cur.execute(steps["before"], p)
            cols = [d.name for d in cur.description]
            before = cur.fetchall()
            cur.execute(steps["update"], p)
            updated = cur.rowcount
            cur.execute(steps["after"], p)
            after = cur.fetchall()
        if commit:
            conn.commit()
        else:
            conn.rollback()
    except Exception:
        conn.rollback()
        raise
    return cols, before + after, updated
