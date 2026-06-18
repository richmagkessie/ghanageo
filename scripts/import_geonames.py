#!/usr/bin/env python3
"""
Import all Ghana settlements from GeoNames into the database.

Strategy:
  1. Primary: GeoNames admin2 code → district name → our district_id (fuzzy match)
  2. Fallback: nearest district capital by coordinate (for places with missing admin2)

This avoids needing boundary shapefiles entirely.

Run: python3 scripts/import_geonames.py
"""

import io
import json
import math
import sqlite3
import sys
import zipfile
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "ghanageo" / "data" / "ghana.db"
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

GEONAMES_URL = "https://download.geonames.org/export/dump/GH.zip"
ADMIN2_URL = "https://download.geonames.org/export/dump/admin2Codes.txt"

FEATURE_TYPE_MAP = {
    "PPLC": "City",
    "PPLA": "City",
    "PPLA2": "Town",
    "PPLA3": "Town",
    "PPLA4": "Town",
    "PPL":  "Town",
    "PPLX": "Community",
    "PPLF": "Village",
    "PPLS": "Village",
    "PPLW": "Village",
    "PPLQ": "Village",
    "PPLG": "Community",
    "STLMT": "Community",
}


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------

def _get_text(url: str, cache_file: Path) -> str:
    if cache_file.exists():
        print(f"  [cache] {cache_file.name}")
        return cache_file.read_text(encoding="utf-8")
    print(f"  Downloading {url} ...")
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    text = r.text
    cache_file.write_text(text, encoding="utf-8")
    print(f"  Saved ({len(text)//1024} KB)")
    return text


def load_geonames_places() -> list:
    txt_cache = CACHE_DIR / "GH.txt"
    if txt_cache.exists():
        print("  [cache] GeoNames GH.txt")
        raw = txt_cache.read_text(encoding="utf-8")
    else:
        print("  Downloading GeoNames GH.zip ...")
        r = requests.get(GEONAMES_URL, timeout=60)
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            raw = z.read("GH.txt").decode("utf-8")
        txt_cache.write_text(raw, encoding="utf-8")
        print(f"  Saved ({len(raw)//1024} KB)")

    places = []
    for line in raw.strip().split("\n"):
        cols = line.split("\t")
        if len(cols) < 15 or cols[6] != "P":
            continue
        try:
            lat = float(cols[4])
            lng = float(cols[5])
        except ValueError:
            continue
        pop = None
        try:
            p = int(cols[14])
            pop = p if p > 0 else None
        except (ValueError, IndexError):
            pass
        feature_code = cols[7]
        places.append({
            "geonames_id": cols[0],
            "name": cols[1].strip(),
            "lat": lat,
            "lng": lng,
            "feature_code": feature_code,
            "type": FEATURE_TYPE_MAP.get(feature_code, "Town"),
            "population": pop,
            "admin1": cols[10].strip(),
            "admin2": cols[11].strip(),
        })

    print(f"  Parsed {len(places):,} populated places")
    return places


def load_admin2_map() -> dict:
    """Returns dict: (admin1_code, admin2_code) → district_name"""
    text = _get_text(ADMIN2_URL, CACHE_DIR / "admin2Codes.txt")
    mapping = {}
    for line in text.strip().split("\n"):
        cols = line.split("\t")
        if not cols[0].startswith("GH."):
            continue
        parts = cols[0].split(".")
        if len(parts) < 3:
            continue
        admin1 = parts[1]
        admin2 = parts[2]
        name = cols[1].strip() if len(cols) > 1 else ""
        if name:
            mapping[(admin1, admin2)] = name
    print(f"  Loaded {len(mapping)} Ghana admin2 entries")
    return mapping


# ---------------------------------------------------------------------------
# District matching
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    name = name.strip().lower()
    for s in (" metropolitan assembly", " municipal assembly",
              " district assembly", " metropolitan", " municipal",
              " district", " metro", " assembly", "-"):
        name = name.replace(s, " ") if s == "-" else (
            name[:-len(s)] if name.endswith(s) else name
        )
    return name.strip()


def build_district_lookup(conn: sqlite3.Connection):
    """
    Returns:
      lookup: normalised_name → district_info dict
      capitals: list of (lat, lng, district_info) for fallback
    """
    lookup = {}
    capitals = []
    rows = conn.execute(
        "SELECT id, name, region_id, region_name, coordinates FROM districts"
    ).fetchall()
    for row in rows:
        d = {"id": row[0], "name": row[1], "region_id": row[2], "region_name": row[3]}
        lookup[_norm(row[1])] = d
        if row[4]:
            coords = json.loads(row[4])
            capitals.append((coords["lat"], coords["lng"], d))
    return lookup, capitals


def match_name(name: str, lookup: dict):
    norm = _norm(name)
    if norm in lookup:
        return lookup[norm]
    for key, val in lookup.items():
        if norm and (norm in key or key in norm):
            return val
    return None


def nearest_district(lat: float, lng: float, capitals: list):
    """Return the district whose capital is closest to (lat, lng)."""
    best = None
    best_d = float("inf")
    for clat, clng, info in capitals:
        # Approximate distance (no need for exact geodesic)
        d = math.sqrt((lat - clat) ** 2 + (lng - clng) ** 2)
        if d < best_d:
            best_d = d
            best = info
    return best


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_places(conn, places, admin2_map, district_lookup, capitals) -> int:
    existing = set(
        (r[0].lower(), r[1])
        for r in conn.execute("SELECT name, district_id FROM towns").fetchall()
    )

    inserted = 0
    by_admin2 = 0
    by_nearest = 0
    skipped_dupe = 0
    total = len(places)

    for i, place in enumerate(places):
        if i % 1000 == 0:
            pct = i * 100 // total
            print(f"  {i:,}/{total:,} ({pct}%)  inserted={inserted:,}", end="\r")

        dist = None

        # Stage 1: admin2 code lookup
        admin2_name = admin2_map.get((place["admin1"], place["admin2"]))
        if admin2_name:
            dist = match_name(admin2_name, district_lookup)

        # Stage 2: nearest capital fallback
        if not dist:
            dist = nearest_district(place["lat"], place["lng"], capitals)
            if dist:
                by_nearest += 1
        else:
            by_admin2 += 1

        if not dist:
            continue

        key = (place["name"].lower(), dist["id"])
        if key in existing:
            skipped_dupe += 1
            continue

        town_id = f"{dist['id']}-GN{place['geonames_id']}"
        coords_json = json.dumps({"lat": place["lat"], "lng": place["lng"]})

        conn.execute(
            """INSERT OR IGNORE INTO towns
               (id, name, district_id, district_name, region_id, region_name,
                type, population, coordinates)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                town_id, place["name"],
                dist["id"], dist["name"],
                dist["region_id"], dist["region_name"],
                place["type"], place["population"], coords_json,
            ),
        )
        existing.add(key)
        inserted += 1

    conn.commit()
    print(f"\n  Done — {inserted:,} inserted")
    print(f"    by admin2 code : {by_admin2:,}")
    print(f"    by nearest cap : {by_nearest:,}")
    print(f"    duplicates skip: {skipped_dupe:,}")
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  GhanaGeo — Full Country Towns Import")
    print("=" * 60)

    print("\n[1/4] Loading GeoNames places...")
    places = load_geonames_places()

    print("\n[2/4] Loading GeoNames admin2 code table...")
    admin2_map = load_admin2_map()

    print("\n[3/4] Loading district lookup from database...")
    conn = sqlite3.connect(DB_PATH)
    district_lookup, capitals = build_district_lookup(conn)
    print(f"  {len(district_lookup)} districts, {len(capitals)} with coordinates")

    print("\n[4/4] Importing settlements...")
    import_places(conn, places, admin2_map, district_lookup, capitals)

    total = conn.execute("SELECT COUNT(*) FROM towns").fetchone()[0]
    print(f"\n  Total towns in database: {total:,}")

    print("\n  Breakdown by region:")
    for row in conn.execute("""
        SELECT region_name, COUNT(*) cnt
        FROM towns GROUP BY region_id ORDER BY cnt DESC
    """).fetchall():
        print(f"    {row[0]}: {row[1]:,}")

    conn.close()
    print("\n  All done. Commit the updated ghana.db to deploy.\n")


if __name__ == "__main__":
    main()
