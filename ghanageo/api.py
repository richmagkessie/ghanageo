from typing import List, Dict, Optional
from .database import db
from .models import Region, District, SearchResult

class DataNotFoundError(Exception):
    """Raised when requested data is not found"""
    pass

def get_regions() -> List[Dict]:
    """Get all Ghana regions"""
    return db.get_all_regions()

def get_region(region_id: str) -> Dict:
    """Get specific region by ID or code"""
    region = db.get_region_by_id(region_id)
    if not region:
        raise DataNotFoundError(f"Region '{region_id}' not found")
    return region

def get_districts(region: Optional[str] = None) -> List[Dict]:
    """Get districts, optionally filtered by region"""
    if region:
        region_data = get_region(region)  # This will raise error if not found
        return db.get_districts_by_region(region_data['id'])
    
    # Get all districts if no region specified
    all_districts = []
    regions = get_regions()
    for region_data in regions:
        districts = db.get_districts_by_region(region_data['id'])
        all_districts.extend(districts)
    
    return all_districts

def search(query: str, limit: int = 50) -> List[Dict]:
    """Search across all geographic entities"""
    if not query.strip():
        return []
    
    return db.search_locations(query, limit)

def get_statistics() -> Dict:
    """Get basic statistics about the data"""
    regions = get_regions()
    all_districts = get_districts()
    
    total_population = sum(r.get('population', 0) for r in regions)
    total_area = sum(r.get('area_km2', 0) for r in regions)
    
    return {
        'total_regions': len(regions),
        'total_districts': len(all_districts),
        'total_population': total_population,
        'total_area_km2': round(total_area, 2),
        'average_population': round(total_population / len(regions), 0) if regions else 0,
        'most_populous_region': max(regions, key=lambda x: x.get('population', 0))['name'] if regions else None
    }
