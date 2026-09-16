'use client'

import { useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { SearchResult } from '@/lib/api'

export type SearchMode = 'semantic' | 'keyword' | 'hybrid'

export interface UseSearchReturn {
  query: string
  setQuery: (q: string) => void
  mode: SearchMode
  setMode: (m: SearchMode) => void
  results: SearchResult[]
  loading: boolean
  error: Error | null
  search: () => Promise<void>
  dateFilter: string
  setDateFilter: (d: string) => void
  typeFilter: string
  setTypeFilter: (t: string) => void
  hasSearched: boolean
}

export function useSearch() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('semantic')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [dateFilter, setDateFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  const search = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true)
    setError(null)
    setHasSearched(true)
    try {
      let data: SearchResult[] = []
      if (mode === 'semantic') data = await api.searchSemantic(query)
      else if (mode === 'keyword') data = await api.searchKeyword(query)
      else data = await api.searchHybrid(query)
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Search failed'))
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query, mode])

  const filteredResults = results.filter((result) => {
    if (dateFilter && result.createdAt) {
      const resultDate = new Date(result.createdAt).toISOString().split('T')[0]
      if (resultDate !== dateFilter) return false
    }
    if (typeFilter && result.type !== typeFilter) return false
    return true
  })

  return {
    query,
    setQuery,
    mode,
    setMode,
    results: filteredResults,
    loading,
    error,
    search,
    dateFilter,
    setDateFilter,
    typeFilter,
    setTypeFilter,
    hasSearched,
  }
}
