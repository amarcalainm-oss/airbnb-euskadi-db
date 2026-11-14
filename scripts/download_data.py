"""
Paso 1 - Descarga de los datos en bruto (raw data).

El enunciado exige que los datos NO se suban a git, sino que se descarguen con
un script. Este script baja los ficheros de Inside Airbnb (Euskadi, scrape del
25-09-2026) a la carpeta data/raw/ y descomprime los .gz.

Fuente : https://insideairbnb.com/get-the-data/  (sección "Euskadi")
Licencia: Creative Commons Attribution 4.0 International (CC BY 4.0)

Uso:
    python scripts/download_data.py           # descarga lo que falte
    python scripts/download_data.py --force   # vuelve a descargarlo todo
"""
import gzip
import shutil
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://data.insideairbnb.com/spain/pv/euskadi/2026-09-25"

# (ruta remota, nombre local). Los .gz se descomprimen al bajarlos.
FILES = [
    ("data/listings.csv.gz", "listings.csv"),        # anuncios, versión detallada (79 columnas)
    ("data/calendar.csv.gz", "calendar.csv"),        # disponibilidad diaria de cada anuncio (365 días)
    ("data/reviews.csv.gz", "reviews.csv"),          # reseñas con texto completo
    ("visualisations/neighbourhoods.csv", "neighbourhoods.csv"),  # municipios y provincias
]

# No se importa db.py: este paso no necesita psycopg2 ni .env
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"


def download(remote: str, local_name: str, force: bool) -> None:
    target = RAW_DIR / local_name
    if target.exists() and not force:
        print(f"  [ok]   {local_name} ya existe, se omite")
        return
    url = f"{BASE_URL}/{remote}"
    tmp = RAW_DIR / (Path(remote).name + ".part")
    print(f"  [get]  {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "tecnun-projectB-downloader"})
    with urllib.request.urlopen(req) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out)
    if remote.endswith(".gz"):
        with gzip.open(tmp, "rb") as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        tmp.unlink()
    else:
        tmp.replace(target)
    print(f"  [save] {target.relative_to(ROOT)} ({target.stat().st_size/1e6:.1f} MB)")


def main() -> None:
    force = "--force" in sys.argv
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Descargando en {RAW_DIR}")
    for remote, local in FILES:
        download(remote, local, force)
    print("Descarga terminada.")


if __name__ == "__main__":
    main()
