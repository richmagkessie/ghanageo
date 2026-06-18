#!/usr/bin/env python3
"""
Spatially reassign all towns to the correct district using the geoBoundaries
Ghana ADM2 polygon file. This corrects the admin2-code approach which used
pre-2019 district boundaries and misassigns places in the 6 regions carved
out in 2019 (Oti, Savannah, North East, Bono East, Ahafo, Western North).

Only towns that have coordinates are reassigned. Manual towns (no coordinates)
are left untouched.

Run: python3 scripts/reassign_spatial.py
"""

import json
import sqlite3
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.strtree import STRtree

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "ghanageo" / "data" / "ghana.db"
GEOJSON_PATH = Path(__file__).parent / "cache" / "GHA_ADM2.geojson"


def _norm(name: str) -> str:
    name = name.strip().lower()
    for suffix in (
        " metropolitan assembly", " municipal assembly", " district assembly",
        " metropolitan", " municipal", " district", " metro", " assembly",
    ):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name.strip().replace("-", " ")


def build_spatial_index(conn):
    """Build STRtree from geoBoundaries polygons. Returns (tree, polygons list)."""
    with open(GEOJSON_PATH) as f:
        gj = json.load(f)

    # Build district lookup: normalised_name → district row
    db_districts = {}
    for row in conn.execute(
        "SELECT id, name, region_id, region_name FROM districts"
    ).fetchall():
        db_districts[_norm(row[1])] = {
            "id": row[0], "name": row[1],
            "region_id": row[2], "region_name": row[3],
        }

    polygons = []  # list of (shapely_geom, district_info)
    unmatched = []

    for feat in gj["features"]:
        shape_name = feat["properties"].get("shapeName", "")
        norm = _norm(shape_name)
        dist = db_districts.get(norm)
        if not dist:
            # Try partial match
            for key, val in db_districts.items():
                if norm and (norm in key or key in norm):
                    dist = val
                    break
        if not dist:
            unmatched.append(shape_name)
            continue
        try:
            geom = shape(feat["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)
            polygons.append((geom, dist))
        except Exception:
            pass

    if unmatched:
        print(f"  Warning: {len(unmatched)} boundary features not matched to DB districts")
        for n in unmatched[:10]:
            print(f"    - {n}")

    geoms = [p[0] for p in polygons]
    tree = STRtree(geoms)
    print(f"  Spatial index built: {len(polygons)} polygons")
    return tree, polygons


def find_district(lat, lng, tree, polygons):
    pt = Point(lng, lat)  # Shapely uses (lng, lat)
    candidates = tree.query(pt)
    for idx in candidates:
        geom, dist = polygons[idx]
        if geom.contains(pt):
            return dist
    # Fallback: nearest centroid
    if len(polygons) == 0:
        return None
    best = min(polygons, key=lambda p: p[0].centroid.distance(pt))
    return best[1]


def main():
    print("=" * 60)
    print("  GhanaGeo — Spatial District Reassignment")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)

    print("\n[1/3] Building spatial index from geoBoundaries GeoJSON...")
    tree, polygons = build_spatial_index(conn)

    print("\n[2/3] Loading towns with coordinates...")
    rows = conn.execute(
        "SELECT id, name, coordinates FROM towns WHERE coordinates IS NOT NULL"
    ).fetchall()
    print(f"  {len(rows):,} towns have coordinates")

    print("\n[3/3] Reassigning...")
    updated = 0
    unchanged = 0
    total = len(rows)

    for i, (town_id, name, coords_json) in enumerate(rows):
        if i % 1000 == 0:
            pct = i * 100 // total
            print(f"  {i:,}/{total:,} ({pct}%)  updated={updated:,}", end="\r")

        try:
            coords = json.loads(coords_json)
            lat, lng = coords["lat"], coords["lng"]
        except Exception:
            continue

        dist = find_district(lat, lng, tree, polygons)
        if not dist:
            continue

        conn.execute(
            """UPDATE towns
               SET district_id=?, district_name=?, region_id=?, region_name=?
               WHERE id=?""",
            (dist["id"], dist["name"], dist["region_id"], dist["region_name"], town_id),
        )
        conn.execute(
            """UPDATE towns SET id=?
               WHERE id=? AND id != ?""",
            (
                f"{dist['id']}-GN{town_id.split('-GN')[-1]}" if "-GN" in town_id else town_id,
                town_id,
                f"{dist['id']}-GN{town_id.split('-GN')[-1]}" if "-GN" in town_id else town_id,
            ),
        )
        if town_id.split("-")[0] != dist["id"].split("-")[0]:
            updated += 1
        else:
            unchanged += 1

    conn.commit()
    print(f"\n  Reassigned: {updated:,} towns moved to correct district")
    print(f"  Unchanged : {unchanged:,} towns already in correct district")

    print("\n  Breakdown by region:")
    for row in conn.execute("""
        SELECT region_name, COUNT(*) cnt
        FROM towns GROUP BY region_id ORDER BY cnt DESC
    """).fetchall():
        print(f"    {row[0]}: {row[1]:,}")

    conn.close()
    print("\n  Done. Commit the updated ghana.db to deploy.\n")


if __name__ == "__main__":
    main()
