from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from ..schemas import ServiceStatistics, RelationshipAnalysis

router = APIRouter()

@router.get("/statistics", response_model=ServiceStatistics)
async def get_system_statistics(db = Depends(get_db)):
    """Get overall system statistics"""
    total_services = len([s for s in db.services.values()])
    total_endpoints = len([ep for ep in db.endpoints.values()])
    total_data_models = len([dm for dm in db.data_models.values()])
    
    # Count endpoints by method
    endpoints_by_method = {}
    for endpoint in db.endpoints.values():
        method = endpoint["method"]
        endpoints_by_method[method] = endpoints_by_method.get(method, 0) + 1
    
    # Count services by status
    active_services = len([s for s in db.services.values() if s.get("is_active", True)])
    inactive_services = total_services - active_services
    
    return ServiceStatistics(
        total_services=total_services,
        total_endpoints=total_endpoints,
        total_data_models=total_data_models,
        endpoints_by_method=endpoints_by_method,
        services_by_status={
            "active": active_services,
            "inactive": inactive_services
        }
    )

@router.get("/analysis/relationships")
async def get_relationship_analysis(db = Depends(get_db)):
    """Get relationship analysis"""
    # This will be implemented in phase 5
    return {"message": "Relationship analysis will be implemented in phase 5"}

@router.get("/analysis/common-fields")
async def analyze_common_fields(db = Depends(get_db)):
    """Analyze common fields across endpoints"""
    # This will be implemented in phase 5
    return {"message": "Common fields analysis will be implemented in phase 5"}

@router.get("/analysis/schema-similarity")
async def analyze_schema_similarity(db = Depends(get_db)):
    """Analyze schema similarity between endpoints"""
    # This will be implemented in phase 5
    return {"message": "Schema similarity analysis will be implemented in phase 5"}
