// Slack Collaboration Integration
// Syncs team chat between AstrovoxAI and Slack.

const { WebClient } = require('@slack/web-api');
const { AstrovoxClient } = require('@astrovox/sdk');

const slack = new WebClient(process.env.SLACK_BOT_TOKEN);
const astrovox = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY,
  baseURL: process.env.ASTROVOX_API_URL || 'http://localhost:8000',
});

async function syncChannels(workspaceId) {
  const astrovoxChannels = await astrovox.get(`/api/team-chat/channels?workspace_id=${workspaceId}`);
  for (const channel of astrovoxChannels.channels || []) {
    try {
      const result = await slack.conversations.create({
        name: `astrovox-${channel.name}`,
        is_private: channel.is_private,
      });
      console.log(`Synced channel ${channel.name} -> ${result.channel.id}`);
    } catch (error) {
      console.error(`Failed to sync channel ${channel.name}:`, error.message);
    }
  }
}

async function relaySlackMessages(channelId, workspaceId) {
  const history = await slack.conversations.history({ channel: channelId, limit: 100 });
  for (const msg of history.messages || []) {
    if (msg.bot_id || msg.subtype) continue;
    try {
      await astrovox.post(`/api/team-chat/messages?workspace_id=${workspaceId}`, {
        channel_id: channelId,
        content: msg.text,
      });
      console.log(`Relayed message from Slack ${channelId}`);
    } catch (error) {
      console.error('Failed to relay message:', error.message);
    }
  }
}

async function start() {
  const workspaceId = process.env.ASTROVOX_WORKSPACE_ID || 'ws-default';
  await syncChannels(workspaceId);
  console.log('Slack collaboration sync complete');
}

if (require.main === module) {
  start().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

module.exports = { syncChannels, relaySlackMessages, start };
