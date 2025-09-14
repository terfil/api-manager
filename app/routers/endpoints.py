from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..database import get_db
from ..schemas import (
    EndpointCreate, EndpointUpdate, EndpointResponse, EndpointDetail,
    EndpointListResponse, HTTPMethod
)

router = APIRouter()

@router.post("/services/{service_id}/endpoints", response_model=EndpointResponse)
async def create_endpoint(
    service_id: int,
    endpoint: EndpointCreate,
    db = Depends(get_db)
):
    """Create a new endpoint for a service"""
    # Verify service exists
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Check if endpoint already exists
    service_endpoints = db.get_endpoints_by_service(service_id)
    existing = None
    for ep in service_endpoints:
        if ep["path"] == endpoint.path and ep["method"] == endpoint.method:
            existing = ep
            break
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Endpoint {endpoint.method} {endpoint.path} already exists for this service"
        )
    
    # Create endpoint
    endpoint_data = endpoint.dict(exclude={'service_id'})  # Exclude service_id from request body
    endpoint_data["service_id"] = service_id  # Set from URL parameter
    created_endpoint = db.create_endpoint(endpoint_data)
    
    return created_endpoint

@router.get("/services/{service_id}/endpoints", response_model=EndpointListResponse)
async def list_service_endpoints(
    service_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    method: Optional[HTTPMethod] = Query(None),
    search: Optional[str] = Query(None),
    include_deprecated: bool = Query(True),
    db = Depends(get_db)
):
    """List endpoints for a specific service"""
    # Verify service exists
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    endpoints = db.get_endpoints_by_service(service_id)
    
    # Apply filters
    filtered_endpoints = endpoints
    if method:
        filtered_endpoints = [ep for ep in filtered_endpoints if ep["method"] == method]
    if search:
        search_lower = search.lower()
        filtered_endpoints = [
            ep for ep in filtered_endpoints 
            if (search_lower in ep.get("path", "").lower() or
                search_lower in ep.get("summary", "").lower() or
                search_lower in ep.get("description", "").lower())
        ]
    if not include_deprecated:
        filtered_endpoints = [ep for ep in filtered_endpoints if not ep.get("is_deprecated", False)]
    
    # Get total count
    total = len(filtered_endpoints)
    
    # Apply pagination
    paginated_endpoints = filtered_endpoints[skip:skip + limit]
    
    return EndpointListResponse(
        endpoints=paginated_endpoints,
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
    db = Depends(get_db)
):
    """List all endpoints across all services"""
    all_endpoints = []
    for service in db.get_all_services():
        endpoints = db.get_endpoints_by_service(service["id"])
        all_endpoints.extend(endpoints)
    
    # Apply filters
    filtered_endpoints = all_endpoints
    if service_id:
        filtered_endpoints = [ep for ep in filtered_endpoints if ep["service_id"] == service_id]
    if method:
        filtered_endpoints = [ep for ep in filtered_endpoints if ep["method"] == method]
    if search:
        search_lower = search.lower()
        filtered_endpoints = [
            ep for ep in filtered_endpoints 
            if (search_lower in ep.get("path", "").lower() or
                search_lower in ep.get("summary", "").lower() or
                search_lower in ep.get("description", "").lower())
        ]
    if not include_deprecated:
        filtered_endpoints = [ep for ep in filtered_endpoints if not ep.get("is_deprecated", False)]
    
    # Get total count
    total = len(filtered_endpoints)
    
    # Apply pagination
    paginated_endpoints = filtered_endpoints[skip:skip + limit]
    
    return EndpointListResponse(
        endpoints=paginated_endpoints,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/endpoints/{endpoint_id}", response_model=EndpointDetail)
async def get_endpoint(
    endpoint_id: int,
    db = Depends(get_db)
):
    """Get a specific endpoint by ID"""
    endpoint = db.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return endpoint

@router.put("/endpoints/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(
    endpoint_id: int,
    endpoint_update: EndpointUpdate,
    db = Depends(get_db)
):
    """Update an endpoint"""
    endpoint = db.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Check for conflicts if path or method is being updated
    update_data = endpoint_update.dict(exclude_unset=True)
    if "path" in update_data or "method" in update_data:
        new_path = update_data.get("path", endpoint["path"])
        new_method = update_data.get("method", endpoint["method"])
        
        service_endpoints = db.get_endpoints_by_service(endpoint["service_id"])
        existing = None
        for ep in service_endpoints:
            if (ep["path"] == new_path and 
                ep["method"] == new_method and 
                ep["id"] != endpoint_id):
                existing = ep
                break
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Endpoint {new_method} {new_path} already exists for this service"
            )
    
    # Update fields
    updated_endpoint = db.update_endpoint(endpoint_id, update_data)
    
    if not updated_endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return updated_endpoint

@router.delete("/endpoints/{endpoint_id}")
async def delete_endpoint(
    endpoint_id: int,
    db = Depends(get_db)
):
    """Delete an endpoint"""
    endpoint = db.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    success = db.delete_endpoint(endpoint_id)
    if not success:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {"message": "Endpoint deleted successfully"}

@router.post("/endpoints/{endpoint_id}/deprecate")
async def deprecate_endpoint(
    endpoint_id: int,
    db = Depends(get_db)
):
    """Mark an endpoint as deprecated"""
    endpoint = db.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    update_data = {"is_deprecated": True}
    updated_endpoint = db.update_endpoint(endpoint_id, update_data)
    
    if not updated_endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {"message": "Endpoint marked as deprecated"}

@router.post("/endpoints/{endpoint_id}/undeprecate")
async def undeprecate_endpoint(
    endpoint_id: int,
    db = Depends(get_db)
):
    """Remove deprecated status from an endpoint"""
    endpoint = db.get_endpoint(endpoint_id)
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    update_data = {"is_deprecated": False}
    updated_endpoint = db.update_endpoint(endpoint_id, update_data)
    
    if not updated_endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    return {"message": "Endpoint deprecated status removed"}
