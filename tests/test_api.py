import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"]
    assert data["version"] == "1.0.0"

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_get_regions():
    """Test getting all regions"""
    response = client.get("/regions")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "data" in data
    assert len(data["data"]) > 0

def test_get_specific_region():
    """Test getting specific region"""
    response = client.get("/regions/GR")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["data"]["name"] == "Greater Accra Region"

def test_search():
    """Test search functionality"""
    response = client.get("/search?q=Accra")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert len(data["data"]) > 0

def test_get_districts():
    """Test getting districts"""
    response = client.get("/districts")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "data" in data

def test_statistics():
    """Test statistics endpoint"""
    response = client.get("/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "total_regions" in data["data"]
