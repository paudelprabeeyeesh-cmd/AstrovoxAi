"""API Documentation setup for serving OpenAPI spec with Swagger UI."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

def setup_api_docs(app: FastAPI, docs_url: str = "/docs", openapi_url: str = "/openapi.json"):
    """Setup API documentation with Swagger UI."""
    
    # Create docs directory if it doesn't exist
    docs_dir = Path("app/api/docs")
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Mount static files for Swagger UI assets
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    @app.get(docs_url, response_class=HTMLResponse)
    async def swagger_ui_html():
        """Serve Swagger UI HTML."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <link type="text/css" rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
            <link rel="shortcut icon" href="https://fastapi.tiangolo.com/img/favicon.png">
            <title>AstrovoxAi API - Swagger UI</title>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
            <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
            <script>
            window.ui = SwaggerUIBundle({{
                url: "{openapi_url}",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout"
            }})
            </script>
        </body>
        </html>
        """
    
    @app.get(openapi_url)
    async def get_openapi_spec():
        """Serve the OpenAPI specification."""
        import yaml
        from fastapi.responses import FileResponse
        
        openapi_path = docs_dir / "openapi.yaml"
        if openapi_path.exists():
            return FileResponse(openapi_path, media_type='application/yaml')
        else:
            # Return a basic OpenAPI spec if file doesn't exist
            return {
                "openapi": "3.0.3",
                "info": {
                    "title": "AstrovoxAi API",
                    "version": "1.0.0",
                    "description": "AI-powered automation platform API"
                },
                "paths": {}
            }