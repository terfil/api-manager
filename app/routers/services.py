from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..database import get_db
from ..schemas import (
    ServiceCreate, ServiceUpdate, ServiceResponse, ServiceDetail, 
    ServiceListResponse
)

router = APIRouter()

@router.post("/services", response_model=ServiceResponse)
async def create_service(
    service: ServiceCreate,
    db = Depends(get_db)
):
    """Create a new service"""
    service_data = service.dict()
    created_service = db.create_service(service_data)
    return created_service

@router.get("/services", response_model=ServiceListResponse)
async def list_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db = Depends(get_db)
):
    """List all services with pagination and filtering"""
    all_services = db.get_all_services()
    
    # Apply filters
    filtered_services = all_services
    if search:
        filtered_services = [s for s in filtered_services if search.lower() in s["name"].lower()]
    if is_active is not None:
        filtered_services = [s for s in filtered_services if s["is_active"] == is_active]
    
    # Get total count
    total = len(filtered_services)
    
    # Apply pagination
    services = filtered_services[skip:skip + limit]
    
    return ServiceListResponse(
        services=services,
        total=total,
        page=skip // limit + 1,
        size=limit
    )

@router.get("/services/{service_id}", response_model=ServiceDetail)
async def get_service(
    service_id: int,
    db = Depends(get_db)
):
    """Get a specific service by ID"""
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return service

@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_update: ServiceUpdate,
    db = Depends(get_db)
):
    """Update a service"""
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Update fields
    update_data = service_update.dict(exclude_unset=True)
    updated_service = db.update_service(service_id, update_data)
    
    if not updated_service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return updated_service

@router.delete("/services/{service_id}")
async def delete_service(
    service_id: int,
    db = Depends(get_db)
):
    """Delete a service"""
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    success = db.delete_service(service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return {"message": "Service deleted successfully"}

@router.get("/services/{service_id}/openapi.json")
async def get_service_openapi(
    service_id: int,
    db = Depends(get_db)
):
    """Get OpenAPI specification for a specific service"""
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # If service has stored OpenAPI spec, return it
    if service.get("openapi_spec"):
        return service["openapi_spec"]
    
    # Otherwise, generate OpenAPI spec from endpoints
    endpoints = db.get_endpoints_by_service(service_id)
    
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": service["name"],
            "description": service.get("description", ""),
            "version": service.get("version", "1.0.0")
        },
        "servers": [],
        "paths": {},
        "components": {
            "schemas": {}
        }
    }
    
    if service.get("base_url"):
        openapi_spec["servers"].append({
            "url": service["base_url"],
            "description": "API Server"
        })
    
    # Group endpoints by path
    paths = {}
    for endpoint in endpoints:
        if endpoint["path"] not in paths:
            paths[endpoint["path"]] = {}
        
        operation = {
            "summary": endpoint.get("summary", ""),
            "description": endpoint.get("description", ""),
            "tags": endpoint.get("tags", []),
            "responses": {}
        }
        
        # Add parameters
        if endpoint.get("parameters"):
            parameters = []
            for param_type, param_list in endpoint["parameters"].items():
                for param in param_list:
                    parameters.append({
                        "name": param.get("name"),
                        "in": param_type,
                        "required": param.get("required", False),
                        "description": param.get("description", ""),
                        "schema": param.get("schema", {"type": "string"})
                    })
            if parameters:
                operation["parameters"] = parameters
        
        # Add request body
        if endpoint.get("request_schema") and endpoint["method"].upper() in ["POST", "PUT", "PATCH"]:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": endpoint["request_schema"]
                    }
                }
            }
        
        # Add responses
        if endpoint.get("response_schema"):
            operation["responses"]["200"] = {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": endpoint["response_schema"]
                    }
                }
            }
        else:
            operation["responses"]["200"] = {
                "description": "Successful response"
            }
        
        paths[endpoint["path"]][endpoint["method"].lower()] = operation
    
    openapi_spec["paths"] = paths
    
    return openapi_spec

@router.get("/services/{service_id}/statistics")
async def get_service_statistics(
    service_id: int,
    db = Depends(get_db)
):
    """Get statistics for a specific service"""
    service = db.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    endpoints = db.get_endpoints_by_service(service_id)
    
    # Calculate statistics
    total_endpoints = len(endpoints)
    methods_count = {}
    deprecated_count = 0
    
    for endpoint in endpoints:
        method = endpoint["method"]
        methods_count[method] = methods_count.get(method, 0) + 1
        if endpoint.get("is_deprecated", False):
            deprecated_count += 1
    
    return {
        "service_id": service_id,
        "service_name": service["name"],
        "total_endpoints": total_endpoints,
        "endpoints_by_method": methods_count,
        "deprecated_endpoints": deprecated_count,
        "active_endpoints": total_endpoints - deprecated_count
    }
