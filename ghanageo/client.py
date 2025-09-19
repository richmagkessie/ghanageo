# ghanageo/client.py
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Any


class GhanaGeo:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Use the bundled database
            db_path = Path(__file__).parent / "data" / "ghana.db"
        self.db_path = Path(db_path)

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert sqlite Row to dict and parse JSON fields."""
        record = dict(row)
        if "coordinates" in record and record["coordinates"]:
            try:
                record["coordinates"] = json.loads(record["coordinates"])
            except json.JSONDecodeError:
                record["coordinates"] = None
        return record

    def get_regions(self) -> List[Dict]:
        """Get all Ghana regions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM regions ORDER BY name")
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_region(self, region_id: str) -> Optional[Dict]:
        """Get specific region by ID or code."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM regions WHERE id = ? OR code = ?",
                (region_id, region_id),
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def get_districts(self, region: Optional[str] = None) -> List[Dict]:
        """Get districts, optionally filtered by region code/ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if region:
                cursor = conn.execute(
                    "SELECT * FROM districts WHERE region_id = ? ORDER BY name",
                    (region,),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM districts ORDER BY region_name, name"
                )
            return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_district(self, district_id: str) -> Optional[Dict]:
        """Get specific district by ID or code."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM districts WHERE id = ? OR code = ?",
                (district_id, district_id),
            )
            row = cursor.fetchone()
            return self._row_to_dict(row) if row else None

    def search(self, query: str, limit: int = 50) -> List[Dict]:
        """Search regions and districts by name."""
        results: List[Dict] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Search regions
            cursor = conn.execute(
                """
                SELECT id, name, 'region' as type, capital, coordinates
                FROM regions
                WHERE name LIKE ?
                LIMIT ?
                """,
                (f"%{query}%", limit),
            )
            results.extend([self._row_to_dict(row) for row in cursor.fetchall()])

            # Search districts if space remains
            if len(results) < limit:
                remaining = limit - len(results)
                cursor = conn.execute(
                    """
                    SELECT id, name, 'district' as type, capital,
                           region_name as region, coordinates
                    FROM districts
                    WHERE name LIKE ?
                    LIMIT ?
                    """,
                    (f"%{query}%", remaining),
                )
                results.extend([self._row_to_dict(row) for row in cursor.fetchall()])

        return results
