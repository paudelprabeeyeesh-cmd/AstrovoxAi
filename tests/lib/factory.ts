export function createFactory<T extends object>(blueprint: T): Factory<T> {
  let sequence = 0
  return {
    build(overrides?: Partial<T>): T {
      return { ...blueprint, ...overrides, id: overrides?.id ?? `id-${++sequence}` }
    },
    buildMany(count: number, overrides?: Partial<T>): T[] {
      return Array.from({ length: count }, (_, i) => this.build({ ...overrides, id: `${overrides?.id ?? 'id'}-${i}` }))
    },
    buildSequence(fn: (i: number) => Partial<T>): T[] {
      return Array.from({ length: 100 }, (_, i) => this.build(fn(i + 1)))
    }
  }
}

export type Factory<T> = {
  build(overrides?: Partial<T>): T
  buildMany(count: number, overrides?: Partial<T>): T[]
  buildSequence(fn: (i: number) => Partial<T>): T[]
}

export const UserFactory = createFactory({
  id: 'user-1',
  email: 'user@example.com',
  name: 'Test User',
  role: 'user',
  created_at: new Date('2025-01-01T00:00:00Z').toISOString()
})

export const ConversationFactory = createFactory({
  id: 'conv-1',
  title: 'Test Conversation',
  model: 'gpt-4',
  user_id: 'user-1',
  created_at: new Date().toISOString()
})

export const MessageFactory = createFactory({
  id: 'msg-1',
  conversation_id: 'conv-1',
  role: 'user',
  content: 'Hello',
  created_at: new Date().toISOString()
})

export const AIResponseFactory = createFactory({
  id: 'msg-1',
  role: 'assistant',
  content: 'Hello! How can I help?',
  model: 'gpt-4',
  created_at: new Date().toISOString()
})
