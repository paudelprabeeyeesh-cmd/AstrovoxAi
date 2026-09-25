import { describe, it, expect } from 'vitest'
import { createFactory, UserFactory, ConversationFactory, MessageFactory, AIResponseFactory } from '../lib/factory'

describe('factory', () => {
  it('createFactory builds objects with defaults', () => {
    const factory = createFactory({ name: 'Test', role: 'user' })
    const obj = factory.build()
    expect(obj.name).toBe('Test')
    expect(obj.role).toBe('user')
    expect(obj.id).toBeDefined()
  })

  it('createFactory applies overrides', () => {
    const factory = createFactory({ name: 'Test', role: 'user' })
    const obj = factory.build({ name: 'Override' })
    expect(obj.name).toBe('Override')
    expect(obj.role).toBe('user')
  })

  it('createFactory generates sequential ids', () => {
    const factory = createFactory({ name: 'Test' })
    const a = factory.build()
    const b = factory.build()
    expect(a.id).not.toBe(b.id)
  })

  it('createFactory.buildMany returns array', () => {
    const factory = createFactory({ name: 'Test' })
    const items = factory.buildMany(3)
    expect(items).toHaveLength(3)
    expect(items[0].name).toBe('Test')
  })

  it('createFactory.buildSequence applies fn', () => {
    const factory = createFactory({ name: 'Test' })
    const items = factory.buildSequence(i => ({ name: `Test ${i}` }))
    expect(items[0].name).toBe('Test 1')
    expect(items[1].name).toBe('Test 2')
  })

  it('UserFactory builds user objects', () => {
    const user = UserFactory.build()
    expect(user).toHaveProperty('id')
    expect(user).toHaveProperty('email')
    expect(user).toHaveProperty('name')
    expect(user).toHaveProperty('role')
  })

  it('ConversationFactory builds conversation objects', () => {
    const conv = ConversationFactory.build()
    expect(conv).toHaveProperty('id')
    expect(conv).toHaveProperty('title')
    expect(conv).toHaveProperty('model')
    expect(conv).toHaveProperty('user_id')
  })

  it('MessageFactory builds message objects', () => {
    const msg = MessageFactory.build()
    expect(msg).toHaveProperty('id')
    expect(msg).toHaveProperty('conversation_id')
    expect(msg).toHaveProperty('role', 'user')
    expect(msg).toHaveProperty('content')
  })

  it('AIResponseFactory builds assistant message objects', () => {
    const msg = AIResponseFactory.build()
    expect(msg).toHaveProperty('id')
    expect(msg).toHaveProperty('role', 'assistant')
    expect(msg).toHaveProperty('content')
    expect(msg).toHaveProperty('model')
  })
})