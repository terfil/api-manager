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
    
    # Load sample OpenAPI data
    try:
        with open("app/test_data/sample_openapi.json", "r") as f:
            content = f.read()
        
        spec, error = parser.parse_from_file_content(content, "sample_openapi.json")
        
        if error == "success":
            # Extract service information
            service_info = parser.extract_service_info(spec)
            service = db.create_service(service_info)
            
            # Extract and create endpoints
            endpoints_data = parser.extract_endpoints(spec)
            for endpoint_data in endpoints_data:
                endpoint_data["service_id"] = service["id"]
                db.create_endpoint(endpoint_data)
            
            # Create import history record
            import_record_data = {
                "source_type": "file",
                "source_location": "sample_openapi.json",
                "service_id": service["id"],
                "status": "success",
                "error_message": None,
                "imported_endpoints_count": len(endpoints_data)
            }
            db.create_import_history(import_record_data)
            
            print(f"Loaded test data: {service['name']} with {len(endpoints_data)} endpoints")
        else:
            print(f"Failed to parse test data: {error}")
            
    except Exception as e:
        print(f"Error loading test data: {e}")

# Include routers
app.include_router(services.router, prefix="/api/v1", tags=["services"])
app.include_router(endpoints.router, prefix="/api/v1", tags=["endpoints"])
app.include_router(relationships.router, prefix="/api/v1", tags=["relationships"])
app.include_router(taxonomy.router, prefix="/api/v1", tags=["taxonomy"])
app.include_router(import_data.router, prefix="/api/v1", tags=["import"])
app.include_router(analysis.router, prefix="/api/v1", tags=["analysis"])
app.include_router(scalar_ui.router, tags=["scalar-ui"])

# Serve static files for Scalar UI
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
            .container { max-width: 800px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 40px; }
            .links { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
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
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 API Management Service</h1>
                <p>Comprehensive API endpoint management with Scalar integration</p>
            </div>
            <div class="links">
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
