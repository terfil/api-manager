import json
import yaml
import requests
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse
import jsonschema
from jsonschema import validate, ValidationError

class OpenAPIParser:
    """Parser for OpenAPI specifications from various sources"""
    
    def __init__(self):
        self.openapi_schema = {
            "type": "object",
            "required": ["openapi", "info"],
            "properties": {
                "openapi": {"type": "string"},
                "info": {
                    "type": "object",
                    "required": ["title", "version"],
                    "properties": {
                        "title": {"type": "string"},
                        "version": {"type": "string"},
                        "description": {"type": "string"}
                    }
                },
                "paths": {"type": "object"},
                "components": {"type": "object"}
            }
        }
    
    def parse_from_url(self, url: str) -> Tuple[Dict[str, Any], str]:
        """Parse OpenAPI specification from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type or url.endswith('.json'):
                spec = response.json()
            elif 'application/yaml' in content_type or 'text/yaml' in content_type or url.endswith(('.yaml', '.yml')):
                spec = yaml.safe_load(response.text)
            else:
                # Try to parse as JSON first, then YAML
                try:
                    spec = response.json()
                except json.JSONDecodeError:
                    spec = yaml.safe_load(response.text)
            
            self._validate_openapi_spec(spec)
            return spec, "success"
            
        except requests.RequestException as e:
            return {}, f"Failed to fetch from URL: {str(e)}"
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return {}, f"Failed to parse specification: {str(e)}"
        except ValidationError as e:
            return {}, f"Invalid OpenAPI specification: {str(e)}"
        except Exception as e:
            return {}, f"Unexpected error: {str(e)}"
    
    def parse_from_file_content(self, content: str, filename: str) -> Tuple[Dict[str, Any], str]:
        """Parse OpenAPI specification from file content"""
        try:
            if filename.endswith('.json'):
                spec = json.loads(content)
            elif filename.endswith(('.yaml', '.yml')):
                spec = yaml.safe_load(content)
            else:
                # Try to parse as JSON first, then YAML
                try:
                    spec = json.loads(content)
                except json.JSONDecodeError:
                    spec = yaml.safe_load(content)
            
            self._validate_openapi_spec(spec)
            return spec, "success"
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return {}, f"Failed to parse file content: {str(e)}"
        except ValidationError as e:
            return {}, f"Invalid OpenAPI specification: {str(e)}"
        except Exception as e:
            return {}, f"Unexpected error: {str(e)}"
    
    def _validate_openapi_spec(self, spec: Dict[str, Any]) -> None:
        """Validate OpenAPI specification structure"""
        validate(instance=spec, schema=self.openapi_schema)
        
        # Additional validation
        openapi_version = spec.get("openapi", "")
        swagger_version = spec.get("swagger", "")
        
        # Support both OpenAPI 3.x and Swagger 2.x
        if not (openapi_version.startswith(("3.", "2.")) or 
                swagger_version.startswith("2.")):
            raise ValidationError("Unsupported OpenAPI/Swagger version")
        
        # Additional Swagger 2.x specific validation
        if swagger_version.startswith("2."):
            self._validate_swagger_spec(spec)
    def _validate_swagger_spec(self, spec: Dict[str, Any]) -> None:
        """Validate Swagger 2.x specification structure"""
        # Basic Swagger 2.x validation
        if not spec.get("info"):
            raise ValidationError("Missing 'info' section in Swagger spec")
        
        if not spec.get("paths"):
            raise ValidationError("Missing 'paths' section in Swagger spec")
        
        info = spec["info"]
        if not info.get("title"):
            raise ValidationError("Missing 'title' in Swagger info section")
        
        if not info.get("version"):
            raise ValidationError("Missing 'version' in Swagger info section")
    
    def is_swagger_spec(self, spec: Dict[str, Any]) -> bool:
        """Check if the specification is a Swagger 2.x or OpenAPI 3.x spec"""
        swagger_version = spec.get("swagger", "")
        openapi_version = spec.get("openapi", "")
        
        # Support both Swagger 2.x and OpenAPI 3.x specifications
        return (swagger_version.startswith("2.") or 
                openapi_version.startswith(("3.", "2.")))
    
    def convert_swagger_to_openapi(self, swagger_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Swagger 2.x spec to OpenAPI 3.x format (basic conversion)"""
        if not self.is_swagger_spec(swagger_spec):
            return swagger_spec
        
        # Basic conversion - in a real implementation, you'd want a more comprehensive conversion
        openapi_spec = swagger_spec.copy()
        openapi_spec["openapi"] = "3.0.0"
        
        # Convert host + basePath to servers
        host = swagger_spec.get("host", "")
        base_path = swagger_spec.get("basePath", "")
        if host:
            server_url = f"https://{host}{base_path}" if host.startswith("http") else f"http://{host}{base_path}"
            openapi_spec["servers"] = [{"url": server_url}]
        
        # Remove Swagger-specific fields
        openapi_spec.pop("swagger", None)
        openapi_spec.pop("host", None)
        openapi_spec.pop("basePath", None)
        openapi_spec.pop("schemes", None)
        
        return openapi_spec
    
    def extract_service_info(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract service information from OpenAPI spec"""
        info = spec.get("info", {})
        servers = spec.get("servers", [])
        
        base_url = None
        if servers:
            base_url = servers[0].get("url", "")
        
        return {
            "name": info.get("title", "Imported Service"),
            "description": info.get("description", ""),
            "version": info.get("version", "1.0.0"),
            "base_url": base_url,
            "openapi_spec": spec
        }
    
    def extract_endpoints(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract endpoints from OpenAPI specification"""
        endpoints = []
        paths = spec.get("paths", {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "summary": operation.get("summary", ""),
                        "description": operation.get("description", ""),
                        "tags": operation.get("tags", []),
                        "parameters": self._extract_parameters(operation),
                        "request_schema": self._extract_request_schema(operation, spec),
                        "response_schema": self._extract_response_schema(operation, spec)
                    }
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _extract_parameters(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameters from operation"""
        parameters = operation.get("parameters", [])
        
        param_groups = {
            "query": [],
            "path": [],
            "header": [],
            "cookie": []
        }
        
        for param in parameters:
            param_in = param.get("in", "query")
            if param_in in param_groups:
                param_groups[param_in].append({
                    "name": param.get("name"),
                    "required": param.get("required", False),
                    "schema": param.get("schema", {}),
                    "description": param.get("description", "")
                })
        
        return param_groups
    
    def _extract_request_schema(self, operation: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract request schema from operation"""
        request_body = operation.get("requestBody")
        if not request_body:
            return None
        
        content = request_body.get("content", {})
        
        # Look for JSON content first
        for content_type in ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                return self._resolve_schema_refs(schema, spec)
        
        # If no specific content type found, take the first one
        if content:
            first_content = next(iter(content.values()))
            schema = first_content.get("schema", {})
            return self._resolve_schema_refs(schema, spec)
        
        return None
    
    def _extract_response_schema(self, operation: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract response schema from operation"""
        responses = operation.get("responses", {})
        
        # Look for successful responses first
        for status_code in ["200", "201", "202", "204"]:
            if status_code in responses:
                response = responses[status_code]
                content = response.get("content", {})
                
                if "application/json" in content:
                    schema = content["application/json"].get("schema", {})
                    return self._resolve_schema_refs(schema, spec)
        
        # If no successful response found, take the first response with content
        for response in responses.values():
            content = response.get("content", {})
            if content:
                first_content = next(iter(content.values()))
                schema = first_content.get("schema", {})
                return self._resolve_schema_refs(schema, spec)
        
        return None
    
    def _resolve_schema_refs(self, schema: Dict[str, Any], spec: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve $ref references in schema"""
        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_path = schema["$ref"]
                if ref_path.startswith("#/"):
                    # Internal reference
                    path_parts = ref_path[2:].split("/")
                    resolved = spec
                    for part in path_parts:
                        resolved = resolved.get(part, {})
                    return self._resolve_schema_refs(resolved, spec)
                else:
                    # External reference - not supported for now
                    return schema
            else:
                # Recursively resolve refs in nested objects
                resolved = {}
                for key, value in schema.items():
                    resolved[key] = self._resolve_schema_refs(value, spec)
                return resolved
        elif isinstance(schema, list):
            return [self._resolve_schema_refs(item, spec) for item in schema]
        else:
            return schema
    
    def extract_data_models(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data models from OpenAPI specification"""
        models = []
        components = spec.get("components", {})
        schemas = components.get("schemas", {})
        
        for model_name, schema in schemas.items():
            model = {
                "name": model_name,
                "schema": self._resolve_schema_refs(schema, spec),
                "description": schema.get("description", ""),
                "model_type": "component"
            }
            models.append(model)
        
        return models
