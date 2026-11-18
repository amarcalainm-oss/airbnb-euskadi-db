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

stats: Counter = Counter()

RULES = {
    "R01": "Double-encoded UTF-8 text (mojibake, e.g. 'GuipÃºzcoa' -> 'Guipúzcoa') repaired (cells)",
    "R02": "Empty string stored as NULL (listings with at least one empty cell in a loaded column)",
    "R03": "Price text '$1,234.00' converted to NUMERIC 1234.00",
    "R04": "Booleans 't'/'f' converted to TRUE/FALSE (listings)",
    "R05": "bathrooms_text split into bathrooms (number) and bathroom_shared (boolean)",
    "R06": "Coordinates with more than 6 decimals rounded to 6 (about 0.1 m)",
    "R07": "HTML <br /> tags replaced by ' | ' in license",
    "R08": "HTML <br> tags replaced by a line break in description",
    "R09": "HTML <br> tags replaced by a line break in reviews.comments",
    "R10": "Host seniority 'years + months' converted to total months",
    "R11": "listing with minimum_nights > maximum_nights: both set to NULL (it is unknown which one is wrong)",
    "R12": "calendar day with minimum_nights > maximum_nights: both set to NULL",
    "R13": "amenities: JSON list split into listing_amenity rows",
    "R14": "amenities: amenity repeated within the same listing removed",
    "R15": "reviewer with several names: the name of the most recent review is kept",
    "R16": "review id repeated on several listings: one review stored (rows merged)",
}

BR_RE = re.compile(r"<br\s*/?>", re.I)

TABLES = ["province", "municipality", "host", "property_type", "listing", "amenity",
          "listing_amenity", "calendar_day", "reviewer", "review", "listing_review"]

# Columns repaired by R01
LISTING_TEXT_COLS = ["name", "description", "host_name", "host_location", "host_about",
                     "neighbourhood_cleansed", "neighbourhood_group_cleansed", "property_type"]

# Columns whose empty cells are counted by R02
LISTING_NULLABLE_COLS = ["description", "host_location", "host_about", "price", "minimum_nights",
                         "maximum_nights", "has_availability", "bedrooms", "beds",
                         "license", "estimated_revenue_l365d", "review_scores_rating"]


def fix_mojibake(s: str | None) -> str | None:
    """R01: repairs UTF-8 text that was read as Latin-1."""
    if not s:
        return s
    try:
        fixed = s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s
    if fixed != s:
        stats["R01"] += 1
    return fixed


def nz(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    return s if s else None


def to_bool(s: str | None) -> bool | None:
    s = nz(s)
    if s is None:
        return None
    if s not in ("t", "f"):
        raise ValueError(f"Unexpected boolean: {s!r}")
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
        raise ValueError(f"Unexpected price format: {s!r}")
    return Decimal(s[1:].replace(",", ""))


def parse_bathrooms(text: str | None) -> tuple[Decimal | None, bool | None]:
    """'1.5 shared baths' -> (1.5, True); None when it does not say whether it is shared."""
    t = nz(text)
    if t is None:
        return None, None
    low = t.lower()
    if "shared" in low:
        shared = True
    elif "private" in low:
        shared = False
    else:
        shared = None
    if "half-bath" in low:
        n = Decimal("0.5")
    elif low == "no bathroom":
        n = Decimal("0")
    else:
        m = re.match(r"^(\d+(\.\d+)?)", low)
        if not m:
            raise ValueError(f"Unexpected bathrooms_text: {t!r}")
        n = Decimal(m.group(1))
    return n, shared


def round_coord(s: str) -> Decimal:
    d = Decimal(s)
    if -d.as_tuple().exponent > 6:
        stats["R06"] += 1
    return d.quantize(Decimal("0.000001"))


def total_months(years: str, months: str) -> int:
    return int(years) * 12 + int(months)


def csv_cell(v):
    """None -> empty cell, which COPY reads as NULL."""
    if v is None:
        return ""
    if v is True:
        return "t"
    if v is False:
        return "f"
    return v


def copy_rows(cur, table: str, columns: list[str], rows) -> int:
    """COPY in blocks of 200,000 rows; returns how many were inserted."""
    sql = f"COPY airbnb.{table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv)"
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    n = 0
    for row in rows:
        writer.writerow([csv_cell(v) for v in row])
        n += 1
        if n % 200_000 == 0:
            buf.seek(0)
            cur.copy_expert(sql, buf)
            buf.seek(0)
            buf.truncate()
    buf.seek(0)
    cur.copy_expert(sql, buf)
    return n


def insert_returning_id(cur, sql: str, params: tuple) -> int:
    cur.execute(sql, params)
    return cur.fetchone()[0]


def read_csv(name: str):
    with open(RAW_DIR / f"{name}.csv", encoding="utf-8", newline="") as f:
        yield from csv.DictReader(f)


def load_geography(cur) -> dict[str, int]:
    """Returns {municipality: id}."""
    rows = [(fix_mojibake(r["neighbourhood_group"]), fix_mojibake(r["neighbourhood"]))
            for r in read_csv("neighbourhoods")]
    prov_ids = {
        prov: insert_returning_id(cur, "INSERT INTO airbnb.province (name) VALUES (%s) RETURNING province_id",
                                  (prov,))
        for prov in sorted({p for p, _ in rows})
    }
    mun_ids = {
        mun: insert_returning_id(cur, "INSERT INTO airbnb.municipality (name, province_id) "
                                      "VALUES (%s, %s) RETURNING municipality_id", (mun, prov_ids[prov]))
        for prov, mun in rows
    }
    print(f"  province: {len(prov_ids)}  municipality: {len(mun_ids)}")
    return mun_ids


def load_listings(cur, mun_ids: dict[str, int]) -> None:
    raw = list(read_csv("listings"))
    for r in raw:
        if any(nz(r[c]) is None for c in LISTING_NULLABLE_COLS):
            stats["R02"] += 1
        for c in LISTING_TEXT_COLS:
            r[c] = fix_mojibake(r[c])

    hosts = {}
    for r in raw:
        hid = int(r["host_id"])
        if hid in hosts:
            continue
        months_host = total_months(r["hosts_time_as_host_years"], r["hosts_time_as_host_months"])
        months_user = total_months(r["hosts_time_as_user_years"], r["hosts_time_as_user_months"])
        stats["R10"] += 1
        hosts[hid] = (hid, int(r["host_profile_id"]), r["host_name"].strip(), nz(r["host_location"]),
                      nz(r["host_about"]), to_bool(r["host_is_superhost"]), to_bool(r["host_has_profile_pic"]),
                      to_bool(r["host_identity_verified"]), int(r["host_listings_count"]), months_host, months_user)
    copy_rows(cur, "host", ["host_id", "host_profile_id", "name", "location", "about", "is_superhost",
                            "has_profile_pic", "identity_verified", "listings_count", "months_as_host",
                            "months_as_user"], hosts.values())
    stats["R04"] += len(raw)

    pt_ids = {
        pt: insert_returning_id(cur, "INSERT INTO airbnb.property_type (name) VALUES (%s) "
                                     "RETURNING property_type_id", (pt,))
        for pt in sorted({r["property_type"] for r in raw})
    }

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
                   int(r["accommodates"]), baths, shared,
                   to_int(r["bedrooms"]), to_int(r["beds"]), price, mn, mx, to_bool(r["has_availability"]),
                   to_dec(r["review_scores_rating"]), to_dec(r["review_scores_accuracy"]),
                   to_dec(r["review_scores_cleanliness"]), to_dec(r["review_scores_checkin"]),
                   to_dec(r["review_scores_communication"]), to_dec(r["review_scores_location"]),
                   to_dec(r["review_scores_value"]), lic, to_int(r["estimated_occupancy_l365d"]),
                   to_dec(r["estimated_revenue_l365d"]), r["last_scraped"])

    n = copy_rows(cur, "listing", [
        "listing_id", "host_id", "municipality_id", "property_type_id", "name", "description",
        "latitude", "longitude", "room_type", "accommodates", "bathrooms", "bathroom_shared",
        "bedrooms", "beds", "price", "minimum_nights", "maximum_nights",
        "has_availability", "score_rating", "score_accuracy", "score_cleanliness", "score_checkin",
        "score_communication", "score_location", "score_value", "license",
        "estimated_occupancy_l365d", "estimated_revenue_l365d", "last_scraped"], listing_rows())

    pairs, names = [], set()
    for r in raw:
        items = json.loads(r["amenities"])
        if items:
            stats["R13"] += 1
        clean = [a.strip() for a in items if a.strip()]
        if len(set(clean)) < len(clean):
            stats["R14"] += 1
        for a in dict.fromkeys(clean):
            names.add(a)
            pairs.append((int(r["id"]), a))
    am_ids = {
        a: insert_returning_id(cur, "INSERT INTO airbnb.amenity (name) VALUES (%s) RETURNING amenity_id", (a,))
        for a in sorted(names)
    }
    copy_rows(cur, "listing_amenity", ["listing_id", "amenity_id"], ((l, am_ids[a]) for l, a in pairs))

    print(f"  host: {len(hosts)}  property_type: {len(pt_ids)}  listing: {n}  "
          f"amenity: {len(am_ids)}  listing_amenity: {len(pairs)}")


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
    reviewers: dict[int, tuple[str, str]] = {}  # id -> most recent (date, name)
    names_seen: dict[int, set] = {}
    reviews: dict[int, tuple] = {}
    links = []
    for r in read_csv("reviews"):
        rid, uid, day = int(r["id"]), int(r["reviewer_id"]), r["date"]
        name = fix_mojibake(r["reviewer_name"].strip())
        names_seen.setdefault(uid, set()).add(name)
        if uid not in reviewers or day >= reviewers[uid][0]:
            reviewers[uid] = (day, name)
        links.append((int(r["listing_id"]), rid))
        if rid in reviews:
            stats["R16"] += 1
            continue
        text = fix_mojibake(r["comments"])
        if BR_RE.search(text):
            stats["R09"] += 1
            text = BR_RE.sub("\n", text)
        reviews[rid] = (rid, uid, day, text)
    stats["R15"] = sum(1 for v in names_seen.values() if len(v) > 1)

    copy_rows(cur, "reviewer", ["reviewer_id", "name"], ((uid, name) for uid, (_, name) in reviewers.items()))
    copy_rows(cur, "review", ["review_id", "reviewer_id", "review_date", "comments"], reviews.values())
    copy_rows(cur, "listing_review", ["listing_id", "review_id"], links)
    print(f"  reviewer: {len(reviewers)}  review: {len(reviews)}  listing_review: {len(links)}")


def table_counts(cur) -> list[tuple[str, int]]:
    counts = []
    for t in TABLES:
        cur.execute(f"SELECT COUNT(*) FROM airbnb.{t}")
        counts.append((t, cur.fetchone()[0]))
    return counts


def write_report(counts: list[tuple[str, int]]) -> None:
    lines = ["# Cleaning report (ETL)", "",
             "_Generated by `scripts/etl.py`._", "",
             "## Cleaning rules and rows affected", "",
             "| Rule | Description | Rows affected |", "|---|---|---|"]
    for key, desc in RULES.items():
        desc = desc.replace("|", "\\|")
        lines.append(f"| {key} | {desc} | {stats.get(key, 0):,} |")
    lines += ["", "## Rows loaded per table", "", "| Table | Rows |", "|---|---|"]
    lines += [f"| {t} | {n:,} |" for t, n in counts]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    simulate_error = "--simulate-error" in sys.argv
    conn = get_connection()
    t0 = time.time()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM airbnb.listing")
            if cur.fetchone()[0] > 0:
                raise RuntimeError("The tables already contain data; run scripts/create_schema.py first")
            print("Loading (single transaction)...")
            mun_ids = load_geography(cur)
            load_listings(cur, mun_ids)
            load_calendar(cur)
            load_reviews(cur)
            if simulate_error:
                print("\n>>> SIMULATION: inserting a review for a listing that does NOT exist (violates the FOREIGN KEY)...")
                cur.execute("INSERT INTO airbnb.listing_review (listing_id, review_id) VALUES (-1, -1)")
            counts = table_counts(cur)
        conn.commit()
        # Without statistics after the bulk load, query plans are very slow
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE")
        write_report(counts)
        print(f"\nCOMMIT done in {time.time()-t0:.0f}s. Report: {REPORT.relative_to(ROOT)}")
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {type(e).__name__}: {e}".rstrip())
        print("ROLLBACK done. Checking that nothing was left loaded:")
        check = get_connection()
        try:
            with check.cursor() as cur:
                for t, n in table_counts(cur):
                    print(f"    {t:16} {n} rows")
        finally:
            check.close()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
