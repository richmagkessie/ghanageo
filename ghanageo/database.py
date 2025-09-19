import sqlite3
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from .models import Region, District, Coordinates

# Database path
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "data" / "ghana.db"

class GhanaGeoDB:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(DATABASE_PATH)
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS regions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    capital TEXT NOT NULL,
                    population INTEGER,
                    area_km2 REAL,
                    coordinates TEXT,
                    created_date TEXT,
                    economic_data TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS districts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    region_id TEXT NOT NULL,
                    region_name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    capital TEXT NOT NULL,
                    population INTEGER,
                    area_km2 REAL,
                    coordinates TEXT,
                    FOREIGN KEY (region_id) REFERENCES regions (id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_regions_name ON regions(name);
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_districts_region ON districts(region_id);
            ''')
            
            conn.commit()
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_all_regions(self) -> List[Dict]:
        """Get all regions"""
        with self.get_connection() as conn:
            cursor = conn.execute('SELECT * FROM regions ORDER BY name')
            regions = []
            for row in cursor.fetchall():
                region_data = dict(row)
                if region_data['coordinates']:
                    coords = json.loads(region_data['coordinates'])
                    region_data['coordinates'] = coords
                regions.append(region_data)
            return regions
    
    def get_region_by_id(self, region_id: str) -> Optional[Dict]:
        """Get region by ID or code"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM regions WHERE id = ? OR code = ?', 
                (region_id, region_id)
            )
            row = cursor.fetchone()
            if row:
                region_data = dict(row)
                if region_data['coordinates']:
                    region_data['coordinates'] = json.loads(region_data['coordinates'])
                return region_data
            return None
    
    def get_districts_by_region(self, region_id: str) -> List[Dict]:
        """Get all districts in a region"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM districts WHERE region_id = ? ORDER BY name',
                (region_id,)
            )
            districts = []
            for row in cursor.fetchall():
                district_data = dict(row)
                if district_data['coordinates']:
                    district_data['coordinates'] = json.loads(district_data['coordinates'])
                districts.append(district_data)
            return districts
    
    def search_locations(self, query: str, limit: int = 50) -> List[Dict]:
        """Search regions and districts"""
        results = []
        query_lower = f"%{query.lower()}%"
        
        with self.get_connection() as conn:
            # Search regions
            cursor = conn.execute(
                "SELECT id, name, 'region' as type, code, coordinates FROM regions WHERE LOWER(name) LIKE ? OR LOWER(code) LIKE ?",
                (query_lower, query_lower)
            )
            for row in cursor.fetchall():
                result = dict(row)
                if result['coordinates']:
                    result['coordinates'] = json.loads(result['coordinates'])
                results.append(result)
            
            # Search districts
            cursor = conn.execute(
                "SELECT d.id, d.name, 'district' as type, d.region_name, d.coordinates FROM districts d WHERE LOWER(d.name) LIKE ?",
                (query_lower,)
            )
            for row in cursor.fetchall():
                result = dict(row)
                result['region'] = result.pop('region_name')
                if result['coordinates']:
                    result['coordinates'] = json.loads(result['coordinates'])
                results.append(result)
        
        return results[:limit]

# Global database instance
db = GhanaGeoDB()
