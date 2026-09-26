# Discord Collaboration Integration

Sync team chat and notifications between AstrovoxAI and Discord.

## Setup

1. Create a Discord application at https://discord.com/developers/applications
2. Enable the `bot` scope and Message Content Intent
3. Invite the bot to your server with `Send Messages` and `Read Message History` permissions
4. Capture the bot token and client ID

## Environment Variables

- `DISCORD_BOT_TOKEN` — Discord bot token
- `DISCORD_CLIENT_ID` — Discord application client ID
- `ASTROVOX_API_KEY` — AstrovoxAI API key
- `ASTROVOX_API_URL` — AstrovoxAI backend URL

## Usage

```bash
node index.js
```

## Features

- Mirror AstrovoxAI team chat to Discord channels
- Relay Discord messages into AstrovoxAI collaboration channels
- Sync reaction counts and pinned messages
