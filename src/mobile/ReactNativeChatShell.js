import React, { useState, useEffect, useRef, useCallback } from 'react'
import { View, Text, TextInput, TouchableOpacity, FlatList, KeyboardAvoidingView, Platform, ActivityIndicator, Alert } from 'react-native'
import { useChatHistory } from '../hooks/useChatHistory'
import { useOfflineMode } from '../offline/OfflineManager'
import { createRNStorage } from './storageAdapter'

const RN_STORAGE = createRNStorage('mobile_chat')

export function ReactNativeChatShell({
  session,
  conversationId,
  model = 'gpt-4',
  onConversationChange,
  onError
}) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const flatListRef = useRef(null)
  const { history } = useChatHistory()
  const { isOnline, saveMessageOffline } = useOfflineMode()

  useEffect(() => {
    loadMessages()
  }, [conversationId])

  const loadMessages = useCallback(async () => {
    try {
      const saved = await RN_STORAGE.get(`messages:${conversationId}`)
      if (Array.isArray(saved)) {
        setMessages(saved)
      }
    } catch (e) {
      console.error('Failed to load messages:', e)
    }
  }, [conversationId])

  const persistMessages = useCallback(async (msgs) => {
    try {
      await RN_STORAGE.set(`messages:${conversationId}`, msgs.slice(-200))
    } catch (e) {
      console.error('Failed to persist messages:', e)
    }
  }, [conversationId])

  const sendMessage = useCallback(async (e) => {
    e?.preventDefault?.()
    if (!input.trim() || loading) return

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
      id: Date.now(),
      offline: false
    }

    setMessages(prev => {
      const next = [...prev, userMessage]
      persistMessages(next)
      return next
    })
    setInput('')
    setLoading(true)
    setStreaming(true)

    try {
      const token = session?.access_token
      if (!token) {
        throw new Error('No authentication token available')
      }

      const apiBase = __DEV__ ? 'http://localhost:8000' : 'https://api.astrovox.ai'
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000)

      const response = await fetch(`${apiBase}/v1/chat/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          message: userMessage.content,
          model,
          stream: true
        }),
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(errorData.detail || 'Failed to send message')
      }

      const reader = response.body?.getReader()
      if (reader) {
        const aiMessage = {
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          id: Date.now() + 1,
          offline: false
        }

        setMessages(prev => {
          const next = [...prev, aiMessage]
          return next
        })

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = new TextDecoder().decode(value)
          const lines = chunk.split('\n').filter(line => line.startsWith('data: '))
          for (const line of lines) {
            const data = line.slice(6).trim()
            if (data === '[DONE]') continue
            try {
              const parsed = JSON.parse(data)
              const delta = parsed.choices?.[0]?.delta?.content || ''
              if (delta) {
                setMessages(prev => {
                  const updated = prev.map(m =>
                    m.id === aiMessage.id ? { ...m, content: m.content + delta } : m
                  )
                  persistMessages(updated)
                  return updated
                })
              }
            } catch {
              // skip malformed chunks
            }
          }
        }
      } else {
        const result = await response.json()
        if (result.ai_message) {
          setMessages(prev => {
            const next = [...prev, {
              ...result.ai_message,
              id: result.ai_message.id || Date.now() + 1,
              timestamp: new Date(result.ai_message.created_at).toISOString()
            }]
            persistMessages(next)
            return next
          })
        }
      }
    } catch (err) {
      if (!isOnline) {
        saveMessageOffline(userMessage)
      }
      onError?.(err)
    } finally {
      setLoading(false)
      setStreaming(false)
    }
  }, [input, loading, conversationId, model, isOnline, saveMessageOffline, onError, session, persistMessages])

  useEffect(() => {
    if (flatListRef.current && messages.length > 0) {
      flatListRef.current.scrollToEnd({ animated: true })
    }
  }, [messages])

  const renderMessage = useCallback(({ item }) => {
    const isUser = item.role === 'user'
    return (
      <View style={{
        alignSelf: isUser ? 'flex-end' : 'flex-start',
        maxWidth: '80%',
        padding: 12,
        borderRadius: 16,
        backgroundColor: isUser ? '#06b6d4' : '#0f172a',
        borderTopRightRadius: isUser ? 4 : 16,
        borderTopLeftRadius: isUser ? 16 : 4,
        marginVertical: 4,
        marginHorizontal: 12
      }}>
        <Text style={{
          fontSize: 14,
          lineHeight: 20,
          color: isUser ? '#02040a' : '#e2e8f0'
        }}>
          {item.content}
        </Text>
        <Text style={{
          fontSize: 10,
          color: isUser ? 'rgba(0,0,0,0.5)' : '#64748b',
          marginTop: 4,
          textAlign: 'right'
        }}>
          {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </Text>
      </View>
    )
  }, [])

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: '#02040a' }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <View style={{
        padding: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#1e293b',
        backgroundColor: 'rgba(4, 8, 20, 0.9)',
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <Text style={{
          fontSize: 13,
          color: '#67e8f9',
          letterSpacing: 1,
          fontWeight: '600'
        }}>
          ASTROVOX CHAT
        </Text>
        <View style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 6
        }}>
          {streaming && (
            <ActivityIndicator size="small" color="#06b6d4" />
          )}
          <View style={{
            width: 6,
            height: 6,
            borderRadius: 3,
            backgroundColor: isOnline ? '#34d399' : '#f87171'
          }} />
          <Text style={{
            fontSize: 10,
            color: isOnline ? '#34d399' : '#f87171'
          }}>
            {isOnline ? 'ONLINE' : 'OFFLINE'}
          </Text>
        </View>
      </View>

      <FlatList
        ref={flatListRef}
        data={messages}
        renderItem={renderMessage}
        keyExtractor={item => String(item.id)}
        contentContainerStyle={{ paddingVertical: 12, flexGrow: 1 }}
        ListEmptyComponent={
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingVertical: 60 }}>
            <Text style={{ color: '#64748b', fontSize: 12, textAlign: 'center' }}>
              Start a conversation with Astrovox AI
            </Text>
          </View>
        }
      />

      <View style={{
        padding: 12,
        borderTopWidth: 1,
        borderTopColor: '#1e293b',
        backgroundColor: 'rgba(4, 8, 20, 0.9)',
        flexDirection: 'row',
        gap: 8,
        alignItems: 'center'
      }}>
        <TextInput
          value={input}
          onChangeText={setInput}
          placeholder="Type your message..."
          placeholderTextColor="#64748b"
          editable={!loading}
          style={{
            flex: 1,
            padding: 12,
            borderWidth: 1,
            borderColor: '#1e293b',
            borderRadius: 24,
            backgroundColor: '#050a18',
            color: '#67e8f9',
            fontSize: 14,
            fontFamily: Platform.select({ ios: 'Menlo', android: 'monospace' }),
            maxHeight: 100
          }}
          onSubmitEditing={sendMessage}
          returnKeyType="send"
          blurOnSubmit={false}
        />
        <TouchableOpacity
          onPress={sendMessage}
          disabled={loading || !input.trim()}
          style={{
            padding: 12,
            backgroundColor: '#06b6d4',
            borderRadius: 24,
            opacity: loading || !input.trim() ? 0.5 : 1
          }}
        >
          <Text style={{
            color: '#02040a',
            fontWeight: '700',
            fontSize: 12
          }}>
            SEND
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

export default ReactNativeChatShell
