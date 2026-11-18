from db import SQL_DIR, get_connection, run_sql_file

conn = get_connection()
try:
    run_sql_file(conn, SQL_DIR / "schema.sql")
    conn.commit()
    print("Schema 'airbnb' created (empty tables with all constraints).")
finally:
    conn.close()
