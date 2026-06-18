"""
GhanaGeo: Comprehensive geographic library for Ghana

Provides easy access to Ghana's administrative boundaries,
demographic data, and geospatial analysis capabilities.
"""

from .api import (
    get_regions,
    get_region,
    get_districts,
    get_towns,
    get_town,
    search,
    get_statistics,
    DataNotFoundError
)

from .models import Region, District, Town, SearchResult, Coordinates

__version__ = "2.0.0"
__all__ = [
    "get_regions",
    "get_region",
    "get_districts",
    "get_towns",
    "get_town",
    "search",
    "get_statistics",
    "DataNotFoundError",
    "Region",
    "District",
    "Town",
    "SearchResult",
    "Coordinates"
]
