from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from app.models import Relationship, Endpoint, Service
from app.schemas import RelationshipResponse
from ..utils.relationship_analyzer import RelationshipAnalyzer

router = APIRouter()

@router.post("/relationships/analyze")
async def analyze_relationships(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Analyze relationships between all endpoints"""
    analyzer = RelationshipAnalyzer(db)
    
    # Run analysis
    results = analyzer.analyze_all_relationships()
    
    return {
        "message": "Relationship analysis completed",
        "results": results
    }

@router.get("/relationships")
async def list_relationships(
    skip: int = 0,
    limit: int = 100,
    relationship_type: str = None,
    min_similarity: float = None,
    db: Session = Depends(get_db)
):
    """List all discovered relationships"""
    query = db.query(Relationship)
    
    if relationship_type:
        query = query.filter(Relationship.relationship_type == relationship_type)
    
    if min_similarity is not None:
        query = query.filter(Relationship.similarity_score >= min_similarity)
    
    query = query.order_by(Relationship.similarity_score.desc())
    
    total = query.count()
    relationships = query.offset(skip).limit(limit).all()
    
    # Enrich with endpoint information
    enriched_relationships = []
    for rel in relationships:
        source_endpoint = db.query(Endpoint).filter(Endpoint.id == rel.source_endpoint_id).first()
        target_endpoint = db.query(Endpoint).filter(Endpoint.id == rel.target_endpoint_id).first()
        
        enriched_rel = {
            "id": rel.id,
            "relationship_type": rel.relationship_type,
            "similarity_score": rel.similarity_score,
            "common_fields": rel.common_fields or [],
            "relationship_metadata": rel.relationship_metadata or {},
            "created_at": rel.created_at,
            "source_endpoint": {
                "id": source_endpoint.id,
                "method": source_endpoint.method,
                "path": source_endpoint.path,
                "service_id": source_endpoint.service_id
            } if source_endpoint else None,
            "target_endpoint": {
                "id": target_endpoint.id,
                "method": target_endpoint.method,
                "path": target_endpoint.path,
                "service_id": target_endpoint.service_id
            } if target_endpoint else None
        }
        enriched_relationships.append(enriched_rel)
    
    return {
        "relationships": enriched_relationships,
        "total": total,
        "skip": skip,
        "limit": limit
    }

@router.get("/relationships/statistics")
async def get_relationship_statistics(db: Session = Depends(get_db)):
    """Get overall relationship statistics"""
    total_relationships = db.query(Relationship).count()
    total_endpoints = db.query(Endpoint).count()
    total_services = db.query(Service).count()
    
    # Count by relationship type
    relationship_types = db.query(
        Relationship.relationship_type,
        db.func.count(Relationship.id).label('count')
    ).group_by(Relationship.relationship_type).all()
    
    # Average similarity scores
    avg_similarity = db.query(db.func.avg(Relationship.similarity_score)).scalar() or 0.0
    
    # Most connected endpoints
    most_connected_query = db.query(
        Relationship.source_endpoint_id.label('endpoint_id'),
        db.func.count(Relationship.id).label('connection_count')
    ).group_by(Relationship.source_endpoint_id).union(
        db.query(
            Relationship.target_endpoint_id.label('endpoint_id'),
            db.func.count(Relationship.id).label('connection_count')
        ).group_by(Relationship.target_endpoint_id)
    ).subquery()
    
    most_connected = db.query(
        most_connected_query.c.endpoint_id,
        db.func.sum(most_connected_query.c.connection_count).label('total_connections')
    ).group_by(most_connected_query.c.endpoint_id).order_by(
        db.func.sum(most_connected_query.c.connection_count).desc()
    ).limit(5).all()
    
    # Enrich most connected endpoints with details
    most_connected_enriched = []
    for endpoint_id, connection_count in most_connected:
        endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
        if endpoint:
            service = db.query(Service).filter(Service.id == endpoint.service_id).first()
            most_connected_enriched.append({
                "endpoint_id": endpoint_id,
                "connection_count": connection_count,
                "method": endpoint.method,
                "path": endpoint.path,
                "service_name": service.name if service else None
            })
    
    return {
        "total_relationships": total_relationships,
        "total_endpoints": total_endpoints,
        "total_services": total_services,
        "relationship_coverage": (total_relationships / max(total_endpoints * (total_endpoints - 1) / 2, 1)) * 100,
        "average_similarity_score": round(avg_similarity, 3),
        "relationship_types": [
            {"type": rel_type, "count": count}
            for rel_type, count in relationship_types
        ],
        "most_connected_endpoints": most_connected_enriched
    }

@router.get("/relationships/{relationship_id}", response_model=RelationshipResponse)
async def get_relationship(
    relationship_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific relationship"""
    relationship = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    return relationship

@router.delete("/relationships/{relationship_id}")
async def delete_relationship(
    relationship_id: int,
    db: Session = Depends(get_db)
):
    """Delete a specific relationship"""
    relationship = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    db.delete(relationship)
    db.commit()
    
    return {"message": "Relationship deleted successfully"}

@router.get("/relationships/graph/visualization")
async def get_relationship_graph(db: Session = Depends(get_db)):
    """Get graph visualization data for relationships"""
    analyzer = RelationshipAnalyzer(db)
    graph_data = analyzer.get_relationship_graph()
    
    return graph_data

@router.get("/relationships/analysis/common-fields")
async def analyze_common_fields(db: Session = Depends(get_db)):
    """Analyze common fields across all services"""
    analyzer = RelationshipAnalyzer(db)
    field_analysis = analyzer.analyze_common_fields_across_services()
    
    return field_analysis

@router.get("/relationships/services/{service_id}")
async def get_service_relationships(
    service_id: int,
    db: Session = Depends(get_db)
):
    """Get relationships for endpoints in a specific service"""
    # Verify service exists
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Get all endpoints for this service
    service_endpoints = db.query(Endpoint).filter(Endpoint.service_id == service_id).all()
    endpoint_ids = [ep.id for ep in service_endpoints]
    
    # Get relationships involving these endpoints
    relationships = db.query(Relationship).filter(
        (Relationship.source_endpoint_id.in_(endpoint_ids)) |
        (Relationship.target_endpoint_id.in_(endpoint_ids))
    ).all()
    
    # Categorize relationships
    internal_relationships = []  # Both endpoints in same service
    external_relationships = []  # One endpoint in different service
    
    for rel in relationships:
        source_endpoint = db.query(Endpoint).filter(Endpoint.id == rel.source_endpoint_id).first()
        target_endpoint = db.query(Endpoint).filter(Endpoint.id == rel.target_endpoint_id).first()
        
        rel_data = {
            "id": rel.id,
            "relationship_type": rel.relationship_type,
            "similarity_score": rel.similarity_score,
            "common_fields": rel.common_fields,
            "source_endpoint": {
                "id": source_endpoint.id,
                "method": source_endpoint.method,
                "path": source_endpoint.path,
                "service_id": source_endpoint.service_id
            },
            "target_endpoint": {
                "id": target_endpoint.id,
                "method": target_endpoint.method,
                "path": target_endpoint.path,
                "service_id": target_endpoint.service_id
            }
        }
        
        if source_endpoint.service_id == service_id and target_endpoint.service_id == service_id:
            internal_relationships.append(rel_data)
        else:
            external_relationships.append(rel_data)
    
    return {
        "service_id": service_id,
        "service_name": service.name,
        "total_relationships": len(relationships),
        "internal_relationships": internal_relationships,
        "external_relationships": external_relationships,
        "internal_count": len(internal_relationships),
        "external_count": len(external_relationships)
    }

@router.get("/relationships/endpoints/{endpoint_id}")
async def get_endpoint_relationships(
    endpoint_id: int,
    db: Session = Depends(get_db)
):
    """Get all relationships for a specific endpoint"""
    # Verify endpoint exists
    endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    
    # Get relationships where this endpoint is source or target
    relationships = db.query(Relationship).filter(
        (Relationship.source_endpoint_id == endpoint_id) |
        (Relationship.target_endpoint_id == endpoint_id)
    ).all()
    
    # Enrich with related endpoint information
    enriched_relationships = []
    for rel in relationships:
        # Determine which is the "other" endpoint
        if rel.source_endpoint_id == endpoint_id:
            other_endpoint_id = rel.target_endpoint_id
            direction = "outgoing"
        else:
            other_endpoint_id = rel.source_endpoint_id
            direction = "incoming"
        
        other_endpoint = db.query(Endpoint).filter(Endpoint.id == other_endpoint_id).first()
        other_service = db.query(Service).filter(Service.id == other_endpoint.service_id).first()
        
        enriched_rel = {
            "id": rel.id,
            "relationship_type": rel.relationship_type,
            "similarity_score": rel.similarity_score,
            "common_fields": rel.common_fields,
            "relationship_metadata": rel.relationship_metadata,
            "direction": direction,
            "related_endpoint": {
                "id": other_endpoint.id,
                "method": other_endpoint.method,
                "path": other_endpoint.path,
                "service_id": other_endpoint.service_id,
                "service_name": other_service.name if other_service else None
            }
        }
        enriched_relationships.append(enriched_rel)
    
    return {
        "endpoint_id": endpoint_id,
        "endpoint_info": {
            "method": endpoint.method,
            "path": endpoint.path,
            "service_id": endpoint.service_id
        },
        "total_relationships": len(relationships),
        "relationships": enriched_relationships
    }

@router.get("/relationships/statistics")
async def get_relationship_statistics(db: Session = Depends(get_db)):
    """Get overall relationship statistics"""
    total_relationships = db.query(Relationship).count()
    total_endpoints = db.query(Endpoint).count()
    total_services = db.query(Service).count()
    
    # Count by relationship type
    relationship_types = db.query(
        Relationship.relationship_type,
        db.func.count(Relationship.id).label('count')
    ).group_by(Relationship.relationship_type).all()
    
    # Average similarity scores
    avg_similarity = db.query(db.func.avg(Relationship.similarity_score)).scalar() or 0.0
    
    # Most connected endpoints
    most_connected_query = db.query(
        Relationship.source_endpoint_id.label('endpoint_id'),
        db.func.count(Relationship.id).label('connection_count')
    ).group_by(Relationship.source_endpoint_id).union(
        db.query(
            Relationship.target_endpoint_id.label('endpoint_id'),
            db.func.count(Relationship.id).label('connection_count')
        ).group_by(Relationship.target_endpoint_id)
    ).subquery()
    
    most_connected = db.query(
        most_connected_query.c.endpoint_id,
        db.func.sum(most_connected_query.c.connection_count).label('total_connections')
    ).group_by(most_connected_query.c.endpoint_id).order_by(
        db.func.sum(most_connected_query.c.connection_count).desc()
    ).limit(5).all()
    
    # Enrich most connected endpoints with details
    most_connected_enriched = []
    for endpoint_id, connection_count in most_connected:
        endpoint = db.query(Endpoint).filter(Endpoint.id == endpoint_id).first()
        if endpoint:
            service = db.query(Service).filter(Service.id == endpoint.service_id).first()
            most_connected_enriched.append({
                "endpoint_id": endpoint_id,
                "connection_count": connection_count,
                "method": endpoint.method,
                "path": endpoint.path,
                "service_name": service.name if service else None
            })
    
    return {
        "total_relationships": total_relationships,
        "total_endpoints": total_endpoints,
        "total_services": total_services,
        "relationship_coverage": (total_relationships / max(total_endpoints * (total_endpoints - 1) / 2, 1)) * 100,
        "average_similarity_score": round(avg_similarity, 3),
        "relationship_types": [
            {"type": rel_type, "count": count}
            for rel_type, count in relationship_types
        ],
        "most_connected_endpoints": most_connected_enriched
    }

