# Integration Setup Guides

Each integration below is supported by the AstrovoxAI integration layer
exposed at `/ecosystem/integrations/*`. The Python SDK method names are
shown alongside the curl examples for convenience.

## GitHub

1. Register an OAuth App at <https://github.com/settings/applications/new>.
2. Set the redirect URL to `https://<your-host>/oauth/github/callback`.
3. Connect:
   ```
   POST /ecosystem/integrations/connections
   {"provider": "github", "label": "CI", "scopes": ["repo"], "access_token": "..."}
   ```
4. Use `client.github_create_issue(connection_id, repo, title)` to create issues.

## GitLab

Same flow as GitHub; obtain a personal access token with the `api` scope.

## Slack

1. Create a Slack app at <https://api.slack.com/apps>.
2. Install it to your workspace and capture the bot token.
3. Connect with `provider: "slack"`, `access_token: "xoxb-..."`.
4. Send messages: `client.slack_post_message(connection_id, channel, text)`.

## Discord

Discord uses incoming webhooks rather than OAuth:

```
POST /ecosystem/integrations/connections
{"provider": "discord", "label": "Main", "config": {"webhook_url": "https://discord.com/api/webhooks/..."}}
```

## Google Drive / OneDrive / Dropbox

These use OAuth2; pass `access_token` + `refresh_token` when connecting and
the integration layer will handle token refresh.

## Notion

1. Create an internal integration at <https://www.notion.so/my-integrations>.
2. Share your pages with the integration.
3. Connect with `provider: "notion"` and the internal integration token.

## Jira

Use an API token from your Atlassian account; connect via OAuth2 or PAT.
The default scopes are `read:jira-work` and `write:jira-work`.

## Trello

Generate an API key and token from <https://trello.com/app-key>; connect via
OAuth1 or pass credentials in `config`.

## Common Operations

- `storage_list_files(connection_id, folder_id)` — list files in a folder.
- `storage_upload(connection_id, name, content, folder_id)` — upload a file.
- `notion_list_pages(connection_id, database_id)` — list pages.
- `jira_create_issue(connection_id, project, summary, description)` — create issues.
- `trello_create_card(connection_id, board, list_name, title, description)` — create cards.

## Error Handling

All integration calls raise `AstrovoxError` on failure. The status code and
payload are forwarded from the upstream provider so you can react
accordingly.