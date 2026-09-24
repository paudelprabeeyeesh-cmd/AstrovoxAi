# Interactive API Documentation

## Swagger UI

AstrovoxAI exposes a Swagger UI at `/docs` when the backend is running.

```bash
# Start backend
cd 02-Backend
uvicorn app.main:app --reload --port 8000

# Open browser
open http://localhost:8000/docs
```

## Features

- **Try it out**: Execute real API calls from the browser
- **Schemas**: View request/response models
- **Auth**: Enter Bearer token for protected endpoints
- **Download**: Export OpenAPI spec via `/openapi.json`

## ReDoc

Alternative documentation available at `/redoc`.

```bash
open http://localhost:8000/redoc
```

## Postman Collection

Import `docs/postman_collection.json` into Postman for offline exploration.

```json
{
  "info": {
    "name": "AstrovoxAI API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health",
      "request": {
        "method": "GET",
        "url": "{{baseUrl}}/health"
      }
    },
    {
      "name": "Login",
      "request": {
        "method": "POST",
        "url": "{{baseUrl}}/auth/login",
        "body": {
          "mode": "raw",
          "raw": "{\"email\":\"user@example.com\",\"password\":\"secure_password\"}"
        }
      }
    }
  ]
}
```

## cURL Examples

See `docs/openapi.md` for full request/response examples.

## API Explorer

The built-in Swagger UI supports:
- Model exploration
- Request body validation
- Response code inspection
- OAuth2 flows (future)
