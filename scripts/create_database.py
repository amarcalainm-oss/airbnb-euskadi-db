from psycopg2 import sql

from db import DB_NAME, get_connection

conn = get_connection("postgres")
conn.autocommit = True  # CREATE DATABASE cannot run inside a transaction
with conn.cursor() as cur:
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone():
        print(f"Database '{DB_NAME}' already exists.")
    else:
        cur.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8'").format(sql.Identifier(DB_NAME)))
        print(f"Database '{DB_NAME}' created.")
conn.close()
