"""
Utilidad común: abre una conexión psycopg2 con los datos del fichero .env.

Todos los scripts del proyecto importan get_connection() de aquí para no
repetir credenciales. La contraseña NUNCA se escribe en el código.
"""
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SQL_DIR = ROOT / "sql"

load_dotenv(ROOT / ".env")
DB_NAME = os.getenv("PGDATABASE", "airbnb_euskadi")


def get_connection(dbname: str | None = None):
    """Devuelve una conexión NUEVA. autocommit=False (por defecto en psycopg2):
    nada se guarda hasta que se llama a conn.commit()."""
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        dbname=dbname or DB_NAME,
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", ""),
    )


def run_sql_file(conn, path: Path) -> None:
    """Ejecuta un fichero .sql completo (dentro de la transacción actual)."""
    with conn.cursor() as cur:
        cur.execute(path.read_text(encoding="utf-8"))
