import { Client } from '@notionhq/client'
import { AstrovoxClient } from '@astrovox/sdk'

const notion = new Client({ auth: process.env.NOTION_API_KEY })
const astrovox = new AstrovoxClient({ apiKey: process.env.ASTROVOX_API_KEY })

export async function syncConversationToNotion(conversationId: string, databaseId: string) {
  const conversation = await astrovox.getConversation(conversationId)

  await notion.pages.create({
    parent: { database_id: databaseId },
    properties: {
      Name: { title: [{ text: { content: conversation.title } }] },
      Date: { date: { start: conversation.createdAt } }
    },
    children: conversation.messages.map(msg => ({
      object: 'block',
      type: 'paragraph',
      paragraph: {
        rich_text: [{ type: 'text', text: { content: `[${msg.role}]: ${msg.content}` } }]
      }
    }))
  })
}

export async function askAboutNotionPage(pageId: string, question: string) {
  const page = await notion.pages.retrieve({ page_id: pageId })
  const content = await extractPageContent(pageId)

  const conv = await astrovox.createConversation({
    title: `Notion: ${page.properties.Name.title[0]?.plain_text || 'Page'}`
  })

  const response = await astrovox.sendMessage({
    conversationId: conv.id,
    message: `Context from Notion page: ${content}\n\nQuestion: ${question}`
  })

  return response.ai_message.content
}

async function extractPageContent(pageId: string): Promise<string> {
  const blocks = await notion.blocks.children.list({ block_id: pageId })
  return blocks.results.map(block => {
    if (block.type === 'paragraph') {
      return block.paragraph.rich_text?.map(t => t.plain_text).join('') || ''
    }
    if (block.type === 'heading_2') {
      return block.heading_2.rich_text?.map(t => t.plain_text).join('') || ''
    }
    return ''
  }).join('\n\n')
}
