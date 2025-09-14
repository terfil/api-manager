# API Management Service

A comprehensive web service for managing API endpoints with advanced relationship discovery, data model taxonomy, and modern Scalar UI integration.

## 🚀 Features

### Core Functionality
- **Complete CRUD Operations** for API services and endpoints
- **OpenAPI Specification Import** from JSON/YAML files and URLs
- **Interactive API Documentation** with Scalar UI
- **Advanced Relationship Discovery** between endpoints
- **Hierarchical Data Model Taxonomy** management
- **Schema Similarity Analysis** across services
- **Real-time API Testing** with multiple client libraries

### Advanced Capabilities
- **Automatic Schema Extraction** from imported services
- **Common Field Detection** across different APIs
- **Data Flow Pattern Recognition** between endpoints
- **CRUD Relationship Identification** for resource operations
- **Graph Visualization Data** for relationship mapping
- **Auto-categorization** of data models

## 🛠️ Technology Stack

- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (development) / PostgreSQL (production)
- **UI Framework**: Scalar API Documentation
- **Analysis Engine**: NetworkX for graph analysis
- **API Standards**: OpenAPI 3.1 specification
- **Authentication**: Built-in FastAPI security features

## 📋 Prerequisites

- Python 3.11+
- pip package manager
- 4GB RAM minimum
- 1GB disk space

## 🔧 Installation

### 1. Clone and Setup
```bash
git clone <repository-url>
cd api_management_service
pip install -r requirements.txt
```

### 2. Start the Application
```bash
python run.py
```

The service will be available at:
- **Main Application**: http://localhost:8000
- **Scalar UI**: http://localhost:8000/scalar
- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📖 Quick Start Guide

### 1. Import Your First API

#### Option A: Import from File
```bash
curl -X POST "http://localhost:8000/api/v1/services/import/file" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-openapi-spec.json" \
  -F "service_name=My API" \
  -F "service_description=My API description"
```

#### Option B: Import from URL
```bash
curl -X POST "http://localhost:8000/api/v1/services/import" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "url",
    "source_location": "https://petstore.swagger.io/v2/swagger.json",
    "service_name": "Pet Store API",
    "service_description": "Sample pet store API"
  }'
```

### 2. View Your APIs
Navigate to http://localhost:8000/scalar to see your imported APIs with interactive documentation.

### 3. Analyze Relationships
```bash
curl -X POST "http://localhost:8000/api/v1/relationships/analyze"
```

### 4. Extract Data Models
```bash
curl -X POST "http://localhost:8000/api/v1/data-models/extract-from-service/1"
```

## 🎯 API Reference

### Services Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/services` | GET | List all services |
| `/api/v1/services` | POST | Create a new service |
| `/api/v1/services/{id}` | GET | Get service details |
| `/api/v1/services/{id}` | PUT | Update service |
| `/api/v1/services/{id}` | DELETE | Delete service |
| `/api/v1/services/{id}/statistics` | GET | Get service statistics |

### Endpoints Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/services/{id}/endpoints` | GET | List service endpoints |
| `/api/v1/services/{id}/endpoints` | POST | Create endpoint |
| `/api/v1/endpoints/{id}` | GET | Get endpoint details |
| `/api/v1/endpoints/{id}` | PUT | Update endpoint |
| `/api/v1/endpoints/{id}` | DELETE | Delete endpoint |

### Relationship Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/relationships/analyze` | POST | Analyze all relationships |
| `/api/v1/relationships` | GET | List relationships |
| `/api/v1/relationships/statistics` | GET | Get relationship statistics |
| `/api/v1/relationships/analysis/common-fields` | GET | Analyze common fields |
| `/api/v1/relationships/services/{id}` | GET | Get service relationships |

### Taxonomy Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/taxonomy` | GET | List taxonomies |
| `/api/v1/taxonomy` | POST | Create taxonomy |
| `/api/v1/taxonomy/{id}` | GET | Get taxonomy |
| `/api/v1/taxonomy/{id}` | PUT | Update taxonomy |
| `/api/v1/taxonomy/{id}` | DELETE | Delete taxonomy |
| `/api/v1/taxonomy/tree/full` | GET | Get full taxonomy tree |

### Data Models

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/data-models` | GET | List data models |
| `/api/v1/data-models` | POST | Create data model |
| `/api/v1/data-models/{id}` | GET | Get data model |
| `/api/v1/data-models/{id}` | PUT | Update data model |
| `/api/v1/data-models/{id}` | DELETE | Delete data model |
| `/api/v1/data-models/extract-from-service/{id}` | POST | Extract models from service |
| `/api/v1/data-models/analysis/schema-similarity` | GET | Analyze schema similarity |

## 🔍 Usage Examples

### Creating a Service Manually

```bash
curl -X POST "http://localhost:8000/api/v1/services" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Management API",
    "description": "API for managing user accounts",
    "version": "1.0.0",
    "base_url": "https://api.example.com/v1",
    "tags": ["users", "authentication"]
  }'
```

### Adding an Endpoint

```bash
curl -X POST "http://localhost:8000/api/v1/services/1/endpoints" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/users",
    "method": "GET",
    "summary": "List users",
    "description": "Retrieve a list of all users",
    "tags": ["users"],
    "parameters": {
      "query": [
        {
          "name": "page",
          "required": false,
          "schema": {"type": "integer", "default": 1},
          "description": "Page number"
        }
      ]
    },
    "response_schema": {
      "type": "object",
      "properties": {
        "users": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id": {"type": "integer"},
              "name": {"type": "string"},
              "email": {"type": "string"}
            }
          }
        },
        "total": {"type": "integer"}
      }
    }
  }'
```

### Creating a Taxonomy

```bash
curl -X POST "http://localhost:8000/api/v1/taxonomy" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Management",
    "description": "Taxonomy for user-related data models"
  }'
```

### Analyzing Schema Similarity

```bash
curl "http://localhost:8000/api/v1/data-models/analysis/schema-similarity?service_id=1"
```

## 🎨 Scalar UI Features

### Service Dashboard
- **Card-based Interface**: Clean overview of all services
- **Service Metadata**: Version, endpoint count, status information
- **Quick Actions**: Direct access to documentation and OpenAPI specs

### Interactive Documentation
- **Modern Design**: Professional, responsive interface
- **Live API Testing**: Send real requests with parameter input
- **Code Generation**: Examples in Shell, Ruby, Node.js, PHP, Python
- **Schema Visualization**: Request/response schema display
- **Search & Navigation**: Quick endpoint discovery

### API Testing
- **Parameter Input**: Interactive forms for all parameter types
- **Request Builder**: Visual request construction
- **Response Display**: Formatted JSON with syntax highlighting
- **Error Handling**: Clear error messages and validation

## 🔬 Relationship Analysis

### Types of Relationships Detected

1. **Common Fields**: Endpoints sharing similar field structures
2. **Schema Similarity**: Structural similarity between request/response schemas
3. **Data Flow Patterns**: Potential data flow between endpoints
4. **CRUD Relationships**: Operations on the same resource type

### Analysis Metrics

- **Similarity Scores**: 0.0 to 1.0 scale for schema similarity
- **Field Frequency**: How often fields appear across endpoints
- **Cross-Service Analysis**: Relationships between different APIs
- **Graph Metrics**: Centrality and connectivity measures

### Example Analysis Output

```json
{
  "total_relationships": 15,
  "common_fields_found": 3,
  "similar_schemas": 3,
  "data_flow_patterns": 9,
  "field_analysis": [
    {
      "field_name": "id",
      "frequency": 5,
      "services": ["Pet Store API", "User API"],
      "field_types": ["identifier"],
      "cross_service": true
    }
  ]
}
```

## 📊 Data Model Taxonomy

### Hierarchical Organization

The taxonomy system allows you to organize data models in a hierarchical structure:

```
API Data Models
├── Request Models
│   ├── Authentication
│   │   ├── Login Request
│   │   └── Register Request
│   └── User Management
│       ├── Create User Request
│       └── Update User Request
└── Response Models
    ├── Success Responses
    │   ├── User Response
    │   └── List Response
    └── Error Responses
        ├── Validation Error
        └── Not Found Error
```

### Auto-categorization

The system automatically categorizes extracted models:
- **Request Models**: Input schemas from endpoints
- **Response Models**: Output schemas from endpoints
- **Common Patterns**: Shared structures across services

### Schema Similarity Analysis

Compare data models to identify:
- **Identical Schemas**: 100% similarity score
- **Similar Structures**: High similarity with common fields
- **Reusable Components**: Schemas that can be standardized

## 🚀 Deployment

### Development Deployment

```bash
# Start the development server
python run.py
```

### Production Deployment

1. **Database Setup**
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb api_management

# Update database URL in config
export DATABASE_URL="postgresql://user:password@localhost/api_management"
```

2. **Environment Configuration**
```bash
export ENVIRONMENT=production
export SECRET_KEY=your-secret-key
export DATABASE_URL=your-database-url
```

3. **Run with Gunicorn**
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "run.py"]
```

```bash
docker build -t api-management-service .
docker run -p 8000:8000 api-management-service
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./api_management.db` |
| `SECRET_KEY` | Application secret key | Auto-generated |
| `DEBUG` | Enable debug mode | `False` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `MAX_UPLOAD_SIZE` | Max file upload size (MB) | `10` |

### Database Configuration

```python
# config.py
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./api_management.db")
SQLALCHEMY_DATABASE_URL = DATABASE_URL

# For PostgreSQL
# DATABASE_URL = "postgresql://user:password@localhost/api_management"

# For MySQL
# DATABASE_URL = "mysql://user:password@localhost/api_management"
```

## 🧪 Testing

### Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **API Tests**: HTTP endpoint testing
- **Performance Tests**: Load and stress testing

## 🐛 Troubleshooting

### Common Issues

1. **Import Fails**
   - Check OpenAPI specification validity
   - Ensure file size is under 10MB
   - Verify URL accessibility

2. **Relationship Analysis Slow**
   - Reduce dataset size for testing
   - Consider implementing pagination
   - Check available memory

3. **Scalar UI Not Loading**
   - Verify service is running on correct port
   - Check browser console for JavaScript errors
   - Ensure OpenAPI specs are valid

### Debug Mode

```bash
export DEBUG=True
python run.py
```

### Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create a virtual environment
3. Install dependencies: `pip install -r requirements-dev.txt`
4. Run tests: `pytest`
5. Submit pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add docstrings for all functions
- Write tests for new features

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **FastAPI**: Modern, fast web framework for building APIs
- **Scalar**: Beautiful API documentation and testing interface
- **SQLAlchemy**: Powerful ORM for database operations
- **NetworkX**: Graph analysis and visualization library
- **Pydantic**: Data validation using Python type annotations

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation at `/docs`
- Review the API reference at `/scalar`

---

**Built with ❤️ using FastAPI and Scalar**

