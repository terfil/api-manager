from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from app.config import settings
from app.database import create_tables
from app.routers import services, endpoints, relationships, taxonomy, import_data, analysis, scalar_ui

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Load test data on startup for in-memory cache
@app.on_event("startup")
async def startup_event():
    from app.database import get_db
    from app.utils.openapi_parser import OpenAPIParser
    
    db = get_db()
    parser = OpenAPIParser()
    
    # List of test data files to load
    test_files = [
        "app/test_data/user_management.json",
        "app/test_data/order_management.json", 
        "app/test_data/product_catalog.json",
        "app/test_data/sample_openapi.json"
    ]
    
    loaded_services = 0
    total_endpoints = 0
    
    for file_path in test_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()
            
            spec, error = parser.parse_from_file_content(content, file_path)
            
            if error == "success":
                # Extract service information
                service_info = parser.extract_service_info(spec)
                service = db.create_service(service_info)
                
                # Extract and create endpoints
                endpoints_data = parser.extract_endpoints(spec)
                for endpoint_data in endpoints_data:
                    endpoint_data["service_id"] = service["id"]
                    db.create_endpoint(endpoint_data)
                
                # Extract and create data models
                models_data = parser.extract_data_models(spec)
                for model_data in models_data:
                    model_data["service_id"] = service["id"]
                    db.create_data_model(model_data)
                
                # Create import history record
                import_record_data = {
                    "source_type": "file",
                    "source_location": file_path.split("/")[-1],
                    "service_id": service["id"],
                    "status": "success",
                    "error_message": None,
                    "imported_endpoints_count": len(endpoints_data)
                }
                db.create_import_history(import_record_data)
                
                loaded_services += 1
                total_endpoints += len(endpoints_data)
                
                print(f"Loaded service: {service['name']} with {len(endpoints_data)} endpoints and {len(models_data)} data models")
            else:
                print(f"Failed to parse {file_path}: {error}")
                
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    if loaded_services > 0:
        print(f"Successfully loaded {loaded_services} services with {total_endpoints} total endpoints")
        
        # Analyze relationships after loading all services
        try:
            from app.utils.relationship_analyzer import RelationshipAnalyzer
            analyzer = RelationshipAnalyzer()
            analyzer.analyze_all_relationships(db)
            print("Relationship analysis completed successfully")
        except Exception as e:
            print(f"Error during relationship analysis: {e}")
    else:
        print("No test data was loaded successfully")

# Include routers
app.include_router(services.router, prefix="/api/v1", tags=["services"])
app.include_router(endpoints.router, prefix="/api/v1", tags=["endpoints"])
app.include_router(relationships.router, prefix="/api/v1", tags=["relationships"])
app.include_router(taxonomy.router, prefix="/api/v1", tags=["taxonomy"])
app.include_router(import_data.router, prefix="/api/v1", tags=["import"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(scalar_ui.router, tags=["scalar-ui"])

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    # Serve import page
    @app.get("/import", response_class=HTMLResponse)
    async def import_page():
        with open(os.path.join(static_dir, "import.html"), "r") as f:
            return f.read()
    
    # Serve relationships page
    @app.get("/relationships", response_class=HTMLResponse)
    async def relationships_page():
        with open(os.path.join(static_dir, "relationships.html"), "r") as f:
            return f.read()

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Management Service</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 1000px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 40px; }
            .links { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 40px; }
            .link-card { 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 20px; 
                text-align: center; 
                text-decoration: none; 
                color: #333;
                transition: box-shadow 0.3s;
            }
            .link-card:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            .link-card h3 { margin-top: 0; color: #007acc; }
            .features { background-color: #f8f9fa; padding: 30px; border-radius: 8px; margin-bottom: 30px; }
            .feature-item { margin-bottom: 15px; }
            .feature-title { font-weight: bold; color: #28a745; }
            .import-section { background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin-bottom: 30px; }
            .import-title { color: #0056b3; margin-top: 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 API Management Service</h1>
                <p>Comprehensive API endpoint management with Scalar integration</p>
            </div>

            <div class="import-section">
                <h2 class="import-title">📥 Import APIs</h2>
                <p>Easily import your API specifications in multiple formats:</p>
                <div class="feature-item">
                    <span class="feature-title">Swagger JSON (v2.x)</span> - Direct support for Swagger 2.0 specifications
                </div>
                <div class="feature-item">
                    <span class="feature-title">OpenAPI JSON/YAML (v3.x)</span> - Full OpenAPI 3.x support
                </div>
                <div class="feature-item">
                    <span class="feature-title">File Upload & URL Import</span> - Import from local files or remote URLs
                </div>
                <p><strong>New:</strong> Dedicated <code>/api/v1/services/import/swagger</code> endpoint for Swagger JSON files!</p>
            </div>

            <div class="features">
                <h2>✨ Key Features</h2>
                <div class="feature-item">
                    <span class="feature-title">Automatic Schema Extraction</span> - Extract endpoints, parameters, and data models automatically
                </div>
                <div class="feature-item">
                    <span class="feature-title">Relationship Discovery</span> - Find connections between different API endpoints
                </div>
                <div class="feature-item">
                    <span class="feature-title">Data Model Taxonomy</span> - Organize and categorize your data models
                </div>
                <div class="feature-item">
                    <span class="feature-title">Interactive Documentation</span> - Beautiful Scalar UI for API exploration
                </div>
            </div>

            <div class="links">
                <a href="/import" class="link-card">
                    <h3>📥 Import APIs</h3>
                    <p>Upload Swagger JSON files to import services</p>
                </a>
                <a href="/relationships" class="link-card">
                    <h3>🔗 Model Relationships</h3>
                    <p>Explore relationships between data models</p>
                </a>
                <a href="/docs" class="link-card">
                    <h3>📚 API Documentation</h3>
                    <p>Interactive Swagger UI for testing APIs</p>
                </a>
                <a href="/redoc" class="link-card">
                    <h3>📖 ReDoc</h3>
                    <p>Alternative API documentation</p>
                </a>
                <a href="/scalar" class="link-card">
                    <h3>⚡ Scalar UI</h3>
                    <p>Modern API documentation and testing</p>
                </a>
                <a href="/api/v1/services" class="link-card">
                    <h3>🔧 Services API</h3>
                    <p>Manage your API services</p>
                </a>
                <a href="/api/v1/import-history" class="link-card">
                    <h3>📋 Import History</h3>
                    <p>View your import history and status</p>
                </a>
            </div>
        </div>
    </body>
    </html>
    """

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.api_version}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
