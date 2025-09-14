from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums
class HTTPMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

class ImportSourceType(str, Enum):
    FILE = "file"
    URL = "url"
    MANUAL = "manual"

class ImportStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"

class RelationshipType(str, Enum):
    COMMON_FIELDS = "common_fields"
    DATA_FLOW = "data_flow"
    SIMILAR_SCHEMA = "similar_schema"

# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

# Service schemas
class ServiceBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = None
    base_url: Optional[str] = None
    tags: Optional[List[str]] = None

class ServiceCreate(ServiceBase):
    openapi_spec: Optional[Dict[str, Any]] = None

class ServiceUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = None
    base_url: Optional[str] = None
    tags: Optional[List[str]] = None
    openapi_spec: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ServiceResponse(ServiceBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    endpoints_count: Optional[int] = 0

class ServiceDetail(ServiceResponse):
    openapi_spec: Optional[Dict[str, Any]] = None
    endpoints: Optional[List["EndpointResponse"]] = None

# Endpoint schemas
class EndpointBase(BaseSchema):
    path: str = Field(..., min_length=1, max_length=500)
    method: HTTPMethod
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

class EndpointCreate(EndpointBase):
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None

class EndpointUpdate(BaseSchema):
    path: Optional[str] = Field(None, min_length=1, max_length=500)
    method: Optional[HTTPMethod] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_deprecated: Optional[bool] = None

class EndpointResponse(EndpointBase):
    id: int
    service_id: int
    request_schema: Optional[Dict[str, Any]] = None
    response_schema: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    is_deprecated: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

class EndpointDetail(EndpointResponse):
    service: Optional[ServiceResponse] = None
    relationships: Optional[List["RelationshipResponse"]] = None

# Data Model schemas
class DataModelBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    schema: Dict[str, Any]
    description: Optional[str] = None
    model_type: Optional[str] = None

class DataModelCreate(DataModelBase):
    service_id: int
    taxonomy_id: Optional[int] = None

class DataModelUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    schema: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    model_type: Optional[str] = None
    taxonomy_id: Optional[int] = None

class DataModelResponse(DataModelBase):
    id: int
    service_id: int
    taxonomy_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

# Taxonomy schemas
class TaxonomyBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class TaxonomyCreate(TaxonomyBase):
    parent_id: Optional[int] = None

class TaxonomyUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    parent_id: Optional[int] = None

class TaxonomyResponse(TaxonomyBase):
    id: int
    parent_id: Optional[int] = None
    level: int
    path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: Optional[List["TaxonomyResponse"]] = None

# Relationship schemas
class RelationshipBase(BaseSchema):
    relationship_type: RelationshipType
    common_fields: Optional[List[str]] = None
    similarity_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    relationship_metadata: Optional[Dict[str, Any]] = None

class RelationshipCreate(RelationshipBase):
    source_endpoint_id: int
    target_endpoint_id: int

class RelationshipResponse(RelationshipBase):
    id: int
    source_endpoint_id: int
    target_endpoint_id: int
    created_at: datetime
    source_endpoint: Optional[EndpointResponse] = None
    target_endpoint: Optional[EndpointResponse] = None

# Import schemas
class ImportRequest(BaseSchema):
    source_type: ImportSourceType
    source_location: Optional[str] = None  # URL or file path
    service_name: Optional[str] = None
    service_description: Optional[str] = None

class ImportResponse(BaseSchema):
    id: int
    source_type: ImportSourceType
    source_location: Optional[str] = None
    service_id: Optional[int] = None
    status: ImportStatus
    error_message: Optional[str] = None
    imported_endpoints_count: int
    created_at: datetime

# File upload schema
class FileUpload(BaseSchema):
    filename: str
    content_type: str
    size: int

# Analysis schemas
class FieldAnalysis(BaseSchema):
    field_name: str
    field_type: str
    frequency: int
    services: List[str]
    endpoints: List[str]

class RelationshipAnalysis(BaseSchema):
    total_relationships: int
    by_type: Dict[str, int]
    most_connected_endpoints: List[Dict[str, Any]]
    common_fields_analysis: List[FieldAnalysis]

class ServiceStatistics(BaseSchema):
    total_services: int
    total_endpoints: int
    total_data_models: int
    endpoints_by_method: Dict[str, int]
    services_by_status: Dict[str, int]

# Response schemas for lists
class ServiceListResponse(BaseSchema):
    services: List[ServiceResponse]
    total: int
    page: int
    size: int

class EndpointListResponse(BaseSchema):
    endpoints: List[EndpointResponse]
    total: int
    page: int
    size: int

# Update forward references
ServiceDetail.model_rebuild()
EndpointDetail.model_rebuild()
TaxonomyResponse.model_rebuild()


# List response schemas
class RelationshipListResponse(BaseSchema):
    relationships: List[RelationshipResponse]
    total: int
    skip: int
    limit: int

