import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["create_database.py", "download_data.py", "load_staging.py", "run_profiling.py",
         "create_schema.py", "etl.py", "run_queries.py"]

for step in STEPS:
    print(f"\n{step}")
    if subprocess.run([sys.executable, str(HERE / step)]).returncode != 0:
        sys.exit(f"{step} failed; stopping.")
print("\nDone. Start the app with: python -m streamlit run app/app.py")
