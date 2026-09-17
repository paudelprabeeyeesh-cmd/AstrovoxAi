'use client'

import { useState, useCallback } from 'react'
import { api } from '@/lib/api'
import type { DocumentUploadResult, IngestionJob } from '@/lib/api'

export interface UseDocumentsReturn {
  documents: any[]
  loading: boolean
  error: Error | null
  uploadFile: (file: File) => Promise<DocumentUploadResult | null>
  ingestWebsite: (url: string) => Promise<IngestionJob | null>
  ingestGitHub: (repo: string) => Promise<IngestionJob | null>
  searchDocuments: (q: string) => Promise<void>
  searchQuery: string
  setSearchQuery: (q: string) => void
  loadDocuments: () => Promise<void>
}

export function useDocuments() {
  const [documents, setDocuments] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<any[]>('/documents')
      setDocuments(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load documents'))
    } finally {
      setLoading(false)
    }
  }, [])

  const uploadFile = useCallback(async (file: File): Promise<DocumentUploadResult | null> => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.uploadDocument(file)
      setDocuments((prev) => [{ id: result.id, filename: result.filename, status: result.status, chunks: result.chunks, createdAt: result.createdAt }, ...prev])
      return result
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Upload failed'))
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const ingestWebsite = useCallback(async (url: string): Promise<IngestionJob | null> => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.ingestWebsite(url)
      setDocuments((prev) => [{ id: result.id, filename: result.source, status: result.status, chunks: 0, createdAt: result.createdAt }, ...prev])
      return result
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Website ingestion failed'))
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const ingestGitHub = useCallback(async (repo: string): Promise<IngestionJob | null> => {
    setLoading(true)
    setError(null)
    try {
      const result = await api.ingestGitHub(repo)
      setDocuments((prev) => [{ id: result.id, filename: result.source, status: result.status, chunks: 0, createdAt: result.createdAt }, ...prev])
      return result
    } catch (err) {
      setError(err instanceof Error ? err : new Error('GitHub ingestion failed'))
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const searchDocuments = useCallback(async (q: string) => {
    setSearchQuery(q)
    setLoading(true)
    setError(null)
    try {
      const data = await api.get<any[]>(`/documents?q=${encodeURIComponent(q)}`)
      setDocuments(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Search failed'))
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    documents,
    loading,
    error,
    uploadFile,
    ingestWebsite,
    ingestGitHub,
    searchDocuments,
    searchQuery,
    setSearchQuery,
    loadDocuments,
  }
}
