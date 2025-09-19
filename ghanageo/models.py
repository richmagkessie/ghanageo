from pydantic import BaseModel
from typing import Optional, Dict, List, Any

class Coordinates(BaseModel):
    lat: float
    lng: float

class Region(BaseModel):
    id: str
    name: str
    code: str
    capital: str
    population: int
    area_km2: float
    coordinates: Optional[Coordinates] = None
    created_date: Optional[str] = None
    
    class Config:
        json_encoders = {
            # Add custom encoders if needed
        }

class District(BaseModel):
    id: str
    name: str
    region_id: str
    region_name: str
    type: str  # 'Metro', 'Municipal', 'District'
    capital: str
    population: int
    area_km2: float
    coordinates: Optional[Coordinates] = None

class SearchResult(BaseModel):
    id: str
    name: str
    type: str  # 'region', 'district', 'constituency'
    region: Optional[str] = None
    district: Optional[str] = None
    coordinates: Optional[Coordinates] = None

class APIResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None
    count: Optional[int] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
