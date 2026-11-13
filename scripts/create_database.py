"""
Paso 0 - Crea la base de datos vacía (si no existe).

CREATE DATABASE no puede ejecutarse dentro de una transacción, por eso aquí se
usa autocommit y nos conectamos a la base de datos de sistema 'postgres'.
"""
import os

from psycopg2 import sql

from db import get_connection

name = os.getenv("PGDATABASE", "airbnb_euskadi")
conn = get_connection("postgres")
conn.autocommit = True
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
    if cur.fetchone():
        print(f"La base de datos '{name}' ya existe.")
    else:
        cur.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8'").format(sql.Identifier(name)))
        print(f"Base de datos '{name}' creada.")
conn.close()
