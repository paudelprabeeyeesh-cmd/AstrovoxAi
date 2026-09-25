'use client'

import { useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { MemoryClassification } from '@/lib/api'

export interface MemoryItem {
  id: string
  title: string
  content: string
  category: string
  tags: string[]
  createdAt: string
  updatedAt: string
}

export function useMemories() {
  const [memories, setMemories] = useState<MemoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const loadMemories = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (categoryFilter !== 'all') params.set('category', categoryFilter)
      if (searchQuery) params.set('q', searchQuery)
      const data = await api.get<MemoryItem[]>(`/memory?${params.toString()}`)
      setMemories(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load memories'))
    } finally {
      setLoading(false)
    }
  }, [categoryFilter, searchQuery])

  const deleteMemory = useCallback(async (id: string) => {
    try {
      await api.delete(`/memory/${id}`)
      setMemories((prev) => prev.filter((m) => m.id !== id))
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to delete memory'))
    }
  }, [])

  const clearAllMemories = useCallback(async () => {
    try {
      await api.delete('/memory')
      setMemories([])
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to clear memories'))
    }
  }, [])

  const classifyContent = useCallback(async (content: string): Promise<MemoryClassification | null> => {
    try {
      return await api.classifyMemory(content)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to classify'))
      return null
    }
  }, [])

  const filteredMemories = memories.filter((memory) => {
    if (categoryFilter !== 'all' && memory.category !== categoryFilter) return false
    if (searchQuery && !memory.title.toLowerCase().includes(searchQuery.toLowerCase()) && !memory.content.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  return {
    memories: filteredMemories,
    loading,
    error,
    categoryFilter,
    setCategoryFilter,
    searchQuery,
    setSearchQuery,
    loadMemories,
    deleteMemory,
    clearAllMemories,
    classifyContent,
  }
}
