// Discord Collaboration Integration
// Syncs team chat and reactions between AstrovoxAI and Discord.

const { Client, GatewayIntentBits, REST, Routes } = require('discord.js');
const { AstrovoxClient } = require('@astrovox/sdk');

const astrovox = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY,
  baseURL: process.env.ASTROVOX_API_URL || 'http://localhost:8000',
});

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ],
});

async function syncChannels(workspaceId) {
  const astrovoxChannels = await astrovox.get(`/api/team-chat/channels?workspace_id=${workspaceId}`);
  for (const channel of astrovoxChannels.channels || []) {
    console.log(`Would sync Astrovox channel ${channel.name} to Discord`);
  }
}

async function relayDiscordMessage(message, workspaceId) {
  try {
    await astrovox.post(`/api/team-chat/messages?workspace_id=${workspaceId}`, {
      channel_id: message.channelId,
      content: message.content,
    });
    console.log(`Relayed Discord message from ${message.channelId}`);
  } catch (error) {
    console.error('Failed to relay Discord message:', error.message);
  }
}

client.on('messageCreate', async (message) => {
  if (message.author.bot || message.interaction) return;
  const workspaceId = message.guild?.id || 'default';
  await relayDiscordMessage(message, workspaceId);
});

async function start() {
  try {
    await client.login(process.env.DISCORD_BOT_TOKEN);
    console.log('Discord collaboration integration started');
  } catch (error) {
    console.error('Failed to start Discord integration:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  const workspaceId = process.env.ASTROVOX_WORKSPACE_ID || 'default';
  syncChannels(workspaceId).then(() => start());
}

module.exports = { syncChannels, relayDiscordMessage, start };
