from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from ..database import get_db
from ..schemas import ImportRequest, ImportResponse, ImportSourceType, ImportStatus
from ..utils.openapi_parser import OpenAPIParser

router = APIRouter()

@router.post("/services/import", response_model=ImportResponse)
async def import_service(
    import_request: ImportRequest,
    db = Depends(get_db)
):
    """Import service from JSON/YAML/URL"""
    parser = OpenAPIParser()
    
    # Create import history record
    import_record_data = {
        "source_type": import_request.source_type,
        "source_location": import_request.source_location,
        "status": ImportStatus.FAILED,
        "error_message": None,
        "imported_endpoints_count": 0
    }
    
    try:
        # Parse OpenAPI specification
        if import_request.source_type == ImportSourceType.URL:
            if not import_request.source_location:
                raise ValueError("URL is required for URL import")
            spec, error = parser.parse_from_url(import_request.source_location)
        else:
            raise ValueError("Only URL import is supported in this endpoint. Use /services/import/file for file uploads.")
        
        if error != "success":
            import_record_data["error_message"] = error
            import_record = db.create_import_history(import_record_data)
            return import_record
        
        # Extract service information
        service_info = parser.extract_service_info(spec)
        
        # Override with user-provided values if available
        if import_request.service_name:
            service_info["name"] = import_request.service_name
        if import_request.service_description:
            service_info["description"] = import_request.service_description
        
        # Check if service already exists
        existing_service = None
        all_services = db.get_all_services()
        for service in all_services:
            if service["name"] == service_info["name"]:
                existing_service = service
                break
        
        if existing_service:
            # Update existing service
            for key, value in service_info.items():
                if key != "name":  # Don't update the name
                    existing_service[key] = value
            service = existing_service
            db.update_service(existing_service["id"], service_info)
        else:
            # Create new service
            service = db.create_service(service_info)
        
        # Extract and create endpoints
        endpoints_data = parser.extract_endpoints(spec)
        created_endpoints = 0
        
        for endpoint_data in endpoints_data:
            # Check if endpoint already exists
            existing_endpoint = None
            service_endpoints = db.get_endpoints_by_service(service["id"])
            for endpoint in service_endpoints:
                if (endpoint["path"] == endpoint_data["path"] and 
                    endpoint["method"] == endpoint_data["method"]):
                    existing_endpoint = endpoint
                    break
            
            if existing_endpoint:
                # Update existing endpoint
                for key, value in endpoint_data.items():
                    if key not in ["path", "method"]:  # Don't update path and method
                        existing_endpoint[key] = value
                db.update_endpoint(existing_endpoint["id"], endpoint_data)
            else:
                # Create new endpoint
                endpoint_data["service_id"] = service["id"]
                db.create_endpoint(endpoint_data)
                created_endpoints += 1
        
        # Extract and create data models
        models_data = parser.extract_data_models(spec)
        for model_data in models_data:
            # Create new model (no update logic for simplicity)
            model_data["service_id"] = service["id"]
            db.create_data_model(model_data)
        
        # Update import record
        import_record_data["service_id"] = service["id"]
        import_record_data["status"] = ImportStatus.SUCCESS
        import_record_data["imported_endpoints_count"] = created_endpoints
        import_record_data["error_message"] = None
        
        import_record = db.create_import_history(import_record_data)
        
        return import_record
        
    except Exception as e:
        import_record_data["error_message"] = str(e)
        import_record = db.create_import_history(import_record_data)
        return import_record

@router.post("/services/import/file", response_model=ImportResponse)
async def import_service_from_file(
    file: UploadFile = File(...),
    service_name: Optional[str] = Form(None),
    service_description: Optional[str] = Form(None),
    db = Depends(get_db)
):
    """Import service from uploaded file"""
    parser = OpenAPIParser()
    
    # Create import history record
    import_record_data = {
        "source_type": ImportSourceType.FILE,
        "source_location": file.filename,
        "status": ImportStatus.FAILED,
        "error_message": None,
        "imported_endpoints_count": 0
    }
    
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Parse OpenAPI specification
        spec, error = parser.parse_from_file_content(content_str, file.filename or "")
        
        if error != "success":
            import_record_data["error_message"] = error
            import_record = db.create_import_history(import_record_data)
            return import_record
        
        # Extract service information
        service_info = parser.extract_service_info(spec)
        
        # Override with user-provided values if available
        if service_name:
            service_info["name"] = service_name
        if service_description:
            service_info["description"] = service_description
        
        # Check if service already exists
        existing_service = None
        all_services = db.get_all_services()
        for service in all_services:
            if service["name"] == service_info["name"]:
                existing_service = service
                break
        
        if existing_service:
            # Update existing service
            for key, value in service_info.items():
                if key != "name":  # Don't update the name
                    existing_service[key] = value
            service = existing_service
            db.update_service(existing_service["id"], service_info)
        else:
            # Create new service
            service = db.create_service(service_info)
        
        # Extract and create endpoints
        endpoints_data = parser.extract_endpoints(spec)
        created_endpoints = 0
        
        for endpoint_data in endpoints_data:
            # Check if endpoint already exists
            existing_endpoint = None
            service_endpoints = db.get_endpoints_by_service(service["id"])
            for endpoint in service_endpoints:
                if (endpoint["path"] == endpoint_data["path"] and 
                    endpoint["method"] == endpoint_data["method"]):
                    existing_endpoint = endpoint
                    break
            
            if existing_endpoint:
                # Update existing endpoint
                for key, value in endpoint_data.items():
                    if key not in ["path", "method"]:  # Don't update path and method
                        existing_endpoint[key] = value
                db.update_endpoint(existing_endpoint["id"], endpoint_data)
            else:
                # Create new endpoint
                endpoint_data["service_id"] = service["id"]
                db.create_endpoint(endpoint_data)
                created_endpoints += 1
        
        # Extract and create data models
        models_data = parser.extract_data_models(spec)
        for model_data in models_data:
            # Create new model (no update logic for simplicity)
            model_data["service_id"] = service["id"]
            db.create_data_model(model_data)
        
        # Update import record
        import_record_data["service_id"] = service["id"]
        import_record_data["status"] = ImportStatus.SUCCESS
        import_record_data["imported_endpoints_count"] = created_endpoints
        import_record_data["error_message"] = None
        
        import_record = db.create_import_history(import_record_data)
        
        return import_record
        
    except Exception as e:
        import_record_data["error_message"] = str(e)
        import_record = db.create_import_history(import_record_data)
        return import_record

@router.get("/import-history", response_model=List[ImportResponse])
async def get_import_history(
    skip: int = 0,
    limit: int = 100,
    db = Depends(get_db)
):
    """Get import history"""
    history = db.get_import_history(skip, limit)
    return history

@router.get("/import-history/{import_id}", response_model=ImportResponse)
async def get_import_details(
    import_id: int,
    db = Depends(get_db)
):
    """Get details of a specific import"""
    import_record = db.get_import_details(import_id)
    if not import_record:
        raise HTTPException(status_code=404, detail="Import record not found")
    
    return import_record
