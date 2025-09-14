"""
Flask-compatible entry point for deployment
"""
from app.src.main import app

# For deployment compatibility
application = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

