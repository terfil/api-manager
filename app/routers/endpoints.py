from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import Endpoint, Service
from ..schemas import (
    EndpointCreate, EndpointUpdate, EndpointResponse, EndpointDetail,
    EndpointListResponse, HTTPMethod
)

router = APIRouter()

@router.post("/services/{service_id}/endpoints", response_model=EndpointResponse)
async def create_endpoint(
    service_id: int,
    endpoint: EndpointCreate,
    db: Session = Depends(get_db)
):
    """Create a new endpoint for a service"""
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Check if endpoint already exists
    existing = db.query(Endpoint).filter(
        Endpoint.service_id == service_id,
        Endpoint.path == endpoint.path,
        Endpoint.method == endpoint.method
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Endpoint {endpoint.method} {endpoint.path} already exists for this service"
        )
    
    # Create endpoint
    endpoint_data = endpoint.dict(exclude={'service_id'})  # Exclude service_id from request body
    endpoint_data["service_id"] = service_id  # Set from URL parameter
    db_endpoint = Endpoint(**endpoint_data)
    
    db.add(db_endpoint)
    db.commit()
    db.refresh(db_endpoint)
    
    return db_endpoint

@router.get("/services/{service_id}/endpoints", response_model=EndpointListResponse)
async def list_service_endpoints(
    service_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    method: Optional[HTTPMethod] = Query(None),
    search: Optional[str] = Query(None),
    include_deprecated: bool = Query(True),
    db: Session = Depends(get_db)
):
    """List endpoints for a specific service"""
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    query = db.query(Endpoint).filter(Endpoint.service_id == service_id)
    
    # Apply filters
    if method:
        query = query.filter(Endpoint.method == method)
    if search:
        query = query.filter(
            (Endpoint.path.contains(search)) |
            (Endpoint.summary.contains(search)) |
            (Endpoint.description.contains(search))
        )
    if not include_deprecated:
        query = query.filter(Endpoint.is_deprecated == False)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    endpoints = query.offset(skip).limit(limit).all()
    
    return EndpointListResponse(
        endpoints=endpoints,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/endpoints", response_model=EndpointListResponse)
async def list_all_endpoints(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    method: Optional[HTTPMethod] = Query(None),
    search: Optional[str] = Query(None),
    service_id: Optional[int] = Query(None),
    include_deprecated: bool = Query(True),
    db: Session = Depends(get_db)
):
    """List all endpoints across all services"""
    query = db.query(Endpoint)
    
    # Apply filters
    if service_id:
        query = query.filter(Endpoint.service_id == service_id)
    if method:
        query = query.filter(Endpoint.method == method)
    if search:
        query = query.filter(
            (Endpoint.path.contains(search)) |
            (Endpoint.summary.contains(search)) |
            (Endpoint.description.contains(search))
        )
    if not include_deprecated:
        query = query.filter(Endpoint.is_deprecated == False)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    endpoints = query.offset(skip).limit(limit).all()
    
    return EndpointListResponse(
        endpoints=endpoints,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/endpoints/{endpoint_id}", response_model=EndpointDetail)
async def get_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific endpoint by ID"""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return endpoint

@router.put("/endpoints/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: int,
    endpoint_update: EndpointUpdate,
    db: Session = Depends(get_db)
):
    """Update an endpoint"""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Check for conflicts if path or method is being updated
    update_data = endpoint_update.dict(exclude_unset=True)
    if "path" in update_data or "method" in update_data:
        new_path = update_data.get("path", endpoint.path)
        new_method = update_data.get("method", endpoint.method)
        
        existing = db.query(Endpoint).filter(
            Endpoint.service_id == endpoint.service_id,
            Endpoint.path == new_path,
            Endpoint.method == new_method,
            Endpoint.id != endpoint_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Endpoint {new_method} {new_path} already exists for this service"
            )
    
    # Update fields
    for field, value in update_data.items():
        setattr(endpoint, field, value)
    
    db.commit()
    db.refresh(endpoint)
    
    return endpoint

@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db)
):
    """Delete an endpoint"""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    db.delete(endpoint)
    db.commit()
    
    return {"message": "Endpoint deleted successfully"}

@router.post("/endpoints/{endpoint_id}/deprecate")
async def deprecate_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db)
):
    """Mark an endpoint as deprecated"""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    endpoint.is_deprecated = True
    db.commit()
    
    return {"message": "Endpoint marked as deprecated"}

@router.post("/endpoints/{endpoint_id}/undeprecate")
async def undeprecate_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db)
):
    """Remove deprecated status from an endpoint"""
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    endpoint.is_deprecated = False
    db.commit()
    
    return {"message": "Endpoint deprecated status removed"}

