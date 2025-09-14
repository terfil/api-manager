from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Service, Endpoint, Relationship, DataModel
from ..schemas import ServiceStatistics, RelationshipAnalysis

router = APIRouter()

@router.get("/statistics", response_model=ServiceStatistics)
async def get_system_statistics(db: Session = Depends(get_db)):
    """Get overall system statistics"""
    total_services = db.query(Service).count()
    total_endpoints = db.query(Endpoint).count()
    total_data_models = db.query(DataModel).count()
    
    # Count endpoints by method
    endpoints = db.query(Endpoint).all()
    endpoints_by_method = {}
    for endpoint in endpoints:
        method = endpoint.method
        endpoints_by_method[method] = endpoints_by_method.get(method, 0) + 1
    
    # Count services by status
    active_services = db.query(Service).filter(Service.is_active == True).count()
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
async def get_relationship_analysis(db: Session = Depends(get_db)):
    """Get relationship analysis"""
    # This will be implemented in phase 5
    return {"message": "Relationship analysis will be implemented in phase 5"}

@router.get("/analysis/common-fields")
async def analyze_common_fields(db: Session = Depends(get_db)):
    """Analyze common fields across endpoints"""
    # This will be implemented in phase 5
    return {"message": "Common fields analysis will be implemented in phase 5"}

@router.get("/analysis/schema-similarity")
async def analyze_schema_similarity(db: Session = Depends(get_db)):
    """Analyze schema similarity between endpoints"""
    # This will be implemented in phase 5
    return {"message": "Schema similarity analysis will be implemented in phase 5"}

