"""
Paso 2 - Copia los CSV TAL CUAL a un esquema 'staging' (todo como TEXT).

¿Por qué? El enunciado obliga a que TODO el análisis se haga en SQL, también
el perfilado de los datos en bruto (número de filas, nulos, claves candidatas...).
Para poder hacerlo en SQL, primero hay que meter los ficheros en PostgreSQL
sin tocarlos. Python aquí solo lee la cabecera para saber el nombre de las
columnas y envía el fichero con COPY; no analiza nada.

Cada columna es TEXT para que no se pierda ni se rechace ningún valor raro:
precisamente queremos VER esos valores raros al perfilar.

Este esquema es auxiliar: NO es el modelo final (ese está en sql/schema.sql).
"""
import csv
import time

from psycopg2 import sql

from db import RAW_DIR, get_connection

FILES = ["neighbourhoods", "listings", "calendar", "reviews"]


def main() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS staging CASCADE; CREATE SCHEMA staging;")
            for name in FILES:
                path = RAW_DIR / f"{name}.csv"
                with open(path, encoding="utf-8", newline="") as f:
                    header = next(csv.reader(f))
                cols = sql.SQL(", ").join(sql.SQL("{} TEXT").format(sql.Identifier(c)) for c in header)
                cur.execute(sql.SQL("CREATE TABLE staging.{} ({})").format(sql.Identifier(name), cols))
                t0 = time.time()
                with open(path, encoding="utf-8", newline="") as f:
                    cur.copy_expert(
                        sql.SQL("COPY staging.{} FROM STDIN WITH (FORMAT csv, HEADER true)")
                        .format(sql.Identifier(name)).as_string(conn),
                        f,
                    )
                print(f"  staging.{name:15} {cur.rowcount:>10,} filas  ({time.time()-t0:.1f}s)")
        conn.commit()
        print("Staging cargado.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
