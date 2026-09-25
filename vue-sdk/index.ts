import { defineComponent, ref, onMounted, h } from 'vue'
import { AstrovoxClient, Message, Conversation } from '@astrovox/sdk'

export const AstrovoxChat = defineComponent({
  name: 'AstrovoxChat',
  props: {
    apiKey: { type: String, required: true },
    theme: { type: String, default: 'dark' },
    model: { type: String, default: 'gpt-4' },
    placeholder: { type: String, default: 'Type your message...' },
    height: { type: String, default: '600px' }
  },
  setup(props) {
    const messages = ref<Message[]>([])
    const input = ref('')
    const loading = ref(false)
    const conversation = ref<Conversation | null>(null)
    const messagesEndRef = ref<HTMLDivElement | null>(null)
    let client: AstrovoxClient | null = null

    onMounted(() => {
      client = new AstrovoxClient({ apiKey: props.apiKey })
    })

    const scrollToBottom = () => {
      messagesEndRef.value?.scrollIntoView({ behavior: 'smooth' })
    }

    const sendMessage = async () => {
      if (!input.value.trim() || loading.value) return
      if (!conversation.value && client) {
        conversation.value = await client.createConversation({ model: props.model })
      }

      const userMessage: Message = { role: 'user', content: input.value, timestamp: new Date().toISOString() }
      messages.value.push(userMessage)
      input.value = ''
      loading.value = true
      scrollToBottom()

      try {
        const response = await client!.sendMessage({
          conversationId: conversation.value!.id,
          message: input.value,
          model: props.model
        })
        messages.value.push({ role: 'assistant', ...response.ai_message })
      } catch (error) {
        console.error('Error:', error)
      } finally {
        loading.value = false
        scrollToBottom()
      }
    }

    const themeStyles = {
      dark: { background: '#02040a', surface: '#0f172a', border: '#1e293b', text: '#e2e8f0' },
      light: { background: '#ffffff', surface: '#f8fafc', border: '#e2e8f0', text: '#0f172a' },
      'high-contrast': { background: '#000000', surface: '#000000', border: '#ffffff', text: '#ffffff' }
    }[props.theme]

    return () => h('div', {
      style: {
        height: props.height,
        background: themeStyles.background,
        border: `1px solid ${themeStyles.border}`,
        borderRadius: '12px',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column'
      }
    }, [
      h('div', {
        style: {
          padding: '12px 16px',
          borderBottom: `1px solid ${themeStyles.border}`,
          background: themeStyles.surface
        }
      }, [
        h('h3', {
          style: {
            margin: 0,
            fontSize: '14px',
            color: '#67e8f9',
            letterSpacing: '1px',
            fontWeight: 600
          }
        }, 'ASTROVOX AI')
      ]),
      h('div', {
        ref: messagesEndRef,
        style: {
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }
      }, [
        ...messages.value.map((msg, i) =>
          h('div', {
            key: i,
            style: {
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '75%',
              padding: '12px 16px',
              borderRadius: '12px',
              background: msg.role === 'user' ? '#06b6d4' : themeStyles.surface,
              color: msg.role === 'user' ? '#02040a' : themeStyles.text,
              border: msg.role === 'user' ? 'none' : `1px solid ${themeStyles.border}`,
              fontSize: '13px',
              lineHeight: 1.6
            }
          }, msg.content)
        ),
        loading.value && h('div', {
          style: {
            display: 'flex',
            gap: '6px',
            padding: '12px 16px',
            background: themeStyles.surface,
            borderRadius: '12px',
            width: 'fit-content'
          }
        }, [
          h('span', { style: { width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4', animation: 'bounce 1.4s infinite' } }),
          h('span', { style: { width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4', animation: 'bounce 1.4s infinite 0.2s' } }),
          h('span', { style: { width: '8px', height: '8px', borderRadius: '50%', background: '#06b6d4', animation: 'bounce 1.4s infinite 0.4s' } })
        ])
      ]),
      h('form', {
        onSubmit: (e: Event) => { e.preventDefault(); sendMessage() },
        style: {
          padding: '12px 16px',
          borderTop: `1px solid ${themeStyles.border}`,
          background: themeStyles.surface,
          display: 'flex',
          gap: '8px'
        }
      }, [
        h('input', {
          value: input.value,
          onInput: (e: Event) => { input.value = (e.target as HTMLInputElement).value },
          placeholder: props.placeholder,
          disabled: loading.value,
          style: {
            flex: 1,
            padding: '10px 14px',
            border: `1px solid ${themeStyles.border}`,
            borderRadius: '24px',
            background: themeStyles.background,
            color: themeStyles.text,
            fontSize: '13px',
            fontFamily: 'inherit',
            outline: 'none'
          }
        }),
        h('button', {
          type: 'submit',
          disabled: loading.value || !input.value.trim(),
          style: {
            padding: '0 20px',
            background: '#06b6d4',
            color: '#02040a',
            border: 'none',
            borderRadius: '24px',
            cursor: 'pointer',
            fontWeight: 700,
            fontSize: '12px',
            fontFamily: 'inherit'
          }
        }, 'SEND')
      ])
    ])
  }
})

export default AstrovoxChat
