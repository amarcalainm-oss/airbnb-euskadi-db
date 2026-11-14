"""
Paso 3 - Ejecuta las consultas de perfilado (sql/profiling/*.sql) y escribe
los resultados en docs/profiling_results.md.

Python solo envía cada consulta y escribe las filas devueltas en una tabla
Markdown: no calcula, filtra ni agrega nada. Todos los números salen de SQL.
"""
import re
from datetime import datetime

from db import ROOT, SQL_DIR, get_connection

OUT = ROOT / "docs" / "profiling_results.md"
MAX_ROWS = 60


def split_queries(text: str) -> list[tuple[str, str]]:
    """Divide un fichero en bloques que empiezan por '-- @query <título>'."""
    parts = re.split(r"^-- @query (.+)$", text, flags=re.M)
    # parts = [preámbulo, título1, sql1, título2, sql2, ...]
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def md_cell(v) -> str:
    """Valor -> celda Markdown (NULL visible, sin '|' ni saltos de línea)."""
    if v is None:
        return "NULL"
    return str(v).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    conn = get_connection()
    lines = [
        "# Resultados del perfilado de los datos en bruto",
        "",
        f"_Generado automáticamente por `scripts/run_profiling.py` el {datetime.now():%Y-%m-%d %H:%M}._",
        "_Cada tabla es el resultado literal de una consulta SQL sobre el esquema `staging`._",
        "",
    ]
    for path in sorted((SQL_DIR / "profiling").glob("*.sql")):
        lines += [f"## {path.stem}", "", f"Fichero: `sql/profiling/{path.name}`", ""]
        for title, query in split_queries(path.read_text(encoding="utf-8")):
            with conn.cursor() as cur:
                cur.execute(query)
                cols = [d.name for d in cur.description]
                rows = cur.fetchmany(MAX_ROWS)
            lines += [f"### {title}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
            lines += ["| " + " | ".join(md_cell(v) for v in r) + " |" for r in rows]
            lines.append("")
            print(f"  ok  {path.name}: {title}")
    conn.rollback()  # solo lectura
    conn.close()
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Resultados escritos en {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
