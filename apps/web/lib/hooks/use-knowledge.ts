'use client'

import { useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { KnowledgeGraph, KnowledgeEntity, KnowledgeRelationship } from '@/lib/api'

export interface UseKnowledgeReturn {
  graph: KnowledgeGraph | null
  loading: boolean
  error: Error | null
  loadGraph: () => Promise<void>
  addEntity: (entity: { name: string; type: string; properties: Record<string, unknown> }) => Promise<void>
  addRelationship: (rel: { sourceId: string; targetId: string; type: string; properties: Record<string, unknown> }) => Promise<void>
}

export function useKnowledge() {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const loadGraph = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getKnowledgeGraph()
      setGraph(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load graph'))
    } finally {
      setLoading(false)
    }
  }, [])

  const addEntity = useCallback(async (entity: { name: string; type: string; properties: Record<string, unknown> }) => {
    setLoading(true)
    setError(null)
    try {
      await api.post<KnowledgeGraph>('/knowledge/entities', entity)
      await loadGraph()
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to add entity'))
    } finally {
      setLoading(false)
    }
  }, [loadGraph])

  const addRelationship = useCallback(async (rel: { sourceId: string; targetId: string; type: string; properties: Record<string, unknown> }) => {
    setLoading(true)
    setError(null)
    try {
      await api.post<KnowledgeGraph>('/knowledge/relationships', rel)
      await loadGraph()
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to add relationship'))
    } finally {
      setLoading(false)
    }
  }, [loadGraph])

  return {
    graph,
    loading,
    error,
    loadGraph,
    addEntity,
    addRelationship,
  }
}
