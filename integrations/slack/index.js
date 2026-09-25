// Astrovox Slack Integration
// @ts-check

const { App } = require('@slack/bolt')
const { AstrovoxClient } = require('@astrovox/sdk')

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET
})

const astrovox = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY
})

app.message(async ({ message, say, client }) => {
  if (message.bot_id || message.subtype) return

  const typing = await client.chat.postMessage({
    channel: message.channel,
    text: 'Thinking...'
  })

  try {
    const conv = await astrovox.createConversation({
      title: `Slack: ${message.channel}`,
      model: 'gpt-4'
    })

    const response = await astrovox.sendMessage({
      conversationId: conv.id,
      message: message.text
    })

    await client.chat.update({
      channel: message.channel,
      ts: typing.ts,
      text: response.ai_message.content
    })
  } catch (error) {
    await client.chat.update({
      channel: message.channel,
      ts: typing.ts,
      text: `Error: ${error.message}`
    })
  }
})

app.command('/astrovox', async ({ command, ack, say }) => {
  await ack()
  const [action, ...args] = command.text.split(' ')

  switch (action) {
    case 'chat':
      await say(`Starting chat with Astrovox...`)
      break
    case 'help':
      await say(`
Astrovox Bot Commands:
/astrovox chat - Start a conversation
/astrovox help - Show this help
/astrovox models - List available models
      `)
      break
    default:
      await say('Unknown command. Try /astrovox help')
  }
})

(async () => {
  await app.start(process.env.PORT || 3000)
  console.log('Astrovox Slack bot is running!')
})()
