from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..database import get_db
from ..models import Taxonomy, DataModel, Service, Endpoint
from ..schemas import (
    TaxonomyResponse, TaxonomyCreate, TaxonomyUpdate,
    DataModelResponse, DataModelCreate, DataModelUpdate
)

router = APIRouter()

# Taxonomy Management Endpoints

@router.post("/taxonomy", response_model=TaxonomyResponse)
async def create_taxonomy(
    taxonomy: TaxonomyCreate,
    db: Session = Depends(get_db)
):
    """Create a new taxonomy category"""
    # Verify parent exists if specified
    if taxonomy.parent_id:
        parent = db.query(Taxonomy).filter(Taxonomy.id == taxonomy.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent taxonomy not found")
        level = parent.level + 1
        path = f"{parent.path}/{taxonomy.name}" if parent.path else taxonomy.name
    else:
        level = 0
        path = taxonomy.name
    
    # Check for duplicate names at the same level
    existing = db.query(Taxonomy).filter(
        Taxonomy.name == taxonomy.name,
        Taxonomy.parent_id == taxonomy.parent_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Taxonomy with this name already exists at this level"
        )
    
    db_taxonomy = Taxonomy(
        name=taxonomy.name,
        description=taxonomy.description,
        parent_id=taxonomy.parent_id,
        level=level,
        path=path
    )
    
    db.add(db_taxonomy)
    db.commit()
    db.refresh(db_taxonomy)
    
    return db_taxonomy

@router.get("/taxonomy", response_model=List[TaxonomyResponse])
async def list_taxonomies(
    parent_id: Optional[int] = Query(None),
    include_children: bool = Query(False),
    db: Session = Depends(get_db)
):
    """List taxonomies, optionally filtered by parent"""
    query = db.query(Taxonomy)
    
    if parent_id is not None:
        query = query.filter(Taxonomy.parent_id == parent_id)
    else:
        # If no parent specified, return root taxonomies
        query = query.filter(Taxonomy.parent_id.is_(None))
    
    taxonomies = query.order_by(Taxonomy.name).all()
    
    if include_children:
        # Load children for each taxonomy
        for taxonomy in taxonomies:
            taxonomy.children = db.query(Taxonomy).filter(
                Taxonomy.parent_id == taxonomy.id
            ).order_by(Taxonomy.name).all()
    
    return taxonomies

@router.get("/taxonomy/{taxonomy_id}", response_model=TaxonomyResponse)
async def get_taxonomy(
    taxonomy_id: int,
    include_children: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get a specific taxonomy"""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(status_code=404, detail="Taxonomy not found")
    
    if include_children:
        taxonomy.children = db.query(Taxonomy).filter(
            Taxonomy.parent_id == taxonomy_id
        ).order_by(Taxonomy.name).all()
    
    return taxonomy

@router.put("/taxonomy/{taxonomy_id}", response_model=TaxonomyResponse)
async def update_taxonomy(
    taxonomy_id: int,
    taxonomy_update: TaxonomyUpdate,
    db: Session = Depends(get_db)
):
    """Update a taxonomy"""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(status_code=404, detail="Taxonomy not found")
    
    # Update fields
    update_data = taxonomy_update.dict(exclude_unset=True)
    
    # Handle parent change
    if "parent_id" in update_data:
        new_parent_id = update_data["parent_id"]
        
        # Verify new parent exists and prevent circular references
        if new_parent_id:
            new_parent = db.query(Taxonomy).filter(Taxonomy.id == new_parent_id).first()
            if not new_parent:
                raise HTTPException(status_code=404, detail="New parent taxonomy not found")
            
            # Check for circular reference
            if _would_create_circular_reference(db, taxonomy_id, new_parent_id):
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot move taxonomy: would create circular reference"
                )
            
            taxonomy.level = new_parent.level + 1
            taxonomy.path = f"{new_parent.path}/{taxonomy.name}" if new_parent.path else taxonomy.name
        else:
            taxonomy.level = 0
            taxonomy.path = taxonomy.name
        
        taxonomy.parent_id = new_parent_id
    
    # Update other fields
    for field, value in update_data.items():
        if field != "parent_id":
            setattr(taxonomy, field, value)
    
    # Update path if name changed
    if "name" in update_data:
        _update_taxonomy_paths(db, taxonomy)
    
    db.commit()
    db.refresh(taxonomy)
    
    return taxonomy

@router.delete("/taxonomy/{taxonomy_id}")
async def delete_taxonomy(
    taxonomy_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Delete a taxonomy"""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(status_code=404, detail="Taxonomy not found")
    
    # Check for children
    children_count = db.query(Taxonomy).filter(Taxonomy.parent_id == taxonomy_id).count()
    if children_count > 0 and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete taxonomy with {children_count} children. Use force=true to delete recursively."
        )
    
    # Check for associated data models
    models_count = db.query(DataModel).filter(DataModel.taxonomy_id == taxonomy_id).count()
    if models_count > 0 and not force:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete taxonomy with {models_count} associated data models. Use force=true to delete."
        )
    
    if force:
        # Delete children recursively
        _delete_taxonomy_recursive(db, taxonomy_id)
    else:
        db.delete(taxonomy)
    
    db.commit()
    
    return {"message": "Taxonomy deleted successfully"}

@router.get("/taxonomy/{taxonomy_id}/tree")
async def get_taxonomy_tree(
    taxonomy_id: int,
    db: Session = Depends(get_db)
):
    """Get the full taxonomy tree starting from a specific taxonomy"""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(status_code=404, detail="Taxonomy not found")
    
    tree = _build_taxonomy_tree(db, taxonomy_id)
    return tree

@router.get("/taxonomy/tree/full")
async def get_full_taxonomy_tree(db: Session = Depends(get_db)):
    """Get the complete taxonomy tree"""
    root_taxonomies = db.query(Taxonomy).filter(Taxonomy.parent_id.is_(None)).order_by(Taxonomy.name).all()
    
    tree = []
    for root in root_taxonomies:
        tree.append(_build_taxonomy_tree(db, root.id))
    
    return {"tree": tree}

# Data Model Management Endpoints

@router.post("/data-models", response_model=DataModelResponse)
async def create_data_model(
    data_model: DataModelCreate,
    db: Session = Depends(get_db)
):
    """Create a new data model"""
    # Verify service exists
    service = db.query(Service).filter(Service.id == data_model.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Verify taxonomy exists if specified
    if data_model.taxonomy_id:
        taxonomy = db.query(Taxonomy).filter(Taxonomy.id == data_model.taxonomy_id).first()
        if not taxonomy:
            raise HTTPException(status_code=404, detail="Taxonomy not found")
    
    # Check for duplicate names within the same service
    existing = db.query(DataModel).filter(
        DataModel.name == data_model.name,
        DataModel.service_id == data_model.service_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="Data model with this name already exists in this service"
        )
    
    db_model = DataModel(**data_model.dict())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    
    return db_model

@router.get("/data-models", response_model=List[DataModelResponse])
async def list_data_models(
    service_id: Optional[int] = Query(None),
    taxonomy_id: Optional[int] = Query(None),
    model_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List data models with filtering"""
    query = db.query(DataModel)
    
    if service_id:
        query = query.filter(DataModel.service_id == service_id)
    
    if taxonomy_id:
        query = query.filter(DataModel.taxonomy_id == taxonomy_id)
    
    if model_type:
        query = query.filter(DataModel.model_type == model_type)
    
    models = query.offset(skip).limit(limit).all()
    return models

@router.get("/data-models/{model_id}", response_model=DataModelResponse)
async def get_data_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific data model"""
    model = db.query(DataModel).filter(DataModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Data model not found")
    
    return model

@router.put("/data-models/{model_id}", response_model=DataModelResponse)
async def update_data_model(
    model_id: int,
    model_update: DataModelUpdate,
    db: Session = Depends(get_db)
):
    """Update a data model"""
    model = db.query(DataModel).filter(DataModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Data model not found")
    
    # Verify taxonomy exists if being updated
    update_data = model_update.dict(exclude_unset=True)
    if "taxonomy_id" in update_data and update_data["taxonomy_id"]:
        taxonomy = db.query(Taxonomy).filter(Taxonomy.id == update_data["taxonomy_id"]).first()
        if not taxonomy:
            raise HTTPException(status_code=404, detail="Taxonomy not found")
    
    # Update fields
    for field, value in update_data.items():
        setattr(model, field, value)
    
    db.commit()
    db.refresh(model)
    
    return model

@router.delete("/data-models/{model_id}")
async def delete_data_model(
    model_id: int,
    db: Session = Depends(get_db)
):
    """Delete a data model"""
    model = db.query(DataModel).filter(DataModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Data model not found")
    
    db.delete(model)
    db.commit()
    
    return {"message": "Data model deleted successfully"}

# Analysis and Utility Endpoints

@router.post("/data-models/extract-from-service/{service_id}")
async def extract_data_models_from_service(
    service_id: int,
    auto_categorize: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Extract data models from service endpoints and optionally auto-categorize them"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    endpoints = db.query(Endpoint).filter(Endpoint.service_id == service_id).all()
    
    extracted_models = []
    model_schemas = {}
    
    for endpoint in endpoints:
        # Extract request schema
        if endpoint.request_schema:
            model_name = f"{endpoint.method}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_Request"
            model_name = model_name.replace('__', '_').strip('_')
            
            if model_name not in model_schemas:
                model_schemas[model_name] = {
                    "schema": endpoint.request_schema,
                    "type": "request",
                    "endpoints": [f"{endpoint.method} {endpoint.path}"]
                }
            else:
                model_schemas[model_name]["endpoints"].append(f"{endpoint.method} {endpoint.path}")
        
        # Extract response schema
        if endpoint.response_schema:
            model_name = f"{endpoint.method}_{endpoint.path.replace('/', '_').replace('{', '').replace('}', '')}_Response"
            model_name = model_name.replace('__', '_').strip('_')
            
            if model_name not in model_schemas:
                model_schemas[model_name] = {
                    "schema": endpoint.response_schema,
                    "type": "response",
                    "endpoints": [f"{endpoint.method} {endpoint.path}"]
                }
            else:
                model_schemas[model_name]["endpoints"].append(f"{endpoint.method} {endpoint.path}")
    
    # Create data models
    for model_name, model_data in model_schemas.items():
        # Check if model already exists
        existing = db.query(DataModel).filter(
            DataModel.name == model_name,
            DataModel.service_id == service_id
        ).first()
        
        if not existing:
            taxonomy_id = None
            if auto_categorize:
                taxonomy_id = _auto_categorize_model(db, model_name, model_data["schema"], model_data["type"])
            
            db_model = DataModel(
                name=model_name,
                schema=model_data["schema"],
                description=f"Auto-extracted {model_data['type']} model from endpoints: {', '.join(model_data['endpoints'])}",
                model_type=model_data["type"],
                service_id=service_id,
                taxonomy_id=taxonomy_id
            )
            
            db.add(db_model)
            extracted_models.append(model_name)
    
    db.commit()
    
    return {
        "message": f"Extracted {len(extracted_models)} data models from service",
        "service_name": service.name,
        "extracted_models": extracted_models,
        "total_schemas_found": len(model_schemas)
    }

@router.get("/taxonomy/{taxonomy_id}/models", response_model=List[DataModelResponse])
async def get_taxonomy_models(
    taxonomy_id: int,
    include_children: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get all data models in a taxonomy category"""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.id == taxonomy_id).first()
    if not taxonomy:
        raise HTTPException(status_code=404, detail="Taxonomy not found")
    
    if include_children:
        # Get all descendant taxonomy IDs
        descendant_ids = _get_descendant_taxonomy_ids(db, taxonomy_id)
        descendant_ids.append(taxonomy_id)
        
        models = db.query(DataModel).filter(
            DataModel.taxonomy_id.in_(descendant_ids)
        ).all()
    else:
        models = db.query(DataModel).filter(DataModel.taxonomy_id == taxonomy_id).all()
    
    return models

@router.get("/data-models/analysis/schema-similarity")
async def analyze_schema_similarity(
    service_id: Optional[int] = Query(None),
    taxonomy_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Analyze schema similarity between data models"""
    query = db.query(DataModel)
    
    if service_id:
        query = query.filter(DataModel.service_id == service_id)
    
    if taxonomy_id:
        query = query.filter(DataModel.taxonomy_id == taxonomy_id)
    
    models = query.all()
    
    if len(models) < 2:
        return {"message": "Need at least 2 data models for similarity analysis", "similarities": []}
    
    similarities = []
    
    for i, model1 in enumerate(models):
        for j, model2 in enumerate(models[i+1:], i+1):
            similarity_score = _calculate_schema_similarity(model1.schema, model2.schema)
            
            if similarity_score > 0.1:  # Only include meaningful similarities
                similarities.append({
                    "model1": {
                        "id": model1.id,
                        "name": model1.name,
                        "service_id": model1.service_id
                    },
                    "model2": {
                        "id": model2.id,
                        "name": model2.name,
                        "service_id": model2.service_id
                    },
                    "similarity_score": round(similarity_score, 3),
                    "common_fields": _get_common_schema_fields(model1.schema, model2.schema)
                })
    
    # Sort by similarity score descending
    similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return {
        "total_models_analyzed": len(models),
        "similarities_found": len(similarities),
        "similarities": similarities[:20]  # Top 20 most similar
    }

# Helper Functions

def _would_create_circular_reference(db: Session, taxonomy_id: int, new_parent_id: int) -> bool:
    """Check if moving taxonomy would create a circular reference"""
    current_id = new_parent_id
    
    while current_id:
        if current_id == taxonomy_id:
            return True
        
        parent = db.query(Taxonomy).filter(Taxonomy.id == current_id).first()
        current_id = parent.parent_id if parent else None
    
    return False

def _update_taxonomy_paths(db: Session, taxonomy: Taxonomy):
    """Update paths for taxonomy and all its descendants"""
    if taxonomy.parent_id:
        parent = db.query(Taxonomy).filter(Taxonomy.id == taxonomy.parent_id).first()
        taxonomy.path = f"{parent.path}/{taxonomy.name}" if parent and parent.path else taxonomy.name
    else:
        taxonomy.path = taxonomy.name
    
    # Update children paths
    children = db.query(Taxonomy).filter(Taxonomy.parent_id == taxonomy.id).all()
    for child in children:
        _update_taxonomy_paths(db, child)

def _delete_taxonomy_recursive(db: Session, taxonomy_id: int):
    """Delete taxonomy and all its descendants"""
    # Delete all data models associated with this taxonomy
    db.query(DataModel).filter(DataModel.taxonomy_id == taxonomy_id).delete()
    
    # Get children
    children = db.query(Taxonomy).filter(Taxonomy.parent_id == taxonomy_id).all()
    
    # Delete children recursively
    for child in children:
        _delete_taxonomy_recursive(db, child.id)
    
    # Delete the taxonomy itself
    db.query(Taxonomy).filter(Taxonomy.id == taxonomy_id).delete()

def _build_taxonomy_tree(db: Session, taxonomy_id: int) -> Dict[str, Any]:
    """Build a tree structure for a taxonomy and its descendants"""
    taxonomy = db.query(Taxonomy).filter(Taxonomy.id == taxonomy_id).first()
    if not taxonomy:
        return None
    
    children = db.query(Taxonomy).filter(Taxonomy.parent_id == taxonomy_id).order_by(Taxonomy.name).all()
    
    tree = {
        "id": taxonomy.id,
        "name": taxonomy.name,
        "description": taxonomy.description,
        "level": taxonomy.level,
        "path": taxonomy.path,
        "children": []
    }
    
    for child in children:
        child_tree = _build_taxonomy_tree(db, child.id)
        if child_tree:
            tree["children"].append(child_tree)
    
    return tree

def _auto_categorize_model(db: Session, model_name: str, schema: Dict[str, Any], model_type: str) -> Optional[int]:
    """Auto-categorize a data model based on its name and schema"""
    # Create basic taxonomies if they don't exist
    request_taxonomy = _get_or_create_taxonomy(db, "Request Models", "Request data models")
    response_taxonomy = _get_or_create_taxonomy(db, "Response Models", "Response data models")
    
    if model_type == "request":
        return request_taxonomy.id
    elif model_type == "response":
        return response_taxonomy.id
    
    return None

def _get_or_create_taxonomy(db: Session, name: str, description: str, parent_id: Optional[int] = None) -> Taxonomy:
    """Get existing taxonomy or create new one"""
    existing = db.query(Taxonomy).filter(
        Taxonomy.name == name,
        Taxonomy.parent_id == parent_id
    ).first()
    
    if existing:
        return existing
    
    level = 0
    path = name
    if parent_id:
        parent = db.query(Taxonomy).filter(Taxonomy.id == parent_id).first()
        if parent:
            level = parent.level + 1
            path = f"{parent.path}/{name}" if parent.path else name
    
    taxonomy = Taxonomy(
        name=name,
        description=description,
        parent_id=parent_id,
        level=level,
        path=path
    )
    
    db.add(taxonomy)
    db.commit()
    db.refresh(taxonomy)
    
    return taxonomy

def _get_descendant_taxonomy_ids(db: Session, taxonomy_id: int) -> List[int]:
    """Get all descendant taxonomy IDs"""
    descendants = []
    children = db.query(Taxonomy).filter(Taxonomy.parent_id == taxonomy_id).all()
    
    for child in children:
        descendants.append(child.id)
        descendants.extend(_get_descendant_taxonomy_ids(db, child.id))
    
    return descendants

def _calculate_schema_similarity(schema1: Dict[str, Any], schema2: Dict[str, Any]) -> float:
    """Calculate similarity between two schemas"""
    fields1 = _extract_schema_fields(schema1)
    fields2 = _extract_schema_fields(schema2)
    
    if not fields1 and not fields2:
        return 1.0
    
    if not fields1 or not fields2:
        return 0.0
    
    intersection = fields1.intersection(fields2)
    union = fields1.union(fields2)
    
    return len(intersection) / len(union) if union else 0.0

def _extract_schema_fields(schema: Dict[str, Any], prefix: str = "") -> set:
    """Extract field names from a schema"""
    fields = set()
    
    if not isinstance(schema, dict):
        return fields
    
    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            field_name = f"{prefix}.{prop_name}" if prefix else prop_name
            fields.add(field_name)
            
            if isinstance(prop_schema, dict):
                fields.update(_extract_schema_fields(prop_schema, field_name))
    
    if "items" in schema and isinstance(schema["items"], dict):
        fields.update(_extract_schema_fields(schema["items"], f"{prefix}[]"))
    
    return fields

def _get_common_schema_fields(schema1: Dict[str, Any], schema2: Dict[str, Any]) -> List[str]:
    """Get common fields between two schemas"""
    fields1 = _extract_schema_fields(schema1)
    fields2 = _extract_schema_fields(schema2)
    
    return list(fields1.intersection(fields2))

