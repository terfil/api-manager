from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from ..database import get_db
from ..models import ImportHistory, Service, Endpoint, DataModel
from ..schemas import ImportRequest, ImportResponse, ImportSourceType, ImportStatus
from ..utils.openapi_parser import OpenAPIParser

router = APIRouter()

@router.post("/services/import", response_model=ImportResponse)
async def import_service(
    import_request: ImportRequest,
    db: Session = Depends(get_db)
):
    """Import service from JSON/YAML/URL"""
    parser = OpenAPIParser()
    
    # Create import history record
    import_record = ImportHistory(
        source_type=import_request.source_type,
        source_location=import_request.source_location,
        status=ImportStatus.FAILED,
        imported_endpoints_count=0
    )
    
    try:
        # Parse OpenAPI specification
        if import_request.source_type == ImportSourceType.URL:
            if not import_request.source_location:
                raise ValueError("URL is required for URL import")
            spec, error = parser.parse_from_url(import_request.source_location)
        else:
            raise ValueError("Only URL import is supported in this endpoint. Use /services/import/file for file uploads.")
        
        if error != "success":
            import_record.error_message = error
            db.add(import_record)
            db.commit()
            db.refresh(import_record)
            return import_record
        
        # Extract service information
        service_info = parser.extract_service_info(spec)
        
        # Override with user-provided values if available
        if import_request.service_name:
            service_info["name"] = import_request.service_name
        if import_request.service_description:
            service_info["description"] = import_request.service_description
        
        # Check if service already exists
        existing_service = db.query(Service).filter(Service.name == service_info["name"]).first()
        if existing_service:
            # Update existing service
            for key, value in service_info.items():
                if key != "name":  # Don't update the name
                    setattr(existing_service, key, value)
            service = existing_service
        else:
            # Create new service
            service = Service(**service_info)
            db.add(service)
        
        db.commit()
        db.refresh(service)
        
        # Extract and create endpoints
        endpoints_data = parser.extract_endpoints(spec)
        created_endpoints = 0
        
        for endpoint_data in endpoints_data:
            # Check if endpoint already exists
            existing_endpoint = db.query(Endpoint).filter(
                Endpoint.service_id == service.id,
                Endpoint.path == endpoint_data["path"],
                Endpoint.method == endpoint_data["method"]
            ).first()
            
            if existing_endpoint:
                # Update existing endpoint
                for key, value in endpoint_data.items():
                    if key not in ["path", "method"]:  # Don't update path and method
                        setattr(existing_endpoint, key, value)
            else:
                # Create new endpoint
                endpoint_data["service_id"] = service.id
                endpoint = Endpoint(**endpoint_data)
                db.add(endpoint)
                created_endpoints += 1
        
        # Extract and create data models
        models_data = parser.extract_data_models(spec)
        for model_data in models_data:
            # Check if model already exists
            existing_model = db.query(DataModel).filter(
                DataModel.service_id == service.id,
                DataModel.name == model_data["name"]
            ).first()
            
            if existing_model:
                # Update existing model
                for key, value in model_data.items():
                    if key != "name":  # Don't update the name
                        setattr(existing_model, key, value)
            else:
                # Create new model
                model_data["service_id"] = service.id
                model = DataModel(**model_data)
                db.add(model)
        
        db.commit()
        
        # Update import record
        import_record.service_id = service.id
        import_record.status = ImportStatus.SUCCESS
        import_record.imported_endpoints_count = created_endpoints
        
        db.add(import_record)
        db.commit()
        db.refresh(import_record)
        
        return import_record
        
    except Exception as e:
        import_record.error_message = str(e)
        db.add(import_record)
        db.commit()
        db.refresh(import_record)
        return import_record

@router.post("/services/import/file", response_model=ImportResponse)
async def import_service_from_file(
    file: UploadFile = File(...),
    service_name: Optional[str] = Form(None),
    service_description: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Import service from uploaded file"""
    parser = OpenAPIParser()
    
    # Create import history record
    import_record = ImportHistory(
        source_type=ImportSourceType.FILE,
        source_location=file.filename,
        status=ImportStatus.FAILED,
        imported_endpoints_count=0
    )
    
    try:
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8')
        
        # Parse OpenAPI specification
        spec, error = parser.parse_from_file_content(content_str, file.filename or "")
        
        if error != "success":
            import_record.error_message = error
            db.add(import_record)
            db.commit()
            db.refresh(import_record)
            return import_record
        
        # Extract service information
        service_info = parser.extract_service_info(spec)
        
        # Override with user-provided values if available
        if service_name:
            service_info["name"] = service_name
        if service_description:
            service_info["description"] = service_description
        
        # Check if service already exists
        existing_service = db.query(Service).filter(Service.name == service_info["name"]).first()
        if existing_service:
            # Update existing service
            for key, value in service_info.items():
                if key != "name":  # Don't update the name
                    setattr(existing_service, key, value)
            service = existing_service
        else:
            # Create new service
            service = Service(**service_info)
            db.add(service)
        
        db.commit()
        db.refresh(service)
        
        # Extract and create endpoints
        endpoints_data = parser.extract_endpoints(spec)
        created_endpoints = 0
        
        for endpoint_data in endpoints_data:
            # Check if endpoint already exists
            existing_endpoint = db.query(Endpoint).filter(
                Endpoint.service_id == service.id,
                Endpoint.path == endpoint_data["path"],
                Endpoint.method == endpoint_data["method"]
            ).first()
            
            if existing_endpoint:
                # Update existing endpoint
                for key, value in endpoint_data.items():
                    if key not in ["path", "method"]:  # Don't update path and method
                        setattr(existing_endpoint, key, value)
            else:
                # Create new endpoint
                endpoint_data["service_id"] = service.id
                endpoint = Endpoint(**endpoint_data)
                db.add(endpoint)
                created_endpoints += 1
        
        # Extract and create data models
        models_data = parser.extract_data_models(spec)
        for model_data in models_data:
            # Check if model already exists
            existing_model = db.query(DataModel).filter(
                DataModel.service_id == service.id,
                DataModel.name == model_data["name"]
            ).first()
            
            if existing_model:
                # Update existing model
                for key, value in model_data.items():
                    if key != "name":  # Don't update the name
                        setattr(existing_model, key, value)
            else:
                # Create new model
                model_data["service_id"] = service.id
                model = DataModel(**model_data)
                db.add(model)
        
        db.commit()
        
        # Update import record
        import_record.service_id = service.id
        import_record.status = ImportStatus.SUCCESS
        import_record.imported_endpoints_count = created_endpoints
        
        db.add(import_record)
        db.commit()
        db.refresh(import_record)
        
        return import_record
        
    except Exception as e:
        import_record.error_message = str(e)
        db.add(import_record)
        db.commit()
        db.refresh(import_record)
        return import_record

@router.get("/import-history", response_model=List[ImportResponse])
async def get_import_history(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get import history"""
    history = db.query(ImportHistory).offset(skip).limit(limit).all()
    return history

@router.get("/import-history/{import_id}", response_model=ImportResponse)
async def get_import_details(
    import_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific import"""
    import_record = db.query(ImportHistory).filter(ImportHistory.id == import_id).first()
    if not import_record:
        raise HTTPException(status_code=404, detail="Import record not found")
    
    return import_record

