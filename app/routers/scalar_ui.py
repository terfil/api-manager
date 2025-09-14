from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Service, Endpoint
from app.config import settings

router = APIRouter()

@router.get("/scalar", response_class=HTMLResponse)
async def scalar_ui_main():
    """Main Scalar UI page showing all services"""
    return """
    <!doctype html>
    <html>
    <head>
        <title>API Management Service - Scalar</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                margin: 0; 
                background: #f8fafc;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem;
                text-align: center;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 2rem; 
            }
            .services-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-top: 2rem;
            }
            .service-card {
                background: white;
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .service-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            }
            .service-title {
                font-size: 1.25rem;
                font-weight: 600;
                color: #1a202c;
                margin-bottom: 0.5rem;
            }
            .service-description {
                color: #64748b;
                margin-bottom: 1rem;
                line-height: 1.5;
            }
            .service-meta {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                font-size: 0.875rem;
                color: #64748b;
            }
            .service-actions {
                display: flex;
                gap: 0.5rem;
            }
            .btn {
                padding: 0.5rem 1rem;
                border-radius: 6px;
                text-decoration: none;
                font-size: 0.875rem;
                font-weight: 500;
                transition: all 0.2s;
                border: none;
                cursor: pointer;
            }
            .btn-primary {
                background: #3b82f6;
                color: white;
            }
            .btn-primary:hover {
                background: #2563eb;
            }
            .btn-secondary {
                background: #f1f5f9;
                color: #475569;
                border: 1px solid #e2e8f0;
            }
            .btn-secondary:hover {
                background: #e2e8f0;
            }
            .loading {
                text-align: center;
                padding: 2rem;
                color: #64748b;
            }
            .error {
                background: #fef2f2;
                border: 1px solid #fecaca;
                color: #dc2626;
                padding: 1rem;
                border-radius: 6px;
                margin: 1rem 0;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚀 API Management Service</h1>
            <p>Comprehensive API documentation and testing with Scalar</p>
        </div>
        
        <div class="container">
            <div id="loading" class="loading">Loading services...</div>
            <div id="error" class="error" style="display: none;"></div>
            <div id="services-container" class="services-grid" style="display: none;"></div>
        </div>

        <script>
            async function loadServices() {
                try {
                    const response = await fetch('/api/v1/services');
                    const data = await response.json();
                    
                    const container = document.getElementById('services-container');
                    const loading = document.getElementById('loading');
                    const error = document.getElementById('error');
                    
                    if (!response.ok) {
                        throw new Error('Failed to load services');
                    }
                    
                    loading.style.display = 'none';
                    container.style.display = 'grid';
                    
                    if (data.services.length === 0) {
                        container.innerHTML = `
                            <div style="grid-column: 1 / -1; text-align: center; padding: 2rem; color: #64748b;">
                                <h3>No services found</h3>
                                <p>Import your first API specification to get started!</p>
                                <a href="/docs" class="btn btn-primary">Go to API Docs</a>
                            </div>
                        `;
                        return;
                    }
                    
                    container.innerHTML = data.services.map(service => `
                        <div class="service-card">
                            <div class="service-title">${service.name}</div>
                            <div class="service-description">${service.description || 'No description available'}</div>
                            <div class="service-meta">
                                <span>Version: ${service.version}</span>
                                <span>${service.endpoints_count} endpoints</span>
                            </div>
                            <div class="service-actions">
                                <a href="/scalar/service/${service.id}" class="btn btn-primary">View API Docs</a>
                                <a href="/api/v1/services/${service.id}/openapi.json" class="btn btn-secondary" target="_blank">OpenAPI Spec</a>
                            </div>
                        </div>
                    `).join('');
                    
                } catch (err) {
                    document.getElementById('loading').style.display = 'none';
                    const errorDiv = document.getElementById('error');
                    errorDiv.textContent = 'Error loading services: ' + err.message;
                    errorDiv.style.display = 'block';
                }
            }
            
            loadServices();
        </script>
    </body>
    </html>
    """

@router.get("/scalar/service/{service_id}", response_class=HTMLResponse)
async def scalar_ui_service(service_id: int, db: Session = Depends(get_db)):
    """Scalar UI for a specific service"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return f"""
    <!doctype html>
    <html>
    <head>
        <title>{service.name} - API Documentation</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <style>
            body {{ margin: 0; }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .header h1 {{ margin: 0; font-size: 1.5rem; }}
            .header a {{ 
                color: white; 
                text-decoration: none; 
                padding: 0.5rem 1rem; 
                background: rgba(255,255,255,0.2); 
                border-radius: 6px;
                transition: background 0.2s;
            }}
            .header a:hover {{ background: rgba(255,255,255,0.3); }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📚 {service.name}</h1>
            <a href="/scalar">← Back to Services</a>
        </div>
        <script
            id="api-reference"
            data-url="/api/v1/services/{service_id}/openapi.json"
            data-configuration='{{"theme":"purple","showSidebar":true,"hideDownloadButton":false}}'
        ></script>
        <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
    </body>
    </html>
    """

@router.get("/services/{service_id}/openapi.json")
async def get_service_openapi_spec(service_id: int, db: Session = Depends(get_db)):
    """Generate OpenAPI specification for a specific service"""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # If service has stored OpenAPI spec, return it
    if service.openapi_spec:
        return service.openapi_spec
    
    # Otherwise, generate OpenAPI spec from endpoints
    endpoints = db.query(Endpoint).filter(Endpoint.service_id == service_id).all()
    
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": service.name,
            "description": service.description or "",
            "version": service.version or "1.0.0"
        },
        "servers": [],
        "paths": {},
        "components": {
            "schemas": {}
        }
    }
    
    if service.base_url:
        openapi_spec["servers"].append({
            "url": service.base_url,
            "description": "API Server"
        })
    
    # Group endpoints by path
    paths = {}
    for endpoint in endpoints:
        if endpoint.path not in paths:
            paths[endpoint.path] = {}
        
        operation = {
            "summary": endpoint.summary or "",
            "description": endpoint.description or "",
            "tags": endpoint.tags or [],
            "responses": {}
        }
        
        # Add parameters
        if endpoint.parameters:
            parameters = []
            for param_type, param_list in endpoint.parameters.items():
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
        if endpoint.request_schema and endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": endpoint.request_schema
                    }
                }
            }
        
        # Add responses
        if endpoint.response_schema:
            operation["responses"]["200"] = {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": endpoint.response_schema
                    }
                }
            }
        else:
            operation["responses"]["200"] = {
                "description": "Successful response"
            }
        
        paths[endpoint.path][endpoint.method.lower()] = operation
    
    openapi_spec["paths"] = paths
    
    return openapi_spec

@router.get("/openapi-combined.json")
async def get_combined_openapi_spec(db: Session = Depends(get_db)):
    """Generate combined OpenAPI specification for all services"""
    services = db.query(Service).filter(Service.is_active == True).all()
    
    combined_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "API Management Service - Combined APIs",
            "description": "Combined OpenAPI specification for all managed services",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": f"http://localhost:{settings.port}",
                "description": "API Management Server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {}
        },
        "tags": []
    }
    
    service_tags = set()
    
    for service in services:
        endpoints = db.query(Endpoint).filter(Endpoint.service_id == service.id).all()
        
        # Add service as a tag
        service_tag = {
            "name": service.name,
            "description": service.description or f"Endpoints from {service.name}"
        }
        service_tags.add(service.name)
        
        for endpoint in endpoints:
            path_key = f"/services/{service.id}/proxy{endpoint.path}"
            
            if path_key not in combined_spec["paths"]:
                combined_spec["paths"][path_key] = {}
            
            operation = {
                "summary": f"[{service.name}] {endpoint.summary or endpoint.path}",
                "description": endpoint.description or f"Endpoint from {service.name}",
                "tags": [service.name] + (endpoint.tags or []),
                "responses": {}
            }
            
            # Add parameters
            if endpoint.parameters:
                parameters = []
                for param_type, param_list in endpoint.parameters.items():
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
            if endpoint.request_schema and endpoint.method.upper() in ["POST", "PUT", "PATCH"]:
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": endpoint.request_schema
                        }
                    }
                }
            
            # Add responses
            if endpoint.response_schema:
                operation["responses"]["200"] = {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": endpoint.response_schema
                        }
                    }
                }
            else:
                operation["responses"]["200"] = {
                    "description": "Successful response"
                }
            
            combined_spec["paths"][path_key][endpoint.method.lower()] = operation
    
    # Add service tags
    combined_spec["tags"] = [{"name": tag, "description": f"Endpoints from {tag}"} for tag in sorted(service_tags)]
    
    return combined_spec

