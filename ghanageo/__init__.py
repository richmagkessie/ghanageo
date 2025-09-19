"""
GhanaGeo: Comprehensive geographic library for Ghana

Provides easy access to Ghana's administrative boundaries,
demographic data, and geospatial analysis capabilities.
"""

from .api import (
    get_regions,
    get_region,
    get_districts,
    search,
    get_statistics,
    DataNotFoundError
)

from .models import Region, District, SearchResult, Coordinates

__version__ = "1.0.0"
__all__ = [
    "get_regions",
    "get_region", 
    "get_districts",
    "search",
    "get_statistics",
    "DataNotFoundError",
    "Region",
    "District", 
    "SearchResult",
    "Coordinates"
]
