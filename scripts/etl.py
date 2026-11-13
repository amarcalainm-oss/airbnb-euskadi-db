"""
Paso 5 - ETL: lee los CSV en bruto, limpia su FORMATO e inserta las filas en
las tablas ya creadas por sql/schema.sql.

Reglas del enunciado que cumple este script:
  * TODA la carga va en UNA transacción: si algo falla -> ROLLBACK y no queda
    nada a medias. (psycopg2 abre la transacción solo; nosotros hacemos
    commit() al final o rollback() si salta una excepción.)
  * Los valores que faltan se quedan en NULL. Nunca se inventa un valor.
  * Cada regla de limpieza cuenta cuántas filas toca; el resumen se escribe en
    docs/cleaning_report.md.
  * Python solo limpia formatos (texto -> número, fecha, booleano...). No
    filtra, agrupa ni calcula resultados: eso se hace en SQL.

Uso:
    python scripts/etl.py                   # carga normal
    python scripts/etl.py --simulate-error  # demostración de ROLLBACK
"""
import csv
import io
import json
import re
import sys
import time
from collections import Counter
from decimal import Decimal

from db import RAW_DIR, ROOT, get_connection

csv.field_size_limit(2**31 - 1)

REPORT = ROOT / "docs" / "cleaning_report.md"

# Contador: regla -> número de filas afectadas
stats: Counter = Counter()

RULES = {
    "R01": "Texto con doble codificación UTF-8 (mojibake, p. ej. 'GuipÃºzcoa' -> 'Guipúzcoa') reparado (nº de celdas)",
    "R02": "Cadena vacía convertida en NULL (anuncios con al menos una celda vacía en columnas cargadas)",
    "R03": "Precio en texto '$1,234.00' convertido a NUMERIC 1234.00",
    "R04": "Booleanos 't'/'f' convertidos a TRUE/FALSE (anuncios)",
    "R05": "bathrooms_text separado en bathrooms (número) y bathroom_shared (booleano)",
    "R06": "Coordenadas con más de 6 decimales redondeadas a 6 (≈0,1 m)",
    "R07": "Etiquetas HTML <br /> sustituidas por ' | ' en license",
    "R08": "Etiquetas HTML <br> sustituidas por salto de línea en description",
    "R09": "Etiquetas HTML <br> sustituidas por salto de línea en reviews.comments",
    "R10": "Antigüedad del anfitrión 'años + meses' convertida a meses totales",
    "R11": "listing con minimum_nights > maximum_nights: ambos se dejan a NULL (no se sabe cuál es erróneo)",
    "R12": "calendar con minimum_nights > maximum_nights: ambos se dejan a NULL",
    "R13": "amenities: lista JSON separada en filas de listing_amenity",
    "R14": "amenities: servicios repetidos dentro del mismo anuncio eliminados",
    "R15": "reviewer con varios nombres: se toma el de su reseña más reciente",
    "R16": "review id repetido en varios anuncios: se guarda una sola reseña (filas fusionadas)",
}

BR_RE = re.compile(r"<br\s*/?>", re.I)


# ----------------------------------------------------------------- helpers
def fix_mojibake(s: str | None, rule_key: str | None = None) -> str | None:
    """'GuipÃºzcoa' es 'Guipúzcoa' codificado en UTF-8 y leído como Latin-1.
    Deshacemos el error: volvemos a bytes Latin-1 y los leemos como UTF-8.
    Si el texto ya era correcto, esa conversión falla y lo dejamos igual."""
    if not s:
        return s
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    if fixed != s and rule_key:
        stats[rule_key] += 1
    return fixed


def nz(s: str | None) -> str | None:
    """'' -> None (NULL)."""
    if s is None:
        return None
    s = s.strip()
    return s if s else None


def to_bool(s: str | None) -> bool | None:
    s = nz(s)
    if s is None:
        return None
    if s not in ("t", "f"):
        raise ValueError(f"Booleano inesperado: {s!r}")
    return s == "t"


def to_int(s: str | None) -> int | None:
    s = nz(s)
    return None if s is None else int(Decimal(s))


def to_dec(s: str | None) -> Decimal | None:
    s = nz(s)
    return None if s is None else Decimal(s)


def parse_price(s: str | None) -> Decimal | None:
    s = nz(s)
    if s is None:
        return None
    if not re.fullmatch(r"\$\d{1,3}(,\d{3})*\.\d{2}", s):
        raise ValueError(f"Precio con formato inesperado: {s!r}")
    return Decimal(s[1:].replace(",", ""))


def parse_bathrooms(text: str | None):
    """'1.5 shared baths' -> (1.5, True); 'Half-bath' -> (0.5, None);
    '2 baths' -> (2, None)  (no dice si es compartido -> NULL, no se inventa)."""
    t = nz(text)
    if t is None:
        return None, None
    low = t.lower()
    shared = True if "shared" in low else False if "private" in low else None
    if "half-bath" in low:
        n = Decimal("0.5")
    elif low == "no bathroom":
        n = Decimal("0")
    else:
        m = re.match(r"^(\d+(\.\d+)?)", low)
        if not m:
            raise ValueError(f"bathrooms_text inesperado: {t!r}")
        n = Decimal(m.group(1))
    return n, shared


def round_coord(s: str) -> Decimal:
    d = Decimal(s)
    if -d.as_tuple().exponent > 6:
        stats["R06"] += 1
    return d.quantize(Decimal("0.000001"))


def copy_rows(cur, table: str, columns: list[str], rows) -> int:
    """Inserta muchas filas rápido con COPY ... FROM STDIN (sigue dentro de la
    MISMA transacción). None se escribe como celda vacía sin comillas = NULL."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    n = 0
    sql = f"COPY airbnb.{table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)"
    for row in rows:
        w.writerow(["" if v is None else ("t" if v is True else "f" if v is False else v) for v in row])
        n += 1
        if n % 200_000 == 0:
            buf.seek(0)
            cur.copy_expert(sql, buf)
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
    buf.seek(0)
    cur.copy_expert(sql, buf)
    return n


def read_csv(name: str):
    with open(RAW_DIR / f"{name}.csv", encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


# ---------------------------------------------------------- carga por tabla
def load_geography(cur) -> dict[str, int]:
    """province y municipality desde neighbourhoods.csv. Devuelve {municipio: id}."""
    rows = [(fix_mojibake(r["neighbourhood_group"], "R01"), fix_mojibake(r["neighbourhood"], "R01"))
            for r in read_csv("neighbourhoods")]
    prov_ids = {}
    for prov in sorted({p for p, _ in rows}):
        cur.execute("INSERT INTO airbnb.province (name) VALUES (%s) RETURNING province_id", (prov,))
        prov_ids[prov] = cur.fetchone()[0]
    mun_ids = {}
    for prov, mun in rows:
        cur.execute("INSERT INTO airbnb.municipality (name, province_id) VALUES (%s, %s) RETURNING municipality_id",
                    (mun, prov_ids[prov]))
        mun_ids[mun] = cur.fetchone()[0]
    print(f"  province: {len(prov_ids)}  municipality: {len(mun_ids)}")
    return mun_ids


LISTING_TEXT_COLS = ["name", "description", "host_name", "host_location", "host_about",
                     "neighbourhood_cleansed", "neighbourhood_group_cleansed", "property_type"]


def load_listings(cur, mun_ids: dict[str, int]) -> set[int]:
    raw = list(read_csv("listings"))

    # R02: contar celdas vacías en las columnas que SÍ se cargan
    used = ["description", "host_location", "host_about", "price", "minimum_nights", "maximum_nights",
            "has_availability", "bathrooms_text", "bedrooms", "beds", "license", "source",
            "estimated_revenue_l365d", "review_scores_rating"]
    for r in raw:
        if any(nz(r[c]) is None for c in used):
            stats["R02"] += 1
        for c in LISTING_TEXT_COLS:
            r[c] = fix_mojibake(r[c], "R01")

    # --- host (1 fila por host_id; los atributos son idénticos en todas sus filas)
    hosts = {}
    for r in raw:
        hid = int(r["host_id"])
        if hid in hosts:
            continue
        months_host = int(r["hosts_time_as_host_years"]) * 12 + int(r["hosts_time_as_host_months"])
        months_user = int(r["hosts_time_as_user_years"]) * 12 + int(r["hosts_time_as_user_months"])
        stats["R10"] += 1
        hosts[hid] = (hid, int(r["host_profile_id"]), r["host_name"].strip(), nz(r["host_location"]),
                      nz(r["host_about"]), to_bool(r["host_is_superhost"]), to_bool(r["host_has_profile_pic"]),
                      to_bool(r["host_identity_verified"]), int(r["host_listings_count"]), months_host, months_user)
    copy_rows(cur, "host", ["host_id", "host_profile_id", "name", "location", "about", "is_superhost",
                            "has_profile_pic", "identity_verified", "listings_count", "months_as_host",
                            "months_as_user"], hosts.values())
    stats["R04"] += len(raw)

    # --- property_type
    pt_ids = {}
    for pt in sorted({r["property_type"] for r in raw}):
        cur.execute("INSERT INTO airbnb.property_type (name) VALUES (%s) RETURNING property_type_id", (pt,))
        pt_ids[pt] = cur.fetchone()[0]

    # --- listing
    def listing_rows():
        for r in raw:
            price = parse_price(r["price"])
            if price is not None:
                stats["R03"] += 1
            baths, shared = parse_bathrooms(r["bathrooms_text"])
            if baths is not None:
                stats["R05"] += 1
            mn, mx = to_int(r["minimum_nights"]), to_int(r["maximum_nights"])
            if mn is not None and mx is not None and mn > mx:
                stats["R11"] += 1
                mn = mx = None
            lic = nz(r["license"])
            if lic and BR_RE.search(lic):
                stats["R07"] += 1
                lic = re.sub(r"(\s*\|\s*)+", " | ", BR_RE.sub(" | ", lic)).strip(" |")
            desc = nz(r["description"])
            if desc and BR_RE.search(desc):
                stats["R08"] += 1
                desc = BR_RE.sub("\n", desc)
            yield (int(r["id"]), int(r["host_id"]), mun_ids[r["neighbourhood_cleansed"]],
                   pt_ids[r["property_type"]], r["name"].strip(), desc,
                   round_coord(r["latitude"]), round_coord(r["longitude"]), r["room_type"],
                   int(r["accommodates"]), baths, shared, nz(r["bathrooms_text"]),
                   to_int(r["bedrooms"]), to_int(r["beds"]), price, mn, mx, to_bool(r["has_availability"]),
                   to_dec(r["review_scores_rating"]), to_dec(r["review_scores_accuracy"]),
                   to_dec(r["review_scores_cleanliness"]), to_dec(r["review_scores_checkin"]),
                   to_dec(r["review_scores_communication"]), to_dec(r["review_scores_location"]),
                   to_dec(r["review_scores_value"]), lic, to_int(r["estimated_occupancy_l365d"]),
                   to_dec(r["estimated_revenue_l365d"]), nz(r["source"]), r["last_scraped"])

    n = copy_rows(cur, "listing", [
        "listing_id", "host_id", "municipality_id", "property_type_id", "name", "description",
        "latitude", "longitude", "room_type", "accommodates", "bathrooms", "bathroom_shared",
        "bathrooms_text", "bedrooms", "beds", "price", "minimum_nights", "maximum_nights",
        "has_availability", "score_rating", "score_accuracy", "score_cleanliness", "score_checkin",
        "score_communication", "score_location", "score_value", "license",
        "estimated_occupancy_l365d", "estimated_revenue_l365d", "source", "last_scraped"], listing_rows())

    # --- amenity + listing_amenity
    pairs, names = [], set()
    for r in raw:
        items = json.loads(r["amenities"])
        if items:
            stats["R13"] += 1
        clean = [a.strip() for a in items if a.strip()]
        if len(set(clean)) < len(clean):
            stats["R14"] += 1
        for a in dict.fromkeys(clean):  # quita repetidos conservando el orden
            names.add(a)
            pairs.append((int(r["id"]), a))
    am_ids = {}
    for a in sorted(names):
        cur.execute("INSERT INTO airbnb.amenity (name) VALUES (%s) RETURNING amenity_id", (a,))
        am_ids[a] = cur.fetchone()[0]
    copy_rows(cur, "listing_amenity", ["listing_id", "amenity_id"], ((l, am_ids[a]) for l, a in pairs))

    print(f"  host: {len(hosts)}  property_type: {len(pt_ids)}  listing: {n}  "
          f"amenity: {len(am_ids)}  listing_amenity: {len(pairs)}")
    return {int(r["id"]) for r in raw}


def load_calendar(cur) -> None:
    def rows():
        for r in read_csv("calendar"):
            mn, mx = int(r["minimum_nights"]), int(r["maximum_nights"])
            if mn > mx:
                stats["R12"] += 1
                mn = mx = None
            yield int(r["listing_id"]), r["date"], to_bool(r["available"]), mn, mx
    n = copy_rows(cur, "calendar_day", ["listing_id", "day", "available", "minimum_nights", "maximum_nights"], rows())
    print(f"  calendar_day: {n}")


def load_reviews(cur) -> None:
    reviewers: dict[int, tuple[str, str]] = {}   # id -> (fecha, nombre) más reciente
    names_seen: dict[int, set] = {}
    reviews: dict[int, tuple] = {}
    links = []
    for r in read_csv("reviews"):
        rid, uid, day = int(r["id"]), int(r["reviewer_id"]), r["date"]
        name = fix_mojibake(r["reviewer_name"].strip(), "R01")
        names_seen.setdefault(uid, set()).add(name)
        if uid not in reviewers or day >= reviewers[uid][0]:
            reviewers[uid] = (day, name)
        links.append((int(r["listing_id"]), rid))
        if rid in reviews:
            stats["R16"] += 1
            continue
        text = fix_mojibake(r["comments"], "R01")
        if BR_RE.search(text):
            stats["R09"] += 1
            text = BR_RE.sub("\n", text)
        reviews[rid] = (rid, uid, day, text)
    stats["R15"] = sum(1 for v in names_seen.values() if len(v) > 1)

    copy_rows(cur, "reviewer", ["reviewer_id", "name"], ((k, v[1]) for k, v in reviewers.items()))
    copy_rows(cur, "review", ["review_id", "reviewer_id", "review_date", "comments"], reviews.values())
    copy_rows(cur, "listing_review", ["listing_id", "review_id"], links)
    print(f"  reviewer: {len(reviewers)}  review: {len(reviews)}  listing_review: {len(links)}")


# ------------------------------------------------------------------ main
def table_counts(cur) -> list[tuple[str, int]]:
    out = []
    for t in ["province", "municipality", "host", "property_type", "listing", "amenity",
              "listing_amenity", "calendar_day", "reviewer", "review", "listing_review"]:
        cur.execute(f"SELECT COUNT(*) FROM airbnb.{t}")
        out.append((t, cur.fetchone()[0]))
    return out


def write_report(counts) -> None:
    lines = ["# Informe de limpieza (ETL)", "",
             "_Generado automáticamente por `scripts/etl.py`._", "",
             "## Reglas de limpieza y filas afectadas", "",
             "| Regla | Descripción | Filas afectadas |", "|---|---|---|"]
    lines += [f"| {k} | {v.replace('|', chr(92) + '|')} | {stats.get(k, 0):,} |" for k, v in RULES.items()]
    lines += ["", "## Filas cargadas por tabla", "", "| Tabla | Filas |", "|---|---|"]
    lines += [f"| {t} | {n:,} |" for t, n in counts]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    simulate_error = "--simulate-error" in sys.argv
    conn = get_connection()          # autocommit = False -> transacción abierta
    t0 = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM airbnb.listing")
            if cur.fetchone()[0] > 0:
                raise RuntimeError("Las tablas ya tienen datos. Ejecuta antes: python scripts/create_schema.py")
            print("Cargando (una sola transacción)...")
            mun_ids = load_geography(cur)
            load_listings(cur, mun_ids)
            load_calendar(cur)
            load_reviews(cur)
            if simulate_error:
                print("\n>>> SIMULACIÓN: insertamos una reseña de un anuncio que NO existe (viola la FOREIGN KEY)...")
                cur.execute("INSERT INTO airbnb.listing_review (listing_id, review_id) VALUES (-1, -1)")
            counts = table_counts(cur)
        conn.commit()                # <-- solo aquí se guarda todo
        write_report(counts)
        print(f"\nCOMMIT correcto en {time.time()-t0:.0f}s. Informe: {REPORT.relative_to(ROOT)}")
    except Exception as e:
        conn.rollback()              # <-- se deshace TODO lo insertado
        print(f"\nERROR: {type(e).__name__}: {e}".rstrip())
        print("ROLLBACK ejecutado. Comprobamos que no ha quedado nada cargado:")
        with get_connection() as check, check.cursor() as cur:
            for t, n in table_counts(cur):
                print(f"    {t:16} {n} filas")
        check.close()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
