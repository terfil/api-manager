"""
Flask wrapper for FastAPI application deployment
"""
import sys
import os
from flask import Flask, request, Response
import requests
import threading
import time

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create Flask app
flask_app = Flask(__name__)

# FastAPI server will run on a different port
FASTAPI_PORT = 8001
FASTAPI_URL = f"http://localhost:{FASTAPI_PORT}"


# Start FastAPI server in background
def start_fastapi():
    import uvicorn
    from app.main import app as fastapi_app
    uvicorn.run(fastapi_app, host="0.0.0.0", port=FASTAPI_PORT, log_level="warning")


# Start FastAPI in a separate thread
fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
fastapi_thread.start()

# Wait for FastAPI to start
time.sleep(3)


@flask_app.route('/', defaults={'path': ''})
@flask_app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def proxy(path):
    """Proxy all requests to FastAPI server"""
    try:
        # Forward the request to FastAPI
        url = f"{FASTAPI_URL}/{path}"

        # Get query parameters
        params = request.args.to_dict()

        # Get headers (exclude host header)
        headers = {k: v for k, v in request.headers if k.lower() != 'host'}

        # Get request data
        data = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.is_json:
                data = request.get_json()
            else:
                data = request.get_data()

        # Make request to FastAPI
        response = requests.request(
            method=request.method,
            url=url,
            params=params,
            headers=headers,
            json=data if request.is_json else None,
            data=data if not request.is_json else None,
            files=request.files if request.files else None,
            timeout=30
        )

        # Return response
        return Response(
            response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )

    except Exception as e:
        return {"error": f"Proxy error: {str(e)}"}, 500


# For deployment compatibility
application = flask_app

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=8000, debug=False)
