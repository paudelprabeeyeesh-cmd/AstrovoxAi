# Slack Collaboration Integration

Sync team chat channels and messages between AstrovoxAI and Slack.

## Setup

1. Create a Slack app at https://api.slack.com/apps
2. Enable `chat:write`, `channels:history`, `groups:history`, `im:history`, `im:write`
3. Install to workspace and capture the bot token

## Environment Variables

- `SLACK_BOT_TOKEN` — Bot user OAuth token
- `SLACK_SIGNING_SECRET` — Signing secret for request verification
- `ASTROVOX_API_KEY` — AstrovoxAI API key
- `ASTROVOX_API_URL` — AstrovoxAI backend URL

## Usage

```bash
node index.js
```

## Features

- Mirror AstrovoxAI team chat channels to Slack
- Relay Slack messages to AstrovoxAI collaboration channels
- Sync thread comments and reactions
