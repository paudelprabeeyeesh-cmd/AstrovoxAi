# Sandbox

Isolated sandbox environment for testing Astrovox AI without affecting production.

## Features

- Isolated API key
- Separate database
- No rate limits
- Full API access

## Usage

```bash
# Start sandbox server
npm run sandbox

# Or use Docker
docker run -p 8001:8000 astrovox/sandbox
```

## Sandbox Endpoints

- `POST /sandbox/chat/message`
- `POST /sandbox/conversations`
- `GET /sandbox/conversations`

## Limitations

- Data is deleted after 24 hours
- No persistent storage
- Limited to 1000 requests/hour
