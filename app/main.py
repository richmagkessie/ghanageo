from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import ghanageo
from typing import Optional, List, Dict
import os

# Create FastAPI app
app = FastAPI(
    title="GhanaGeo API",
    description="Comprehensive geographic API for Ghana with regions, districts, constituencies and demographic data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "GhanaGeo Support",
        "url": "https://ghanageo.com/support",
        "email": "support@ghanageo.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/", tags=["Info"])
async def root():
    """API information and health check"""
    return {
        "message": "GhanaGeo API - Comprehensive geographic data for Ghana",
        "version": "1.0.0",
        "status": "active",
        "docs": "/docs",
        "endpoints": {
            "regions": "/regions",
            "search": "/search?q=query",
            "districts": "/districts",
            "statistics": "/statistics"
        },
        "free_tier": "1000 requests/month",
        "upgrade": "https://ghanageo.com/pricing"
    }

# Health check
@app.get("/health", tags=["Info"])
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        regions = ghanageo.get_regions()
        return {
            "status": "healthy",
            "database": "connected",
            "regions_count": len(regions)
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

# Geographic endpoints
@app.get("/regions", tags=["Geographic Data"])
async def get_regions():
    """Get all Ghana regions (Free tier)"""
    try:
        regions = ghanageo.get_regions()
        return {
            "success": True,
            "count": len(regions),
            "data": regions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/regions/{region_id}", tags=["Geographic Data"])
async def get_region(region_id: str):
    """Get specific region by ID or code (Free tier)"""
    try:
        region = ghanageo.get_region(region_id)
        return {
            "success": True,
            "data": region
        }
    except ghanageo.DataNotFoundError:
        raise HTTPException(status_code=404, detail=f"Region '{region_id}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/districts", tags=["Geographic Data"])
async def get_districts(region: Optional[str] = None):
    """Get districts, optionally filtered by region (Free tier)"""
    try:
        districts = ghanageo.get_districts(region=region)
        return {
            "success": True,
            "count": len(districts),
            "data": districts
        }
    except ghanageo.DataNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search", tags=["Search"])
async def search(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(10, le=50, description="Maximum results to return")
):
    """Search regions and districts by name (Free tier)"""
    try:
        results = ghanageo.search(q, limit=limit)
        return {
            "success": True,
            "query": q,
            "count": len(results),
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics", tags=["Data"])
async def get_statistics():
    """Get statistical overview of Ghana geographic data"""
    try:
        stats = ghanageo.get_statistics()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Not Found",
            "message": "The requested resource was not found"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error", 
            "message": "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
