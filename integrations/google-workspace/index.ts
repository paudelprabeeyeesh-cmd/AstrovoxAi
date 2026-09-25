import { google } from 'googleapis'
import { AstrovoxClient } from '@astrovox/sdk'

const astrovox = new AstrovoxClient({ apiKey: process.env.ASTROVOX_API_KEY })

export async function syncGmailThreads(query: string, maxResults = 10) {
  const gmail = google.gmail({ version: 'v1' })
  const res = await gmail.users.threads.list({
    userId: 'me',
    q: query,
    maxResults
  })

  const threads = res.data.threads || []
  const summaries = []

  for (const thread of threads) {
    const threadDetail = await gmail.users.threads.get({ userId: 'me', id: thread.id! })
    const messages = threadDetail.data.messages || []

    const conversation = await astrovox.createConversation({
      title: `Email: ${messages[0]?.payload?.headers?.find((h: any) => h.name === 'Subject')?.value || 'Thread'}`
    })

    for (const msg of messages) {
      const headers = msg.payload?.headers || []
      const from = headers.find((h: any) => h.name === 'From')?.value || ''
      const subject = headers.find((h: any) => h.name === 'Subject')?.value || ''
      const body = msg.payload?.body?.data || ''

      await astrovox.sendMessage({
        conversationId: conversation.id,
        message: `Email from ${from}: ${subject}\n\n${body}`
      })
    }

    summaries.push({
      threadId: thread.id,
      subject: messages[0]?.payload?.headers?.find((h: any) => h.name === 'Subject')?.value || '',
      messageCount: messages.length
    })
  }

  return summaries
}

export async function summarizeCalendarEvents(timeMin: string, timeMax: string) {
  const calendar = google.calendar({ version: 'v3' })
  const res = await calendar.events.list({
    calendarId: 'primary',
    timeMin,
    timeMax,
    singleEvents: true,
    orderBy: 'startTime'
  })

  const events = res.data.items || []
  const eventSummary = events.map(e => `${e.summary} (${e.start?.dateTime || e.start?.date})`).join('\n')

  const conv = await astrovox.createConversation({
    title: `Calendar: ${timeMin.split('T')[0]}`
  })

  const response = await astrovox.sendMessage({
    conversationId: conv.id,
    message: `Summarize my calendar for this period:\n${eventSummary}`
  })

  return response.ai_message.content
}

export async function appendToGoogleDoc(documentId: string, content: string) {
  const docs = google.docs({ version: 'v1' })
  await docs.documents.batchUpdate({
    documentId,
    requestBody: {
      requests: [{
        insertText: {
          text: content + '\n',
          endOfSegmentLocation: {}
        }
      }]
    }
  })
}
