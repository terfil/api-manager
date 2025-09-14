import json
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict
import networkx as nx
from sqlalchemy.orm import Session
from ..models import Endpoint, Relationship, Service
from ..schemas import RelationshipType

class RelationshipAnalyzer:
    """Analyzes relationships between API endpoints"""
    
    def __init__(self, db: Session):
        self.db = db
        self.similarity_threshold = 0.3  # Minimum similarity score to create relationship
    
    def analyze_all_relationships(self) -> Dict[str, Any]:
        """Analyze relationships between all endpoints"""
        endpoints = self.db.query(Endpoint).all()
        
        # Clear existing relationships
        self.db.query(Relationship).delete()
        self.db.commit()
        
        results = {
            "total_endpoints": len(endpoints),
            "relationships_created": 0,
            "common_fields_found": 0,
            "similar_schemas": 0,
            "data_flow_patterns": 0
        }
        
        # Analyze pairwise relationships
        for i, endpoint1 in enumerate(endpoints):
            for j, endpoint2 in enumerate(endpoints[i+1:], i+1):
                relationships = self._analyze_endpoint_pair(endpoint1, endpoint2)
                
                for rel_type, rel_data in relationships.items():
                    if rel_data["score"] >= self.similarity_threshold:
                        relationship = Relationship(
                            source_endpoint_id=endpoint1.id,
                            target_endpoint_id=endpoint2.id,
                            relationship_type=rel_type,
                            common_fields=rel_data.get("common_fields", []),
                            similarity_score=rel_data["score"],
                            relationship_metadata=rel_data.get("metadata", {})
                        )
                        self.db.add(relationship)
                        results["relationships_created"] += 1
                        
                        if rel_type == RelationshipType.COMMON_FIELDS:
                            results["common_fields_found"] += 1
                        elif rel_type == RelationshipType.SIMILAR_SCHEMA:
                            results["similar_schemas"] += 1
                        elif rel_type == RelationshipType.DATA_FLOW:
                            results["data_flow_patterns"] += 1
        
        self.db.commit()
        return results
    
    def _analyze_endpoint_pair(self, endpoint1: Endpoint, endpoint2: Endpoint) -> Dict[str, Dict[str, Any]]:
        """Analyze relationship between two endpoints"""
        relationships = {}
        
        # Skip if same endpoint
        if endpoint1.id == endpoint2.id:
            return relationships
        
        # Analyze common fields
        common_fields_rel = self._analyze_common_fields(endpoint1, endpoint2)
        if common_fields_rel["score"] > 0:
            relationships[RelationshipType.COMMON_FIELDS] = common_fields_rel
        
        # Analyze schema similarity
        schema_similarity_rel = self._analyze_schema_similarity(endpoint1, endpoint2)
        if schema_similarity_rel["score"] > 0:
            relationships[RelationshipType.SIMILAR_SCHEMA] = schema_similarity_rel
        
        # Analyze data flow patterns
        data_flow_rel = self._analyze_data_flow(endpoint1, endpoint2)
        if data_flow_rel["score"] > 0:
            relationships[RelationshipType.DATA_FLOW] = data_flow_rel
        
        return relationships
    
    def _analyze_common_fields(self, endpoint1: Endpoint, endpoint2: Endpoint) -> Dict[str, Any]:
        """Find common fields between endpoints"""
        fields1 = self._extract_fields_from_endpoint(endpoint1)
        fields2 = self._extract_fields_from_endpoint(endpoint2)
        
        common_fields = fields1.intersection(fields2)
        
        if not common_fields:
            return {"score": 0.0, "common_fields": [], "metadata": {}}
        
        # Calculate similarity score based on common fields ratio
        total_unique_fields = len(fields1.union(fields2))
        score = len(common_fields) / total_unique_fields if total_unique_fields > 0 else 0.0
        
        return {
            "score": score,
            "common_fields": list(common_fields),
            "metadata": {
                "endpoint1_fields": len(fields1),
                "endpoint2_fields": len(fields2),
                "common_count": len(common_fields),
                "total_unique": total_unique_fields
            }
        }
    
    def _analyze_schema_similarity(self, endpoint1: Endpoint, endpoint2: Endpoint) -> Dict[str, Any]:
        """Analyze structural similarity between schemas"""
        schema1 = self._get_combined_schema(endpoint1)
        schema2 = self._get_combined_schema(endpoint2)
        
        if not schema1 or not schema2:
            return {"score": 0.0, "metadata": {}}
        
        similarity_score = self._calculate_schema_similarity(schema1, schema2)
        
        return {
            "score": similarity_score,
            "metadata": {
                "schema1_complexity": self._calculate_schema_complexity(schema1),
                "schema2_complexity": self._calculate_schema_complexity(schema2),
                "structural_similarity": similarity_score
            }
        }
    
    def _analyze_data_flow(self, endpoint1: Endpoint, endpoint2: Endpoint) -> Dict[str, Any]:
        """Analyze potential data flow between endpoints"""
        # Check if one endpoint's response could be input to another
        response1 = endpoint1.response_schema
        request2 = endpoint2.request_schema
        
        response2 = endpoint2.response_schema
        request1 = endpoint1.request_schema
        
        flow_score = 0.0
        flow_direction = None
        
        # Check flow from endpoint1 to endpoint2
        if response1 and request2:
            score_1_to_2 = self._calculate_schema_compatibility(response1, request2)
            if score_1_to_2 > flow_score:
                flow_score = score_1_to_2
                flow_direction = "1_to_2"
        
        # Check flow from endpoint2 to endpoint1
        if response2 and request1:
            score_2_to_1 = self._calculate_schema_compatibility(response2, request1)
            if score_2_to_1 > flow_score:
                flow_score = score_2_to_1
                flow_direction = "2_to_1"
        
        # Check if endpoints are part of CRUD operations on same resource
        crud_score = self._analyze_crud_relationship(endpoint1, endpoint2)
        if crud_score > flow_score:
            flow_score = crud_score
            flow_direction = "crud_operations"
        
        return {
            "score": flow_score,
            "metadata": {
                "flow_direction": flow_direction,
                "crud_relationship": crud_score > 0,
                "path_similarity": self._calculate_path_similarity(endpoint1.path, endpoint2.path)
            }
        }
    
    def _extract_fields_from_endpoint(self, endpoint: Endpoint) -> Set[str]:
        """Extract all field names from endpoint schemas and parameters"""
        fields = set()
        
        # Extract from request schema
        if endpoint.request_schema:
            fields.update(self._extract_fields_from_schema(endpoint.request_schema))
        
        # Extract from response schema
        if endpoint.response_schema:
            fields.update(self._extract_fields_from_schema(endpoint.response_schema))
        
        # Extract from parameters
        if endpoint.parameters:
            for param_type, param_list in endpoint.parameters.items():
                for param in param_list:
                    if isinstance(param, dict) and "name" in param:
                        fields.add(param["name"])
        
        return fields
    
    def _extract_fields_from_schema(self, schema: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Recursively extract field names from JSON schema"""
        fields = set()
        
        if not isinstance(schema, dict):
            return fields
        
        # Handle properties
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                field_name = f"{prefix}.{prop_name}" if prefix else prop_name
                fields.add(field_name)
                
                # Recursively extract nested fields
                if isinstance(prop_schema, dict):
                    fields.update(self._extract_fields_from_schema(prop_schema, field_name))
        
        # Handle array items
        if "items" in schema and isinstance(schema["items"], dict):
            fields.update(self._extract_fields_from_schema(schema["items"], f"{prefix}[]"))
        
        # Handle allOf, oneOf, anyOf
        for key in ["allOf", "oneOf", "anyOf"]:
            if key in schema and isinstance(schema[key], list):
                for sub_schema in schema[key]:
                    if isinstance(sub_schema, dict):
                        fields.update(self._extract_fields_from_schema(sub_schema, prefix))
        
        return fields
    
    def _get_combined_schema(self, endpoint: Endpoint) -> Dict[str, Any]:
        """Get combined schema from request and response"""
        combined = {"type": "object", "properties": {}}
        
        if endpoint.request_schema:
            if "properties" in endpoint.request_schema:
                combined["properties"].update(endpoint.request_schema["properties"])
        
        if endpoint.response_schema:
            if "properties" in endpoint.response_schema:
                combined["properties"].update(endpoint.response_schema["properties"])
        
        return combined if combined["properties"] else None
    
    def _calculate_schema_similarity(self, schema1: Dict[str, Any], schema2: Dict[str, Any]) -> float:
        """Calculate structural similarity between two schemas"""
        fields1 = self._extract_fields_from_schema(schema1)
        fields2 = self._extract_fields_from_schema(schema2)
        
        if not fields1 and not fields2:
            return 0.0
        
        if not fields1 or not fields2:
            return 0.0
        
        intersection = fields1.intersection(fields2)
        union = fields1.union(fields2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_schema_complexity(self, schema: Dict[str, Any]) -> int:
        """Calculate complexity score of a schema"""
        if not isinstance(schema, dict):
            return 0
        
        complexity = 0
        
        # Count properties
        if "properties" in schema:
            complexity += len(schema["properties"])
            
            # Add complexity for nested objects
            for prop_schema in schema["properties"].values():
                if isinstance(prop_schema, dict):
                    complexity += self._calculate_schema_complexity(prop_schema)
        
        # Add complexity for arrays
        if "items" in schema:
            complexity += 1
            if isinstance(schema["items"], dict):
                complexity += self._calculate_schema_complexity(schema["items"])
        
        return complexity
    
    def _calculate_schema_compatibility(self, output_schema: Dict[str, Any], input_schema: Dict[str, Any]) -> float:
        """Calculate how compatible output schema is with input schema"""
        output_fields = self._extract_fields_from_schema(output_schema)
        input_fields = self._extract_fields_from_schema(input_schema)
        
        if not input_fields:
            return 0.0
        
        # Calculate how many input fields can be satisfied by output
        satisfied_fields = output_fields.intersection(input_fields)
        return len(satisfied_fields) / len(input_fields)
    
    def _analyze_crud_relationship(self, endpoint1: Endpoint, endpoint2: Endpoint) -> float:
        """Analyze if endpoints are CRUD operations on same resource"""
        # Extract resource from path (remove parameters)
        path1_clean = self._clean_path(endpoint1.path)
        path2_clean = self._clean_path(endpoint2.path)
        
        # Check if paths are similar (same resource)
        path_similarity = self._calculate_path_similarity(path1_clean, path2_clean)
        
        if path_similarity < 0.7:  # Not similar enough paths
            return 0.0
        
        # Check if methods suggest CRUD operations
        crud_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
        if endpoint1.method in crud_methods and endpoint2.method in crud_methods:
            # Different methods on same resource suggest CRUD relationship
            if endpoint1.method != endpoint2.method:
                return 0.8
        
        return 0.0
    
    def _clean_path(self, path: str) -> str:
        """Clean path by removing path parameters"""
        import re
        # Remove path parameters like {id}, {userId}, etc.
        cleaned = re.sub(r'\{[^}]+\}', '', path)
        # Remove trailing slashes and normalize
        cleaned = cleaned.rstrip('/').lower()
        return cleaned
    
    def _calculate_path_similarity(self, path1: str, path2: str) -> float:
        """Calculate similarity between two API paths"""
        # Split paths into segments
        segments1 = [s for s in path1.split('/') if s]
        segments2 = [s for s in path2.split('/') if s]
        
        if not segments1 and not segments2:
            return 1.0
        
        if not segments1 or not segments2:
            return 0.0
        
        # Calculate segment similarity
        max_len = max(len(segments1), len(segments2))
        min_len = min(len(segments1), len(segments2))
        
        common_segments = 0
        for i in range(min_len):
            if segments1[i] == segments2[i] or self._are_similar_segments(segments1[i], segments2[i]):
                common_segments += 1
        
        return common_segments / max_len
    
    def _are_similar_segments(self, seg1: str, seg2: str) -> bool:
        """Check if two path segments are similar"""
        # Check if both are path parameters
        if seg1.startswith('{') and seg2.startswith('{'):
            return True
        
        # Check string similarity
        if len(seg1) > 3 and len(seg2) > 3:
            # Simple substring check
            return seg1 in seg2 or seg2 in seg1
        
        return False
    
    def get_relationship_graph(self) -> Dict[str, Any]:
        """Generate a graph representation of endpoint relationships"""
        relationships = self.db.query(Relationship).all()
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes (endpoints)
        endpoints = self.db.query(Endpoint).all()
        for endpoint in endpoints:
            G.add_node(endpoint.id, 
                      label=f"{endpoint.method} {endpoint.path}",
                      service_id=endpoint.service_id,
                      method=endpoint.method,
                      path=endpoint.path)
        
        # Add edges (relationships)
        for rel in relationships:
            G.add_edge(rel.source_endpoint_id, rel.target_endpoint_id,
                      relationship_type=rel.relationship_type,
                      similarity_score=rel.similarity_score,
                      common_fields=rel.common_fields)
        
        # Calculate graph metrics
        metrics = {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "density": nx.density(G),
            "connected_components": nx.number_connected_components(G)
        }
        
        # Find most connected endpoints
        degree_centrality = nx.degree_centrality(G)
        most_connected = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Convert to serializable format
        graph_data = {
            "nodes": [
                {
                    "id": node_id,
                    "label": data["label"],
                    "service_id": data["service_id"],
                    "method": data["method"],
                    "path": data["path"]
                }
                for node_id, data in G.nodes(data=True)
            ],
            "edges": [
                {
                    "source": edge[0],
                    "target": edge[1],
                    "relationship_type": data["relationship_type"],
                    "similarity_score": data["similarity_score"],
                    "common_fields": data.get("common_fields", [])
                }
                for edge, data in G.edges(data=True)
            ],
            "metrics": metrics,
            "most_connected": [
                {
                    "endpoint_id": endpoint_id,
                    "centrality_score": score,
                    "endpoint_info": G.nodes[endpoint_id]
                }
                for endpoint_id, score in most_connected
            ]
        }
        
        return graph_data
    
    def analyze_common_fields_across_services(self) -> Dict[str, Any]:
        """Analyze common fields across all services"""
        services = self.db.query(Service).all()
        field_analysis = defaultdict(lambda: {
            "frequency": 0,
            "services": set(),
            "endpoints": set(),
            "field_types": set()
        })
        
        for service in services:
            endpoints = self.db.query(Endpoint).filter(Endpoint.service_id == service.id).all()
            
            for endpoint in endpoints:
                fields = self._extract_fields_from_endpoint(endpoint)
                
                for field in fields:
                    field_analysis[field]["frequency"] += 1
                    field_analysis[field]["services"].add(service.name)
                    field_analysis[field]["endpoints"].add(f"{endpoint.method} {endpoint.path}")
                    
                    # Try to determine field type
                    field_type = self._infer_field_type(field, endpoint)
                    if field_type:
                        field_analysis[field]["field_types"].add(field_type)
        
        # Convert to serializable format and sort by frequency
        result = []
        for field_name, data in field_analysis.items():
            result.append({
                "field_name": field_name,
                "frequency": data["frequency"],
                "services": list(data["services"]),
                "endpoints": list(data["endpoints"]),
                "field_types": list(data["field_types"]),
                "cross_service": len(data["services"]) > 1
            })
        
        # Sort by frequency descending
        result.sort(key=lambda x: x["frequency"], reverse=True)
        
        return {
            "total_unique_fields": len(result),
            "cross_service_fields": len([f for f in result if f["cross_service"]]),
            "most_common_fields": result[:20],  # Top 20 most common fields
            "field_analysis": result
        }
    
    def _infer_field_type(self, field_name: str, endpoint: Endpoint) -> str:
        """Infer field type based on name and context"""
        field_lower = field_name.lower()
        
        # Common ID patterns
        if field_lower.endswith('id') or field_lower == 'id':
            return "identifier"
        
        # Date/time patterns
        if any(pattern in field_lower for pattern in ['date', 'time', 'created', 'updated', 'timestamp']):
            return "datetime"
        
        # Name patterns
        if any(pattern in field_lower for pattern in ['name', 'title', 'label']):
            return "name"
        
        # Email pattern
        if 'email' in field_lower:
            return "email"
        
        # Status/state patterns
        if any(pattern in field_lower for pattern in ['status', 'state', 'active', 'enabled']):
            return "status"
        
        # Count/number patterns
        if any(pattern in field_lower for pattern in ['count', 'total', 'number', 'amount']):
            return "numeric"
        
        return "unknown"

