"""
Ejecuta TODO el proceso de principio a fin, en orden:
  0. crear la base de datos       (create_database.py)
  1. descargar los datos          (download_data.py)
  2. cargar CSV en bruto          (load_staging.py)
  3. perfilado en SQL             (run_profiling.py)
  4. crear el esquema             (create_schema.py)
  5. ETL en una transacción       (etl.py)
  6. consultas -> informe         (run_queries.py)
Después: streamlit run app/app.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["create_database.py", "download_data.py", "load_staging.py", "run_profiling.py",
         "create_schema.py", "etl.py", "run_queries.py"]

for step in STEPS:
    print(f"\n===== {step} =====")
    if subprocess.run([sys.executable, str(HERE / step)]).returncode != 0:
        sys.exit(f"Falló {step}; se detiene el proceso.")
print("\nTodo listo. Arranca la app con:  streamlit run app/app.py")
