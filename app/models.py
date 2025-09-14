from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    version = Column(String(50))
    base_url = Column(String(500))
    openapi_spec = Column(JSON)
    tags = Column(JSON)  # For categorization
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    endpoints = relationship("Endpoint", back_populates="service", cascade="all, delete-orphan")
    data_models = relationship("DataModel", back_populates="service", cascade="all, delete-orphan")

class Endpoint(Base):
    __tablename__ = "endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)
    summary = Column(Text)
    description = Column(Text)
    request_schema = Column(JSON)
    response_schema = Column(JSON)
    parameters = Column(JSON)  # Query, path, header parameters
    tags = Column(JSON)
    is_deprecated = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    service = relationship("Service", back_populates="endpoints")
    source_relationships = relationship("Relationship", foreign_keys="Relationship.source_endpoint_id", back_populates="source_endpoint")
    target_relationships = relationship("Relationship", foreign_keys="Relationship.target_endpoint_id", back_populates="target_endpoint")

class DataModel(Base):
    __tablename__ = "data_models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    schema = Column(JSON, nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    taxonomy_id = Column(Integer, ForeignKey("taxonomies.id"))
    description = Column(Text)
    model_type = Column(String(50))  # request, response, component
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    service = relationship("Service", back_populates="data_models")
    taxonomy = relationship("Taxonomy", back_populates="data_models")

class Taxonomy(Base):
    __tablename__ = "taxonomies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("taxonomies.id"))
    description = Column(Text)
    level = Column(Integer, default=0)
    path = Column(String(1000))  # Hierarchical path like "/root/category/subcategory"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    parent = relationship("Taxonomy", remote_side=[id], back_populates="children")
    children = relationship("Taxonomy", back_populates="parent")
    data_models = relationship("DataModel", back_populates="taxonomy")

class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    source_endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    target_endpoint_id = Column(Integer, ForeignKey("endpoints.id"), nullable=False)
    relationship_type = Column(String(50), nullable=False)  # common_fields, data_flow, similar_schema
    common_fields = Column(JSON)
    similarity_score = Column(Float)
    relationship_metadata = Column(JSON)  # Additional relationship metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    source_endpoint = relationship("Endpoint", foreign_keys=[source_endpoint_id], back_populates="source_relationships")
    target_endpoint = relationship("Endpoint", foreign_keys=[target_endpoint_id], back_populates="target_relationships")

class ImportHistory(Base):
    __tablename__ = "import_history"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False)  # file, url, manual
    source_location = Column(String(1000))  # File path or URL
    service_id = Column(Integer, ForeignKey("services.id"))
    status = Column(String(50), nullable=False)  # success, failed, partial
    error_message = Column(Text)
    imported_endpoints_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    service = relationship("Service")

