import { Client } from '@notionhq/client';
import { AstrovoxClient } from '@astrovox/sdk';

const notion = new Client({ auth: process.env.NOTION_API_KEY });
const astrovox = new AstrovoxClient({
  apiKey: process.env.ASTROVOX_API_KEY,
  baseURL: process.env.ASTROVOX_API_URL || 'http://localhost:8000',
});

async function syncDocumentsToNotion(workspaceId: string, databaseId: string) {
  const documents = await astrovox.get(`/api/collaboration/documents?workspace_id=${workspaceId}`);
  for (const doc of documents.documents || []) {
    try {
      await notion.pages.create({
        parent: { database_id: databaseId },
        properties: {
          Name: { title: [{ text: { content: doc.title } }] },
          Updated: { date: { start: new Date(doc.updated_at * 1000).toISOString() } },
        },
        children: [
          {
            object: 'block',
            type: 'paragraph',
            paragraph: { rich_text: [{ type: 'text', text: { content: doc.content || '' } }] },
          },
        ],
      });
      console.log(`Synced document ${doc.title} to Notion`);
    } catch (error) {
      console.error(`Failed to sync document ${doc.title}:`, error.message);
    }
  }
}

async function syncNotionPageToDocument(pageId: string, workspaceId: string) {
  const page = await notion.pages.retrieve({ page_id: pageId });
  const blocks = await notion.blocks.children.list({ block_id: pageId });
  const content = blocks.results
    .map((block) => {
      if (block.type === 'paragraph') {
        return block.paragraph.rich_text?.map((t) => t.plain_text).join('') || '';
      }
      if (block.type === 'heading_2') {
        return block.heading_2.rich_text?.map((t) => t.plain_text).join('') || '';
      }
      return '';
    })
    .join('\n\n');

  const title = page.properties.Name?.title?.[0]?.plain_text || 'Imported Notion Page';
  await astrovox.post(`/api/collaboration/documents?workspace_id=${workspaceId}`, {
    title,
    content,
    format: 'markdown',
  });
  console.log(`Imported Notion page ${pageId} as document`);
}

async function start() {
  const workspaceId = process.env.ASTROVOX_WORKSPACE_ID || 'ws-default';
  const databaseId = process.env.NOTION_DATABASE_ID;
  if (databaseId) {
    await syncDocumentsToNotion(workspaceId, databaseId);
  }
  console.log('Notion collaboration sync complete');
}

if (require.main === module) {
  start().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}

export { syncDocumentsToNotion, syncNotionPageToDocument, start };
