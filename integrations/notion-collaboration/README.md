# Notion Collaboration Integration

Sync shared documents between AstrovoxAI and Notion.

## Setup

1. Create a Notion integration at https://www.notion.so/my-integrations
2. Enable read/write capabilities for pages and databases
3. Share target pages/databases with the integration
4. Capture the internal integration token

## Environment Variables

- `NOTION_API_KEY` — Notion internal integration token
- `ASTROVOX_API_KEY` — AstrovoxAI API key
- `ASTROVOX_API_URL` — AstrovoxAI backend URL

## Usage

```bash
npx tsx index.ts
```

## Features

- Push AstrovoxAI shared documents to Notion pages
- Pull Notion page content into AstrovoxAI documents
- Sync document version history as Notion page comments
