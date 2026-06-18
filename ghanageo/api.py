from typing import List, Dict, Optional
from .database import db
from .models import Region, District, Town, SearchResult

class DataNotFoundError(Exception):
    """Raised when requested data is not found"""
    pass

def get_regions() -> List[Dict]:
    return db.get_all_regions()

def get_region(region_id: str) -> Dict:
    region = db.get_region_by_id(region_id)
    if not region:
        raise DataNotFoundError(f"Region '{region_id}' not found")
    return region

def get_districts(region: Optional[str] = None) -> List[Dict]:
    if region:
        region_data = get_region(region)
        return db.get_districts_by_region(region_data['id'])

    all_districts = []
    regions = get_regions()
    for region_data in regions:
        districts = db.get_districts_by_region(region_data['id'])
        all_districts.extend(districts)
    return all_districts

def get_towns(district: Optional[str] = None, region: Optional[str] = None,
              limit: int = 500, offset: int = 0) -> List[Dict]:
    if district:
        return db.get_towns_by_district(district)
    if region:
        region_data = get_region(region)
        return db.get_towns_by_region(region_data['id'])
    return db.get_all_towns(limit=limit, offset=offset)

def get_town(town_id: str) -> Dict:
    town = db.get_town_by_id(town_id)
    if not town:
        raise DataNotFoundError(f"Town '{town_id}' not found")
    return town

def search(query: str, limit: int = 50) -> List[Dict]:
    if not query.strip():
        return []
    return db.search_locations(query, limit)

def get_statistics() -> Dict:
    regions = get_regions()
    all_districts = get_districts()
    towns_count = db.get_towns_count()

    total_population = sum(r.get('population', 0) for r in regions)
    total_area = sum(r.get('area_km2', 0) for r in regions)

    return {
        'total_regions': len(regions),
        'total_districts': len(all_districts),
        'total_towns': towns_count,
        'total_population': total_population,
        'total_area_km2': round(total_area, 2),
        'average_population': round(total_population / len(regions), 0) if regions else 0,
        'most_populous_region': max(regions, key=lambda x: x.get('population', 0))['name'] if regions else None
    }
