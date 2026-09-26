# Roadmap Portal

The Roadmap Portal is a public, interactive view of AstrovoxAI's product roadmap.

## Access

Open `frontend/developer.html` and select the **Roadmap** tab, or visit the portal URL.

## Features

### Public Voting

Users can upvote or comment on proposed features. Voting weight is based on account age and API usage.

### Status Tracking

Each roadmap item has a status:

- **Proposed** — Under community discussion
- **Planned** — Accepted for an upcoming release
- **In Progress** — Active development
- **In Review** — PR open, awaiting merge
- **Released** — Shipped in the current version
- **Deprecated** — Removed or superseded

### Release Notes

Auto-generated release notes are linked from completed roadmap items.

### Subscribe

Users can subscribe to roadmap items to receive notifications when status changes.

## CLI Access

```bash
# List roadmap items
astrovox roadmap list --status planned

# Vote on an item
astrovox roadmap vote <item_id> --direction up

# Subscribe to updates
astrovox roadmap subscribe <item_id>
```

## API

```bash
GET /ecosystem/public/roadmap
GET /ecosystem/public/roadmap/{id}
POST /ecosystem/public/roadmap/{id}/vote
```

## Governance

- Roadmap items are reviewed monthly by the core team
- Top-voted items are prioritized for the next quarter
- Enterprise customers may submit private feature requests via the support portal
