// Astrovox Discord Integration
const { Client, GatewayIntentBits, SlashCommandBuilder, REST, Routes } = require('discord.js')
const { AstrovoxClient } = require('@astrovox/sdk')

const astrovox = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY
})

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
})

const commands = [
  new SlashCommandBuilder()
    .setName('chat')
    .setDescription('Chat with Astrovox AI')
    .addStringOption(option =>
      option.setName('message')
        .setDescription('Your message')
        .setRequired(true)
    ),
  new SlashCommandBuilder()
    .setName('models')
    .setDescription('List available models'),
  new SlashCommandBuilder()
    .setName('help')
    .setDescription('Show help')
]

const rest = new REST().setToken(process.env.DISCORD_BOT_TOKEN)

(async () => {
  try {
    console.log('Registering slash commands...')
    await rest.put(Routes.applicationCommands(process.env.DISCORD_CLIENT_ID), {
      body: commands.map(cmd => cmd.toJSON())
    })
    console.log('Slash commands registered!')
  } catch (error) {
    console.error(error)
  }
})()

client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return

  const { commandName } = interaction

  if (commandName === 'chat') {
    const message = interaction.options.getString('message')
    await interaction.deferReply()

    try {
      const conv = await astrovox.createConversation({
        title: `Discord: ${interaction.guild?.name || 'DM'}`,
        model: 'gpt-4'
      })

      const response = await astrovox.sendMessage({
        conversationId: conv.id,
        message
      })

      await interaction.editReply(response.ai_message.content)
    } catch (error) {
      await interaction.editReply(`Error: ${error.message}`)
    }
  }

  if (commandName === 'models') {
    await interaction.reply('Available models: gpt-4, gpt-4-turbo, claude-3-opus')
  }

  if (commandName === 'help') {
    await interaction.reply(`
Astrovox AI Discord Bot
Commands:
/chat <message> - Chat with AI
/models - List available models
/help - Show this message
    `)
  }
})

client.on('messageCreate', async message => {
  if (message.author.bot || message.interaction) return
  if (!message.mentions.has(client.user)) return

  const content = message.content.replace(/<@!?\d+>/g, '').trim()
  if (!content) return

  await message.channel.sendTyping()

  try {
    const conv = await astrovox.createConversation({
      title: `Discord: ${message.guild?.name || 'DM'}`,
      model: 'gpt-4'
    })

    const response = await astrovox.sendMessage({
      conversationId: conv.id,
      message: content
    })

    await message.reply(response.ai_message.content)
  } catch (error) {
    await message.reply(`Error: ${error.message}`)
  }
})

client.login(process.env.DISCORD_BOT_TOKEN)
