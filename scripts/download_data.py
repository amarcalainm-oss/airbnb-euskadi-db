import gzip
import shutil
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://data.insideairbnb.com/spain/pv/euskadi/2026-09-25"

FILES = [
    ("data/listings.csv.gz", "listings.csv"),
    ("data/calendar.csv.gz", "calendar.csv"),
    ("data/reviews.csv.gz", "reviews.csv"),
    ("visualisations/neighbourhoods.csv", "neighbourhoods.csv"),
    ("visualisations/neighbourhoods.geojson", "neighbourhoods.geojson"),
]

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"


def download(remote: str, local_name: str, force: bool) -> None:
    target = RAW_DIR / local_name
    if target.exists() and not force:
        print(f"  [ok]   {local_name} already exists, skipped")
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
    print(f"Downloading into {RAW_DIR}")
    for remote, local in FILES:
        download(remote, local, force)
    print("Download finished.")


if __name__ == "__main__":
    main()
