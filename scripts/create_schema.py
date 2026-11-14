from db import SQL_DIR, get_connection, run_sql_file

conn = get_connection()
try:
    run_sql_file(conn, SQL_DIR / "schema.sql")
    conn.commit()
    print("Esquema 'airbnb' creado (tablas vacías, con todas las restricciones).")
finally:
    conn.close()
