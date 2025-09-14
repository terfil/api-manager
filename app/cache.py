"""
In-memory cache implementation for API Management Service
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class InMemoryCache:
    """Simple in-memory cache using Python dictionaries"""
    
    def __init__(self):
        self.services: Dict[int, Dict] = {}
        self.endpoints: Dict[int, Dict] = {}
        self.data_models: Dict[int, Dict] = {}
        self.taxonomies: Dict[int, Dict] = {}
        self.relationships: Dict[int, Dict] = {}
        self.import_history: Dict[int, Dict] = {}
        
        # Counters for ID generation
        self.service_counter = 1
        self.endpoint_counter = 1
        self.data_model_counter = 1
        self.taxonomy_counter = 1
        self.relationship_counter = 1
        self.import_history_counter = 1
    
    # Service operations
    def get_service(self, service_id: int) -> Optional[Dict]:
        return self.services.get(service_id)
    
    def get_all_services(self) -> List[Dict]:
        return list(self.services.values())
    
    def create_service(self, service_data: Dict) -> Dict:
        service_id = self.service_counter
        self.service_counter += 1
        
        service = {
            "id": service_id,
            "name": service_data["name"],
            "description": service_data.get("description"),
            "version": service_data.get("version"),
            "base_url": service_data.get("base_url"),
            "openapi_spec": service_data.get("openapi_spec"),
            "tags": service_data.get("tags", []),
            "is_active": service_data.get("is_active", True),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "endpoints_count": 0
        }
        
        self.services[service_id] = service
        return service
    
    def update_service(self, service_id: int, service_data: Dict) -> Optional[Dict]:
        if service_id not in self.services:
            return None
        
        service = self.services[service_id]
        for key, value in service_data.items():
            if key != "id":  # Don't update the ID
                service[key] = value
        
        service["updated_at"] = datetime.now()
        return service
    
    def delete_service(self, service_id: int) -> bool:
        if service_id in self.services:
            # Also delete associated endpoints
            endpoints_to_delete = [
                endpoint_id for endpoint_id, endpoint in self.endpoints.items()
                if endpoint["service_id"] == service_id
            ]
            for endpoint_id in endpoints_to_delete:
                del self.endpoints[endpoint_id]
            
            del self.services[service_id]
            return True
        return False
    
    # Endpoint operations
    def get_endpoint(self, endpoint_id: int) -> Optional[Dict]:
        return self.endpoints.get(endpoint_id)
    
    def get_endpoints_by_service(self, service_id: int) -> List[Dict]:
        return [
            endpoint for endpoint in self.endpoints.values()
            if endpoint["service_id"] == service_id
        ]
    
    def create_endpoint(self, endpoint_data: Dict) -> Dict:
        endpoint_id = self.endpoint_counter
        self.endpoint_counter += 1
        
        endpoint = {
            "id": endpoint_id,
            "service_id": endpoint_data["service_id"],
            "path": endpoint_data["path"],
            "method": endpoint_data["method"],
            "summary": endpoint_data.get("summary"),
            "description": endpoint_data.get("description"),
            "request_schema": endpoint_data.get("request_schema"),
            "response_schema": endpoint_data.get("response_schema"),
            "parameters": endpoint_data.get("parameters", {}),
            "tags": endpoint_data.get("tags", []),
            "is_deprecated": endpoint_data.get("is_deprecated", False),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        self.endpoints[endpoint_id] = endpoint
        
        # Update service endpoints count
        service = self.services.get(endpoint_data["service_id"])
        if service:
            service["endpoints_count"] = len(self.get_endpoints_by_service(endpoint_data["service_id"]))
        
        return endpoint
    
    def update_endpoint(self, endpoint_id: int, endpoint_data: Dict) -> Optional[Dict]:
        if endpoint_id not in self.endpoints:
            return None
        
        endpoint = self.endpoints[endpoint_id]
        for key, value in endpoint_data.items():
            if key not in ["id", "service_id"]:  # Don't update ID or service_id
                endpoint[key] = value
        
        endpoint["updated_at"] = datetime.now()
        return endpoint
    
    def delete_endpoint(self, endpoint_id: int) -> bool:
        if endpoint_id in self.endpoints:
            endpoint = self.endpoints[endpoint_id]
            service_id = endpoint["service_id"]
            del self.endpoints[endpoint_id]
            
            # Update service endpoints count
            service = self.services.get(service_id)
            if service:
                service["endpoints_count"] = len(self.get_endpoints_by_service(service_id))
            
            return True
        return False
    
    # Import history operations
    def create_import_history(self, import_data: Dict) -> Dict:
        import_id = self.import_history_counter
        self.import_history_counter += 1
        
        import_record = {
            "id": import_id,
            "source_type": import_data["source_type"],
            "source_location": import_data["source_location"],
            "service_id": import_data.get("service_id"),
            "status": import_data["status"],
            "error_message": import_data.get("error_message"),
            "imported_endpoints_count": import_data.get("imported_endpoints_count", 0),
            "created_at": datetime.now()
        }
        
        self.import_history[import_id] = import_record
        return import_record
    
    def get_import_history(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        history = list(self.import_history.values())
        return history[skip:skip + limit]
    
    def get_import_details(self, import_id: int) -> Optional[Dict]:
        return self.import_history.get(import_id)
    
    # Data model operations (simplified for now)
    def create_data_model(self, model_data: Dict) -> Dict:
        model_id = self.data_model_counter
        self.data_model_counter += 1
        
        model = {
            "id": model_id,
            "name": model_data["name"],
            "schema": model_data["schema"],
            "service_id": model_data["service_id"],
            "taxonomy_id": model_data.get("taxonomy_id"),
            "description": model_data.get("description"),
            "model_type": model_data.get("model_type"),
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        self.data_models[model_id] = model
        return model
    
    def get_data_models_by_service(self, service_id: int) -> List[Dict]:
        return [
            model for model in self.data_models.values()
            if model["service_id"] == service_id
        ]

# Global cache instance
cache = InMemoryCache()

# Dependency function to get cache (similar to get_db)
def get_cache():
    return cache
